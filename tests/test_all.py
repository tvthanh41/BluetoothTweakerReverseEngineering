import unittest
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from i18n import Translator, tr
from core import RegistryManager, normalize_mac, format_mac, CodecDecoder, ServiceMonitor, DeviceManager


class TestBluetoothTweaker(unittest.TestCase):

    def setUp(self):
        self.translator = Translator.get_instance()

    def test_mac_normalization(self):
        self.assertEqual(normalize_mac("0C:AE:BD:7C:16:7A"), "0caebd7c167a")
        self.assertEqual(normalize_mac("b4-e7-b3-b6-eb-e8"), "b4e7b3b6ebe8")
        self.assertEqual(format_mac("0caebd7c167a"), "0C:AE:BD:7C:16:7A")

    def test_i18n_locales(self):
        for lang in ["en", "vi", "zh", "ja"]:
            self.assertTrue(self.translator.set_locale(lang))
            title = tr("app.title")
            self.assertNotEqual(title, "app.title")
            self.assertTrue(len(title) > 0)

        # Verify key resolution across locales
        self.translator.set_locale("vi")
        self.assertIn("Âm Lượng", tr("volume_control.title"))

        self.translator.set_locale("en")
        self.assertIn("Stereo Audio", tr("volume_control.title"))
        self.assertEqual(tr("non.existent.key", default="fallback"), "fallback")

    def test_codec_decoder_sbc(self):
        payload = bytes([0x07, 0x04, 0x00, 0x00, 0x21, 0x89, 0x02, 0x35])
        res = CodecDecoder.decode_avdtp_capability(payload)
        self.assertEqual(res["codec_name"], "SBC (Subband Codec)")
        self.assertIn("44.1 kHz", res["sample_rates"])
        self.assertIn("Joint Stereo", res["channel_modes"])
        self.assertEqual(res["details"]["Bitpool Range"], "2 - 53")

    def test_codec_decoder_aptx_hd(self):
        payload = bytes([0x07, 0x0A, 0x00, 0xFF, 0xD7, 0x00, 0x00, 0x00, 0x24, 0x00, 0x12, 0x00])
        res = CodecDecoder.decode_avdtp_capability(payload)
        self.assertEqual(res["codec_name"], "Qualcomm aptX HD")
        self.assertEqual(res["details"]["Bit Depth"], "24-bit Hi-Res")
        self.assertEqual(res["details"]["Bitrate"], "576 kbps")

    def test_codec_decoder_ldac(self):
        payload = bytes([0x07, 0x0A, 0x00, 0xFF, 0x2D, 0x01, 0x00, 0x00, 0xAA, 0x00, 0x00, 0x00])
        res = CodecDecoder.decode_avdtp_capability(payload)
        self.assertEqual(res["codec_name"], "Sony LDAC")
        self.assertIn("96 kHz", res["sample_rates"])

    def test_service_monitor(self):
        status = ServiceMonitor.get_status()
        self.assertIsInstance(status, dict)
        self.assertTrue(status["service_installed"])
        self.assertTrue(status["driver_installed"])

    def test_device_discovery(self):
        devices = DeviceManager.get_paired_devices()
        self.assertGreaterEqual(len(devices), 1)
        for d in devices:
            self.assertEqual(len(d.mac), 12)
            self.assertTrue(len(d.name) > 0)
    def test_codec_exact_formatting(self):
        # Full SBC capability with all modes and bitpool 2/38
        payload = bytes([0x07, 0x06, 0x00, 0x00, 0xFF, 0xFF, 0x02, 0x26])
        res = CodecDecoder.decode_avdtp_capability(payload)
        expected = (
            "CODEC Type: SBC, Sampling Frequency: 16/32/44.1/48kHz, "
            "Channel Mode: Mono/Dual Channel/Stereo/Joint Stereo, "
            "Block Length: 4/8/12/16, Subbands: 4/8, Allocation Method: SNR/Loudness, "
            "Min/Max Bitpool: 2/38"
        )
        self.assertEqual(res["formatted_text"], expected)

    def test_edifier_x2_codec(self):
        devices = DeviceManager.get_paired_devices()
        x2_dev = next((d for d in devices if "x2" in d.name.lower() or d.mac == "b4e7b3b6ebe8"), None)
        if x2_dev:
            codecs = x2_dev.get_actual_codecs()
            # Must strictly support SBC only, NO AAC
            self.assertEqual(len(codecs["supported"]), 1)
            self.assertIn("CODEC Type: SBC", codecs["supported"][0])
            self.assertNotIn("AAC", codecs["supported"][0])
            # Check exact user-provided string matches
            expected_x2_str = (
                "CODEC Type: SBC, Sampling Frequency: 16/32/44.1/48kHz, "
                "Channel Mode: Mono/Dual Channel/Stereo/Joint Stereo, "
                "Block Length: 4/8/12/16, Subbands: 4/8, Allocation Method: SNR/Loudness, "
                "Min/Max Bitpool: 2/38"
            )
            self.assertEqual(codecs["supported"][0], expected_x2_str)
            self.assertIn("CODEC Type: SBC", codecs["selected"])
            self.assertIn("Min/Max Bitpool: 2/38", codecs["selected"])

    def test_codec_storage(self):
        from core import CodecStorage
        test_mac = "aabbccddeeff"
        test_supported = ["CODEC Type: SBC, Min/Max Bitpool: 2/53"]
        test_selected = "CODEC Type: SBC, Sampling Frequency: 48kHz"
        CodecStorage.save_profile(test_mac, test_supported, test_selected)
        retrieved = CodecStorage.get_device_codecs(test_mac, is_connected=True)
        self.assertIn("CODEC Type: SBC", retrieved["selected"])
        # Clean up test mac from cache and file
        data = CodecStorage._load_data()
        if test_mac in data:
            del data[test_mac]
            import json, os
            from core.codec_storage import DATA_FILE
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)


if __name__ == "__main__":
    unittest.main()
