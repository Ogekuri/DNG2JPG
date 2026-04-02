# pyright: reportMissingImports=false
"""Unit tests for uint16 static postprocess and JPEG quantization boundary."""

from __future__ import annotations

import importlib.util
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


class _FakeOpenCvModule:
    """Minimal cv2 shim for deterministic `_run_opencv_hdr_merge` tests."""

    IMREAD_UNCHANGED = -1
    COLOR_BGR2RGB = 1
    COLOR_RGB2BGR = 2
    CV_32F = 5

    def __init__(self) -> None:
        self._images_by_path: dict[str, np.ndarray] = {}
        self.merge_mertens = _FakeMergeMertens()
        self.merge_debevec = _FakeMergeDebevec()
        self.merge_robertson = _FakeMergeRobertson()
        self.calibrate_debevec = _FakeCalibrateDebevec()
        self.calibrate_robertson = _FakeCalibrateRobertson()
        self.written_image: np.ndarray | None = None
        self.last_tonemap: _FakeTonemap | None = None

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
        np.clip(image_rgb_float.astype(np.float64) * 1.11, 0.0, 1.0).astype(np.float32),
        rtol=1e-6,
        atol=1e-6,
    )
    distance_to_u16_grid = np.abs(
        (output.astype(np.float64) * 65535.0)
        - np.round(output.astype(np.float64) * 65535.0)
    )
    assert np.any(distance_to_u16_grid > 1e-3)


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


def test_apply_static_postprocess_float_matches_legacy_within_quantization_tolerance() -> None:
    """Float static postprocess must preserve legacy transfer semantics."""

    image_rgb_float = np.array(
        [
            [[0.03125, 0.125, 0.21875], [0.34375, 0.4375, 0.53125]],
            [[0.65625, 0.75, 0.84375], [0.96875, 0.59375, 0.40625]],
        ],
        dtype=np.float32,
    )
    postprocess_options = dng2jpg_module.PostprocessOptions(
        post_gamma=1.07,
        brightness=1.13,
        contrast=1.11,
        saturation=1.09,
        jpg_compression=25,
        auto_brightness_enabled=False,
        auto_levels_enabled=False,
    )

    output = dng2jpg_module._apply_static_postprocess_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        postprocess_options=postprocess_options,
    )

    expected_float = np.power(image_rgb_float.astype(np.float64), 1.0 / 1.07)
    expected_float = np.clip(expected_float * 1.13, 0.0, 1.0)
    channel_mean = np.mean(expected_float, axis=(0, 1), keepdims=True)
    expected_float = np.clip(
        channel_mean + 1.11 * (expected_float - channel_mean),
        0.0,
        1.0,
    )
    grayscale = (
        (0.2126 * expected_float[:, :, 0])
        + (0.7152 * expected_float[:, :, 1])
        + (0.0722 * expected_float[:, :, 2])
    )[:, :, None]
    expected_float = np.clip(
        grayscale + 1.09 * (expected_float - grayscale),
        0.0,
        1.0,
    ).astype(np.float32)
    legacy_quantized = _legacy_static_postprocess_quantized_reference(
        image_rgb_float=image_rgb_float,
        postprocess_options=postprocess_options,
    )

    np.testing.assert_allclose(output, expected_float, rtol=1e-6, atol=1e-6)
    max_delta = float(np.max(np.abs(output.astype(np.float64) - legacy_quantized)))
    assert max_delta <= (6.0 / 65535.0), max_delta


def test_encode_jpg_quantizes_once_at_final_boundary(monkeypatch, tmp_path) -> None:
    """`_encode_jpg` must call float->uint8 conversion exactly once at JPEG boundary."""

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

    dng2jpg_module._encode_jpg(  # pylint: disable=protected-access
        imageio_module=imageio_module,
        pil_image_module=pil_module,
        merged_image_float=merged_rgb_float,
        output_jpg=tmp_path / "out.jpg",
        postprocess_options=_build_postprocess_options(),
        numpy_module=np,
    )

    assert call_trace.count("to_uint8") == 1
    assert call_trace.index("to_uint8") > call_trace.index("static")



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
    imageio_module = _FakeImageIoModule(
        merged_rgb_u16=(merged_rgb_float * 65535.0).astype(np.uint16)
    )
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
        imageio_module=imageio_module,
        pil_image_module=pil_module,
        merged_image_float=merged_rgb_float,
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
    """Debug mode must persist TIFF checkpoints in post-merge execution order."""

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
    dng2jpg_module._encode_jpg(  # pylint: disable=protected-access
        imageio_module=imageio_module,
        pil_image_module=pil_module,
        merged_image_float=merged_rgb_float,
        output_jpg=tmp_path / "out.jpg",
        postprocess_options=dng2jpg_module.PostprocessOptions(
            post_gamma=1.05,
            brightness=1.02,
            contrast=1.01,
            saturation=1.03,
            jpg_compression=25,
            auto_brightness_enabled=True,
            auto_levels_enabled=True,
            auto_adjust_enabled=False,
            debug_enabled=True,
        ),
        numpy_module=np,
        debug_context=debug_context,
    )

    assert call_trace == ["static", "auto-brightness", "auto-levels"]
    written_paths = [Path(path) for path, _image in imageio_module.writes]
    assert written_paths == [
        tmp_path / "sample_3.1_static_correction_gamma.tiff",
        tmp_path / "sample_3.2_static_correction_brightness.tiff",
        tmp_path / "sample_3.3_static_correction_contrast.tiff",
        tmp_path / "sample_3.4_static_correction_saturation.tiff",
        tmp_path / "sample_4.0_auto-brightness.tiff",
        tmp_path / "sample_5.0_auto-levels.tiff",
    ]
    for _path, image in imageio_module.writes:
        assert image.dtype == np.uint16
        assert image.shape[-1] == 3


def test_parse_run_options_accepts_remaining_auto_brightness_controls() -> None:
    """Parser must expose the surviving float-domain auto-brightness controls."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--ev=1",
            "--auto-brightness=enable",
            "--ab-key-value=0.22",
            "--ab-white-point-pct=99.5",
            "--ab-key-min=0.05",
            "--ab-key-max=0.7",
            "--ab-max-auto-boost=1.1",
            "--ab-enable-luminance-preserving-desat=false",
            "--ab-eps=1e-5",
            "--hdr-merge=OpenCV",
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
            "--ev=1",
            "--auto-adjust=enable",
            "--aa-enable-local-contrast=false",
            "--aa-local-contrast-strength=0.35",
            "--aa-clahe-clip-limit=1.7",
            "--aa-clahe-tile-grid-size=6x10",
            "--hdr-merge=OpenCV",
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

    def _fake_to_linear(*, np_module, image_srgb):
        del np_module, image_srgb  # Unused by fake stage.
        call_trace.append("to_linear")
        return np.full((1, 1, 3), 0.25, dtype=np.float64)

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

    def _fake_from_linear(*, np_module, image_linear):
        del np_module, image_linear  # Unused by fake stage.
        call_trace.append("from_linear")
        return np.full((1, 1, 3), 0.5, dtype=np.float64)

    monkeypatch.setattr(dng2jpg_module, "_to_linear_srgb", _fake_to_linear)
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
    monkeypatch.setattr(dng2jpg_module, "_from_linear_srgb", _fake_from_linear)

    output = dng2jpg_module._apply_auto_brightness_rgb_float(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_float=image_rgb_float,
        auto_brightness_options=dng2jpg_module.AutoBrightnessOptions(
            enable_luminance_preserving_desat=True,
        ),
    )

    assert output.dtype == np.float32
    assert call_trace == [
        "to_linear",
        "compute_luminance",
        "analyze",
        "choose",
        "reinhard",
        "desaturate",
        "from_linear",
    ]


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
    """Parser must accept `--hdr-merge=OpenCV` as backend selector."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev=1", "--hdr-merge=OpenCV"]
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
    assert opencv_merge_options.tonemap_gamma == 2.2


def test_parse_run_options_defaults_hdr_merge_to_opencv() -> None:
    """Parser must default backend selector to OpenCV when omitted."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev=1"]
    )
    assert parsed is not None
    assert parsed[6] is True
    assert parsed[5] is False
    assert parsed[10] is False


def test_resolve_default_postprocess_opencv_uses_updated_static_defaults() -> None:
    """OpenCV backend defaults must resolve to the updated static factors."""

    for algorithm in dng2jpg_module._OPENCV_MERGE_ALGORITHMS:  # pylint: disable=protected-access
        defaults = dng2jpg_module._resolve_default_postprocess(  # pylint: disable=protected-access
            dng2jpg_module.HDR_MERGE_MODE_OPENCV,
            dng2jpg_module.DEFAULT_LUMINANCE_TMO,
            opencv_merge_algorithm=algorithm,
        )
        assert defaults == (1.0, 1.0, 1.0, 1.0)


def test_print_help_orders_sections_by_pipeline_step(capsys) -> None:
    """Help output must follow pipeline step order and colocate stage knobs."""

    dng2jpg_module.print_help("test-version")
    output = capsys.readouterr().out

    assert output.index("Step 1 - Inputs and command surface") < output.index(
        "Step 2 - Exposure planning and RAW bracket extraction"
    )
    assert output.index(
        "Step 2 - Exposure planning and RAW bracket extraction"
    ) < output.index("Step 3 - HDR backend selection and backend-local configuration")
    assert output.index(
        "Step 3 - HDR backend selection and backend-local configuration"
    ) < output.index("Step 4 - Auto-brightness stage")
    assert output.index("Step 4 - Auto-brightness stage") < output.index(
        "Step 5 - Auto-levels stage"
    )
    assert output.index("Step 5 - Auto-levels stage") < output.index(
        "Step 6 - Static postprocess stage"
    )
    assert output.index("Step 6 - Static postprocess stage") < output.index(
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
    assert output.index("--hdr-merge <Luminace-HDR|OpenCV|HDR-Plus>") < output.index(
        "--opencv-merge-algorithm=<name>"
    )
    assert output.index("--hdr-merge <Luminace-HDR|OpenCV|HDR-Plus>") < output.index(
        "--hdrplus-proxy-mode=<name>"
    )
    assert output.index("--hdr-merge <Luminace-HDR|OpenCV|HDR-Plus>") < output.index(
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
        "--ev=<value>",
        "--auto-ev=<enable|disable>",
        "--ev-zero=<value>",
        "--auto-ev-shadow-clipping=<0..100>",
        "--auto-ev-highlight-clipping=<0..100>",
        "--auto-ev-step=<value>",
        "--hdr-merge <Luminace-HDR|OpenCV|HDR-Plus>",
        "--opencv-merge-algorithm=<name>",
        "--opencv-tonemap=<bool>",
        "--opencv-tonemap-gamma=<value>",
        "--hdrplus-proxy-mode=<name>",
        "--hdrplus-search-radius=<value>",
        "--hdrplus-temporal-factor=<value>",
        "--hdrplus-temporal-min-dist=<value>",
        "--hdrplus-temporal-max-dist=<value>",
        "--luminance-hdr-model=<name>",
        "--luminance-hdr-weight=<name>",
        "--luminance-hdr-response-curve=<name>",
        "--luminance-tmo=<name>",
        "--tmo* <value> | --tmo*=<value>",
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
        "--al-highlight-reconstruction-method <name>",
        "--al-gain-threshold=<value>",
        "--post-gamma=<value>",
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

    assert "Value options accept both `--option value` and `--option=value` forms." in output
    assert "Only accepted value: `linear`." in output
    assert "Allowed values: Debevec, Robertson, Mertens." in output
    assert "Allowed values: rggb, bt709, mean." in output
    assert "Effective only when `--hdr-merge OpenCV`." in output
    assert "Effective only when `--hdr-merge HDR-Plus`." in output
    assert "Effective only when `--hdr-merge Luminace-HDR`." in output
    assert "Default: `OpenCV`." in output
    assert output.count("Default:\n                                    `20`.") >= 2
    assert "Default: `Robertson`." in output
    assert "Default: `enable`." in output
    assert "Static postprocess defaults when omitted:" in output


def test_parse_run_options_rejects_unknown_hdr_merge_backend() -> None:
    """Parser must reject unknown `--hdr-merge` selector values."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev=1", "--hdr-merge=unknown-backend"]
    )
    assert parsed is None


def test_parse_run_options_auto_ev_defaults_and_disable_behavior(capsys) -> None:
    """`--auto-ev` must default to enabled and require another mode when disabled."""

    parsed_default_auto = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg"]
    )
    assert parsed_default_auto is not None
    assert parsed_default_auto[2] is None
    assert parsed_default_auto[3] is True
    auto_ev_options = parsed_default_auto[13]
    assert auto_ev_options.shadow_clipping_pct == 20.0
    assert auto_ev_options.highlight_clipping_pct == 20.0

    parsed_disabled_without_ev = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--auto-ev=disable"]
    )
    assert parsed_disabled_without_ev is None
    captured = capsys.readouterr()
    assert "No exposure mode selected: provide --ev or --auto-ev enable." in captured.err


def test_parse_run_options_rejects_auto_ev_with_static_ev(capsys) -> None:
    """`--auto-ev` and `--ev` must be mutually exclusive."""

    parsed_conflict = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev=1", "--auto-ev=enable"]
    )
    assert parsed_conflict is None
    captured = capsys.readouterr()
    assert "--auto-ev cannot be combined with --ev" in captured.err


def test_parse_run_options_static_ev_defaults_ev_zero_to_zero_with_unspecified_flag() -> None:
    """Static `--ev` without `--ev-zero` must preserve the unset manual-center flag."""

    parsed_static = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev=1.25"]
    )
    assert parsed_static is not None
    assert parsed_static[2] == 1.25
    assert parsed_static[3] is False
    assert parsed_static[11] == 0.0
    assert parsed_static[12] is False


def test_parse_run_options_static_ev_preserves_manual_ev_zero() -> None:
    """Static `--ev` with `--ev-zero` must preserve the manual center and flag."""

    parsed_static = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev=1.25", "--ev-zero=0.5"]
    )
    assert parsed_static is not None
    assert parsed_static[2] == 1.25
    assert parsed_static[3] is False
    assert parsed_static[11] == 0.5
    assert parsed_static[12] is True


def test_parse_run_options_rejects_ev_zero_without_ev(capsys) -> None:
    """`--ev-zero` must require static `--ev` mode."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev-zero=0.5"]
    )
    assert parsed is None
    captured = capsys.readouterr()
    assert "--ev-zero requires --ev" in captured.err


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
            "--auto-ev=enable",
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
            "--ev=1",
            "--hdr-merge=OpenCV",
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
    assert "--ldrTiff 16b" in captured
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


def test_select_ev_zero_candidate_chooses_minimum_absolute_value() -> None:
    """Default ev-zero selection must choose the minimum absolute-value candidate."""

    selected_ev_zero, selected_source = dng2jpg_module._select_ev_zero_candidate(  # pylint: disable=protected-access
        evaluations=dng2jpg_module.AutoZeroEvaluation(
            ev_best=-1.2,
            ev_ettr=0.3,
            ev_detail=-0.4,
        ),
        safe_ev_zero_max=3.0,
    )

    assert selected_ev_zero == 0.3
    assert selected_source == "ev_ettr"



def test_select_ev_zero_candidate_clamps_to_safe_range() -> None:
    """Default ev-zero selection must clamp candidates before comparing absolute value."""

    selected_ev_zero, selected_source = dng2jpg_module._select_ev_zero_candidate(  # pylint: disable=protected-access
        evaluations=dng2jpg_module.AutoZeroEvaluation(
            ev_best=-5.0,
            ev_ettr=2.0,
            ev_detail=0.8,
        ),
        safe_ev_zero_max=1.0,
    )

    assert selected_ev_zero == 0.8
    assert selected_source == "ev_detail"



def test_resolve_joint_auto_ev_solution_iterates_until_clipping_threshold() -> None:
    """Automatic EV planning must stop at the first step crossing either clipping threshold."""

    base_rgb_float = np.array([[[0.5, 0.5, 0.5], [0.25, 0.25, 0.25]]], dtype=np.float32)

    solution = dng2jpg_module._resolve_joint_auto_ev_solution(  # pylint: disable=protected-access
        raw_handle=None,
        bits_per_color=16,
        base_max_ev=4.0,
        auto_ev_options=dng2jpg_module.AutoEvOptions(
            shadow_clipping_pct=5.0,
            highlight_clipping_pct=5.0,
            step=0.5,
        ),
        auto_adjust_dependencies=(None, np),
        base_rgb_float=base_rgb_float,
    )

    assert solution.selected_source in {"ev_best", "ev_ettr", "ev_detail"}
    assert solution.ev_delta == 1.0
    assert [step.ev_delta for step in solution.iteration_steps] == [0.5, 1.0]
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



def test_run_opencv_hdr_merge_keeps_mertens_inputs_as_float32() -> None:
    """OpenCV merge must feed Mertens with backend-local float32 images."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.array([[[2048, 1024, 0], [8192, 4096, 3072]]], dtype=np.float32) / 65535.0,
        np.array([[[36000, 24000, 12000], [3000, 2000, 1000]]], dtype=np.float32)
        / 65535.0,
        np.array([[[50000, 60000, 65535], [20000, 30000, 40000]]], dtype=np.float32)
        / 65535.0,
    ]

    output = dng2jpg_module._run_opencv_hdr_merge(  # pylint: disable=protected-access
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
        ["input.dng", "output.jpg", "--ev=1", "--hdr-merge=OpenCV"]
    )
    assert parsed_default is not None
    default_options = parsed_default[8]
    assert default_options == dng2jpg_module.OpenCvMergeOptions(
        merge_algorithm=dng2jpg_module.OPENCV_MERGE_ALGORITHM_ROBERTSON,
        tonemap_enabled=True,
        tonemap_gamma=2.2,
    )

    parsed_override = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--ev=1",
            "--hdr-merge=OpenCV",
            "--opencv-merge-algorithm=Debevec",
            "--opencv-tonemap=off",
            "--opencv-tonemap-gamma=2.2",
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
            "--ev=1",
            "--hdr-merge=OpenCV",
            "--opencv-merge-algorithm=unknown",
        ]
    )
    assert invalid_algorithm is None

    invalid_tonemap = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--ev=1",
            "--hdr-merge=OpenCV",
            "--opencv-tonemap=maybe",
        ]
    )
    assert invalid_tonemap is None

    invalid_coupling = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--ev=1",
            "--hdr-merge=HDR-Plus",
            "--opencv-tonemap=on",
        ]
    )
    assert invalid_coupling is None


def test_run_opencv_hdr_merge_dispatches_debevec_uint8_radiance_path_with_tonemap() -> None:
    """OpenCV Debevec radiance path must quantize locally and return float output."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((1, 2, 3), 0.125, dtype=np.float32),
        np.full((1, 2, 3), 0.5, dtype=np.float32),
        np.full((1, 2, 3), 0.875, dtype=np.float32),
    ]

    output = dng2jpg_module._run_opencv_hdr_merge(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        ev_value=1.0,
        ev_zero=1.5,
        source_exposure_time_seconds=0.125,
        opencv_merge_options=dng2jpg_module.OpenCvMergeOptions(
            merge_algorithm=dng2jpg_module.OPENCV_MERGE_ALGORITHM_DEBEVEC,
            tonemap_enabled=True,
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
    assert fake_cv2.last_tonemap.gamma == 2.2
    assert output.dtype == np.float32
    assert float(np.min(output)) >= 0.0
    assert float(np.max(output)) <= 1.0


def test_run_opencv_hdr_merge_dispatches_robertson_uint8_radiance_path() -> None:
    """OpenCV Robertson radiance path must quantize locally and return float output."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((1, 1, 3), 0.2, dtype=np.float32),
        np.full((1, 1, 3), 0.4, dtype=np.float32),
        np.full((1, 1, 3), 0.8, dtype=np.float32),
    ]

    output = dng2jpg_module._run_opencv_hdr_merge(  # pylint: disable=protected-access
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


def test_run_opencv_hdr_merge_skips_tonemap_for_mertens() -> None:
    """Mertens path must not instantiate the OpenCV tonemap stage."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((1, 1, 3), 0.1, dtype=np.float32),
        np.full((1, 1, 3), 0.3, dtype=np.float32),
        np.full((1, 1, 3), 0.6, dtype=np.float32),
    ]

    _ = dng2jpg_module._run_opencv_hdr_merge(  # pylint: disable=protected-access
        bracket_images_float=bracket_images_float,
        ev_value=1.0,
        ev_zero=0.0,
        source_exposure_time_seconds=0.125,
        opencv_merge_options=dng2jpg_module.OpenCvMergeOptions(
            merge_algorithm=dng2jpg_module.OPENCV_MERGE_ALGORITHM_MERTENS,
            tonemap_enabled=True,
            tonemap_gamma=2.2,
        ),
        auto_adjust_dependencies=(fake_cv2, np),
    )

    assert fake_cv2.last_tonemap is None
    assert fake_cv2.merge_mertens.last_inputs is not None
    assert fake_cv2.merge_debevec.last_inputs is None
    assert fake_cv2.merge_robertson.last_inputs is None


def test_extract_bracket_images_float_uses_single_linear_base_pass() -> None:
    """Bracket extraction must use one linear RAW base pass plus NumPy scaling."""

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

        def postprocess(
            self,
            *,
            bright,
            output_bps,
            use_camera_wb,
            no_auto_bright,
            gamma,
            user_flip,
        ) -> np.ndarray:
            self.calls.append(
                {
                    "bright": bright,
                    "output_bps": output_bps,
                    "use_camera_wb": use_camera_wb,
                    "no_auto_bright": no_auto_bright,
                    "gamma": gamma,
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
        "bright": 1.0,
        "output_bps": 16,
        "use_camera_wb": True,
        "no_auto_bright": True,
        "gamma": (1.0, 1.0),
        "user_flip": 0,
    }
    base_rgb_float = base_rgb_u16.astype(np.float32) / 65535.0
    for bracket_image, multiplier in zip(bracket_images, multipliers):
        np.testing.assert_allclose(
            bracket_image,
            np.clip(base_rgb_float * multiplier, 0.0, 1.0).astype(np.float32),
            rtol=1e-6,
            atol=1e-6,
        )


def test_parse_run_options_defaults_gamma_to_auto() -> None:
    """Parser must default merge gamma to automatic EXIF/source resolution."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev=1"]
    )

    assert parsed is not None
    assert parsed[4].merge_gamma_option == dng2jpg_module.MergeGammaOption(mode="auto")


def test_parse_run_options_accepts_custom_gamma() -> None:
    """Parser must accept custom merge-gamma coefficient pairs."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev=1", "--gamma=4.5,0.45"]
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
        ["input.dng", "output.jpg", "--ev=1", "--gamma=4.5"]
    )
    invalid_non_positive = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev=1", "--gamma=0,0.45"]
    )

    assert invalid_shape is None
    assert invalid_non_positive is None


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

        def createMergeMertens(self) -> _ScalingMergeMertens:
            return self.merge_mertens

    scaled = dng2jpg_module._run_opencv_merge_mertens(  # pylint: disable=protected-access
        cv2_module=_ScalingCv2(),
        np_module=np,
        exposures_float=[np.full((1, 1, 3), 0.5, dtype=np.float32) for _ in range(3)],
    )

    np.testing.assert_allclose(
        scaled,
        np.array([[[0.25, 0.5, 1.0]]], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )


def test_run_opencv_hdr_merge_applies_resolved_merge_gamma_last() -> None:
    """OpenCV merge must apply resolved merge gamma after backend normalization."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((1, 1, 3), 0.1, dtype=np.float32),
        np.full((1, 1, 3), 0.3, dtype=np.float32),
        np.full((1, 1, 3), 0.6, dtype=np.float32),
    ]

    output = dng2jpg_module._run_opencv_hdr_merge(  # pylint: disable=protected-access
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
            "--ev=1",
            "--auto-levels=enable",
            "--al-clip-pct=0.5",
            "--al-clip-out-of-gamut=false",
            "--al-highlight-reconstruction",
            "--al-highlight-reconstruction-method",
            "Inpaint Opposed",
            "--al-gain-threshold=1.25",
            "--hdr-merge=OpenCV",
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
            "--ev=1",
            "--auto-levels=enable",
            "--al-highlight-reconstruction-method=Color Propagation",
            "--hdr-merge=OpenCV",
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
        np.array([[[65535, 60000, 40000]]], dtype=np.float32) / 65535.0,
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
            "--ev=1",
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
            "--ev=1",
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
    """`run` must persist extraction and merge debug checkpoints when enabled."""

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

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        def postprocess(
            self,
            *,
            bright,
            output_bps,
            use_camera_wb,
            no_auto_bright,
            gamma,
            user_flip,
        ) -> np.ndarray:
            del output_bps, use_camera_wb, no_auto_bright, gamma, user_flip
            return np.clip(raw_pixels.astype(np.float32) * float(bright), 0.0, 65535.0).astype(
                np.uint16
            )

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
            "--ev=1",
            "--hdr-merge=OpenCV",
            "--debug",
        ]
    )

    assert exit_code == 0
    assert debug_calls == [
        ("scene", "_1.1_ev_min-0.1"),
        ("scene", "_1.2_ev_zero+0.9"),
        ("scene", "_1.3_ev_max+1.9"),
        ("scene", "_2.0_hdr-merge"),
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

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        def postprocess(
            self,
            *,
            bright,
            output_bps,
            use_camera_wb,
            no_auto_bright,
            gamma,
            user_flip,
        ) -> np.ndarray:
            del output_bps, use_camera_wb, no_auto_bright, gamma, user_flip
            return np.clip(raw_pixels.astype(np.float32) * float(bright), 0.0, 65535.0).astype(
                np.uint16
            )

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
            "--auto-ev=enable",
            "--hdr-merge=OpenCV",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Using exposure mode: auto" in output
    assert "Exposure Misure EV ev_best:" in output
    assert "Exposure Misure EV ev_ettr:" in output
    assert "Exposure Misure EV ev_detail:" in output
    assert "Exposure planning selected ev_zero:" in output
    assert "Bracket step:" in output
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

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        def postprocess(
            self,
            *,
            bright,
            output_bps,
            use_camera_wb,
            no_auto_bright,
            gamma,
            user_flip,
        ) -> np.ndarray:
            del output_bps, use_camera_wb, no_auto_bright, gamma, user_flip
            return np.clip(raw_pixels.astype(np.float32) * float(bright), 0.0, 65535.0).astype(
                np.uint16
            )

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
            "--ev=1",
            "--ev-zero=0.5",
            "--hdr-merge=OpenCV",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Using exposure mode: static" in output
    assert "Using selected EV center (ev_zero): 0.5" in output
    assert "Using EV bracket delta: 1 (static)" in output
    assert "Exposure Misure EV ev_best:" in output
    assert "Exposure Misure EV ev_ettr:" in output
    assert "Exposure Misure EV ev_detail:" in output


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

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            del exc_type, exc, tb

        def postprocess(
            self,
            *,
            bright,
            output_bps,
            use_camera_wb,
            no_auto_bright,
            gamma,
            user_flip,
        ) -> np.ndarray:
            del bright, output_bps, use_camera_wb, no_auto_bright, gamma, user_flip
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
            "--ev=1",
            "--hdr-merge=OpenCV",
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
        "_run_opencv_hdr_merge",
        lambda **_kwargs: np.full((2, 2, 3), 0.5, dtype=np.float32),
    )
    monkeypatch.setattr(dng2jpg_module, "_encode_jpg", lambda **_kwargs: None)
    monkeypatch.setattr(
        dng2jpg_module,
        "_sync_output_file_timestamps_from_exif",
        lambda **_kwargs: None,
    )

    exit_code = dng2jpg_module.run(
        [str(input_dng), str(output_jpg), "--ev=1", "--hdr-merge=OpenCV"]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Merge gamma request: auto" in output
    assert "Merge gamma EXIF inputs: ColorSpace=1; InteroperabilityIndex=missing" in output
    assert (
        "Merge gamma: request=auto; transfer=srgb; label=sRGB; params=-; evidence=exif-colorspace=1"
        in output
    )
def test_run_opencv_hdr_merge_requires_exif_exposure_time_for_radiance_modes() -> None:
    """OpenCV radiance modes must reject missing EXIF exposure time."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_images_float = [
        np.full((1, 1, 3), 0.1, dtype=np.float32),
        np.full((1, 1, 3), 0.3, dtype=np.float32),
        np.full((1, 1, 3), 0.6, dtype=np.float32),
    ]

    with np.testing.assert_raises(ValueError):
        dng2jpg_module._run_opencv_hdr_merge(  # pylint: disable=protected-access
            bracket_images_float=bracket_images_float,
            ev_value=1.0,
            ev_zero=0.0,
            source_exposure_time_seconds=None,
            opencv_merge_options=dng2jpg_module.OpenCvMergeOptions(
                merge_algorithm=dng2jpg_module.OPENCV_MERGE_ALGORITHM_DEBEVEC,
            ),
            auto_adjust_dependencies=(fake_cv2, np),
        )
