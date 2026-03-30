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


class _FakePathImageIoModule:
    """Minimal imageio shim with per-path deterministic image payloads."""

    def __init__(self) -> None:
        self._images_by_path: dict[str, np.ndarray] = {}
        self.writes: list[tuple[str, np.ndarray]] = []

    def register_image(self, path: Path, image: np.ndarray) -> None:
        self._images_by_path[str(path)] = np.array(image, copy=True)

    def imread(self, path: str) -> np.ndarray:
        image = self._images_by_path.get(path)
        if image is None:
            raise AssertionError(f"Unexpected imageio read path: {path}")
        return np.array(image, copy=True)

    def imwrite(self, path: str, image: np.ndarray) -> None:
        self.writes.append((path, np.array(image, copy=True)))


class _FakeMergeMertens:
    """Minimal OpenCV MergeMertens shim for HDR backend tests."""

    def __init__(self) -> None:
        self.last_inputs: list[np.ndarray] | None = None

    def process(self, images: list[np.ndarray]) -> np.ndarray:
        self.last_inputs = [np.array(image, copy=True) for image in images]
        output_shape = self.last_inputs[0].shape
        return np.full(output_shape, 0.35, dtype=np.float32)


class _FakeMergeDebevec:
    """Minimal OpenCV MergeDebevec shim for HDR backend tests."""

    def __init__(self) -> None:
        self.last_inputs: list[np.ndarray] | None = None
        self.last_times: np.ndarray | None = None

    def process(self, images: list[np.ndarray], times: np.ndarray) -> np.ndarray:
        self.last_inputs = [np.array(image, copy=True) for image in images]
        self.last_times = np.array(times, copy=True)
        hdr_base = self.last_inputs[1].astype(np.float32)
        return (hdr_base * 4.0) + 1.0


class _FakeOpenCvModule:
    """Minimal cv2 shim for deterministic `_run_opencv_hdr_merge` tests."""

    IMREAD_UNCHANGED = -1
    COLOR_BGR2RGB = 1
    COLOR_RGB2BGR = 2

    def __init__(self) -> None:
        self._images_by_path: dict[str, np.ndarray] = {}
        self.merge_mertens = _FakeMergeMertens()
        self.merge_debevec = _FakeMergeDebevec()
        self.written_image: np.ndarray | None = None

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

    def imwrite(self, _path: str, image: np.ndarray) -> bool:
        self.written_image = np.array(image, copy=True)
        return True


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


def test_parse_run_options_accepts_all_original_auto_brightness_controls() -> None:
    """Parser must expose every control carried by the original TonemapParams."""

    parsed = dng2jpg_module._parse_run_options(  # pylint: disable=protected-access
        [
            "input.dng",
            "output.jpg",
            "--ev=1",
            "--auto-brightness",
            "--ab-key-value=0.22",
            "--ab-white-point-pct=99.5",
            "--ab-key-min=0.05",
            "--ab-key-max=0.7",
            "--ab-max-auto-boost=1.1",
            "--ab-enable-local-contrast=false",
            "--ab-local-contrast-strength=0.3",
            "--ab-clahe-clip-limit=1.7",
            "--ab-clahe-tile-grid-size=6x10",
            "--ab-enable-luminance-preserving-desat=false",
            "--ab-eps=1e-5",
            "--enable-opencv",
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
        enable_mild_local_contrast=False,
        local_contrast_strength=0.3,
        clahe_clip_limit=1.7,
        clahe_tile_grid_size=(6, 10),
        enable_luminance_preserving_desat=False,
        eps=1e-5,
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


def test_apply_auto_brightness_rgb_uint16_executes_original_stage_order(
    monkeypatch,
) -> None:
    """Auto-brightness must keep the original stage order inside the uint16 port."""

    call_trace: list[str] = []
    image_rgb_uint16 = np.array([[[1024, 2048, 4096]]], dtype=np.uint16)
    fake_cv2 = _FakeOpenCvModule()

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

    def _fake_local_contrast(*, cv2_module, np_module, image_bgr_uint16, options):
        del cv2_module, np_module, options  # Unused by fake stage.
        call_trace.append("local_contrast")
        return image_bgr_uint16

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
    monkeypatch.setattr(
        dng2jpg_module,
        "_apply_mild_local_contrast_bgr_uint16",
        _fake_local_contrast,
    )

    output = dng2jpg_module._apply_auto_brightness_rgb_uint16(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_uint16=image_rgb_uint16,
        auto_brightness_options=dng2jpg_module.AutoBrightnessOptions(
            enable_mild_local_contrast=True,
            local_contrast_strength=0.2,
            enable_luminance_preserving_desat=True,
        ),
        cv2_module=fake_cv2,
    )

    assert output.dtype == np.uint16
    assert call_trace == [
        "to_linear",
        "compute_luminance",
        "analyze",
        "choose",
        "reinhard",
        "desaturate",
        "from_linear",
        "local_contrast",
    ]


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


def test_run_opencv_hdr_merge_normalizes_mertens_inputs_to_unit_float32(tmp_path) -> None:
    """OpenCV merge must feed Mertens with [0,1] float32 images from uint16 brackets."""

    fake_cv2 = _FakeOpenCvModule()
    bracket_paths = [
        tmp_path / "ev_minus.tif",
        tmp_path / "ev_zero.tif",
        tmp_path / "ev_plus.tif",
    ]
    minus_bgr = np.array(
        [[[0, 1024, 2048], [3072, 4096, 8192]]],
        dtype=np.uint16,
    )
    zero_bgr = np.array(
        [[[12000, 24000, 36000], [1000, 2000, 3000]]],
        dtype=np.uint16,
    )
    plus_bgr = np.array(
        [[[65535, 60000, 50000], [40000, 30000, 20000]]],
        dtype=np.uint16,
    )
    fake_cv2.register_image(bracket_paths[0], minus_bgr)
    fake_cv2.register_image(bracket_paths[1], zero_bgr)
    fake_cv2.register_image(bracket_paths[2], plus_bgr)

    dng2jpg_module._run_opencv_hdr_merge(  # pylint: disable=protected-access
        bracket_paths=bracket_paths,
        output_hdr_tiff=tmp_path / "merged_hdr.tif",
        ev_value=1.0,
        ev_zero=0.0,
        opencv_merge_options=dng2jpg_module.OpenCvMergeOptions(),
        auto_adjust_opencv_dependencies=(fake_cv2, np),
    )

    assert fake_cv2.merge_mertens.last_inputs is not None
    assert fake_cv2.merge_debevec.last_inputs is not None
    assert all(
        frame.dtype == np.float32 for frame in fake_cv2.merge_mertens.last_inputs
    ), "Mertens input must be float32 to avoid uint16-scale artifacts"
    assert all(
        float(np.min(frame)) >= 0.0 and float(np.max(frame)) <= 1.0
        for frame in fake_cv2.merge_mertens.last_inputs
    ), "Mertens input must be normalized to [0,1]"
    assert all(
        frame.dtype == np.uint16 for frame in fake_cv2.merge_debevec.last_inputs
    ), "Debevec input must remain uint16 for HDR radiance estimation"
    assert fake_cv2.written_image is not None
    assert fake_cv2.written_image.dtype == np.uint16


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
            "--auto-levels",
            "--al-clip-pct=0.5",
            "--al-clip-out-of-gamut=false",
            "--al-highlight-reconstruction-method",
            "Inpaint Opposed",
            "--al-gain-threshold=1.25",
            "--enable-opencv",
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

    image_rgb_uint16 = np.array([[[40000, 30000, 20000]]], dtype=np.uint16)

    monkeypatch.setattr(
        dng2jpg_module,
        "_build_autoexp_histogram_rgb_uint16",
        lambda **_kwargs: np.zeros(1, dtype=np.uint64),
    )
    monkeypatch.setattr(
        dng2jpg_module,
        "_compute_auto_levels_from_histogram",
        lambda **_kwargs: {"gain": 2.0},
    )

    disabled = dng2jpg_module._apply_auto_levels_uint16(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_uint16=image_rgb_uint16,
        auto_levels_options=dng2jpg_module.AutoLevelsOptions(
            clip_out_of_gamut=False,
        ),
    )
    enabled = dng2jpg_module._apply_auto_levels_uint16(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_uint16=image_rgb_uint16,
        auto_levels_options=dng2jpg_module.AutoLevelsOptions(
            clip_out_of_gamut=True,
        ),
    )

    np.testing.assert_array_equal(disabled, np.array([[[65535, 60000, 40000]]], dtype=np.uint16))
    np.testing.assert_array_equal(enabled, np.array([[[65535, 49151, 32768]]], dtype=np.uint16))


def test_apply_auto_levels_color_methods_preserve_uint16_pipeline(monkeypatch) -> None:
    """New method selectors must dispatch on float internals and preserve uint16 output."""

    image_rgb_uint16 = np.array(
        [[[1000, 2000, 3000], [4000, 5000, 6000]]],
        dtype=np.uint16,
    )
    call_trace: list[tuple[str, float | None]] = []

    monkeypatch.setattr(
        dng2jpg_module,
        "_build_autoexp_histogram_rgb_uint16",
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

    color_output = dng2jpg_module._apply_auto_levels_uint16(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_uint16=image_rgb_uint16,
        auto_levels_options=dng2jpg_module.AutoLevelsOptions(
            highlight_reconstruction_enabled=True,
            highlight_reconstruction_method="Color Propagation",
            clip_out_of_gamut=False,
        ),
    )
    inpaint_output = dng2jpg_module._apply_auto_levels_uint16(  # pylint: disable=protected-access
        np_module=np,
        image_rgb_uint16=image_rgb_uint16,
        auto_levels_options=dng2jpg_module.AutoLevelsOptions(
            highlight_reconstruction_enabled=True,
            highlight_reconstruction_method="Inpaint Opposed",
            gain_threshold=1.25,
            clip_out_of_gamut=False,
        ),
    )

    assert color_output.dtype == np.uint16
    assert inpaint_output.dtype == np.uint16
    np.testing.assert_array_equal(
        color_output,
        np.array([[[1100, 2100, 3100], [4100, 5100, 6100]]], dtype=np.uint16),
    )
    np.testing.assert_array_equal(
        inpaint_output,
        np.array([[[1200, 2200, 3200], [4200, 5200, 6200]]], dtype=np.uint16),
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
            "--enable-hdr-plus",
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
            "--enable-hdr-plus",
            "--hdrplus-temporal-min-dist=30",
            "--hdrplus-temporal-max-dist=30",
        ]
    )

    assert parsed is None


def test_hdrplus_proxy_rggb_matches_green_weighted_scalar() -> None:
    """`rggb` proxy mode must match the Bayer-inspired green-weighted scalar."""

    frames_rgb_uint16 = np.array(
        [
            [
                [[100, 200, 300], [500, 1000, 1500]],
                [[40, 80, 120], [7, 11, 19]],
            ]
        ],
        dtype=np.uint16,
    )

    scalar_proxy = dng2jpg_module._hdrplus_build_scalar_proxy_float32(  # pylint: disable=protected-access
        np_module=np,
        frames_rgb_uint16=frames_rgb_uint16,
        hdrplus_options=dng2jpg_module.HdrPlusOptions(proxy_mode="rggb"),
    )

    np.testing.assert_allclose(
        scalar_proxy,
        np.array([[[200.0, 1000.0], [80.0, 12.0]]], dtype=np.float32),
        rtol=1e-6,
        atol=1e-6,
    )


def test_hdrplus_align_layers_detects_translated_alternate_frame() -> None:
    """Hierarchical HDR+ alignment must recover non-zero alternate-frame offsets."""

    rng = np.random.default_rng(1234)
    reference = rng.integers(0, 4096, size=(96, 96), dtype=np.int16).astype(np.float32)
    alternate = _reflect_shift_2d(reference, shift_y=1, shift_x=2).astype(np.float32)
    alignments = dng2jpg_module._hdrplus_align_layers(  # pylint: disable=protected-access
        np_module=np,
        scalar_frames=np.stack([reference, alternate], axis=0),
        hdrplus_options=dng2jpg_module.HdrPlusOptions(),
    )

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
    reference_rgb_uint16 = rng.integers(
        0,
        200,
        size=(64, 64, 3),
        dtype=np.uint16,
    )
    alternate_rgb_uint16 = _reflect_shift_rgb(
        reference_rgb_uint16,
        shift_y=0,
        shift_x=2,
    )
    frames_rgb_uint16 = np.stack([reference_rgb_uint16, alternate_rgb_uint16], axis=0)
    hdrplus_options = dng2jpg_module.HdrPlusOptions()
    scalar_frames = dng2jpg_module._hdrplus_build_scalar_proxy_float32(  # pylint: disable=protected-access
        np_module=np,
        frames_rgb_uint16=frames_rgb_uint16,
        hdrplus_options=hdrplus_options,
    )
    downsampled_scalar_frames = dng2jpg_module._hdrplus_box_down2_float32(  # pylint: disable=protected-access
        np_module=np,
        frames_float32=scalar_frames,
    )
    tile_start_positions_y = dng2jpg_module._hdrplus_compute_tile_start_positions(  # pylint: disable=protected-access
        np_module=np,
        axis_length=frames_rgb_uint16.shape[1],
        tile_stride=dng2jpg_module.HDRPLUS_TILE_STRIDE,
        pad_margin=dng2jpg_module.HDRPLUS_TILE_SIZE,
    )
    tile_start_positions_x = dng2jpg_module._hdrplus_compute_tile_start_positions(  # pylint: disable=protected-access
        np_module=np,
        axis_length=frames_rgb_uint16.shape[2],
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

    frames_rgb_float32 = frames_rgb_uint16.astype(np.float32)
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


def test_run_hdr_plus_merge_preserves_float_internal_and_uint16_io(
    monkeypatch,
    tmp_path,
) -> None:
    """HDR+ merge must keep float intermediates while preserving uint16 image boundaries."""

    imageio_module = _FakePathImageIoModule()
    bracket_paths = [
        tmp_path / "ev_minus.tif",
        tmp_path / "ev_zero.tif",
        tmp_path / "ev_plus.tif",
    ]
    for offset, path in enumerate(bracket_paths):
        imageio_module.register_image(
            path,
            np.full((32, 32, 3), 1000 + (offset * 500), dtype=np.uint16),
        )

    call_trace: list[str] = []

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
        return np.full((height, width, 3), 1234, dtype=np.uint16)

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

    dng2jpg_module._run_hdr_plus_merge(  # pylint: disable=protected-access
        bracket_paths=bracket_paths,
        output_hdr_tiff=tmp_path / "merged_hdr.tif",
        imageio_module=imageio_module,
        np_module=np,
        hdrplus_options=dng2jpg_module.HdrPlusOptions(),
    )

    assert call_trace == ["align", "weights", "merge_temporal", "merge_spatial"]
    assert imageio_module.writes
    output_image = imageio_module.writes[-1][1]
    assert output_image.dtype == np.uint16
    assert output_image.shape == (32, 32, 3)
