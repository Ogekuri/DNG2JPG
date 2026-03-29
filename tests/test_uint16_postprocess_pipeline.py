# pyright: reportMissingImports=false
"""Unit tests for uint16 static postprocess and JPEG quantization boundary."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
import sys

import numpy as np

_SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

_MODULE_PATH = _SRC_PATH / "dng2jpg" / "dng2jpg.py"
_MODULE_SPEC = importlib.util.spec_from_file_location(
    "dng2jpg_test_module",
    _MODULE_PATH,
)
if _MODULE_SPEC is None or _MODULE_SPEC.loader is None:
    raise RuntimeError(f"Unable to load module spec: {_MODULE_PATH}")
dng2jpg_module = importlib.util.module_from_spec(_MODULE_SPEC)
_MODULE_SPEC.loader.exec_module(dng2jpg_module)


@dataclass
class _FakeSavedImage:
    """Minimal Pillow-like image object for `_encode_jpg` tests."""

    array: np.ndarray
    mode: str = "RGB"
    saved_path: str | None = None
    saved_kwargs: dict | None = None

    def convert(self, mode: str) -> "_FakeSavedImage":
        self.mode = mode
        return self

    def save(self, path: str, **kwargs) -> None:
        self.saved_path = path
        self.saved_kwargs = dict(kwargs)


class _FakePilModule:
    """Minimal Pillow module shim exposing `fromarray`."""

    def __init__(self) -> None:
        self.last_image: _FakeSavedImage | None = None

    def fromarray(self, image_array: np.ndarray) -> _FakeSavedImage:
        self.last_image = _FakeSavedImage(array=np.array(image_array, copy=True))
        return self.last_image


class _FakeImageIoModule:
    """Minimal imageio shim exposing `imread` and `imwrite`."""

    def __init__(self, merged_rgb_u16: np.ndarray) -> None:
        self._merged_rgb_u16 = merged_rgb_u16
        self.writes: list[tuple[str, np.ndarray]] = []

    def imread(self, _path: str) -> np.ndarray:
        return np.array(self._merged_rgb_u16, copy=True)

    def imwrite(self, path: str, image: np.ndarray) -> None:
        self.writes.append((path, np.array(image, copy=True)))


def _build_postprocess_options():
    return dng2jpg_module.PostprocessOptions(
        post_gamma=1.07,
        brightness=1.13,
        contrast=1.11,
        saturation=1.09,
        jpg_compression=25,
        auto_brightness_enabled=False,
        auto_levels_enabled=False,
        auto_adjust_mode=None,
    )


def test_apply_brightness_uint16_keeps_16bit_gradation_without_u8_lift() -> None:
    """Reproducer: static brightness must not quantize to `uint8*257` bins."""

    image_rgb_uint16 = np.array(
        [[[1000, 2001, 3002], [12345, 23456, 34567]]],
        dtype=np.uint16,
    )
    output = dng2jpg_module._apply_brightness_uint16(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_uint16=image_rgb_uint16,
        brightness_factor=1.11,
    )
    assert output.dtype == np.uint16
    assert output.shape == image_rgb_uint16.shape
    assert np.any(output % 257 != 0), "Detected unexpected uint8->uint16 lift quantization"


def test_apply_static_postprocess_uint16_does_not_call_uint8_conversion(monkeypatch) -> None:
    """Static postprocess stages must stay fully in uint16 domain."""

    image_rgb_uint16 = np.array(
        [[[4096, 8192, 16384], [11111, 22222, 33333]]],
        dtype=np.uint16,
    )

    def _fail_uint8_conversion(**_kwargs):
        raise AssertionError("Static postprocess called _to_uint8_image_array unexpectedly")

    monkeypatch.setattr(dng2jpg_module, "_to_uint8_image_array", _fail_uint8_conversion)
    output = dng2jpg_module._apply_static_postprocess_uint16(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_uint16=image_rgb_uint16,
        postprocess_options=_build_postprocess_options(),
    )
    assert output.dtype == np.uint16
    assert output.shape == image_rgb_uint16.shape


def test_encode_jpg_quantizes_once_at_final_boundary(monkeypatch, tmp_path) -> None:
    """`_encode_jpg` must call uint16->uint8 conversion exactly once at JPEG boundary."""

    merged_rgb_uint16 = np.array(
        [
            [[1000, 2000, 3000], [12000, 22000, 32000]],
            [[40000, 50000, 60000], [65535, 30000, 10000]],
        ],
        dtype=np.uint16,
    )
    imageio_module = _FakeImageIoModule(merged_rgb_u16=merged_rgb_uint16)
    pil_module = _FakePilModule()
    call_trace: list[str] = []

    original_to_uint8 = dng2jpg_module._to_uint8_image_array  # pylint: disable=protected-access

    def _tracked_to_uint8(*, np_module, image_data):
        call_trace.append("to_uint8")
        assert image_data.dtype == np.uint16
        return original_to_uint8(np_module=np_module, image_data=image_data)

    original_static = dng2jpg_module._apply_static_postprocess_uint16  # pylint: disable=protected-access

    def _tracked_static(*, np_module, image_rgb_uint16, postprocess_options):
        call_trace.append("static")
        assert image_rgb_uint16.dtype == np.uint16
        return original_static(
            np_module=np_module,
            image_rgb_uint16=image_rgb_uint16,
            postprocess_options=postprocess_options,
        )

    monkeypatch.setattr(dng2jpg_module, "_to_uint8_image_array", _tracked_to_uint8)
    monkeypatch.setattr(dng2jpg_module, "_apply_static_postprocess_uint16", _tracked_static)

    dng2jpg_module._encode_jpg(  # pylint: disable=protected-access
        imageio_module=imageio_module,
        pil_image_module=pil_module,
        merged_tiff=tmp_path / "merged.tif",
        output_jpg=tmp_path / "out.jpg",
        postprocess_options=_build_postprocess_options(),
        numpy_module=np,
    )

    assert call_trace.count("to_uint8") == 1
    assert call_trace.index("to_uint8") > call_trace.index("static")


def test_parse_run_options_accepts_enable_opencv_backend() -> None:
    """Parser must accept `--enable-opencv` as exclusive backend selector."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev=1", "--enable-opencv"]
    )
    assert parsed is not None
    _input_path = parsed[0]
    _output_path = parsed[1]
    _ev_value = parsed[2]
    _auto_ev_enabled = parsed[3]
    _gamma_value = parsed[4]
    _postprocess = parsed[5]
    enable_luminance = parsed[6]
    enable_opencv = parsed[7]
    opencv_merge_options = parsed[9]
    del (
        _input_path,
        _output_path,
        _ev_value,
        _auto_ev_enabled,
        _gamma_value,
        _postprocess,
    )
    assert enable_luminance is False
    assert enable_opencv is True
    assert opencv_merge_options.debevec_white_point_percentile > 0.0


def test_parse_run_options_rejects_multiple_backends_with_opencv() -> None:
    """Parser must reject simultaneous backend selectors including OpenCV."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--ev=1",
            "--enable-opencv",
            "--enable-enfuse",
        ]
    )
    assert parsed is None


def test_build_ev_times_from_ev_zero_and_delta_matches_bracket_sequence() -> None:
    """EV times helper must generate three deterministic stop-space samples."""

    times = dng2jpg_module._build_ev_times_from_ev_zero_and_delta(  # pylint: disable=protected-access
        ev_zero=1.0,
        ev_delta=0.5,
    )
    assert times.dtype == np.float32
    assert times.shape == (3,)
    np.testing.assert_allclose(
        times,
        np.array([2 ** 0.5, 2**1.0, 2**1.5], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )


def test_normalize_debevec_hdr_to_unit_range_clamps_to_valid_interval() -> None:
    """Debevec normalization must return float32 RGB data in [0,1]."""

    hdr_rgb = np.array(
        [
            [[10.0, 20.0, 30.0], [100.0, 120.0, 140.0]],
            [[1.0, 1.5, 2.0], [0.1, 0.2, 0.3]],
        ],
        dtype=np.float32,
    )
    normalized = dng2jpg_module._normalize_debevec_hdr_to_unit_range(  # pylint: disable=protected-access
        np_module=np,
        hdr_rgb_float32=hdr_rgb,
        white_point_percentile=99.0,
    )
    assert normalized.dtype == np.float32
    assert normalized.shape == hdr_rgb.shape
    assert float(np.min(normalized)) >= 0.0
    assert float(np.max(normalized)) <= 1.0
