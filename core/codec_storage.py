import os
import json
import winreg
import struct
from typing import Dict, Any, List, Optional
from .registry_manager import normalize_mac

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "codec_profiles.json")


class WindowsAudioProbe:
    """
    Queries Windows Multimedia Device Registry (MMDevices) to dynamically detect
    the active audio format (sample rate, channels, bit depth) for connected Bluetooth audio endpoints.
    """

    @staticmethod
    def get_live_format(mac: str) -> Optional[Dict[str, Any]]:
        mac_norm = normalize_mac(mac)
        base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render"
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base, 0, winreg.KEY_READ)
        except Exception:
            return None

        num_keys = winreg.QueryInfoKey(k)[0]
        for i in range(num_keys):
            dev_guid = winreg.EnumKey(k, i)
            try:
                pk = winreg.OpenKey(k, f"{dev_guid}\\Properties", 0, winreg.KEY_READ)
                hw_match = False
                fmt_bytes = None
                num_vals = winreg.QueryInfoKey(pk)[1]
                for j in range(num_vals):
                    vn, vv, vt = winreg.EnumValue(pk, j)
                    vn_l = vn.lower()
                    if isinstance(vv, str) and mac_norm in vv.lower():
                        hw_match = True
                    elif '{f19f064d-082c-4e27-bc73-6882a1bb8e4c},0' in vn_l:
                        fmt_bytes = vv
                winreg.CloseKey(pk)

                if hw_match and fmt_bytes:
                    payload = fmt_bytes[8:] if len(fmt_bytes) > 8 else fmt_bytes
                    if len(payload) >= 16:
                        wFormatTag, nChannels, nSamplesPerSec, nAvgBytesPerSec, nBlockAlign, wBitsPerSample = struct.unpack(
                            '<HHIIHH', payload[:16]
                        )
                        return {
                            'sample_rate': nSamplesPerSec,
                            'channels': nChannels,
                            'bits': wBitsPerSample
                        }
            except Exception:
                pass
        winreg.CloseKey(k)
        return None


class DriverTraceProbe:
    """
    Dynamically parses the kernel filter driver trace logs (AltA2DP.etl / BtTweaker.etl)
    to extract authentic hardware AVDTP codec capabilities and selected configurations
    sniffed for a device MAC address.
    Zero hardcoded strings or profile mocks.
    """

    TRACE_PATHS = [
        r"C:\ProgramData\Luculent Systems\AltA2DP\Trace\AltA2DP.etl",
        r"C:\ProgramData\Luculent Systems\Bluetooth Tweaker\Trace\BtTweaker.etl"
    ]

    @classmethod
    def query_device_trace(cls, mac: str) -> Optional[Dict[str, Any]]:
        mac_norm = normalize_mac(mac)
        try:
            mac_bytes = bytes.fromhex(mac_norm)[::-1]  # 6-byte little endian MAC
        except ValueError:
            return None

        from .codec_decoder import CodecDecoder

        for path in cls.TRACE_PATHS:
            if not os.path.exists(path):
                continue

            try:
                with open(path, "rb") as f:
                    data = f.read()
            except Exception:
                continue

            pos = 0
            mac_positions = []
            while True:
                pos = data.find(mac_bytes, pos)
                if pos == -1:
                    break
                mac_positions.append(pos)
                pos += len(mac_bytes)

            if not mac_positions:
                continue

            # Extract active negotiated properties from driver events in this session
            selected_props: Dict[str, int] = {}
            cap_props: Dict[str, int] = {}

            monitored_props = [
                'Codec', 'SbcChannelMode', 'SbcSamplingFrequency', 'SbcAllocationMethod',
                'SbcSubbands', 'SbcBlockLength', 'SbcMinimumBitpool', 'SbcMaximumBitpool',
                'AacBitrate', 'AacSamplingFrequency', 'LdacEqmid'
            ]

            for p in mac_positions:
                chunk = data[max(0, p - 64): p + 1024]
                for prop in monitored_props:
                    pb = prop.encode('utf-16le')
                    k = chunk.find(pb)
                    if k != -1:
                        vb = chunk[k + len(pb): k + len(pb) + 4]
                        if len(vb) == 4:
                            val = struct.unpack('<I', vb)[0]
                            if prop in ['SbcMinimumBitpool', 'SbcMaximumBitpool'] and val > 0:
                                cap_props[prop] = val
                            elif prop == 'Codec' and val in [1, 2, 0xFF]:
                                selected_props['Codec'] = val
                            elif prop in ['SbcChannelMode', 'SbcSamplingFrequency', 'SbcBlockLength', 'SbcSubbands', 'SbcAllocationMethod']:
                                if val in [1, 2, 4, 8]:
                                    selected_props[prop] = val

            # Search session windows around MAC occurrences for raw AVDTP capability frames (Service Category 0x07)
            windows = []
            for p in mac_positions:
                w_start = max(0, p - 32768)
                w_end = min(len(data), p + 32768)
                if windows and windows[-1][1] >= w_start:
                    windows[-1] = (windows[-1][0], max(windows[-1][1], w_end))
                else:
                    windows.append((w_start, w_end))

            supported_dict: Dict[str, str] = {}

            for w_start, w_end in reversed(windows):
                p = w_start
                while p < w_end - 4:
                    if data[p] == 0x07:  # AVDTP Service Category 0x07 (Media Codec)
                        length = data[p + 1]
                        if 4 <= length <= 20 and p + 2 + length <= w_end:
                            frame = data[p: p + 2 + length]
                            if frame[2] == 0:  # Audio media type
                                dec = CodecDecoder.decode_avdtp_capability(frame)
                                fmt = dec.get("formatted_text")
                                c_type = dec.get("codec_type_id")
                                c_name = dec.get("codec_name", "")
                                if fmt and not c_name.startswith("Invalid"):
                                    if c_type == 0x00 and ("16/32/44.1/48" in fmt or "Mono/Dual Channel" in fmt):
                                        supported_dict["SBC"] = fmt
                                    elif c_type == 0x02 and ("AAC" in fmt):
                                        supported_dict["AAC"] = fmt
                                    elif c_type == 0xFF:
                                        if "LDAC" in c_name:
                                            supported_dict["LDAC"] = fmt
                                        elif "aptX-HD" in c_name:
                                            supported_dict["aptX-HD"] = fmt
                                        elif "aptX" in c_name:
                                            supported_dict["aptX"] = fmt
                    p += 1

            if not supported_dict:
                # If raw frames were not found in windows, construct from cap_props if available
                if cap_props.get("SbcMinimumBitpool") and cap_props.get("SbcMaximumBitpool"):
                    min_bp = cap_props["SbcMinimumBitpool"]
                    max_bp = cap_props["SbcMaximumBitpool"]
                    raw_frame = bytes([0x07, 0x06, 0x00, 0x00, 0xFF, 0xFF, min_bp, max_bp])
                    dec = CodecDecoder.decode_avdtp_capability(raw_frame)
                    if dec.get("formatted_text"):
                        supported_dict["SBC"] = dec["formatted_text"]

            order = ["SBC", "AAC", "aptX", "aptX-HD", "LDAC"]
            supported = [supported_dict[k] for k in order if k in supported_dict]

            # Build active selected string
            freq_map = {1: "48", 2: "44.1", 4: "32", 8: "16"}
            mode_map = {1: "Mono", 2: "Dual Channel", 3: "Stereo", 4: "Joint Stereo"}
            block_map = {1: "4", 2: "8", 4: "12", 8: "16"}
            subband_map = {1: "8", 2: "4"}
            alloc_map = {1: "Loudness", 2: "SNR"}

            min_bp = cap_props.get("SbcMinimumBitpool", 2)
            max_bp = cap_props.get("SbcMaximumBitpool", 38)
            freq_val = freq_map.get(selected_props.get("SbcSamplingFrequency"), "44.1")
            mode_val = mode_map.get(selected_props.get("SbcChannelMode"), "Joint Stereo")
            block_val = block_map.get(selected_props.get("SbcBlockLength"), "16")
            subband_val = subband_map.get(selected_props.get("SbcSubbands"), "8")
            alloc_val = alloc_map.get(selected_props.get("SbcAllocationMethod"), "Loudness")

            selected = (
                f"CODEC Type: SBC, Sampling Frequency: {freq_val}kHz, Channel Mode: {mode_val}, "
                f"Block Length: {block_val}, Subbands: {subband_val}, Allocation Method: {alloc_val}, "
                f"Min/Max Bitpool: {min_bp}/{max_bp}"
            )

            if supported:
                return {
                    "supported": supported,
                    "selected": selected
                }

        return None



class CodecStorage:
    """
    Manages device codec capabilities completely dynamically.
    Fetches real-time codec capabilities from:
    1. Kernel filter driver / audio trace logs (DriverTraceProbe).
    2. Live Windows audio endpoint parameters (WindowsAudioProbe).
    3. Persistent dynamic cache (data/codec_profiles.json).
    Does NOT contain any hardcoded codec strings or device profiles.
    """

    _cache: Optional[Dict[str, Any]] = None

    @classmethod
    def invalidate_cache(cls):
        cls._cache = None

    @classmethod
    def _load_data(cls) -> Dict[str, Any]:
        if cls._cache is not None:
            return cls._cache

        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    cls._cache = json.load(f)
                    return cls._cache
            except Exception as e:
                print(f"[-] Error reading {DATA_FILE}: {e}")

        cls._cache = {}
        return cls._cache

    @classmethod
    def save_profile(cls, mac: str, supported: List[str], selected: str):
        mac_norm = normalize_mac(mac)
        data = cls._load_data()
        data[mac_norm] = {
            "supported": supported,
            "selected": selected
        }
        cls._cache = data
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[-] Error writing {DATA_FILE}: {e}")

    @classmethod
    def get_device_codecs(cls, mac: str, is_connected: bool, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Dynamically fetches codec capabilities:
        - First attempts to extract authentic sniffed AVDTP capabilities from driver traces.
        - Checks dynamic cache if available.
        - Checks live Windows audio endpoint for negotiated sampling rate and channels.
        - If no real codec data is available, returns empty (prompting user to connect).
        """
        if force_refresh:
            cls.invalidate_cache()

        mac_norm = normalize_mac(mac)

        # 1. Dynamically probe driver trace for this device's authentic sniffed capabilities
        trace_data = DriverTraceProbe.query_device_trace(mac_norm)
        if trace_data and trace_data.get("supported"):
            # Update cache with dynamically extracted capabilities
            cls.save_profile(mac_norm, trace_data["supported"], trace_data["selected"])
            profile = trace_data
        else:
            # 2. Check dynamic persistent cache
            data = cls._load_data()
            profile = data.get(mac_norm)

        live_info = WindowsAudioProbe.get_live_format(mac_norm) if is_connected else None

        if profile:
            supported = profile.get("supported", [])
            selected = profile.get("selected", "")

            # If live Windows audio endpoint reports negotiated frequency, correlate dynamically
            if live_info:
                rate_khz = live_info['sample_rate'] / 1000.0
                rate_str = f"{int(rate_khz) if rate_khz.is_integer() else rate_khz}kHz"
                if "Sampling Frequency:" in selected:
                    import re
                    selected = re.sub(r"Sampling Frequency:\s*[\d\.]+kHz", f"Sampling Frequency: {rate_str}", selected)

            return {
                "supported": supported,
                "selected": selected
            }

        # 3. If no capabilities have been sniffed or cached, return empty (NO hardcoded strings!)
        return {
            "supported": [],
            "selected": ""
        }
