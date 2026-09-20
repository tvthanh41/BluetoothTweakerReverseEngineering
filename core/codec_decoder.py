import struct
from typing import Dict, Any, List, Optional


class CodecDecoder:
    """
    Decodes Bluetooth AVDTP Media Codec Capability records (Category 0x07)
    and formats human-readable technical capabilities.
    """

    VENDOR_NAMES = {
        0x0000004f: "CSR (Qualcomm)",
        0x000000d7: "Qualcomm Technologies International",
        0x0000000a: "Qualcomm / CSR",
        0x0000012d: "Sony Corporation",
        0x0000053a: "Savitech Corp.",
        0x00000075: "Samsung Electronics",
        0x000008a9: "Fraunhofer IIS",
        0x000000e0: "Google LLC",
        0x0000000a: "Apple Inc."
    }

    @staticmethod
    def decode_avdtp_capability(raw_bytes: bytes) -> Dict[str, Any]:
        """
        Parses raw AVDTP capability frame and returns structured codec details.
        """
        if not raw_bytes or len(raw_bytes) < 4:
            return {
                "codec_name": "Unknown",
                "codec_type": "None",
                "raw_hex": raw_bytes.hex() if raw_bytes else "",
                "description": "No data",
                "sample_rates": [],
                "channel_modes": [],
                "details": {}
            }

        data = raw_bytes
        # If payload starts with Service Category 0x07 (Media Codec)
        offset = 0
        if data[0] == 0x07 and len(data) >= 2:
            cat_len = data[1]
            offset = 2

        if len(data) <= offset + 1:
            return {"codec_name": "Invalid AVDTP", "raw_hex": data.hex(), "details": {}}

        media_type = data[offset]  # 0x00 = Audio
        codec_type = data[offset + 1]  # Codec Type
        body = data[offset + 2:]

        result = {
            "media_type": "Audio" if media_type == 0 else f"Type {media_type}",
            "codec_type_id": codec_type,
            "raw_hex": data.hex().upper(),
            "sample_rates": [],
            "channel_modes": [],
            "details": {}
        }

        # 1. SBC Codec (0x00)
        if codec_type == 0x00 and len(body) >= 4:
            result["codec_name"] = "SBC (Subband Codec)"
            result["codec_category"] = "Standard Bluetooth Audio"
            
            b0, b1, min_bp, max_bp = body[0], body[1], body[2], body[3]
            
            rates = []
            if b0 & 0x80: rates.append("16")
            if b0 & 0x40: rates.append("32")
            if b0 & 0x20: rates.append("44.1")
            if b0 & 0x10: rates.append("48")
            rates_str = ("/".join(rates) + "kHz") if rates else "N/A"
            result["sample_rates"] = [f"{r} kHz" for r in rates]

            modes = []
            if b0 & 0x08: modes.append("Mono")
            if b0 & 0x04: modes.append("Dual Channel")
            if b0 & 0x02: modes.append("Stereo")
            if b0 & 0x01: modes.append("Joint Stereo")
            modes_str = "/".join(modes) if modes else "N/A"
            result["channel_modes"] = modes

            blocks = []
            if b1 & 0x10: blocks.append("4")
            if b1 & 0x20: blocks.append("8")
            if b1 & 0x40: blocks.append("12")
            if b1 & 0x80: blocks.append("16")
            blocks_str = "/".join(blocks) if blocks else "N/A"

            subbands = []
            if b1 & 0x04: subbands.append("4")
            if b1 & 0x08: subbands.append("8")
            subbands_str = "/".join(subbands) if subbands else "N/A"

            alloc = []
            if b1 & 0x02: alloc.append("SNR")
            if b1 & 0x01: alloc.append("Loudness")
            alloc_str = "/".join(alloc) if alloc else "N/A"

            formatted = (
                f"CODEC Type: SBC, Sampling Frequency: {rates_str}, "
                f"Channel Mode: {modes_str}, Block Length: {blocks_str}, "
                f"Subbands: {subbands_str}, Allocation Method: {alloc_str}, "
                f"Min/Max Bitpool: {min_bp}/{max_bp}"
            )
            result["formatted_text"] = formatted

            result["details"] = {
                "Bitpool Range": f"{min_bp} - {max_bp}",
                "Block Length": blocks_str,
                "Subbands": subbands_str,
                "Allocation": alloc_str,
                "Max Bitrate (Est.)": f"~{int(max_bp * 6.5)} kbps"
            }
            return result

        # 2. MPEG-2, 4 AAC (0x02)
        elif codec_type == 0x02 and len(body) >= 6:
            result["codec_name"] = "MPEG-2, 4 AAC"
            result["codec_category"] = "Advanced Audio Coding"

            obj_type, freq_hi, freq_lo_ch, b_rate0, b_rate1, b_rate2 = body[0:6]
            
            objs = []
            if obj_type & 0x80: objs.append("MPEG-2 AAC LC")
            if obj_type & 0x40: objs.append("MPEG-4 AAC LC")
            if obj_type & 0x20: objs.append("MPEG-4 AAC LTP")
            if obj_type & 0x10: objs.append("MPEG-4 AAC scalable")
            objs_str = "/".join(objs) if objs else "MPEG-4 AAC LC"

            rates = []
            if freq_hi & 0x80: rates.append("8")
            if freq_hi & 0x40: rates.append("11.025")
            if freq_hi & 0x20: rates.append("12")
            if freq_hi & 0x10: rates.append("16")
            if freq_hi & 0x08: rates.append("22.05")
            if freq_hi & 0x04: rates.append("24")
            if freq_hi & 0x02: rates.append("32")
            if freq_hi & 0x01: rates.append("44.1")
            if freq_lo_ch & 0x80: rates.append("48")
            if freq_lo_ch & 0x40: rates.append("64")
            if freq_lo_ch & 0x20: rates.append("88.2")
            if freq_lo_ch & 0x10: rates.append("96")
            rates_str = ("/".join(rates) + "kHz") if rates else "44.1/48kHz"
            result["sample_rates"] = [f"{r} kHz" for r in rates]

            chans = []
            if freq_lo_ch & 0x08: chans.append("1")
            if freq_lo_ch & 0x04: chans.append("2")
            chans_str = "/".join(chans) if chans else "1/2"
            result["channel_modes"] = [f"{c} Channel" for c in chans]

            vbr = bool(b_rate0 & 0x80)
            bitrate = ((b_rate0 & 0x7F) << 16) | (b_rate1 << 8) | b_rate2
            vbr_str = "supported" if vbr else "not supported"
            bitrate_str = str(bitrate) if bitrate > 0 else "Variable"

            formatted = (
                f"CODEC Type: MPEG-2, 4 AAC, Object Type: {objs_str}, "
                f"Sampling Frequency: {rates_str}, Channels: {chans_str}, "
                f"VBR: {vbr_str}, Bit rate: {bitrate_str}"
            )
            result["formatted_text"] = formatted

            result["details"] = {
                "Object Types": ", ".join(objs) if objs else "AAC LC",
                "VBR Supported": "Yes" if vbr else "No (CBR)",
                "Bitrate": f"{bitrate} bps ({bitrate // 1000} kbps)" if bitrate > 0 else "Variable (Auto)"
            }
            return result

        # 3. Vendor Specific Codecs (0xFF)
        elif codec_type == 0xFF and len(body) >= 6:
            vendor_id = struct.unpack("<I", body[0:4])[0]
            codec_id = struct.unpack("<H", body[4:6])[0]
            vendor_data = body[6:]
            vendor_name = CodecDecoder.VENDOR_NAMES.get(vendor_id, f"Vendor 0x{vendor_id:08X}")

            result["details"]["Vendor"] = vendor_name
            result["details"]["Vendor ID"] = f"0x{vendor_id:08X}"
            result["details"]["Codec ID"] = f"0x{codec_id:04X}"

            # aptX (Vendor 0x4f, Codec 0x0001)
            if vendor_id in [0x0000004f, 0x0000000a] and codec_id == 0x0001:
                result["codec_name"] = "Qualcomm aptX"
                result["codec_category"] = "Hi-Res Audio"
                rates = []
                if len(vendor_data) >= 1:
                    b = vendor_data[0]
                    if b & 0x80: rates.append("16")
                    if b & 0x40: rates.append("32")
                    if b & 0x20: rates.append("44.1")
                    if b & 0x10: rates.append("48")
                    modes = []
                    if b & 0x02: modes.append("Stereo")
                    if b & 0x01: modes.append("Dual Channel")
                    result["channel_modes"] = modes
                rates_str = ("/".join(rates) + "kHz") if rates else "44.1/48kHz"
                modes_str = "/".join(modes) if modes else "Stereo/Dual Channel"
                result["sample_rates"] = [f"{r} kHz" for r in (rates or ["44.1", "48"])]
                result["formatted_text"] = f"CODEC Type: aptX, Sampling Frequency: {rates_str}, Channel Mode: {modes_str}"
                result["details"]["Bit Depth"] = "16-bit"
                result["details"]["Compression"] = "ADPCM 4:1 (352 / 384 kbps)"
                return result

            # aptX HD (Vendor 0xd7, Codec 0x0024)
            elif vendor_id == 0x000000d7 and codec_id == 0x0024:
                result["codec_name"] = "Qualcomm aptX HD"
                result["codec_category"] = "High-Definition 24-bit Audio"
                result["sample_rates"] = ["44.1 kHz", "48 kHz"]
                result["channel_modes"] = ["Stereo"]
                result["formatted_text"] = "CODEC Type: aptX-HD, Sampling Frequency: 44.1/48kHz, Channel Mode: Stereo"
                result["details"]["Bit Depth"] = "24-bit Hi-Res"
                result["details"]["Bitrate"] = "576 kbps"
                result["details"]["Compression"] = "ADPCM 4:1"
                return result

            # aptX Low Latency / FastStream
            elif vendor_id == 0x0000000a and codec_id in [0x0001, 0x0002]:
                name = "aptX Low Latency" if codec_id == 0x0002 else "FastStream"
                result["codec_name"] = name
                result["codec_category"] = "Ultra-Low Latency Audio"
                result["sample_rates"] = ["44.1 kHz", "48 kHz"]
                result["channel_modes"] = ["Stereo + Voice Return Channel"]
                result["formatted_text"] = f"CODEC Type: {name}, Sampling Frequency: 44.1/48kHz, Channel Mode: Stereo"
                result["details"]["Latency"] = "< 40 ms"
                return result

            # aptX Adaptive
            elif vendor_id == 0x000000d7 and codec_id in [0x00ad, 0x00a7]:
                result["codec_name"] = "Qualcomm aptX Adaptive"
                result["codec_category"] = "Dynamic Bitrate & Latency"
                result["sample_rates"] = ["44.1 kHz", "48 kHz", "96 kHz"]
                result["channel_modes"] = ["Stereo"]
                result["formatted_text"] = "CODEC Type: aptX Adaptive, Sampling Frequency: 44.1/48/96kHz, Channel Mode: Stereo"
                result["details"]["Bit Depth"] = "24-bit"
                result["details"]["Bitrate Range"] = "279 kbps - 420 kbps (Dynamic)"
                return result

            # Sony LDAC (Vendor 0x12d, Codec 0x00aa)
            elif vendor_id == 0x0000012d and codec_id == 0x00AA:
                result["codec_name"] = "Sony LDAC"
                result["codec_category"] = "Hi-Res Audio Wireless Certified"
                result["sample_rates"] = ["44.1 kHz", "48 kHz", "88.2 kHz", "96 kHz"]
                result["channel_modes"] = ["Stereo", "Dual", "Mono"]
                result["formatted_text"] = "CODEC Type: LDAC, Sampling Frequency: 44.1/48/88.2/96kHz, Channel Mode: Stereo/Dual/Mono"
                result["details"]["Bit Depth"] = "Up to 24-bit / 96 kHz"
                result["details"]["Bitrates"] = "330 / 660 / 990 kbps"
                return result

            # Savitech LHDC (Vendor 0x53a)
            elif vendor_id == 0x0000053a:
                v5 = (codec_id == 0x4c35)
                result["codec_name"] = "Savitech LHDC V5" if v5 else "Savitech LHDC"
                result["codec_category"] = "Low Latency High-Definition Audio Codec"
                result["sample_rates"] = ["44.1 kHz", "48 kHz", "96 kHz", "192 kHz"] if v5 else ["48 kHz", "96 kHz"]
                result["channel_modes"] = ["Stereo"]
                result["details"]["Bit Depth"] = "24-bit"
                result["details"]["Bitrates"] = "400 / 500 / 900 / 1000 kbps"
                return result

            # Samsung Scalable Codec / Samsung HD (Vendor 0x75)
            elif vendor_id == 0x00000075:
                result["codec_name"] = "Samsung Scalable CODEC" if codec_id == 0x0103 else "Samsung HD"
                result["codec_category"] = "Samsung Proprietary Dynamic Audio"
                result["sample_rates"] = ["44.1 kHz", "48 kHz"]
                result["channel_modes"] = ["Stereo"]
                result["details"]["Dynamic Bitrate"] = "88 kbps - 512 kbps"
                return result

            # Fraunhofer LC3plus (Vendor 0x8a9, Codec 0x0001)
            elif vendor_id == 0x000008a9:
                result["codec_name"] = "Fraunhofer LC3plus"
                result["codec_category"] = "High-Resolution Next-Gen Codec"
                result["sample_rates"] = ["48 kHz", "96 kHz"]
                result["channel_modes"] = ["Stereo"]
                result["details"]["Bit Depth"] = "24-bit / 32-bit"
                return result

            # Google Opus (Vendor 0xe0, Codec 0x0001)
            elif vendor_id == 0x000000e0:
                result["codec_name"] = "Google Opus"
                result["codec_category"] = "Interactive Audio & Speech"
                result["sample_rates"] = ["48 kHz"]
                result["channel_modes"] = ["Stereo"]
                return result

            # Other vendor codec
            result["codec_name"] = f"Vendor Specific ({vendor_name})"
            result["codec_category"] = "Proprietary Codec"
            return result

        # Fallback
        result["codec_name"] = f"CODEC (Type 0x{codec_type:02X})"
        result["codec_category"] = "Custom Audio Stream"
        return result

    @staticmethod
    def get_supported_codecs_list(a2dp_data: Optional[bytes] = None) -> List[Dict[str, Any]]:
        """
        Extracts all supported codecs from raw A2dpSink data if present,
        or returns default standard list supported by typical modern headphones.
        """
        codecs = []
        if a2dp_data and len(a2dp_data) > 4:
            # Parse multiple capability frames if concatenated
            offset = 0
            while offset < len(a2dp_data):
                if a2dp_data[offset] == 0x07 and offset + 1 < len(a2dp_data):
                    length = a2dp_data[offset + 1]
                    frame = a2dp_data[offset:offset + 2 + length]
                    decoded = CodecDecoder.decode_avdtp_capability(frame)
                    codecs.append(decoded)
                    offset += 2 + length
                else:
                    break
        return codecs

