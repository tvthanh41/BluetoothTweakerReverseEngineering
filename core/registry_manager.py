import winreg
import datetime
import ctypes
from typing import Dict, Any, Optional

# Primary Driver Parameter Storage
REG_DRIVER_BASE = r"SYSTEM\CurrentControlSet\Services\BtTweakerFltr\Parameters\UserParams"
# Software Mirror Storage (synchronized by BtTweakerSvc)
REG_SOFTWARE_BASE = r"SOFTWARE\Luculent Systems\Bluetooth Tweaker\UserParams"


def is_admin() -> bool:
    """Checks whether the current process is running with Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def normalize_mac(mac: str) -> str:
    """Formats any MAC string into 12-character lowercase hex (e.g. '0C:AE:BD:7C:16:7A' -> '0caebd7c167a')."""
    return mac.replace(":", "").replace("-", "").replace(" ", "").lower()


def format_mac(mac_hex: str) -> str:
    """Formats 12-char hex string into colon-separated uppercase MAC (e.g. '0caebd7c167a' -> '0C:AE:BD:7C:16:7A')."""
    m = normalize_mac(mac_hex)
    if len(m) == 12:
        return ":".join(m[i:i+2].upper() for i in range(0, 12, 2))
    return mac_hex.upper()


def get_current_filetime() -> int:
    """Returns current Windows FILETIME (100-nanosecond intervals since January 1, 1601 UTC)."""
    epoch_diff = 11644473600  # seconds between 1601 and 1970
    now_utc = datetime.datetime.now(datetime.timezone.utc).timestamp()
    return int((now_utc + epoch_diff) * 10000000)


class RegistryManager:
    """
    Direct interface to Windows Registry for Bluetooth Tweaker Kernel Filter driver parameters.
    Bypasses official GUI and licensing checks entirely.
    """

    @staticmethod
    def get_configured_devices() -> list:
        """Returns list of MAC addresses (12-char hex) that have custom parameters set in UserParams."""
        macs = set()
        for sub_feature in ["DisableHardwareVolume", "MicMute", "CodecInfo", "AvrcpProxy", "A2dpSink"]:
            try:
                path = f"{REG_DRIVER_BASE}\\{sub_feature}"
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ)
                num_subkeys = winreg.QueryInfoKey(key)[0]
                for i in range(num_subkeys):
                    sk = winreg.EnumKey(key, i)
                    if len(sk) == 12:
                        macs.add(sk.lower())
                winreg.CloseKey(key)
            except Exception:
                pass
        return sorted(list(macs))

    @staticmethod
    def get_device_params(mac_address: str) -> Dict[str, Any]:
        """Reads all configuration settings for a given MAC address."""
        mac = normalize_mac(mac_address)
        params = {
            "mac": mac,
            "mac_formatted": format_mac(mac),
            "disable_hardware_volume": False,
            "mic_mute": False,
            "codec_current": 1,
            "codec_next": 1,
            "avrcp_proxy": False,
            "a2dp_sink": False,
            "a2dp_sink_data": None
        }

        # 1. DisableHardwareVolume
        try:
            path = f"{REG_DRIVER_BASE}\\DisableHardwareVolume\\{mac}"
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(k, "Next")
            params["disable_hardware_volume"] = (val == 1)
            winreg.CloseKey(k)
        except Exception:
            pass

        # 2. MicMute
        try:
            path = f"{REG_DRIVER_BASE}\\MicMute\\{mac}"
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(k, "Current")
            params["mic_mute"] = (val == 1)
            winreg.CloseKey(k)
        except Exception:
            pass

        # 3. CodecInfo
        try:
            path = f"{REG_DRIVER_BASE}\\CodecInfo\\{mac}"
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ)
            try:
                params["codec_next"], _ = winreg.QueryValueEx(k, "Next")
            except Exception:
                pass
            try:
                params["codec_current"], _ = winreg.QueryValueEx(k, "Current")
            except Exception:
                pass
            winreg.CloseKey(k)
        except Exception:
            pass

        # 4. AvrcpProxy
        try:
            path = f"{REG_DRIVER_BASE}\\AvrcpProxy\\{mac}"
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(k, "Next")
            params["avrcp_proxy"] = (val == 1)
            winreg.CloseKey(k)
        except Exception:
            pass

        # 5. A2dpSink
        try:
            path = f"{REG_DRIVER_BASE}\\A2dpSink\\{mac}"
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ)
            try:
                val, _ = winreg.QueryValueEx(k, "Next")
                params["a2dp_sink"] = (val == 1)
            except Exception:
                pass
            try:
                data_bytes, _ = winreg.QueryValueEx(k, "Data")
                params["a2dp_sink_data"] = bytes(data_bytes)
            except Exception:
                pass
            winreg.CloseKey(k)
        except Exception:
            pass

        return params

    @staticmethod
    def set_hardware_volume_override(mac_address: str, disable_hw_volume: bool) -> bool:
        """
        Enables or disables hardware volume control for a specific Bluetooth headset.
        disable_hw_volume = True: Forces Windows to perform digital software PCM scaling.
        """
        mac = normalize_mac(mac_address)
        val = 1 if disable_hw_volume else 0
        ft = get_current_filetime()

        for base in [REG_DRIVER_BASE, REG_SOFTWARE_BASE]:
            try:
                sub_path = f"{base}\\DisableHardwareVolume\\{mac}"
                key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, sub_path, 0, winreg.KEY_WRITE)
                winreg.SetValueEx(key, "Next", 0, winreg.REG_DWORD, val)
                winreg.SetValueEx(key, "Updated", 0, winreg.REG_QWORD, ft)
                winreg.CloseKey(key)
            except Exception as e:
                print(f"[-] set_hardware_volume_override({base}) error: {e}")
                if base == REG_DRIVER_BASE:
                    return False
        return True

    @staticmethod
    def set_mic_mute(mac_address: str, mute: bool) -> bool:
        """Mutes or unmutes the headset microphone stream at the kernel filter level."""
        mac = normalize_mac(mac_address)
        val = 1 if mute else 0

        for base in [REG_DRIVER_BASE, REG_SOFTWARE_BASE]:
            try:
                sub_path = f"{base}\\MicMute\\{mac}"
                key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, sub_path, 0, winreg.KEY_WRITE)
                winreg.SetValueEx(key, "Current", 0, winreg.REG_DWORD, val)
                winreg.CloseKey(key)
            except Exception as e:
                print(f"[-] set_mic_mute({base}) error: {e}")
                if base == REG_DRIVER_BASE:
                    return False
        return True

    @staticmethod
    def set_a2dp_sink(mac_address: str, enable: bool) -> bool:
        """Enables or disables the PC Speaker (A2DP Sink) role for this device."""
        mac = normalize_mac(mac_address)
        val = 1 if enable else 0

        try:
            sub_path = f"{REG_DRIVER_BASE}\\A2dpSink\\{mac}"
            key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, sub_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "Next", 0, winreg.REG_DWORD, val)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"[-] set_a2dp_sink error: {e}")
            return False

    @staticmethod
    def set_avrcp_proxy(mac_address: str, enable: bool) -> bool:
        """Enables or disables AVRCP proxy routing for legacy desktop media players."""
        mac = normalize_mac(mac_address)
        val = 1 if enable else 0

        try:
            sub_path = f"{REG_DRIVER_BASE}\\AvrcpProxy\\{mac}"
            key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, sub_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "Next", 0, winreg.REG_DWORD, val)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"[-] set_avrcp_proxy error: {e}")
            return False

    @staticmethod
    def set_desired_codec(mac_address: str, codec_index: int) -> bool:
        """Writes the desired Next codec mode into CodecInfo."""
        mac = normalize_mac(mac_address)
        ft = get_current_filetime()

        try:
            sub_path = f"{REG_DRIVER_BASE}\\CodecInfo\\{mac}"
            key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, sub_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "Next", 0, winreg.REG_DWORD, codec_index)
            winreg.SetValueEx(key, "Updated", 0, winreg.REG_QWORD, ft)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"[-] set_desired_codec error: {e}")
            return False
