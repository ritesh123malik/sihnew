import pytest
import numpy as np
from app.services.sadh_physics import (
    estimate_target_height,
    compute_physics_confidence,
    extract_sadh_from_bbox,
)
from app.services.xtf_parser import (
    create_synthetic_xtf,
    parse_xtf_bytes,
    XtfParseError,
)


class TestSadhPhysics:
    def test_height_formula(self):
        # h_est = (L * H_s) / R_s
        # L = 10m, H_s = 15m, R_s = 50m -> h_est = 150 / 50 = 3.0m
        h = estimate_target_height(shadow_length_m=10.0, altitude_m=15.0, slant_range_m=50.0)
        assert abs(h - 3.0) < 1e-3

    def test_zero_or_negative_inputs(self):
        assert estimate_target_height(0, 15.0, 50.0) == 0.0
        assert estimate_target_height(10.0, 0.0, 50.0) == 0.0
        assert estimate_target_height(10.0, 15.0, 0.0) == 0.0

    def test_physics_confidence_elevated_with_shadow(self):
        conf = compute_physics_confidence(
            class_label="shipwreck",
            detection_conf=0.85,
            estimated_height_m=2.5,
            has_shadow=True,
        )
        assert conf >= 0.80

    def test_physics_confidence_elevated_missing_shadow_penalty(self):
        conf_with_shadow = compute_physics_confidence(
            class_label="shipwreck",
            detection_conf=0.85,
            estimated_height_m=2.5,
            has_shadow=True,
        )
        conf_no_shadow = compute_physics_confidence(
            class_label="shipwreck",
            detection_conf=0.85,
            estimated_height_m=0.0,
            has_shadow=False,
        )
        assert conf_no_shadow < conf_with_shadow
        assert conf_no_shadow <= 0.55


class TestXtfParser:
    def test_synthetic_xtf_generation_and_parsing(self):
        xtf_data = create_synthetic_xtf(num_pings=32, samples_per_channel=256)
        assert len(xtf_data) >= 1024

        waterfall, meta = parse_xtf_bytes(xtf_data)
        assert waterfall.ndim == 2
        assert waterfall.shape[0] == 31 or waterfall.shape[0] == 32
        assert waterfall.shape[1] == 512  # 256 port + 256 starboard
        assert meta["num_pings"] > 0
        assert "avg_latitude" in meta
        assert "avg_longitude" in meta
        assert "avg_heading_deg" in meta

    def test_corrupt_xtf_rejected(self):
        bad_xtf = b"FAKE_XTF_HEADER" + b"\x00" * 1024
        with pytest.raises(XtfParseError):
            parse_xtf_bytes(bad_xtf)

    def test_noaa_geoswath_16bit_xtf_parsing(self, tmp_path):
        """Test parsing of 16-bit interferometric sidescan sonar XTF files (NOAA Hudson River / GeoSwath spec)."""
        import struct
        import io
        from app.services.xtf_parser import parse_xtf_file

        samples_per_chan = 128
        bytes_per_sample = 2
        pkt_len = 256 + 128 + (samples_per_chan * bytes_per_sample * 2)

        buf = io.BytesIO()
        hdr = bytearray(1024)
        hdr[0] = 0x7B
        hdr[1] = 1
        hdr[2:10] = b"HSX2Xtf "
        hdr[18:34] = b"GeoAcoustics    "
        struct.pack_into("<H", hdr, 142, 2)
        buf.write(hdr)

        for i in range(16):
            pkt_hdr = bytearray(256)
            struct.pack_into("<H", pkt_hdr, 0, 0xFACE)
            struct.pack_into("<I", pkt_hdr, 4, pkt_len)
            struct.pack_into("<H", pkt_hdr, 8, 2009)
            struct.pack_into("<I", pkt_hdr, 16, i + 1)
            struct.pack_into("<d", pkt_hdr, 80, 42.15)  # Hudson River latitude
            struct.pack_into("<d", pkt_hdr, 88, -73.85) # Hudson River longitude

            c0_hdr = bytearray(64)
            struct.pack_into("<I", c0_hdr, 36, samples_per_chan)
            c1_hdr = bytearray(64)
            struct.pack_into("<I", c1_hdr, 36, samples_per_chan)

            p_16 = np.random.randint(5000, 30000, size=samples_per_chan, dtype=np.uint16)
            s_16 = np.random.randint(5000, 30000, size=samples_per_chan, dtype=np.uint16)

            buf.write(pkt_hdr)
            buf.write(c0_hdr)
            buf.write(c1_hdr)
            buf.write(p_16.tobytes())
            buf.write(s_16.tobytes())

        xtf_path = tmp_path / "hudson_river_16bit.xtf"
        xtf_path.write_bytes(buf.getvalue())

        waterfall, meta = parse_xtf_file(str(xtf_path))
        assert waterfall.ndim == 2
        assert waterfall.dtype == np.uint8
        assert waterfall.shape[0] == 16
        assert waterfall.shape[1] == samples_per_chan * 2
        assert meta["num_pings"] == 16
        assert abs(meta["avg_latitude"] - 42.15) < 1e-3
        assert abs(meta["avg_longitude"] - (-73.85)) < 1e-3

