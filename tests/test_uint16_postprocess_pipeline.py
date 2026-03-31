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
        hdr_base = self.last_inputs[1].astype(np.float32) / 255.0
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
        hdr_base = self.last_inputs[1].astype(np.float32) / 255.0
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
    postprocess = parsed[5]
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
    postprocess = parsed[5]
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
    assert (
        opencv_merge_options.merge_algorithm
        == dng2jpg_module.DEFAULT_OPENCV_MERGE_ALGORITHM
    )
    assert opencv_merge_options.tonemap_enabled is True
    assert opencv_merge_options.tonemap_gamma == 1.0


def test_parse_run_options_defaults_hdr_merge_to_opencv() -> None:
    """Parser must default backend selector to OpenCV when omitted."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev=1"]
    )
    assert parsed is not None
    assert parsed[7] is True
    assert parsed[6] is False
    assert parsed[11] is False


def test_resolve_default_postprocess_opencv_uses_updated_static_defaults() -> None:
    """OpenCV backend defaults must resolve to the updated static factors."""

    defaults = dng2jpg_module._resolve_default_postprocess(  # pylint: disable=protected-access
        dng2jpg_module.HDR_MERGE_MODE_OPENCV,
        dng2jpg_module.DEFAULT_LUMINANCE_TMO,
    )

    assert defaults == (1.0, 1.0, 1.0, 1.0)


def test_parse_run_options_rejects_unknown_hdr_merge_backend() -> None:
    """Parser must reject unknown `--hdr-merge` selector values."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev=1", "--hdr-merge=unknown-backend"]
    )
    assert parsed is None


def test_parse_run_options_auto_ev_defaults_and_override_behavior(capsys) -> None:
    """`--auto-ev` defaults and `--ev` override must be deterministic."""

    parsed_default_auto = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg"]
    )
    assert parsed_default_auto is not None
    assert parsed_default_auto[2] is None
    assert parsed_default_auto[3] is True

    parsed_disabled_without_ev = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--auto-ev=disable"]
    )
    assert parsed_disabled_without_ev is None

    parsed_override = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev=1", "--auto-ev=enable"]
    )
    assert parsed_override is not None
    assert parsed_override[2] == 1.0
    assert parsed_override[3] is False
    captured = capsys.readouterr()
    assert "Ignoring --auto-ev because --ev is specified." in captured.out


def test_parse_run_options_auto_zero_defaults_and_override_behavior(capsys) -> None:
    """`--auto-zero` defaults and `--ev-zero` override must be deterministic."""

    parsed_default_auto_zero = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg"]
    )
    assert parsed_default_auto_zero is not None
    assert parsed_default_auto_zero[13] is True

    parsed_default_manual_zero = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev-zero=0.5"]
    )
    assert parsed_default_manual_zero is not None
    assert parsed_default_manual_zero[12] == 0.5
    assert parsed_default_manual_zero[13] is False

    parsed_override_zero = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--ev-zero=0.5", "--auto-zero=enable"]
    )
    assert parsed_override_zero is not None
    assert parsed_override_zero[13] is False
    captured = capsys.readouterr()
    assert "Ignoring --auto-zero because --ev-zero is specified." in captured.out


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
    assert parsed[5].auto_adjust_enabled is True


def test_parse_run_options_disables_auto_adjust_and_rejects_knobs() -> None:
    """Disabled auto-adjust must reject any `--aa-*` knob overrides."""

    parsed_disabled = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        ["input.dng", "output.jpg", "--auto-adjust=disable"]
    )
    assert parsed_disabled is not None
    assert parsed_disabled[5].auto_adjust_enabled is False

    parsed_with_knob = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--auto-adjust=disable",
            "--aa-clahe-clip-limit=1.7",
        ]
    )
    assert parsed_with_knob is None


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
        np.array([2 ** -0.5, 1.0, 2**0.5], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )


def test_run_opencv_hdr_merge_adapts_mertens_inputs_to_uint8() -> None:
    """OpenCV merge must feed Mertens with backend-local uint8 images."""

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
        opencv_merge_options=dng2jpg_module.OpenCvMergeOptions(
            merge_algorithm=dng2jpg_module.OPENCV_MERGE_ALGORITHM_MERTENS
        ),
        auto_adjust_dependencies=(fake_cv2, np),
    )

    assert fake_cv2.merge_mertens.last_inputs is not None
    assert all(
        frame.dtype == np.uint8 for frame in fake_cv2.merge_mertens.last_inputs
    ), "Mertens input must be adapted to uint8 for OpenCV compatibility"
    assert all(
        float(np.min(frame)) >= 0.0 and float(np.max(frame)) <= 255.0
        for frame in fake_cv2.merge_mertens.last_inputs
    ), "Mertens input must stay on OpenCV-compatible 8-bit scale"
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
    default_options = parsed_default[9]
    assert default_options == dng2jpg_module.OpenCvMergeOptions(
        merge_algorithm=dng2jpg_module.OPENCV_MERGE_ALGORITHM_ROBERTSON,
        tonemap_enabled=True,
        tonemap_gamma=1.0,
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
    override_options = parsed_override[9]
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


def test_run_opencv_hdr_merge_dispatches_debevec_path_with_tonemap() -> None:
    """OpenCV merge must dispatch Debevec calibration, merge, and tone-map stages."""

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
    np.testing.assert_allclose(
        fake_cv2.calibrate_debevec.last_times,
        np.array([0.5, 1.0, 2.0], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )
    np.testing.assert_allclose(
        fake_cv2.merge_debevec.last_times,
        np.array([0.5, 1.0, 2.0], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )
    assert all(frame.dtype == np.uint8 for frame in fake_cv2.merge_debevec.last_inputs)
    assert fake_cv2.last_tonemap.gamma == 1.0
    assert output.dtype == np.float32
    assert float(np.min(output)) >= 0.0
    assert float(np.max(output)) <= 1.0


def test_run_opencv_hdr_merge_dispatches_robertson_path() -> None:
    """OpenCV merge must dispatch Robertson calibration and merge stages."""

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
    np.testing.assert_allclose(
        fake_cv2.calibrate_robertson.last_times,
        np.array([2 ** -0.5, 1.0, 2**0.5], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
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
            "--al-highlight-reconstruction-method",
            "Inpaint Opposed",
            "--al-gain-threshold=1.25",
            "--hdr-merge=OpenCV",
        ]
    )
    assert parsed is not None
    postprocess = parsed[5]
    assert postprocess.auto_levels_enabled is True
    assert postprocess.auto_levels_options.clip_percent == 0.5
    assert postprocess.auto_levels_options.clip_out_of_gamut is False
    assert postprocess.auto_levels_options.highlight_reconstruction_enabled is True
    assert (
        postprocess.auto_levels_options.highlight_reconstruction_method
        == "Inpaint Opposed"
    )
    assert postprocess.auto_levels_options.gain_threshold == 1.25


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


def test_apply_auto_levels_clip_out_of_gamut_normalizes_triplet(monkeypatch) -> None:
    """Out-of-gamut clipping must preserve channel ratios instead of hard clipping."""

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
        np.array([[[1.0, 0.75, 0.5]]], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )


def test_apply_auto_levels_color_methods_preserve_float_pipeline(monkeypatch) -> None:
    """New method selectors must dispatch on float internals and preserve float output."""

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
        lambda **_kwargs: {"gain": 1.0},
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
    hdrplus_options = parsed[10]
    enable_hdr_plus = parsed[11]
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
