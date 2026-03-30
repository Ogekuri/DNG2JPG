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


def test_apply_auto_levels_dispatches_new_color_methods(monkeypatch) -> None:
    """New method selectors must dispatch deterministically through the auto-levels stage."""

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
        call_trace.append(("Color Propagation", None))
        return image_rgb + 100.0

    def _fake_inpaint_opposed(*, np_module, image_rgb, gain_threshold, maxval):
        del np_module, maxval  # Unused by fake dispatcher.
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
