# pyright: reportMissingImports=false
"""Unit tests for uint16 static postprocess and JPEG quantization boundary."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from dng2jpg import dng2jpg as dng2jpg_module


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


def _build_postprocess_options() -> dng2jpg_module.PostprocessOptions:
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
