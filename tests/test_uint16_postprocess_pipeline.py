# pyright: reportMissingImports=false
"""Unit tests for uint16 static postprocess and JPEG quantization boundary."""

from __future__ import annotations

import importlib.util
import warnings
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Protocol

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


class _FakeExifRatio:
    """Minimal EXIF rational-like payload for exposure-time parsing tests."""

    def __init__(self, numerator: int, denominator: int) -> None:
        self.numerator = numerator
        self.denominator = denominator


class _FakeExifData:
    """Minimal EXIF mapping shim for `_extract_dng_exif_payload_and_timestamp` tests."""

    def __init__(
        self,
        values: dict[int, object],
        payload: bytes = b"fake-exif",
        ifd_values: dict[int, dict[int, object]] | None = None,
    ) -> None:
        self._values = dict(values)
        self._payload = payload
        self._ifd_values = (
            {
                ifd_tag: dict(ifd_payload)
                for ifd_tag, ifd_payload in (ifd_values or {}).items()
            }
            if ifd_values is not None
            else {}
        )

    def get(self, key: int):
        return self._values.get(key)

    def get_ifd(self, key: int):
        if key not in self._ifd_values:
            raise KeyError(key)
        return self._ifd_values[key]

    def tobytes(self) -> bytes:
        return self._payload


class _FakeOpenedImage:
    """Minimal context-managed Pillow image shim exposing `getexif`."""

    def __init__(self, exif_data: _FakeExifData | None) -> None:
        self._exif_data = exif_data

    def __enter__(self) -> "_FakeOpenedImage":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb

    def getexif(self) -> _FakeExifData | None:
        return self._exif_data


class _FakeExifPilModule:
    """Minimal Pillow module shim exposing `open` for EXIF extraction tests."""

    def __init__(self, exif_data: _FakeExifData | None) -> None:
        self._exif_data = exif_data

    def open(self, _path: str) -> _FakeOpenedImage:
        return _FakeOpenedImage(self._exif_data)


class _FakeMergeMertens:
    """Minimal OpenCV MergeMertens shim for HDR backend tests."""

    def __init__(self) -> None:
        self.last_inputs: list[np.ndarray] | None = None

    def process(self, images: list[np.ndarray]) -> np.ndarray:
        self.last_inputs = [np.array(image, copy=True) for image in images]
        output_shape = self.last_inputs[0].shape
        return np.full(output_shape, 128.0, dtype=np.float32)


class _FakeMergeDebevec:
    """Minimal OpenCV MergeDebevec shim for HDR backend tests."""

    def __init__(self) -> None:
        self.last_inputs: list[np.ndarray] | None = None
        self.last_times: np.ndarray | None = None
        self.last_response: np.ndarray | None = None

    def process(
        self,
        images: list[np.ndarray],
        times: np.ndarray,
        response: np.ndarray | None = None,
    ) -> np.ndarray:
        self.last_inputs = [np.array(image, copy=True) for image in images]
        self.last_times = np.array(times, copy=True)
        self.last_response = None if response is None else np.array(response, copy=True)
        hdr_base = self.last_inputs[1].astype(np.float32)
        return (hdr_base * 1.6) + 0.2


class _FakeMergeRobertson:
    """Minimal OpenCV MergeRobertson shim for HDR backend tests."""

    def __init__(self) -> None:
        self.last_inputs: list[np.ndarray] | None = None
        self.last_times: np.ndarray | None = None
        self.last_response: np.ndarray | None = None

    def process(
        self,
        images: list[np.ndarray],
        times: np.ndarray,
        response: np.ndarray | None = None,
    ) -> np.ndarray:
        self.last_inputs = [np.array(image, copy=True) for image in images]
        self.last_times = np.array(times, copy=True)
        self.last_response = None if response is None else np.array(response, copy=True)
        hdr_base = self.last_inputs[1].astype(np.float32)
        return (hdr_base * 1.4) + 0.1


class _FakeCalibrateDebevec:
    """Minimal OpenCV CalibrateDebevec shim for HDR backend tests."""

    def __init__(self) -> None:
        self.last_inputs: list[np.ndarray] | None = None
        self.last_times: np.ndarray | None = None

    def process(self, images: list[np.ndarray], times: np.ndarray) -> np.ndarray:
        self.last_inputs = [np.array(image, copy=True) for image in images]
        self.last_times = np.array(times, copy=True)
        return np.full((256, 1, 3), 0.5, dtype=np.float32)


class _FakeCalibrateRobertson:
    """Minimal OpenCV CalibrateRobertson shim for HDR backend tests."""

    def __init__(self) -> None:
        self.last_inputs: list[np.ndarray] | None = None
        self.last_times: np.ndarray | None = None

    def process(self, images: list[np.ndarray], times: np.ndarray) -> np.ndarray:
        self.last_inputs = [np.array(image, copy=True) for image in images]
        self.last_times = np.array(times, copy=True)
        return np.full((256, 1, 3), 0.75, dtype=np.float32)


class _FakeTonemap:
    """Minimal OpenCV Tonemap shim for HDR backend tests."""

    def __init__(self, gamma: float) -> None:
        self.gamma = gamma
        self.last_input: np.ndarray | None = None

    def process(self, image: np.ndarray) -> np.ndarray:
        self.last_input = np.array(image, copy=True)
        scale = 1.0 / max(self.gamma, 1e-12)
        assert self.last_input is not None
        return np.clip(self.last_input * scale, 0.0, 1.0).astype(np.float32)


class _FakeAdvancedTonemap:
    """Minimal OpenCV advanced-tonemap shim preserving un-clipped float range."""

    def __init__(self, kind: str, **params: float) -> None:
        self.kind = kind
        self.params = dict(params)
        self.last_input: np.ndarray | None = None

    def process(self, image: np.ndarray) -> np.ndarray:
        self.last_input = np.array(image, copy=True)
        assert self.last_input is not None
        if self.kind == "drago":
            gain = float(self.params.get("saturation", 1.0)) + float(
                self.params.get("bias", 0.0)
            )
            return (self.last_input * gain).astype(np.float32)
        if self.kind == "reinhard":
            offset = float(self.params.get("intensity", 0.0))
            gain = 1.0 + float(self.params.get("light_adapt", 0.0)) + float(
                self.params.get("color_adapt", 0.0)
            )
            return ((self.last_input * gain) + offset).astype(np.float32)
        if self.kind == "mantiuk":
            gain = float(self.params.get("scale", 1.0)) * float(
                self.params.get("saturation", 1.0)
            )
            return (self.last_input * gain).astype(np.float32)
        raise AssertionError(f"Unsupported fake advanced tonemap kind: {self.kind}")


class _FakeXphotoWhiteBalanceAlgorithm:
    """Minimal OpenCV xphoto white-balance algorithm shim."""

    def __init__(self, marker: str) -> None:
        self.marker = marker
        self.hist_bin_num: int | None = None
        self.range_max: float | None = None

    def setHistBinNum(self, hist_bin_num: int) -> None:
        self.hist_bin_num = int(hist_bin_num)

    def setRangeMax(self, range_max: float) -> None:
        self.range_max = float(range_max)

    def balanceWhite(self, image_bgr_u8: np.ndarray) -> np.ndarray:
        del image_bgr_u8
        return np.zeros((1, 1, 3), dtype=np.uint8)


class _FakeXphotoModule:
    """Minimal OpenCV xphoto factory shim for white-balance mode tests."""

    def __init__(self) -> None:
        self.simple_wb = _FakeXphotoWhiteBalanceAlgorithm("simple")
        self.grayworld_wb = _FakeXphotoWhiteBalanceAlgorithm("grayworld")
        self.learning_wb = _FakeXphotoWhiteBalanceAlgorithm("learning")
        self.simple_calls = 0
        self.grayworld_calls = 0
        self.learning_calls = 0

    def createSimpleWB(self) -> _FakeXphotoWhiteBalanceAlgorithm:
        self.simple_calls += 1
        return self.simple_wb

    def createGrayworldWB(self) -> _FakeXphotoWhiteBalanceAlgorithm:
        self.grayworld_calls += 1
        return self.grayworld_wb

    def createLearningBasedWB(self) -> _FakeXphotoWhiteBalanceAlgorithm:
        self.learning_calls += 1
        return self.learning_wb


class _FakeOpenCvModule:
    """Minimal cv2 shim for deterministic `_run_opencv_merge_backend` tests."""

    IMREAD_UNCHANGED = -1
    COLOR_BGR2RGB = 1
    COLOR_RGB2BGR = 2
    INTER_AREA = 3
    CV_32F = 5

    def __init__(self) -> None:
        self._images_by_path: dict[str, np.ndarray] = {}
        self.merge_mertens = _FakeMergeMertens()
        self.merge_debevec = _FakeMergeDebevec()
        self.merge_robertson = _FakeMergeRobertson()
        self.calibrate_debevec = _FakeCalibrateDebevec()
        self.calibrate_robertson = _FakeCalibrateRobertson()
        self.xphoto = _FakeXphotoModule()
        self.written_image: np.ndarray | None = None
        self.last_tonemap: _FakeTonemap | None = None
        self.last_tonemap_drago: _FakeAdvancedTonemap | None = None
        self.last_tonemap_reinhard: _FakeAdvancedTonemap | None = None
        self.last_tonemap_mantiuk: _FakeAdvancedTonemap | None = None
        self.resize_calls: list[tuple[tuple[int, ...], tuple[int, int], int]] = []

    def register_image(self, path: Path, image: np.ndarray) -> None:
        self._images_by_path[str(path)] = np.array(image, copy=True)

    def imread(self, path: str, _flags: int) -> np.ndarray | None:
        image = self._images_by_path.get(path)
        if image is None:
            return None
        return np.array(image, copy=True)

    def cvtColor(self, image: np.ndarray, color_code: int) -> np.ndarray:
        if color_code not in (self.COLOR_BGR2RGB, self.COLOR_RGB2BGR):
            raise AssertionError(f"Unsupported color conversion code: {color_code}")
        return np.array(image[..., ::-1], copy=True)

    def resize(
        self,
        image: np.ndarray,
        dsize: tuple[int, int],
        interpolation: int,
    ) -> np.ndarray:
        if interpolation != self.INTER_AREA:
            raise AssertionError(f"Unsupported interpolation: {interpolation}")
        self.resize_calls.append((tuple(image.shape), dsize, interpolation))
        width, height = dsize
        row_indices = np.linspace(0, image.shape[0] - 1, num=height).astype(np.int32)
        col_indices = np.linspace(0, image.shape[1] - 1, num=width).astype(np.int32)
        return np.array(image[row_indices][:, col_indices], copy=True)

    def createMergeMertens(self) -> _FakeMergeMertens:
        return self.merge_mertens

    def createMergeDebevec(self) -> _FakeMergeDebevec:
        return self.merge_debevec

    def createMergeRobertson(self) -> _FakeMergeRobertson:
        return self.merge_robertson

    def createCalibrateDebevec(self) -> _FakeCalibrateDebevec:
        return self.calibrate_debevec

    def createCalibrateRobertson(self) -> _FakeCalibrateRobertson:
        return self.calibrate_robertson

    def createTonemap(self, gamma: float) -> _FakeTonemap:
        self.last_tonemap = _FakeTonemap(gamma=gamma)
        return self.last_tonemap

    def createTonemapDrago(
        self,
        *,
        gamma: float,
        saturation: float,
        bias: float,
    ) -> _FakeAdvancedTonemap:
        self.last_tonemap_drago = _FakeAdvancedTonemap(
            "drago",
            gamma=float(gamma),
            saturation=float(saturation),
            bias=float(bias),
        )
        return self.last_tonemap_drago

    def createTonemapReinhard(
        self,
        *,
        gamma: float,
        intensity: float,
        light_adapt: float,
        color_adapt: float,
    ) -> _FakeAdvancedTonemap:
        self.last_tonemap_reinhard = _FakeAdvancedTonemap(
            "reinhard",
            gamma=float(gamma),
            intensity=float(intensity),
            light_adapt=float(light_adapt),
            color_adapt=float(color_adapt),
        )
        return self.last_tonemap_reinhard

    def createTonemapMantiuk(
        self,
        *,
        gamma: float,
        scale: float,
        saturation: float,
    ) -> _FakeAdvancedTonemap:
        self.last_tonemap_mantiuk = _FakeAdvancedTonemap(
            "mantiuk",
            gamma=float(gamma),
            scale=float(scale),
            saturation=float(saturation),
        )
        return self.last_tonemap_mantiuk

    def imwrite(self, _path: str, image: np.ndarray) -> bool:
        self.written_image = np.array(image, copy=True)
        return True

    def calcHist(
        self,
        images: list[np.ndarray],
        channels: list[int],
        mask,
        hist_size: list[int],
        ranges: list[int],
    ) -> np.ndarray:
        del mask, channels, ranges
        histogram, _ = np.histogram(
            np.asarray(images[0]).ravel(),
            bins=int(hist_size[0]),
            range=(0, 256),
        )
        return histogram.astype(np.float32).reshape(-1, 1)

    def Sobel(
        self,
        image: np.ndarray,
        ddepth: int,
        dx: int,
        dy: int,
        ksize: int = 3,
    ) -> np.ndarray:
        del ddepth, ksize
        image_float = np.asarray(image, dtype=np.float32)
        grad_y, grad_x = np.gradient(image_float)
        if dx == 1 and dy == 0:
            return grad_x.astype(np.float32)
        if dx == 0 and dy == 1:
            return grad_y.astype(np.float32)
        raise AssertionError(f"Unsupported Sobel derivative order: dx={dx}, dy={dy}")

    def GaussianBlur(
        self,
        image: np.ndarray,
        ksize: tuple[int, int],
        sigma: float,
    ) -> np.ndarray:
        del ksize, sigma
        return np.asarray(image, dtype=np.float32)


class _StaticPostprocessOptionsLike(Protocol):
    """Structural type for static postprocess option access in test helpers."""

    post_gamma: float
    brightness: float
    contrast: float
    saturation: float


def _build_postprocess_options():
    return dng2jpg_module.PostprocessOptions(
        post_gamma=1.07,
        brightness=1.13,
        contrast=1.11,
        saturation=1.09,
        jpg_compression=25,
        auto_brightness_enabled=False,
        auto_levels_enabled=False,
        auto_adjust_enabled=False,
        debug_enabled=False,
    )


def _legacy_static_postprocess_quantized_reference(
    image_rgb_float: np.ndarray,
    postprocess_options: _StaticPostprocessOptionsLike,
) -> np.ndarray:
    """Run the pre-refactor quantized static postprocess for comparison tests."""

    image_u16 = np.clip(np.round(np.clip(image_rgb_float, 0.0, 1.0) * 65535.0), 0.0, 65535.0)
    image_u16 = image_u16.astype(np.uint16)
    if postprocess_options.post_gamma != 1.0:
        value_u16 = np.arange(65536, dtype=np.float64)
        lut_u16 = np.clip(
            np.round(
                np.power(value_u16 / 65535.0, 1.0 / float(postprocess_options.post_gamma))
                * 65535.0
            ),
            0.0,
            65535.0,
        ).astype(np.uint16)
        image_u16 = lut_u16[image_u16.astype(np.int32)]
    if postprocess_options.brightness != 1.0:
        image_u16 = np.clip(
            np.round(image_u16.astype(np.float64) * float(postprocess_options.brightness)),
            0.0,
            65535.0,
        ).astype(np.uint16)
    if postprocess_options.contrast != 1.0:
        image_float = image_u16.astype(np.float64)
        channel_mean = np.mean(image_float, axis=(0, 1), keepdims=True)
        image_u16 = np.clip(
            np.round(
                channel_mean
                + float(postprocess_options.contrast) * (image_float - channel_mean)
            ),
            0.0,
            65535.0,
        ).astype(np.uint16)
    if postprocess_options.saturation != 1.0:
        image_float = image_u16.astype(np.float64)
        grayscale = (
            (0.2126 * image_float[:, :, 0])
            + (0.7152 * image_float[:, :, 1])
            + (0.0722 * image_float[:, :, 2])
        )[:, :, None]
        image_u16 = np.clip(
            np.round(
                grayscale
                + float(postprocess_options.saturation) * (image_float - grayscale)
            ),
            0.0,
            65535.0,
        ).astype(np.uint16)
    return image_u16.astype(np.float32) / 65535.0


def _reflect_shift_2d(image: np.ndarray, shift_y: int, shift_x: int) -> np.ndarray:
    """Shift 2D image content using reflect padding instead of wraparound."""

    pad_y = abs(shift_y) + 4
    pad_x = abs(shift_x) + 4
    padded = np.pad(image, ((pad_y, pad_y), (pad_x, pad_x)), mode="reflect")
    start_y = pad_y - shift_y
    start_x = pad_x - shift_x
    return np.array(
        padded[start_y : start_y + image.shape[0], start_x : start_x + image.shape[1]],
        copy=True,
    )


def _reflect_shift_rgb(image: np.ndarray, shift_y: int, shift_x: int) -> np.ndarray:
    """Shift RGB image content using reflect padding instead of wraparound."""

    shifted_channels = [
        _reflect_shift_2d(image[..., channel_index], shift_y, shift_x)
        for channel_index in range(image.shape[2])
    ]
    return np.stack(shifted_channels, axis=-1).astype(image.dtype, copy=False)


def test_apply_brightness_float_preserves_sub_u16_precision() -> None:
    """Float brightness stage must avoid snapping outputs onto uint16 code values."""

    image_rgb_float = np.array(
        [[[0.1234567, 0.2345678, 0.3456789], [0.4567891, 0.5678912, 0.6789123]]],
        dtype=np.float32,
    )
    output = dng2jpg_module._apply_brightness_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        brightness_factor=1.11,
    )
    assert output.dtype == np.float32
    assert output.shape == image_rgb_float.shape
    np.testing.assert_allclose(
        output,
        (image_rgb_float.astype(np.float64) * 1.11).astype(np.float32),
        rtol=1e-6,
        atol=1e-6,
    )
    distance_to_u16_grid = np.abs(
        (output.astype(np.float64) * 65535.0)
        - np.round(output.astype(np.float64) * 65535.0)
    )
    assert np.any(distance_to_u16_grid > 1e-3)


def test_apply_post_gamma_float_preserves_unclipped_float_domain() -> None:
    """Gamma stage must preserve legacy equation without stage-local clipping."""

    image_rgb_float = np.array(
        [[[1.21, 0.81, 0.16], [0.49, 1.44, 0.25]]],
        dtype=np.float32,
    )
    output = dng2jpg_module._apply_post_gamma_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        gamma_value=2.0,
    )
    expected = np.power(image_rgb_float.astype(np.float64), 0.5).astype(np.float32)
    np.testing.assert_allclose(output, expected, rtol=1e-6, atol=1e-6)
    assert np.max(output) > 1.0


def test_apply_contrast_float_preserves_unclipped_float_domain() -> None:
    """Contrast stage must preserve legacy equation without stage-local clipping."""

    image_rgb_float = np.array(
        [[[0.05, 0.2, 0.95], [0.9, 0.8, 0.1]]],
        dtype=np.float32,
    )
    output = dng2jpg_module._apply_contrast_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        contrast_factor=1.8,
    )
    channel_mean = np.mean(image_rgb_float.astype(np.float64), axis=(0, 1), keepdims=True)
    expected = (
        channel_mean + 1.8 * (image_rgb_float.astype(np.float64) - channel_mean)
    ).astype(np.float32)
    np.testing.assert_allclose(output, expected, rtol=1e-6, atol=1e-6)
    assert np.min(output) < 0.0
    assert np.max(output) > 1.0


def test_apply_saturation_float_preserves_unclipped_float_domain() -> None:
    """Saturation stage must preserve legacy equation without stage-local clipping."""

    image_rgb_float = np.array(
        [[[0.02, 0.9, 0.1], [0.95, 0.05, 0.85]]],
        dtype=np.float32,
    )
    output = dng2jpg_module._apply_saturation_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        saturation_factor=1.8,
    )
    image_float = image_rgb_float.astype(np.float64)
    grayscale = (
        (0.2126 * image_float[:, :, 0])
        + (0.7152 * image_float[:, :, 1])
        + (0.0722 * image_float[:, :, 2])
    )[:, :, None]
    expected = (grayscale + 1.8 * (image_float - grayscale)).astype(np.float32)
    np.testing.assert_allclose(output, expected, rtol=1e-6, atol=1e-6)
    assert np.min(output) < 0.0
    assert np.max(output) > 1.0


def test_apply_static_postprocess_float_does_not_call_uint16_conversion(
    monkeypatch,
) -> None:
    """Static postprocess stage must keep float interfaces and avoid uint16 conversion."""

    image_rgb_float = np.array(
        [[[4096, 8192, 16384], [11111, 22222, 33333]]],
        dtype=np.float32,
    ) / 65535.0

    def _fail_uint16_conversion(**_kwargs):
        raise AssertionError("Static postprocess called _to_uint16_image_array unexpectedly")

    monkeypatch.setattr(dng2jpg_module, "_to_uint16_image_array", _fail_uint16_conversion)
    output = dng2jpg_module._apply_static_postprocess_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        postprocess_options=_build_postprocess_options(),
    )
    assert output.dtype == np.float32
    assert output.shape == image_rgb_float.shape


def test_apply_static_postprocess_float_skips_stage_when_all_factors_are_neutral(
    monkeypatch,
) -> None:
    """Static postprocess must bypass all substages when all factors are neutral."""

    image_rgb_float = np.array(
        [[[0.12, 0.34, 0.56], [0.78, 0.9, 0.21]]],
        dtype=np.float32,
    )
    postprocess_options = dng2jpg_module.PostprocessOptions(
        post_gamma=1.0,
        brightness=1.0,
        contrast=1.0,
        saturation=1.0,
        jpg_compression=25,
        auto_brightness_enabled=False,
        auto_levels_enabled=False,
        auto_adjust_enabled=False,
        debug_enabled=False,
    )

    def _fail_post_gamma(*_args, **_kwargs):
        raise AssertionError("Unexpected gamma stage execution")

    def _fail_brightness(*_args, **_kwargs):
        raise AssertionError("Unexpected brightness stage execution")

    def _fail_contrast(*_args, **_kwargs):
        raise AssertionError("Unexpected contrast stage execution")

    def _fail_saturation(*_args, **_kwargs):
        raise AssertionError("Unexpected saturation stage execution")

    monkeypatch.setattr(dng2jpg_module, "_apply_post_gamma_float", _fail_post_gamma)
    monkeypatch.setattr(dng2jpg_module, "_apply_brightness_float", _fail_brightness)
    monkeypatch.setattr(dng2jpg_module, "_apply_contrast_float", _fail_contrast)
    monkeypatch.setattr(dng2jpg_module, "_apply_saturation_float", _fail_saturation)

    output = dng2jpg_module._apply_static_postprocess_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        postprocess_options=postprocess_options,
    )
    np.testing.assert_allclose(output, image_rgb_float, rtol=0.0, atol=0.0)


def test_apply_static_postprocess_float_executes_only_non_neutral_substages_in_order(
    monkeypatch,
) -> None:
    """Static postprocess must execute only non-neutral substages in fixed order."""

    image_rgb_float = np.array(
        [[[0.2, 0.4, 0.6], [0.8, 0.3, 0.1]]],
        dtype=np.float32,
    )
    postprocess_options = dng2jpg_module.PostprocessOptions(
        post_gamma=1.0,
        brightness=1.25,
        contrast=1.0,
        saturation=0.85,
        jpg_compression=25,
        auto_brightness_enabled=False,
        auto_levels_enabled=False,
        auto_adjust_enabled=False,
        debug_enabled=False,
    )
    execution_order: list[str] = []

    def _tracked_gamma(*_args, **_kwargs):
        execution_order.append("gamma")
        raise AssertionError("Gamma stage must be skipped for neutral factor")

    def _tracked_brightness(*, np_module, image_rgb_float, brightness_factor):
        execution_order.append("brightness")
        return image_rgb_float.astype(np_module.float32, copy=False) + np_module.float32(0.01)

    def _tracked_contrast(*_args, **_kwargs):
        execution_order.append("contrast")
        raise AssertionError("Contrast stage must be skipped for neutral factor")

    def _tracked_saturation(*, np_module, image_rgb_float, saturation_factor):
        execution_order.append("saturation")
        return image_rgb_float.astype(np_module.float32, copy=False) + np_module.float32(0.02)

    monkeypatch.setattr(dng2jpg_module, "_apply_post_gamma_float", _tracked_gamma)
    monkeypatch.setattr(dng2jpg_module, "_apply_brightness_float", _tracked_brightness)
    monkeypatch.setattr(dng2jpg_module, "_apply_contrast_float", _tracked_contrast)
    monkeypatch.setattr(dng2jpg_module, "_apply_saturation_float", _tracked_saturation)

    output = dng2jpg_module._apply_static_postprocess_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        postprocess_options=postprocess_options,
    )
    expected = image_rgb_float + np.float32(0.03)
    np.testing.assert_allclose(output, expected, rtol=0.0, atol=0.0)
    assert execution_order == ["brightness", "saturation"]


def test_apply_static_postprocess_float_executes_auto_gamma_then_static_substages(
    monkeypatch,
) -> None:
    """Static stage must run `auto-gamma->brightness->contrast->saturation` in order."""

    image_rgb_float = np.array(
        [[[0.2, 0.4, 0.6], [0.8, 0.3, 0.1]]],
        dtype=np.float32,
    )
    postprocess_options = dng2jpg_module.PostprocessOptions(
        post_gamma=1.4,
        brightness=1.25,
        contrast=0.9,
        saturation=1.1,
        jpg_compression=25,
        post_gamma_mode="auto",
        post_gamma_auto_options=dng2jpg_module.PostGammaAutoOptions(
            target_gray=0.5,
            luma_min=0.01,
            luma_max=0.99,
            lut_size=256,
        ),
        auto_brightness_enabled=False,
        auto_levels_enabled=False,
        auto_adjust_enabled=False,
        debug_enabled=False,
    )
    execution_order: list[str] = []

    def _tracked_auto(*, np_module, image_rgb_float, post_gamma_auto_options):
        del post_gamma_auto_options
        execution_order.append("auto-gamma")
        return (
            image_rgb_float.astype(np_module.float32, copy=False) + np_module.float32(0.01),
            1.23,
        )

    def _tracked_gamma(*_args, **_kwargs):
        execution_order.append("gamma")
        raise AssertionError("Numeric gamma stage must not execute in auto-gamma mode")

    def _tracked_brightness(*, np_module, image_rgb_float, brightness_factor):
        del brightness_factor
        execution_order.append("brightness")
        return image_rgb_float.astype(np_module.float32, copy=False) + np_module.float32(0.02)

    def _tracked_contrast(*, np_module, image_rgb_float, contrast_factor):
        del contrast_factor
        execution_order.append("contrast")
        return image_rgb_float.astype(np_module.float32, copy=False) + np_module.float32(0.03)

    def _tracked_saturation(*, np_module, image_rgb_float, saturation_factor):
        del saturation_factor
        execution_order.append("saturation")
        return image_rgb_float.astype(np_module.float32, copy=False) + np_module.float32(0.04)

    monkeypatch.setattr(dng2jpg_module, "_apply_auto_post_gamma_float", _tracked_auto)
    monkeypatch.setattr(dng2jpg_module, "_apply_post_gamma_float", _tracked_gamma)
    monkeypatch.setattr(dng2jpg_module, "_apply_brightness_float", _tracked_brightness)
    monkeypatch.setattr(dng2jpg_module, "_apply_contrast_float", _tracked_contrast)
    monkeypatch.setattr(dng2jpg_module, "_apply_saturation_float", _tracked_saturation)

    output = dng2jpg_module._apply_static_postprocess_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        postprocess_options=postprocess_options,
    )
    np.testing.assert_allclose(output, image_rgb_float + np.float32(0.10), rtol=0.0, atol=1e-7)
    assert execution_order == ["auto-gamma", "brightness", "contrast", "saturation"]


def test_encode_jpg_quantizes_once_at_final_boundary(monkeypatch, tmp_path) -> None:
    """Postprocess+encode must quantize exactly once at the final JPEG boundary."""

    merged_rgb_float = np.array(
        [
            [[1000, 2000, 3000], [12000, 22000, 32000]],
            [[40000, 50000, 60000], [65535, 30000, 10000]],
        ],
        dtype=np.float32,
    ) / 65535.0
    imageio_module = _FakeImageIoModule(
        merged_rgb_u16=(merged_rgb_float * 65535.0).astype(np.uint16)
    )
    pil_module = _FakePilModule()
    call_trace: list[str] = []

    original_to_uint8 = dng2jpg_module._to_uint8_image_array  # pylint: disable=protected-access

    def _tracked_to_uint8(*, np_module, image_data):
        call_trace.append("to_uint8")
        assert image_data.dtype == np.float32
        return original_to_uint8(np_module=np_module, image_data=image_data)

    original_static = dng2jpg_module._apply_static_postprocess_float  # pylint: disable=protected-access

    def _tracked_static(*, np_module, image_rgb_float, postprocess_options):
        call_trace.append("static")
        assert image_rgb_float.dtype == np.float32
        return original_static(
            np_module=np_module,
            image_rgb_float=image_rgb_float,
            postprocess_options=postprocess_options,
        )

    monkeypatch.setattr(dng2jpg_module, "_to_uint8_image_array", _tracked_to_uint8)
    monkeypatch.setattr(dng2jpg_module, "_apply_static_postprocess_float", _tracked_static)

    postprocessed_image_float = dng2jpg_module._postprocess(  # pylint: disable=protected-access
        imageio_module=imageio_module,
        merged_image_float=merged_rgb_float,
        postprocess_options=_build_postprocess_options(),
        numpy_module=np,
    )
    dng2jpg_module._encode_jpg(  # pylint: disable=protected-access
        pil_image_module=pil_module,
        postprocessed_image_float=postprocessed_image_float,
        output_jpg=tmp_path / "out.jpg",
        postprocess_options=_build_postprocess_options(),
        numpy_module=np,
    )

    assert call_trace.count("to_uint8") == 1
    assert call_trace.index("to_uint8") > call_trace.index("static")



def test_postprocess_skips_entry_normalization_for_float_merge_output(
    monkeypatch,
) -> None:
    """Postprocess must pass float merge output to static stage without entry clipping."""

    merged_rgb_float = np.array([[[-0.25, 0.5, 1.75]]], dtype=np.float32)
    imageio_module = _FakeImageIoModule(
        merged_rgb_u16=np.zeros((1, 1, 3), dtype=np.uint16)
    )
    captured_static_inputs: list[np.ndarray] = []

    def _capture_static(*, np_module, image_rgb_float, postprocess_options):
        del np_module, postprocess_options
        captured_static_inputs.append(np.array(image_rgb_float, copy=True))
        return np.array(image_rgb_float, copy=True)

    monkeypatch.setattr(dng2jpg_module, "_apply_static_postprocess_float", _capture_static)

    _ = dng2jpg_module._postprocess(  # pylint: disable=protected-access
        imageio_module=imageio_module,
        merged_image_float=merged_rgb_float,
        postprocess_options=dng2jpg_module.PostprocessOptions(
            post_gamma=1.0,
            brightness=1.0,
            contrast=1.0,
            saturation=1.0,
            jpg_compression=25,
            auto_brightness_enabled=False,
            auto_levels_enabled=False,
            auto_adjust_enabled=False,
            debug_enabled=False,
        ),
        numpy_module=np,
    )

    assert len(captured_static_inputs) == 1
    np.testing.assert_allclose(
        captured_static_inputs[0],
        merged_rgb_float,
        rtol=0.0,
        atol=0.0,
    )


def test_postprocess_normalizes_non_float_entry_payload(monkeypatch) -> None:
    """Postprocess must normalize non-float image payloads before static stage."""

    merged_rgb_u16 = np.array([[[0, 32768, 65535]]], dtype=np.uint16)
    imageio_module = _FakeImageIoModule(
        merged_rgb_u16=np.zeros((1, 1, 3), dtype=np.uint16)
    )
    captured_static_inputs: list[np.ndarray] = []

    def _capture_static(*, np_module, image_rgb_float, postprocess_options):
        del np_module, postprocess_options
        captured_static_inputs.append(np.array(image_rgb_float, copy=True))
        return np.array(image_rgb_float, copy=True)

    monkeypatch.setattr(dng2jpg_module, "_apply_static_postprocess_float", _capture_static)

    _ = dng2jpg_module._postprocess(  # pylint: disable=protected-access
        imageio_module=imageio_module,
        merged_image_float=merged_rgb_u16,
        postprocess_options=dng2jpg_module.PostprocessOptions(
            post_gamma=1.0,
            brightness=1.0,
            contrast=1.0,
            saturation=1.0,
            jpg_compression=25,
            auto_brightness_enabled=False,
            auto_levels_enabled=False,
            auto_adjust_enabled=False,
            debug_enabled=False,
        ),
        numpy_module=np,
    )

    assert len(captured_static_inputs) == 1
    np.testing.assert_allclose(
        captured_static_inputs[0],
        np.array([[[0.0, 32768.0 / 65535.0, 1.0]]], dtype=np.float32),
        rtol=0.0,
        atol=1e-7,
    )


def test_encode_jpg_refreshes_exif_thumbnail_from_final_quantized_rgb_uint8(
    monkeypatch, tmp_path
) -> None:
    """EXIF thumbnail refresh must reuse the final quantized RGB uint8 save image."""

    merged_rgb_float = np.array(
        [
            [[0.05, 0.15, 0.25], [0.35, 0.45, 0.55]],
            [[0.65, 0.75, 0.85], [0.95, 0.4, 0.2]],
        ],
        dtype=np.float32,
    )
    pil_module = _FakePilModule()
    captured_thumbnail_inputs: list[np.ndarray] = []

    class _FakePiexifModule:
        class ImageIFD:
            Orientation = 274

        def __init__(self) -> None:
            self.loaded_payload: bytes | None = None
            self.dump_input: dict[str, object] | None = None
            self.inserted: tuple[bytes, str] | None = None
            self.TAGS = {}

        def load(self, payload: bytes) -> dict[str, object]:
            self.loaded_payload = payload
            return {
                "0th": {},
                "Exif": {},
                "GPS": {},
                "Interop": {},
                "1st": {},
                "thumbnail": None,
            }

        def dump(self, exif_dict: dict[str, object]) -> bytes:
            self.dump_input = exif_dict
            return b"updated-exif"

        def insert(self, exif_bytes: bytes, output_path: str) -> None:
            self.inserted = (exif_bytes, output_path)

    fake_piexif = _FakePiexifModule()

    def _fake_build_thumbnail(*, pil_image_module, final_image_rgb_uint8, source_orientation):
        assert pil_image_module is pil_module
        assert source_orientation == 6
        captured_thumbnail_inputs.append(np.array(final_image_rgb_uint8, copy=True))
        return b"thumb-bytes"

    monkeypatch.setattr(
        dng2jpg_module,
        "_build_oriented_thumbnail_jpeg_bytes",
        _fake_build_thumbnail,
    )

    dng2jpg_module._encode_jpg(  # pylint: disable=protected-access
        pil_image_module=pil_module,
        postprocessed_image_float=merged_rgb_float,
        output_jpg=tmp_path / "out.jpg",
        postprocess_options=_build_postprocess_options(),
        numpy_module=np,
        piexif_module=fake_piexif,
        source_exif_payload=b"source-exif",
        source_orientation=6,
    )

    assert pil_module.last_image is not None
    assert len(captured_thumbnail_inputs) == 1
    np.testing.assert_array_equal(captured_thumbnail_inputs[0], pil_module.last_image.array)
    assert fake_piexif.loaded_payload == b"source-exif"
    assert fake_piexif.dump_input is not None
    zero_ifd = fake_piexif.dump_input["0th"]
    first_ifd = fake_piexif.dump_input["1st"]
    assert isinstance(zero_ifd, dict)
    assert isinstance(first_ifd, dict)
    assert zero_ifd[274] == 6
    assert first_ifd[274] == 1
    assert fake_piexif.dump_input["thumbnail"] == b"thumb-bytes"
    assert fake_piexif.inserted == (b"updated-exif", str(tmp_path / "out.jpg"))


def test_encode_jpg_writes_debug_checkpoints_with_progressive_suffixes(
    monkeypatch, tmp_path
) -> None:
    """Postprocess debug mode must persist TIFF checkpoints in execution order."""

    merged_rgb_float = np.array(
        [
            [[0.10, 0.20, 0.30], [0.40, 0.50, 0.60]],
            [[0.70, 0.80, 0.90], [0.95, 0.65, 0.35]],
        ],
        dtype=np.float32,
    )
    imageio_module = _FakeImageIoModule(
        merged_rgb_u16=(merged_rgb_float * 65535.0).astype(np.uint16)
    )
    pil_module = _FakePilModule()
    debug_context = dng2jpg_module.DebugArtifactContext(  # pylint: disable=protected-access
        output_dir=tmp_path,
        input_stem="sample",
    )
    call_trace: list[str] = []

    original_static = dng2jpg_module._apply_static_postprocess_float  # pylint: disable=protected-access
    original_auto_brightness = dng2jpg_module._apply_auto_brightness_rgb_float  # pylint: disable=protected-access
    original_auto_levels = dng2jpg_module._apply_auto_levels_float  # pylint: disable=protected-access

    def _tracked_static(*, np_module, image_rgb_float, postprocess_options, **kwargs):
        call_trace.append("static")
        return original_static(
            np_module=np_module,
            image_rgb_float=image_rgb_float,
            postprocess_options=postprocess_options,
            **kwargs,
        )

    def _tracked_auto_brightness(*, np_module, image_rgb_float, auto_brightness_options):
        call_trace.append("auto-brightness")
        return original_auto_brightness(
            np_module=np_module,
            image_rgb_float=image_rgb_float,
            auto_brightness_options=auto_brightness_options,
        )

    def _tracked_auto_levels(*, np_module, image_rgb_float, auto_levels_options):
        call_trace.append("auto-levels")
        return original_auto_levels(
            np_module=np_module,
            image_rgb_float=image_rgb_float,
            auto_levels_options=auto_levels_options,
        )

    monkeypatch.setattr(dng2jpg_module, "_apply_static_postprocess_float", _tracked_static)
    monkeypatch.setattr(
        dng2jpg_module,
        "_apply_auto_brightness_rgb_float",
        _tracked_auto_brightness,
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_apply_auto_levels_float",
        _tracked_auto_levels,
    )
    postprocess_options = dng2jpg_module.PostprocessOptions(
        post_gamma=1.05,
        brightness=1.02,
        contrast=1.01,
        saturation=1.03,
        jpg_compression=25,
        auto_brightness_enabled=True,
        auto_levels_enabled=True,
        auto_adjust_enabled=False,
        debug_enabled=True,
    )
    postprocessed_image_float = dng2jpg_module._postprocess(  # pylint: disable=protected-access
        imageio_module=imageio_module,
        merged_image_float=merged_rgb_float,
        postprocess_options=postprocess_options,
        numpy_module=np,
        debug_context=debug_context,
    )
    dng2jpg_module._encode_jpg(  # pylint: disable=protected-access
        pil_image_module=pil_module,
        postprocessed_image_float=postprocessed_image_float,
        output_jpg=tmp_path / "out.jpg",
        postprocess_options=postprocess_options,
        numpy_module=np,
    )

    assert call_trace == ["auto-brightness", "static", "auto-levels"]
    written_paths = [Path(path) for path, _image in imageio_module.writes]
    assert written_paths == [
        tmp_path / "sample_3.0_auto-brightness.tiff",
        tmp_path / "sample_4.1_static_correction_gamma.tiff",
        tmp_path / "sample_4.2_static_correction_brightness.tiff",
        tmp_path / "sample_4.3_static_correction_contrast.tiff",
        tmp_path / "sample_4.4_static_correction_saturation.tiff",
        tmp_path / "sample_5.0_auto-levels.tiff",
    ]
    for _path, image in imageio_module.writes:
        assert image.dtype == np.uint16
        assert image.shape[-1] == 3


def test_encode_jpg_writes_auto_white_balance_checkpoint_when_enabled(
    monkeypatch, tmp_path
) -> None:
    """Postprocess debug mode must persist auto-white-balance checkpoint."""

    merged_rgb_float = np.full((2, 2, 3), 0.25, dtype=np.float32)
    imageio_module = _FakeImageIoModule(
        merged_rgb_u16=(merged_rgb_float * 65535.0).astype(np.uint16)
    )
    pil_module = _FakePilModule()
    debug_context = dng2jpg_module.DebugArtifactContext(  # pylint: disable=protected-access
        output_dir=tmp_path,
        input_stem="sample",
    )

    monkeypatch.setattr(
        dng2jpg_module,
        "_apply_auto_white_balance_stage_float",
        lambda **kwargs: np.array(kwargs["image_rgb_float"], copy=True),
    )

    postprocess_options = dng2jpg_module.PostprocessOptions(
        post_gamma=1.0,
        brightness=1.0,
        contrast=1.0,
        saturation=1.0,
        jpg_compression=25,
        auto_brightness_enabled=False,
        auto_levels_enabled=False,
        auto_adjust_enabled=False,
        debug_enabled=True,
        white_balance_mode="TTL",
    )
    postprocessed_image_float = dng2jpg_module._postprocess(  # pylint: disable=protected-access
        imageio_module=imageio_module,
        merged_image_float=merged_rgb_float,
        postprocess_options=postprocess_options,
        numpy_module=np,
        debug_context=debug_context,
    )
    dng2jpg_module._encode_jpg(  # pylint: disable=protected-access
        pil_image_module=pil_module,
        postprocessed_image_float=postprocessed_image_float,
        output_jpg=tmp_path / "out.jpg",
        postprocess_options=postprocess_options,
        numpy_module=np,
    )

    written_paths = [Path(path) for path, _image in imageio_module.writes]
    assert written_paths == [tmp_path / "sample_3.5_auto-white-balance.tiff"]


def test_write_hdr_merge_debug_checkpoints_writes_merge_gamma_boundaries(
    tmp_path,
) -> None:
    """HDR merge debug helper must persist pre/post merge-gamma and final checkpoints."""

    imageio_module = _FakeImageIoModule(
        merged_rgb_u16=np.zeros((2, 2, 3), dtype=np.uint16)
    )
    debug_context = dng2jpg_module.DebugArtifactContext(  # pylint: disable=protected-access
        output_dir=tmp_path,
        input_stem="sample",
    )
    pre_merge_gamma = np.full((2, 2, 3), 0.25, dtype=np.float32)
    post_merge_gamma = np.full((2, 2, 3), 0.5, dtype=np.float32)
    final_merge = np.full((2, 2, 3), 0.75, dtype=np.float32)

    dng2jpg_module._write_hdr_merge_debug_checkpoints(  # pylint: disable=protected-access
        imageio_module=imageio_module,
        np_module=np,
        debug_context=debug_context,
        merged_image_float=final_merge,
        merge_debug_snapshots={
            "pre_merge_gamma_output": pre_merge_gamma,
            "post_merge_gamma_output": post_merge_gamma,
            "hdr_merge_final_output": final_merge,
        },
    )

    written_paths = [Path(path) for path, _image in imageio_module.writes]
    assert written_paths == [
        tmp_path / "sample_2.0_hdr-merge_pre-merge-gamma.tiff",
        tmp_path / "sample_2.1_hdr-merge_post-merge-gamma.tiff",
        tmp_path / "sample_2.2_hdr-merge_final.tiff",
    ]


def test_write_hdr_merge_debug_checkpoints_writes_final_only_without_boundaries(
    tmp_path,
) -> None:
    """HDR merge debug helper must persist only final checkpoint when boundaries are absent."""

    imageio_module = _FakeImageIoModule(
        merged_rgb_u16=np.zeros((2, 2, 3), dtype=np.uint16)
    )
    debug_context = dng2jpg_module.DebugArtifactContext(  # pylint: disable=protected-access
        output_dir=tmp_path,
        input_stem="sample",
    )
    final_merge = np.full((2, 2, 3), 0.75, dtype=np.float32)

    dng2jpg_module._write_hdr_merge_debug_checkpoints(  # pylint: disable=protected-access
        imageio_module=imageio_module,
        np_module=np,
        debug_context=debug_context,
        merged_image_float=final_merge,
        merge_debug_snapshots={},
    )

    written_paths = [Path(path) for path, _image in imageio_module.writes]
    assert written_paths == [tmp_path / "sample_2.0_hdr-merge_final.tiff"]


def test_parse_run_options_accepts_remaining_auto_brightness_controls() -> None:
    """Parser must expose the surviving float-domain auto-brightness controls."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--auto-brightness=enable",
            "--ab-key-value=0.22",
            "--ab-white-point-pct=99.5",
            "--ab-key-min=0.05",
            "--ab-key-max=0.7",
            "--ab-max-auto-boost=1.1",
            "--ab-enable-luminance-preserving-desat=false",
            "--ab-eps=1e-5",
            "--hdr-merge=OpenCV-Merge",
        ]
    )

    assert parsed is not None
    postprocess = parsed[4]
    assert postprocess.auto_brightness_enabled is True
    assert postprocess.auto_brightness_options == dng2jpg_module.AutoBrightnessOptions(
        key_value=0.22,
        white_point_percentile=99.5,
        a_min=0.05,
        a_max=0.7,
        max_auto_boost_factor=1.1,
        enable_luminance_preserving_desat=False,
        eps=1e-5,
    )


def test_parse_run_options_accepts_auto_adjust_clahe_controls() -> None:
    """Parser must expose enabled auto-adjust CLAHE-luma controls."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--auto-adjust=enable",
            "--aa-enable-local-contrast=false",
            "--aa-local-contrast-strength=0.35",
            "--aa-clahe-clip-limit=1.7",
            "--aa-clahe-tile-grid-size=6x10",
            "--hdr-merge=OpenCV-Merge",
        ]
    )

    assert parsed is not None
    postprocess = parsed[4]
    assert postprocess.auto_adjust_enabled is True
    assert postprocess.auto_adjust_options == dng2jpg_module.AutoAdjustOptions(
        enable_local_contrast=False,
        local_contrast_strength=0.35,
        clahe_clip_limit=1.7,
        clahe_tile_grid_size=(6, 10),
    )


def test_parse_run_options_accepts_white_balance_modes_and_selector_defaults() -> None:
    """Parser must accept white-balance selectors and default xphoto selector."""

    parsed_default = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1"]
    )
    assert parsed_default is not None
    assert (
        parsed_default[4].raw_white_balance_mode
        == dng2jpg_module.DEFAULT_RAW_WHITE_BALANCE_MODE
    )
    assert parsed_default[4].white_balance_mode is None
    assert (
        parsed_default[4].white_balance_xphoto_domain
        == dng2jpg_module.DEFAULT_WHITE_BALANCE_XPHOTO_DOMAIN
    )
    assert (
        parsed_default[4].white_balance_xphoto_domain
        == dng2jpg_module.WHITE_BALANCE_XPHOTO_DOMAIN_LINEAR
    )

    for raw_white_balance_mode in ("GREEN", "MAX", "MIN", "MEAN"):
        parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
            [
                "input.dng",
                "output.jpg",
                "--bracketing=1",
                f"--white-balance={raw_white_balance_mode}",
            ]
        )
        assert parsed is not None
        assert parsed[4].raw_white_balance_mode == raw_white_balance_mode

    for white_balance_mode in (
        "Simple",
        "GrayworldWB",
        "IA",
        "ColorConstancy",
        "TTL",
    ):
        parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
            [
                "input.dng",
                "output.jpg",
                "--bracketing=1",
                f"--auto-white-balance={white_balance_mode}",
            ]
        )
        assert parsed is not None
        assert parsed[4].white_balance_mode == white_balance_mode
        assert (
            parsed[4].white_balance_xphoto_domain
            == dng2jpg_module.DEFAULT_WHITE_BALANCE_XPHOTO_DOMAIN
        )
    parsed_explicit_disable = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1", "--auto-white-balance=DISABLE"]
    )
    assert parsed_explicit_disable is not None
    assert parsed_explicit_disable[4].white_balance_mode is None
    assert (
        parsed_explicit_disable[4].white_balance_xphoto_domain
        == dng2jpg_module.DEFAULT_WHITE_BALANCE_XPHOTO_DOMAIN
    )
    parsed_xphoto_domain = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--auto-white-balance=Simple",
            "--white-balance-xphoto-domain=srgb",
        ]
    )
    assert parsed_xphoto_domain is not None
    assert (
        parsed_xphoto_domain[4].white_balance_xphoto_domain
        == dng2jpg_module.WHITE_BALANCE_XPHOTO_DOMAIN_SRGB
    )


def test_parse_run_options_rejects_invalid_white_balance_mode_or_selectors() -> None:
    """Parser must reject unsupported white-balance mode and selector values."""

    invalid_raw_white_balance = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1", "--white-balance=invalid-mode"]
    )
    assert invalid_raw_white_balance is None
    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1", "--auto-white-balance=invalid-mode"]
    )
    assert parsed is None
    missing = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1", "--auto-white-balance"]
    )
    assert missing is None
    removed_analysis_source = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--auto-white-balance=Simple",
            "--white-balance-analysis-source=linear-base",
        ]
    )
    assert removed_analysis_source is None
    invalid_xphoto_domain = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--auto-white-balance=Simple",
            "--white-balance-xphoto-domain=invalid",
        ]
    )
    assert invalid_xphoto_domain is None


def test_analyze_luminance_key_uses_original_thresholds_and_auto_boost_rules() -> None:
    """Key analysis must keep the original clipping proxies and boost heuristics."""

    luminance = np.array(
        [
            [0.0, 1.0 / 255.0, 1.0 / 254.0],
            [253.0 / 255.0, 254.0 / 255.0, 1.0],
        ],
        dtype=np.float64,
    )
    analysis = dng2jpg_module._analyze_luminance_key(  # pylint: disable=protected-access
        np_module=np,
        luminance=luminance,
        eps=1e-6,
    )

    np.testing.assert_allclose(analysis["shadow_clip_in"], 2.0 / 6.0, rtol=1e-12)
    np.testing.assert_allclose(analysis["highlight_clip_in"], 2.0 / 6.0, rtol=1e-12)

    options = dng2jpg_module.AutoBrightnessOptions(
        a_min=0.045,
        a_max=0.72,
        max_auto_boost_factor=1.25,
    )
    boosted = dng2jpg_module._choose_auto_key_value(  # pylint: disable=protected-access
        key_analysis={
            "key_type": "low-key",
            "median_lum": 0.20,
            "p05": 0.01,
            "p95": 0.50,
        },
        auto_brightness_options=options,
    )
    attenuated = dng2jpg_module._choose_auto_key_value(  # pylint: disable=protected-access
        key_analysis={
            "key_type": "high-key",
            "median_lum": 0.70,
            "p05": 0.50,
            "p95": 0.98,
        },
        auto_brightness_options=options,
    )

    np.testing.assert_allclose(boosted, 0.1125, rtol=1e-12)
    np.testing.assert_allclose(attenuated, 0.288, rtol=1e-12)


def test_apply_auto_brightness_rgb_float_executes_original_stage_order(
    monkeypatch,
) -> None:
    """Auto-brightness must keep the original stage order on float interfaces."""

    call_trace: list[str] = []
    image_rgb_float = np.array([[[1024, 2048, 4096]]], dtype=np.float32) / 65535.0

    def _fake_luminance(*, np_module, linear_rgb):
        del np_module, linear_rgb  # Unused by fake stage.
        call_trace.append("compute_luminance")
        return np.full((1, 1), 0.2, dtype=np.float64)

    def _fake_analyze(*, np_module, luminance, eps):
        del np_module, luminance, eps  # Unused by fake stage.
        call_trace.append("analyze")
        return {"key_type": "normal-key", "median_lum": 0.4, "p05": 0.1, "p95": 0.8}

    def _fake_choose(*, key_analysis, auto_brightness_options):
        del key_analysis, auto_brightness_options  # Unused by fake stage.
        call_trace.append("choose")
        return 0.18

    def _fake_reinhard(*, np_module, luminance, key_value, white_point_percentile, eps):
        del np_module, luminance, key_value, white_point_percentile, eps  # Unused by fake stage.
        call_trace.append("reinhard")
        return np.full((1, 1), 0.4, dtype=np.float64), {}

    def _fake_desaturate(*, np_module, rgb_linear, luminance, eps):
        del np_module, rgb_linear, luminance, eps  # Unused by fake stage.
        call_trace.append("desaturate")
        return np.full((1, 1, 3), 0.35, dtype=np.float64)

    monkeypatch.setattr(
        dng2jpg_module,
        "_compute_bt709_luminance",
        _fake_luminance,
    )
    monkeypatch.setattr(dng2jpg_module, "_analyze_luminance_key", _fake_analyze)
    monkeypatch.setattr(dng2jpg_module, "_choose_auto_key_value", _fake_choose)
    monkeypatch.setattr(
        dng2jpg_module,
        "_reinhard_global_tonemap_luminance",
        _fake_reinhard,
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_luminance_preserving_desaturate_to_fit",
        _fake_desaturate,
    )

    output = dng2jpg_module._apply_auto_brightness_rgb_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        auto_brightness_options=dng2jpg_module.AutoBrightnessOptions(
            enable_luminance_preserving_desat=True,
        ),
    )

    assert output.dtype == np.float32
    assert call_trace == [
        "compute_luminance",
        "analyze",
        "choose",
        "reinhard",
        "desaturate",
    ]


def test_should_use_low_variance_auto_brightness_fallback_uses_sample_count_and_spread() -> None:
    """Low-variance safeguard must route sparse or flat luminance to fallback path."""

    use_sparse_fallback, sparse_metrics = (
        dng2jpg_module._should_use_low_variance_auto_brightness_fallback(  # pylint: disable=protected-access
            np_module=np,
            finite_luminance_samples=np.array([0.4], dtype=np.float64),
        )
    )
    assert use_sparse_fallback is True
    assert sparse_metrics["sample_count"] == 1

    use_uniform_fallback, _ = (
        dng2jpg_module._should_use_low_variance_auto_brightness_fallback(  # pylint: disable=protected-access
            np_module=np,
            finite_luminance_samples=np.full((64,), 0.4, dtype=np.float64),
        )
    )
    assert use_uniform_fallback is True

    use_near_uniform_fallback, _ = (
        dng2jpg_module._should_use_low_variance_auto_brightness_fallback(  # pylint: disable=protected-access
            np_module=np,
            finite_luminance_samples=np.linspace(0.497, 0.503, 64, dtype=np.float64),
        )
    )
    assert use_near_uniform_fallback is True

    use_dynamic_fallback, dynamic_metrics = (
        dng2jpg_module._should_use_low_variance_auto_brightness_fallback(  # pylint: disable=protected-access
            np_module=np,
            finite_luminance_samples=np.linspace(0.05, 0.95, 64, dtype=np.float64),
        )
    )
    assert use_dynamic_fallback is False
    assert (
        dynamic_metrics["spread_p01_p99"]
        > dng2jpg_module.DEFAULT_AB_LOW_VARIANCE_SPREAD_THRESHOLD
    )


def test_apply_auto_brightness_low_variance_fallback_uniform_and_near_uniform_inputs() -> None:
    """Auto-brightness fallback must avoid whitening while preserving float-domain behavior."""

    auto_brightness_options = dng2jpg_module.AutoBrightnessOptions(
        enable_luminance_preserving_desat=True,
    )
    uniform_1x1 = np.full((1, 1, 3), 0.20, dtype=np.float32)
    uniform_8x8 = np.full((8, 8, 3), 0.35, dtype=np.float32)
    near_uniform_noise = np.repeat(
        np.clip(
            0.50 + np.linspace(-0.003, 0.003, 64, dtype=np.float64).reshape(8, 8, 1),
            0.0,
            1.0,
        ),
        3,
        axis=2,
    ).astype(np.float32)
    dynamic_non_uniform = np.array(
        [
            [[0.05, 0.10, 0.15], [0.35, 0.40, 0.45]],
            [[0.65, 0.70, 0.75], [0.90, 0.95, 0.85]],
        ],
        dtype=np.float32,
    )

    output_1x1 = dng2jpg_module._apply_auto_brightness_rgb_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=uniform_1x1,
        auto_brightness_options=auto_brightness_options,
    )
    output_8x8 = dng2jpg_module._apply_auto_brightness_rgb_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=uniform_8x8,
        auto_brightness_options=auto_brightness_options,
    )
    output_near_uniform = dng2jpg_module._apply_auto_brightness_rgb_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=near_uniform_noise,
        auto_brightness_options=auto_brightness_options,
    )
    output_dynamic = dng2jpg_module._apply_auto_brightness_rgb_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=dynamic_non_uniform,
        auto_brightness_options=auto_brightness_options,
    )

    for output in (output_1x1, output_8x8, output_near_uniform, output_dynamic):
        assert output.dtype == np.float32
        assert float(np.min(output)) >= 0.0
        assert float(np.max(output)) <= 1.0

    assert float(np.max(output_1x1)) < 0.95
    assert float(np.max(output_8x8)) < 0.95

    monotonic_means = []
    for level in (0.10, 0.50, 0.90):
        output_level = dng2jpg_module._apply_auto_brightness_rgb_float(  # pylint: disable=protected-access
            np_module=np,
            image_rgb_float=np.full((1, 1, 3), level, dtype=np.float32),
            auto_brightness_options=auto_brightness_options,
        )
        monotonic_means.append(float(np.mean(output_level)))
    assert monotonic_means[0] < monotonic_means[1] < monotonic_means[2]

    near_uniform_quantized_8bit = np.round(output_near_uniform * 255.0) / 255.0
    assert bool(np.any(np.abs(output_near_uniform - near_uniform_quantized_8bit) > 1e-6))
    assert np.unique(np.round(output_near_uniform[..., 0], decimals=6)).size > 8

    dynamic_luminance = dng2jpg_module._compute_bt709_luminance(  # pylint: disable=protected-access
        np_module=np,
        linear_rgb=dynamic_non_uniform.astype(np.float64),
    )
    dynamic_finite_samples = dng2jpg_module._extract_finite_luminance_samples(  # pylint: disable=protected-access
        np_module=np,
        luminance=dynamic_luminance,
    )
    use_dynamic_fallback, _ = (
        dng2jpg_module._should_use_low_variance_auto_brightness_fallback(  # pylint: disable=protected-access
            np_module=np,
            finite_luminance_samples=dynamic_finite_samples,
        )
    )
    assert use_dynamic_fallback is False
    assert float(np.std(output_dynamic[..., 0])) > 0.05


def test_apply_validated_auto_adjust_pipeline_executes_clahe_stage_order(
    monkeypatch,
) -> None:
    """Auto-adjust must insert float-domain CLAHE-luma after level."""

    call_trace: list[str] = []
    image_rgb_float = np.array([[[0.25, 0.5, 0.75]]], dtype=np.float32)

    def _fake_blur(np_module, rgb, sigma, threshold_percent):
        del np_module, rgb, sigma, threshold_percent  # Unused by fake stage.
        call_trace.append("blur")
        return np.full((1, 1, 3), 0.2, dtype=np.float64)

    def _fake_level(np_module, rgb, low_pct, high_pct):
        del np_module, rgb, low_pct, high_pct  # Unused by fake stage.
        call_trace.append("level")
        return np.full((1, 1, 3), 0.3, dtype=np.float64)

    def _fake_clahe(cv2_module, np_module, image_rgb_float, auto_adjust_options):
        del cv2_module, np_module, image_rgb_float, auto_adjust_options  # Unused by fake stage.
        call_trace.append("clahe")
        return np.full((1, 1, 3), 0.4, dtype=np.float64)

    def _fake_sigmoid(np_module, rgb, contrast, midpoint):
        del np_module, rgb, contrast, midpoint  # Unused by fake stage.
        call_trace.append("sigmoid")
        return np.full((1, 1, 3), 0.5, dtype=np.float64)

    def _fake_vibrance(np_module, rgb, saturation_gamma):
        del np_module, rgb, saturation_gamma  # Unused by fake stage.
        call_trace.append("vibrance")
        return np.full((1, 1, 3), 0.6, dtype=np.float64)

    def _fake_high_pass(cv2_module, np_module, rgb, blur_sigma):
        del cv2_module, np_module, rgb, blur_sigma  # Unused by fake stage.
        call_trace.append("highpass")
        return np.full((1, 1), 0.7, dtype=np.float64)

    def _fake_overlay(np_module, base_rgb, overlay_gray):
        del np_module, base_rgb, overlay_gray  # Unused by fake stage.
        call_trace.append("overlay")
        return np.full((1, 1, 3), 0.8, dtype=np.float64)

    monkeypatch.setattr(
        dng2jpg_module,
        "_selective_blur_contrast_gated_vectorized",
        _fake_blur,
    )
    monkeypatch.setattr(dng2jpg_module, "_level_per_channel_adaptive", _fake_level)
    monkeypatch.setattr(dng2jpg_module, "_apply_clahe_luma_rgb_float", _fake_clahe)
    monkeypatch.setattr(dng2jpg_module, "_sigmoidal_contrast", _fake_sigmoid)
    monkeypatch.setattr(dng2jpg_module, "_vibrance_hsl_gamma", _fake_vibrance)
    monkeypatch.setattr(dng2jpg_module, "_high_pass_math_gray", _fake_high_pass)
    monkeypatch.setattr(dng2jpg_module, "_overlay_composite", _fake_overlay)

    output = dng2jpg_module._apply_validated_auto_adjust_pipeline(  # pylint: disable=protected-access
        image_rgb_float=image_rgb_float,
        cv2_module=object(),
        np_module=np,
        auto_adjust_options=dng2jpg_module.AutoAdjustOptions(),
    )

    assert output.dtype == np.float32
    assert call_trace == [
        "blur",
        "level",
        "clahe",
        "sigmoid",
        "vibrance",
        "highpass",
        "overlay",
    ]


def test_apply_clahe_luma_rgb_float_matches_uint16_reference_within_quantization_tolerance() -> None:
    """Float-domain CLAHE-luma must stay within quantization-only deviation."""

    import cv2  # pylint: disable=import-outside-toplevel

    ramp = np.linspace(0.0, 1.0, 16, dtype=np.float32)
    grid_x, grid_y = np.meshgrid(ramp, ramp)
    image_rgb_float = np.stack(
        [
            grid_x,
            (0.65 * grid_y) + (0.35 * grid_x),
            np.clip(1.0 - (0.55 * grid_x) - (0.25 * grid_y), 0.0, 1.0),
        ],
        axis=-1,
    ).astype(np.float32)
    options = dng2jpg_module.AutoAdjustOptions(
        enable_local_contrast=True,
        local_contrast_strength=0.35,
        clahe_clip_limit=1.7,
        clahe_tile_grid_size=(4, 4),
    )

    float_output = dng2jpg_module._apply_clahe_luma_rgb_float(  # pylint: disable=protected-access
        cv2_module=cv2,
        np_module=np,
        image_rgb_float=image_rgb_float,
        auto_adjust_options=options,
    )

    reference_rgb_uint16 = dng2jpg_module._to_uint16_image_array(  # pylint: disable=protected-access
        np_module=np,
        image_data=image_rgb_float,
    )
    reference_bgr_uint16 = cv2.cvtColor(reference_rgb_uint16, cv2.COLOR_RGB2BGR)
    reference_bgr_uint16 = dng2jpg_module._apply_mild_local_contrast_bgr_uint16(  # pylint: disable=protected-access
        cv2_module=cv2,
        np_module=np,
        image_bgr_uint16=reference_bgr_uint16,
        options=options,
    )
    reference_rgb_float = dng2jpg_module._normalize_float_rgb_image(  # pylint: disable=protected-access
        np_module=np,
        image_data=cv2.cvtColor(reference_bgr_uint16, cv2.COLOR_BGR2RGB),
    )

    assert float_output.dtype == np.float64
    assert reference_rgb_float.dtype == np.float32
    np.testing.assert_allclose(
        float_output.astype(np.float32),
        reference_rgb_float,
        rtol=0.0,
        atol=3.0 / 65535.0,
    )


def test_parse_run_options_accepts_hdr_merge_opencv_backend() -> None:
    """Parser must accept `--hdr-merge=OpenCV-Merge` as backend selector."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1", "--hdr-merge=OpenCV-Merge"]
    )
    assert parsed is not None
    _input_path = parsed[0]
    _output_path = parsed[1]
    _ev_value = parsed[2]
    _auto_ev_enabled = parsed[3]
    _postprocess = parsed[4]
    enable_luminance = parsed[5]
    enable_opencv = parsed[6]
    opencv_merge_options = parsed[8]
    del (
        _input_path,
        _output_path,
        _ev_value,
        _auto_ev_enabled,
        _postprocess,
    )
    assert enable_luminance is False
    assert enable_opencv is True
    assert (
        opencv_merge_options.merge_algorithm
        == dng2jpg_module.DEFAULT_OPENCV_MERGE_ALGORITHM
    )
    assert opencv_merge_options.tonemap_enabled is True
    assert opencv_merge_options.tonemap_gamma == 1.0


def test_parse_run_options_defaults_hdr_merge_to_opencv_tonemap() -> None:
    """Parser must default backend selector to OpenCV-Tonemap when omitted."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1"]
    )
    assert parsed is not None
    assert parsed[4].opencv_tonemap_options is not None
    assert parsed[4].opencv_tonemap_options.tonemap_map == "reinhard"
    assert parsed[6] is False
    assert parsed[5] is False
    assert parsed[10] is False


def test_parse_run_options_accepts_opencv_tonemap_backend_and_default_selector(
) -> None:
    """Parser must accept OpenCV-Tonemap and default omitted selector to reinhard."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--hdr-merge=OpenCV-Tonemap",
            "--opencv-tonemap-algorithm=drago",
        ]
    )
    assert parsed is not None
    postprocess = parsed[4]
    assert postprocess.opencv_tonemap_options is not None
    assert postprocess.opencv_tonemap_options.tonemap_map == "drago"
    assert parsed[5] is False
    assert parsed[6] is False
    assert parsed[10] is False

    missing_selector = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1", "--hdr-merge=OpenCV-Tonemap"]
    )
    assert missing_selector is not None
    missing_postprocess = missing_selector[4]
    assert missing_postprocess.opencv_tonemap_options is not None
    assert missing_postprocess.opencv_tonemap_options.tonemap_map == "reinhard"

    multiple_selectors = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--hdr-merge=OpenCV-Tonemap",
            "--opencv-tonemap-algorithm=drago",
            "--opencv-tonemap-algorithm=reinhard",
        ]
    )
    assert multiple_selectors is None


def test_resolve_default_postprocess_opencv_uses_updated_static_defaults() -> None:
    """OpenCV backend defaults must resolve to the updated static factors."""

    expected_defaults = {
        dng2jpg_module.OPENCV_MERGE_ALGORITHM_DEBEVEC: (1.0, 1.2, 1.5, 1.0),
        dng2jpg_module.OPENCV_MERGE_ALGORITHM_ROBERTSON: (1.0, 1.4, 1.4, 1.0),
        dng2jpg_module.OPENCV_MERGE_ALGORITHM_MERTENS: (1.0, 0.9, 1.4, 1.1),
    }
    for algorithm, expected in expected_defaults.items():
        defaults = dng2jpg_module._resolve_default_postprocess(  # pylint: disable=protected-access
            dng2jpg_module.HDR_MERGE_MODE_OPENCV_MERGE,
            dng2jpg_module.DEFAULT_LUMINANCE_TMO,
            opencv_merge_algorithm=algorithm,
        )
        assert defaults == expected


def test_resolve_default_postprocess_hdrplus_uses_updated_static_defaults() -> None:
    """HDR+ backend defaults must resolve to the updated static factors."""

    defaults = dng2jpg_module._resolve_default_postprocess(  # pylint: disable=protected-access
        dng2jpg_module.HDR_MERGE_MODE_HDR_PLUS,
        dng2jpg_module.DEFAULT_LUMINANCE_TMO,
    )
    assert defaults == (0.9, 0.9, 1.2, 1.0)


def test_resolve_default_postprocess_luminance_uses_updated_tmo_defaults() -> None:
    """Luminance backend defaults must resolve the updated TMO-specific factors."""

    mantiuk_defaults = dng2jpg_module._resolve_default_postprocess(  # pylint: disable=protected-access
        dng2jpg_module.HDR_MERGE_MODE_LUMINANCE,
        "mantiuk08",
    )
    reinhard_defaults = dng2jpg_module._resolve_default_postprocess(  # pylint: disable=protected-access
        dng2jpg_module.HDR_MERGE_MODE_LUMINANCE,
        "reinhard02",
    )
    assert mantiuk_defaults == (0.9, 0.8, 1.2, 1.05)
    assert reinhard_defaults == (0.9, 1.3, 0.9, 0.7)


def test_resolve_default_postprocess_opencv_tonemap_uses_algorithm_defaults() -> None:
    """OpenCV-Tonemap defaults must resolve per selected tone-map algorithm."""

    expected_defaults = {
        dng2jpg_module.OPENCV_TONEMAP_MAP_DRAGO: (1.0, 1.0, 1.4, 0.6),
        dng2jpg_module.OPENCV_TONEMAP_MAP_REINHARD: (1.0, 1.0, 1.0, 1.0),
        dng2jpg_module.OPENCV_TONEMAP_MAP_MANTIUK: (0.9, 1.2, 1.4, 0.5),
    }
    for algorithm, expected in expected_defaults.items():
        defaults = dng2jpg_module._resolve_default_postprocess(  # pylint: disable=protected-access
            dng2jpg_module.HDR_MERGE_MODE_OPENCV_TONEMAP,
            dng2jpg_module.DEFAULT_LUMINANCE_TMO,
            opencv_tonemap_algorithm=algorithm,
        )
        assert defaults == expected


def test_print_help_orders_sections_by_pipeline_step(capsys) -> None:
    """Help output must follow pipeline step order and colocate stage knobs."""

    dng2jpg_module.print_help("test-version")
    output = capsys.readouterr().out

    assert output.index("Step 1 - Inputs and command surface") < output.index(
        "Step 2 - Exposure planning and RAW bracket extraction"
    )
    assert output.index(
        "Step 2 - Exposure planning and RAW bracket extraction"
    ) < output.index("Step 3 - Optional white-balance stage and HDR backend selection")
    assert output.index(
        "Step 3 - Optional white-balance stage and HDR backend selection"
    ) < output.index("Step 4 - Auto-brightness stage")
    assert output.index("Step 4 - Auto-brightness stage") < output.index(
        "Step 5 - Static postprocess stage"
    )
    assert output.index("Step 5 - Static postprocess stage") < output.index(
        "Step 6 - Auto-levels stage"
    )
    assert output.index("Step 6 - Auto-levels stage") < output.index(
        "Step 7 - Auto-adjust stage"
    )
    assert output.index("Step 7 - Auto-adjust stage") < output.index(
        "Step 8 - Final JPEG, EXIF refresh, and debug artifacts"
    )
    assert output.index("--auto-brightness=<enable|disable>") < output.index(
        "--ab-key-value=<value>"
    )
    assert output.index("--auto-levels=<enable|disable>") < output.index(
        "--al-clip-pct=<value>"
    )
    assert output.index("--white-balance=<GREEN|MAX|MIN|MEAN>") < output.index(
        "--auto-white-balance=<mode>"
    )
    assert output.index("--auto-white-balance=<mode>") < output.index(
        "--white-balance-xphoto-domain=<domain>"
    )
    assert output.index("--white-balance-xphoto-domain=<domain>") < output.index(
        "--hdr-merge=<Luminace-HDR|OpenCV-Merge|OpenCV-Tonemap|HDR-Plus>"
    )
    assert output.index("--hdr-merge=<Luminace-HDR|OpenCV-Merge|OpenCV-Tonemap|HDR-Plus>") < output.index(
        "--opencv-merge-algorithm=<name>"
    )
    assert output.index("--hdr-merge=<Luminace-HDR|OpenCV-Merge|OpenCV-Tonemap|HDR-Plus>") < output.index(
        "--opencv-tonemap-algorithm=<drago|reinhard|mantiuk>"
    )
    assert output.index("--hdr-merge=<Luminace-HDR|OpenCV-Merge|OpenCV-Tonemap|HDR-Plus>") < output.index(
        "--hdrplus-proxy-mode=<name>"
    )
    assert output.index("--hdr-merge=<Luminace-HDR|OpenCV-Merge|OpenCV-Tonemap|HDR-Plus>") < output.index(
        "--luminance-hdr-model=<name>"
    )


def test_print_help_documents_all_conversion_options_with_defaults(capsys) -> None:
    """Help output must enumerate accepted conversion options and omitted defaults."""

    dng2jpg_module.print_help("test-version")
    output = capsys.readouterr().out

    required_tokens = [
        "<input.dng>",
        "<output.jpg>",
        "--help",
        "--bracketing=<value>",
        "--exposure=<value>",
        "--auto-ev-shadow-clipping=<0..100>",
        "--auto-ev-highlight-clipping=<0..100>",
        "--auto-ev-step=<value>",
        "--white-balance=<GREEN|MAX|MIN|MEAN>",
        "--auto-white-balance=<mode>",
        "--white-balance-xphoto-domain=<domain>",
        "--hdr-merge=<Luminace-HDR|OpenCV-Merge|OpenCV-Tonemap|HDR-Plus>",
        "--opencv-merge-algorithm=<name>",
        "--opencv-merge-tonemap=<bool>",
        "--opencv-merge-tonemap-gamma=<value>",
        "--opencv-tonemap-algorithm=<drago|reinhard|mantiuk>",
        "--opencv-tonemap-drago-saturation=<value>",
        "--opencv-tonemap-drago-bias=<0..1>",
        "--opencv-tonemap-reinhard-intensity=<value>",
        "--opencv-tonemap-reinhard-light_adapt=<0..1>",
        "--opencv-tonemap-reinhard-color_adapt=<0..1>",
        "--opencv-tonemap-mantiuk-scale=<value>",
        "--opencv-tonemap-mantiuk-saturation=<value>",
        "--hdrplus-proxy-mode=<name>",
        "--hdrplus-search-radius=<value>",
        "--hdrplus-temporal-factor=<value>",
        "--hdrplus-temporal-min-dist=<value>",
        "--hdrplus-temporal-max-dist=<value>",
        "--luminance-hdr-model=<name>",
        "--luminance-hdr-weight=<name>",
        "--luminance-hdr-response-curve=<name>",
        "--luminance-tmo=<name>",
        "--tmo*=<value>",
        "--auto-brightness=<enable|disable>",
        "--ab-key-value=<value>",
        "--ab-white-point-pct=<(0,100)>",
        "--ab-key-min=<value>",
        "--ab-key-max=<value>",
        "--ab-max-auto-boost=<value>",
        "--ab-enable-luminance-preserving-desat[=<bool>]",
        "--ab-eps=<value>",
        "--auto-levels=<enable|disable>",
        "--al-clip-pct=<value>",
        "--al-clip-out-of-gamut[=<bool>]",
        "--al-highlight-reconstruction-method=<name>",
        "--al-gain-threshold=<value>",
        "--post-gamma=<value|auto>",
        "--post-gamma-auto-target-gray=<value>",
        "--post-gamma-auto-luma-min=<value>",
        "--post-gamma-auto-luma-max=<value>",
        "--post-gamma-auto-lut-size=<value>",
        "--brightness=<value>",
        "--contrast=<value>",
        "--saturation=<value>",
        "--auto-adjust=<enable|disable>",
        "--aa-blur-sigma=<value>",
        "--aa-blur-threshold-pct=<0..100>",
        "--aa-level-low-pct=<0..100>",
        "--aa-level-high-pct=<0..100>",
        "--aa-enable-local-contrast[=<bool>]",
        "--aa-local-contrast-strength=<0..1>",
        "--aa-clahe-clip-limit=<value>",
        "--aa-clahe-tile-grid-size=<rows>x<cols>",
        "--aa-sigmoid-contrast=<value>",
        "--aa-sigmoid-midpoint=<0..1>",
        "--aa-saturation-gamma=<value>",
        "--aa-highpass-blur-sigma=<value>",
        "--jpg-compression=<0..100>",
        "--debug",
    ]
    for token in required_tokens:
        assert token in output
    assert "--gamma=<auto|a,b>" in output
    assert "--auto-zero=<enable|disable>" not in output
    assert "--auto-zero-pct=<0..100>" not in output

    assert "Value options MUST use the `--option=value` form; the separated `--option value` form is rejected." in output
    assert "Only accepted value: `linear`." in output
    assert "Allowed values: Debevec, Robertson, Mertens." in output
    assert "Allowed values: rggb, bt709, mean." in output
    assert "Allowed values: GREEN, MAX, MIN, MEAN." in output
    assert (
        "Allowed values: Simple, GrayworldWB, IA, ColorConstancy, TTL, disable."
        in output
    )
    assert "Effective only when `--hdr-merge=OpenCV-Merge`." in output
    assert "Effective only when `--hdr-merge=OpenCV-Tonemap`" in output
    assert "Effective only when `--hdr-merge=HDR-Plus`." in output
    assert "Effective only when `--hdr-merge=Luminace-HDR`." in output
    assert "Default: `OpenCV-Tonemap`." in output
    assert output.count("Default:\n                                    `20`.") >= 2
    assert "Default: `Debevec`." in output
    assert "Default: `enable`." in output
    assert "Default by algorithm: `Debevec=1`, `Robertson=0.9`, `Mertens=0.8`." in output
    assert "Static postprocess defaults when omitted:" in output
    assert "HDR-Plus" in output and "0.9 / 0.9 / 1.2 / 1" in output
    assert "mantiuk08" in output and "0.9 / 0.8 / 1.2 / 1.05" in output
    assert "reinhard02" in output and "0.9 / 1.3 / 0.9 / 0.7" in output
    assert "Debevec" in output and "1 / 1.2 / 1.5 / 1" in output
    assert "Mertens" in output and "1 / 0.9 / 1.4 / 1.1" in output
    assert "Robertson" in output and "1 / 1.4 / 1.4 / 1" in output
    assert "drago" in output and "1 / 1 / 1.4 / 0.6" in output
    assert "mantiuk" in output and "0.9 / 1.2 / 1.4 / 0.5" in output


def test_parse_run_options_rejects_unknown_hdr_merge_backend() -> None:
    """Parser must reject unknown `--hdr-merge` selector values."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1", "--hdr-merge=unknown-backend"]
    )
    assert parsed is None


def test_parse_run_options_auto_ev_defaults_and_explicit_ev_auto() -> None:
    """Auto exposure must default to enabled and be selectable by `--bracketing=auto`."""

    parsed_default_auto = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg"]
    )
    assert parsed_default_auto is not None
    assert parsed_default_auto[2] is None
    assert parsed_default_auto[3] is True
    auto_ev_options = parsed_default_auto[13]
    assert auto_ev_options.shadow_clipping_pct == 20.0
    assert auto_ev_options.highlight_clipping_pct == 20.0

    parsed_explicit_auto = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=auto"]
    )
    assert parsed_explicit_auto is not None
    assert parsed_explicit_auto[2] == 0.1
    assert parsed_explicit_auto[3] is False


def test_parse_run_options_rejects_removed_auto_ev_option(capsys) -> None:
    """Legacy `--auto-ev` must be rejected as removed option."""

    parsed_conflict = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--auto-ev=enable"]
    )
    assert parsed_conflict is None
    captured = capsys.readouterr()
    assert "Removed option: --auto-ev" in captured.err


def test_parse_run_options_static_ev_defaults_ev_zero_to_zero_with_unspecified_flag() -> None:
    """Static `--ev` without `--exposure` must preserve the unset manual-center flag."""

    parsed_static = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1.25"]
    )
    assert parsed_static is not None
    assert parsed_static[2] == 1.2
    assert parsed_static[3] is False
    assert parsed_static[11] == 0.0
    assert parsed_static[12] is True


def test_parse_run_options_static_ev_preserves_manual_ev_zero() -> None:
    """Static `--ev` with `--exposure` must preserve the manual center and flag."""

    parsed_static = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1.25", "--exposure=0.5"]
    )
    assert parsed_static is not None
    assert parsed_static[2] == 1.2
    assert parsed_static[3] is False
    assert parsed_static[11] == 0.5
    assert parsed_static[12] is False


def test_parse_run_options_rejects_ev_zero_without_ev(capsys) -> None:
    """`--exposure` must require static `--ev` mode."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--exposure=0.5"]
    )
    assert parsed is None
    captured = capsys.readouterr()
    assert "--exposure requires numeric --bracketing value" in captured.err


def test_parse_run_options_last_exposure_auto_overrides_previous_manual_value() -> None:
    """The last `--exposure=auto` must restore auto ev-zero mode and clear stale manual center."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--exposure=0.5", "--exposure=auto"]
    )
    assert parsed is not None
    assert parsed[3] is True
    assert parsed[11] == 0.0
    assert parsed[12] is True


def test_parse_run_options_last_exposure_auto_keeps_static_bracketing() -> None:
    """`--exposure=auto` must keep static bracketing when `--bracketing=<value>` is set."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1.2",
            "--exposure=0.5",
            "--exposure=auto",
        ]
    )
    assert parsed is not None
    assert parsed[2] == 1.2
    assert parsed[3] is False
    assert parsed[11] == 0.0
    assert parsed[12] is True


def test_parse_run_options_rejects_removed_auto_zero_options(capsys) -> None:
    """Removed auto-zero CLI options must fail explicitly."""

    parsed_auto_zero = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--auto-zero=enable"]
    )
    assert parsed_auto_zero is None
    captured = capsys.readouterr()
    assert "Removed option: --auto-zero" in captured.err

    parsed_auto_zero_pct = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--auto-zero-pct=50"]
    )
    assert parsed_auto_zero_pct is None
    captured = capsys.readouterr()
    assert "Removed option: --auto-zero-pct" in captured.err


def test_parse_run_options_accepts_new_auto_ev_clipping_options() -> None:
    """Parser must accept the new automatic clipping thresholds and step."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=auto",
            "--auto-ev-shadow-clipping=4",
            "--auto-ev-highlight-clipping=6",
            "--auto-ev-step=0.2",
        ]
    )
    assert parsed is not None
    auto_ev_options = parsed[13]
    assert auto_ev_options.shadow_clipping_pct == 4.0
    assert auto_ev_options.highlight_clipping_pct == 6.0
    assert auto_ev_options.step == 0.2


def test_parse_run_options_requires_explicit_auto_brightness_value() -> None:
    """`--auto-brightness` must require explicit enable/disable value."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--auto-brightness"]
    )
    assert parsed is None


def test_parse_run_options_requires_explicit_auto_levels_value() -> None:
    """`--auto-levels` must require explicit enable/disable value."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--auto-levels"]
    )
    assert parsed is None


def test_parse_run_options_defaults_enable_auto_adjust() -> None:
    """Auto-adjust must default to enabled when omitted."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg"]
    )
    assert parsed is not None
    assert parsed[4].auto_brightness_enabled is False
    assert parsed[4].auto_levels_enabled is True
    assert parsed[4].auto_adjust_enabled is True


def test_parse_run_options_disables_auto_adjust_and_rejects_knobs() -> None:
    """Disabled auto-adjust must reject any `--aa-*` knob overrides."""

    parsed_disabled = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--auto-adjust=disable"]
    )
    assert parsed_disabled is not None
    assert parsed_disabled[4].auto_adjust_enabled is False

    parsed_with_knob = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--auto-adjust=disable",
            "--aa-clahe-clip-limit=1.7",
        ]
    )
    assert parsed_with_knob is None


def test_parse_run_options_enables_debug_flag() -> None:
    """Parser must accept `--debug` without changing backend parsing."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--hdr-merge=OpenCV-Merge",
            "--debug",
        ]
    )

    assert parsed is not None
    assert parsed[4].debug_enabled is True
    assert parsed[6] is True


def test_collect_missing_external_executables_reports_luminance_dependency(
    monkeypatch,
) -> None:
    """Luminance backend preflight must report missing `luminance-hdr-cli`."""

    monkeypatch.setattr(dng2jpg_module.shutil, "which", lambda _cmd: None)
    missing = dng2jpg_module._collect_missing_external_executables(  # pylint: disable=protected-access
        enable_luminance=True,
    )
    assert missing == ("luminance-hdr-cli",)


def test_collect_processing_errors_includes_overflowerror() -> None:
    """Recoverable processing errors must include `OverflowError` safety guard."""

    class _RawpyWithoutCustomErrors:
        """Minimal rawpy stub exposing no optional LibRaw exception subclasses."""

    processing_errors = dng2jpg_module._collect_processing_errors(  # pylint: disable=protected-access
        rawpy_module=_RawpyWithoutCustomErrors(),
    )

    assert OverflowError in processing_errors


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
        np.array([2 ** 0.5, 2.0, 2 ** 1.5], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )


def test_build_exposure_multipliers_rejects_overflowing_ev_scaling() -> None:
    """Static EV multipliers must fail fast on non-representable `2**EV` values."""

    try:
        dng2jpg_module._build_exposure_multipliers(  # pylint: disable=protected-access
            ev_value=1024.0,
            ev_zero=0.0,
        )
    except ValueError as error:
        assert "EV scaling failed [exposure_multipliers_ev_plus]" in str(error)
    else:
        raise AssertionError("Expected ValueError for overflowing exposure multipliers")


def test_build_opencv_radiance_exposure_times_rejects_overflowing_ev_scaling() -> None:
    """OpenCV radiance exposure times must fail fast on overflowed EV scaling."""

    try:
        dng2jpg_module._build_opencv_radiance_exposure_times(  # pylint: disable=protected-access
            source_exposure_time_seconds=1.0,
            ev_zero=1024.0,
            ev_delta=0.0,
        )
    except ValueError as error:
        assert "EV scaling failed [opencv_radiance_times_ev_minus]" in str(error)
    else:
        raise AssertionError("Expected ValueError for overflowing OpenCV radiance times")


def test_run_luminance_hdr_cli_prints_full_command_syntax(
    monkeypatch, tmp_path, capsys
) -> None:
    """Luminance backend must log the full external command syntax with parameters."""

    bracket_images_float = [
        np.full((1, 1, 3), 0.1, dtype=np.float32),
        np.full((1, 1, 3), 0.5, dtype=np.float32),
        np.full((1, 1, 3), 0.9, dtype=np.float32),
    ]
    imageio_module = _FakeImageIoModule(
        merged_rgb_u16=np.full((1, 1, 3), 32768, dtype=np.uint16)
    )

    recorded_command: list[str] = []

    def _fake_subprocess_run(command: list[str], check: bool) -> None:
        del check  # Unused by deterministic subprocess stub.
        recorded_command[:] = list(command)

    monkeypatch.setattr(
        dng2jpg_module.subprocess,
        "run",
        _fake_subprocess_run,
    )

    output = dng2jpg_module._run_luminance_hdr_cli(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        temp_dir=tmp_path,
        imageio_module=imageio_module,
        np_module=np,
        ev_value=1.0,
        ev_zero=0.0,
        luminance_options=dng2jpg_module.LuminanceOptions(
            hdr_model="debevec",
            hdr_weight="flat",
            hdr_response_curve="linear",
            tmo="mantiuk08",
            tmo_extra_args=("--tmoFerRho", "0.4"),
        ),
    )

    captured = capsys.readouterr().out
    assert "Luminance-HDR command: luminance-hdr-cli" in captured
    assert "-e -1,0,1" in captured
    assert "-g 1" in captured
    assert "-S 1" in captured
    assert "-G 1" in captured
    assert "--hdrModel debevec" in captured
    assert "--hdrWeight flat" in captured
    assert "--hdrResponseCurve linear" in captured
    assert "--tmo mantiuk08" in captured
    assert "--ldrTiff 32b" in captured
    assert "--tmoFerRho 0.4" in captured
    assert "-o" in captured
    assert "ev_minus.tif" in captured
    assert "ev_zero.tif" in captured
    assert "ev_plus.tif" in captured
    assert recorded_command[:13] == [
        "luminance-hdr-cli",
        "-e",
        "-1,0,1",
        "-g",
        "1",
        "-S",
        "1",
        "-G",
        "1",
        "--hdrModel",
        "debevec",
        "--hdrWeight",
        "flat",
    ]
    assert "--hdrResponseCurve" in recorded_command
    assert recorded_command[recorded_command.index("--hdrResponseCurve") + 1] == "linear"
    assert output.shape == (1, 1, 3)


def test_run_luminance_hdr_cli_normalizes_float_tiff_output(
    monkeypatch,
    tmp_path,
) -> None:
    """Luminance backend must normalize float TIFF output before postprocess handoff."""

    bracket_images_float = [
        np.full((1, 1, 3), 0.1, dtype=np.float32),
        np.full((1, 1, 3), 0.5, dtype=np.float32),
        np.full((1, 1, 3), 0.9, dtype=np.float32),
    ]
    imageio_module = _FakeImageIoModule(
        merged_rgb_u16=np.array([[[-0.5, 0.5, 1.5]]], dtype=np.float32)
    )

    monkeypatch.setattr(
        dng2jpg_module.subprocess,
        "run",
        lambda command, check: (command, check),
    )

    output = dng2jpg_module._run_luminance_hdr_cli(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        temp_dir=tmp_path,
        imageio_module=imageio_module,
        np_module=np,
        ev_value=1.0,
        ev_zero=0.0,
        luminance_options=dng2jpg_module.LuminanceOptions(
            hdr_model="debevec",
            hdr_weight="flat",
            hdr_response_curve="linear",
            tmo="mantiuk08",
            tmo_extra_args=(),
        ),
    )

    np.testing.assert_allclose(
        output,
        np.array([[[0.0, 0.5, 1.0]]], dtype=np.float32),
        rtol=0.0,
        atol=1e-7,
    )


def test_parse_run_options_rejects_non_linear_luminance_response_curve(capsys) -> None:
    """Luminance response-curve parser must reject non-linear command overrides."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--hdr-merge=Luminace-HDR",
            "--luminance-hdr-response-curve=srgb",
        ]
    )

    assert parsed is None
    captured = capsys.readouterr()
    assert (
        "--luminance-hdr-response-curve only accepts `linear`" in captured.err
        or "--luminance-hdr-response-curve only accepts `linear`" in captured.out
    )


def test_extract_dng_exif_payload_and_timestamp_reads_datetime_priority_and_exposure_time() -> None:
    """EXIF extraction must prioritize datetime tags and parse exposure time seconds."""

    fake_exif = _FakeExifData(
        {
            dng2jpg_module._EXIF_TAG_DATETIME_ORIGINAL: b"2024:01:02 03:04:05",  # pylint: disable=protected-access
            dng2jpg_module._EXIF_TAG_DATETIME_DIGITIZED: b"2023:01:01 00:00:00",  # pylint: disable=protected-access
            dng2jpg_module._EXIF_TAG_ORIENTATION: 6,  # pylint: disable=protected-access
            dng2jpg_module._EXIF_TAG_EXPOSURE_TIME: _FakeExifRatio(1, 8),  # pylint: disable=protected-access
        }
    )
    payload, timestamp, orientation, exposure_time_seconds = (
        dng2jpg_module._extract_dng_exif_payload_and_timestamp(  # pylint: disable=protected-access
            pil_image_module=_FakeExifPilModule(fake_exif),
            input_dng=Path("input.dng"),
        )
    )

    assert payload == b"fake-exif"
    assert orientation == 6
    assert exposure_time_seconds == 0.125
    assert timestamp is not None


def test_extract_dng_exif_payload_and_timestamp_reads_nested_exif_ifd_exposure_time() -> None:
    """Nested EXIF IFD exposure time must be accepted when top-level EXIF omits it."""

    fake_exif = _FakeExifData(
        {
            dng2jpg_module._EXIF_TAG_DATETIME: b"2024:01:02 03:04:05",  # pylint: disable=protected-access
            dng2jpg_module._EXIF_TAG_ORIENTATION: 6,  # pylint: disable=protected-access
        },
        ifd_values={
            34665: {
                dng2jpg_module._EXIF_TAG_DATETIME_ORIGINAL: b"2024:01:02 03:04:05",  # pylint: disable=protected-access
                dng2jpg_module._EXIF_TAG_EXPOSURE_TIME: _FakeExifRatio(1, 60),  # pylint: disable=protected-access
            }
        },
    )

    payload, timestamp, orientation, exposure_time_seconds = (
        dng2jpg_module._extract_dng_exif_payload_and_timestamp(  # pylint: disable=protected-access
            pil_image_module=_FakeExifPilModule(fake_exif),
            input_dng=Path("input.dng"),
        )
    )

    assert payload == b"fake-exif"
    assert orientation == 6
    assert exposure_time_seconds == 1.0 / 60.0
    assert timestamp is not None


def test_select_ev_zero_candidate_chooses_numeric_minimum() -> None:
    """Default ev-zero selection must choose the signed numeric minimum candidate."""

    selected_ev_zero, selected_source = dng2jpg_module._select_ev_zero_candidate(  # pylint: disable=protected-access
        evaluations=dng2jpg_module.AutoZeroEvaluation(
            ev_best=-1.2,
            ev_ettr=0.3,
            ev_detail=-0.4,
        ),
    )

    assert selected_ev_zero == -1.2
    assert selected_source == "ev_best"



def test_select_ev_zero_candidate_uses_unclamped_values() -> None:
    """Default ev-zero selection must compare raw candidate values without clamp."""

    selected_ev_zero, selected_source = dng2jpg_module._select_ev_zero_candidate(  # pylint: disable=protected-access
        evaluations=dng2jpg_module.AutoZeroEvaluation(
            ev_best=5.0,
            ev_ettr=2.0,
            ev_detail=3.0,
        ),
    )

    assert selected_ev_zero == 2.0
    assert selected_source == "ev_ettr"



def test_resolve_joint_auto_ev_solution_iterates_until_clipping_threshold() -> None:
    """Automatic EV planning must stop at the first step crossing either clipping threshold."""

    base_rgb_float = np.array([[[0.5, 0.5, 0.5], [0.25, 0.25, 0.25]]], dtype=np.float32)

    solution = dng2jpg_module._resolve_joint_auto_ev_solution(  # pylint: disable=protected-access
        auto_ev_options=dng2jpg_module.AutoEvOptions(
            shadow_clipping_pct=5.0,
            highlight_clipping_pct=5.0,
            step=0.5,
        ),
        auto_adjust_dependencies=(None, np),
        base_rgb_float=base_rgb_float,
    )

    assert solution.selected_source in {"ev_best", "ev_ettr", "ev_detail"}
    assert solution.ev_delta == 4.0
    assert [step.ev_delta for step in solution.iteration_steps] == [
        0.5,
        1.0,
        1.5,
        2.0,
        2.5,
        3.0,
        3.5,
        4.0,
    ]
    assert solution.iteration_steps[-1].highlight_clipping_pct >= 5.0



def test_measure_any_channel_clipping_percentages() -> None:
    """Clipping metrics must count any-channel threshold crossings in percent."""

    plus = np.array(
        [
            [[1.0, 0.2, 0.3], [0.1, 0.2, 0.3]],
            [[0.0, 0.0, 0.0], [1.2, 0.2, 0.3]],
        ],
        dtype=np.float32,
    )
    minus = np.array(
        [
            [[-0.1, 0.2, 0.3], [0.1, 0.2, 0.3]],
            [[0.0, 0.1, 0.2], [0.3, 0.4, 0.5]],
        ],
        dtype=np.float32,
    )

    assert dng2jpg_module._measure_any_channel_highlight_clipping_pct(np, plus) == 50.0  # pylint: disable=protected-access
    assert dng2jpg_module._measure_any_channel_shadow_clipping_pct(np, minus) == 50.0  # pylint: disable=protected-access



def test_run_opencv_merge_backend_keeps_mertens_inputs_as_float32() -> None:
    """OpenCV merge must feed Mertens with backend-local float32 images."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.array([[[2048, 1024, 0], [8192, 4096, 3072]]], dtype=np.float32) / 65535.0,
        np.array([[[36000, 24000, 12000], [3000, 2000, 1000]]], dtype=np.float32)
        / 65535.0,
        np.array([[[50000, 60000, 65535], [20000, 30000, 40000]]], dtype=np.float32)
        / 65535.0,
    ]

    output = dng2jpg_module._run_opencv_merge_backend(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        ev_value=1.0,
        ev_zero=0.0,
        source_exposure_time_seconds=0.125,
        opencv_merge_options=dng2jpg_module.OpenCvMergeOptions(
            merge_algorithm=dng2jpg_module.OPENCV_MERGE_ALGORITHM_MERTENS
        ),
        auto_adjust_dependencies=(fake_cv2, np),
    )

    assert fake_cv2.merge_mertens.last_inputs is not None
    assert all(
        frame.dtype == np.float32 for frame in fake_cv2.merge_mertens.last_inputs
    ), "Mertens input must stay on float32 for OpenCV float-path compatibility"
    assert all(
        float(np.min(frame)) >= 0.0 and float(np.max(frame)) <= 1.0
        for frame in fake_cv2.merge_mertens.last_inputs
    ), "Mertens input must stay on normalized OpenCV-compatible float scale"
    assert fake_cv2.merge_debevec.last_inputs is None
    assert output.dtype == np.float32
    assert float(np.min(output)) >= 0.0
    assert float(np.max(output)) <= 1.0


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


def test_parse_run_options_accepts_opencv_controls_and_defaults() -> None:
    """Parser must expose OpenCV algorithm and tone-map controls with defaults."""

    parsed_default = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1", "--hdr-merge=OpenCV-Merge"]
    )
    assert parsed_default is not None
    default_options = parsed_default[8]
    assert default_options == dng2jpg_module.OpenCvMergeOptions(
        merge_algorithm=dng2jpg_module.OPENCV_MERGE_ALGORITHM_DEBEVEC,
        tonemap_enabled=True,
        tonemap_gamma=1.0,
    )

    parsed_override = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--hdr-merge=OpenCV-Merge",
            "--opencv-merge-algorithm=Debevec",
            "--opencv-merge-tonemap=off",
            "--opencv-merge-tonemap-gamma=2.2",
        ]
    )
    assert parsed_override is not None
    override_options = parsed_override[8]
    assert override_options == dng2jpg_module.OpenCvMergeOptions(
        merge_algorithm=dng2jpg_module.OPENCV_MERGE_ALGORITHM_DEBEVEC,
        tonemap_enabled=False,
        tonemap_gamma=2.2,
    )


def test_parse_run_options_rejects_invalid_opencv_controls() -> None:
    """Parser must reject invalid OpenCV algorithm, tone-map, and coupling values."""

    invalid_algorithm = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--hdr-merge=OpenCV-Merge",
            "--opencv-merge-algorithm=unknown",
        ]
    )
    assert invalid_algorithm is None

    invalid_tonemap = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--hdr-merge=OpenCV-Merge",
            "--opencv-merge-tonemap=maybe",
        ]
    )
    assert invalid_tonemap is None

    invalid_coupling = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--hdr-merge=HDR-Plus",
            "--opencv-merge-tonemap=on",
        ]
    )
    assert invalid_coupling is None


def test_parse_run_options_rejects_tonemap_options_without_opencv_tonemap_backend() -> None:
    """Parser must reject OpenCV-Tonemap options outside OpenCV-Tonemap backend."""

    invalid_selector = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--hdr-merge=OpenCV-Merge",
            "--opencv-tonemap-algorithm=drago",
        ]
    )
    assert invalid_selector is None

    invalid_knob = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--hdr-merge=OpenCV-Merge",
            "--opencv-tonemap-drago-saturation=1.2",
        ]
    )
    assert invalid_knob is None

    invalid_map_knob = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--hdr-merge=OpenCV-Tonemap",
            "--opencv-tonemap-algorithm=drago",
            "--opencv-tonemap-reinhard-intensity=0.2",
        ]
    )
    assert invalid_map_knob is None


def test_parse_run_options_accepts_post_gamma_auto_and_knobs() -> None:
    """Parser must accept `--post-gamma=auto` and parse auto-gamma knobs."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--post-gamma=auto",
            "--post-gamma-auto-target-gray=0.42",
            "--post-gamma-auto-luma-min=0.02",
            "--post-gamma-auto-luma-max=0.95",
            "--post-gamma-auto-lut-size=1024",
        ]
    )
    assert parsed is not None
    postprocess_options = parsed[4]
    assert postprocess_options.post_gamma_mode == "auto"
    assert postprocess_options.post_gamma_auto_options == dng2jpg_module.PostGammaAutoOptions(
        target_gray=0.42,
        luma_min=0.02,
        luma_max=0.95,
        lut_size=1024,
    )


def test_parse_run_options_rejects_post_gamma_auto_knobs_without_auto() -> None:
    """Parser must reject `--post-gamma-auto-*` options without `--post-gamma=auto`."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--post-gamma=1.2",
            "--post-gamma-auto-target-gray=0.42",
        ]
    )
    assert parsed is None


def test_run_opencv_merge_backend_dispatches_debevec_uint8_radiance_path_with_tonemap() -> None:
    """OpenCV Debevec radiance path must quantize locally and return float output."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((1, 2, 3), 0.125, dtype=np.float32),
        np.full((1, 2, 3), 0.5, dtype=np.float32),
        np.full((1, 2, 3), 0.875, dtype=np.float32),
    ]

    output = dng2jpg_module._run_opencv_merge_backend(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        ev_value=1.0,
        ev_zero=1.5,
        source_exposure_time_seconds=0.125,
        opencv_merge_options=dng2jpg_module.OpenCvMergeOptions(
            merge_algorithm=dng2jpg_module.OPENCV_MERGE_ALGORITHM_DEBEVEC,
            tonemap_enabled=True,
            tonemap_gamma=1.0,
        ),
        auto_adjust_dependencies=(fake_cv2, np),
    )

    assert fake_cv2.calibrate_debevec.last_inputs is not None
    assert fake_cv2.merge_debevec.last_inputs is not None
    assert fake_cv2.merge_robertson.last_inputs is None
    assert fake_cv2.last_tonemap is not None
    assert all(
        frame.dtype == np.uint8 for frame in fake_cv2.calibrate_debevec.last_inputs
    )
    np.testing.assert_allclose(
        fake_cv2.merge_debevec.last_times,
        np.array([0.17677669, 0.35355338, 0.70710677], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )
    np.testing.assert_array_equal(
        fake_cv2.calibrate_debevec.last_inputs[1],
        np.full((1, 2, 3), 128, dtype=np.uint8),
    )
    assert fake_cv2.merge_debevec.last_response is not None
    assert all(
        frame.dtype == np.uint8 for frame in fake_cv2.merge_debevec.last_inputs
    )
    np.testing.assert_array_equal(
        fake_cv2.merge_debevec.last_inputs[1],
        np.full((1, 2, 3), 128, dtype=np.uint8),
    )
    assert fake_cv2.last_tonemap.gamma == 1.0
    assert output.dtype == np.float32
    assert float(np.min(output)) >= 0.0
    assert float(np.max(output)) <= 1.0


def test_run_opencv_merge_backend_dispatches_robertson_uint8_radiance_path() -> None:
    """OpenCV Robertson radiance path must quantize locally and return float output."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((1, 1, 3), 0.2, dtype=np.float32),
        np.full((1, 1, 3), 0.4, dtype=np.float32),
        np.full((1, 1, 3), 0.8, dtype=np.float32),
    ]

    output = dng2jpg_module._run_opencv_merge_backend(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        ev_value=0.5,
        ev_zero=-0.5,
        source_exposure_time_seconds=0.125,
        opencv_merge_options=dng2jpg_module.OpenCvMergeOptions(
            merge_algorithm=dng2jpg_module.OPENCV_MERGE_ALGORITHM_ROBERTSON,
            tonemap_enabled=False,
            tonemap_gamma=1.7,
        ),
        auto_adjust_dependencies=(fake_cv2, np),
    )

    assert fake_cv2.calibrate_robertson.last_inputs is not None
    assert fake_cv2.merge_robertson.last_inputs is not None
    assert fake_cv2.merge_debevec.last_inputs is None
    assert fake_cv2.last_tonemap is None
    assert all(
        frame.dtype == np.uint8 for frame in fake_cv2.calibrate_robertson.last_inputs
    )
    np.testing.assert_allclose(
        fake_cv2.merge_robertson.last_times,
        np.array([0.0625, 0.08838835, 0.125], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )
    np.testing.assert_array_equal(
        fake_cv2.calibrate_robertson.last_inputs[1],
        np.full((1, 1, 3), 102, dtype=np.uint8),
    )
    assert fake_cv2.merge_robertson.last_response is not None
    assert all(
        frame.dtype == np.uint8 for frame in fake_cv2.merge_robertson.last_inputs
    )
    np.testing.assert_array_equal(
        fake_cv2.merge_robertson.last_inputs[1],
        np.full((1, 1, 3), 102, dtype=np.uint8),
    )
    assert output.dtype == np.float32
    assert float(np.min(output)) >= 0.0
    assert float(np.max(output)) <= 1.0


def test_run_opencv_merge_backend_applies_tonemap_for_mertens_when_enabled() -> None:
    """Mertens path must instantiate OpenCV tonemap when explicitly enabled."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((1, 1, 3), 0.1, dtype=np.float32),
        np.full((1, 1, 3), 0.3, dtype=np.float32),
        np.full((1, 1, 3), 0.6, dtype=np.float32),
    ]

    _ = dng2jpg_module._run_opencv_merge_backend(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        ev_value=1.0,
        ev_zero=0.0,
        source_exposure_time_seconds=0.125,
        opencv_merge_options=dng2jpg_module.OpenCvMergeOptions(
            merge_algorithm=dng2jpg_module.OPENCV_MERGE_ALGORITHM_MERTENS,
            tonemap_enabled=True,
            tonemap_gamma=0.8,
        ),
        auto_adjust_dependencies=(fake_cv2, np),
    )

    assert fake_cv2.last_tonemap is not None
    assert fake_cv2.last_tonemap.gamma == 0.8
    assert fake_cv2.merge_mertens.last_inputs is not None
    assert fake_cv2.merge_debevec.last_inputs is None
    assert fake_cv2.merge_robertson.last_inputs is None


def test_run_opencv_merge_backend_skips_tonemap_for_mertens_when_disabled() -> None:
    """Mertens path must skip OpenCV tonemap when explicitly disabled."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((1, 1, 3), 0.1, dtype=np.float32),
        np.full((1, 1, 3), 0.3, dtype=np.float32),
        np.full((1, 1, 3), 0.6, dtype=np.float32),
    ]

    _ = dng2jpg_module._run_opencv_merge_backend(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        ev_value=1.0,
        ev_zero=0.0,
        source_exposure_time_seconds=0.125,
        opencv_merge_options=dng2jpg_module.OpenCvMergeOptions(
            merge_algorithm=dng2jpg_module.OPENCV_MERGE_ALGORITHM_MERTENS,
            tonemap_enabled=False,
            tonemap_gamma=2.2,
        ),
        auto_adjust_dependencies=(fake_cv2, np),
    )

    assert fake_cv2.last_tonemap is None
    assert fake_cv2.merge_mertens.last_inputs is not None
    assert fake_cv2.merge_debevec.last_inputs is None
    assert fake_cv2.merge_robertson.last_inputs is None


def test_run_opencv_tonemap_backend_uses_ev_zero_only() -> None:
    """OpenCV-Tonemap backend must consume only bracket index 1 (ev_zero)."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((1, 1, 3), 10.0, dtype=np.float32),
        np.full((1, 1, 3), 2.0, dtype=np.float32),
        np.full((1, 1, 3), 99.0, dtype=np.float32),
    ]

    result = dng2jpg_module._run_opencv_tonemap_backend(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        opencv_tonemap_options=dng2jpg_module.OpenCvTonemapOptions(
            tonemap_map="drago"
        ),
        auto_adjust_dependencies=(fake_cv2, np),
        resolved_merge_gamma=dng2jpg_module.ResolvedMergeGamma(
            request=dng2jpg_module.MergeGammaOption(mode="auto"),
            transfer="linear",
            label="Linear",
            param_a=None,
            param_b=None,
            evidence="default-linear",
        ),
    )
    assert fake_cv2.last_tonemap_drago is not None
    np.testing.assert_allclose(
        fake_cv2.last_tonemap_drago.last_input,
        np.full((1, 1, 3), 2.0, dtype=np.float32),
        rtol=0.0,
        atol=0.0,
    )
    assert float(np.max(result)) < 10.0


def test_run_opencv_tonemap_backend_dispatches_algorithms_with_fixed_gamma() -> None:
    """OpenCV-Tonemap backend must dispatch drago/reinhard/mantiuk with gamma inverse."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((2, 2, 3), 0.2, dtype=np.float32),
        np.full((2, 2, 3), 0.4, dtype=np.float32),
        np.full((2, 2, 3), 0.6, dtype=np.float32),
    ]

    drago_result = dng2jpg_module._run_opencv_tonemap_backend(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        opencv_tonemap_options=dng2jpg_module.OpenCvTonemapOptions(
            tonemap_map="drago",
            drago_saturation=1.2,
            drago_bias=0.8,
        ),
        auto_adjust_dependencies=(fake_cv2, np),
        resolved_merge_gamma=dng2jpg_module.ResolvedMergeGamma(
            request=dng2jpg_module.MergeGammaOption(mode="auto"),
            transfer="srgb",
            label="sRGB",
            param_a=None,
            param_b=None,
            evidence="exif-colorspace=1",
        ),
    )
    assert fake_cv2.last_tonemap_drago is not None
    assert abs(fake_cv2.last_tonemap_drago.params["gamma"] - (1.0 / 2.4)) < 1e-9
    np.testing.assert_allclose(
        drago_result,
        np.full((2, 2, 3), 0.9063318, dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )

    reinhard_result = dng2jpg_module._run_opencv_tonemap_backend(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        opencv_tonemap_options=dng2jpg_module.OpenCvTonemapOptions(
            tonemap_map="reinhard",
            reinhard_intensity=0.2,
            reinhard_light_adapt=0.3,
            reinhard_color_adapt=0.1,
        ),
        auto_adjust_dependencies=(fake_cv2, np),
        resolved_merge_gamma=dng2jpg_module.ResolvedMergeGamma(
            request=dng2jpg_module.MergeGammaOption(mode="auto"),
            transfer="power",
            label="Adobe RGB",
            param_a=2.19921875,
            param_b=None,
            evidence="exif-adobe-rgb",
        ),
    )
    assert fake_cv2.last_tonemap_reinhard is not None
    assert abs(fake_cv2.last_tonemap_reinhard.params["gamma"] - (1.0 / 2.19921875)) < 1e-9
    np.testing.assert_allclose(
        reinhard_result,
        np.full((2, 2, 3), 0.8826837, dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )

    mantiuk_result = dng2jpg_module._run_opencv_tonemap_backend(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        opencv_tonemap_options=dng2jpg_module.OpenCvTonemapOptions(
            tonemap_map="mantiuk",
            mantiuk_scale=0.75,
            mantiuk_saturation=1.1,
        ),
        auto_adjust_dependencies=(fake_cv2, np),
        resolved_merge_gamma=dng2jpg_module.ResolvedMergeGamma(
            request=dng2jpg_module.MergeGammaOption(mode="auto"),
            transfer="srgb",
            label="sRGB",
            param_a=None,
            param_b=None,
            evidence="unresolved-default-srgb",
        ),
    )
    assert fake_cv2.last_tonemap_mantiuk is not None
    assert abs(fake_cv2.last_tonemap_mantiuk.params["gamma"] - (1.0 / 2.4)) < 1e-9
    np.testing.assert_allclose(
        mantiuk_result,
        np.full((2, 2, 3), 0.6097116, dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )


def test_run_opencv_tonemap_backend_applies_merge_gamma_last() -> None:
    """OpenCV-Tonemap backend must apply merge gamma only after tone mapping."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((1, 1, 3), 0.1, dtype=np.float32),
        np.full((1, 1, 3), 0.4, dtype=np.float32),
        np.full((1, 1, 3), 0.8, dtype=np.float32),
    ]

    result = dng2jpg_module._run_opencv_tonemap_backend(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        opencv_tonemap_options=dng2jpg_module.OpenCvTonemapOptions(
            tonemap_map="drago",
            drago_saturation=1.0,
            drago_bias=0.0,
        ),
        auto_adjust_dependencies=(fake_cv2, np),
        resolved_merge_gamma=dng2jpg_module.ResolvedMergeGamma(
            request=dng2jpg_module.MergeGammaOption(
                mode="custom",
                linear_coeff=4.5,
                exponent=0.5,
            ),
            transfer="rec709",
            label="Rec.709 custom",
            param_a=4.5,
            param_b=0.5,
            evidence="cli-custom",
        ),
    )
    np.testing.assert_allclose(
        result,
        np.full((1, 1, 3), 0.596, dtype=np.float32),
        rtol=1e-4,
        atol=1e-4,
    )


def test_run_opencv_tonemap_backend_preserves_dynamic_range_without_clipping() -> None:
    """OpenCV-Tonemap backend must preserve out-of-range float values without clipping."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((1, 1, 3), 0.1, dtype=np.float32),
        np.full((1, 1, 3), 2.0, dtype=np.float32),
        np.full((1, 1, 3), 0.9, dtype=np.float32),
    ]

    result = dng2jpg_module._run_opencv_tonemap_backend(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        opencv_tonemap_options=dng2jpg_module.OpenCvTonemapOptions(
            tonemap_map="reinhard",
            reinhard_intensity=1.0,
            reinhard_light_adapt=1.0,
            reinhard_color_adapt=1.0,
        ),
        auto_adjust_dependencies=(fake_cv2, np),
        resolved_merge_gamma=dng2jpg_module.ResolvedMergeGamma(
            request=dng2jpg_module.MergeGammaOption(mode="auto"),
            transfer="linear",
            label="Linear",
            param_a=None,
            param_b=None,
            evidence="default-linear",
        ),
    )
    assert result.dtype == np.float32
    assert float(result[0, 0, 0]) > 1.0


def test_run_opencv_tonemap_backend_sanitizes_non_finite_outputs_for_all_algorithms() -> None:
    """OpenCV-Tonemap backend must sanitize non-finite outputs for every selector."""

    class _FakeNonFiniteAdvancedTonemap(_FakeAdvancedTonemap):
        """Fake tonemap that always returns non-finite payload values."""

        def __init__(self, kind: str) -> None:
            super().__init__(kind=kind, gamma=1.0)

        def process(self, image: np.ndarray) -> np.ndarray:
            del image
            return np.array([[[np.nan, np.inf, -np.inf]]], dtype=np.float32)

    class _FakeNonFiniteOpenCvModule(_FakeOpenCvModule):
        """OpenCV shim that emits non-finite payloads on all advanced tonemap paths."""

        def createTonemapDrago(
            self,
            *,
            gamma: float,
            saturation: float,
            bias: float,
        ) -> _FakeAdvancedTonemap:
            del gamma, saturation, bias
            return _FakeNonFiniteAdvancedTonemap(kind="drago")

        def createTonemapReinhard(
            self,
            *,
            gamma: float,
            intensity: float,
            light_adapt: float,
            color_adapt: float,
        ) -> _FakeAdvancedTonemap:
            del gamma, intensity, light_adapt, color_adapt
            return _FakeNonFiniteAdvancedTonemap(kind="reinhard")

        def createTonemapMantiuk(
            self,
            *,
            gamma: float,
            scale: float,
            saturation: float,
        ) -> _FakeAdvancedTonemap:
            del gamma, scale, saturation
            return _FakeNonFiniteAdvancedTonemap(kind="mantiuk")

    fake_cv2 = _FakeNonFiniteOpenCvModule()
    bracket_images_float = [
        np.full((1, 1, 3), 0.1, dtype=np.float32),
        np.full((1, 1, 3), 0.5, dtype=np.float32),
        np.full((1, 1, 3), 0.9, dtype=np.float32),
    ]
    options_list = (
        dng2jpg_module.OpenCvTonemapOptions(tonemap_map="drago"),
        dng2jpg_module.OpenCvTonemapOptions(tonemap_map="reinhard"),
        dng2jpg_module.OpenCvTonemapOptions(tonemap_map="mantiuk"),
    )

    for tonemap_options in options_list:
        result = dng2jpg_module._run_opencv_tonemap_backend(  # pylint: disable=protected-access
            bracket_images_float=bracket_images_float,
            opencv_tonemap_options=tonemap_options,
            auto_adjust_dependencies=(fake_cv2, np),
            resolved_merge_gamma=dng2jpg_module.ResolvedMergeGamma(
                request=dng2jpg_module.MergeGammaOption(mode="auto"),
                transfer="linear",
                label="Linear",
                param_a=None,
                param_b=None,
                evidence="default-linear",
            ),
        )
        assert result.shape == (1, 1, 3)
        assert result.dtype == np.float32
        assert bool(np.all(np.isfinite(result)))
        np.testing.assert_allclose(
            result,
            np.zeros((1, 1, 3), dtype=np.float32),
            rtol=0.0,
            atol=0.0,
        )


def test_to_uint16_image_array_replaces_non_finite_without_runtime_warning() -> None:
    """`_to_uint16_image_array` must clear non-finite values without warnings."""

    source = np.array([[np.nan]], dtype=np.float32)

    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        converted = dng2jpg_module._to_uint16_image_array(  # pylint: disable=protected-access
            np_module=np,
            image_data=source,
        )

    assert converted.dtype == np.uint16
    np.testing.assert_array_equal(converted, np.array([[0]], dtype=np.uint16))


def test_extract_bracket_images_float_uses_single_linear_base_pass() -> None:
    """Bracket extraction must use one neutral RAW pass plus mode-normalized WB base."""

    base_rgb_u16 = np.array(
        [
            [[1000, 2000, 4000], [8000, 12000, 16000]],
            [[20000, 24000, 28000], [32000, 36000, 40000]],
        ],
        dtype=np.uint16,
    )

    class _FakeRawHandle:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []
            self.camera_whitebalance = (1.6, 1.0, 1.4, 0.0)
            self.white_level = 16383
            self.black_level_per_channel = (127.0, 125.0, 128.0, 126.0)

        def postprocess(
            self,
            *,
            output_bps,
            use_camera_wb,
            no_auto_bright,
            gamma,
            user_wb,
            output_color,
            no_auto_scale,
            user_flip,
        ) -> np.ndarray:
            self.calls.append(
                {
                    "output_bps": output_bps,
                    "use_camera_wb": use_camera_wb,
                    "no_auto_bright": no_auto_bright,
                    "gamma": gamma,
                    "user_wb": list(user_wb),
                    "output_color": output_color,
                    "no_auto_scale": no_auto_scale,
                    "user_flip": user_flip,
                }
            )
            return np.array(base_rgb_u16, copy=True)

    fake_raw = _FakeRawHandle()
    multipliers = (0.5, 1.0, 2.0)

    bracket_images = dng2jpg_module._extract_bracket_images_float(  # pylint: disable=protected-access
        raw_handle=fake_raw,
        np_module=np,
        multipliers=multipliers,
    )

    assert len(fake_raw.calls) == 1
    assert fake_raw.calls[0] == {
        "output_bps": 16,
        "use_camera_wb": False,
        "no_auto_bright": True,
        "gamma": (1.0, 1.0),
        "user_wb": [1.0, 1.0, 1.0, 1.0],
        "output_color": fake_raw.calls[0]["output_color"],
        "no_auto_scale": True,
        "user_flip": 0,
    }
    assert fake_raw.calls[0]["output_color"] is not None
    dynamic_range_max = np.float32(
        float(fake_raw.white_level) - float(np.mean(np.array(fake_raw.black_level_per_channel)))
    )
    base_rgb_float = base_rgb_u16.astype(np.float32) / dynamic_range_max
    mean_coefficient = np.float32(np.mean(np.array([1.6, 1.0, 1.4], dtype=np.float32)))
    normalized_gains = np.array([1.6, 1.0, 1.4], dtype=np.float32) / mean_coefficient
    balanced_base = base_rgb_float * normalized_gains.reshape((1, 1, 3))
    for bracket_image, multiplier in zip(bracket_images, multipliers):
        np.testing.assert_allclose(
            bracket_image,
            np.clip(balanced_base * multiplier, 0.0, 1.0).astype(np.float32),
            rtol=1e-6,
            atol=1e-6,
        )


def test_extract_base_rgb_linear_float_uses_neutral_raw_postprocess_and_normalized_camera_wb() -> None:
    """Base extraction must normalize by dynamic range then apply default MEAN WB."""

    base_rgb_u16 = np.array(
        [
            [[8000, 10000, 12000], [14000, 16000, 18000]],
            [[20000, 22000, 24000], [26000, 28000, 30000]],
        ],
        dtype=np.uint16,
    )

    class _FakeRawHandle:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []
            self.camera_whitebalance = (1.6, 1.0, 1.4, 0.0)
            self.white_level = 16383
            self.black_level_per_channel = (127.0, 125.0, 128.0, 126.0)

        def postprocess(
            self,
            *,
            output_bps,
            use_camera_wb,
            no_auto_bright,
            gamma,
            user_wb,
            output_color,
            no_auto_scale,
            user_flip,
        ) -> np.ndarray:
            self.calls.append(
                {
                    "output_bps": output_bps,
                    "use_camera_wb": use_camera_wb,
                    "no_auto_bright": no_auto_bright,
                    "gamma": gamma,
                    "user_wb": list(user_wb),
                    "output_color": output_color,
                    "no_auto_scale": no_auto_scale,
                    "user_flip": user_flip,
                }
            )
            return np.array(base_rgb_u16, copy=True)

    fake_raw = _FakeRawHandle()
    output = dng2jpg_module._extract_base_rgb_linear_float(  # pylint: disable=protected-access
        raw_handle=fake_raw,
        np_module=np,
    )

    assert len(fake_raw.calls) == 1
    assert fake_raw.calls[0] == {
        "output_bps": 16,
        "use_camera_wb": False,
        "no_auto_bright": True,
        "gamma": (1.0, 1.0),
        "user_wb": [1.0, 1.0, 1.0, 1.0],
        "output_color": fake_raw.calls[0]["output_color"],
        "no_auto_scale": True,
        "user_flip": 0,
    }
    assert fake_raw.calls[0]["output_color"] is not None
    dynamic_range_max = np.float32(
        float(fake_raw.white_level) - float(np.mean(np.array(fake_raw.black_level_per_channel)))
    )
    neutral_base = base_rgb_u16.astype(np.float32) / dynamic_range_max
    mean_coefficient = np.float32(np.mean(np.array([1.6, 1.0, 1.4], dtype=np.float32)))
    expected_gains = np.array([1.6, 1.0, 1.4], dtype=np.float32) / mean_coefficient
    expected = neutral_base * expected_gains.reshape((1, 1, 3))
    np.testing.assert_allclose(output, expected.astype(np.float32), rtol=1e-6, atol=1e-6)
    np.testing.assert_allclose(float(np.mean(expected_gains)), 1.0, rtol=1e-6, atol=1e-6)


def test_normalize_white_balance_gains_rgb_supports_all_modes() -> None:
    """WB normalization helper must apply GREEN/MAX/MIN/MEAN formulas."""

    camera_wb = (1.6, 1.0, 1.4)
    gains_green = dng2jpg_module._normalize_white_balance_gains_rgb(  # pylint: disable=protected-access
        np_module=np,
        camera_wb_rgb=camera_wb,
        raw_white_balance_mode="GREEN",
    )
    np.testing.assert_allclose(gains_green, np.array([1.6, 1.0, 1.4], dtype=np.float64))

    gains_max = dng2jpg_module._normalize_white_balance_gains_rgb(  # pylint: disable=protected-access
        np_module=np,
        camera_wb_rgb=camera_wb,
        raw_white_balance_mode="MAX",
    )
    np.testing.assert_allclose(gains_max, np.array([1.0, 0.625, 0.875], dtype=np.float64))
    np.testing.assert_allclose(float(np.max(gains_max)), 1.0, rtol=1e-12, atol=1e-12)

    gains_min = dng2jpg_module._normalize_white_balance_gains_rgb(  # pylint: disable=protected-access
        np_module=np,
        camera_wb_rgb=camera_wb,
        raw_white_balance_mode="MIN",
    )
    np.testing.assert_allclose(gains_min, np.array([1.6, 1.0, 1.4], dtype=np.float64))
    np.testing.assert_allclose(float(np.min(gains_min)), 1.0, rtol=1e-12, atol=1e-12)

    gains_mean = dng2jpg_module._normalize_white_balance_gains_rgb(  # pylint: disable=protected-access
        np_module=np,
        camera_wb_rgb=camera_wb,
        raw_white_balance_mode="MEAN",
    )
    np.testing.assert_allclose(gains_mean, np.array([1.2, 0.75, 1.05], dtype=np.float64))
    np.testing.assert_allclose(float(np.mean(gains_mean)), 1.0, rtol=1e-12, atol=1e-12)


def test_normalize_white_balance_gains_rgb_green_mode_accepts_non_unit_green() -> None:
    """GREEN mode must normalize by green coefficient without strict input check."""

    gains_green = dng2jpg_module._normalize_white_balance_gains_rgb(  # pylint: disable=protected-access
        np_module=np,
        camera_wb_rgb=(1.6, 1.1, 1.4),
        raw_white_balance_mode="GREEN",
    )
    np.testing.assert_allclose(
        gains_green,
        np.array([1.6 / 1.1, 1.0, 1.4 / 1.1], dtype=np.float64),
        rtol=1e-12,
        atol=1e-12,
    )
    np.testing.assert_allclose(float(gains_green[1]), 1.0, rtol=1e-12, atol=1e-12)


def test_parse_run_options_defaults_gamma_to_auto() -> None:
    """Parser must default merge gamma to automatic EXIF/source resolution."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1"]
    )

    assert parsed is not None
    assert parsed[4].merge_gamma_option == dng2jpg_module.MergeGammaOption(mode="auto")


def test_parse_run_options_accepts_custom_gamma() -> None:
    """Parser must accept custom merge-gamma coefficient pairs."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1", "--gamma=4.5,0.45"]
    )

    assert parsed is not None
    assert parsed[4].merge_gamma_option == dng2jpg_module.MergeGammaOption(
        mode="custom",
        linear_coeff=4.5,
        exponent=0.45,
    )


def test_parse_run_options_rejects_invalid_gamma_payload() -> None:
    """Parser must reject malformed or non-positive merge-gamma payloads."""

    invalid_shape = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1", "--gamma=4.5"]
    )
    invalid_non_positive = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--bracketing=1", "--gamma=0,0.45"]
    )

    assert invalid_shape is None
    assert invalid_non_positive is None


def test_apply_auto_white_balance_stage_float_uses_transient_auto_brightness_preprocessing(
    monkeypatch,
) -> None:
    """Auto-white-balance must estimate on transient auto-brightness data only."""

    stage_input = np.full((2, 2, 3), [0.2, 0.3, 0.4], dtype=np.float32)
    transient_estimation = np.full((2, 2, 3), [0.8, 0.6, 0.5], dtype=np.float32)
    fake_cv2 = _FakeOpenCvModule()
    captured_estimation_images: list[np.ndarray] = []

    monkeypatch.setattr(
        dng2jpg_module,
        "_apply_auto_brightness_rgb_float",
        lambda **_kwargs: np.array(transient_estimation, copy=True),
    )

    def _fake_estimate_xphoto(
        *,
        cv2_module,
        np_module,
        white_balance_mode,
        analysis_image_rgb_float,
        bits_per_color,
        white_balance_xphoto_domain,
        source_gamma_info,
    ):
        del cv2_module, np_module, white_balance_mode, bits_per_color, source_gamma_info
        captured_estimation_images.append(np.array(analysis_image_rgb_float, copy=True))
        assert white_balance_xphoto_domain == "srgb"
        return np.array([2.0, 3.0, 4.0], dtype=np.float64)

    monkeypatch.setattr(
        dng2jpg_module,
        "_estimate_xphoto_white_balance_gains_rgb",
        _fake_estimate_xphoto,
    )

    output_image = dng2jpg_module._apply_auto_white_balance_stage_float(  # pylint: disable=protected-access
        image_rgb_float=stage_input,
        white_balance_mode="Simple",
        auto_brightness_options=dng2jpg_module.AutoBrightnessOptions(),
        white_balance_xphoto_domain="srgb",
        auto_adjust_dependencies=(fake_cv2, np),
    )

    assert len(captured_estimation_images) == 1
    np.testing.assert_allclose(
        captured_estimation_images[0],
        transient_estimation,
        rtol=0.0,
        atol=0.0,
    )
    np.testing.assert_allclose(
        output_image,
        stage_input * np.array([2.0, 3.0, 4.0], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )


def test_apply_white_balance_to_bracket_triplet_simple_mode_uses_xphoto_factory(
    monkeypatch,
) -> None:
    """Simple mode must use OpenCV xphoto SimpleWB factory."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((2, 2, 3), 0.15, dtype=np.float32),
        np.full((2, 2, 3), 0.25, dtype=np.float32),
        np.full((2, 2, 3), 0.35, dtype=np.float32),
    ]

    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_white_balance_channel_gains_from_xphoto",
        lambda **_kwargs: np.array([1.1, 1.0, 0.9], dtype=np.float64),
    )

    output_triplet = dng2jpg_module._apply_white_balance_to_bracket_triplet(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        white_balance_mode="Simple",
        white_balance_analysis_image_float=bracket_images_float[1],
        auto_adjust_dependencies=(fake_cv2, np),
    )

    assert fake_cv2.xphoto.simple_calls == 1
    assert fake_cv2.xphoto.grayworld_calls == 0
    assert fake_cv2.xphoto.learning_calls == 0
    np.testing.assert_allclose(
        output_triplet[1],
        bracket_images_float[1] * np.array([1.1, 1.0, 0.9], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )


def test_apply_white_balance_to_bracket_triplet_grayworld_mode_uses_xphoto_factory(
    monkeypatch,
) -> None:
    """Grayworld mode must use OpenCV xphoto GrayworldWB factory."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((2, 2, 3), 0.15, dtype=np.float32),
        np.full((2, 2, 3), 0.25, dtype=np.float32),
        np.full((2, 2, 3), 0.35, dtype=np.float32),
    ]

    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_white_balance_channel_gains_from_xphoto",
        lambda **_kwargs: np.array([0.9, 1.0, 1.1], dtype=np.float64),
    )

    output_triplet = dng2jpg_module._apply_white_balance_to_bracket_triplet(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        white_balance_mode="GrayworldWB",
        white_balance_analysis_image_float=bracket_images_float[1],
        auto_adjust_dependencies=(fake_cv2, np),
    )

    assert fake_cv2.xphoto.simple_calls == 0
    assert fake_cv2.xphoto.grayworld_calls == 1
    assert fake_cv2.xphoto.learning_calls == 0
    np.testing.assert_allclose(
        output_triplet[1],
        bracket_images_float[1] * np.array([0.9, 1.0, 1.1], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )


def test_apply_white_balance_to_bracket_triplet_ia_mode_sets_hist_bins(
    monkeypatch,
) -> None:
    """IA mode must configure LearningBasedWB range and histogram by bit depth."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((2, 2, 3), 0.15, dtype=np.float32),
        np.full((2, 2, 3), 0.25, dtype=np.float32),
        np.full((2, 2, 3), 0.35, dtype=np.float32),
    ]

    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_white_balance_channel_gains_from_xphoto",
        lambda **_kwargs: np.array([1.0, 1.0, 1.0], dtype=np.float64),
    )

    dng2jpg_module._apply_white_balance_to_bracket_triplet(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        white_balance_mode="IA",
        white_balance_analysis_image_float=bracket_images_float[1],
        bits_per_color=14,
        auto_adjust_dependencies=(fake_cv2, np),
    )

    assert fake_cv2.xphoto.learning_calls == 1
    assert fake_cv2.xphoto.learning_wb.range_max == float((1 << 14) - 1)
    assert fake_cv2.xphoto.learning_wb.hist_bin_num == 1024


def test_extract_white_balance_channel_gains_from_xphoto_accepts_real_image_payload_shape(
    monkeypatch,
) -> None:
    """xphoto gain extraction must consume real-image payload, not fixed `(1,9,3)` proxy."""

    class _FakeXphotoAlgorithm:
        def __init__(self) -> None:
            self.seen_payload: np.ndarray | None = None

        def balanceWhite(self, image_bgr_u8: np.ndarray) -> np.ndarray:
            self.seen_payload = np.array(image_bgr_u8, copy=True)
            return np.array(image_bgr_u8, copy=True)

    fake_cv2 = _FakeOpenCvModule()
    fake_algorithm = _FakeXphotoAlgorithm()
    ev_zero_rgb = np.linspace(
        0.0,
        1.0,
        num=3 * 64 * 64,
        endpoint=True,
        dtype=np.float32,
    ).reshape((64, 64, 3))
    uint8_shapes: list[tuple[int, ...]] = []
    original_uint8_converter = dng2jpg_module._to_uint8_image_array  # pylint: disable=protected-access

    def _record_uint8_shape(*, np_module, image_data):
        uint8_shapes.append(tuple(image_data.shape))
        return original_uint8_converter(np_module=np_module, image_data=image_data)

    monkeypatch.setattr(
        dng2jpg_module,
        "_to_uint8_image_array",
        _record_uint8_shape,
    )

    gains = dng2jpg_module._extract_white_balance_channel_gains_from_xphoto(  # pylint: disable=protected-access
        cv2_module=fake_cv2,
        np_module=np,
        wb_algorithm=fake_algorithm,
        analysis_image_rgb_float=ev_zero_rgb,
        bits_per_color=8,
        prefer_uint16_payload=False,
    )

    assert len(uint8_shapes) == 1
    assert uint8_shapes[0][2] == 3
    assert uint8_shapes[0] != (1, 9, 3)
    assert fake_algorithm.seen_payload is not None
    assert fake_algorithm.seen_payload.shape == uint8_shapes[0]
    np.testing.assert_allclose(gains, np.array([1.0, 1.0, 1.0], dtype=np.float64), rtol=0.0, atol=0.0)


def test_extract_white_balance_channel_gains_from_xphoto_uses_inter_area_pyramid_downsampling() -> None:
    """xphoto payload builder must use INTER_AREA pyramid downsampling for large images."""

    class _FakeXphotoAlgorithm:
        def __init__(self) -> None:
            self.seen_payload: np.ndarray | None = None

        def balanceWhite(self, image_bgr_u8: np.ndarray) -> np.ndarray:
            self.seen_payload = np.array(image_bgr_u8, copy=True)
            return np.array(image_bgr_u8, copy=True)

    fake_cv2 = _FakeOpenCvModule()
    fake_algorithm = _FakeXphotoAlgorithm()
    large_analysis_rgb = np.linspace(
        0.0,
        1.0,
        num=3 * 1200 * 1400,
        endpoint=True,
        dtype=np.float32,
    ).reshape((1200, 1400, 3))

    gains = dng2jpg_module._extract_white_balance_channel_gains_from_xphoto(  # pylint: disable=protected-access
        cv2_module=fake_cv2,
        np_module=np,
        wb_algorithm=fake_algorithm,
        analysis_image_rgb_float=large_analysis_rgb,
        bits_per_color=8,
        prefer_uint16_payload=False,
    )

    assert fake_algorithm.seen_payload is not None
    assert fake_algorithm.seen_payload.shape[0] <= 1024
    assert fake_algorithm.seen_payload.shape[1] <= 1024
    assert fake_cv2.resize_calls
    assert all(
        resize_call[2] == fake_cv2.INTER_AREA for resize_call in fake_cv2.resize_calls
    )
    np.testing.assert_allclose(
        gains,
        np.array([1.0, 1.0, 1.0], dtype=np.float64),
        rtol=0.0,
        atol=0.0,
    )


def test_extract_white_balance_channel_gains_from_xphoto_supports_uint16_payload_for_ia() -> None:
    """IA extraction must support uint16 payloads when backend support is available."""

    class _FakeXphotoAlgorithm:
        def __init__(self) -> None:
            self.seen_payload: np.ndarray | None = None

        def balanceWhite(self, image_bgr_u16: np.ndarray) -> np.ndarray:
            self.seen_payload = np.array(image_bgr_u16, copy=True)
            return np.array(image_bgr_u16, copy=True)

    fake_cv2 = _FakeOpenCvModule()
    fake_algorithm = _FakeXphotoAlgorithm()
    analysis_rgb = np.full((8, 8, 3), 0.75, dtype=np.float32)

    gains = dng2jpg_module._extract_white_balance_channel_gains_from_xphoto(  # pylint: disable=protected-access
        cv2_module=fake_cv2,
        np_module=np,
        wb_algorithm=fake_algorithm,
        analysis_image_rgb_float=analysis_rgb,
        bits_per_color=14,
        prefer_uint16_payload=True,
    )

    assert fake_algorithm.seen_payload is not None
    assert fake_algorithm.seen_payload.dtype == np.uint16
    assert int(np.max(fake_algorithm.seen_payload)) <= (1 << 14) - 1
    np.testing.assert_allclose(
        gains,
        np.array([1.0, 1.0, 1.0], dtype=np.float64),
        rtol=0.0,
        atol=0.0,
    )


def test_estimate_xphoto_white_balance_gains_grayworld_uses_uint16_when_probe_succeeds(
    monkeypatch,
) -> None:
    """Grayworld mode must prefer uint16 payload when runtime probe confirms support."""

    fake_cv2 = _FakeOpenCvModule()

    class _GrayworldUint16Algorithm(_FakeXphotoWhiteBalanceAlgorithm):
        def balanceWhite(self, image_bgr_u8: np.ndarray) -> np.ndarray:
            return np.array(image_bgr_u8, copy=True)

    fake_cv2.xphoto.grayworld_wb = _GrayworldUint16Algorithm("grayworld")
    captured_prefer_uint16: list[bool] = []

    def _capture_extract(**kwargs):
        captured_prefer_uint16.append(bool(kwargs["prefer_uint16_payload"]))
        return np.array([1.0, 1.0, 1.0], dtype=np.float64)

    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_white_balance_channel_gains_from_xphoto",
        _capture_extract,
    )

    gains = dng2jpg_module._estimate_xphoto_white_balance_gains_rgb(  # pylint: disable=protected-access
        cv2_module=fake_cv2,
        np_module=np,
        white_balance_mode="GrayworldWB",
        analysis_image_rgb_float=np.full((4, 4, 3), 0.25, dtype=np.float32),
        bits_per_color=14,
        white_balance_xphoto_domain=dng2jpg_module.WHITE_BALANCE_XPHOTO_DOMAIN_LINEAR,
        source_gamma_info=None,
    )

    assert captured_prefer_uint16 == [True]
    np.testing.assert_allclose(
        gains,
        np.array([1.0, 1.0, 1.0], dtype=np.float64),
        rtol=0.0,
        atol=0.0,
    )


def test_estimate_xphoto_white_balance_gains_simple_falls_back_to_uint8_without_probe_support(
    monkeypatch,
) -> None:
    """Simple mode must remain on uint8 when uint16 probe does not confirm support."""

    fake_cv2 = _FakeOpenCvModule()
    captured_prefer_uint16: list[bool] = []

    def _capture_extract(**kwargs):
        captured_prefer_uint16.append(bool(kwargs["prefer_uint16_payload"]))
        return np.array([1.0, 1.0, 1.0], dtype=np.float64)

    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_white_balance_channel_gains_from_xphoto",
        _capture_extract,
    )

    gains = dng2jpg_module._estimate_xphoto_white_balance_gains_rgb(  # pylint: disable=protected-access
        cv2_module=fake_cv2,
        np_module=np,
        white_balance_mode="Simple",
        analysis_image_rgb_float=np.full((4, 4, 3), 0.25, dtype=np.float32),
        bits_per_color=14,
        white_balance_xphoto_domain=dng2jpg_module.WHITE_BALANCE_XPHOTO_DOMAIN_LINEAR,
        source_gamma_info=None,
    )

    assert captured_prefer_uint16 == [False]
    np.testing.assert_allclose(
        gains,
        np.array([1.0, 1.0, 1.0], dtype=np.float64),
        rtol=0.0,
        atol=0.0,
    )


def test_compress_xphoto_estimation_payload_highlights_soft_knee_reduces_hard_clip() -> None:
    """Soft-knee compression must reduce hard-clip saturation on xphoto payload."""

    payload = np.array(
        [[[0.10, 0.20, 0.40], [0.95, 1.00, 1.10], [1.40, 2.00, 4.00]]],
        dtype=np.float32,
    )
    hard_clipped = np.clip(payload, 0.0, 1.0)
    soft_knee = dng2jpg_module._compress_xphoto_estimation_payload_highlights_soft_knee(  # pylint: disable=protected-access
        np_module=np,
        rescaled_payload_rgb_float=payload,
    )

    hard_clip_saturation = int(np.sum(hard_clipped >= 1.0))
    soft_knee_saturation = int(np.sum(soft_knee >= 1.0))
    assert hard_clip_saturation > 0
    assert soft_knee_saturation < hard_clip_saturation
    sorted_input = np.sort(payload.reshape(-1))
    sorted_output = np.sort(soft_knee.reshape(-1))
    assert np.all(np.diff(sorted_output) >= -1e-9)
    assert sorted_output.shape == sorted_input.shape


def test_estimate_xphoto_white_balance_gains_source_auto_resolves_srgb_domain(
    monkeypatch,
) -> None:
    """Source-auto domain must resolve from source gamma diagnostics for xphoto estimation."""

    fake_cv2 = _FakeOpenCvModule()
    captured_analysis_means: list[float] = []

    def _capture_extract(**kwargs):
        captured_analysis_means.append(
            float(np.mean(kwargs["analysis_image_rgb_float"]))
        )
        return np.array([1.0, 1.0, 1.0], dtype=np.float64)

    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_white_balance_channel_gains_from_xphoto",
        _capture_extract,
    )
    source_gamma_info = dng2jpg_module.SourceGammaInfo(
        label="sRGB",
        gamma_value=2.2,
        evidence="explicit-profile",
    )
    gains = dng2jpg_module._estimate_xphoto_white_balance_gains_rgb(  # pylint: disable=protected-access
        cv2_module=fake_cv2,
        np_module=np,
        white_balance_mode="Simple",
        analysis_image_rgb_float=np.full((2, 2, 3), 0.25, dtype=np.float32),
        bits_per_color=12,
        white_balance_xphoto_domain=dng2jpg_module.WHITE_BALANCE_XPHOTO_DOMAIN_SOURCE_AUTO,
        source_gamma_info=source_gamma_info,
    )

    assert len(captured_analysis_means) == 1
    assert captured_analysis_means[0] > 0.25
    np.testing.assert_allclose(
        gains,
        np.array([1.0, 1.0, 1.0], dtype=np.float64),
        rtol=0.0,
        atol=0.0,
    )


def test_build_white_balance_robust_analysis_mask_uses_percentile_thresholds() -> None:
    """Robust mask must reject near-black and near-saturated pixels using percentiles."""

    channel = np.linspace(0.0, 1.0, num=100, dtype=np.float32).reshape((10, 10, 1))
    analysis_rgb = np.repeat(channel, repeats=3, axis=2)

    robust_mask = dng2jpg_module._build_white_balance_robust_analysis_mask(  # pylint: disable=protected-access
        np_module=np,
        analysis_rgb_float=analysis_rgb,
    )

    assert robust_mask.shape == (10, 10)
    assert not bool(robust_mask[0, 0])
    assert not bool(robust_mask[-1, -1])
    assert bool(robust_mask[5, 5])


def test_apply_white_balance_to_bracket_triplet_color_constancy_mode_uses_robust_masked_statistics(
    monkeypatch,
) -> None:
    """ColorConstancy mode must use robust masked statistics over analysis image."""

    bracket_images_float = [
        np.full((2, 2, 3), 0.15, dtype=np.float32),
        np.full((2, 2, 3), 0.25, dtype=np.float32),
        np.full((2, 2, 3), 0.35, dtype=np.float32),
    ]
    analysis_calls: list[np.ndarray] = []

    def _fake_estimate_color_constancy(
        *,
        np_module,
        skimage_color_module,
        analysis_image_rgb_float,
    ):
        del np_module
        assert skimage_color_module is not None
        analysis_calls.append(np.array(analysis_image_rgb_float, copy=True))
        return np.array([1.2, 1.0, 0.8], dtype=np.float64)

    class _FakeSkimageColorModule:
        @staticmethod
        def rgb2gray(image_rgb: np.ndarray) -> np.ndarray:
            return np.mean(image_rgb, axis=2)

    class _FakeSkimagePackage:
        color = _FakeSkimageColorModule()

    monkeypatch.setattr(
        dng2jpg_module,
        "_estimate_color_constancy_white_balance_gains_rgb",
        _fake_estimate_color_constancy,
    )
    monkeypatch.setitem(sys.modules, "skimage", _FakeSkimagePackage())

    output_triplet = dng2jpg_module._apply_white_balance_to_bracket_triplet(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        white_balance_mode="ColorConstancy",
        white_balance_analysis_image_float=bracket_images_float[1],
        auto_adjust_dependencies=(None, np),
    )

    assert len(analysis_calls) == 1
    np.testing.assert_allclose(analysis_calls[0], bracket_images_float[1], rtol=0.0, atol=0.0)
    np.testing.assert_allclose(
        output_triplet[2],
        bracket_images_float[2] * np.array([1.2, 1.0, 0.8], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )
    sys.modules.pop("skimage", None)


def test_apply_white_balance_to_bracket_triplet_ttl_mode_uses_robust_masked_statistics() -> None:
    """TTL mode must use robust masked statistics and apply un-clipped gains."""

    bracket_images_float = [
        np.full((2, 2, 3), [0.10, 0.20, 0.30], dtype=np.float32),
        np.full((2, 2, 3), [0.80, 0.40, 0.20], dtype=np.float32),
        np.full((2, 2, 3), [0.90, 0.60, 0.50], dtype=np.float32),
    ]

    output_triplet = dng2jpg_module._apply_white_balance_to_bracket_triplet(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        white_balance_mode="TTL",
        white_balance_analysis_image_float=bracket_images_float[1],
        auto_adjust_dependencies=(None, np),
    )

    analysis_mask = dng2jpg_module._build_white_balance_robust_analysis_mask(  # pylint: disable=protected-access
        np_module=np,
        analysis_rgb_float=bracket_images_float[1],
    )
    masked_pixels = bracket_images_float[1][analysis_mask]
    channel_means = np.mean(masked_pixels, axis=0)
    expected_gains = float(np.mean(channel_means)) / channel_means
    np.testing.assert_allclose(
        output_triplet[0],
        bracket_images_float[0] * expected_gains.astype(np.float32),
        rtol=1e-6,
        atol=1e-6,
    )
    assert float(np.max(output_triplet[2])) > 1.0


def test_apply_auto_white_balance_stage_float_ttl_path_avoids_quantized_helpers(
    monkeypatch,
) -> None:
    """TTL stage must keep estimation fully in float domain without uint quantization helpers."""

    monkeypatch.setattr(
        dng2jpg_module,
        "_to_uint8_image_array",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("TTL path called _to_uint8_image_array unexpectedly")
        ),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_to_uint16_image_array",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("TTL path called _to_uint16_image_array unexpectedly")
        ),
    )
    stage_input = np.array(
        [[[0.2, 0.4, 0.6], [0.3, 0.5, 0.7]], [[0.4, 0.2, 0.1], [0.8, 0.6, 0.4]]],
        dtype=np.float32,
    )
    output_image = dng2jpg_module._apply_auto_white_balance_stage_float(  # pylint: disable=protected-access
        image_rgb_float=stage_input,
        white_balance_mode="TTL",
        auto_brightness_options=dng2jpg_module.AutoBrightnessOptions(),
        auto_adjust_dependencies=(None, np),
        estimation_input_is_auto_brightness_preprocessed=True,
    )
    assert output_image.dtype == np.float32
    assert output_image.shape == stage_input.shape


def test_apply_auto_white_balance_stage_float_color_constancy_path_avoids_quantized_helpers(
    monkeypatch,
) -> None:
    """ColorConstancy stage must keep estimation fully in float domain without uint quantization helpers."""

    monkeypatch.setattr(
        dng2jpg_module,
        "_to_uint8_image_array",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("ColorConstancy path called _to_uint8_image_array unexpectedly")
        ),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_to_uint16_image_array",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("ColorConstancy path called _to_uint16_image_array unexpectedly")
        ),
    )

    class _FakeSkimageColorModule:
        @staticmethod
        def rgb2gray(image_rgb: np.ndarray) -> np.ndarray:
            return np.mean(image_rgb, axis=2)

    class _FakeSkimagePackage:
        color = _FakeSkimageColorModule()

    monkeypatch.setitem(sys.modules, "skimage", _FakeSkimagePackage())
    stage_input = np.array(
        [[[0.2, 0.4, 0.6], [0.3, 0.5, 0.7]], [[0.4, 0.2, 0.1], [0.8, 0.6, 0.4]]],
        dtype=np.float32,
    )
    output_image = dng2jpg_module._apply_auto_white_balance_stage_float(  # pylint: disable=protected-access
        image_rgb_float=stage_input,
        white_balance_mode="ColorConstancy",
        auto_brightness_options=dng2jpg_module.AutoBrightnessOptions(),
        auto_adjust_dependencies=(None, np),
        estimation_input_is_auto_brightness_preprocessed=True,
    )
    assert output_image.dtype == np.float32
    assert output_image.shape == stage_input.shape
    sys.modules.pop("skimage", None)


def test_apply_white_balance_to_bracket_triplet_linear_base_analysis_avoids_ev_zero_clipping_bias() -> None:
    """Linear-base analysis must preserve unclipped center-domain information."""

    base_rgb_float = np.full((2, 2, 3), [0.6, 0.9, 0.9], dtype=np.float32)
    ev_zero = 1.0
    analysis_image = (
        dng2jpg_module._build_white_balance_analysis_image_from_linear_base_float(  # pylint: disable=protected-access
            np_module=np,
            base_rgb_float=base_rgb_float,
            ev_zero=ev_zero,
        )
    )
    clipped_ev_zero = np.clip(base_rgb_float * np.float32(2.0 ** ev_zero), 0.0, 1.0)
    assert float(np.max(analysis_image)) > 1.0
    assert float(np.max(clipped_ev_zero)) == 1.0

    bracket_images_float = [
        np.full((2, 2, 3), 0.1, dtype=np.float32),
        clipped_ev_zero.astype(np.float32, copy=False),
        np.full((2, 2, 3), 0.3, dtype=np.float32),
    ]
    output_triplet = dng2jpg_module._apply_white_balance_to_bracket_triplet(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        white_balance_mode="TTL",
        white_balance_analysis_image_float=analysis_image,
        auto_adjust_dependencies=(None, np),
    )
    assert float(np.max(output_triplet[1])) > 1.0


def test_apply_auto_post_gamma_float_uses_mean_luminance_anchor_and_guards() -> None:
    """Auto-gamma must use mean-luminance anchoring and guard-path identity behavior."""

    image_rgb_float = np.array(
        [[[0.25, 0.25, 0.25], [0.75, 0.75, 0.75]]],
        dtype=np.float32,
    )
    options = dng2jpg_module.PostGammaAutoOptions(
        target_gray=0.5,
        luma_min=0.01,
        luma_max=0.99,
        lut_size=256,
    )
    output, resolved_gamma = dng2jpg_module._apply_auto_post_gamma_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        post_gamma_auto_options=options,
    )
    mean_luminance = float(np.mean((0.2126 * image_rgb_float[:, :, 0]) + (0.7152 * image_rgb_float[:, :, 1]) + (0.0722 * image_rgb_float[:, :, 2])))
    expected_gamma = float(np.log(0.5) / np.log(mean_luminance))
    np.testing.assert_allclose(resolved_gamma, expected_gamma, rtol=1e-7, atol=0.0)
    np.testing.assert_allclose(
        output,
        np.power(image_rgb_float.astype(np.float64), expected_gamma).astype(np.float32),
        rtol=1e-5,
        atol=1e-6,
    )

    guarded_options = dng2jpg_module.PostGammaAutoOptions(
        target_gray=0.5,
        luma_min=0.26,
        luma_max=0.99,
        lut_size=256,
    )
    guarded_output, guarded_gamma = dng2jpg_module._apply_auto_post_gamma_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        post_gamma_auto_options=guarded_options,
    )
    assert guarded_gamma == 1.0
    np.testing.assert_allclose(guarded_output, image_rgb_float, rtol=0.0, atol=0.0)


def test_apply_auto_post_gamma_float_uses_float_lut_mapping_without_quantized_helpers(
    monkeypatch,
) -> None:
    """Auto-gamma LUT mapping must stay float-only without quantized helper calls."""

    image_rgb_float = np.array(
        [[[0.125, 0.375, 0.625], [0.875, 0.5, 0.25]]],
        dtype=np.float32,
    )
    options = dng2jpg_module.PostGammaAutoOptions(
        target_gray=0.5,
        luma_min=0.01,
        luma_max=0.99,
        lut_size=64,
    )

    def _fail_uint8(*_args, **_kwargs):
        raise AssertionError("Auto-gamma must not call _to_uint8_image_array")

    def _fail_uint16(*_args, **_kwargs):
        raise AssertionError("Auto-gamma must not call _to_uint16_image_array")

    monkeypatch.setattr(dng2jpg_module, "_to_uint8_image_array", _fail_uint8)
    monkeypatch.setattr(dng2jpg_module, "_to_uint16_image_array", _fail_uint16)

    output, resolved_gamma = dng2jpg_module._apply_auto_post_gamma_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        post_gamma_auto_options=options,
    )
    assert output.dtype == np.float32
    assert output.shape == image_rgb_float.shape
    assert resolved_gamma > 0.0

def test_extract_source_gamma_info_prefers_explicit_profile_metadata() -> None:
    """Source gamma diagnostics must prefer explicit profile metadata."""

    class _FakeRawHandle:
        output_color = "sRGB"
        tone_curve = [0, 128, 255]
        rgb_xyz_matrix = [[1.0, 0.0, 0.0]]
        color_matrix = [[1.0, 0.0, 0.0]]
        color_desc = b"RGBG"

    source_gamma_info = dng2jpg_module._extract_source_gamma_info(  # pylint: disable=protected-access
        _FakeRawHandle()
    )

    assert source_gamma_info == dng2jpg_module.SourceGammaInfo(
        label="sRGB",
        gamma_value=2.2,
        evidence="explicit-profile",
    )


def test_extract_source_gamma_info_reports_unknown_without_metadata() -> None:
    """Source gamma diagnostics must fall back to unknown when metadata is insufficient."""

    class _FakeRawHandle:
        tone_curve = []
        rgb_xyz_matrix = None
        color_matrix = None
        color_desc = None

    source_gamma_info = dng2jpg_module._extract_source_gamma_info(  # pylint: disable=protected-access
        _FakeRawHandle()
    )

    assert source_gamma_info == dng2jpg_module.SourceGammaInfo(
        label="unknown",
        gamma_value=None,
        evidence="insufficient-metadata",
    )


def test_resolve_auto_merge_gamma_prefers_exif_colorspace() -> None:
    """Auto merge gamma must prioritize EXIF color-space evidence."""

    resolved = dng2jpg_module._resolve_auto_merge_gamma(  # pylint: disable=protected-access
        exif_gamma_tags=dng2jpg_module.ExifGammaTags(
            color_space="2",
            interoperability_index=None,
        ),
        source_gamma_info=dng2jpg_module.SourceGammaInfo(
            label="sRGB",
            gamma_value=2.2,
            evidence="explicit-profile",
        ),
    )

    assert resolved == dng2jpg_module.ResolvedMergeGamma(
        request=dng2jpg_module.MergeGammaOption(mode="auto"),
        transfer="power",
        label="Adobe RGB",
        param_a=2.19921875,
        param_b=None,
        evidence="exif-adobe-rgb",
    )


def test_describe_resolved_merge_gamma_exposes_linear_and_curve_parameters() -> None:
    """Merge-gamma diagnostics must expose the applied transfer parameters."""

    srgb_description = dng2jpg_module._describe_resolved_merge_gamma(  # pylint: disable=protected-access
        dng2jpg_module.ResolvedMergeGamma(
            request=dng2jpg_module.MergeGammaOption(mode="auto"),
            transfer="srgb",
            label="sRGB",
            param_a=None,
            param_b=None,
            evidence="exif-colorspace=1",
        )
    )
    adobe_description = dng2jpg_module._describe_resolved_merge_gamma(  # pylint: disable=protected-access
        dng2jpg_module.ResolvedMergeGamma(
            request=dng2jpg_module.MergeGammaOption(mode="auto"),
            transfer="power",
            label="Adobe RGB",
            param_a=2.19921875,
            param_b=None,
            evidence="exif-adobe-rgb",
        )
    )
    custom_description = dng2jpg_module._describe_resolved_merge_gamma(  # pylint: disable=protected-access
        dng2jpg_module.ResolvedMergeGamma(
            request=dng2jpg_module.MergeGammaOption(
                mode="custom",
                linear_coeff=4.5,
                exponent=0.45,
            ),
            transfer="rec709",
            label="Rec.709 custom",
            param_a=4.5,
            param_b=0.45,
            evidence="cli-custom",
        )
    )

    assert "linear(scale=12.92,limit=0.0031308)" in srgb_description
    assert "curve(scale=1.055,power=1/2.4,offset=-0.055)" in srgb_description
    assert "linear=none" in adobe_description
    assert "curve(power=1/2.19921875)" in adobe_description
    assert "linear(scale=4.5,limit=0.018)" in custom_description
    assert "curve(scale=1.099,power=0.45,offset=-0.099)" in custom_description


def test_run_opencv_merge_mertens_applies_float_path_brightness_rescaling() -> None:
    """Mertens float path must rescale OpenCV output before normalization."""

    class _ScalingMergeMertens:
        def __init__(self) -> None:
            self.last_inputs: list[np.ndarray] | None = None

        def process(self, images: list[np.ndarray]) -> np.ndarray:
            self.last_inputs = [np.array(image, copy=True) for image in images]
            return np.array([[[0.1, 0.2, 0.4]]], dtype=np.float32)

    class _ScalingCv2:
        def __init__(self) -> None:
            self.merge_mertens = _ScalingMergeMertens()
            self.last_tonemap: _FakeTonemap | None = None

        def createMergeMertens(self) -> _ScalingMergeMertens:
            return self.merge_mertens

        def createTonemap(self, gamma: float) -> _FakeTonemap:
            self.last_tonemap = _FakeTonemap(gamma=gamma)
            return self.last_tonemap

    scaling_cv2 = _ScalingCv2()
    scaled = dng2jpg_module._run_opencv_merge_mertens(  # pylint: disable=protected-access
        cv2_module=scaling_cv2,
        np_module=np,
        exposures_float=[np.full((1, 1, 3), 0.5, dtype=np.float32) for _ in range(3)],
        tonemap_enabled=False,
        tonemap_gamma=2.2,
    )

    np.testing.assert_allclose(
        scaled,
        np.array([[[0.25, 0.5, 1.0]]], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )
    assert scaling_cv2.last_tonemap is None


def test_run_opencv_merge_backend_applies_resolved_merge_gamma_last() -> None:
    """OpenCV merge must apply resolved merge gamma after backend normalization."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((1, 1, 3), 0.1, dtype=np.float32),
        np.full((1, 1, 3), 0.3, dtype=np.float32),
        np.full((1, 1, 3), 0.6, dtype=np.float32),
    ]

    output = dng2jpg_module._run_opencv_merge_backend(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        ev_value=1.0,
        ev_zero=0.0,
        source_exposure_time_seconds=0.125,
        opencv_merge_options=dng2jpg_module.OpenCvMergeOptions(
            merge_algorithm=dng2jpg_module.OPENCV_MERGE_ALGORITHM_MERTENS
        ),
        auto_adjust_dependencies=(fake_cv2, np),
        resolved_merge_gamma=dng2jpg_module.ResolvedMergeGamma(
            request=dng2jpg_module.MergeGammaOption(mode="auto"),
            transfer="power",
            label="Adobe RGB",
            param_a=2.19921875,
            param_b=None,
            evidence="exif-adobe-rgb",
        ),
    )

    np.testing.assert_allclose(
        output,
        np.full((1, 1, 3), 1.0, dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )


def test_parse_auto_levels_options_defaults_match_rawtherapee() -> None:
    """Auto-levels defaults must match the RawTherapee exposure tool defaults."""

    options = dng2jpg_module._parse_auto_levels_options({})  # pylint: disable=protected-access
    assert options == dng2jpg_module.AutoLevelsOptions(
        clip_percent=0.02,
        clip_out_of_gamut=True,
        histcompr=3,
        highlight_reconstruction_enabled=False,
        highlight_reconstruction_method="Inpaint Opposed",
        gain_threshold=1.0,
    )


def test_parse_run_options_accepts_extended_auto_levels_knobs() -> None:
    """Parser must accept the expanded RawTherapee-aligned auto-levels knobs."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--auto-levels=enable",
            "--al-clip-pct=0.5",
            "--al-clip-out-of-gamut=false",
            "--al-highlight-reconstruction",
            "--al-highlight-reconstruction-method=Inpaint Opposed",
            "--al-gain-threshold=1.25",
            "--hdr-merge=OpenCV-Merge",
        ]
    )
    assert parsed is not None
    postprocess = parsed[4]
    assert postprocess.auto_levels_enabled is True
    assert postprocess.auto_levels_options.clip_percent == 0.5
    assert postprocess.auto_levels_options.clip_out_of_gamut is False
    assert postprocess.auto_levels_options.highlight_reconstruction_enabled is True
    assert (
        postprocess.auto_levels_options.highlight_reconstruction_method
        == "Inpaint Opposed"
    )
    assert postprocess.auto_levels_options.gain_threshold == 1.25


def test_parse_run_options_method_does_not_enable_highlight_reconstruction() -> None:
    """Method selection must not implicitly enable highlight reconstruction."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--auto-levels=enable",
            "--al-highlight-reconstruction-method=Color Propagation",
            "--hdr-merge=OpenCV-Merge",
        ]
    )
    assert parsed is not None
    postprocess = parsed[4]
    assert postprocess.auto_levels_options.highlight_reconstruction_enabled is False
    assert (
        postprocess.auto_levels_options.highlight_reconstruction_method
        == "Color Propagation"
    )


def test_compute_auto_levels_from_histogram_matches_rawtherapee_reference() -> None:
    """Auto-levels metric solver must keep the frozen RawTherapee reference output."""

    histogram = np.zeros(65536 >> dng2jpg_module.DEFAULT_AL_HISTCOMPR, dtype=np.uint64)
    histogram_updates = {
        8: 10,
        16: 20,
        32: 35,
        64: 60,
        128: 90,
        256: 130,
        512: 170,
        1024: 220,
        1536: 200,
        2048: 180,
        2560: 140,
        3072: 100,
        3584: 60,
        4096: 30,
        4608: 10,
        5120: 3,
    }
    for histogram_index, count in histogram_updates.items():
        histogram[histogram_index] = count

    metrics = dng2jpg_module._compute_auto_levels_from_histogram(  # pylint: disable=protected-access
        np_module=np,
        histogram=histogram,
        histcompr=dng2jpg_module.DEFAULT_AL_HISTCOMPR,
        clip_percent=dng2jpg_module.DEFAULT_AL_CLIP_PERCENT,
    )

    assert metrics["black"] == 102
    assert metrics["brightness"] == 0
    assert metrics["contrast"] == 21
    assert metrics["hlcompr"] == 0
    assert metrics["hlcomprthresh"] == 0
    assert metrics["whiteclip"] == 40960
    assert metrics["rawmax"] == 40960
    assert metrics["shc"] == 64
    assert metrics["median"] == 8192
    assert metrics["overex"] == 2
    np.testing.assert_allclose(metrics["expcomp"], 0.24540694839048818, rtol=1e-9)
    np.testing.assert_allclose(metrics["gain"], 1.1854271032896186, rtol=1e-9)
    np.testing.assert_allclose(metrics["average"], 11540.631001371743, rtol=1e-9)
    np.testing.assert_allclose(metrics["ospread"], 0.6606658566861634, rtol=1e-9)


def test_apply_auto_levels_clip_out_of_gamut_matches_rawtherapee_filmlike_clip(
    monkeypatch,
) -> None:
    """Out-of-gamut clipping must follow RawTherapee film-like hue-stable clipping."""

    image_rgb_float = np.array([[[40000, 30000, 20000]]], dtype=np.float32) / 65535.0

    monkeypatch.setattr(
        dng2jpg_module,
        "_build_autoexp_histogram_rgb_float",
        lambda **_kwargs: np.zeros(1, dtype=np.uint64),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_compute_auto_levels_from_histogram",
        lambda **_kwargs: {"gain": 2.0},
    )

    disabled = dng2jpg_module._apply_auto_levels_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        auto_levels_options=dng2jpg_module.AutoLevelsOptions(
            clip_out_of_gamut=False,
        ),
    )
    enabled = dng2jpg_module._apply_auto_levels_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        auto_levels_options=dng2jpg_module.AutoLevelsOptions(
            clip_out_of_gamut=True,
        ),
    )

    np.testing.assert_allclose(
        disabled,
        np.array([[[80000, 60000, 40000]]], dtype=np.float32) / 65535.0,
        rtol=1e-6,
        atol=1e-6,
    )
    np.testing.assert_allclose(
        enabled,
        np.array([[[1.0, 0.80518043, 0.61036086]]], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )


def test_apply_auto_levels_tonal_transform_uses_metric_driven_float_curves(
    monkeypatch,
) -> None:
    """Auto-levels must apply the full float tone transform before clipping."""

    image_rgb_float = np.array([[[0.2, 0.4, 0.6]]], dtype=np.float32)
    monkeypatch.setattr(
        dng2jpg_module,
        "_build_autoexp_histogram_rgb_float",
        lambda **_kwargs: np.zeros(1, dtype=np.uint64),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_compute_auto_levels_from_histogram",
        lambda **_kwargs: {
            "expcomp": 0.25,
            "gain": 1.0,
            "black_normalized": 0.01,
            "brightness": 10,
            "contrast": 15,
            "hlcompr": 20,
            "hlcomprthresh": 35,
        },
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_apply_auto_levels_tonal_transform_float",
        lambda **kwargs: kwargs["image_rgb_float"].astype(np.float64) + 0.125,
    )

    output = dng2jpg_module._apply_auto_levels_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        auto_levels_options=dng2jpg_module.AutoLevelsOptions(
            clip_out_of_gamut=False,
        ),
    )

    np.testing.assert_allclose(
        output,
        np.array([[[0.325, 0.525, 0.725]]], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )


def test_apply_auto_levels_tonal_transform_keeps_mixed_overflow_on_tonecurve_path(
    monkeypatch,
) -> None:
    """Mixed-overflow pixels must still sample the final tone curve."""

    image_rgb_float = np.array([[[0.4, 0.8, 1.2]]], dtype=np.float32)
    highlight_curve = np.linspace(0.75, 1.25, 65536, dtype=np.float64)
    shadow_curve = np.ones(65536, dtype=np.float64)
    tone_curve = np.linspace(0.1, 0.9, 65536, dtype=np.float64)
    metrics = {
        "expcomp": 0.0,
        "black_normalized": 0.0,
        "brightness": 0,
        "contrast": 0,
        "hlcompr": 0,
        "hlcomprthresh": 0,
    }

    monkeypatch.setattr(
        dng2jpg_module,
        "_build_auto_levels_tone_curve_state",
        lambda **_kwargs: {
            "highlight_curve": highlight_curve,
            "shadow_curve": shadow_curve,
            "tone_curve": tone_curve,
            "exp_scale": 1.0,
            "comp": 0.0,
            "hlrange": float(dng2jpg_module._AUTO_LEVELS_CODE_MAX),  # pylint: disable=protected-access
        },
    )
    output = dng2jpg_module._apply_auto_levels_tonal_transform_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        auto_levels_metrics=metrics,
    )

    image_code = np.clip(image_rgb_float.astype(np.float64), 0.0, 1.0)
    image_code *= dng2jpg_module._AUTO_LEVELS_CODE_MAX  # pylint: disable=protected-access
    channel_factors = [
        dng2jpg_module._sample_auto_levels_lut_float(  # pylint: disable=protected-access
            np_module=np,
            lut_values=highlight_curve,
            indices=image_code[..., channel_index],
        )
        for channel_index in range(3)
    ]
    highlight_factor = np.stack(channel_factors, axis=0).mean(axis=0)
    expected = dng2jpg_module._sample_auto_levels_lut_float(  # pylint: disable=protected-access
        np_module=np,
        lut_values=tone_curve,
        indices=image_code * highlight_factor[..., None],
    )
    np.testing.assert_allclose(output, expected, rtol=1e-6, atol=1e-6)


def test_apply_auto_levels_color_methods_require_explicit_enable(
    monkeypatch,
) -> None:
    """Highlight reconstruction methods must execute only when explicitly enabled."""

    image_rgb_float = (
        np.array([[[1000, 2000, 3000], [4000, 5000, 6000]]], dtype=np.float32)
        / 65535.0
    )
    call_trace: list[tuple[str, float | None]] = []

    monkeypatch.setattr(
        dng2jpg_module,
        "_build_autoexp_histogram_rgb_float",
        lambda **_kwargs: np.zeros(1, dtype=np.uint64),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_compute_auto_levels_from_histogram",
        lambda **_kwargs: {
            "expcomp": 0.0,
            "gain": 1.0,
            "black_normalized": 0.0,
            "brightness": 0,
            "contrast": 0,
            "hlcompr": 0,
            "hlcomprthresh": 0,
        },
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_apply_auto_levels_tonal_transform_float",
        lambda **kwargs: kwargs["image_rgb_float"].astype(np.float64),
    )

    def _fake_color_propagation(*, np_module, image_rgb, maxval):
        del np_module, maxval  # Unused by fake dispatcher.
        assert image_rgb.dtype.kind == "f"
        call_trace.append(("Color Propagation", None))
        return image_rgb + 100.0

    def _fake_inpaint_opposed(*, np_module, image_rgb, gain_threshold, maxval):
        del np_module, maxval  # Unused by fake dispatcher.
        assert image_rgb.dtype.kind == "f"
        call_trace.append(("Inpaint Opposed", gain_threshold))
        return image_rgb + 200.0

    monkeypatch.setattr(
        dng2jpg_module,
        "_hlrecovery_color_propagation_uint16",
        _fake_color_propagation,
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_hlrecovery_inpaint_opposed_uint16",
        _fake_inpaint_opposed,
    )

    disabled_output = dng2jpg_module._apply_auto_levels_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        auto_levels_options=dng2jpg_module.AutoLevelsOptions(
            highlight_reconstruction_enabled=False,
            highlight_reconstruction_method="Color Propagation",
            clip_out_of_gamut=False,
        ),
    )
    color_output = dng2jpg_module._apply_auto_levels_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        auto_levels_options=dng2jpg_module.AutoLevelsOptions(
            highlight_reconstruction_enabled=True,
            highlight_reconstruction_method="Color Propagation",
            clip_out_of_gamut=False,
        ),
    )
    inpaint_output = dng2jpg_module._apply_auto_levels_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        auto_levels_options=dng2jpg_module.AutoLevelsOptions(
            highlight_reconstruction_enabled=True,
            highlight_reconstruction_method="Inpaint Opposed",
            gain_threshold=1.25,
            clip_out_of_gamut=False,
        ),
    )

    np.testing.assert_allclose(
        disabled_output,
        image_rgb_float.astype(np.float32),
        rtol=1e-6,
        atol=1e-6,
    )
    assert color_output.dtype == np.float32
    assert inpaint_output.dtype == np.float32
    np.testing.assert_allclose(
        color_output,
        np.array([[[1100, 2100, 3100], [4100, 5100, 6100]]], dtype=np.float32)
        / 65535.0,
        rtol=1e-6,
        atol=1e-6,
    )
    np.testing.assert_allclose(
        inpaint_output,
        np.array([[[1200, 2200, 3200], [4200, 5200, 6200]]], dtype=np.float32)
        / 65535.0,
        rtol=1e-6,
        atol=1e-6,
    )
    assert call_trace == [
        ("Color Propagation", None),
        ("Inpaint Opposed", 1.25),
    ]


def test_parse_run_options_accepts_hdrplus_controls() -> None:
    """Parser must expose HDR+ proxy, alignment, and temporal knobs."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--hdr-merge=HDR-Plus",
            "--hdrplus-proxy-mode=bt709",
            "--hdrplus-search-radius=3",
            "--hdrplus-temporal-factor=6.5",
            "--hdrplus-temporal-min-dist=4",
            "--hdrplus-temporal-max-dist=120",
        ]
    )

    assert parsed is not None
    hdrplus_options = parsed[9]
    enable_hdr_plus = parsed[10]
    assert enable_hdr_plus is True
    assert hdrplus_options == dng2jpg_module.HdrPlusOptions(
        proxy_mode="bt709",
        search_radius=3,
        temporal_factor=6.5,
        temporal_min_dist=4.0,
        temporal_max_dist=120.0,
    )


def test_parse_run_options_rejects_invalid_hdrplus_controls() -> None:
    """Parser must reject inconsistent HDR+ temporal threshold combinations."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--bracketing=1",
            "--hdr-merge=HDR-Plus",
            "--hdrplus-temporal-min-dist=30",
            "--hdrplus-temporal-max-dist=30",
        ]
    )

    assert parsed is None


def test_hdrplus_proxy_rggb_matches_green_weighted_scalar() -> None:
    """`rggb` proxy mode must match the Bayer-inspired green-weighted scalar."""

    frames_rgb_float32 = np.array(
        [
            [
                [[100, 200, 300], [500, 1000, 1500]],
                [[40, 80, 120], [7, 11, 19]],
            ]
        ],
        dtype=np.float32,
    ) / 65535.0

    scalar_proxy = dng2jpg_module._hdrplus_build_scalar_proxy_float32(  # pylint: disable=protected-access
        np_module=np,
        frames_rgb_float32=frames_rgb_float32,
        hdrplus_options=dng2jpg_module.HdrPlusOptions(proxy_mode="rggb"),
    )

    np.testing.assert_allclose(
        scalar_proxy,
        np.array([[[200.0, 1000.0], [80.0, 12.0]]], dtype=np.float32) / 65535.0,
        rtol=1e-6,
        atol=1e-6,
    )


def test_hdrplus_align_layers_detects_translated_alternate_frame() -> None:
    """Hierarchical HDR+ alignment must recover non-zero alternate-frame offsets."""

    rng = np.random.default_rng(1234)
    reference = (
        rng.integers(0, 4096, size=(96, 96), dtype=np.int16).astype(np.float32)
        / 65535.0
    )
    alternate = _reflect_shift_2d(reference, shift_y=1, shift_x=2).astype(np.float32)
    alignments = dng2jpg_module._hdrplus_align_layers(  # pylint: disable=protected-access
        np_module=np,
        scalar_frames=np.stack([reference, alternate], axis=0),
        hdrplus_options=dng2jpg_module.HdrPlusOptions(),
    )

    assert alignments.dtype == np.int32
    assert np.all(alignments[0] == 0)
    central_offsets = alignments[1, 2:-2, 2:-2].reshape(-1, 2)
    assert central_offsets.size > 0
    median_x = int(np.median(central_offsets[:, 0]))
    median_y = int(np.median(central_offsets[:, 1]))
    assert median_x <= -1
    assert median_y <= -1


def test_hdrplus_temporal_merge_uses_alignment_offsets() -> None:
    """Temporal HDR+ weighting and merge must improve when alignment offsets are applied."""

    rng = np.random.default_rng(5678)
    reference_rgb_float32 = rng.integers(
        0,
        200,
        size=(64, 64, 3),
        dtype=np.uint16,
    ).astype(np.float32) / 65535.0
    alternate_rgb_float32 = _reflect_shift_rgb(
        reference_rgb_float32,
        shift_y=0,
        shift_x=2,
    )
    frames_rgb_float32 = np.stack([reference_rgb_float32, alternate_rgb_float32], axis=0)
    hdrplus_options = dng2jpg_module.HdrPlusOptions()
    scalar_frames = dng2jpg_module._hdrplus_build_scalar_proxy_float32(  # pylint: disable=protected-access
        np_module=np,
        frames_rgb_float32=frames_rgb_float32,
        hdrplus_options=hdrplus_options,
    )
    downsampled_scalar_frames = dng2jpg_module._hdrplus_box_down2_float32(  # pylint: disable=protected-access
        np_module=np,
        frames_float32=scalar_frames,
    )
    tile_start_positions_y = dng2jpg_module._hdrplus_compute_tile_start_positions(  # pylint: disable=protected-access
        np_module=np,
        axis_length=frames_rgb_float32.shape[1],
        tile_stride=dng2jpg_module.HDRPLUS_TILE_STRIDE,
        pad_margin=dng2jpg_module.HDRPLUS_TILE_SIZE,
    )
    tile_start_positions_x = dng2jpg_module._hdrplus_compute_tile_start_positions(  # pylint: disable=protected-access
        np_module=np,
        axis_length=frames_rgb_float32.shape[2],
        tile_stride=dng2jpg_module.HDRPLUS_TILE_STRIDE,
        pad_margin=dng2jpg_module.HDRPLUS_TILE_SIZE,
    )
    alignment_offsets = np.zeros(
        (2, len(tile_start_positions_y), len(tile_start_positions_x), 2),
        dtype=np.int32,
    )
    alignment_offsets[1, :, :, 0] = -2
    zero_offsets = np.zeros_like(alignment_offsets)

    aligned_weights, aligned_total = dng2jpg_module._hdrplus_compute_temporal_weights(  # pylint: disable=protected-access
        np_module=np,
        downsampled_scalar_frames=downsampled_scalar_frames,
        alignment_offsets=alignment_offsets,
        hdrplus_options=hdrplus_options,
    )
    zero_weights, zero_total = dng2jpg_module._hdrplus_compute_temporal_weights(  # pylint: disable=protected-access
        np_module=np,
        downsampled_scalar_frames=downsampled_scalar_frames,
        alignment_offsets=zero_offsets,
        hdrplus_options=hdrplus_options,
    )

    temporal_aligned = dng2jpg_module._hdrplus_merge_temporal_rgb(  # pylint: disable=protected-access
        np_module=np,
        frames_rgb_float32=frames_rgb_float32,
        alignment_offsets=alignment_offsets,
        weights=aligned_weights,
        total_weight=aligned_total,
        hdrplus_options=hdrplus_options,
    )
    temporal_zero = dng2jpg_module._hdrplus_merge_temporal_rgb(  # pylint: disable=protected-access
        np_module=np,
        frames_rgb_float32=frames_rgb_float32,
        alignment_offsets=zero_offsets,
        weights=zero_weights,
        total_weight=zero_total,
        hdrplus_options=hdrplus_options,
    )
    reference_tiles = dng2jpg_module._hdrplus_extract_overlapping_tiles(  # pylint: disable=protected-access
        np_module=np,
        frames_array=frames_rgb_float32[0:1],
        tile_size=dng2jpg_module.HDRPLUS_TILE_SIZE,
        tile_stride=dng2jpg_module.HDRPLUS_TILE_STRIDE,
        pad_margin=dng2jpg_module.HDRPLUS_TILE_SIZE
        + dng2jpg_module._hdrplus_compute_alignment_margin(  # pylint: disable=protected-access
            search_radius=hdrplus_options.search_radius
        ),
    )[0]
    aligned_error = float(np.mean(np.abs(temporal_aligned - reference_tiles)))
    zero_error = float(np.mean(np.abs(temporal_zero - reference_tiles)))
    assert aligned_error < zero_error


def test_hdrplus_temporal_runtime_options_preserve_code_domain_weights() -> None:
    """Temporal runtime remap must preserve the historical 16-bit-domain weight curve."""

    runtime_options = dng2jpg_module._hdrplus_resolve_temporal_runtime_options(  # pylint: disable=protected-access
        dng2jpg_module.HdrPlusOptions()
    )
    np.testing.assert_allclose(
        runtime_options.distance_factor,
        np.float32(8.0 / 65535.0),
        rtol=1e-6,
        atol=1e-9,
    )
    np.testing.assert_allclose(
        runtime_options.min_distance,
        np.float32(10.0 / 65535.0),
        rtol=1e-6,
        atol=1e-9,
    )
    np.testing.assert_allclose(
        runtime_options.max_weight_distance,
        np.float32(290.0),
        rtol=1e-6,
        atol=1e-6,
    )

    tile_start_positions_y = dng2jpg_module._hdrplus_compute_tile_start_positions(  # pylint: disable=protected-access
        np_module=np,
        axis_length=32,
        tile_stride=dng2jpg_module.HDRPLUS_TILE_STRIDE,
        pad_margin=dng2jpg_module.HDRPLUS_TILE_SIZE,
    )
    tile_start_positions_x = dng2jpg_module._hdrplus_compute_tile_start_positions(  # pylint: disable=protected-access
        np_module=np,
        axis_length=32,
        tile_stride=dng2jpg_module.HDRPLUS_TILE_STRIDE,
        pad_margin=dng2jpg_module.HDRPLUS_TILE_SIZE,
    )
    alignment_offsets = np.zeros(
        (2, len(tile_start_positions_y), len(tile_start_positions_x), 2),
        dtype=np.int32,
    )

    near_distance_frames = np.stack(
        [
            np.zeros((32, 32), dtype=np.float32),
            np.full((32, 32), 20.0 / 65535.0, dtype=np.float32),
        ],
        axis=0,
    )
    near_weights, _near_total = dng2jpg_module._hdrplus_compute_temporal_weights(  # pylint: disable=protected-access
        np_module=np,
        downsampled_scalar_frames=dng2jpg_module._hdrplus_box_down2_float32(  # pylint: disable=protected-access
            np_module=np,
            frames_float32=near_distance_frames,
        ),
        alignment_offsets=alignment_offsets,
        hdrplus_options=dng2jpg_module.HdrPlusOptions(),
    )
    np.testing.assert_allclose(
        near_weights,
        np.full_like(near_weights, 0.8, dtype=np.float32),
        rtol=1e-5,
        atol=1e-5,
    )

    far_distance_frames = np.stack(
        [
            np.zeros((32, 32), dtype=np.float32),
            np.full((32, 32), 3000.0 / 65535.0, dtype=np.float32),
        ],
        axis=0,
    )
    far_weights, _far_total = dng2jpg_module._hdrplus_compute_temporal_weights(  # pylint: disable=protected-access
        np_module=np,
        downsampled_scalar_frames=dng2jpg_module._hdrplus_box_down2_float32(  # pylint: disable=protected-access
            np_module=np,
            frames_float32=far_distance_frames,
        ),
        alignment_offsets=alignment_offsets,
        hdrplus_options=dng2jpg_module.HdrPlusOptions(),
    )
    np.testing.assert_array_equal(
        far_weights,
        np.zeros_like(far_weights, dtype=np.float32),
    )


def test_run_hdr_plus_merge_preserves_float_internal_and_float_io(monkeypatch) -> None:
    """HDR+ merge must keep normalized float32 intermediates and avoid uint16 staging."""

    bracket_images_float = [
        np.full((32, 32, 3), 1000 + (offset * 500), dtype=np.float32) / 65535.0
        for offset in range(3)
    ]

    call_trace: list[str] = []

    def _fail_uint16_conversion(**_kwargs):
        raise AssertionError("HDR+ merge called _to_uint16_image_array unexpectedly")

    def _fake_build_scalar_proxy_float32(*, np_module, frames_rgb_float32, hdrplus_options):
        del hdrplus_options  # Unused by fake stage.
        assert np_module is np
        assert frames_rgb_float32.dtype == np.float32
        assert float(np.min(frames_rgb_float32)) >= 0.0
        assert float(np.max(frames_rgb_float32)) <= 1.0
        call_trace.append("proxy")
        return np.zeros((3, 32, 32), dtype=np.float32)

    def _fake_align_layers(*, np_module, scalar_frames, hdrplus_options):
        del hdrplus_options  # Unused by fake stage.
        assert np_module is np
        assert scalar_frames.dtype.kind == "f"
        call_trace.append("align")
        return np.zeros((3, 5, 5, 2), dtype=np.int32)

    def _fake_compute_temporal_weights(
        *,
        np_module,
        downsampled_scalar_frames,
        alignment_offsets,
        hdrplus_options,
    ):
        del alignment_offsets, hdrplus_options  # Unused by fake stage.
        assert np_module is np
        assert downsampled_scalar_frames.dtype.kind == "f"
        call_trace.append("weights")
        return (
            np.zeros((2, 5, 5), dtype=np.float32),
            np.ones((5, 5), dtype=np.float32),
        )

    def _fake_merge_temporal_rgb(
        *,
        np_module,
        frames_rgb_float32,
        alignment_offsets,
        weights,
        total_weight,
        hdrplus_options,
    ):
        del alignment_offsets, weights, total_weight, hdrplus_options  # Unused by fake stage.
        assert np_module is np
        assert frames_rgb_float32.dtype.kind == "f"
        call_trace.append("merge_temporal")
        return np.zeros((5, 5, 32, 32, 3), dtype=np.float32)

    def _fake_merge_spatial_rgb(*, np_module, temporal_tiles, width, height):
        assert np_module is np
        assert temporal_tiles.dtype.kind == "f"
        call_trace.append("merge_spatial")
        return np.full((height, width, 3), 1234.0 / 65535.0, dtype=np.float32)

    monkeypatch.setattr(dng2jpg_module, "_to_uint16_image_array", _fail_uint16_conversion)
    monkeypatch.setattr(
        dng2jpg_module,
        "_hdrplus_build_scalar_proxy_float32",
        _fake_build_scalar_proxy_float32,
    )
    monkeypatch.setattr(dng2jpg_module, "_hdrplus_align_layers", _fake_align_layers)
    monkeypatch.setattr(
        dng2jpg_module,
        "_hdrplus_compute_temporal_weights",
        _fake_compute_temporal_weights,
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_hdrplus_merge_temporal_rgb",
        _fake_merge_temporal_rgb,
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_hdrplus_merge_spatial_rgb",
        _fake_merge_spatial_rgb,
    )

    output_image = dng2jpg_module._run_hdr_plus_merge(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        np_module=np,
        hdrplus_options=dng2jpg_module.HdrPlusOptions(),
    )

    assert call_trace == ["proxy", "align", "weights", "merge_temporal", "merge_spatial"]
    assert output_image.dtype == np.float32
    assert output_image.shape == (32, 32, 3)
    np.testing.assert_allclose(
        output_image,
        np.full((32, 32, 3), 1234.0 / 65535.0, dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )


def test_run_hdr_plus_merge_applies_resolved_merge_gamma_last(monkeypatch) -> None:
    """HDR+ merge must apply resolved merge gamma after spatial merge output."""

    bracket_images_float = [
        np.full((32, 32, 3), 0.1, dtype=np.float32),
        np.full((32, 32, 3), 0.3, dtype=np.float32),
        np.full((32, 32, 3), 0.6, dtype=np.float32),
    ]

    monkeypatch.setattr(
        dng2jpg_module,
        "_hdrplus_build_scalar_proxy_float32",
        lambda **_kwargs: np.zeros((3, 32, 32), dtype=np.float32),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_hdrplus_align_layers",
        lambda **_kwargs: np.zeros((3, 5, 5, 2), dtype=np.int32),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_hdrplus_compute_temporal_weights",
        lambda **_kwargs: (
            np.zeros((2, 5, 5), dtype=np.float32),
            np.ones((5, 5), dtype=np.float32),
        ),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_hdrplus_merge_temporal_rgb",
        lambda **_kwargs: np.zeros((5, 5, 32, 32, 3), dtype=np.float32),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_hdrplus_merge_spatial_rgb",
        lambda **_kwargs: np.full((32, 32, 3), 0.25, dtype=np.float32),
    )

    output_image = dng2jpg_module._run_hdr_plus_merge(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        np_module=np,
        hdrplus_options=dng2jpg_module.HdrPlusOptions(),
        resolved_merge_gamma=dng2jpg_module.ResolvedMergeGamma(
            request=dng2jpg_module.MergeGammaOption(
                mode="custom",
                linear_coeff=4.5,
                exponent=0.45,
            ),
            transfer="rec709",
            label="Rec.709 custom",
            param_a=4.5,
            param_b=0.45,
            evidence="cli-custom",
        ),
    )

    expected = np.full((32, 32, 3), 1.099 * (0.25**0.45) - 0.099, dtype=np.float32)
    np.testing.assert_allclose(output_image, expected, rtol=1e-6, atol=1e-6)


def test_run_debug_writes_extraction_and_merge_checkpoints(monkeypatch, tmp_path) -> None:
    """`run` must persist extraction and HDR merge boundary checkpoints."""

    input_dng = tmp_path / "scene.dng"
    input_dng.write_bytes(b"fake-dng")
    output_jpg = tmp_path / "scene.jpg"
    raw_pixels = np.array(
        [
            [[1000, 2000, 3000], [4000, 5000, 6000]],
            [[7000, 8000, 9000], [10000, 11000, 12000]],
        ],
        dtype=np.uint16,
    )

    class _FakeRawHandle:
        def __init__(self) -> None:
            self.raw_image_visible = np.zeros((2, 2), dtype=np.uint16)
            self.white_level = int(16383)
            self.black_level_per_channel = (127.0, 125.0, 128.0, 126.0)
            self.camera_whitebalance = (1.0, 1.0, 1.0, 0.0)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        def postprocess(
            self,
            *,
            output_bps,
            use_camera_wb,
            no_auto_bright,
            gamma,
            user_wb,
            output_color,
            no_auto_scale,
            user_flip,
        ) -> np.ndarray:
            del (
                output_bps,
                use_camera_wb,
                no_auto_bright,
                gamma,
                user_wb,
                output_color,
                no_auto_scale,
                user_flip,
            )
            return np.array(raw_pixels, copy=True)

    class _FakeRawPyModule:
        LibRawError = RuntimeError

        @staticmethod
        def imread(_path: str) -> _FakeRawHandle:
            return _FakeRawHandle()

    fake_imageio_module = _FakeImageIoModule(
        merged_rgb_u16=np.full((2, 2, 3), 32768, dtype=np.uint16)
    )
    fake_pil_module = _FakePilModule()
    debug_calls: list[tuple[str, str]] = []

    def _fake_write_debug(
        *,
        imageio_module,
        np_module,
        debug_context,
        stage_suffix,
        image_rgb_float,
    ):
        del imageio_module, np_module, image_rgb_float
        debug_calls.append((debug_context.input_stem, stage_suffix))
        return debug_context.output_dir / f"{debug_context.input_stem}{stage_suffix}.tiff"

    monkeypatch.setattr(
        dng2jpg_module,
        "_load_image_dependencies",
        lambda: (_FakeRawPyModule(), fake_imageio_module, fake_pil_module),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_dng_exif_payload_and_timestamp",
        lambda **_kwargs: (None, None, 1, 0.125),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_resolve_auto_adjust_dependencies",
        lambda: (_FakeOpenCvModule(), np),
    )
    monkeypatch.setattr(dng2jpg_module, "_write_debug_rgb_float_tiff", _fake_write_debug)
    monkeypatch.setattr(
        dng2jpg_module,
        "_postprocess",
        lambda **kwargs: kwargs["merged_image_float"],
    )
    monkeypatch.setattr(dng2jpg_module, "_encode_jpg", lambda **_kwargs: None)
    monkeypatch.setattr(
        dng2jpg_module,
        "_sync_output_file_timestamps_from_exif",
        lambda **_kwargs: None,
    )

    exit_code = dng2jpg_module.run(
        [
            str(input_dng),
            str(output_jpg),
            "--bracketing=1",
            "--hdr-merge=OpenCV-Merge",
            "--debug",
        ]
    )

    assert exit_code == 0
    extraction_stages = [stage for _stem, stage in debug_calls[:3]]
    merge_stages = [stage for _stem, stage in debug_calls[3:]]
    assert len(extraction_stages) == 3
    assert extraction_stages[0].startswith("_1.1_ev_min")
    assert extraction_stages[1].startswith("_1.2_ev_zero")
    assert extraction_stages[2].startswith("_1.3_ev_max")
    assert merge_stages == [
        "_2.0_hdr-merge_pre-merge-gamma",
        "_2.1_hdr-merge_post-merge-gamma",
        "_2.2_hdr-merge_final",
    ]


def test_run_auto_ev_prints_joint_candidate_diagnostics(monkeypatch, tmp_path, capsys) -> None:
    """Automatic runtime must print heuristic anchors and the selected joint solution."""

    input_dng = tmp_path / "scene.dng"
    input_dng.write_bytes(b"fake-dng")
    output_jpg = tmp_path / "scene.jpg"
    raw_pixels = np.array(
        [
            [[2000, 4000, 6000], [8000, 10000, 12000]],
            [[14000, 16000, 18000], [20000, 22000, 24000]],
        ],
        dtype=np.uint16,
    )

    class _FakeRawHandle:
        def __init__(self) -> None:
            self.raw_image_visible = np.zeros((2, 2), dtype=np.uint16)
            self.white_level = int(16383)
            self.camera_whitebalance = (1.0, 1.0, 1.0, 0.0)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        def postprocess(
            self,
            *,
            output_bps,
            use_camera_wb,
            no_auto_bright,
            gamma,
            user_wb,
            output_color,
            no_auto_scale,
            user_flip,
        ) -> np.ndarray:
            del (
                output_bps,
                use_camera_wb,
                no_auto_bright,
                gamma,
                user_wb,
                output_color,
                no_auto_scale,
                user_flip,
            )
            return np.array(raw_pixels, copy=True)

    class _FakeRawPyModule:
        LibRawError = RuntimeError

        @staticmethod
        def imread(_path: str) -> _FakeRawHandle:
            return _FakeRawHandle()

    fake_imageio_module = _FakeImageIoModule(
        merged_rgb_u16=np.full((2, 2, 3), 32768, dtype=np.uint16)
    )
    fake_pil_module = _FakePilModule()

    monkeypatch.setattr(
        dng2jpg_module,
        "_load_image_dependencies",
        lambda: (_FakeRawPyModule(), fake_imageio_module, fake_pil_module),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_dng_exif_payload_and_timestamp",
        lambda **_kwargs: (None, None, 1, 0.125),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_resolve_auto_adjust_dependencies",
        lambda: (_FakeOpenCvModule(), np),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_postprocess",
        lambda **kwargs: kwargs["merged_image_float"],
    )
    monkeypatch.setattr(dng2jpg_module, "_encode_jpg", lambda **_kwargs: None)
    monkeypatch.setattr(
        dng2jpg_module,
        "_sync_output_file_timestamps_from_exif",
        lambda **_kwargs: None,
    )

    exit_code = dng2jpg_module.run(
        [
            str(input_dng),
            str(output_jpg),
            "--bracketing=auto",
            "--hdr-merge=OpenCV-Merge",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Using exposure mode: static" in output
    assert "Using EV bracket delta: 0.1 (static)" in output
    assert "Exposure Misure EV ev_best:" in output
    assert "Exposure Misure EV ev_ettr:" in output
    assert "Exposure Misure EV ev_detail:" in output
    assert "Exposure planning selected ev_zero:" in output
    assert "Bracket step: skipped" in output
    assert "Exposure planning selected bracket half-span:" in output
    assert "Export EV triplet:" in output


def test_run_static_ev_uses_manual_center_and_reports_static_mode(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    """Static runtime must preserve manual center and avoid automatic diagnostics."""

    input_dng = tmp_path / "scene.dng"
    input_dng.write_bytes(b"fake-dng")
    output_jpg = tmp_path / "scene.jpg"
    raw_pixels = np.array(
        [
            [[1000, 2000, 3000], [4000, 5000, 6000]],
            [[7000, 8000, 9000], [10000, 11000, 12000]],
        ],
        dtype=np.uint16,
    )

    class _FakeRawHandle:
        def __init__(self) -> None:
            self.raw_image_visible = np.zeros((2, 2), dtype=np.uint16)
            self.white_level = int(16383)
            self.camera_whitebalance = (1.0, 1.0, 1.0, 0.0)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        def postprocess(
            self,
            *,
            output_bps,
            use_camera_wb,
            no_auto_bright,
            gamma,
            user_wb,
            output_color,
            no_auto_scale,
            user_flip,
        ) -> np.ndarray:
            del (
                output_bps,
                use_camera_wb,
                no_auto_bright,
                gamma,
                user_wb,
                output_color,
                no_auto_scale,
                user_flip,
            )
            return np.array(raw_pixels, copy=True)

    class _FakeRawPyModule:
        LibRawError = RuntimeError

        @staticmethod
        def imread(_path: str) -> _FakeRawHandle:
            return _FakeRawHandle()

    fake_imageio_module = _FakeImageIoModule(
        merged_rgb_u16=np.full((2, 2, 3), 32768, dtype=np.uint16)
    )
    fake_pil_module = _FakePilModule()

    monkeypatch.setattr(
        dng2jpg_module,
        "_load_image_dependencies",
        lambda: (_FakeRawPyModule(), fake_imageio_module, fake_pil_module),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_dng_exif_payload_and_timestamp",
        lambda **_kwargs: (None, None, 1, 0.125),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_resolve_auto_adjust_dependencies",
        lambda: (_FakeOpenCvModule(), np),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_postprocess",
        lambda **kwargs: kwargs["merged_image_float"],
    )
    monkeypatch.setattr(dng2jpg_module, "_encode_jpg", lambda **_kwargs: None)
    monkeypatch.setattr(
        dng2jpg_module,
        "_sync_output_file_timestamps_from_exif",
        lambda **_kwargs: None,
    )

    exit_code = dng2jpg_module.run(
        [
            str(input_dng),
            str(output_jpg),
            "--bracketing=1",
            "--exposure=0.5",
            "--hdr-merge=OpenCV-Merge",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Using exposure mode: static" in output
    assert "Using selected EV center (ev_zero): 0.5" in output
    assert "Using EV bracket delta: 1 (static)" in output
    assert "Exposure Misure EV ev_best:" not in output
    assert "Exposure Misure EV ev_ettr:" not in output
    assert "Exposure Misure EV ev_detail:" not in output


def test_run_skips_white_balance_when_mode_not_specified(monkeypatch, tmp_path) -> None:
    """Runtime must skip white-balance stage when `--auto-white-balance` is omitted."""

    input_dng = tmp_path / "scene.dng"
    input_dng.write_bytes(b"fake-dng")
    output_jpg = tmp_path / "scene.jpg"

    class _FakeRawHandle:
        output_color = "sRGB"
        tone_curve = [0, 128, 255]
        rgb_xyz_matrix = [[1.0, 0.0, 0.0]]
        color_matrix = [[1.0, 0.0, 0.0]]
        color_desc = b"RGBG"
        raw_image_visible = np.zeros((2, 2), dtype=np.uint16)
        white_level = int(16383)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

    class _FakeRawPyModule:
        LibRawError = RuntimeError

        @staticmethod
        def imread(_path: str) -> _FakeRawHandle:
            return _FakeRawHandle()

    fake_imageio_module = _FakeImageIoModule(
        merged_rgb_u16=np.full((2, 2, 3), 32768, dtype=np.uint16)
    )
    fake_pil_module = _FakePilModule()
    white_balance_calls: list[str] = []
    captured_brackets: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []

    monkeypatch.setattr(
        dng2jpg_module,
        "_load_image_dependencies",
        lambda: (_FakeRawPyModule(), fake_imageio_module, fake_pil_module),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_dng_exif_payload_and_timestamp",
        lambda **_kwargs: (None, None, 1, 0.125),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_exif_gamma_tags",
        lambda **_kwargs: dng2jpg_module.ExifGammaTags(
            color_space="1",
            interoperability_index=None,
        ),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_resolve_auto_adjust_dependencies",
        lambda: (_FakeOpenCvModule(), np),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_base_rgb_linear_float",
        lambda **_kwargs: np.full((2, 2, 3), 0.25, dtype=np.float32),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_bracket_images_float",
        lambda **_kwargs: (
            np.full((2, 2, 3), 0.125, dtype=np.float32),
            np.full((2, 2, 3), 0.25, dtype=np.float32),
            np.full((2, 2, 3), 0.5, dtype=np.float32),
        ),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_apply_white_balance_to_bracket_triplet",
        lambda **_kwargs: white_balance_calls.append("called"),
    )

    def _fake_run_opencv_merge_backend(**kwargs):
        bracket_images_float = kwargs["bracket_images_float"]
        captured_brackets.append(
            (
                np.array(bracket_images_float[0], copy=True),
                np.array(bracket_images_float[1], copy=True),
                np.array(bracket_images_float[2], copy=True),
            )
        )
        return np.full((2, 2, 3), 0.5, dtype=np.float32)

    monkeypatch.setattr(
        dng2jpg_module,
        "_run_opencv_merge_backend",
        _fake_run_opencv_merge_backend,
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_postprocess",
        lambda **kwargs: kwargs["merged_image_float"],
    )
    monkeypatch.setattr(dng2jpg_module, "_encode_jpg", lambda **_kwargs: None)
    monkeypatch.setattr(
        dng2jpg_module,
        "_sync_output_file_timestamps_from_exif",
        lambda **_kwargs: None,
    )

    exit_code = dng2jpg_module.run(
        [
            str(input_dng),
            str(output_jpg),
            "--bracketing=1",
            "--hdr-merge=OpenCV-Merge",
        ]
    )

    assert exit_code == 0
    assert white_balance_calls == []
    assert len(captured_brackets) == 1
    np.testing.assert_allclose(captured_brackets[0][0], 0.125, rtol=0.0, atol=0.0)
    np.testing.assert_allclose(captured_brackets[0][1], 0.25, rtol=0.0, atol=0.0)
    np.testing.assert_allclose(captured_brackets[0][2], 0.5, rtol=0.0, atol=0.0)


def test_run_routes_auto_white_balance_to_post_merge_stage(
    monkeypatch, tmp_path
) -> None:
    """Runtime must not apply white balance on bracket triplet before HDR merge."""

    input_dng = tmp_path / "scene.dng"
    input_dng.write_bytes(b"fake-dng")
    output_jpg = tmp_path / "scene.jpg"

    class _FakeRawHandle:
        output_color = "sRGB"
        tone_curve = [0, 128, 255]
        rgb_xyz_matrix = [[1.0, 0.0, 0.0]]
        color_matrix = [[1.0, 0.0, 0.0]]
        color_desc = b"RGBG"
        raw_image_visible = np.zeros((2, 2), dtype=np.uint16)
        white_level = int(16383)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

    class _FakeRawPyModule:
        LibRawError = RuntimeError

        @staticmethod
        def imread(_path: str) -> _FakeRawHandle:
            return _FakeRawHandle()

    fake_imageio_module = _FakeImageIoModule(
        merged_rgb_u16=np.full((2, 2, 3), 32768, dtype=np.uint16)
    )
    fake_pil_module = _FakePilModule()
    pre_merge_wb_calls: list[str] = []
    merge_input_triplets: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    encode_stage_inputs: list[np.ndarray] = []
    encode_modes: list[str | None] = []

    monkeypatch.setattr(
        dng2jpg_module,
        "_load_image_dependencies",
        lambda: (_FakeRawPyModule(), fake_imageio_module, fake_pil_module),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_dng_exif_payload_and_timestamp",
        lambda **_kwargs: (None, None, 1, 0.125),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_exif_gamma_tags",
        lambda **_kwargs: dng2jpg_module.ExifGammaTags(
            color_space="1",
            interoperability_index=None,
        ),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_resolve_auto_adjust_dependencies",
        lambda: (_FakeOpenCvModule(), np),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_base_rgb_linear_float",
        lambda **_kwargs: np.full((2, 2, 3), 0.8, dtype=np.float32),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_bracket_images_float",
        lambda **_kwargs: (
            np.full((2, 2, 3), 0.1, dtype=np.float32),
            np.full((2, 2, 3), 1.0, dtype=np.float32),
            np.full((2, 2, 3), 0.3, dtype=np.float32),
        ),
    )

    monkeypatch.setattr(
        dng2jpg_module,
        "_apply_white_balance_to_bracket_triplet",
        lambda **_kwargs: pre_merge_wb_calls.append("called"),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_run_opencv_merge_backend",
        lambda **_kwargs: (
            merge_input_triplets.append(tuple(np.array(image, copy=True) for image in _kwargs["bracket_images_float"])),
            np.full((2, 2, 3), 0.5, dtype=np.float32),
        )[1],
    )

    def _capture_encode_stage(**kwargs):
        encode_stage_inputs.append(np.array(kwargs["postprocessed_image_float"], copy=True))
        encode_modes.append(kwargs["postprocess_options"].auto_white_balance_mode)

    monkeypatch.setattr(
        dng2jpg_module,
        "_postprocess",
        lambda **kwargs: kwargs["merged_image_float"],
    )
    monkeypatch.setattr(dng2jpg_module, "_encode_jpg", _capture_encode_stage)
    monkeypatch.setattr(
        dng2jpg_module,
        "_sync_output_file_timestamps_from_exif",
        lambda **_kwargs: None,
    )

    exit_code = dng2jpg_module.run(
        [
            str(input_dng),
            str(output_jpg),
            "--bracketing=1",
            "--exposure=1",
            "--auto-white-balance=TTL",
            "--hdr-merge=OpenCV-Merge",
        ]
    )

    assert exit_code == 0
    assert pre_merge_wb_calls == []
    assert len(merge_input_triplets) == 1
    np.testing.assert_allclose(
        merge_input_triplets[0][0],
        np.full((2, 2, 3), 0.1, dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )
    np.testing.assert_allclose(
        merge_input_triplets[0][1],
        np.full((2, 2, 3), 1.0, dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )
    np.testing.assert_allclose(
        merge_input_triplets[0][2],
        np.full((2, 2, 3), 0.3, dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )
    assert len(encode_stage_inputs) == 1
    np.testing.assert_allclose(
        encode_stage_inputs[0],
        np.full((2, 2, 3), 0.5, dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )
    assert encode_modes == ["TTL"]


def test_run_prints_source_gamma_diagnostics(monkeypatch, tmp_path, capsys) -> None:
    """Runtime must print deterministic source gamma diagnostics from RAW metadata."""

    input_dng = tmp_path / "scene.dng"
    input_dng.write_bytes(b"fake-dng")
    output_jpg = tmp_path / "scene.jpg"

    class _FakeRawHandle:
        def __init__(self) -> None:
            self.raw_image_visible = np.zeros((2, 2), dtype=np.uint16)
            self.white_level = int(16383)
            self.output_color = "ProPhoto RGB"
            self.tone_curve = [0, 64, 128, 192, 255]
            self.rgb_xyz_matrix = None
            self.color_matrix = None
            self.color_desc = None
            self.camera_whitebalance = (1.0, 1.0, 1.0, 0.0)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        def postprocess(
            self,
            *,
            output_bps,
            use_camera_wb,
            no_auto_bright,
            gamma,
            user_wb,
            output_color,
            no_auto_scale,
            user_flip,
        ) -> np.ndarray:
            del (
                output_bps,
                use_camera_wb,
                no_auto_bright,
                gamma,
                user_wb,
                output_color,
                no_auto_scale,
                user_flip,
            )
            return np.full((2, 2, 3), 32768, dtype=np.uint16)

    class _FakeRawPyModule:
        LibRawError = RuntimeError

        @staticmethod
        def imread(_path: str) -> _FakeRawHandle:
            return _FakeRawHandle()

    fake_imageio_module = _FakeImageIoModule(
        merged_rgb_u16=np.full((2, 2, 3), 32768, dtype=np.uint16)
    )
    fake_pil_module = _FakePilModule()

    monkeypatch.setattr(
        dng2jpg_module,
        "_load_image_dependencies",
        lambda: (_FakeRawPyModule(), fake_imageio_module, fake_pil_module),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_dng_exif_payload_and_timestamp",
        lambda **_kwargs: (None, None, 1, 0.125),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_resolve_auto_adjust_dependencies",
        lambda: (_FakeOpenCvModule(), np),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_postprocess",
        lambda **kwargs: kwargs["merged_image_float"],
    )
    monkeypatch.setattr(dng2jpg_module, "_encode_jpg", lambda **_kwargs: None)
    monkeypatch.setattr(
        dng2jpg_module,
        "_sync_output_file_timestamps_from_exif",
        lambda **_kwargs: None,
    )

    exit_code = dng2jpg_module.run(
        [
            str(input_dng),
            str(output_jpg),
            "--bracketing=1",
            "--hdr-merge=OpenCV-Merge",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert (
        "Source gamma info: label=ProPhoto RGB; gamma=1.8; evidence=explicit-profile"
        in output
    )


def test_run_prints_merge_gamma_diagnostics(monkeypatch, tmp_path, capsys) -> None:
    """Runtime must print deterministic merge-gamma request and resolution diagnostics."""

    input_dng = tmp_path / "scene.dng"
    input_dng.write_bytes(b"fake-dng")
    output_jpg = tmp_path / "scene.jpg"

    class _FakeRawHandle:
        output_color = "ProPhoto RGB"
        tone_curve = [0, 128, 255]
        rgb_xyz_matrix = [[1.0, 0.0, 0.0]]
        color_matrix = [[1.0, 0.0, 0.0]]
        color_desc = b"RGBG"
        raw_image_visible = np.zeros((2, 2), dtype=np.uint16)
        white_level = int(16383)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

    class _FakeRawPyModule:
        LibRawError = RuntimeError

        @staticmethod
        def imread(_path: str) -> _FakeRawHandle:
            return _FakeRawHandle()

    fake_imageio_module = _FakeImageIoModule(
        merged_rgb_u16=np.full((2, 2, 3), 32768, dtype=np.uint16)
    )
    fake_pil_module = _FakePilModule()

    monkeypatch.setattr(
        dng2jpg_module,
        "_load_image_dependencies",
        lambda: (_FakeRawPyModule(), fake_imageio_module, fake_pil_module),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_dng_exif_payload_and_timestamp",
        lambda **_kwargs: (None, None, 1, 0.125),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_exif_gamma_tags",
        lambda **_kwargs: dng2jpg_module.ExifGammaTags(
            color_space="1",
            interoperability_index=None,
        ),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_resolve_auto_adjust_dependencies",
        lambda: (_FakeOpenCvModule(), np),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_base_rgb_linear_float",
        lambda **_kwargs: np.full((2, 2, 3), 0.25, dtype=np.float32),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_extract_bracket_images_float",
        lambda **_kwargs: (
            np.full((2, 2, 3), 0.125, dtype=np.float32),
            np.full((2, 2, 3), 0.25, dtype=np.float32),
            np.full((2, 2, 3), 0.5, dtype=np.float32),
        ),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_run_opencv_merge_backend",
        lambda **_kwargs: np.full((2, 2, 3), 0.5, dtype=np.float32),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_postprocess",
        lambda **kwargs: kwargs["merged_image_float"],
    )
    monkeypatch.setattr(dng2jpg_module, "_encode_jpg", lambda **_kwargs: None)
    monkeypatch.setattr(
        dng2jpg_module,
        "_sync_output_file_timestamps_from_exif",
        lambda **_kwargs: None,
    )

    exit_code = dng2jpg_module.run(
        [str(input_dng), str(output_jpg), "--bracketing=1", "--hdr-merge=OpenCV-Merge"]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Merge gamma request: auto" in output
    assert "Merge gamma EXIF inputs: ColorSpace=1; InteroperabilityIndex=missing" in output
    assert (
        "Merge gamma: request=auto; transfer=srgb; label=sRGB; params=-; "
        "linear(scale=12.92,limit=0.0031308); "
        "curve(scale=1.055,power=1/2.4,offset=-0.055); "
        "evidence=exif-colorspace=1"
        in output
    )
def test_run_opencv_merge_backend_requires_exif_exposure_time_for_radiance_modes() -> None:
    """OpenCV radiance modes must reject missing EXIF exposure time."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((1, 1, 3), 0.1, dtype=np.float32),
        np.full((1, 1, 3), 0.3, dtype=np.float32),
        np.full((1, 1, 3), 0.6, dtype=np.float32),
    ]

    with np.testing.assert_raises(ValueError):
        dng2jpg_module._run_opencv_merge_backend(  # pylint: disable=protected-access
            bracket_images_float=bracket_images_float,
            ev_value=1.0,
            ev_zero=0.0,
            source_exposure_time_seconds=None,
            opencv_merge_options=dng2jpg_module.OpenCvMergeOptions(
                merge_algorithm=dng2jpg_module.OPENCV_MERGE_ALGORITHM_DEBEVEC,
            ),
            auto_adjust_dependencies=(fake_cv2, np),
        )


def test_normalize_ifd_drops_scalar_int_for_undefined_type_7_tag() -> None:
    """Scalar int values for UNDEFINED (type-7) EXIF tags must be dropped before piexif.dump.

    Regression: tag 41729 (SceneType, type UNDEFINED) stored as scalar int
    in source DNG EXIF caused piexif.dump to raise a TypeError at runtime.
    _normalize_ifd_integer_like_values_for_piexif_dump must drop such entries.
    @satisfies REQ-042
    """

    class _FakePiexifModule:
        """Minimal piexif shim exposing TAGS with tag 41729 as type 7 (UNDEFINED)."""

        TAGS = {
            "Exif": {
                41729: {"name": "SceneType", "type": 7},
            },
        }

    exif_ifd: dict[int, object] = {41729: 1}
    exif_dict: dict[str, object] = {
        "0th": {},
        "Exif": exif_ifd,
        "GPS": {},
        "Interop": {},
        "1st": {},
    }

    dng2jpg_module._normalize_ifd_integer_like_values_for_piexif_dump(  # pylint: disable=protected-access
        piexif_module=_FakePiexifModule(),
        exif_dict=exif_dict,
    )

    assert 41729 not in exif_ifd, (
        "scalar int value for type-7 UNDEFINED tag 41729 must be dropped"
    )


def test_to_float32_image_array_replaces_non_finite_samples_with_zero() -> None:
    """Float32 normalization must clear `NaN` and infinities before clipping."""

    source = np.array(
        [[[np.nan, np.inf, -np.inf], [0.25, 1.5, 0.5]]],
        dtype=np.float32,
    )

    output = dng2jpg_module._to_float32_image_array(  # pylint: disable=protected-access
        np_module=np,
        image_data=source,
    )

    assert output.dtype == np.float32
    assert bool(np.all(np.isfinite(output)))
    np.testing.assert_allclose(
        output,
        np.array([[[0.0, 0.0, 0.0], [0.25, 1.0, 0.5]]], dtype=np.float32),
        rtol=0.0,
        atol=0.0,
    )


def test_ensure_three_channel_float_array_no_range_adjust_sanitizes_non_finite_payloads() -> None:
    """Three-channel no-range helper must sanitize grayscale and RGBA non-finite samples."""

    grayscale = np.array(
        [[np.nan, np.inf], [-np.inf, 0.5]],
        dtype=np.float32,
    )
    grayscale_output = (
        dng2jpg_module._ensure_three_channel_float_array_no_range_adjust(  # pylint: disable=protected-access
            np_module=np,
            image_data=grayscale,
        )
    )
    assert grayscale_output.shape == (2, 2, 3)
    assert bool(np.all(np.isfinite(grayscale_output)))
    np.testing.assert_allclose(grayscale_output[0, 0], [0.0, 0.0, 0.0], rtol=0.0, atol=0.0)
    np.testing.assert_allclose(grayscale_output[1, 1], [0.5, 0.5, 0.5], rtol=0.0, atol=0.0)

    rgba = np.array([[[0.2, np.nan, 0.4, np.inf]]], dtype=np.float32)
    rgba_output = dng2jpg_module._ensure_three_channel_float_array_no_range_adjust(  # pylint: disable=protected-access
        np_module=np,
        image_data=rgba,
    )
    assert rgba_output.shape == (1, 1, 3)
    assert bool(np.all(np.isfinite(rgba_output)))
    np.testing.assert_allclose(
        rgba_output[0, 0],
        [0.2, 0.0, 0.4],
        rtol=0.0,
        atol=1e-8,
    )


def test_coerce_positive_luminance_rejects_non_finite_values() -> None:
    """Preview luminance coercion must route NaN/Inf values to deterministic fallback."""

    fallback = 0.125
    assert (
        dng2jpg_module._coerce_positive_luminance(float("nan"), fallback)  # pylint: disable=protected-access
        == fallback
    )
    assert (
        dng2jpg_module._coerce_positive_luminance(float("inf"), fallback)  # pylint: disable=protected-access
        == fallback
    )
    assert (
        dng2jpg_module._coerce_positive_luminance(float("-inf"), fallback)  # pylint: disable=protected-access
        == fallback
    )
    assert (
        dng2jpg_module._coerce_positive_luminance(0.5, fallback)  # pylint: disable=protected-access
        == 0.5
    )


def test_extract_normalized_preview_luminance_stats_filters_non_finite_samples() -> None:
    """Preview luminance statistics must return finite normalized output for mixed input."""

    class _FakeRawHandle:
        """Minimal rawpy-like handle returning deterministic preview tensors."""

        def __init__(self, preview_rgb: np.ndarray) -> None:
            self._preview_rgb = np.array(preview_rgb, copy=True)

        def postprocess(self, **_kwargs) -> np.ndarray:
            return np.array(self._preview_rgb, copy=True)

    preview_rgb = np.array(
        [[[np.inf, 1.0, 0.9], [0.4, 0.5, 0.6], [np.nan, -np.inf, 0.2]]],
        dtype=np.float32,
    )

    p_low, p_median, p_high = dng2jpg_module._extract_normalized_preview_luminance_stats(  # pylint: disable=protected-access
        raw_handle=_FakeRawHandle(preview_rgb=preview_rgb),
    )

    assert bool(np.isfinite(p_low))
    assert bool(np.isfinite(p_median))
    assert bool(np.isfinite(p_high))
    assert 0.0 < p_low < 1.0
    assert 0.0 < p_median < 1.0
    assert 0.0 < p_high < 1.0


def test_extract_normalized_preview_luminance_stats_rejects_all_non_finite_samples() -> None:
    """Preview luminance statistics must fail fast when finite samples are unavailable."""

    class _FakeRawHandle:
        """Minimal rawpy-like handle returning deterministic preview tensors."""

        def __init__(self, preview_rgb: np.ndarray) -> None:
            self._preview_rgb = np.array(preview_rgb, copy=True)

        def postprocess(self, **_kwargs) -> np.ndarray:
            return np.array(self._preview_rgb, copy=True)

    preview_rgb = np.array(
        [[[np.nan, np.inf, -np.inf], [np.nan, np.inf, -np.inf]]],
        dtype=np.float32,
    )

    try:
        dng2jpg_module._extract_normalized_preview_luminance_stats(  # pylint: disable=protected-access
            raw_handle=_FakeRawHandle(preview_rgb=preview_rgb),
        )
    except ValueError as error:
        assert "Adaptive preview produced no valid luminance values" in str(error)
    else:
        raise AssertionError("Expected ValueError for preview payload without finite samples")


def test_calculate_ettr_ev_returns_zero_for_all_non_finite_samples() -> None:
    """ETTR evaluator must provide deterministic finite fallback for non-finite input."""

    luminance = np.array(
        [[np.nan, np.inf], [-np.inf, np.nan]],
        dtype=np.float32,
    )

    ev_value = dng2jpg_module._calculate_ettr_ev(  # pylint: disable=protected-access
        np_module=np,
        luminance_float=luminance,
    )

    assert ev_value == 0.0
    assert bool(np.isfinite(ev_value))


def test_calculate_detail_preservation_ev_returns_zero_for_all_non_finite_samples() -> None:
    """Detail evaluator must provide deterministic finite fallback for non-finite input."""

    luminance = np.array(
        [[np.nan, np.inf], [-np.inf, np.nan]],
        dtype=np.float32,
    )

    ev_value = dng2jpg_module._calculate_detail_preservation_ev(  # pylint: disable=protected-access
        _cv2_module=None,
        np_module=np,
        luminance_float=luminance,
    )

    assert ev_value == 0.0
    assert bool(np.isfinite(ev_value))


def test_ev_evaluators_keep_finite_outputs_with_mixed_non_finite_samples() -> None:
    """EV evaluators must produce finite values when mixed finite/non-finite samples exist."""

    luminance = np.array(
        [[0.1, np.nan], [np.inf, 0.8]],
        dtype=np.float32,
    )

    ev_ettr = dng2jpg_module._calculate_ettr_ev(  # pylint: disable=protected-access
        np_module=np,
        luminance_float=luminance,
    )
    ev_detail = dng2jpg_module._calculate_detail_preservation_ev(  # pylint: disable=protected-access
        _cv2_module=None,
        np_module=np,
        luminance_float=luminance,
    )

    assert bool(np.isfinite(ev_ettr))
    assert bool(np.isfinite(ev_detail))


def test_resolve_auto_ev_delta_rejects_all_non_finite_base_rgb() -> None:
    """Auto EV planning must fail fast when base RGB has no finite samples."""

    invalid_base = np.full((1, 2, 3), np.nan, dtype=np.float32)

    try:
        dng2jpg_module._resolve_auto_ev_delta(  # pylint: disable=protected-access
            np_module=np,
            base_rgb_float=invalid_base,
            ev_zero=0.0,
            auto_ev_options=dng2jpg_module.AutoEvOptions(step=0.5),
        )
    except ValueError as error:
        assert "finite RGB sample" in str(error)
    else:
        raise AssertionError("Expected ValueError for all-non-finite base RGB input")


def test_resolve_auto_ev_delta_enforces_iteration_guard_for_unreachable_thresholds() -> None:
    """Auto EV planning must fail deterministically when thresholds cannot be reached."""

    base_rgb_float = np.full((2, 2, 3), 0.5, dtype=np.float32)

    try:
        dng2jpg_module._resolve_auto_ev_delta(  # pylint: disable=protected-access
            np_module=np,
            base_rgb_float=base_rgb_float,
            ev_zero=0.0,
            auto_ev_options=dng2jpg_module.AutoEvOptions(
                shadow_clipping_pct=101.0,
                highlight_clipping_pct=101.0,
                step=0.1,
            ),
        )
    except ValueError as error:
        assert "maximum" in str(error)
    else:
        raise AssertionError("Expected deterministic ValueError when auto EV cannot converge")


def test_resolve_auto_ev_delta_terminates_with_sparse_non_finite_samples() -> None:
    """Auto EV planning must terminate when base RGB includes sparse non-finite samples."""

    base_rgb_float = np.array(
        [[[0.5, np.nan, 0.5], [0.25, 0.25, np.inf]]],
        dtype=np.float32,
    )
    ev_delta, iteration_steps = dng2jpg_module._resolve_auto_ev_delta(  # pylint: disable=protected-access
        np_module=np,
        base_rgb_float=base_rgb_float,
        ev_zero=0.0,
        auto_ev_options=dng2jpg_module.AutoEvOptions(
            shadow_clipping_pct=5.0,
            highlight_clipping_pct=5.0,
            step=0.5,
        ),
    )
    assert ev_delta >= 0.5
    assert len(iteration_steps) >= 1
    assert np.isfinite(ev_delta)
    assert np.isfinite(iteration_steps[-1].shadow_clipping_pct)
    assert np.isfinite(iteration_steps[-1].highlight_clipping_pct)


def test_analyze_luminance_key_ignores_non_finite_samples() -> None:
    """Luminance-key analysis must compute finite stats from finite-only samples."""

    luminance = np.array(
        [[0.0, np.nan, 0.8], [np.inf, 0.4, -np.inf]],
        dtype=np.float64,
    )
    analysis = dng2jpg_module._analyze_luminance_key(  # pylint: disable=protected-access
        np_module=np,
        luminance=luminance,
        eps=1e-6,
    )
    assert analysis["key_type"] in {"low-key", "normal-key", "high-key"}
    assert all(
        np.isfinite(float(analysis[key]))
        for key in ("log_avg_lum", "median_lum", "p05", "p95", "shadow_clip_in", "highlight_clip_in")
    )


def test_analyze_luminance_key_rejects_all_non_finite_samples() -> None:
    """Luminance-key analysis must fail with explicit error for invalid luminance."""

    luminance = np.array([[np.nan, np.inf], [-np.inf, np.nan]], dtype=np.float64)

    try:
        dng2jpg_module._analyze_luminance_key(  # pylint: disable=protected-access
            np_module=np,
            luminance=luminance,
            eps=1e-6,
        )
    except ValueError as error:
        assert "finite luminance sample" in str(error)
    else:
        raise AssertionError("Expected ValueError for all-non-finite luminance input")


def test_apply_auto_post_gamma_float_falls_back_when_gamma_is_non_finite() -> None:
    """Auto gamma must return identity when resolved gamma is non-finite."""

    image_rgb_float = np.full((2, 2, 3), 1.0, dtype=np.float32)
    options = dng2jpg_module.PostGammaAutoOptions(
        target_gray=0.5,
        luma_min=0.0,
        luma_max=1.1,
        lut_size=64,
    )

    output, resolved_gamma = dng2jpg_module._apply_auto_post_gamma_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        post_gamma_auto_options=options,
    )

    assert resolved_gamma == 1.0
    assert bool(np.all(np.isfinite(output)))
    np.testing.assert_allclose(output, image_rgb_float, rtol=0.0, atol=0.0)


def test_apply_auto_levels_float_sanitizes_non_finite_input() -> None:
    """Auto-levels output must remain finite when source RGB contains non-finite samples."""

    image_rgb_float = np.array(
        [[[np.nan, 0.2, np.inf], [-np.inf, 0.4, 0.6]]],
        dtype=np.float32,
    )

    output = dng2jpg_module._apply_auto_levels_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        auto_levels_options=dng2jpg_module.AutoLevelsOptions(),
    )

    assert output.shape == image_rgb_float.shape
    assert output.dtype == np.float32
    assert bool(np.all(np.isfinite(output)))


def test_apply_clahe_luminance_float_sanitizes_non_finite_luminance() -> None:
    """Float CLAHE must sanitize non-finite luminance before histogram indexing."""

    luminance = np.array(
        [[np.nan, 0.2], [np.inf, -np.inf]],
        dtype=np.float64,
    )
    output = dng2jpg_module._apply_clahe_luminance_float(  # pylint: disable=protected-access
        np_module=np,
        luminance_float=luminance,
        clip_limit=1.6,
        tile_grid_size=(2, 2),
    )
    assert output.shape == luminance.shape
    assert bool(np.all(np.isfinite(output)))
    assert float(np.min(output)) >= 0.0
    assert float(np.max(output)) <= 1.0


def test_vibrance_hsl_gamma_sanitizes_non_finite_rgb_samples() -> None:
    """HSL vibrance stage must sanitize non-finite RGB channel values."""

    rgb = np.array(
        [[[np.nan, 0.5, 0.2], [0.3, np.inf, -np.inf]]],
        dtype=np.float64,
    )
    output = dng2jpg_module._vibrance_hsl_gamma(  # pylint: disable=protected-access
        np_module=np,
        rgb=rgb,
        saturation_gamma=0.8,
    )
    assert output.shape == rgb.shape
    assert bool(np.all(np.isfinite(output)))


def test_apply_validated_auto_adjust_pipeline_sanitizes_stage_outputs(
    monkeypatch,
) -> None:
    """Auto-adjust must keep final RGB output finite even with non-finite stage payloads."""

    image_rgb_float = np.array(
        [[[np.nan, 0.5, np.inf], [0.4, -np.inf, 0.1]]],
        dtype=np.float32,
    )

    monkeypatch.setattr(
        dng2jpg_module,
        "_selective_blur_contrast_gated_vectorized",
        lambda _np_module, rgb, sigma, threshold_percent: rgb,
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_level_per_channel_adaptive",
        lambda _np_module, rgb, low_pct, high_pct: rgb,
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_apply_clahe_luma_rgb_float",
        lambda cv2_module, np_module, image_rgb_float, auto_adjust_options: image_rgb_float,
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_sigmoidal_contrast",
        lambda _np_module, rgb, contrast, midpoint: rgb,
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_vibrance_hsl_gamma",
        lambda _np_module, rgb, saturation_gamma: rgb,
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_high_pass_math_gray",
        lambda cv2_module, np_module, rgb, blur_sigma: np.array(
            [[np.nan, np.inf]],
            dtype=np.float64,
        ),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_overlay_composite",
        lambda np_module, base_rgb, overlay_gray: base_rgb + overlay_gray[..., None],
    )

    output = dng2jpg_module._apply_validated_auto_adjust_pipeline(  # pylint: disable=protected-access
        image_rgb_float=image_rgb_float,
        cv2_module=object(),
        np_module=np,
        auto_adjust_options=dng2jpg_module.AutoAdjustOptions(),
    )
    assert output.shape == image_rgb_float.shape
    assert output.dtype == np.float32
    assert bool(np.all(np.isfinite(output)))
