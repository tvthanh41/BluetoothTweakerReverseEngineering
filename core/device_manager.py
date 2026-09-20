import winreg
import ctypes
from ctypes import wintypes
from typing import List, Dict, Any, Optional, Set, Tuple
from .registry_manager import normalize_mac, format_mac, RegistryManager

REG_BTHPORT_DEVICES = r"SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters\Devices"

# Hardware IDs on which BtTweakerFltr.sys operates as a LowerFilter.
# The service (BtTweakerSvc.exe) normally writes LowerFilters on each
# device instance after pairing. If the service is dead, we replicate
# that behaviour in ensure_filter_attached().
_BTHENUM_FILTER_PROFILES = [
    r"BTHENUM\{0000110b-0000-1000-8000-00805f9b34fb}",  # A2DP Audio Sink
    r"BTHENUM\{0000110c-0000-1000-8000-00805f9b34fb}",  # AVRCP Target
    r"BTHENUM\{0000110e-0000-1000-8000-00805f9b34fb}",  # AVRCP Controller
]
_FILTER_DRIVER_NAME = "BtTweakerFltr"


def ensure_filter_attached(mac: str) -> Tuple[bool, str]:
    """
    Ensures BtTweakerFltr.sys is registered as a LowerFilter for all
    relevant BTHENUM PnP device instances that match the given MAC address.

    Normally BtTweakerSvc.exe handles this when a new device is paired.
    If the service is dead or expired, this function replicates that
    behaviour so the kernel driver can sniff AVDTP codec frames for
    newly-paired devices.

    Returns:
        (changed: bool, message: str)
        changed=True  → at least one instance was updated (device reconnect required).
        changed=False → all instances already had the filter, nothing changed.

    Requires admin rights (write access to HKLM\\SYSTEM\\CurrentControlSet\\Enum).
    """
    mac_norm = normalize_mac(mac).upper()
    base_enum = r"SYSTEM\CurrentControlSet\Enum"
    patched: List[str] = []
    already_ok: List[str] = []
    errors: List[str] = []

    for profile_prefix in _BTHENUM_FILTER_PROFILES:
        try:
            k_profile = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                f"{base_enum}\\{profile_prefix}",
                0,
                winreg.KEY_READ,
            )
        except FileNotFoundError:
            continue

        num_vid = winreg.QueryInfoKey(k_profile)[0]
        for i in range(num_vid):
            vid_key_name = winreg.EnumKey(k_profile, i)
            try:
                k_vid = winreg.OpenKey(k_profile, vid_key_name, 0, winreg.KEY_READ)
                num_inst = winreg.QueryInfoKey(k_vid)[0]
                for j in range(num_inst):
                    inst_name = winreg.EnumKey(k_vid, j)
                    # Instance names embed the MAC at the end, e.g.
                    # "b&62612bf&0&EFF6A4DA6051_C00000000"
                    if mac_norm not in inst_name.upper():
                        continue

                    inst_path = (
                        f"{base_enum}\\{profile_prefix}\\{vid_key_name}\\{inst_name}"
                    )

                    # Read current LowerFilters
                    try:
                        k_inst = winreg.OpenKey(
                            winreg.HKEY_LOCAL_MACHINE, inst_path, 0, winreg.KEY_READ
                        )
                        try:
                            existing, _ = winreg.QueryValueEx(k_inst, "LowerFilters")
                        except FileNotFoundError:
                            existing = []
                        winreg.CloseKey(k_inst)
                    except Exception:
                        existing = []

                    if _FILTER_DRIVER_NAME in existing:
                        already_ok.append(inst_name)
                        continue

                    # Write LowerFilters (requires admin / HKLM write access)
                    try:
                        k_inst_w = winreg.OpenKey(
                            winreg.HKEY_LOCAL_MACHINE,
                            inst_path,
                            0,
                            winreg.KEY_SET_VALUE,
                        )
                        new_val = list(existing) + [_FILTER_DRIVER_NAME]
                        winreg.SetValueEx(
                            k_inst_w, "LowerFilters", 0, winreg.REG_MULTI_SZ, new_val
                        )
                        winreg.CloseKey(k_inst_w)
                        patched.append(inst_name)
                    except PermissionError:
                        errors.append(f"No write access to {inst_path!r}. Run as admin.")
                    except Exception as e:
                        errors.append(f"{inst_name}: {e}")

                winreg.CloseKey(k_vid)
            except Exception:
                pass
        winreg.CloseKey(k_profile)

    if errors:
        return False, "; ".join(errors)
    if patched:
        return True, (
            f"Filter registered on {len(patched)} instance(s) for {mac_norm}. "
            "Please disconnect and reconnect the device for the driver to attach."
        )
    return False, (
        f"Filter already present on all {len(already_ok)} instance(s) for {mac_norm}. No action needed."
    )


class SYSTEMTIME(ctypes.Structure):
    _fields_ = [
        ('wYear', wintypes.WORD),
        ('wMonth', wintypes.WORD),
        ('wDayOfWeek', wintypes.WORD),
        ('wDay', wintypes.WORD),
        ('wHour', wintypes.WORD),
        ('wMinute', wintypes.WORD),
        ('wSecond', wintypes.WORD),
        ('wMilliseconds', wintypes.WORD)
    ]


class BLUETOOTH_ADDRESS(ctypes.Structure):
    _fields_ = [('ullLong', ctypes.c_ulonglong)]


class BLUETOOTH_DEVICE_INFO(ctypes.Structure):
    _fields_ = [
        ('dwSize', wintypes.DWORD),
        ('Address', BLUETOOTH_ADDRESS),
        ('ulClassofDevice', wintypes.ULONG),
        ('fConnected', wintypes.BOOL),
        ('fRemembered', wintypes.BOOL),
        ('fAuthenticated', wintypes.BOOL),
        ('stLastSeen', SYSTEMTIME),
        ('stLastUsed', SYSTEMTIME),
        ('szName', wintypes.WCHAR * 248)
    ]


class BLUETOOTH_DEVICE_SEARCH_PARAMS(ctypes.Structure):
    _fields_ = [
        ('dwSize', wintypes.DWORD),
        ('fReturnAuthenticated', wintypes.BOOL),
        ('fReturnRemembered', wintypes.BOOL),
        ('fReturnUnknown', wintypes.BOOL),
        ('fReturnConnected', wintypes.BOOL),
        ('fIssueInquiry', wintypes.BOOL),
        ('cTimeoutMultiplier', ctypes.c_ubyte),
        ('hRadio', wintypes.HANDLE)
    ]


def get_connected_bluetooth_macs() -> Set[str]:
    """Queries Windows Bluetooth API for all currently connected Bluetooth devices."""
    connected = set()
    try:
        bth = ctypes.windll.LoadLibrary('bthprops.cpl')
        bth.BluetoothFindFirstDevice.restype = wintypes.HANDLE
        bth.BluetoothFindFirstDevice.argtypes = [
            ctypes.POINTER(BLUETOOTH_DEVICE_SEARCH_PARAMS),
            ctypes.POINTER(BLUETOOTH_DEVICE_INFO)
        ]
        bth.BluetoothFindNextDevice.restype = wintypes.BOOL
        bth.BluetoothFindNextDevice.argtypes = [wintypes.HANDLE, ctypes.POINTER(BLUETOOTH_DEVICE_INFO)]
        bth.BluetoothFindDeviceClose.restype = wintypes.BOOL
        bth.BluetoothFindDeviceClose.argtypes = [wintypes.HANDLE]

        search = BLUETOOTH_DEVICE_SEARCH_PARAMS()
        search.dwSize = ctypes.sizeof(search)
        search.fReturnAuthenticated = True
        search.fReturnRemembered = True
        search.fReturnConnected = True
        search.fReturnUnknown = False
        search.fIssueInquiry = False
        search.hRadio = None

        info = BLUETOOTH_DEVICE_INFO()
        info.dwSize = ctypes.sizeof(info)

        hFind = bth.BluetoothFindFirstDevice(ctypes.byref(search), ctypes.byref(info))
        if hFind:
            while True:
                if info.fConnected:
                    mac_bytes = info.Address.ullLong.to_bytes(8, 'little')[:6]
                    connected.add(mac_bytes[::-1].hex().lower())
                if not bth.BluetoothFindNextDevice(hFind, ctypes.byref(info)):
                    break
            bth.BluetoothFindDeviceClose(hFind)
    except Exception as e:
        print(f"[-] get_connected_bluetooth_macs error: {e}")
    return connected


def get_device_transport_types() -> Dict[str, str]:
    """Determines BR/EDR vs LE transport type for each device by checking PnP enum entries."""
    transports = {}
    base_enum = r'SYSTEM\CurrentControlSet\Enum'
    for bus, tname in [(r'BTHENUM', 'BR/EDR'), (r'BTHLE', 'LE')]:
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f'{base_enum}\\{bus}', 0, winreg.KEY_READ)
            num_sub = winreg.QueryInfoKey(k)[0]
            for i in range(num_sub):
                sub = winreg.EnumKey(k, i)
                subk = winreg.OpenKey(k, sub, 0, winreg.KEY_READ)
                for j in range(winreg.QueryInfoKey(subk)[0]):
                    inst = winreg.EnumKey(subk, j)
                    full_str = (sub + '_' + inst).lower()
                    for part in full_str.split('&'):
                        for piece in part.split('_'):
                            if len(piece) == 12 and all(c in '0123456789abcdef' for c in piece):
                                if piece in transports and transports[piece] != tname:
                                    transports[piece] = 'Dual mode'
                                else:
                                    transports[piece] = tname
                winreg.CloseKey(subk)
            winreg.CloseKey(k)
        except Exception:
            pass
    return transports


class BluetoothDevice:
    def __init__(self, mac: str, name: str, cod: int = 0, is_connected: bool = False, transport_type: str = "BR/EDR"):
        self.mac = normalize_mac(mac)
        self.mac_formatted = format_mac(self.mac)
        self.mac_colon_lower = ":".join(self.mac[i:i+2] for i in range(0, 12, 2))
        self.name = name or self.mac_formatted
        self.cod = cod
        self.is_connected = is_connected
        self.transport_type = transport_type
        self.category = self._determine_category()
        self.params: Dict[str, Any] = {}

    def _determine_category(self) -> str:
        """
        Categorizes device into:
        - 'audio': Headphones, Earbuds, TWS, Headset, Speaker
        - 'phone': Smartphone, Tablet (A2DP Audio Source)
        - 'peripheral': Keyboard, Mouse, Controller, other HID
        """
        name_l = self.name.lower()
        
        # 1. Non-audio peripherals check
        if any(w in name_l for w in ["mouse", "kb", "keyboard", "controller", "sc650", "aula", "m71", "x3-5.2", "xbox", "gamepad"]):
            return "peripheral"
        if (self.cod & 0x002000) or ((self.cod >> 8) & 0x1F) == 0x05:  # Peripheral CoD
            return "peripheral"

        # 2. Phone check
        if any(w in name_l for w in ["phone", "redmi", "galaxy", "iphone", "pixel", "xiaomi"]):
            return "phone"
        if ((self.cod >> 8) & 0x1F) == 0x02:  # Phone CoD
            return "phone"

        # 3. Audio check (Headphones / Earbuds / Speaker)
        if any(w in name_l for w in ["edifier", "w820", "x2", "hitune", "tribit", "headphone", "earbuds", "buds", "speaker", "tws", "max5", "sound"]):
            return "audio"
        if ((self.cod >> 8) & 0x1F) == 0x04:  # Audio/Video CoD
            return "audio"

        return "peripheral"

    def refresh_params(self):
        self.params = RegistryManager.get_device_params(self.mac)

    def get_actual_codecs(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Returns the codec support and active selected codec for this device.
        Retrieved dynamically from CodecStorage (external database) and live Windows audio endpoint inspection.
        No device names or hardware profiles are hardcoded in source code.
        """
        from .codec_storage import CodecStorage
        return CodecStorage.get_device_codecs(self.mac, self.is_connected, force_refresh=force_refresh)


class DeviceManager:
    """
    Discovers paired Bluetooth devices from the Windows Bluetooth stack,
    correlates real-time connection status, and classifies devices.
    """

    @staticmethod
    def get_paired_devices() -> List[BluetoothDevice]:
        devices_dict: Dict[str, BluetoothDevice] = {}
        connected_macs = get_connected_bluetooth_macs()
        transport_map = get_device_transport_types()

        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REG_BTHPORT_DEVICES, 0, winreg.KEY_READ)
            num_subkeys = winreg.QueryInfoKey(k)[0]
            for i in range(num_subkeys):
                mac = winreg.EnumKey(k, i)
                if len(mac) != 12:
                    continue
                try:
                    sk = winreg.OpenKey(k, mac, 0, winreg.KEY_READ)
                    raw_name, _ = winreg.QueryValueEx(sk, "Name")
                    if isinstance(raw_name, (bytes, bytearray)):
                        name = bytes(raw_name).decode("utf-8", errors="ignore").rstrip("\x00")
                    else:
                        name = str(raw_name).rstrip("\x00")

                    cod = 0
                    try:
                        cod, _ = winreg.QueryValueEx(sk, "COD")
                    except Exception:
                        pass
                    winreg.CloseKey(sk)

                    mac_norm = mac.lower()
                    is_connected = (mac_norm in connected_macs)
                    trans = transport_map.get(mac_norm, "BR/EDR")

                    dev = BluetoothDevice(
                        mac=mac_norm,
                        name=name,
                        cod=cod,
                        is_connected=is_connected,
                        transport_type=trans
                    )
                    dev.refresh_params()
                    devices_dict[dev.mac] = dev
                except Exception as e:
                    print(f"[-] Error reading device {mac}: {e}")
            winreg.CloseKey(k)
        except Exception as e:
            print(f"[-] Error opening BTHPORT\\Parameters\\Devices: {e}")

        # Add configured devices that may not be in BTHPORT
        configured_macs = RegistryManager.get_configured_devices()
        for mac in configured_macs:
            if mac not in devices_dict:
                trans = transport_map.get(mac, "BR/EDR")
                dev = BluetoothDevice(
                    mac=mac,
                    name=f"Bluetooth Device ({format_mac(mac)})",
                    is_connected=(mac in connected_macs),
                    transport_type=trans
                )
                dev.refresh_params()
                devices_dict[mac] = dev

        # Sort: alphabetical by name, matching the original UI order!
        result = list(devices_dict.values())
        result.sort(key=lambda d: d.name.lower())
        return result
