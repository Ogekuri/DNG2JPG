#!/usr/bin/env python3
"""@brief Convert one DNG file into one HDR-merged JPG output.

@details Implements bracketed RAW extraction with three synthetic exposures
(`ev_zero-ev`, `ev_zero`, `ev_zero+ev`), merges them through selected `enfuse`, selected
`luminance-hdr-cli`, selected OpenCV (`Mertens+Debevec`), or selected HDR+
tile-based flow with deterministic parameters, then writes final JPG to
user-selected output path. Temporary artifacts are isolated in a temporary
directory and removed automatically on success and failure.
    @satisfies PRJ-003, DES-008, REQ-055, REQ-056, REQ-057, REQ-058, REQ-059, REQ-060, REQ-061, REQ-062, REQ-063, REQ-064, REQ-065, REQ-066, REQ-067, REQ-068, REQ-069, REQ-070, REQ-071, REQ-072, REQ-073, REQ-074, REQ-075, REQ-077, REQ-078, REQ-079, REQ-080, REQ-081, REQ-088, REQ-089, REQ-090, REQ-091, REQ-092, REQ-093, REQ-094, REQ-095, REQ-096, REQ-097, REQ-098, REQ-111, REQ-112, REQ-113, REQ-114, REQ-115
"""

import os
import shutil
import subprocess
import tempfile
import warnings
import math
from io import BytesIO
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from shell_scripts.utils import (
    get_runtime_os,
    print_error,
    print_info,
    print_success,
)

PROGRAM = "dng2jpg"
DESCRIPTION = "Convert DNG to HDR-merged JPG with enfuse, luminance-hdr-cli, OpenCV, or HDR+ backend."
DEFAULT_GAMMA = (2.222, 4.5)
DEFAULT_POST_GAMMA = 1.0
DEFAULT_BRIGHTNESS = 1.0
DEFAULT_CONTRAST = 1.0
DEFAULT_SATURATION = 1.0
DEFAULT_JPG_COMPRESSION = 15
DEFAULT_AUTO_ZERO_PCT = 50.0
DEFAULT_AUTO_EV_PCT = 50.0
DEFAULT_AA_BLUR_SIGMA = 0.9
DEFAULT_AA_BLUR_THRESHOLD_PCT = 5.0
DEFAULT_AA_LEVEL_LOW_PCT = 0.1
DEFAULT_AA_LEVEL_HIGH_PCT = 99.9
DEFAULT_AA_SIGMOID_CONTRAST = 1.8
DEFAULT_AA_SIGMOID_MIDPOINT = 0.5
DEFAULT_AA_SATURATION_GAMMA = 0.8
DEFAULT_AA_HIGHPASS_BLUR_SIGMA = 2.0
DEFAULT_AB_KEY_VALUE = None
DEFAULT_AB_WHITE_POINT_PERCENTILE = 99.8
DEFAULT_AB_KEY_MIN = 0.045
DEFAULT_AB_KEY_MAX = 0.72
DEFAULT_AB_MAX_AUTO_BOOST_FACTOR = 1.25
DEFAULT_AB_LOCAL_CONTRAST_STRENGTH = 0.20
DEFAULT_AB_CLAHE_CLIP_LIMIT = 1.6
DEFAULT_AB_CLAHE_TILE_GRID_SIZE = (8, 8)
DEFAULT_AB_EPS = 1e-6
DEFAULT_AB_LOW_KEY_VALUE = 0.09
DEFAULT_AB_NORMAL_KEY_VALUE = 0.18
DEFAULT_AB_HIGH_KEY_VALUE = 0.36
DEFAULT_AL_CLIP_PERCENT = 0.02
DEFAULT_AL_CLIP_OUT_OF_GAMUT = True
DEFAULT_AL_GAIN_THRESHOLD = 1.0
DEFAULT_AL_HISTCOMPR = 3
_AUTO_LEVELS_HIGHLIGHT_METHODS = (
    "Luminance Recovery",
    "CIELab Blending",
    "Blend",
    "Color Propagation",
    "Inpaint Opposed",
)
DEFAULT_LUMINANCE_HDR_MODEL = "debevec"
DEFAULT_LUMINANCE_HDR_WEIGHT = "flat"
DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE = "srgb"
DEFAULT_LUMINANCE_TMO = "mantiuk08"
DEFAULT_REINHARD02_BRIGHTNESS = 1.25
DEFAULT_REINHARD02_CONTRAST = 0.85
DEFAULT_REINHARD02_SATURATION = 0.55
DEFAULT_MANTIUK08_CONTRAST = 1.2
DEFAULT_OPENCV_DEBEVEC_WHITE_POINT_PERCENTILE = 99.5
HDRPLUS_TILE_SIZE = 32
HDRPLUS_TILE_STRIDE = HDRPLUS_TILE_SIZE // 2
HDRPLUS_DOWNSAMPLED_TILE_SIZE = HDRPLUS_TILE_STRIDE
HDRPLUS_TEMPORAL_FACTOR = 8.0
HDRPLUS_TEMPORAL_MIN_DIST = 10
HDRPLUS_TEMPORAL_MAX_DIST = 300
EV_STEP = 0.25
MIN_SUPPORTED_BITS_PER_COLOR = 9
DEFAULT_DNG_BITS_PER_COLOR = 14
SUPPORTED_EV_VALUES = tuple(
    round(index * EV_STEP, 2)
    for index in range(
        1, int((((DEFAULT_DNG_BITS_PER_COLOR - 8) / 2.0) / EV_STEP)) + 1
    )
)
AUTO_EV_LOW_PERCENTILE = 0.1
AUTO_EV_HIGH_PERCENTILE = 99.9
AUTO_EV_MEDIAN_PERCENTILE = 50.0
AUTO_EV_TARGET_SHADOW = 0.05
AUTO_EV_TARGET_HIGHLIGHT = 0.90
AUTO_EV_MEDIAN_TARGET = 0.5
AUTO_ZERO_SCENE_KEY_LOW_THRESHOLD = 0.35
AUTO_ZERO_SCENE_KEY_HIGH_THRESHOLD = 0.65
AUTO_ZERO_TARGET_LOW_KEY = 0.35
AUTO_ZERO_TARGET_HIGH_KEY = 0.65
_RUNTIME_OS_LABELS = {
    "windows": "Windows",
    "darwin": "MacOS",
}
_EXIF_TAG_ORIENTATION = 274
_EXIF_TAG_DATETIME = 306
_EXIF_TAG_DATETIME_ORIGINAL = 36867
_EXIF_TAG_DATETIME_DIGITIZED = 36868
_EXIF_VALID_ORIENTATIONS = (1, 2, 3, 4, 5, 6, 7, 8)
_THUMBNAIL_MAX_SIZE = (256, 256)
_AUTO_ADJUST_KNOB_OPTIONS = (
    "--aa-blur-sigma",
    "--aa-blur-threshold-pct",
    "--aa-level-low-pct",
    "--aa-level-high-pct",
    "--aa-sigmoid-contrast",
    "--aa-sigmoid-midpoint",
    "--aa-saturation-gamma",
    "--aa-highpass-blur-sigma",
)
_AUTO_BRIGHTNESS_KNOB_OPTIONS = (
    "--ab-key-value",
    "--ab-white-point-pct",
    "--ab-key-min",
    "--ab-key-max",
    "--ab-max-auto-boost",
    "--ab-local-contrast-strength",
    "--ab-clahe-clip-limit",
)
_AUTO_LEVELS_KNOB_OPTIONS = (
    "--al-clip-pct",
    "--al-clip-out-of-gamut",
    "--al-highlight-reconstruction-method",
    "--al-gain-threshold",
)
_LUMINANCE_OPERATOR_TABLE_HEADERS = (
    "Operator",
    "Family / idea",
    "Character / typical result",
)
_LUMINANCE_OPERATOR_TABLE_SECONDARY_HEADER = ("", "Neutrality", "When to use")
_LUMINANCE_OPERATOR_TABLE_ENTRIES = (
    (
        "`ashikhmin`",
        "Local HVS-inspired tone mapping",
        "Natural local contrast, detail-preserving",
        "Medium",
        "Natural-looking local adaptation with preserved detail",
    ),
    (
        "`drago`",
        "Adaptive logarithmic compression",
        "Smooth, simple, highlight-friendly",
        "Medium",
        "Fast global compression of very wide dynamic range",
    ),
    (
        "`durand`",
        "Bilateral base/detail decomposition",
        "Soft local compression, photographic look",
        "Low-Medium",
        "Controlled local contrast compression",
    ),
    (
        "`fattal`",
        "Gradient-domain compression",
        "Strong detail enhancement, dramatic HDR",
        "Low",
        "Detail-heavy, stylized rendering",
    ),
    (
        "`ferradans`",
        "Perception-inspired adaptation + local contrast",
        "Realistic but locally adaptive",
        "Low-Medium",
        "Perceptual rendering with local contrast recovery",
    ),
    (
        "`ferwerda`",
        "Perceptually based visibility / adaptation",
        "Vision-model oriented, scene-visibility focused",
        "Medium",
        "Research / perceptual-visibility oriented rendering",
    ),
    (
        "`kimkautz`",
        "Consistent global tone reproduction",
        "Stable, consistent, restrained",
        "Medium-High",
        "Consistent results across different HDR images",
    ),
    (
        "`pattanaik`",
        "Human visual system adaptation model",
        "Perceptual, adaptive, scene-aware",
        "Low-Medium",
        "HVS-inspired tone mapping with rod/cone adaptation",
    ),
    (
        "`reinhard02`",
        "Photographic tone reproduction",
        "Natural, controllable, predictable",
        "High",
        "Best baseline when you want a relatively neutral operator",
    ),
    (
        "`reinhard05`",
        "Visual adaptation / photoreceptor model",
        "Natural but more adaptive than `reinhard02`",
        "Medium",
        "Simple controls with a perceptual/natural look",
    ),
    (
        "`mai`",
        "Fast effective tone mapping",
        "Clean, practical, generally easy to use",
        "Medium",
        "Quick all-purpose rendering with minimal tuning",
    ),
    (
        "`mantiuk06`",
        "Contrast mapping with detail enhancement",
        'Punchy, detailed, classic "HDR" look',
        "Low",
        "Strong detail and local contrast enhancement",
    ),
    (
        "`mantiuk08`",
        "Display-adaptive contrast mapping",
        "Perceptual, display-oriented, refined",
        "Low-Medium",
        "Optimizing HDR for display appearance",
    ),
    (
        "`vanhateren`",
        "Retina-inspired visual adaptation",
        "Vision-model based, adaptive",
        "Medium",
        "Retina-style perceptual adaptation experiments",
    ),
    (
        "`lischinski`",
        "Optimization-based local tonal adjustment",
        "Local, edge-aware, selective adjustments",
        "Low",
        "Local tonal manipulation with strong edge preservation",
    ),
)
_LUMINANCE_CONTROL_TABLE_HEADERS = (
    "Operator",
    "Main CLI controls",
)
_LUMINANCE_CONTROL_TABLE_ROWS = (
    ("`ashikhmin`", "`--tmoAshEq2`, `--tmoAshSimple`, `--tmoAshLocal`"),
    ("`drago`", "`--tmoDrgBias`"),
    ("`durand`", "`--tmoDurSigmaS`, `--tmoDurSigmaR`, `--tmoDurBase`"),
    (
        "`fattal`",
        "`--tmoFatAlpha`, `--tmoFatBeta`, `--tmoFatColor`, `--tmoFatNoise`, `--tmoFatNew`",
    ),
    ("`ferradans`", "`--tmoFerRho`, `--tmoFerInvAlpha`"),
    ("`kimkautz`", "`--tmoKimKautzC1`, `--tmoKimKautzC2`"),
    (
        "`pattanaik`",
        "`--tmoPatMultiplier`, `--tmoPatLocal`, `--tmoPatAutoLum`, `--tmoPatCone`, `--tmoPatRod`",
    ),
    (
        "`reinhard02`",
        "`--tmoR02Key`, `--tmoR02Phi`, `--tmoR02Scales`, `--tmoR02Num`, `--tmoR02Low`, `--tmoR02High`",
    ),
    ("`reinhard05`", "`--tmoR05Brightness`, `--tmoR05Chroma`, `--tmoR05Lightness`"),
    (
        "`mantiuk06`",
        "`--tmoM06Contrast`, `--tmoM06Saturation`, `--tmoM06Detail`, `--tmoM06ContrastEqual`",
    ),
    (
        "`mantiuk08`",
        "`--tmoM08ColorSaturation`, `--tmoM08ConstrastEnh`, `--tmoM08LuminanceLvl`, `--tmoM08SetLuminance`",
    ),
    ("`vanhateren`", "`--tmoVanHaterenPupilArea`"),
    ("`lischinski`", "`--tmoLischinskiAlpha`"),
)


@dataclass(frozen=True)
class AutoAdjustOptions:
    """@brief Hold shared auto-adjust knob values used by ImageMagick and OpenCV.

    @details Encapsulates validated knob values consumed by both auto-adjust
    implementations so both pipelines remain numerically aligned and backward
    compatible when no explicit overrides are provided.
    @param blur_sigma {float} Selective blur Gaussian sigma (`> 0`).
    @param blur_threshold_pct {float} Selective blur threshold percentage in `[0, 100]`.
    @param level_low_pct {float} Low percentile for level normalization in `[0, 100]`.
    @param level_high_pct {float} High percentile for level normalization in `[0, 100]`.
    @param sigmoid_contrast {float} Sigmoidal contrast slope (`> 0`).
    @param sigmoid_midpoint {float} Sigmoidal contrast midpoint in `[0, 1]`.
    @param saturation_gamma {float} HSL saturation gamma denominator (`> 0`).
    @param highpass_blur_sigma {float} High-pass Gaussian blur sigma (`> 0`).
    @return {None} Immutable dataclass container.
    @satisfies REQ-073, REQ-075, REQ-082, REQ-083, REQ-084, REQ-086, REQ-087
    """

    blur_sigma: float = DEFAULT_AA_BLUR_SIGMA
    blur_threshold_pct: float = DEFAULT_AA_BLUR_THRESHOLD_PCT
    level_low_pct: float = DEFAULT_AA_LEVEL_LOW_PCT
    level_high_pct: float = DEFAULT_AA_LEVEL_HIGH_PCT
    sigmoid_contrast: float = DEFAULT_AA_SIGMOID_CONTRAST
    sigmoid_midpoint: float = DEFAULT_AA_SIGMOID_MIDPOINT
    saturation_gamma: float = DEFAULT_AA_SATURATION_GAMMA
    highpass_blur_sigma: float = DEFAULT_AA_HIGHPASS_BLUR_SIGMA


@dataclass(frozen=True)
class AutoBrightnessOptions:
    """@brief Hold `--auto-brightness` knob values.

    @details Encapsulates parameters for the 16-bit BT.709 photographic
    tonemap pipeline: key-classification, key-value selection, robust white
    point, luminance-preserving anti-clipping desaturation, and optional mild
    CLAHE micro-contrast blending in the Y channel.
    @param key_value {float|None} Manual Reinhard key value override in `(0, +inf)`; `None` enables automatic key selection.
    @param white_point_percentile {float} Percentile in `(0, 100)` used to derive robust `Lwhite`.
    @param key_min {float} Minimum allowed key value clamp in `(0, +inf)`.
    @param key_max {float} Maximum allowed key value clamp in `(0, +inf)`.
    @param max_auto_boost_factor {float} Multiplicative adjustment factor for automatic key adaptation in `(0, +inf)`.
    @param local_contrast_strength {float} CLAHE blend factor in `[0, 1]`.
    @param clahe_clip_limit {float} OpenCV CLAHE clip limit in `(0, +inf)`.
    @param clahe_tile_grid_size {tuple[int, int]} OpenCV CLAHE tile grid size `(rows, cols)`, each `>=1`.
    @param eps {float} Positive numerical stability guard used in divisions and logarithms.
    @return {None} Immutable dataclass container.
    @satisfies REQ-050, REQ-065, REQ-088, REQ-089, REQ-090, REQ-103, REQ-104, REQ-105
    """

    key_value: float | None = DEFAULT_AB_KEY_VALUE
    white_point_percentile: float = DEFAULT_AB_WHITE_POINT_PERCENTILE
    key_min: float = DEFAULT_AB_KEY_MIN
    key_max: float = DEFAULT_AB_KEY_MAX
    max_auto_boost_factor: float = DEFAULT_AB_MAX_AUTO_BOOST_FACTOR
    local_contrast_strength: float = DEFAULT_AB_LOCAL_CONTRAST_STRENGTH
    clahe_clip_limit: float = DEFAULT_AB_CLAHE_CLIP_LIMIT
    clahe_tile_grid_size: tuple[int, int] = DEFAULT_AB_CLAHE_TILE_GRID_SIZE
    eps: float = DEFAULT_AB_EPS


@dataclass(frozen=True)
class AutoLevelsOptions:
    """@brief Hold `--auto-levels` knob values.

    @details Encapsulates validated histogram-based auto-levels controls ported
    from the attached RawTherapee-oriented source and adapted for RGB uint16
    stage execution in the current post-merge pipeline.
    @param clip_percent {float} Histogram clipping percentage in `[0, +inf)`.
    @param clip_out_of_gamut {bool} `True` to normalize overflowing RGB triplets back into uint16 gamut after gain/reconstruction.
    @param histcompr {int} Histogram compression shift in `[0, 15]`.
    @param highlight_reconstruction_enabled {bool} `True` when highlight reconstruction is enabled.
    @param highlight_reconstruction_method {str} Highlight reconstruction method selector.
    @param gain_threshold {float} Inpaint Opposed gain threshold in `(0, +inf)`.
    @return {None} Immutable dataclass container.
    @satisfies REQ-100, REQ-101, REQ-102, REQ-116
    """

    clip_percent: float = DEFAULT_AL_CLIP_PERCENT
    clip_out_of_gamut: bool = DEFAULT_AL_CLIP_OUT_OF_GAMUT
    histcompr: int = DEFAULT_AL_HISTCOMPR
    highlight_reconstruction_enabled: bool = False
    highlight_reconstruction_method: str = "Inpaint Opposed"
    gain_threshold: float = DEFAULT_AL_GAIN_THRESHOLD


@dataclass(frozen=True)
class PostprocessOptions:
    """@brief Hold deterministic postprocessing option values.

    @details Encapsulates correction factors and JPEG compression level used by
    shared TIFF-to-JPG postprocessing for both HDR backends.
    @param post_gamma {float} Gamma correction factor for postprocessing stage.
    @param brightness {float} Brightness enhancement factor.
    @param contrast {float} Contrast enhancement factor.
    @param saturation {float} Saturation enhancement factor.
    @param jpg_compression {int} JPEG compression level in range `[0, 100]`.
    @param auto_brightness_enabled {bool} `True` when auto-brightness pre-stage is enabled.
    @param auto_brightness_options {AutoBrightnessOptions} Auto-brightness stage knobs.
    @param auto_levels_enabled {bool} `True` when auto-levels stage is enabled.
    @param auto_levels_options {AutoLevelsOptions} Auto-levels stage knobs.
    @param auto_adjust_mode {str|None} Optional auto-adjust implementation selector (`ImageMagick` or `OpenCV`).
    @param auto_adjust_options {AutoAdjustOptions} Shared auto-adjust knobs for `ImageMagick` and `OpenCV` implementations.
    @return {None} Immutable dataclass container.
    @satisfies REQ-050, REQ-065, REQ-066, REQ-069, REQ-071, REQ-072, REQ-073, REQ-075, REQ-082, REQ-083, REQ-084, REQ-086, REQ-087, REQ-088, REQ-089, REQ-090, REQ-100, REQ-101, REQ-102, REQ-103, REQ-104, REQ-105
    """

    post_gamma: float
    brightness: float
    contrast: float
    saturation: float
    jpg_compression: int
    auto_brightness_enabled: bool = False
    auto_brightness_options: AutoBrightnessOptions = field(
        default_factory=AutoBrightnessOptions
    )
    auto_levels_enabled: bool = False
    auto_levels_options: AutoLevelsOptions = field(default_factory=AutoLevelsOptions)
    auto_adjust_mode: str | None = None
    auto_adjust_options: AutoAdjustOptions = field(default_factory=AutoAdjustOptions)


@dataclass(frozen=True)
class LuminanceOptions:
    """@brief Hold deterministic luminance-hdr-cli option values.

    @details Encapsulates luminance backend model and tone-mapping parameters
    forwarded to `luminance-hdr-cli` command generation.
    @param hdr_model {str} Luminance HDR model (`--hdrModel`).
    @param hdr_weight {str} Luminance weighting function (`--hdrWeight`).
    @param hdr_response_curve {str} Luminance response curve (`--hdrResponseCurve`).
    @param tmo {str} Tone-mapping operator (`--tmo`).
    @param tmo_extra_args {tuple[str, ...]} Explicit passthrough `--tmo*` option pairs in CLI order.
    @return {None} Immutable dataclass container.
    @satisfies REQ-061, REQ-067, REQ-068
    """

    hdr_model: str
    hdr_weight: str
    hdr_response_curve: str
    tmo: str
    tmo_extra_args: tuple[str, ...]


@dataclass(frozen=True)
class OpenCvMergeOptions:
    """@brief Hold deterministic OpenCV HDR merge option values.

    @details Encapsulates OpenCV merge controls used by the `--enable-opencv`
    backend. The backend computes exposure fusion (`MergeMertens`) and
    radiance merge (`MergeDebevec`) from the same uint16 bracket TIFF set, then
    blends both outputs in float domain before one uint16 conversion.
    @param debevec_white_point_percentile {float} Percentile in `(0, 100)` used to derive robust white-point normalization from Debevec luminance.
    @return {None} Immutable dataclass container.
    @satisfies REQ-108, REQ-109, REQ-110
    """

    debevec_white_point_percentile: float = DEFAULT_OPENCV_DEBEVEC_WHITE_POINT_PERCENTILE


@dataclass(frozen=True)
class AutoEvInputs:
    """@brief Hold adaptive EV optimization scalar inputs.

    @details Stores normalized luminance percentiles and thresholds for
    deterministic adaptive EV optimization. The optimization function uses these
    scalar values to compute one clamped EV delta for bracket generation.
    @param p_low {float} Luminance at low percentile bound in `[0.0, 1.0]`.
    @param p_median {float} Median luminance in `[0.0, 1.0]`.
    @param p_high {float} Luminance at high percentile bound in `[0.0, 1.0]`.
    @param target_shadow {float} Target lower luminance guardrail in `(0.0, 1.0)`.
    @param target_highlight {float} Target upper luminance guardrail in `(0.0, 1.0)`.
    @param median_target {float} Preferred median-centered luminance target in `(0.0, 1.0)`.
    @param ev_zero {float} Resolved EV-zero center used as adaptive solver anchor.
    @param ev_values {tuple[float, ...]} Supported EV selector values derived from source DNG bit depth.
    @return {None} Immutable scalar container.
    @satisfies REQ-080, REQ-081, REQ-092, REQ-093, REQ-095, REQ-098
    """

    p_low: float
    p_median: float
    p_high: float
    target_shadow: float
    target_highlight: float
    median_target: float
    ev_zero: float
    ev_values: tuple[float, ...]


def _print_box_table(headers, rows, header_rows=()):
    """@brief Print one Unicode box-drawing table.

    @details Computes deterministic column widths from headers and rows, then
    prints aligned borders and cells using Unicode line-drawing glyphs.
    @param headers {tuple[str, ...]} Table header labels in fixed output order.
    @param header_rows {tuple[tuple[str, ...], ...]} Additional physical header rows rendered before header/body separator.
    @param rows {tuple[tuple[str, ...], ...]} Table body rows with one value per column.
    @return {None} Writes formatted table to stdout.
    @satisfies REQ-070
    """

    widths = [len(header) for header in headers]
    for header_row in header_rows:
        for idx, value in enumerate(header_row):
            widths[idx] = max(widths[idx], len(value))
    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def _border(left, middle, right):
        return left + middle.join("─" * (width + 2) for width in widths) + right

    def _line(values):
        cells = [f" {value.ljust(widths[idx])} " for idx, value in enumerate(values)]
        return "│" + "│".join(cells) + "│"

    print(_border("┌", "┬", "┐"))
    print(_line(headers))
    for header_row in header_rows:
        print(_line(header_row))
    print(_border("├", "┼", "┤"))
    for row in rows:
        print(_line(row))
    print(_border("└", "┴", "┘"))


def _build_two_line_operator_rows(operator_entries):
    """@brief Build two-line physical rows for luminance operator table.

    @details Expands each logical operator entry into two physical rows while
    preserving the bordered three-column layout used by help rendering.
    @param operator_entries {tuple[tuple[str, str, str, str, str], ...]} Logical operator rows in `(operator, family, character, neutrality, when_to_use)` format.
    @return {tuple[tuple[str, str, str], ...]} Expanded physical rows for `_print_box_table`.
    @satisfies REQ-070
    """

    rows = []
    for operator, family, character, neutrality, when_to_use in operator_entries:
        rows.append((operator, family, character))
        rows.append(("", neutrality, when_to_use))
    return tuple(rows)


def print_help(version):
    """@brief Print help text for the `dng2jpg` command.

    @details Documents required positional arguments, required mutually
    exclusive exposure selectors (`--ev` or `--auto-ev`), optional RAW gamma
    controls, optional `--ev-zero` and `--auto-zero` selectors, shared
    postprocessing controls, backend selection including HDR+, and
    luminance-hdr-cli tone-mapping options.
    @param version {str} CLI version label to append in usage output.
    @return {None} Writes help text to stdout.
    @satisfies DES-008, REQ-056, REQ-063, REQ-069, REQ-070, REQ-071, REQ-072, REQ-073, REQ-075, REQ-082, REQ-083, REQ-084, REQ-088, REQ-089, REQ-090, REQ-091, REQ-094, REQ-097, REQ-100, REQ-101, REQ-102, REQ-111
    """

    print(
        f"Usage: {PROGRAM} <input.dng> <output.jpg> "
        f"(--ev=<value> | --auto-ev[=<1|true|yes|on>]) [--ev-zero=<value> | --auto-zero[=<1|true|yes|on>]] [--gamma=<a,b>] [--post-gamma=<value>] "
        "[--auto-zero-pct=<0..100>] [--auto-ev-pct=<0..100>] "
        f"[--brightness=<value>] [--contrast=<value>] [--saturation=<value>] "
        "[--auto-brightness[=<1|true|yes|on>]] "
        "[--ab-key-value=<value>] [--ab-white-point-pct=<(0,100)>] "
        "[--ab-key-min=<value>] [--ab-key-max=<value>] "
        "[--ab-max-auto-boost=<value>] "
        "[--ab-local-contrast-strength=<0..1>] "
        "[--ab-clahe-clip-limit=<value>] "
        "[--auto-levels[=<1|true|yes|on>]] "
        "[--al-clip-pct=<value>] "
        "[--al-clip-out-of-gamut[=<0|1|false|true|no|yes|off|on>]] "
        "[--al-highlight-reconstruction-method <Luminance Recovery|CIELab Blending|Blend|Color Propagation|Inpaint Opposed>] "
        "[--al-gain-threshold=<value>] "
        f"[--jpg-compression=<0..100>] [--auto-adjust <ImageMagick|OpenCV>] "
        "[--aa-blur-sigma=<value>] [--aa-blur-threshold-pct=<0..100>] "
        "[--aa-level-low-pct=<0..100>] [--aa-level-high-pct=<0..100>] "
        "[--aa-sigmoid-contrast=<value>] [--aa-sigmoid-midpoint=<0..1>] "
        "[--aa-saturation-gamma=<value>] [--aa-highpass-blur-sigma=<value>] "
        f"(--enable-enfuse | --enable-luminance | --enable-opencv | --enable-hdr-plus) "
        f"[--luminance-hdr-model=<name>] [--luminance-hdr-weight=<name>] "
        f"[--luminance-hdr-response-curve=<name>] [--luminance-tmo=<name>] "
        f"[--tmo*=<value>] ({version})"
    )
    print()
    print("dng2jpg options:")
    print("  <input.dng>      - Input DNG file (required).")
    print("  <output.jpg>     - Output JPG file (required).")
    print(
        "  --ev=<value>     - Fixed exposure bracket EV: 0.25 .. MAX_BRACKET in 0.25 steps"
        " (MAX_BRACKET = ((bits_per_color-8)/2)-abs(ev_zero) from input DNG)."
    )
    print("  --auto-ev        - Adaptive EV mode (required unless --ev is selected).")
    print(
        "                     Optional value forms: --auto-ev=1, --auto-ev=true, --auto-ev yes."
    )
    print(
        "  --ev-zero=<value> - Central EV for bracket export: -SAFE_ZERO_MAX .. +SAFE_ZERO_MAX in 0.25 steps"
        " (SAFE_ZERO_MAX = ((bits_per_color-8)/2)-1 from input DNG, default: 0)."
    )
    print(
        "  --auto-zero      - Auto-resolve EV center from RAW median luminance"
        " (mutually exclusive with --ev-zero)."
    )
    print(
        "                     Optional value forms: --auto-zero=1, --auto-zero=true, --auto-zero yes."
    )
    print(
        f"  --auto-zero-pct=<0..100> - Scale auto-resolved EV center by percentage before 0.25-step quantization toward zero (default: {DEFAULT_AUTO_ZERO_PCT:g})."
    )
    print(
        f"  --auto-ev-pct=<0..100>   - Scale adaptive EV bracket by percentage before 0.25-step quantization toward zero (default: {DEFAULT_AUTO_EV_PCT:g})."
    )
    print(
        f"  --gamma=<a,b>    - RAW extraction gamma pair (default: {DEFAULT_GAMMA[0]},{DEFAULT_GAMMA[1]})."
    )
    print("                     Example: --gamma=1,1 for linear extraction.")
    print(
        "  --post-gamma=<value> - Postprocess gamma correction factor (backend-default when omitted)."
    )
    print(
        "  --brightness=<value> - Postprocess brightness factor (backend-default when omitted)."
    )
    print(
        "  --contrast=<value>   - Postprocess contrast factor (backend-default when omitted)."
    )
    print(
        "  --saturation=<value> - Postprocess saturation factor (backend-default when omitted)."
    )
    print(
        "  --auto-brightness   - Enable auto-brightness pre-stage before static postprocess factors."
    )
    print(
        "                     Optional value forms: --auto-brightness=1, --auto-brightness=true, --auto-brightness yes."
    )
    print(
        "  [auto-brightness knobs] - Effective only when --auto-brightness is set."
    )
    print(
        "  --ab-key-value=<value> - Manual Reinhard key value a (>0); omit to enable automatic low/normal/high-key selection."
    )
    print(
        f"  --ab-white-point-pct=<(0,100)> - Percentile for robust white point in burn-out compression (default: {DEFAULT_AB_WHITE_POINT_PERCENTILE:g})."
    )
    print(
        f"  --ab-key-min=<value> - Minimum key-value clamp (>0, default: {DEFAULT_AB_KEY_MIN:g})."
    )
    print(
        f"  --ab-key-max=<value> - Maximum key-value clamp (>0, default: {DEFAULT_AB_KEY_MAX:g})."
    )
    print(
        f"  --ab-max-auto-boost=<value> - Auto key adaptation factor (>0, default: {DEFAULT_AB_MAX_AUTO_BOOST_FACTOR:g})."
    )
    print(
        f"  --ab-local-contrast-strength=<0..1> - CLAHE Y-channel blend factor for mild local contrast (default: {DEFAULT_AB_LOCAL_CONTRAST_STRENGTH:g})."
    )
    print(
        f"  --ab-clahe-clip-limit=<value> - CLAHE clip limit for local contrast (>0, default: {DEFAULT_AB_CLAHE_CLIP_LIMIT:g})."
    )
    print(
        "  --auto-levels      - Enable auto-levels stage after auto-brightness and before post-gamma/brightness/contrast/saturation."
    )
    print(
        "                     Optional value forms: --auto-levels=1, --auto-levels=true, --auto-levels yes."
    )
    print(
        "  [auto-levels knobs] - Effective only when --auto-levels is set."
    )
    print(
        f"  --al-clip-pct=<value> - Histogram clipping percentage >= 0 (default: {DEFAULT_AL_CLIP_PERCENT:g})."
    )
    print(
        "  --al-clip-out-of-gamut - Normalize overflowing RGB triplets after auto-levels gain/reconstruction."
    )
    print(
        "                     Optional value forms: --al-clip-out-of-gamut=0, --al-clip-out-of-gamut=false, --al-clip-out-of-gamut=yes."
    )
    print(
        "  --al-highlight-reconstruction-method <name> - Enable highlight reconstruction and select one RawTherapee-aligned method."
    )
    print(
        "                     Allowed values: "
        + ", ".join(_AUTO_LEVELS_HIGHLIGHT_METHODS)
        + "."
    )
    print(
        f"  --al-gain-threshold=<value> - Inpaint Opposed gain threshold (>0, default: {DEFAULT_AL_GAIN_THRESHOLD:g})."
    )
    print(
        f"  --jpg-compression=<0..100> - JPEG compression level (default: {DEFAULT_JPG_COMPRESSION})."
    )
    print(
        "  --auto-adjust <name>     - Enable auto-adjust stage implementation (`ImageMagick` or `OpenCV`)."
    )
    print(
        "  [auto-adjust knobs]      - Effective only when --auto-adjust is set; shared by ImageMagick and OpenCV."
    )
    print(
        f"  --aa-blur-sigma=<value>  - Selective blur sigma > 0 (default: {DEFAULT_AA_BLUR_SIGMA:g})."
    )
    print(
        f"  --aa-blur-threshold-pct=<0..100> - Selective blur threshold percent (default: {DEFAULT_AA_BLUR_THRESHOLD_PCT:g})."
    )
    print(
        f"  --aa-level-low-pct=<0..100>  - Level low percentile; must be < --aa-level-high-pct (default: {DEFAULT_AA_LEVEL_LOW_PCT:g})."
    )
    print(
        f"  --aa-level-high-pct=<0..100> - Level high percentile; must be > --aa-level-low-pct (default: {DEFAULT_AA_LEVEL_HIGH_PCT:g})."
    )
    print(
        f"  --aa-sigmoid-contrast=<value> - Sigmoidal contrast slope > 0 (default: {DEFAULT_AA_SIGMOID_CONTRAST:g})."
    )
    print(
        f"  --aa-sigmoid-midpoint=<0..1> - Sigmoidal midpoint in [0,1] (default: {DEFAULT_AA_SIGMOID_MIDPOINT:g})."
    )
    print(
        f"  --aa-saturation-gamma=<value> - HSL saturation gamma > 0 (default: {DEFAULT_AA_SATURATION_GAMMA:g})."
    )
    print(
        f"  --aa-highpass-blur-sigma=<value> - High-pass blur sigma > 0 (default: {DEFAULT_AA_HIGHPASS_BLUR_SIGMA:g})."
    )
    print("  --enable-enfuse")
    print(
        "                   - Select enfuse backend (required, mutually exclusive with --enable-luminance, --enable-opencv, and --enable-hdr-plus)."
    )
    print("  --enable-luminance")
    print(
        "                   - Select luminance-hdr-cli backend (required, mutually exclusive with --enable-enfuse, --enable-opencv, and --enable-hdr-plus)."
    )
    print("  --enable-opencv")
    print(
        "                   - Select OpenCV merge backend (Mertens+Debevec, required, mutually exclusive with --enable-enfuse, --enable-luminance, and --enable-hdr-plus)."
    )
    print("  --enable-hdr-plus")
    print(
        "                   - Select HDR+ tile merge backend (Google Pixel temporal+spatial merge, ev_zero reference, required, mutually exclusive with --enable-enfuse, --enable-luminance, and --enable-opencv)."
    )
    print(
        "  [postprocess defaults]"
        f" - --enable-enfuse: post-gamma={DEFAULT_POST_GAMMA}, brightness={DEFAULT_BRIGHTNESS},"
        f" contrast={DEFAULT_CONTRAST}, saturation={DEFAULT_SATURATION}."
    )
    print(
        "                   - --enable-luminance + --luminance-tmo=reinhard02: "
        f"post-gamma={DEFAULT_POST_GAMMA}, brightness={DEFAULT_REINHARD02_BRIGHTNESS}, "
        f"contrast={DEFAULT_REINHARD02_CONTRAST}, saturation={DEFAULT_REINHARD02_SATURATION}."
    )
    print(
        "                   - --enable-luminance + --luminance-tmo=mantiuk08: "
        f"post-gamma={DEFAULT_POST_GAMMA}, brightness={DEFAULT_BRIGHTNESS}, "
        f"contrast={DEFAULT_MANTIUK08_CONTRAST}, saturation={DEFAULT_SATURATION}."
    )
    print(
        "                   - --enable-luminance + other --luminance-tmo (except reinhard02,mantiuk08): "
        f"post-gamma={DEFAULT_POST_GAMMA}, brightness={DEFAULT_BRIGHTNESS}, "
        f"contrast={DEFAULT_CONTRAST}, saturation={DEFAULT_SATURATION}."
    )
    print(
        "                   - --enable-opencv: "
        f"post-gamma={DEFAULT_POST_GAMMA}, brightness={DEFAULT_BRIGHTNESS}, "
        f"contrast={DEFAULT_CONTRAST}, saturation={DEFAULT_SATURATION}."
    )
    print(
        "                   - --enable-hdr-plus: "
        f"post-gamma={DEFAULT_POST_GAMMA}, brightness={DEFAULT_BRIGHTNESS}, "
        f"contrast={DEFAULT_CONTRAST}, saturation={DEFAULT_SATURATION}."
    )
    print("  --luminance-hdr-model=<name>")
    print(
        f"                   - Luminance HDR model (default: {DEFAULT_LUMINANCE_HDR_MODEL})."
    )
    print("  --luminance-hdr-weight=<name>")
    print(
        f"                   - Luminance weighting function (default: {DEFAULT_LUMINANCE_HDR_WEIGHT})."
    )
    print("  --luminance-hdr-response-curve=<name>")
    print(
        f"                   - Luminance response curve (default: {DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE})."
    )
    print("  --luminance-tmo=<name>")
    print(
        f"                   - Luminance tone mapper (default: {DEFAULT_LUMINANCE_TMO})."
    )
    print()
    print("  Luminance operators:")
    operator_rows = _build_two_line_operator_rows(_LUMINANCE_OPERATOR_TABLE_ENTRIES)
    _print_box_table(
        _LUMINANCE_OPERATOR_TABLE_HEADERS,
        operator_rows,
        header_rows=(_LUMINANCE_OPERATOR_TABLE_SECONDARY_HEADER,),
    )
    print()
    print("  Luminance operator main CLI controls:")
    _print_box_table(_LUMINANCE_CONTROL_TABLE_HEADERS, _LUMINANCE_CONTROL_TABLE_ROWS)
    print()
    print("  --tmo* <value> | --tmo*=<value>")
    print(
        "                   - Forward explicit luminance-hdr-cli --tmo* parameters as-is."
    )
    print("  [platform]       - Command is available on Linux only.")
    print("  --help           - Show this help message.")


def _calculate_max_ev_from_bits(bits_per_color):
    """@brief Compute EV ceiling from detected DNG bits per color.

    @details Implements `MAX=((bits_per_color-8)/2)` and validates minimum
    supported bit depth before computing clamp ceiling used by static and
    adaptive EV flows.
    @param bits_per_color {int} Detected source DNG bits per color.
    @return {float} Bit-derived EV ceiling.
    @exception ValueError Raised when bit depth is below supported minimum.
    @satisfies REQ-057, REQ-081, REQ-093, REQ-094, REQ-096
    """

    if bits_per_color < MIN_SUPPORTED_BITS_PER_COLOR:
        raise ValueError(
            f"Unsupported bits_per_color={bits_per_color}; expected >= {MIN_SUPPORTED_BITS_PER_COLOR}"
        )
    return (bits_per_color - 8) / 2.0


def _calculate_safe_ev_zero_max(base_max_ev):
    """@brief Compute safe absolute EV-zero ceiling preserving at least `±1EV` bracket.

    @details Derives `SAFE_ZERO_MAX=(BASE_MAX-1)` where `BASE_MAX=((bits_per_color-8)/2)`.
    Safe range guarantees `MAX_BRACKET=(BASE_MAX-abs(ev_zero)) >= 1`.
    @param base_max_ev {float} Bit-derived `BASE_MAX` value.
    @return {float} Safe absolute EV-zero ceiling.
    @satisfies REQ-093, REQ-094, REQ-096, REQ-097
    """

    return max(0.0, base_max_ev - 1.0)


def _derive_supported_ev_zero_values(base_max_ev):
    """@brief Derive non-negative EV-zero quantization set preserving `±1EV` bracket.

    @details Generates deterministic quarter-step tuple in `[0, SAFE_ZERO_MAX]`,
    where `SAFE_ZERO_MAX=max(0, BASE_MAX-1)` and `BASE_MAX=((bits_per_color-8)/2)`.
    @param base_max_ev {float} Bit-derived `BASE_MAX` value.
    @return {tuple[float, ...]} Supported non-negative EV-zero magnitudes including `0.0`.
    @satisfies REQ-093, REQ-094, REQ-096, REQ-097
    """

    safe_ev_zero_max = _calculate_safe_ev_zero_max(base_max_ev)
    if safe_ev_zero_max < (EV_STEP - 1e-9):
        return (0.0,)
    max_steps = int(math.floor((safe_ev_zero_max / EV_STEP) + 1e-9))
    return tuple(round(index * EV_STEP, 2) for index in range(0, max_steps + 1))


def _derive_supported_ev_values(bits_per_color, ev_zero=0.0):
    """@brief Derive valid bracket EV selector set from bit depth and `ev_zero`.

    @details Builds deterministic EV selector tuple with fixed `0.25` step in
    closed range `[0.25, MAX_BRACKET]`, where
    `MAX_BRACKET=((bits_per_color-8)/2)-abs(ev_zero)`.
    @param bits_per_color {int} Detected source DNG bits per color.
    @param ev_zero {float} Central EV selector.
    @return {tuple[float, ...]} Supported bracket EV selector tuple.
    @exception ValueError Raised when bit-derived bracket EV ceiling cannot produce any selector values.
    @satisfies REQ-057, REQ-081, REQ-093, REQ-094, REQ-096
    """

    base_max_ev = _calculate_max_ev_from_bits(bits_per_color)
    max_bracket = base_max_ev - abs(ev_zero)
    if max_bracket < (1.0 - 1e-9):
        raise ValueError(
            "Bit-derived bracket EV ceiling is too small for selector generation: "
            f"{max_bracket:g} (formula: ((bits_per_color-8)/2)-abs(ev_zero))"
        )
    max_steps = int(math.floor((max_bracket / EV_STEP) + 1e-9))
    if max_steps < 1:
        raise ValueError(
            "Bit-derived bracket EV ceiling cannot produce selector values: "
            f"{max_bracket:g} (formula: ((bits_per_color-8)/2)-abs(ev_zero))"
        )
    return tuple(round(index * EV_STEP, 2) for index in range(1, max_steps + 1))


def _detect_dng_bits_per_color(raw_handle):
    """@brief Detect source DNG bits-per-color from RAW metadata.

    @details Prefers RAW sample container bit depth from
    `raw_handle.raw_image_visible.dtype.itemsize * 8` because the DNG white
    level can represent effective sensor range (for example `4000`) while RAW
    samples are still stored in a wider container (for example `uint16`).
    Falls back to `raw_handle.white_level` `bit_length` when container metadata
    is unavailable.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @return {int} Detected source DNG bits per color.
    @exception ValueError Raised when metadata is missing, non-numeric, or non-positive.
    @satisfies REQ-057, REQ-081, REQ-092, REQ-093
    """

    raw_visible = getattr(raw_handle, "raw_image_visible", None)
    raw_dtype = getattr(raw_visible, "dtype", None)
    raw_itemsize = getattr(raw_dtype, "itemsize", None)
    if raw_itemsize is not None:
        try:
            container_bits = int(raw_itemsize) * 8
        except (TypeError, ValueError):
            container_bits = 0
        if container_bits > 0:
            return container_bits

    white_level_raw = getattr(raw_handle, "white_level", None)
    if white_level_raw is None:
        raise ValueError("RAW metadata does not expose white_level")
    if isinstance(white_level_raw, (tuple, list)):
        if not white_level_raw:
            raise ValueError("RAW metadata white_level sequence is empty")
        white_level_value = max(white_level_raw)
    else:
        white_level_value = white_level_raw
    try:
        white_level_int = int(white_level_value)
    except (TypeError, ValueError):
        raise ValueError(
            f"RAW metadata white_level is non-numeric: {white_level_value!r}"
        ) from None
    if white_level_int <= 0:
        raise ValueError(f"RAW metadata white_level must be positive: {white_level_int}")
    return white_level_int.bit_length()


def _is_ev_value_on_supported_step(ev_value):
    """@brief Validate EV value belongs to fixed `0.25` step grid.

    @details Checks whether EV value can be represented as integer multiples of
    `0.25` using tolerance-based floating-point comparison.
    @param ev_value {float} Parsed EV numeric value.
    @return {bool} `True` when EV value is aligned to `0.25` step.
    @satisfies REQ-057
    """

    scaled = ev_value / EV_STEP
    return math.isclose(scaled, round(scaled), rel_tol=0.0, abs_tol=1e-9)


def _parse_ev_option(ev_raw):
    """@brief Parse and validate one EV option value.

    @details Converts token to `float`, enforces minimum `0.25`, and enforces
    fixed `0.25` granularity. Bit-depth upper-bound validation is deferred until
    RAW metadata is loaded from source DNG.
    @param ev_raw {str} EV token extracted from command arguments.
    @return {float|None} Parsed EV value when valid; `None` otherwise.
    @satisfies REQ-056, REQ-057
    """

    try:
        ev_value = float(ev_raw)
    except ValueError:
        print_error(f"Invalid --ev value: {ev_raw}")
        print_error(
            "Allowed values: 0.25 .. MAX_BRACKET in 0.25 steps "
            "(MAX_BRACKET = ((bits_per_color-8)/2)-abs(ev_zero))"
        )
        return None

    if ev_value < EV_STEP or not _is_ev_value_on_supported_step(ev_value):
        print_error(f"Unsupported --ev value: {ev_raw}")
        print_error(
            "Allowed values: 0.25 .. MAX_BRACKET in 0.25 steps "
            "(MAX_BRACKET = ((bits_per_color-8)/2)-abs(ev_zero))"
        )
        return None

    return round(ev_value, 2)


def _parse_ev_zero_option(ev_zero_raw):
    """@brief Parse and validate one `--ev-zero` option value.

    @details Converts token to `float`, enforces fixed `0.25` granularity, and
    defers bit-depth bound validation to RAW-metadata runtime stage.
    @param ev_zero_raw {str} EV-zero token extracted from command arguments.
    @return {float|None} Parsed EV-zero value when valid; `None` otherwise.
    @satisfies REQ-094
    """

    try:
        ev_zero_value = float(ev_zero_raw)
    except ValueError:
        print_error(f"Invalid --ev-zero value: {ev_zero_raw}")
        print_error(
            "Allowed values: -SAFE_ZERO_MAX .. +SAFE_ZERO_MAX in 0.25 steps "
            "(SAFE_ZERO_MAX = ((bits_per_color-8)/2)-1)"
        )
        return None

    if not _is_ev_value_on_supported_step(ev_zero_value):
        print_error(f"Unsupported --ev-zero value: {ev_zero_raw}")
        print_error(
            "Allowed values: -SAFE_ZERO_MAX .. +SAFE_ZERO_MAX in 0.25 steps "
            "(SAFE_ZERO_MAX = ((bits_per_color-8)/2)-1)"
        )
        return None

    return round(ev_zero_value, 2)


def _parse_auto_ev_option(auto_ev_raw):
    """@brief Parse and validate one `--auto-ev` option value.

    @details Accepts only boolean-like activator tokens (`1`, `true`, `yes`,
    `on`) and rejects all other values to keep deterministic CLI behavior.
    @param auto_ev_raw {str} Raw `--auto-ev` value token from CLI args.
    @return {bool|None} `True` when token enables adaptive mode; `None` on parse failure.
    @satisfies REQ-056
    """

    auto_ev_text = auto_ev_raw.strip().lower()
    if auto_ev_text in ("1", "true", "yes", "on"):
        return True
    print_error(f"Invalid --auto-ev value: {auto_ev_raw}")
    print_error("Allowed values: 1, true, yes, on")
    return None


def _parse_auto_zero_option(auto_zero_raw):
    """@brief Parse and validate one `--auto-zero` option value.

    @details Accepts only boolean-like activator tokens (`1`, `true`, `yes`,
    `on`) and rejects all other values to keep deterministic CLI behavior.
    @param auto_zero_raw {str} Raw `--auto-zero` value token from CLI args.
    @return {bool|None} `True` when token enables automatic EV-zero mode; `None` on parse failure.
    @satisfies REQ-094
    """

    auto_zero_text = auto_zero_raw.strip().lower()
    if auto_zero_text in ("1", "true", "yes", "on"):
        return True
    print_error(f"Invalid --auto-zero value: {auto_zero_raw}")
    print_error("Allowed values: 1, true, yes, on")
    return None


def _parse_percentage_option(option_name, option_raw):
    """@brief Parse and validate one percentage option value.

    @details Converts option token to `float`, requires inclusive range
    `[0, 100]`, and emits deterministic parse errors on malformed values.
    @param option_name {str} Long-option identifier used in error messages.
    @param option_raw {str} Raw option token value from CLI args.
    @return {float|None} Parsed percentage value when valid; `None` otherwise.
    @satisfies REQ-081, REQ-094, REQ-097
    """

    try:
        option_value = float(option_raw)
    except ValueError:
        print_error(f"Invalid {option_name} value: {option_raw}")
        return None
    if option_value < 0.0 or option_value > 100.0:
        print_error(f"Invalid {option_name} value: {option_raw}")
        print_error("Allowed range: 0..100")
        return None
    return option_value


def _parse_auto_brightness_option(auto_brightness_raw):
    """@brief Parse and validate one `--auto-brightness` option value.

    @details Accepts only boolean-like activator tokens (`1`, `true`, `yes`,
    `on`) and rejects all other values to keep deterministic CLI behavior.
    @param auto_brightness_raw {str} Raw `--auto-brightness` value token from CLI args.
    @return {bool|None} `True` when token enables auto-brightness; `None` on parse failure.
    @satisfies REQ-065, REQ-089
    """

    auto_brightness_text = auto_brightness_raw.strip().lower()
    if auto_brightness_text in ("1", "true", "yes", "on"):
        return True
    print_error(f"Invalid --auto-brightness value: {auto_brightness_raw}")
    print_error("Allowed values: 1, true, yes, on")
    return None


def _parse_auto_levels_option(auto_levels_raw):
    """@brief Parse and validate one `--auto-levels` option value.

    @details Accepts only boolean-like activator tokens (`1`, `true`, `yes`,
    `on`) and rejects all other values to keep deterministic CLI behavior.
    @param auto_levels_raw {str} Raw `--auto-levels` value token from CLI args.
    @return {bool|None} `True` when token enables auto-levels; `None` on parse failure.
    @satisfies REQ-100, REQ-101
    """

    auto_levels_text = auto_levels_raw.strip().lower()
    if auto_levels_text in ("1", "true", "yes", "on"):
        return True
    print_error(f"Invalid --auto-levels value: {auto_levels_raw}")
    print_error("Allowed values: 1, true, yes, on")
    return None


def _parse_explicit_boolean_option(option_name, option_raw):
    """@brief Parse one explicit boolean option value.

    @details Accepts canonical true/false token families to keep deterministic
    toggle parsing for CLI knobs that support both enabling and disabling.
    @param option_name {str} Long-option identifier used in error messages.
    @param option_raw {str} Raw option token value from CLI args.
    @return {bool|None} Parsed boolean value; `None` on parse failure.
    @satisfies REQ-101
    """

    option_text = option_raw.strip().lower()
    if option_text in ("1", "true", "yes", "on"):
        return True
    if option_text in ("0", "false", "no", "off"):
        return False
    print_error(f"Invalid {option_name} value: {option_raw}")
    print_error("Allowed values: 0, 1, false, true, no, yes, off, on")
    return None


def _clamp_ev_to_supported(ev_candidate, ev_values):
    """@brief Clamp one EV candidate to supported numeric interval.

    @details Applies lower/upper bound clamp to keep computed adaptive EV value
    inside configured EV bounds before command generation.
    @param ev_candidate {float} Candidate EV delta from adaptive optimization.
    @param ev_values {tuple[float, ...]} Sorted supported EV selector values.
    @return {float} Clamped EV delta in `[min(ev_values), max(ev_values)]`.
    @satisfies REQ-081, REQ-093
    """

    return max(ev_values[0], min(ev_values[-1], ev_candidate))


def _quantize_ev_to_supported(ev_value, ev_values):
    """@brief Quantize one EV value to nearest supported selector value.

    @details Chooses nearest value from `ev_values` to preserve
    deterministic three-bracket behavior in downstream static multiplier and HDR
    command construction paths.
    @param ev_value {float} Clamped EV value.
    @param ev_values {tuple[float, ...]} Sorted supported EV selector values.
    @return {float} Nearest supported EV selector value.
    @satisfies REQ-080, REQ-081, REQ-093
    """

    nearest_ev = ev_values[0]
    smallest_distance = abs(ev_value - nearest_ev)
    for candidate in ev_values[1:]:
        distance = abs(ev_value - candidate)
        if distance < smallest_distance:
            nearest_ev = candidate
            smallest_distance = distance
    return nearest_ev


def _quantize_ev_toward_zero_step(ev_value, step=EV_STEP):
    """@brief Quantize one EV value toward zero using fixed step size.

    @details Converts EV value to step units, truncates fractional remainder
    toward zero, and reconstructs signed EV value using deterministic `0.25`
    precision rounding.
    @param ev_value {float} EV value to quantize.
    @param step {float} Quantization step size.
    @return {float} Quantized EV value with truncation toward zero.
    @satisfies REQ-081, REQ-097
    """

    if math.isclose(ev_value, 0.0, rel_tol=0.0, abs_tol=1e-9):
        return 0.0
    step_units = abs(ev_value) / step
    quantized_units = int(math.floor(step_units + 1e-9))
    quantized_abs = round(quantized_units * step, 2)
    if ev_value >= 0.0:
        return quantized_abs
    return -quantized_abs


def _apply_auto_percentage_scaling(ev_value, percentage):
    """@brief Apply percentage scaling to EV value with downward 0.25 quantization.

    @details Multiplies EV value by percentage in `[0,100]` and quantizes
    scaled result toward zero with fixed `0.25` step.
    @param ev_value {float} EV value before scaling.
    @param percentage {float} Percentage scaling factor in `[0,100]`.
    @return {float} Scaled EV value quantized toward zero.
    @satisfies REQ-081, REQ-097
    """

    scaled_value = ev_value * (percentage / 100.0)
    return _quantize_ev_toward_zero_step(scaled_value)


def _extract_normalized_preview_luminance_stats(raw_handle):
    """@brief Extract normalized preview luminance percentiles from RAW handle.

    @details Generates one deterministic linear preview (`bright=1.0`,
    `output_bps=16`, camera white balance, no auto-bright, linear gamma,
    `user_flip=0`), computes luminance for each pixel, then returns normalized
    low/median/high percentiles by dividing with preview maximum luminance.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @return {tuple[float, float, float]} Normalized `(p_low, p_median, p_high)` in `(0,1)`.
    @exception ValueError Raised when preview extraction cannot produce valid luminance values.
    @satisfies REQ-080, REQ-081, REQ-092, REQ-093, REQ-097
    """

    linear_preview = raw_handle.postprocess(
        bright=1.0,
        output_bps=16,
        use_camera_wb=True,
        no_auto_bright=True,
        gamma=(1.0, 1.0),
        user_flip=0,
    )
    flat_luminance = []
    for row in linear_preview:
        for pixel in row:
            red = _coerce_positive_luminance(pixel[0], 0.0)
            green = _coerce_positive_luminance(pixel[1], 0.0)
            blue = _coerce_positive_luminance(pixel[2], 0.0)
            luminance = (0.2126 * red) + (0.7152 * green) + (0.0722 * blue)
            if luminance > 0.0:
                flat_luminance.append(luminance)
    if not flat_luminance:
        raise ValueError("Adaptive preview produced no valid luminance values")
    flat_luminance.sort()

    def _percentile(percentile_value):
        position = (len(flat_luminance) - 1) * (percentile_value / 100.0)
        lower_index = int(math.floor(position))
        upper_index = int(math.ceil(position))
        if lower_index == upper_index:
            return flat_luminance[lower_index]
        weight = position - lower_index
        lower_value = flat_luminance[lower_index]
        upper_value = flat_luminance[upper_index]
        return lower_value + ((upper_value - lower_value) * weight)

    p_low_raw = _percentile(AUTO_EV_LOW_PERCENTILE)
    p_median_raw = _percentile(AUTO_EV_MEDIAN_PERCENTILE)
    p_high_raw = _percentile(AUTO_EV_HIGH_PERCENTILE)

    max_luminance = max(flat_luminance)
    if max_luminance <= 0.0:
        raise ValueError("Adaptive preview maximum luminance is not positive")

    epsilon = 1e-9
    p_low = max(epsilon, min(1.0 - epsilon, p_low_raw / max_luminance))
    p_high = max(epsilon, min(1.0 - epsilon, p_high_raw / max_luminance))
    p_median = max(epsilon, min(1.0 - epsilon, p_median_raw / max_luminance))
    return (p_low, p_median, p_high)


def _coerce_positive_luminance(value, fallback):
    """@brief Coerce luminance scalar to positive range for logarithmic math.

    @details Converts input to float and enforces a strictly positive minimum.
    Returns fallback when conversion fails or result is non-positive.
    @param value {object} Candidate luminance scalar.
    @param fallback {float} Fallback positive luminance scalar.
    @return {float} Positive luminance value suitable for `log2`.
    @satisfies REQ-081
    """

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return fallback
    if numeric_value <= 0.0:
        return fallback
    return numeric_value


def _derive_scene_key_preserving_median_target(p_median):
    """@brief Derive scene-key-preserving median target for auto-zero optimization.

    @details Classifies scene key from normalized preview median luminance and maps
    it to a bounded median target preserving low-key/high-key intent while enabling
    exposure correction. Low-key medians map to a low-key target, high-key medians map
    to a high-key target, and mid-key medians map to neutral target `0.5`.
    @param p_median {float} Normalized median luminance in `(0.0, 1.0)`.
    @return {float} Scene-key-preserving median target in `(0.0, 1.0)`.
    @satisfies REQ-097, REQ-098
    """

    if p_median <= AUTO_ZERO_SCENE_KEY_LOW_THRESHOLD:
        return AUTO_ZERO_TARGET_LOW_KEY
    if p_median >= AUTO_ZERO_SCENE_KEY_HIGH_THRESHOLD:
        return AUTO_ZERO_TARGET_HIGH_KEY
    return AUTO_EV_MEDIAN_TARGET


def _optimize_auto_zero(auto_ev_inputs):
    """@brief Compute optimal EV-zero center from normalized luminance statistics.

    @details Solves `ev_zero=log2(target_median/p_median)` using a scene-key-preserving
    target derived from preview median luminance, clamps result to
    `[-SAFE_ZERO_MAX,+SAFE_ZERO_MAX]` where `SAFE_ZERO_MAX=max(ev_values)`, and quantizes to
    nearest quarter-step represented by `ev_values` with sign preservation.
    @param auto_ev_inputs {AutoEvInputs} Adaptive EV scalar inputs.
    @return {float} Quantized EV-zero center.
    @satisfies REQ-094, REQ-095, REQ-097, REQ-098
    """

    base_max = auto_ev_inputs.ev_values[-1]
    target_median = _derive_scene_key_preserving_median_target(auto_ev_inputs.p_median)
    ev_zero_candidate = math.log2(target_median / auto_ev_inputs.p_median)
    ev_zero_clamped = max(-base_max, min(base_max, ev_zero_candidate))
    if math.isclose(ev_zero_clamped, 0.0, rel_tol=0.0, abs_tol=1e-9):
        return 0.0
    quantized_abs = _quantize_ev_to_supported(abs(ev_zero_clamped), auto_ev_inputs.ev_values)
    if ev_zero_clamped >= 0.0:
        return quantized_abs
    return -quantized_abs


def _optimize_adaptive_ev_delta(auto_ev_inputs):
    """@brief Compute adaptive EV delta from preview luminance statistics.

    @details Computes symmetric delta constraints around resolved EV-zero:
    `ev_shadow=max(0, log2(target_shadow/p_low)-ev_zero)` and
    `ev_high=max(0, ev_zero-log2(target_highlight/p_high))`, chooses maximum as
    safe symmetric bracket half-width, then clamps and quantizes to supported
    EV selector set.
    @param auto_ev_inputs {AutoEvInputs} Adaptive EV scalar inputs.
    @return {float} Quantized adaptive EV delta.
    @satisfies REQ-080, REQ-081, REQ-093, REQ-095
    """

    ev_shadow = max(
        0.0,
        math.log2(auto_ev_inputs.target_shadow / auto_ev_inputs.p_low)
        - auto_ev_inputs.ev_zero,
    )
    ev_high = max(
        0.0,
        auto_ev_inputs.ev_zero
        - math.log2(auto_ev_inputs.target_highlight / auto_ev_inputs.p_high),
    )
    ev_candidate = max(ev_shadow, ev_high)
    if ev_candidate <= 0.0:
        ev_candidate = EV_STEP
    clamped_candidate = _clamp_ev_to_supported(ev_candidate, auto_ev_inputs.ev_values)
    return _quantize_ev_to_supported(clamped_candidate, auto_ev_inputs.ev_values)


def _compute_auto_ev_value_from_stats(
    p_low,
    p_median,
    p_high,
    supported_ev_values,
    ev_zero=0.0,
):
    """@brief Compute adaptive EV selector from normalized preview luminance stats.

    @details Builds adaptive-EV input container from already extracted normalized
    percentiles and solves symmetric EV delta around resolved `ev_zero`.
    @param p_low {float} Normalized low percentile luminance.
    @param p_median {float} Normalized median percentile luminance.
    @param p_high {float} Normalized high percentile luminance.
    @param supported_ev_values {tuple[float, ...]} Bit-depth-derived supported EV selector tuple.
    @param ev_zero {float} Resolved EV-zero center used as adaptive solver anchor.
    @return {float} Adaptive EV selector value from bit-depth-derived selector set.
    @satisfies REQ-080, REQ-081, REQ-093, REQ-095
    """

    auto_ev_inputs = AutoEvInputs(
        p_low=p_low,
        p_median=p_median,
        p_high=p_high,
        target_shadow=AUTO_EV_TARGET_SHADOW,
        target_highlight=AUTO_EV_TARGET_HIGHLIGHT,
        median_target=AUTO_EV_MEDIAN_TARGET,
        ev_zero=ev_zero,
        ev_values=supported_ev_values,
    )
    return _optimize_adaptive_ev_delta(auto_ev_inputs)


def _compute_auto_ev_value(raw_handle, supported_ev_values=None, ev_zero=0.0):
    """@brief Compute adaptive EV selector from RAW linear preview histogram.

    @details Extracts normalized luminance percentiles (`0.1`, `50.0`, `99.9`)
    from one linear RAW preview and computes symmetric adaptive EV delta around
    resolved `ev_zero`, then clamps and quantizes to bit-depth-derived selector
    bounds.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @param supported_ev_values {tuple[float, ...]|None} Optional bit-derived EV selector tuple.
    @param ev_zero {float} Resolved EV-zero center used as adaptive solver anchor.
    @return {float} Adaptive EV selector value from bit-depth-derived selector set.
    @exception ValueError Raised when preview luminance extraction cannot produce valid values.
    @satisfies REQ-080, REQ-081, REQ-092, REQ-093, REQ-095, REQ-096
    """

    p_low, p_median, p_high = _extract_normalized_preview_luminance_stats(raw_handle)
    if supported_ev_values is None:
        bits_per_color = _detect_dng_bits_per_color(raw_handle)
        supported_ev_values = _derive_supported_ev_values(bits_per_color)
    return _compute_auto_ev_value_from_stats(
        p_low=p_low,
        p_median=p_median,
        p_high=p_high,
        supported_ev_values=supported_ev_values,
        ev_zero=ev_zero,
    )


def _resolve_ev_zero(
    raw_handle,
    ev_zero,
    auto_zero_enabled,
    auto_zero_pct,
    base_max_ev,
    supported_ev_values_for_auto_zero,
    preview_luminance_stats=None,
):
    """@brief Resolve EV-zero center from manual or automatic selector.

    @details Uses manual `--ev-zero` unless `--auto-zero` is enabled. In
    automatic mode computes EV-zero from normalized median luminance and
    quantizes to supported quarter-step values. Applies final safe-range clamp
    preserving at least `±1EV` bracket margin.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @param ev_zero {float} Parsed manual EV-zero candidate.
    @param auto_zero_enabled {bool} Auto-zero selector state.
    @param auto_zero_pct {float} Percentage scaler applied to computed auto-zero result.
    @param base_max_ev {float} Bit-derived `BASE_MAX` limit.
    @param supported_ev_values_for_auto_zero {tuple[float, ...]} Supported non-negative EV-zero magnitudes for quantization.
    @param preview_luminance_stats {tuple[float, float, float]|None} Optional precomputed `(p_low, p_median, p_high)` tuple to avoid duplicate preview extraction.
    @return {float} Resolved EV-zero center.
    @exception ValueError Raised when resolved EV-zero is outside bit-derived safe range.
    @satisfies REQ-094, REQ-095, REQ-097, REQ-098
    """

    resolved_ev_zero = ev_zero
    if auto_zero_enabled:
        if preview_luminance_stats is None:
            p_low, p_median, p_high = _extract_normalized_preview_luminance_stats(raw_handle)
        else:
            p_low, p_median, p_high = preview_luminance_stats
        auto_zero_inputs = AutoEvInputs(
            p_low=p_low,
            p_median=p_median,
            p_high=p_high,
            target_shadow=AUTO_EV_TARGET_SHADOW,
            target_highlight=AUTO_EV_TARGET_HIGHLIGHT,
            median_target=AUTO_EV_MEDIAN_TARGET,
            ev_zero=0.0,
            ev_values=supported_ev_values_for_auto_zero,
        )
        resolved_ev_zero = _optimize_auto_zero(auto_zero_inputs)
        resolved_ev_zero = _apply_auto_percentage_scaling(
            resolved_ev_zero, auto_zero_pct
        )
    safe_ev_zero_max = _calculate_safe_ev_zero_max(base_max_ev)
    if abs(resolved_ev_zero) > (safe_ev_zero_max + 1e-9):
        raise ValueError(
            "Unsupported --ev-zero value: "
            f"{resolved_ev_zero:g}; allowed range for input DNG is "
            f"{-safe_ev_zero_max:g}..{safe_ev_zero_max:g} in 0.25 steps "
            "(SAFE_ZERO_MAX = ((bits_per_color-8)/2)-1)"
        )
    return round(resolved_ev_zero, 2)


def _resolve_ev_value(
    raw_handle,
    ev_value,
    auto_ev_enabled,
    auto_ev_pct,
    supported_ev_values=None,
    ev_zero=0.0,
    preview_luminance_stats=None,
):
    """@brief Resolve effective EV selector for static or adaptive mode.

    @details Returns explicit static `--ev` value when adaptive mode is not
    enabled and validates it against bit-derived supported EV selectors. In
    adaptive mode, computes EV from RAW linear preview statistics.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @param ev_value {float|None} Parsed static EV option value.
    @param auto_ev_enabled {bool} Adaptive mode selector state.
    @param auto_ev_pct {float} Percentage scaler applied to computed adaptive EV delta.
    @param supported_ev_values {tuple[float, ...]|None} Optional bit-derived EV selector tuple.
    @param ev_zero {float} Resolved EV-zero center used for adaptive EV solver anchoring.
    @param preview_luminance_stats {tuple[float, float, float]|None} Optional precomputed `(p_low, p_median, p_high)` tuple to avoid duplicate preview extraction.
    @return {float} Effective EV selector value used for bracket multipliers.
    @exception ValueError Raised when no static EV is provided while adaptive mode is disabled.
    @satisfies REQ-056, REQ-057, REQ-080, REQ-081, REQ-092, REQ-093, REQ-095, REQ-096
    """

    effective_supported_values = supported_ev_values
    if effective_supported_values is None:
        bits_per_color = _detect_dng_bits_per_color(raw_handle)
        effective_supported_values = _derive_supported_ev_values(bits_per_color)
    if auto_ev_enabled:
        computed_auto_ev = None
        if preview_luminance_stats is not None:
            p_low, p_median, p_high = preview_luminance_stats
            computed_auto_ev = _compute_auto_ev_value_from_stats(
                p_low=p_low,
                p_median=p_median,
                p_high=p_high,
                supported_ev_values=effective_supported_values,
                ev_zero=ev_zero,
            )
        else:
            computed_auto_ev = _compute_auto_ev_value(
                raw_handle,
                supported_ev_values=effective_supported_values,
                ev_zero=ev_zero,
            )
        scaled_auto_ev = _apply_auto_percentage_scaling(computed_auto_ev, auto_ev_pct)
        return _clamp_ev_to_supported(scaled_auto_ev, effective_supported_values)
    if ev_value is None:
        raise ValueError("Missing static EV value")
    if ev_value not in effective_supported_values:
        max_ev = effective_supported_values[-1]
        raise ValueError(
            f"Unsupported --ev value: {ev_value:g}; allowed range for input DNG is 0.25..{max_ev:g} in 0.25 steps"
            " (MAX_BRACKET = ((bits_per_color-8)/2)-abs(ev_zero))"
        )
    return ev_value


def _parse_luminance_text_option(option_name, option_raw):
    """@brief Parse and validate non-empty luminance string option value.

    @details Normalizes surrounding spaces, lowercases token, rejects empty
    values, and rejects ambiguous values that start with option prefix marker.
    @param option_name {str} Long-option identifier used in error messages.
    @param option_raw {str} Raw option token value from CLI args.
    @return {str|None} Parsed normalized option token when valid; `None` otherwise.
    @satisfies REQ-061
    """

    option_value = option_raw.strip().lower()
    if not option_value:
        print_error(f"Invalid {option_name} value: empty value")
        return None
    if option_value.startswith("-"):
        print_error(f"Invalid {option_name} value: {option_raw}")
        return None
    return option_value


def _parse_gamma_option(gamma_raw):
    """@brief Parse and validate one gamma option value pair.

    @details Accepts comma-separated positive float pair in `a,b` format with
    optional surrounding parentheses, normalizes to `(a, b)` tuple, and rejects
    malformed, non-numeric, or non-positive values.
    @param gamma_raw {str} Raw gamma token extracted from CLI args.
    @return {tuple[float, float]|None} Parsed gamma tuple when valid; `None` otherwise.
    @satisfies REQ-064
    """

    gamma_text = gamma_raw.strip()
    if gamma_text.startswith("(") and gamma_text.endswith(")"):
        gamma_text = gamma_text[1:-1].strip()

    gamma_parts = [part.strip() for part in gamma_text.split(",")]
    if len(gamma_parts) != 2 or not gamma_parts[0] or not gamma_parts[1]:
        print_error(f"Invalid --gamma value: {gamma_raw}")
        print_error("Expected format: --gamma=<a,b> with positive numeric values.")
        return None

    try:
        gamma_a = float(gamma_parts[0])
        gamma_b = float(gamma_parts[1])
    except ValueError:
        print_error(f"Invalid --gamma value: {gamma_raw}")
        print_error("Expected format: --gamma=<a,b> with positive numeric values.")
        return None

    if gamma_a <= 0.0 or gamma_b <= 0.0:
        print_error(f"Invalid --gamma value: {gamma_raw}")
        print_error("Gamma values must be greater than zero.")
        return None

    return (gamma_a, gamma_b)


def _parse_positive_float_option(option_name, option_raw):
    """@brief Parse and validate one positive float option value.

    @details Converts option token to `float`, requires value greater than zero,
    and emits deterministic parse errors on malformed values.
    @param option_name {str} Long-option identifier used in error messages.
    @param option_raw {str} Raw option token value from CLI args.
    @return {float|None} Parsed positive float value when valid; `None` otherwise.
    @satisfies REQ-065
    """

    try:
        option_value = float(option_raw)
    except ValueError:
        print_error(f"Invalid {option_name} value: {option_raw}")
        return None

    if option_value <= 0.0:
        print_error(f"Invalid {option_name} value: {option_raw}")
        print_error(f"{option_name} must be greater than zero.")
        return None
    return option_value


def _parse_tmo_passthrough_value(option_name, option_raw):
    """@brief Parse and validate one luminance `--tmo*` passthrough value.

    @details Rejects empty values and preserves original payload for
    transparent forwarding to `luminance-hdr-cli`.
    @param option_name {str} Long-option identifier used in error messages.
    @param option_raw {str} Raw option token value from CLI args.
    @return {str|None} Original value when valid; `None` otherwise.
    @satisfies REQ-067
    """

    if option_raw.strip() == "":
        print_error(f"Invalid {option_name} value: empty value")
        return None
    return option_raw


def _parse_jpg_compression_option(compression_raw):
    """@brief Parse and validate JPEG compression option value.

    @details Converts option token to `int`, requires inclusive range
    `[0, 100]`, and emits deterministic parse errors on malformed values.
    @param compression_raw {str} Raw compression token value from CLI args.
    @return {int|None} Parsed JPEG compression level when valid; `None` otherwise.
    @satisfies REQ-065
    """

    try:
        compression_value = int(compression_raw)
    except ValueError:
        print_error(f"Invalid --jpg-compression value: {compression_raw}")
        return None

    if compression_value < 0 or compression_value > 100:
        print_error(f"Invalid --jpg-compression value: {compression_raw}")
        print_error("Allowed range: 0..100")
        return None
    return compression_value


def _parse_float_exclusive_range_option(option_name, option_raw, min_value, max_value):
    """@brief Parse and validate one float option in an exclusive range.

    @details Converts option token to `float`, validates `min < value < max`,
    and emits deterministic parse errors on malformed or out-of-range values.
    @param option_name {str} Long-option identifier used in error messages.
    @param option_raw {str} Raw option token value from CLI args.
    @param min_value {float} Exclusive minimum bound.
    @param max_value {float} Exclusive maximum bound.
    @return {float|None} Parsed float value when valid; `None` otherwise.
    @satisfies REQ-065, REQ-089
    """

    try:
        option_value = float(option_raw)
    except ValueError:
        print_error(f"Invalid {option_name} value: {option_raw}")
        return None
    if option_value <= min_value or option_value >= max_value:
        print_error(f"Invalid {option_name} value: {option_raw}")
        print_error(f"Allowed range: ({min_value:g},{max_value:g})")
        return None
    return option_value


def _parse_non_negative_float_option(option_name, option_raw):
    """@brief Parse and validate one non-negative float option value.

    @details Converts option token to `float`, requires value greater than or
    equal to zero, and emits deterministic parse errors on malformed values.
    @param option_name {str} Long-option identifier used in error messages.
    @param option_raw {str} Raw option token value from CLI args.
    @return {float|None} Parsed non-negative float value when valid; `None` otherwise.
    @satisfies REQ-065, REQ-089
    """

    try:
        option_value = float(option_raw)
    except ValueError:
        print_error(f"Invalid {option_name} value: {option_raw}")
        return None
    if option_value < 0.0:
        print_error(f"Invalid {option_name} value: {option_raw}")
        print_error(f"{option_name} must be greater than or equal to zero.")
        return None
    return option_value


def _parse_float_in_range_option(option_name, option_raw, min_value, max_value):
    """@brief Parse and validate one float option constrained to inclusive range.

    @details Converts option token to `float`, validates inclusive bounds, and
    emits deterministic parse errors on malformed or out-of-range values.
    @param option_name {str} Long-option identifier used in error messages.
    @param option_raw {str} Raw option token value from CLI args.
    @param min_value {float} Inclusive minimum bound.
    @param max_value {float} Inclusive maximum bound.
    @return {float|None} Parsed bounded float value when valid; `None` otherwise.
    @satisfies REQ-082, REQ-084
    """

    try:
        option_value = float(option_raw)
    except ValueError:
        print_error(f"Invalid {option_name} value: {option_raw}")
        return None

    if option_value < min_value or option_value > max_value:
        print_error(f"Invalid {option_name} value: {option_raw}")
        print_error(f"Allowed range: {min_value:g}..{max_value:g}")
        return None
    return option_value


def _parse_auto_brightness_options(auto_brightness_raw_values):
    """@brief Parse and validate auto-brightness parameters.

    @details Parses optional key-value and compression controls for the
    photographic BT.709 16-bit tonemap pipeline and applies deterministic
    defaults for omitted auto-brightness options.
    @param auto_brightness_raw_values {dict[str, str]} Raw `--ab-*` option values keyed by long option name.
    @return {AutoBrightnessOptions|None} Parsed auto-brightness options or `None` on validation error.
    @satisfies REQ-088, REQ-089, REQ-103, REQ-104, REQ-105
    """

    defaults = AutoBrightnessOptions()
    key_value = defaults.key_value
    white_point_percentile = defaults.white_point_percentile
    key_min = defaults.key_min
    key_max = defaults.key_max
    max_auto_boost_factor = defaults.max_auto_boost_factor
    local_contrast_strength = defaults.local_contrast_strength
    clahe_clip_limit = defaults.clahe_clip_limit

    if "--ab-key-value" in auto_brightness_raw_values:
        parsed = _parse_positive_float_option(
            "--ab-key-value", auto_brightness_raw_values["--ab-key-value"]
        )
        if parsed is None:
            return None
        key_value = parsed

    if "--ab-white-point-pct" in auto_brightness_raw_values:
        parsed = _parse_float_exclusive_range_option(
            "--ab-white-point-pct",
            auto_brightness_raw_values["--ab-white-point-pct"],
            0.0,
            100.0,
        )
        if parsed is None:
            return None
        white_point_percentile = parsed

    if "--ab-key-min" in auto_brightness_raw_values:
        parsed = _parse_positive_float_option(
            "--ab-key-min", auto_brightness_raw_values["--ab-key-min"]
        )
        if parsed is None:
            return None
        key_min = parsed

    if "--ab-key-max" in auto_brightness_raw_values:
        parsed = _parse_positive_float_option(
            "--ab-key-max", auto_brightness_raw_values["--ab-key-max"]
        )
        if parsed is None:
            return None
        key_max = parsed

    if key_min > key_max:
        print_error("Invalid --ab-key-min/--ab-key-max values")
        print_error("--ab-key-min must be less than or equal to --ab-key-max")
        return None

    if "--ab-max-auto-boost" in auto_brightness_raw_values:
        parsed = _parse_positive_float_option(
            "--ab-max-auto-boost",
            auto_brightness_raw_values["--ab-max-auto-boost"],
        )
        if parsed is None:
            return None
        max_auto_boost_factor = parsed

    if "--ab-local-contrast-strength" in auto_brightness_raw_values:
        parsed = _parse_float_in_range_option(
            "--ab-local-contrast-strength",
            auto_brightness_raw_values["--ab-local-contrast-strength"],
            0.0,
            1.0,
        )
        if parsed is None:
            return None
        local_contrast_strength = parsed

    if "--ab-clahe-clip-limit" in auto_brightness_raw_values:
        parsed = _parse_positive_float_option(
            "--ab-clahe-clip-limit",
            auto_brightness_raw_values["--ab-clahe-clip-limit"],
        )
        if parsed is None:
            return None
        clahe_clip_limit = parsed

    return AutoBrightnessOptions(
        key_value=key_value,
        white_point_percentile=white_point_percentile,
        key_min=key_min,
        key_max=key_max,
        max_auto_boost_factor=max_auto_boost_factor,
        local_contrast_strength=local_contrast_strength,
        clahe_clip_limit=clahe_clip_limit,
        clahe_tile_grid_size=defaults.clahe_tile_grid_size,
        eps=defaults.eps,
    )


def _parse_auto_levels_hr_method_option(auto_levels_method_raw):
    """@brief Parse auto-levels highlight reconstruction method option value.

    @details Validates case-insensitive method names and normalizes accepted
    values to canonical tokens used by runtime dispatch.
    @param auto_levels_method_raw {str} Raw `--al-highlight-reconstruction-method` option token.
    @return {str|None} Canonical method token or `None` on parse failure.
    @satisfies REQ-101, REQ-102, REQ-119
    """

    method_text = auto_levels_method_raw.strip()
    if not method_text:
        print_error("Invalid --al-highlight-reconstruction-method value: empty value")
        return None
    canonical_method = None
    for allowed_method in _AUTO_LEVELS_HIGHLIGHT_METHODS:
        if method_text.lower() == allowed_method.lower():
            canonical_method = allowed_method
            break
    if canonical_method is None:
        print_error(
            "Invalid --al-highlight-reconstruction-method value: "
            f"{auto_levels_method_raw}"
        )
        print_error(
            "Allowed values: "
            + ", ".join(_AUTO_LEVELS_HIGHLIGHT_METHODS)
        )
        return None
    return canonical_method


def _parse_auto_levels_options(auto_levels_raw_values):
    """@brief Parse and validate auto-levels parameters.

    @details Parses histogram clip percentage, explicit gamut clipping toggle,
    optional highlight reconstruction method, and Inpaint Opposed gain
    threshold using RawTherapee-aligned defaults.
    @param auto_levels_raw_values {dict[str, str]} Raw `--al-*` option values keyed by long option name.
    @return {AutoLevelsOptions|None} Parsed auto-levels options or `None` on validation error.
    @satisfies REQ-100, REQ-101, REQ-102, REQ-116
    """

    options = AutoLevelsOptions()
    clip_percent = options.clip_percent
    clip_out_of_gamut = options.clip_out_of_gamut
    histcompr = options.histcompr
    highlight_reconstruction_enabled = options.highlight_reconstruction_enabled
    highlight_reconstruction_method = options.highlight_reconstruction_method
    gain_threshold = options.gain_threshold

    if "--al-clip-pct" in auto_levels_raw_values:
        parsed = _parse_non_negative_float_option(
            "--al-clip-pct", auto_levels_raw_values["--al-clip-pct"]
        )
        if parsed is None:
            return None
        clip_percent = parsed

    if "--al-clip-out-of-gamut" in auto_levels_raw_values:
        parsed = _parse_explicit_boolean_option(
            "--al-clip-out-of-gamut",
            auto_levels_raw_values["--al-clip-out-of-gamut"],
        )
        if parsed is None:
            return None
        clip_out_of_gamut = parsed

    if "--al-highlight-reconstruction-method" in auto_levels_raw_values:
        parsed = _parse_auto_levels_hr_method_option(
            auto_levels_raw_values["--al-highlight-reconstruction-method"]
        )
        if parsed is None:
            return None
        highlight_reconstruction_enabled = True
        highlight_reconstruction_method = parsed

    if "--al-gain-threshold" in auto_levels_raw_values:
        parsed = _parse_positive_float_option(
            "--al-gain-threshold",
            auto_levels_raw_values["--al-gain-threshold"],
        )
        if parsed is None:
            return None
        gain_threshold = parsed

    return AutoLevelsOptions(
        clip_percent=clip_percent,
        clip_out_of_gamut=clip_out_of_gamut,
        histcompr=histcompr,
        highlight_reconstruction_enabled=highlight_reconstruction_enabled,
        highlight_reconstruction_method=highlight_reconstruction_method,
        gain_threshold=gain_threshold,
    )


def _parse_auto_adjust_options(auto_adjust_raw_values):
    """@brief Parse and validate shared auto-adjust knobs for both implementations.

    @details Applies defaults for omitted knobs, validates scalar/range
    constraints, and enforces level percentile ordering contract.
    @param auto_adjust_raw_values {dict[str, str]} Raw `--aa-*` option values keyed by long option name.
    @return {AutoAdjustOptions|None} Parsed shared auto-adjust options or `None` on validation error.
    @satisfies REQ-082, REQ-083, REQ-084
    """

    options = AutoAdjustOptions()
    blur_sigma = options.blur_sigma
    blur_threshold_pct = options.blur_threshold_pct
    level_low_pct = options.level_low_pct
    level_high_pct = options.level_high_pct
    sigmoid_contrast = options.sigmoid_contrast
    sigmoid_midpoint = options.sigmoid_midpoint
    saturation_gamma = options.saturation_gamma
    highpass_blur_sigma = options.highpass_blur_sigma

    if "--aa-blur-sigma" in auto_adjust_raw_values:
        parsed = _parse_positive_float_option(
            "--aa-blur-sigma", auto_adjust_raw_values["--aa-blur-sigma"]
        )
        if parsed is None:
            return None
        blur_sigma = parsed
    if "--aa-blur-threshold-pct" in auto_adjust_raw_values:
        parsed = _parse_float_in_range_option(
            "--aa-blur-threshold-pct",
            auto_adjust_raw_values["--aa-blur-threshold-pct"],
            0.0,
            100.0,
        )
        if parsed is None:
            return None
        blur_threshold_pct = parsed
    if "--aa-level-low-pct" in auto_adjust_raw_values:
        parsed = _parse_float_in_range_option(
            "--aa-level-low-pct",
            auto_adjust_raw_values["--aa-level-low-pct"],
            0.0,
            100.0,
        )
        if parsed is None:
            return None
        level_low_pct = parsed
    if "--aa-level-high-pct" in auto_adjust_raw_values:
        parsed = _parse_float_in_range_option(
            "--aa-level-high-pct",
            auto_adjust_raw_values["--aa-level-high-pct"],
            0.0,
            100.0,
        )
        if parsed is None:
            return None
        level_high_pct = parsed
    if level_low_pct >= level_high_pct:
        print_error(
            "Invalid auto-adjust levels: --aa-level-low-pct must be lower than --aa-level-high-pct"
        )
        return None
    if "--aa-sigmoid-contrast" in auto_adjust_raw_values:
        parsed = _parse_positive_float_option(
            "--aa-sigmoid-contrast", auto_adjust_raw_values["--aa-sigmoid-contrast"]
        )
        if parsed is None:
            return None
        sigmoid_contrast = parsed
    if "--aa-sigmoid-midpoint" in auto_adjust_raw_values:
        parsed = _parse_float_in_range_option(
            "--aa-sigmoid-midpoint",
            auto_adjust_raw_values["--aa-sigmoid-midpoint"],
            0.0,
            1.0,
        )
        if parsed is None:
            return None
        sigmoid_midpoint = parsed
    if "--aa-saturation-gamma" in auto_adjust_raw_values:
        parsed = _parse_positive_float_option(
            "--aa-saturation-gamma", auto_adjust_raw_values["--aa-saturation-gamma"]
        )
        if parsed is None:
            return None
        saturation_gamma = parsed
    if "--aa-highpass-blur-sigma" in auto_adjust_raw_values:
        parsed = _parse_positive_float_option(
            "--aa-highpass-blur-sigma",
            auto_adjust_raw_values["--aa-highpass-blur-sigma"],
        )
        if parsed is None:
            return None
        highpass_blur_sigma = parsed

    return AutoAdjustOptions(
        blur_sigma=blur_sigma,
        blur_threshold_pct=blur_threshold_pct,
        level_low_pct=level_low_pct,
        level_high_pct=level_high_pct,
        sigmoid_contrast=sigmoid_contrast,
        sigmoid_midpoint=sigmoid_midpoint,
        saturation_gamma=saturation_gamma,
        highpass_blur_sigma=highpass_blur_sigma,
    )


def _parse_auto_adjust_mode_option(auto_adjust_raw):
    """@brief Parse auto-adjust implementation selector option value.

    @details Accepts case-insensitive auto-adjust implementation names and normalizes
    to canonical values for runtime dispatch.
    @param auto_adjust_raw {str} Raw auto-adjust implementation token.
    @return {str|None} Canonical auto-adjust mode (`ImageMagick` or `OpenCV`) or `None` on parse failure.
    @satisfies REQ-065, REQ-073, REQ-075
    """

    auto_adjust_text = auto_adjust_raw.strip()
    if not auto_adjust_text:
        print_error("Invalid --auto-adjust value: empty value")
        return None
    auto_adjust_text_lower = auto_adjust_text.lower()
    if auto_adjust_text_lower == "imagemagick":
        return "ImageMagick"
    if auto_adjust_text_lower == "opencv":
        return "OpenCV"
    print_error(f"Invalid --auto-adjust value: {auto_adjust_raw}")
    print_error("Allowed values: ImageMagick, OpenCV")
    return None


def _resolve_default_postprocess(
    enable_luminance,
    enable_opencv,
    enable_hdr_plus,
    luminance_tmo,
):
    """@brief Resolve backend-specific postprocess defaults.

    @details Selects neutral defaults for enfuse/OpenCV/HDR+ and non-tuned luminance
    operators, and selects tuned defaults for luminance `reinhard02` and
    `mantiuk08`.
    @param enable_luminance {bool} Backend selector state.
    @param enable_opencv {bool} OpenCV backend selector state.
    @param enable_hdr_plus {bool} HDR+ backend selector state.
    @param luminance_tmo {str} Selected luminance tone-mapping operator.
    @return {tuple[float, float, float, float]} Defaults in `(post_gamma, brightness, contrast, saturation)` order.
    @satisfies REQ-069, REQ-071, REQ-072, REQ-091, REQ-107, REQ-111
    """

    del enable_opencv
    del enable_hdr_plus
    if not enable_luminance:
        return (
            DEFAULT_POST_GAMMA,
            DEFAULT_BRIGHTNESS,
            DEFAULT_CONTRAST,
            DEFAULT_SATURATION,
        )

    if luminance_tmo == "reinhard02":
        return (
            DEFAULT_POST_GAMMA,
            DEFAULT_REINHARD02_BRIGHTNESS,
            DEFAULT_REINHARD02_CONTRAST,
            DEFAULT_REINHARD02_SATURATION,
        )
    if luminance_tmo == "mantiuk08":
        return (
            DEFAULT_POST_GAMMA,
            DEFAULT_BRIGHTNESS,
            DEFAULT_MANTIUK08_CONTRAST,
            DEFAULT_SATURATION,
        )

    return (
        DEFAULT_POST_GAMMA,
        DEFAULT_BRIGHTNESS,
        DEFAULT_CONTRAST,
        DEFAULT_SATURATION,
    )


def _parse_run_options(args):
    """@brief Parse CLI args into input, output, and EV parameters.

    @details Supports positional file arguments, required mutually exclusive
    exposure selectors (`--ev=<value>`/`--ev <value>` or
    `--auto-ev[=<1|true|yes|on>]`), optional `--ev-zero=<value>` or
    `--ev-zero <value>`, optional `--auto-zero[=<1|true|yes|on>]`,
    optional `--auto-zero-pct=<0..100>`, optional `--auto-ev-pct=<0..100>`,
    optional `--gamma=<a,b>` or `--gamma <a,b>`,
    optional postprocess controls, optional auto-brightness stage and
    `--ab-*` knobs, optional auto-levels stage and `--al-*` knobs,
    optional shared auto-adjust knobs, required backend selector
    (`--enable-enfuse`, `--enable-luminance`, `--enable-opencv`, or
    `--enable-hdr-plus`), and luminance backend controls
    including explicit `--tmo*` passthrough options and optional
    auto-adjust implementation selector (`--auto-adjust <ImageMagick|OpenCV>`);
    rejects unknown options and invalid arity.
    @param args {list[str]} Raw command argument vector.
    @return {tuple[Path, Path, float|None, bool, tuple[float, float], PostprocessOptions, bool, bool, LuminanceOptions, OpenCvMergeOptions, bool, float, bool, float, float]|None} Parsed `(input, output, ev, auto_ev, gamma, postprocess, enable_luminance, enable_opencv, luminance_options, opencv_merge_options, enable_hdr_plus, ev_zero, auto_zero_enabled, auto_zero_pct, auto_ev_pct)` tuple; `None` on parse failure.
    @satisfies REQ-055, REQ-056, REQ-057, REQ-060, REQ-061, REQ-064, REQ-065, REQ-067, REQ-069, REQ-071, REQ-072, REQ-073, REQ-075, REQ-079, REQ-080, REQ-081, REQ-082, REQ-083, REQ-084, REQ-085, REQ-087, REQ-088, REQ-089, REQ-090, REQ-091, REQ-094, REQ-097, REQ-107, REQ-108, REQ-111
    """

    positional = []
    ev_value = None
    auto_ev_enabled = False
    ev_zero = 0.0
    ev_zero_specified = False
    auto_zero_enabled = False
    auto_zero_pct = DEFAULT_AUTO_ZERO_PCT
    auto_ev_pct = DEFAULT_AUTO_EV_PCT
    gamma_value = DEFAULT_GAMMA
    post_gamma = DEFAULT_POST_GAMMA
    brightness = DEFAULT_BRIGHTNESS
    contrast = DEFAULT_CONTRAST
    saturation = DEFAULT_SATURATION
    jpg_compression = DEFAULT_JPG_COMPRESSION
    post_gamma_set = False
    brightness_set = False
    contrast_set = False
    saturation_set = False
    auto_brightness_enabled = False
    auto_brightness_raw_values = {}
    auto_levels_enabled = False
    auto_levels_raw_values = {}
    auto_adjust_mode = None
    auto_adjust_raw_values = {}
    enable_enfuse = False
    enable_luminance = False
    enable_opencv = False
    enable_hdr_plus = False
    luminance_hdr_model = DEFAULT_LUMINANCE_HDR_MODEL
    luminance_hdr_weight = DEFAULT_LUMINANCE_HDR_WEIGHT
    luminance_hdr_response_curve = DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE
    luminance_tmo = DEFAULT_LUMINANCE_TMO
    luminance_tmo_extra_args = []
    luminance_option_specified = False
    idx = 0

    while idx < len(args):
        token = args[idx]
        if token == "--enable-enfuse":
            enable_enfuse = True
            idx += 1
            continue

        if token == "--enable-luminance":
            enable_luminance = True
            idx += 1
            continue

        if token == "--enable-opencv":
            enable_opencv = True
            idx += 1
            continue

        if token == "--enable-hdr-plus":
            enable_hdr_plus = True
            idx += 1
            continue

        if token == "--auto-adjust":
            if idx + 1 >= len(args):
                print_error("Missing value for --auto-adjust")
                return None
            if args[idx + 1].startswith("--"):
                print_error("Missing value for --auto-adjust")
                return None
            parsed_auto_adjust_mode = _parse_auto_adjust_mode_option(args[idx + 1])
            if parsed_auto_adjust_mode is None:
                return None
            auto_adjust_mode = parsed_auto_adjust_mode
            idx += 2
            continue

        if token.startswith("--auto-adjust="):
            parsed_auto_adjust_mode = _parse_auto_adjust_mode_option(
                token.split("=", 1)[1]
            )
            if parsed_auto_adjust_mode is None:
                return None
            auto_adjust_mode = parsed_auto_adjust_mode
            idx += 1
            continue

        if token == "--auto-brightness":
            if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
                parsed_auto_brightness = _parse_auto_brightness_option(args[idx + 1])
                if parsed_auto_brightness is None:
                    return None
                auto_brightness_enabled = parsed_auto_brightness
                idx += 2
                continue
            auto_brightness_enabled = True
            idx += 1
            continue

        if token.startswith("--auto-brightness="):
            parsed_auto_brightness = _parse_auto_brightness_option(
                token.split("=", 1)[1]
            )
            if parsed_auto_brightness is None:
                return None
            auto_brightness_enabled = parsed_auto_brightness
            idx += 1
            continue

        if token.startswith("--ab-"):
            option_name = token
            option_value = None
            consume_count = 1
            if "=" in token:
                option_name, option_value = token.split("=", 1)
            else:
                if idx + 1 >= len(args):
                    print_error(f"Missing value for {token}")
                    return None
                option_value = args[idx + 1]
                if option_value.startswith("--"):
                    print_error(f"Missing value for {token}")
                    return None
                consume_count = 2
            if option_name not in _AUTO_BRIGHTNESS_KNOB_OPTIONS:
                print_error(f"Unknown option: {option_name}")
                return None
            auto_brightness_raw_values[option_name] = option_value
            idx += consume_count
            continue

        if token == "--auto-levels":
            if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
                parsed_auto_levels = _parse_auto_levels_option(args[idx + 1])
                if parsed_auto_levels is None:
                    return None
                auto_levels_enabled = parsed_auto_levels
                idx += 2
                continue
            auto_levels_enabled = True
            idx += 1
            continue

        if token.startswith("--auto-levels="):
            parsed_auto_levels = _parse_auto_levels_option(token.split("=", 1)[1])
            if parsed_auto_levels is None:
                return None
            auto_levels_enabled = parsed_auto_levels
            idx += 1
            continue

        if token.startswith("--al-"):
            if token == "--al-clip-out-of-gamut":
                if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
                    auto_levels_raw_values[token] = args[idx + 1]
                    idx += 2
                    continue
                auto_levels_raw_values[token] = "true"
                idx += 1
                continue
            option_name = token
            option_value = None
            consume_count = 1
            if "=" in token:
                option_name, option_value = token.split("=", 1)
            else:
                if idx + 1 >= len(args):
                    print_error(f"Missing value for {token}")
                    return None
                option_value = args[idx + 1]
                if option_value.startswith("--"):
                    print_error(f"Missing value for {token}")
                    return None
                consume_count = 2
            if option_name not in _AUTO_LEVELS_KNOB_OPTIONS:
                print_error(f"Unknown option: {option_name}")
                return None
            auto_levels_raw_values[option_name] = option_value
            idx += consume_count
            continue

        if token.startswith("--aa-"):
            option_name = token
            option_value = None
            consume_count = 1
            if "=" in token:
                option_name, option_value = token.split("=", 1)
            else:
                if idx + 1 >= len(args):
                    print_error(f"Missing value for {token}")
                    return None
                option_value = args[idx + 1]
                if option_value.startswith("--"):
                    print_error(f"Missing value for {token}")
                    return None
                consume_count = 2

            if option_name not in _AUTO_ADJUST_KNOB_OPTIONS:
                print_error(f"Unknown option: {option_name}")
                return None
            auto_adjust_raw_values[option_name] = option_value
            idx += consume_count
            continue

        if token == "--luminance-hdr-model":
            if idx + 1 >= len(args):
                print_error("Missing value for --luminance-hdr-model")
                return None
            parsed_value = _parse_luminance_text_option(
                "--luminance-hdr-model", args[idx + 1]
            )
            if parsed_value is None:
                return None
            luminance_hdr_model = parsed_value
            luminance_option_specified = True
            idx += 2
            continue

        if token.startswith("--luminance-hdr-model="):
            parsed_value = _parse_luminance_text_option(
                "--luminance-hdr-model", token.split("=", 1)[1]
            )
            if parsed_value is None:
                return None
            luminance_hdr_model = parsed_value
            luminance_option_specified = True
            idx += 1
            continue

        if token == "--luminance-hdr-weight":
            if idx + 1 >= len(args):
                print_error("Missing value for --luminance-hdr-weight")
                return None
            parsed_value = _parse_luminance_text_option(
                "--luminance-hdr-weight", args[idx + 1]
            )
            if parsed_value is None:
                return None
            luminance_hdr_weight = parsed_value
            luminance_option_specified = True
            idx += 2
            continue

        if token.startswith("--luminance-hdr-weight="):
            parsed_value = _parse_luminance_text_option(
                "--luminance-hdr-weight", token.split("=", 1)[1]
            )
            if parsed_value is None:
                return None
            luminance_hdr_weight = parsed_value
            luminance_option_specified = True
            idx += 1
            continue

        if token == "--luminance-hdr-response-curve":
            if idx + 1 >= len(args):
                print_error("Missing value for --luminance-hdr-response-curve")
                return None
            parsed_value = _parse_luminance_text_option(
                "--luminance-hdr-response-curve", args[idx + 1]
            )
            if parsed_value is None:
                return None
            luminance_hdr_response_curve = parsed_value
            luminance_option_specified = True
            idx += 2
            continue

        if token.startswith("--luminance-hdr-response-curve="):
            parsed_value = _parse_luminance_text_option(
                "--luminance-hdr-response-curve", token.split("=", 1)[1]
            )
            if parsed_value is None:
                return None
            luminance_hdr_response_curve = parsed_value
            luminance_option_specified = True
            idx += 1
            continue

        if token == "--luminance-tmo":
            if idx + 1 >= len(args):
                print_error("Missing value for --luminance-tmo")
                return None
            parsed_value = _parse_luminance_text_option(
                "--luminance-tmo", args[idx + 1]
            )
            if parsed_value is None:
                return None
            luminance_tmo = parsed_value
            luminance_option_specified = True
            idx += 2
            continue

        if token.startswith("--luminance-tmo="):
            parsed_value = _parse_luminance_text_option(
                "--luminance-tmo", token.split("=", 1)[1]
            )
            if parsed_value is None:
                return None
            luminance_tmo = parsed_value
            luminance_option_specified = True
            idx += 1
            continue

        if token.startswith("--tmo"):
            if token == "--tmo":
                print_error("Unknown option: --tmo")
                return None

            option_name = token
            option_value = None
            consume_count = 1
            if "=" in token:
                option_name, option_value = token.split("=", 1)
            else:
                if idx + 1 >= len(args):
                    print_error(f"Missing value for {token}")
                    return None
                option_value = args[idx + 1]
                if option_value.startswith("--"):
                    print_error(f"Missing value for {token}")
                    return None
                consume_count = 2

            parsed_value = _parse_tmo_passthrough_value(option_name, option_value)
            if parsed_value is None:
                return None
            luminance_tmo_extra_args.extend((option_name, parsed_value))
            luminance_option_specified = True
            idx += consume_count
            continue

        if token == "--ev":
            if idx + 1 >= len(args):
                print_error("Missing value for --ev")
                return None
            parsed_ev = _parse_ev_option(args[idx + 1])
            if parsed_ev is None:
                return None
            ev_value = parsed_ev
            idx += 2
            continue

        if token.startswith("--ev="):
            parsed_ev = _parse_ev_option(token.split("=", 1)[1])
            if parsed_ev is None:
                return None
            ev_value = parsed_ev
            idx += 1
            continue

        if token == "--auto-ev":
            auto_ev_enabled = True
            idx += 1
            continue

        if token.startswith("--auto-ev="):
            parsed_auto_ev = _parse_auto_ev_option(token.split("=", 1)[1])
            if parsed_auto_ev is None:
                return None
            auto_ev_enabled = parsed_auto_ev
            idx += 1
            continue

        if token == "--auto-zero":
            if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
                parsed_auto_zero = _parse_auto_zero_option(args[idx + 1])
                if parsed_auto_zero is None:
                    return None
                auto_zero_enabled = parsed_auto_zero
                idx += 2
                continue
            auto_zero_enabled = True
            idx += 1
            continue

        if token.startswith("--auto-zero="):
            parsed_auto_zero = _parse_auto_zero_option(token.split("=", 1)[1])
            if parsed_auto_zero is None:
                return None
            auto_zero_enabled = parsed_auto_zero
            idx += 1
            continue

        if token == "--auto-zero-pct":
            if idx + 1 >= len(args):
                print_error("Missing value for --auto-zero-pct")
                return None
            parsed_auto_zero_pct = _parse_percentage_option(
                "--auto-zero-pct", args[idx + 1]
            )
            if parsed_auto_zero_pct is None:
                return None
            auto_zero_pct = parsed_auto_zero_pct
            idx += 2
            continue

        if token.startswith("--auto-zero-pct="):
            parsed_auto_zero_pct = _parse_percentage_option(
                "--auto-zero-pct", token.split("=", 1)[1]
            )
            if parsed_auto_zero_pct is None:
                return None
            auto_zero_pct = parsed_auto_zero_pct
            idx += 1
            continue

        if token == "--auto-ev-pct":
            if idx + 1 >= len(args):
                print_error("Missing value for --auto-ev-pct")
                return None
            parsed_auto_ev_pct = _parse_percentage_option("--auto-ev-pct", args[idx + 1])
            if parsed_auto_ev_pct is None:
                return None
            auto_ev_pct = parsed_auto_ev_pct
            idx += 2
            continue

        if token.startswith("--auto-ev-pct="):
            parsed_auto_ev_pct = _parse_percentage_option(
                "--auto-ev-pct", token.split("=", 1)[1]
            )
            if parsed_auto_ev_pct is None:
                return None
            auto_ev_pct = parsed_auto_ev_pct
            idx += 1
            continue

        if token == "--ev-zero":
            if idx + 1 >= len(args):
                print_error("Missing value for --ev-zero")
                return None
            parsed_ev_zero = _parse_ev_zero_option(args[idx + 1])
            if parsed_ev_zero is None:
                return None
            ev_zero = parsed_ev_zero
            ev_zero_specified = True
            idx += 2
            continue

        if token.startswith("--ev-zero="):
            parsed_ev_zero = _parse_ev_zero_option(token.split("=", 1)[1])
            if parsed_ev_zero is None:
                return None
            ev_zero = parsed_ev_zero
            ev_zero_specified = True
            idx += 1
            continue

        if token == "--gamma":
            if idx + 1 >= len(args):
                print_error("Missing value for --gamma")
                return None
            parsed_gamma = _parse_gamma_option(args[idx + 1])
            if parsed_gamma is None:
                return None
            gamma_value = parsed_gamma
            idx += 2
            continue

        if token.startswith("--gamma="):
            parsed_gamma = _parse_gamma_option(token.split("=", 1)[1])
            if parsed_gamma is None:
                return None
            gamma_value = parsed_gamma
            idx += 1
            continue

        if token == "--post-gamma":
            if idx + 1 >= len(args):
                print_error("Missing value for --post-gamma")
                return None
            parsed_post_gamma = _parse_positive_float_option(
                "--post-gamma", args[idx + 1]
            )
            if parsed_post_gamma is None:
                return None
            post_gamma = parsed_post_gamma
            post_gamma_set = True
            idx += 2
            continue

        if token.startswith("--post-gamma="):
            parsed_post_gamma = _parse_positive_float_option(
                "--post-gamma", token.split("=", 1)[1]
            )
            if parsed_post_gamma is None:
                return None
            post_gamma = parsed_post_gamma
            post_gamma_set = True
            idx += 1
            continue

        if token == "--brightness":
            if idx + 1 >= len(args):
                print_error("Missing value for --brightness")
                return None
            parsed_brightness = _parse_positive_float_option(
                "--brightness", args[idx + 1]
            )
            if parsed_brightness is None:
                return None
            brightness = parsed_brightness
            brightness_set = True
            idx += 2
            continue

        if token.startswith("--brightness="):
            parsed_brightness = _parse_positive_float_option(
                "--brightness", token.split("=", 1)[1]
            )
            if parsed_brightness is None:
                return None
            brightness = parsed_brightness
            brightness_set = True
            idx += 1
            continue

        if token == "--contrast":
            if idx + 1 >= len(args):
                print_error("Missing value for --contrast")
                return None
            parsed_contrast = _parse_positive_float_option("--contrast", args[idx + 1])
            if parsed_contrast is None:
                return None
            contrast = parsed_contrast
            contrast_set = True
            idx += 2
            continue

        if token.startswith("--contrast="):
            parsed_contrast = _parse_positive_float_option(
                "--contrast", token.split("=", 1)[1]
            )
            if parsed_contrast is None:
                return None
            contrast = parsed_contrast
            contrast_set = True
            idx += 1
            continue

        if token == "--saturation":
            if idx + 1 >= len(args):
                print_error("Missing value for --saturation")
                return None
            parsed_saturation = _parse_positive_float_option(
                "--saturation", args[idx + 1]
            )
            if parsed_saturation is None:
                return None
            saturation = parsed_saturation
            saturation_set = True
            idx += 2
            continue

        if token.startswith("--saturation="):
            parsed_saturation = _parse_positive_float_option(
                "--saturation", token.split("=", 1)[1]
            )
            if parsed_saturation is None:
                return None
            saturation = parsed_saturation
            saturation_set = True
            idx += 1
            continue

        if token == "--jpg-compression":
            if idx + 1 >= len(args):
                print_error("Missing value for --jpg-compression")
                return None
            parsed_compression = _parse_jpg_compression_option(args[idx + 1])
            if parsed_compression is None:
                return None
            jpg_compression = parsed_compression
            idx += 2
            continue

        if token.startswith("--jpg-compression="):
            parsed_compression = _parse_jpg_compression_option(token.split("=", 1)[1])
            if parsed_compression is None:
                return None
            jpg_compression = parsed_compression
            idx += 1
            continue

        if token.startswith("-"):
            print_error(f"Unknown option: {token}")
            return None

        positional.append(token)
        idx += 1

    if len(positional) != 2:
        print_error(
            "Usage: dng2jpg <input.dng> <output.jpg> "
            "(--ev=<value> | --auto-ev) [--ev-zero=<value>] [--gamma=<a,b>]"
        )
        return None

    if (ev_value is None and not auto_ev_enabled) or (
        ev_value is not None and auto_ev_enabled
    ):
        print_error("Exactly one exposure selector is required: --ev or --auto-ev")
        return None
    if auto_zero_enabled and ev_zero_specified:
        print_error("Exactly one EV-zero selector is allowed: --ev-zero or --auto-zero")
        return None

    backend_enabled_count = (
        int(enable_enfuse)
        + int(enable_luminance)
        + int(enable_opencv)
        + int(enable_hdr_plus)
    )
    if backend_enabled_count != 1:
        print_error(
            "Exactly one backend selector is required: --enable-enfuse, --enable-luminance, --enable-opencv, or --enable-hdr-plus"
        )
        return None

    if luminance_option_specified and not enable_luminance:
        print_error("Luminance options require --enable-luminance")
        return None

    if auto_adjust_mode is None and auto_adjust_raw_values:
        invalid_knob = next(iter(auto_adjust_raw_values))
        print_error(
            f"Auto-adjust knob {invalid_knob} requires --auto-adjust <ImageMagick|OpenCV>"
        )
        return None
    if not auto_brightness_enabled and auto_brightness_raw_values:
        invalid_knob = next(iter(auto_brightness_raw_values))
        print_error(
            f"Auto-brightness knob {invalid_knob} requires --auto-brightness"
        )
        return None
    if not auto_levels_enabled and auto_levels_raw_values:
        invalid_knob = next(iter(auto_levels_raw_values))
        print_error(f"Auto-levels knob {invalid_knob} requires --auto-levels")
        return None

    (
        backend_post_gamma,
        backend_brightness,
        backend_contrast,
        backend_saturation,
    ) = _resolve_default_postprocess(
        enable_luminance,
        enable_opencv,
        enable_hdr_plus,
        luminance_tmo,
    )
    if not post_gamma_set:
        post_gamma = backend_post_gamma
    if not brightness_set:
        brightness = backend_brightness
    if not contrast_set:
        contrast = backend_contrast
    if not saturation_set:
        saturation = backend_saturation
    auto_brightness_options = _parse_auto_brightness_options(auto_brightness_raw_values)
    if auto_brightness_options is None:
        return None
    auto_levels_options = _parse_auto_levels_options(auto_levels_raw_values)
    if auto_levels_options is None:
        return None
    auto_adjust_options = _parse_auto_adjust_options(auto_adjust_raw_values)
    if auto_adjust_options is None:
        return None

    return (
        Path(positional[0]),
        Path(positional[1]),
        ev_value,
        auto_ev_enabled,
        gamma_value,
        PostprocessOptions(
            post_gamma=post_gamma,
            brightness=brightness,
            contrast=contrast,
            saturation=saturation,
            jpg_compression=jpg_compression,
            auto_brightness_enabled=auto_brightness_enabled,
            auto_brightness_options=auto_brightness_options,
            auto_levels_enabled=auto_levels_enabled,
            auto_levels_options=auto_levels_options,
            auto_adjust_mode=auto_adjust_mode,
            auto_adjust_options=auto_adjust_options,
        ),
        enable_luminance,
        enable_opencv,
        LuminanceOptions(
            hdr_model=luminance_hdr_model,
            hdr_weight=luminance_hdr_weight,
            hdr_response_curve=luminance_hdr_response_curve,
            tmo=luminance_tmo,
            tmo_extra_args=tuple(luminance_tmo_extra_args),
        ),
        OpenCvMergeOptions(
            debevec_white_point_percentile=DEFAULT_OPENCV_DEBEVEC_WHITE_POINT_PERCENTILE
        ),
        enable_hdr_plus,
        ev_zero,
        auto_zero_enabled,
        auto_zero_pct,
        auto_ev_pct,
    )


def _load_image_dependencies():
    """@brief Load optional Python dependencies required by `dng2jpg`.

    @details Imports `rawpy` for RAW decoding and `imageio` for image IO using
    `imageio.v3` when available with fallback to top-level `imageio` module.
    @return {tuple[ModuleType, ModuleType, ModuleType]|None} `(rawpy_module, imageio_module, pil_image_module)` on success; `None` on missing dependency.
    @satisfies REQ-059, REQ-066, REQ-074
    """

    try:
        import rawpy  # type: ignore
    except ModuleNotFoundError:
        print_error("Python dependency missing: rawpy")
        print_error("Install dependencies with: uv pip install rawpy imageio pillow")
        return None

    try:
        import imageio.v3 as imageio  # type: ignore
    except ModuleNotFoundError:
        try:
            import imageio  # type: ignore
        except ModuleNotFoundError:
            print_error("Python dependency missing: imageio")
            print_error(
                "Install dependencies with: uv pip install rawpy imageio pillow"
            )
            return None

    try:
        from PIL import Image as pil_image  # type: ignore
    except ModuleNotFoundError:
        print_error("Python dependency missing: pillow")
        print_error("Install dependencies with: uv pip install rawpy imageio pillow")
        return None

    return rawpy, imageio, pil_image


def _parse_exif_datetime_to_timestamp(datetime_raw):
    """@brief Parse one EXIF datetime token into POSIX timestamp.

    @details Normalizes scalar EXIF datetime input (`str` or `bytes`), trims
    optional null-terminated EXIF payload suffix, and parses strict EXIF format
    `YYYY:MM:DD HH:MM:SS` to generate filesystem timestamp.
    @param datetime_raw {str|bytes|object} EXIF datetime scalar.
    @return {float|None} Parsed POSIX timestamp; `None` when value is missing or invalid.
    @satisfies REQ-074, REQ-077
    """

    if datetime_raw is None:
        return None
    if isinstance(datetime_raw, (list, tuple)):
        if not datetime_raw:
            return None
        datetime_raw = datetime_raw[0]
    if isinstance(datetime_raw, bytes):
        datetime_text = datetime_raw.decode("utf-8", errors="ignore").strip()
    else:
        datetime_text = str(datetime_raw).strip()
    datetime_text = datetime_text.rstrip("\x00")
    if not datetime_text:
        return None
    try:
        parsed_datetime = datetime.strptime(datetime_text, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
    return parsed_datetime.timestamp()


def _extract_dng_exif_payload_and_timestamp(pil_image_module, input_dng):
    """@brief Extract DNG EXIF payload bytes, preferred datetime timestamp, and source orientation.

    @details Opens input DNG via Pillow, suppresses known non-actionable
    `PIL.TiffImagePlugin` metadata warning for malformed TIFF tag `33723`, reads
    EXIF mapping without orientation mutation, serializes payload for JPEG save
    while source image handle is still open,
    resolves source orientation from EXIF tag `274`, and resolves filesystem timestamp priority:
    `DateTimeOriginal`(36867) > `DateTimeDigitized`(36868) > `DateTime`(306).
    @param pil_image_module {ModuleType} Imported Pillow Image module.
    @param input_dng {Path} Source DNG path.
    @return {tuple[bytes|None, float|None, int]} `(exif_payload, exif_timestamp, source_orientation)` with orientation defaulting to `1`.
    @satisfies REQ-066, REQ-074, REQ-077
    """

    if not hasattr(pil_image_module, "open"):
        return (None, None, 1)
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r".*tag 33723 had too many entries.*",
                category=UserWarning,
            )
            with pil_image_module.open(str(input_dng)) as source_image:
                if not hasattr(source_image, "getexif"):
                    return (None, None, 1)
                exif_data = source_image.getexif()
                if exif_data is None:
                    return (None, None, 1)
                exif_payload = (
                    exif_data.tobytes() if hasattr(exif_data, "tobytes") else None
                )
                source_orientation = 1
                orientation_raw = exif_data.get(_EXIF_TAG_ORIENTATION)
                if orientation_raw is not None:
                    try:
                        orientation_value = int(orientation_raw)
                        if orientation_value in _EXIF_VALID_ORIENTATIONS:
                            source_orientation = orientation_value
                    except (TypeError, ValueError):
                        source_orientation = 1
                exif_timestamp = None
                for exif_tag in (
                    _EXIF_TAG_DATETIME_ORIGINAL,
                    _EXIF_TAG_DATETIME_DIGITIZED,
                    _EXIF_TAG_DATETIME,
                ):
                    exif_timestamp = _parse_exif_datetime_to_timestamp(
                        exif_data.get(exif_tag)
                    )
                    if exif_timestamp is not None:
                        break
                return (exif_payload, exif_timestamp, source_orientation)
    except (OSError, ValueError, TypeError, AttributeError):
        return (None, None, 1)


def _resolve_thumbnail_transpose_map(pil_image_module):
    """@brief Build deterministic EXIF-orientation-to-transpose mapping.

    @details Resolves Pillow transpose constants from modern `Image.Transpose`
    namespace with fallback to legacy module-level constants.
    @param pil_image_module {ModuleType} Imported Pillow Image module.
    @return {dict[int, int]} Orientation-to-transpose mapping for values `2..8`.
    @satisfies REQ-077, REQ-078
    """

    transpose_enum = getattr(pil_image_module, "Transpose", None)
    if transpose_enum is not None:
        return {
            2: transpose_enum.FLIP_LEFT_RIGHT,
            3: transpose_enum.ROTATE_180,
            4: transpose_enum.FLIP_TOP_BOTTOM,
            5: transpose_enum.TRANSPOSE,
            6: transpose_enum.ROTATE_270,
            7: transpose_enum.TRANSVERSE,
            8: transpose_enum.ROTATE_90,
        }
    return {
        2: getattr(pil_image_module, "FLIP_LEFT_RIGHT"),
        3: getattr(pil_image_module, "ROTATE_180"),
        4: getattr(pil_image_module, "FLIP_TOP_BOTTOM"),
        5: getattr(pil_image_module, "TRANSPOSE"),
        6: getattr(pil_image_module, "ROTATE_270"),
        7: getattr(pil_image_module, "TRANSVERSE"),
        8: getattr(pil_image_module, "ROTATE_90"),
    }


def _apply_orientation_transform(pil_image_module, pil_image, source_orientation):
    """@brief Apply EXIF orientation transform to one image copy.

    @details Produces display-oriented pixels from source-oriented input while
    preserving the original image object and preserving orientation invariants in
    the main processing pipeline.
    @param pil_image_module {ModuleType} Imported Pillow Image module.
    @param pil_image {object} Pillow image-like object.
    @param source_orientation {int} EXIF orientation value in range `1..8`.
    @return {object} Transformed Pillow image object.
    @satisfies REQ-077, REQ-078
    """

    transformed = pil_image.copy()
    if source_orientation not in _EXIF_VALID_ORIENTATIONS:
        return transformed
    transpose_map = _resolve_thumbnail_transpose_map(pil_image_module)
    transpose_method = transpose_map.get(source_orientation)
    if transpose_method is None:
        return transformed
    return transformed.transpose(transpose_method)


def _build_oriented_thumbnail_jpeg_bytes(
    pil_image_module, output_jpg, source_orientation
):
    """@brief Build refreshed JPEG thumbnail bytes from final JPG output.

    @details Opens final JPG pixels, applies source-orientation-aware transform,
    scales to bounded thumbnail size, and serializes deterministic JPEG thumbnail
    payload for EXIF embedding.
    @param pil_image_module {ModuleType} Imported Pillow Image module.
    @param output_jpg {Path} Final JPG path.
    @param source_orientation {int} EXIF orientation value in range `1..8`.
    @return {bytes} Serialized JPEG thumbnail payload.
    @exception OSError Raised when final JPG cannot be read.
    @satisfies REQ-077, REQ-078
    """

    with pil_image_module.open(str(output_jpg)) as output_image:
        thumbnail_image = _apply_orientation_transform(
            pil_image_module=pil_image_module,
            pil_image=output_image,
            source_orientation=source_orientation,
        )
        if getattr(thumbnail_image, "mode", "") not in ("RGB", "L"):
            thumbnail_image = thumbnail_image.convert("RGB")
        thumbnail_image.thumbnail(_THUMBNAIL_MAX_SIZE)
        buffer = BytesIO()
        thumbnail_image.save(buffer, format="JPEG", quality=85, optimize=True)
        return buffer.getvalue()


def _coerce_exif_int_like_value(raw_value):
    """@brief Coerce integer-like EXIF scalar values to Python integers.

    @details Converts scalar EXIF values represented as `int`, integer-valued
    `float`, ASCII-digit `str`, or ASCII-digit `bytes` (including trailing
    null-terminated variants) into deterministic Python `int`; returns `None`
    when conversion is not safe.
    @param raw_value {object} Candidate EXIF scalar value.
    @return {int|None} Coerced integer value or `None` when not coercible.
    @satisfies REQ-066, REQ-077, REQ-078
    """

    if isinstance(raw_value, bool):
        return None
    if isinstance(raw_value, int):
        return raw_value
    if isinstance(raw_value, float):
        if raw_value.is_integer():
            return int(raw_value)
        return None
    text_value = None
    if isinstance(raw_value, bytes):
        try:
            text_value = raw_value.decode("ascii").strip()
        except UnicodeDecodeError:
            return None
    elif isinstance(raw_value, str):
        text_value = raw_value.strip()
    if text_value is None or not text_value:
        return None
    text_value = text_value.rstrip("\x00")
    if not text_value:
        return None
    sign = text_value[0]
    digits = text_value[1:] if sign in ("+", "-") else text_value
    if not digits.isdigit():
        return None
    try:
        return int(text_value)
    except ValueError:
        return None


def _normalize_ifd_integer_like_values_for_piexif_dump(piexif_module, exif_dict):
    """@brief Normalize integer-like IFD values before `piexif.dump`.

    @details Traverses EXIF IFD mappings (`0th`, `Exif`, `GPS`, `Interop`,
    `1st`) and coerces integer-like values that can trigger `piexif.dump`
    packing failures when represented as strings or other non-int scalars.
    Tuple/list values are normalized only when all items are integer-like.
    For integer sequence tag types, nested two-item pairs are flattened to a
    single integer sequence for `piexif.dump` compatibility.
    Scalar conversion is additionally constrained by `piexif.TAGS` integer
    field types when tag metadata is available.
    @param piexif_module {ModuleType} Imported piexif module.
    @param exif_dict {dict[str, object]} EXIF dictionary loaded via piexif.
    @return {None} Mutates `exif_dict` in place.
    @satisfies REQ-066, REQ-077, REQ-078
    """

    integer_type_ids = {1, 3, 4, 6, 8, 9}
    integer_type_ranges = {
        1: (0, 255),
        3: (0, 65535),
        4: (0, 4294967295),
        6: (-128, 127),
        8: (-32768, 32767),
        9: (-2147483648, 2147483647),
    }
    tags_table = getattr(piexif_module, "TAGS", {})
    for ifd_name in ("0th", "Exif", "GPS", "Interop", "1st"):
        ifd_mapping = exif_dict.get(ifd_name)
        if not isinstance(ifd_mapping, dict):
            continue
        ifd_tag_definitions = (
            tags_table.get(ifd_name, {}) if isinstance(tags_table, dict) else {}
        )
        for tag_id, raw_value in list(ifd_mapping.items()):
            normalized_value = raw_value
            if isinstance(raw_value, tuple):
                normalized_items = []
                for item in raw_value:
                    coerced_item = _coerce_exif_int_like_value(item)
                    if coerced_item is None:
                        normalized_items = []
                        break
                    normalized_items.append(coerced_item)
                if normalized_items:
                    normalized_value = tuple(normalized_items)
            elif isinstance(raw_value, list):
                normalized_items = []
                for item in raw_value:
                    coerced_item = _coerce_exif_int_like_value(item)
                    if coerced_item is None:
                        normalized_items = []
                        break
                    normalized_items.append(coerced_item)
                if normalized_items:
                    normalized_value = normalized_items
            else:
                tag_metadata = (
                    ifd_tag_definitions.get(tag_id)
                    if isinstance(ifd_tag_definitions, dict)
                    else None
                )
                tag_type = (
                    tag_metadata.get("type") if isinstance(tag_metadata, dict) else None
                )
                if tag_type in integer_type_ids:
                    coerced_scalar = _coerce_exif_int_like_value(raw_value)
                    if coerced_scalar is not None:
                        normalized_value = coerced_scalar

            tag_metadata = (
                ifd_tag_definitions.get(tag_id)
                if isinstance(ifd_tag_definitions, dict)
                else None
            )
            tag_type = (
                tag_metadata.get("type") if isinstance(tag_metadata, dict) else None
            )
            if tag_type in integer_type_ids and isinstance(
                normalized_value, (tuple, list)
            ):
                flattened_items = []
                flattenable = True
                for item in normalized_value:
                    if isinstance(item, (tuple, list)):
                        nested_values = []
                        for nested_item in item:
                            coerced_nested_item = _coerce_exif_int_like_value(
                                nested_item
                            )
                            if coerced_nested_item is None:
                                flattenable = False
                                break
                            nested_values.append(coerced_nested_item)
                        if not flattenable:
                            break
                        flattened_items.extend(nested_values)
                        continue
                    coerced_item = _coerce_exif_int_like_value(item)
                    if coerced_item is None:
                        flattenable = False
                        break
                    flattened_items.append(coerced_item)
                if flattenable and flattened_items:
                    normalized_value = (
                        tuple(flattened_items)
                        if isinstance(normalized_value, tuple)
                        else flattened_items
                    )
            if tag_type in integer_type_ranges:
                min_allowed, max_allowed = integer_type_ranges[tag_type]
                if isinstance(normalized_value, (tuple, list)):
                    if any(
                        not isinstance(item, int)
                        or item < min_allowed
                        or item > max_allowed
                        for item in normalized_value
                    ):
                        ifd_mapping.pop(tag_id, None)
                        continue
                elif isinstance(normalized_value, int):
                    if normalized_value < min_allowed or normalized_value > max_allowed:
                        ifd_mapping.pop(tag_id, None)
                        continue
            if tag_type == 7 and isinstance(normalized_value, tuple):
                if all(
                    isinstance(item, int) and 0 <= item <= 255
                    for item in normalized_value
                ):
                    normalized_value = bytes(normalized_value)
            if normalized_value is not raw_value:
                ifd_mapping[tag_id] = normalized_value


def _refresh_output_jpg_exif_thumbnail_after_save(
    pil_image_module,
    piexif_module,
    output_jpg,
    source_exif_payload,
    source_orientation,
):
    """@brief Refresh output JPG EXIF thumbnail while preserving source orientation.

    @details Loads source EXIF payload, regenerates thumbnail from final JPG
    pixels with orientation-aware transform, preserves source orientation in main
    EXIF IFD, sets thumbnail orientation to identity, and re-inserts updated EXIF
    payload into output JPG.
    @param pil_image_module {ModuleType} Imported Pillow Image module.
    @param piexif_module {ModuleType} Imported piexif module.
    @param output_jpg {Path} Final JPG path.
    @param source_exif_payload {bytes} Serialized EXIF payload from source DNG.
    @param source_orientation {int} Source EXIF orientation value in range `1..8`.
    @return {None} Side effects only.
    @exception RuntimeError Raised when EXIF thumbnail refresh fails.
    @satisfies REQ-066, REQ-077, REQ-078
    """

    if source_exif_payload is None:
        return
    try:
        exif_dict = piexif_module.load(source_exif_payload)
        for ifd_name in ("0th", "Exif", "GPS", "Interop", "1st"):
            if ifd_name not in exif_dict or exif_dict[ifd_name] is None:
                exif_dict[ifd_name] = {}
        thumbnail_payload = _build_oriented_thumbnail_jpeg_bytes(
            pil_image_module=pil_image_module,
            output_jpg=output_jpg,
            source_orientation=source_orientation,
        )
        orientation_tag = piexif_module.ImageIFD.Orientation
        orientation_value = (
            source_orientation if source_orientation in _EXIF_VALID_ORIENTATIONS else 1
        )
        exif_dict["0th"][orientation_tag] = orientation_value
        exif_dict["1st"][orientation_tag] = 1
        exif_dict["thumbnail"] = thumbnail_payload
        _normalize_ifd_integer_like_values_for_piexif_dump(
            piexif_module=piexif_module,
            exif_dict=exif_dict,
        )
        exif_bytes = piexif_module.dump(exif_dict)
        piexif_module.insert(exif_bytes, str(output_jpg))
    except (ValueError, TypeError, KeyError, OSError, AttributeError) as error:
        raise RuntimeError(
            f"Failed to refresh output JPG EXIF thumbnail: {error}"
        ) from error


def _set_output_file_timestamps(output_jpg, exif_timestamp):
    """@brief Set output JPG atime and mtime from EXIF timestamp.

    @details Applies EXIF-derived POSIX timestamp to both access and
    modification times using `os.utime`.
    @param output_jpg {Path} Output JPG path.
    @param exif_timestamp {float} Source EXIF-derived POSIX timestamp.
    @return {None} Side effects only.
    @exception OSError Raised when filesystem metadata update fails.
    @satisfies REQ-074, REQ-077
    """

    os.utime(output_jpg, (exif_timestamp, exif_timestamp))


def _sync_output_file_timestamps_from_exif(output_jpg, exif_timestamp):
    """@brief Synchronize output JPG atime/mtime from optional EXIF timestamp.

    @details Provides one dedicated call site for filesystem timestamp sync and
    applies update only when EXIF datetime parsing produced a valid POSIX value.
    @param output_jpg {Path} Output JPG path.
    @param exif_timestamp {float|None} Source EXIF-derived POSIX timestamp.
    @return {None} Side effects only.
    @exception OSError Raised when filesystem metadata update fails.
    @satisfies REQ-074, REQ-077
    """

    if exif_timestamp is None:
        return
    _set_output_file_timestamps(output_jpg=output_jpg, exif_timestamp=exif_timestamp)


def _build_exposure_multipliers(ev_value, ev_zero=0.0):
    """@brief Compute bracketing brightness multipliers from EV delta and center.

    @details Produces exactly three multipliers mapped to exposure stops
    `[ev_zero-ev, ev_zero, ev_zero+ev]` as powers of two for RAW postprocess
    brightness control.
    @param ev_value {float} Exposure bracket EV delta.
    @param ev_zero {float} Central bracket EV value.
    @return {tuple[float, float, float]} Multipliers in order `(under, base, over)`.
    @satisfies REQ-057, REQ-077, REQ-079, REQ-080, REQ-092, REQ-093, REQ-095
    """

    return (
        2 ** (ev_zero - ev_value),
        2**ev_zero,
        2 ** (ev_zero + ev_value),
    )


def _write_bracket_images(
    raw_handle, imageio_module, multipliers, gamma_value, temp_dir
):
    """@brief Materialize three bracket TIFF files from one RAW handle.

    @details Invokes `raw.postprocess` with `output_bps=16`,
    `use_camera_wb=True`, `no_auto_bright=True`, explicit `user_flip=0` to
    disable implicit RAW orientation mutation, and configurable gamma pair for
    deterministic HDR-oriented bracket extraction before merge.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @param imageio_module {ModuleType} Imported imageio module with `imwrite`.
    @param multipliers {tuple[float, float, float]} Ordered exposure multipliers.
    @param gamma_value {tuple[float, float]} Gamma pair forwarded to RAW postprocess.
    @param temp_dir {Path} Directory for intermediate TIFF artifacts.
    @return {list[Path]} Ordered temporary TIFF file paths.
    @satisfies REQ-057, REQ-077, REQ-079, REQ-080
    """

    labels = ("ev_minus", "ev_zero", "ev_plus")
    bracket_paths = []

    for label, multiplier in zip(labels, multipliers):
        temp_path = temp_dir / f"{label}.tif"
        print_info(f"Extracting bracket {label}: brightness={multiplier:.4f}x")
        rgb_data = raw_handle.postprocess(
            bright=multiplier,
            output_bps=16,
            use_camera_wb=True,
            no_auto_bright=True,
            gamma=gamma_value,
            user_flip=0,
        )
        imageio_module.imwrite(str(temp_path), rgb_data)
        bracket_paths.append(temp_path)

    return bracket_paths


def _order_bracket_paths(bracket_paths):
    """@brief Validate and reorder bracket TIFF paths for deterministic backend argv.

    @details Enforces exact exposure order `<ev_minus.tif> <ev_zero.tif> <ev_plus.tif>`
    required by backend command generation and raises on missing labels.
    @param bracket_paths {list[Path]} Temporary bracket TIFF paths generated from RAW.
    @return {list[Path]} Reordered bracket path list in deterministic exposure order.
    @exception ValueError Raised when any expected bracket label is missing.
    @satisfies REQ-062, REQ-112
    """

    expected = ("ev_minus.tif", "ev_zero.tif", "ev_plus.tif")
    by_name = {path.name: path for path in bracket_paths}
    ordered = []
    missing = []
    for name in expected:
        path = by_name.get(name)
        if path is None:
            missing.append(name)
            continue
        ordered.append(path)
    if missing:
        raise ValueError(f"Missing expected bracket files: {', '.join(missing)}")
    return ordered


def _order_hdr_plus_reference_paths(bracket_paths):
    """@brief Reorder bracket TIFF paths into HDR+ reference-first frame order.

    @details Converts canonical bracket order `(ev_minus, ev_zero, ev_plus)` to
    source-algorithm frame order `(ev_zero, ev_minus, ev_plus)` so the central
    bracket acts as temporal reference frame `n=0`, matching HDR+ temporal
    merge semantics while preserving existing bracket export filenames.
    @param bracket_paths {list[Path]} Temporary bracket TIFF paths generated from RAW.
    @return {list[Path]} Ordered bracket paths in HDR+ reference-first order.
    @satisfies REQ-112
    """

    ordered_paths = _order_bracket_paths(bracket_paths)
    return [ordered_paths[1], ordered_paths[0], ordered_paths[2]]


def _run_enfuse(bracket_paths, merged_tiff):
    """@brief Merge bracket TIFF files into one HDR TIFF via `enfuse`.

    @details Builds deterministic enfuse argv with LZW compression and executes
    subprocess in checked mode to propagate command failures.
    @param bracket_paths {list[Path]} Ordered intermediate exposure TIFF paths.
    @param merged_tiff {Path} Output merged TIFF target path.
    @return {None} Side effects only.
    @exception subprocess.CalledProcessError Raised when `enfuse` returns non-zero exit status.
    @satisfies REQ-058, REQ-077
    """

    command = [
        "enfuse",
        f"--output={merged_tiff}",
        "--compression=lzw",
        *[str(path) for path in bracket_paths],
    ]
    subprocess.run(command, check=True)


def _run_luminance_hdr_cli(
    bracket_paths, output_hdr_tiff, ev_value, ev_zero, luminance_options
):
    """@brief Merge bracket TIFF files into one HDR TIFF via `luminance-hdr-cli`.

    @details Builds deterministic luminance-hdr-cli argv using EV sequence
    centered around zero-reference (`-ev_value,0,+ev_value`) even when extraction
    uses non-zero `ev_zero`,
    HDR model controls, tone-mapper controls, mandatory `--ldrTiff 16b`,
    optional explicit `--tmo*` passthrough arguments, and ordered exposure
    inputs (`ev_minus`, `ev_zero`, `ev_plus`), then writes to TIFF output path
    used by shared postprocess conversion. Executes subprocess in output-TIFF
    parent directory to isolate backend-generated sidecar artifacts (e.g. `.pp3`)
    inside command temporary workspace lifecycle.
    @param bracket_paths {list[Path]} Ordered intermediate exposure TIFF paths.
    @param output_hdr_tiff {Path} Output HDR TIFF target path.
    @param ev_value {float} EV bracket delta used to generate exposure files.
    @param ev_zero {float} Central EV used to generate exposure files.
    @param luminance_options {LuminanceOptions} Luminance backend command controls.
    @return {None} Side effects only.
    @exception subprocess.CalledProcessError Raised when `luminance-hdr-cli` returns non-zero exit status.
    @satisfies REQ-060, REQ-061, REQ-062, REQ-067, REQ-068, REQ-077, REQ-080, REQ-095
    """

    ordered_paths = _order_bracket_paths(bracket_paths)
    command = [
        "luminance-hdr-cli",
        "-e",
        f"{-ev_value:g},0,{ev_value:g}",
        "--hdrModel",
        luminance_options.hdr_model,
        "--hdrWeight",
        luminance_options.hdr_weight,
        "--hdrResponseCurve",
        luminance_options.hdr_response_curve,
        "--tmo",
        luminance_options.tmo,
        "--ldrTiff",
        "16b",
        *luminance_options.tmo_extra_args,
        "-o",
        str(output_hdr_tiff),
        *[str(path) for path in ordered_paths],
    ]
    original_working_directory = Path.cwd()
    backend_working_directory = output_hdr_tiff.parent
    try:
        os.chdir(backend_working_directory)
        subprocess.run(command, check=True)
    finally:
        os.chdir(original_working_directory)


def _build_ev_times_from_ev_zero_and_delta(ev_zero, ev_delta):
    """@brief Build deterministic exposure times array from EV center and EV delta.

    @details Computes exposure times in stop space as
    `[2^(ev_zero-ev_delta), 2^ev_zero, 2^(ev_zero+ev_delta)]` mapped to
    bracket order `(ev_minus, ev_zero, ev_plus)` and returns `float32` vector
    suitable for OpenCV `MergeDebevec.process`.
    @param ev_zero {float} Central EV used during bracket extraction.
    @param ev_delta {float} EV bracket delta used during bracket extraction.
    @return {object} `numpy.float32` vector with length `3`.
    @exception RuntimeError Raised when numpy dependency is unavailable.
    @satisfies REQ-108, REQ-109
    """

    try:
        import numpy as np_module  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing required dependency: numpy") from exc
    return np_module.array(
        [
            2 ** (ev_zero - ev_delta),
            2**ev_zero,
            2 ** (ev_zero + ev_delta),
        ],
        dtype=np_module.float32,
    )


def _normalize_debevec_hdr_to_unit_range(np_module, hdr_rgb_float32, white_point_percentile):
    """@brief Normalize Debevec HDR tensor to unit range with robust white point.

    @details Computes BT.709 luminance, extracts percentile-derived `Lwhite`,
    scales RGB tensor by `1/Lwhite`, and clamps into `[0,1]` to produce
    deterministic blend-ready Debevec contribution.
    @param np_module {ModuleType} Imported numpy module.
    @param hdr_rgb_float32 {object} Debevec output RGB tensor in float domain.
    @param white_point_percentile {float} White-point percentile in `(0,100)`.
    @return {object} Debevec RGB float tensor clamped to `[0,1]`.
    @satisfies REQ-109, REQ-110
    """

    hdr_rgb_float64 = np_module.array(hdr_rgb_float32, dtype=np_module.float64)
    luminance = (
        0.2126 * hdr_rgb_float64[..., 0]
        + 0.7152 * hdr_rgb_float64[..., 1]
        + 0.0722 * hdr_rgb_float64[..., 2]
    )
    positive_mask = luminance > 0.0
    if np_module.any(positive_mask):
        positive_luminance = luminance[positive_mask]
        white_point = float(
            np_module.percentile(positive_luminance, float(white_point_percentile))
        )
        if white_point <= 0.0:
            white_point = float(np_module.max(positive_luminance))
        if white_point <= 0.0:
            white_point = 1.0
    else:
        white_point = 1.0
    normalized = hdr_rgb_float64 / white_point
    return np_module.clip(normalized, 0.0, 1.0).astype(np_module.float32)


def _run_opencv_hdr_merge(
    bracket_paths,
    output_hdr_tiff,
    ev_value,
    ev_zero,
    opencv_merge_options,
    auto_adjust_opencv_dependencies,
):
    """@brief Merge bracket TIFF files into one HDR TIFF via OpenCV Mertens+Debevec.

    @details Loads deterministic bracket order, preserves one uint16 RGB tensor
    list for Debevec radiance merge, derives one normalized float32 RGB tensor
    list in `[0,1]` for Mertens exposure fusion, executes both merges with the
    EV-derived exposure-time vector, normalizes Debevec HDR with percentile
    robust white-point luminance scaling, averages both outputs in float domain,
    then writes one RGB uint16 TIFF.
    @param bracket_paths {list[Path]} Ordered intermediate exposure TIFF paths.
    @param output_hdr_tiff {Path} Output HDR TIFF target path.
    @param ev_value {float} EV bracket delta used to generate exposure files.
    @param ev_zero {float} Central EV used to generate exposure files.
    @param opencv_merge_options {OpenCvMergeOptions} OpenCV merge backend controls.
    @param auto_adjust_opencv_dependencies {tuple[ModuleType, ModuleType]|None} Optional `(cv2, numpy)` dependency tuple.
    @return {None} Side effects only.
    @exception RuntimeError Raised when OpenCV/numpy dependencies are missing or bracket payloads are invalid.
    @satisfies REQ-077, REQ-107, REQ-108, REQ-109, REQ-110
    """

    if auto_adjust_opencv_dependencies is not None:
        cv2_module, np_module = auto_adjust_opencv_dependencies
    else:
        resolved_dependencies = _resolve_auto_adjust_opencv_dependencies()
        if resolved_dependencies is None:
            raise RuntimeError("Missing required dependencies: opencv-python and numpy")
        cv2_module, np_module = resolved_dependencies

    ordered_paths = _order_bracket_paths(bracket_paths)
    exposures_uint16 = []
    exposures_unit_float32 = []
    for path in ordered_paths:
        image_bgr = cv2_module.imread(str(path), cv2_module.IMREAD_UNCHANGED)
        if image_bgr is None:
            raise RuntimeError(f"OpenCV failed to read bracket image: {path}")
        if len(image_bgr.shape) != 3 or image_bgr.shape[2] != 3:
            raise RuntimeError(f"OpenCV bracket image must be RGB 3-channel: {path}")
        dtype_name = str(getattr(image_bgr, "dtype", ""))
        if dtype_name == "uint8":
            image_bgr = (image_bgr.astype(np_module.uint16) * 257).astype(np_module.uint16)
        elif dtype_name != "uint16":
            raise RuntimeError(f"OpenCV bracket image must be uint16 or uint8: {path}")
        image_rgb_uint16 = cv2_module.cvtColor(image_bgr, cv2_module.COLOR_BGR2RGB)
        image_rgb_uint16 = image_rgb_uint16.astype(np_module.uint16)
        exposures_uint16.append(image_rgb_uint16)
        exposures_unit_float32.append(
            (image_rgb_uint16.astype(np_module.float32) / 65535.0).astype(np_module.float32)
        )

    exposure_times = _build_ev_times_from_ev_zero_and_delta(ev_zero=ev_zero, ev_delta=ev_value)
    merge_mertens = cv2_module.createMergeMertens()
    fusion_rgb_float32 = merge_mertens.process(exposures_unit_float32)
    merge_debevec = cv2_module.createMergeDebevec()
    debevec_hdr_float32 = merge_debevec.process(exposures_uint16, times=exposure_times)
    debevec_rgb_unit = _normalize_debevec_hdr_to_unit_range(
        np_module=np_module,
        hdr_rgb_float32=debevec_hdr_float32,
        white_point_percentile=opencv_merge_options.debevec_white_point_percentile,
    )
    fusion_rgb_float32 = np_module.clip(
        np_module.array(fusion_rgb_float32, dtype=np_module.float32),
        0.0,
        1.0,
    )
    blended_rgb_float32 = (fusion_rgb_float32 + debevec_rgb_unit) * 0.5
    blended_rgb_u16 = np_module.clip(
        np_module.round(blended_rgb_float32 * 65535.0),
        0.0,
        65535.0,
    ).astype(np_module.uint16)
    output_bgr_u16 = cv2_module.cvtColor(blended_rgb_u16, cv2_module.COLOR_RGB2BGR)
    if not cv2_module.imwrite(str(output_hdr_tiff), output_bgr_u16):
        raise RuntimeError(f"OpenCV failed to write merged HDR TIFF: {output_hdr_tiff}")


def _hdrplus_box_down2_uint16(np_module, frames_uint16):
    """@brief Downsample HDR+ scalar frames with 2x2 box averaging.

    @details Ports `box_down2` from `util.cpp` by reflect-padding odd image
    sizes to even extents, summing each 2x2 region in `uint32`, and dividing by
    `4` once to preserve integer averaging semantics.
    @param np_module {ModuleType} Imported numpy module.
    @param frames_uint16 {object} Scalar frame tensor with shape `(N,H,W)`.
    @return {object} Downsampled `uint16` tensor with shape `(N,ceil(H/2),ceil(W/2))`.
    @satisfies REQ-112, REQ-113
    """

    pad_bottom = int(frames_uint16.shape[1] % 2)
    pad_right = int(frames_uint16.shape[2] % 2)
    padded_frames = np_module.pad(
        frames_uint16,
        ((0, 0), (0, pad_bottom), (0, pad_right)),
        mode="reflect",
    )
    summed = (
        padded_frames[:, 0::2, 0::2].astype(np_module.uint32)
        + padded_frames[:, 0::2, 1::2].astype(np_module.uint32)
        + padded_frames[:, 1::2, 0::2].astype(np_module.uint32)
        + padded_frames[:, 1::2, 1::2].astype(np_module.uint32)
    )
    return (summed // 4).astype(np_module.uint16)


def _hdrplus_luminance_proxy_uint16(np_module, frames_rgb_uint16):
    """@brief Convert RGB bracket tensor into scalar HDR+ merge proxy.

    @details Adapts single-channel Bayer merge input to aligned RGB bracket TIFF
    inputs by computing deterministic per-pixel arithmetic RGB mean, rounding to
    `uint16`, and preserving source 16-bit scale for subsequent `box_down2` and
    tile L1 distance steps.
    @param np_module {ModuleType} Imported numpy module.
    @param frames_rgb_uint16 {object} RGB frame tensor with shape `(N,H,W,3)`.
    @return {object} Scalar `uint16` tensor with shape `(N,H,W)`.
    @satisfies REQ-112, REQ-115
    """

    rgb_float = frames_rgb_uint16.astype(np_module.float64)
    luminance_proxy = np_module.round(np_module.mean(rgb_float, axis=-1))
    return np_module.clip(luminance_proxy, 0.0, 65535.0).astype(np_module.uint16)


def _hdrplus_extract_overlapping_tiles(
    np_module,
    frames_array,
    tile_size,
    tile_stride,
    pad_margin,
):
    """@brief Extract half-overlapped HDR+ tiles from padded frame tensor.

    @details Reflect-pads frame tensor, builds sliding-window views for every
    possible tile origin, then samples origins corresponding to source HDR+
    overlap geometry (`stride = tile_size / 2`) including the leading virtual
    tile at `-tile_stride`.
    @param np_module {ModuleType} Imported numpy module.
    @param frames_array {object} Frame tensor with shape `(N,H,W)` or `(N,H,W,C)`.
    @param tile_size {int} Square tile edge length.
    @param tile_stride {int} Tile stride between adjacent overlapping tiles.
    @param pad_margin {int} Reflect padding added on each image edge.
    @return {object} Tile tensor with shape `(N,Ty,Tx,tile_size,tile_size[,C])`.
    @satisfies REQ-112, REQ-113, REQ-114
    """

    from numpy.lib.stride_tricks import sliding_window_view  # type: ignore

    tile_count_y = int(math.ceil(frames_array.shape[1] / float(tile_stride)))
    tile_count_x = int(math.ceil(frames_array.shape[2] / float(tile_stride)))
    start_positions_y = pad_margin - tile_stride + (
        np_module.arange(tile_count_y + 1, dtype=np_module.int32) * tile_stride
    )
    start_positions_x = pad_margin - tile_stride + (
        np_module.arange(tile_count_x + 1, dtype=np_module.int32) * tile_stride
    )
    if frames_array.ndim == 3:
        padded_frames = np_module.pad(
            frames_array,
            ((0, 0), (pad_margin, pad_margin), (pad_margin, pad_margin)),
            mode="reflect",
        )
        windows = sliding_window_view(
            padded_frames,
            window_shape=(tile_size, tile_size),
            axis=(1, 2),
        )
        return windows[:, start_positions_y[:, None], start_positions_x[None, :], ...]
    padded_frames = np_module.pad(
        frames_array,
        ((0, 0), (pad_margin, pad_margin), (pad_margin, pad_margin), (0, 0)),
        mode="reflect",
    )
    windows = sliding_window_view(
        padded_frames,
        window_shape=(tile_size, tile_size),
        axis=(1, 2),
    )
    windows = np_module.moveaxis(windows, 3, -1)
    return windows[:, start_positions_y[:, None], start_positions_x[None, :], ...]


def _hdrplus_compute_temporal_weights(np_module, layer_tiles):
    """@brief Compute HDR+ temporal tile weights against reference frame.

    @details Ports `merge_temporal` weight equations from `merge.cpp` with
    alignment offsets fixed to zero: computes integer tile L1 distance over each
    16x16 downsampled tile, derives `norm_dist = max(1, dist/8 - 10/8)`,
    applies hard cutoff when `norm_dist > 290`, and returns inverse-distance
    weights for alternate frames only.
    @param np_module {ModuleType} Imported numpy module.
    @param layer_tiles {object} Downsampled scalar tile tensor with shape `(N,Ty,Tx,16,16)`.
    @return {tuple[object, object]} `(weights, total_weight)` where `weights`
      has shape `(N-1,Ty,Tx)` and `total_weight` has shape `(Ty,Tx)`.
    @satisfies REQ-112, REQ-113
    """

    if layer_tiles.shape[0] <= 1:
        total_weight = np_module.ones(layer_tiles.shape[1:3], dtype=np_module.float32)
        return (
            np_module.zeros((0,) + layer_tiles.shape[1:3], dtype=np_module.float32),
            total_weight,
        )
    reference_tiles = layer_tiles[0].astype(np_module.int32)
    alternate_tiles = layer_tiles[1:].astype(np_module.int32)
    distances = np_module.sum(
        np_module.abs(alternate_tiles - reference_tiles[None, ...]),
        axis=(-2, -1),
        dtype=np_module.int64,
    )
    distances = (distances // 256).astype(np_module.float32)
    norm_dist = np_module.maximum(
        1.0,
        (distances / HDRPLUS_TEMPORAL_FACTOR)
        - (HDRPLUS_TEMPORAL_MIN_DIST / HDRPLUS_TEMPORAL_FACTOR),
    )
    max_norm_dist = HDRPLUS_TEMPORAL_MAX_DIST - HDRPLUS_TEMPORAL_MIN_DIST
    weights = np_module.where(norm_dist > max_norm_dist, 0.0, 1.0 / norm_dist)
    weights = weights.astype(np_module.float32)
    total_weight = (
        np_module.sum(weights, axis=0, dtype=np_module.float32) + 1.0
    ).astype(np_module.float32)
    return (weights, total_weight)


def _hdrplus_merge_temporal_rgb(np_module, full_tiles_rgb, weights, total_weight):
    """@brief Merge HDR+ full-resolution tiles across temporal dimension.

    @details Ports the temporal accumulation step from `merge.cpp` with zero
    alignment offsets by normalizing the reference tile and all alternate tiles
    with shared per-tile `total_weight`, while preserving RGB `uint16` content
    in float64 accumulation until the spatial merge stage.
    @param np_module {ModuleType} Imported numpy module.
    @param full_tiles_rgb {object} RGB tile tensor with shape `(N,Ty,Tx,32,32,3)`.
    @param weights {object} Alternate-frame weight tensor with shape `(N-1,Ty,Tx)`.
    @param total_weight {object} Reference-inclusive tile total weights with shape `(Ty,Tx)`.
    @return {object} Temporally merged RGB tile tensor with shape `(Ty,Tx,32,32,3)`.
    @satisfies REQ-112, REQ-113
    """

    total_weight_expanded = total_weight[..., None, None, None].astype(np_module.float64)
    merged_tiles = full_tiles_rgb[0].astype(np_module.float64) / total_weight_expanded
    if weights.shape[0] > 0:
        merged_tiles += np_module.sum(
            full_tiles_rgb[1:].astype(np_module.float64)
            * weights[..., None, None, None].astype(np_module.float64),
            axis=0,
            dtype=np_module.float64,
        ) / total_weight_expanded
    return merged_tiles


def _hdrplus_merge_spatial_rgb(np_module, temporal_tiles, width, height):
    """@brief Blend HDR+ temporally merged tiles with raised-cosine overlap.

    @details Ports `merge_spatial` from `merge.cpp`: builds source
    raised-cosine weights over `32` samples, gathers four overlapping tiles for
    each output pixel using source index formulas derived from `tile_0`,
    `tile_1`, `idx_0`, and `idx_1`, then computes weighted RGB sum once and
    rounds/clamps to `uint16`.
    @param np_module {ModuleType} Imported numpy module.
    @param temporal_tiles {object} Temporally merged RGB tile tensor with shape `(Ty,Tx,32,32,3)`.
    @param width {int} Output image width.
    @param height {int} Output image height.
    @return {object} RGB `uint16` merged image tensor with shape `(H,W,3)`.
    @satisfies REQ-112, REQ-114
    """

    positions = np_module.arange(HDRPLUS_TILE_SIZE, dtype=np_module.float64)
    weight_1d = 0.5 - 0.5 * np_module.cos(
        (2.0 * np_module.pi * (positions + 0.5)) / HDRPLUS_TILE_SIZE
    )
    x_positions = np_module.arange(width, dtype=np_module.int32)
    y_positions = np_module.arange(height, dtype=np_module.int32)
    tile0_x = x_positions // HDRPLUS_TILE_STRIDE
    tile1_x = tile0_x + 1
    tile0_y = y_positions // HDRPLUS_TILE_STRIDE
    tile1_y = tile0_y + 1
    idx0_x = (x_positions % HDRPLUS_TILE_STRIDE) + HDRPLUS_TILE_STRIDE
    idx1_x = x_positions % HDRPLUS_TILE_STRIDE
    idx0_y = (y_positions % HDRPLUS_TILE_STRIDE) + HDRPLUS_TILE_STRIDE
    idx1_y = y_positions % HDRPLUS_TILE_STRIDE
    val_00 = temporal_tiles[
        tile0_y[:, None],
        tile0_x[None, :],
        idx0_y[:, None],
        idx0_x[None, :],
    ]
    val_10 = temporal_tiles[
        tile0_y[:, None],
        tile1_x[None, :],
        idx0_y[:, None],
        idx1_x[None, :],
    ]
    val_01 = temporal_tiles[
        tile1_y[:, None],
        tile0_x[None, :],
        idx1_y[:, None],
        idx0_x[None, :],
    ]
    val_11 = temporal_tiles[
        tile1_y[:, None],
        tile1_x[None, :],
        idx1_y[:, None],
        idx1_x[None, :],
    ]
    weight_00 = weight_1d[idx0_y][:, None] * weight_1d[idx0_x][None, :]
    weight_10 = weight_1d[idx0_y][:, None] * weight_1d[idx1_x][None, :]
    weight_01 = weight_1d[idx1_y][:, None] * weight_1d[idx0_x][None, :]
    weight_11 = weight_1d[idx1_y][:, None] * weight_1d[idx1_x][None, :]
    merged_image = (
        (weight_00[..., None] * val_00)
        + (weight_10[..., None] * val_10)
        + (weight_01[..., None] * val_01)
        + (weight_11[..., None] * val_11)
    )
    return np_module.clip(
        np_module.round(merged_image),
        0.0,
        65535.0,
    ).astype(np_module.uint16)


def _run_hdr_plus_merge(bracket_paths, output_hdr_tiff, imageio_module, np_module):
    """@brief Merge bracket TIFF files into one RGB uint16 TIFF via HDR+.

    @details Ports the source HDR+ merge pipeline from `merge.cpp` and
    `util.cpp` while intentionally omitting alignment stages per integration
    requirements: reorders bracket inputs into reference-first frame order
    `(ev_zero, ev_minus, ev_plus)`, computes scalar merge proxy from aligned RGB
    TIFFs, executes source `box_down2`, source temporal tile weighting with zero
    offsets, source temporal full-resolution tile accumulation, and source
    raised-cosine spatial blending, then writes one merged RGB `uint16` TIFF.
    @param bracket_paths {list[Path]} Temporary bracket TIFF paths generated from RAW.
    @param output_hdr_tiff {Path} Output HDR TIFF target path.
    @param imageio_module {ModuleType} Imported imageio module with `imread` and `imwrite`.
    @param np_module {ModuleType} Imported numpy module.
    @return {None} Side effects only.
    @exception RuntimeError Raised when bracket payloads are invalid.
    @satisfies REQ-077, REQ-111, REQ-112, REQ-113, REQ-114, REQ-115
    """

    ordered_paths = _order_hdr_plus_reference_paths(bracket_paths)
    frames_rgb_uint16 = []
    for path in ordered_paths:
        frame_data = imageio_module.imread(str(path))
        normalized_frame = _normalize_uint16_rgb_image(
            np_module=np_module,
            image_data=frame_data,
        )
        frames_rgb_uint16.append(normalized_frame.astype(np_module.uint16))
    frames_rgb_uint16 = np_module.stack(frames_rgb_uint16, axis=0)
    if frames_rgb_uint16.shape[0] < 2:
        raise RuntimeError("HDR+ merge requires at least two aligned frames")
    scalar_frames = _hdrplus_luminance_proxy_uint16(np_module, frames_rgb_uint16)
    downsampled_scalar_frames = _hdrplus_box_down2_uint16(np_module, scalar_frames)
    scalar_tiles = _hdrplus_extract_overlapping_tiles(
        np_module=np_module,
        frames_array=downsampled_scalar_frames,
        tile_size=HDRPLUS_DOWNSAMPLED_TILE_SIZE,
        tile_stride=HDRPLUS_DOWNSAMPLED_TILE_SIZE // 2,
        pad_margin=HDRPLUS_DOWNSAMPLED_TILE_SIZE,
    )
    full_tiles = _hdrplus_extract_overlapping_tiles(
        np_module=np_module,
        frames_array=frames_rgb_uint16,
        tile_size=HDRPLUS_TILE_SIZE,
        tile_stride=HDRPLUS_TILE_STRIDE,
        pad_margin=HDRPLUS_TILE_SIZE,
    )
    weights, total_weight = _hdrplus_compute_temporal_weights(np_module, scalar_tiles)
    temporal_tiles = _hdrplus_merge_temporal_rgb(
        np_module=np_module,
        full_tiles_rgb=full_tiles,
        weights=weights,
        total_weight=total_weight,
    )
    merged_rgb_uint16 = _hdrplus_merge_spatial_rgb(
        np_module=np_module,
        temporal_tiles=temporal_tiles,
        width=int(frames_rgb_uint16.shape[2]),
        height=int(frames_rgb_uint16.shape[1]),
    )
    imageio_module.imwrite(str(output_hdr_tiff), merged_rgb_uint16)


def _convert_compression_to_quality(jpg_compression):
    """@brief Convert JPEG compression level to Pillow quality value.

    @details Maps inclusive compression range `[0, 100]` to inclusive quality
    range `[100, 1]` preserving deterministic inverse relation.
    @param jpg_compression {int} JPEG compression level.
    @return {int} Pillow quality value in `[1, 100]`.
    @satisfies REQ-065, REQ-066
    """

    return max(1, min(100, 100 - jpg_compression))


def _resolve_imagemagick_command():
    """@brief Resolve ImageMagick executable name for current runtime.

    @details Probes `magick` first (ImageMagick 7+ preferred CLI), then
    `convert` (legacy-compatible CLI alias) to preserve auto-adjust-stage compatibility
    across distributions that package ImageMagick under different executable
    names.
    @return {str|None} Resolved executable token (`magick` or `convert`) or
      `None` when no supported executable is available.
    @satisfies REQ-059, REQ-073
    """

    for executable in ("magick", "convert"):
        if shutil.which(executable) is not None:
            return executable
    return None


def _resolve_auto_adjust_opencv_dependencies():
    """@brief Resolve OpenCV runtime dependencies for image-domain stages.

    @details Imports `cv2` and `numpy` modules required by OpenCV auto-adjust
    pipeline and returns `None` with deterministic error output when
    dependencies are missing.
    @return {tuple[ModuleType, ModuleType]|None} `(cv2_module, numpy_module)` when available; `None` on dependency failure.
    @satisfies REQ-059, REQ-073, REQ-075
    """

    try:
        import cv2  # type: ignore
    except ModuleNotFoundError:
        print_error("Python dependency missing: opencv-python")
        print_error("Install dependencies with: uv pip install opencv-python numpy")
        return None
    try:
        import numpy as numpy_module  # type: ignore
    except ModuleNotFoundError:
        print_error("Python dependency missing: numpy")
        print_error("Install dependencies with: uv pip install opencv-python numpy")
        return None
    return (cv2, numpy_module)


def _resolve_numpy_dependency():
    """@brief Resolve numpy runtime dependency for auto-levels and auto-brightness.

    @details Imports `numpy` required by uint16-domain post-merge pre-stages and
    returns `None` with deterministic error output when dependency is missing.
    @return {ModuleType|None} Imported numpy module; `None` on dependency failure.
    @satisfies REQ-059, REQ-090, REQ-100
    """

    try:
        import numpy as numpy_module  # type: ignore
    except ModuleNotFoundError:
        print_error("Python dependency missing: numpy")
        print_error("Install dependencies with: uv pip install numpy")
        return None
    return numpy_module


def _to_uint8_image_array(np_module, image_data):
    """@brief Convert image tensor to `uint8` range `[0,255]`.

    @details Normalizes integer or float image payloads into `uint8` preserving
    relative brightness scale: `uint16` uses `/257`, normalized float arrays in
    `[0,1]` use `*255`, and all paths clamp to inclusive byte range.
    @param np_module {ModuleType} Imported numpy module.
    @param image_data {object} Numeric image tensor.
    @return {object} `uint8` image tensor.
    @satisfies REQ-066, REQ-090
    """

    dtype_name = str(getattr(image_data, "dtype", ""))
    if dtype_name == "uint8":
        return image_data
    if dtype_name == "uint16":
        if all(
            hasattr(np_module, attr) for attr in ("clip", "round", "uint8")
        ) and hasattr(image_data, "shape"):
            return np_module.clip(np_module.round(image_data / 257.0), 0, 255).astype(
                np_module.uint8
            )
        scaled_data = image_data / 257.0
        if hasattr(scaled_data, "clip"):
            scaled_data = scaled_data.clip(0, 255)
        if hasattr(scaled_data, "astype"):
            return scaled_data.astype("uint8")
        return scaled_data
    if all(
        hasattr(np_module, attr)
        for attr in ("array", "float64", "min", "max", "clip", "round", "uint8")
    ):
        numeric_data = np_module.array(image_data, dtype=np_module.float64)
        minimum_value = float(np_module.min(numeric_data)) if numeric_data.size else 0.0
        maximum_value = float(np_module.max(numeric_data)) if numeric_data.size else 0.0
        if minimum_value >= 0.0 and maximum_value <= 1.0:
            numeric_data = numeric_data * 255.0
        elif minimum_value >= 0.0 and maximum_value <= 65535.0 and maximum_value > 255.0:
            numeric_data = numeric_data / 257.0
        return np_module.clip(np_module.round(numeric_data), 0, 255).astype(
            np_module.uint8
        )
    if hasattr(image_data, "astype"):
        return image_data.astype("uint8")
    return image_data


def _to_uint16_image_array(np_module, image_data):
    """@brief Convert image tensor to `uint16` range `[0,65535]`.

    @details Normalizes integer or float image payloads into `uint16` preserving
    relative brightness scale: `uint8` uses `*257`, normalized float arrays in
    `[0,1]` use `*65535`, and all paths clamp to inclusive 16-bit range.
    @param np_module {ModuleType} Imported numpy module.
    @param image_data {object} Numeric image tensor.
    @return {object} `uint16` image tensor.
    @satisfies REQ-066, REQ-090
    """

    dtype_name = str(getattr(image_data, "dtype", ""))
    if dtype_name == "uint16":
        return image_data
    if dtype_name == "uint8":
        if all(
            hasattr(np_module, attr) for attr in ("clip", "round", "uint16")
        ) and hasattr(image_data, "shape"):
            return np_module.clip(np_module.round(image_data * 257.0), 0, 65535).astype(
                np_module.uint16
            )
        scaled_data = image_data * 257.0
        if hasattr(scaled_data, "clip"):
            scaled_data = scaled_data.clip(0, 65535)
        if hasattr(scaled_data, "astype"):
            return scaled_data.astype("uint16")
        return scaled_data
    if all(
        hasattr(np_module, attr)
        for attr in ("array", "float64", "min", "max", "clip", "round", "uint16")
    ):
        numeric_data = np_module.array(image_data, dtype=np_module.float64)
        minimum_value = float(np_module.min(numeric_data)) if numeric_data.size else 0.0
        maximum_value = float(np_module.max(numeric_data)) if numeric_data.size else 0.0
        if minimum_value >= 0.0 and maximum_value <= 1.0:
            numeric_data = numeric_data * 65535.0
        return np_module.clip(np_module.round(numeric_data), 0, 65535).astype(
            np_module.uint16
        )
    if hasattr(image_data, "astype"):
        return image_data.astype("uint16")
    return image_data


def _normalize_uint16_rgb_image(np_module, image_data):
    """@brief Normalize image payload into RGB uint16 tensor.

    @details Converts input image payload to `uint16`, normalizes channel layout
    for static postprocess stages by expanding grayscale to one channel,
    replicating single-channel input to RGB, dropping alpha from RGBA input,
    and returning first three channels for deterministic RGB processing.
    @param np_module {ModuleType} Imported numpy module.
    @param image_data {object} Numeric image tensor.
    @return {object} RGB uint16 image tensor with shape `(H,W,3)`.
    @exception ValueError Raised when normalized image has unsupported shape.
    @satisfies REQ-012, REQ-013, REQ-106
    """

    normalized = _to_uint16_image_array(np_module=np_module, image_data=image_data)
    if len(normalized.shape) == 2:
        normalized = normalized[:, :, None]
    if len(normalized.shape) == 3 and normalized.shape[2] == 1:
        normalized = np_module.repeat(normalized, 3, axis=2)
    if len(normalized.shape) == 3 and normalized.shape[2] == 4:
        normalized = normalized[:, :, :3]
    if len(normalized.shape) != 3 or normalized.shape[2] < 3:
        raise ValueError("Postprocess input image has unsupported shape")
    if normalized.shape[2] > 3:
        normalized = normalized[:, :, :3]
    return normalized


def _validate_uint16_rgb_stage_image(np_module, image_rgb_uint16, stage_label):
    """@brief Validate uint16 RGB tensor contract for static postprocess stages.

    @details Enforces deterministic guard rails for static uint16 postprocess
    steps by requiring dtype `uint16`, rank `3`, and channel count `3`.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_uint16 {object} Stage image payload to validate.
    @param stage_label {str} Diagnostic stage identifier for deterministic errors.
    @return {object} Validated RGB uint16 tensor.
    @exception ValueError Raised when stage tensor dtype or shape is unsupported.
    @satisfies REQ-012, REQ-013, REQ-106
    """

    dtype_name = str(getattr(image_rgb_uint16, "dtype", ""))
    if dtype_name != "uint16":
        raise ValueError(f"{stage_label}: expected uint16 RGB tensor")
    shape = getattr(image_rgb_uint16, "shape", ())
    if len(shape) != 3 or shape[2] != 3:
        raise ValueError(f"{stage_label}: expected shape (H,W,3)")
    return image_rgb_uint16


def _apply_post_gamma_uint16(np_module, image_rgb_uint16, gamma_value):
    """@brief Apply static post-gamma over RGB uint16 tensor.

    @details Executes gamma transfer directly in uint16 domain using a 65536-step
    LUT (`index == input uint16 code value`) and returns uint16 output without
    intermediate byte quantization to preserve full 16-bit gradation.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_uint16 {object} RGB uint16 image tensor.
    @param gamma_value {float} Static post-gamma factor.
    @return {object} RGB uint16 tensor after gamma stage.
    @satisfies REQ-012, REQ-013
    """

    validated_input = _validate_uint16_rgb_stage_image(
        np_module=np_module,
        image_rgb_uint16=image_rgb_uint16,
        stage_label="_apply_post_gamma_uint16.input",
    )
    if gamma_value == 1.0:
        return validated_input
    value_u16 = np_module.arange(65536, dtype=np_module.float64)
    lut_u16 = np_module.clip(
        np_module.round(
            np_module.power(value_u16 / 65535.0, 1.0 / float(gamma_value)) * 65535.0
        ),
        0.0,
        65535.0,
    ).astype(np_module.uint16)
    indices = np_module.clip(validated_input, 0, 65535).astype(np_module.int32)
    output = lut_u16[indices]
    return _validate_uint16_rgb_stage_image(
        np_module=np_module,
        image_rgb_uint16=output,
        stage_label="_apply_post_gamma_uint16.output",
    )


def _blend_uint16(np_module, base_uint16, target_uint16, factor):
    """@brief Blend two uint16 tensors with deterministic linear interpolation.

    @details Computes `base + factor*(target-base)` in float64, then rounds and
    clamps to uint16 to preserve deterministic postprocess factor behavior.
    @param np_module {ModuleType} Imported numpy module.
    @param base_uint16 {object} Base RGB uint16 tensor.
    @param target_uint16 {object} Target RGB uint16 tensor.
    @param factor {float} Interpolation factor.
    @return {object} RGB uint16 tensor after blend operation.
    @satisfies REQ-012, REQ-013
    """

    base_float = base_uint16.astype(np_module.float64)
    target_float = target_uint16.astype(np_module.float64)
    blended = base_float + float(factor) * (target_float - base_float)
    return np_module.clip(np_module.round(blended), 0.0, 65535.0).astype(np_module.uint16)


def _apply_brightness_uint16(np_module, image_rgb_uint16, brightness_factor):
    """@brief Apply static brightness factor on RGB uint16 tensor.

    @details Multiplies uint16 RGB channels by `brightness_factor` in float64
    domain and applies deterministic clamp/round to uint16 without byte-domain
    conversion.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_uint16 {object} RGB uint16 image tensor.
    @param brightness_factor {float} Brightness scale factor.
    @return {object} RGB uint16 tensor after brightness stage.
    @satisfies REQ-012, REQ-013
    """

    validated_input = _validate_uint16_rgb_stage_image(
        np_module=np_module,
        image_rgb_uint16=image_rgb_uint16,
        stage_label="_apply_brightness_uint16.input",
    )
    if brightness_factor == 1.0:
        return validated_input
    image_float = validated_input.astype(np_module.float64)
    adjusted = image_float * float(brightness_factor)
    output = np_module.clip(np_module.round(adjusted), 0.0, 65535.0).astype(np_module.uint16)
    return _validate_uint16_rgb_stage_image(
        np_module=np_module,
        image_rgb_uint16=output,
        stage_label="_apply_brightness_uint16.output",
    )


def _apply_contrast_uint16(np_module, image_rgb_uint16, contrast_factor):
    """@brief Apply static contrast factor on RGB uint16 tensor.

    @details Applies contrast interpolation around luminance mean computed on
    float64 uint16 tensor (`output = mean + factor*(input-mean)`), then clamps
    and rounds to uint16.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_uint16 {object} RGB uint16 image tensor.
    @param contrast_factor {float} Contrast interpolation factor.
    @return {object} RGB uint16 tensor after contrast stage.
    @satisfies REQ-012, REQ-013
    """

    validated_input = _validate_uint16_rgb_stage_image(
        np_module=np_module,
        image_rgb_uint16=image_rgb_uint16,
        stage_label="_apply_contrast_uint16.input",
    )
    if contrast_factor == 1.0:
        return validated_input
    image_float = validated_input.astype(np_module.float64)
    luminance_mean = np_module.mean(image_float, axis=(0, 1), keepdims=True)
    adjusted = luminance_mean + float(contrast_factor) * (image_float - luminance_mean)
    output = np_module.clip(np_module.round(adjusted), 0.0, 65535.0).astype(np_module.uint16)
    return _validate_uint16_rgb_stage_image(
        np_module=np_module,
        image_rgb_uint16=output,
        stage_label="_apply_contrast_uint16.output",
    )


def _apply_saturation_uint16(np_module, image_rgb_uint16, saturation_factor):
    """@brief Apply static saturation factor on RGB uint16 tensor.

    @details Applies saturation interpolation around BT.709 luminance in float64
    uint16 domain (`output = gray + factor*(input-gray)`), then clamps and rounds
    to uint16.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_uint16 {object} RGB uint16 image tensor.
    @param saturation_factor {float} Saturation interpolation factor.
    @return {object} RGB uint16 tensor after saturation stage.
    @satisfies REQ-012, REQ-013
    """

    validated_input = _validate_uint16_rgb_stage_image(
        np_module=np_module,
        image_rgb_uint16=image_rgb_uint16,
        stage_label="_apply_saturation_uint16.input",
    )
    if saturation_factor == 1.0:
        return validated_input
    image_float = validated_input.astype(np_module.float64)
    red_channel = image_float[:, :, 0]
    green_channel = image_float[:, :, 1]
    blue_channel = image_float[:, :, 2]
    grayscale = (
        (0.2126 * red_channel) + (0.7152 * green_channel) + (0.0722 * blue_channel)
    )[:, :, None]
    adjusted = grayscale + float(saturation_factor) * (image_float - grayscale)
    output = np_module.clip(np_module.round(adjusted), 0.0, 65535.0).astype(np_module.uint16)
    return _validate_uint16_rgb_stage_image(
        np_module=np_module,
        image_rgb_uint16=output,
        stage_label="_apply_saturation_uint16.output",
    )


def _apply_static_postprocess_uint16(np_module, image_rgb_uint16, postprocess_options):
    """@brief Execute static postprocess chain fully in uint16 precision.

    @details Applies post-gamma, brightness, contrast, and saturation in fixed
    order over RGB uint16 tensor and preserves uint16 output for downstream
    auto-adjust/final quantization stages.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_uint16 {object} RGB uint16 image tensor.
    @param postprocess_options {PostprocessOptions} Parsed postprocess controls.
    @return {object} RGB uint16 tensor after static postprocess chain.
    @satisfies REQ-012, REQ-013, REQ-106
    """

    processed = _validate_uint16_rgb_stage_image(
        np_module=np_module,
        image_rgb_uint16=image_rgb_uint16,
        stage_label="_apply_static_postprocess_uint16.input",
    )
    processed = _apply_post_gamma_uint16(
        np_module=np_module,
        image_rgb_uint16=processed,
        gamma_value=postprocess_options.post_gamma,
    )
    processed = _apply_brightness_uint16(
        np_module=np_module,
        image_rgb_uint16=processed,
        brightness_factor=postprocess_options.brightness,
    )
    processed = _apply_contrast_uint16(
        np_module=np_module,
        image_rgb_uint16=processed,
        contrast_factor=postprocess_options.contrast,
    )
    processed = _apply_saturation_uint16(
        np_module=np_module,
        image_rgb_uint16=processed,
        saturation_factor=postprocess_options.saturation,
    )
    return processed


def _to_linear_srgb(np_module, image_srgb):
    """@brief Convert sRGB tensor to linear-sRGB tensor.

    @details Applies IEC 61966-2-1 piecewise inverse transfer function on
    normalized channel values in `[0,1]`.
    @param np_module {ModuleType} Imported numpy module.
    @param image_srgb {object} Float image tensor in sRGB domain `[0,1]`.
    @return {object} Float image tensor in linear-sRGB domain `[0,1]`.
    @satisfies REQ-090, REQ-099
    """

    mask = image_srgb <= 0.04045
    result = image_srgb.copy()
    result[mask] = image_srgb[mask] / 12.92
    result[~mask] = ((image_srgb[~mask] + 0.055) / 1.055) ** 2.4
    return result


def _from_linear_srgb(np_module, image_linear):
    """@brief Convert linear-sRGB tensor to sRGB tensor.

    @details Applies IEC 61966-2-1 piecewise forward transfer function on
    normalized linear channel values in `[0,1]`.
    @param np_module {ModuleType} Imported numpy module.
    @param image_linear {object} Float image tensor in linear-sRGB domain `[0,1]`.
    @return {object} Float image tensor in sRGB domain `[0,1]`.
    @satisfies REQ-090, REQ-099
    """

    mask = image_linear <= 0.0031308
    result = image_linear.copy()
    result[mask] = image_linear[mask] * 12.92
    result[~mask] = 1.055 * (image_linear[~mask] ** (1.0 / 2.4)) - 0.055
    return result


def _compute_bt709_luminance(np_module, linear_rgb):
    """@brief Compute BT.709 linear luminance from linear RGB tensor.

    @details Computes per-pixel luminance using BT.709 coefficients with RGB
    channel order: `0.2126*R + 0.7152*G + 0.0722*B`.
    @param np_module {ModuleType} Imported numpy module.
    @param linear_rgb {object} Linear-sRGB float tensor with shape `H,W,3`.
    @return {object} Float luminance tensor with shape `H,W`.
    @satisfies REQ-090, REQ-099
    """

    return (
        0.2126 * linear_rgb[..., 0]
        + 0.7152 * linear_rgb[..., 1]
        + 0.0722 * linear_rgb[..., 2]
    )


def _analyze_luminance_key(np_module, luminance, eps):
    """@brief Analyze luminance distribution and classify scene key.

    @details Computes log-average luminance, median, percentile tails, and
    clip proxies on normalized BT.709 luminance and classifies scene as
    `low-key`, `normal-key`, or `high-key` using conservative thresholds.
    @param np_module {ModuleType} Imported numpy module.
    @param luminance {object} BT.709 luminance float tensor in `[0, 1]`.
    @param eps {float} Positive numerical stability guard.
    @return {dict[str, float|str]} Key analysis dictionary with key type, central statistics, tails, and clipping proxies.
    @satisfies REQ-050, REQ-103
    """

    luminance_clamped = np_module.clip(luminance, 0.0, 1.0)
    log_average = float(
        np_module.exp(np_module.mean(np_module.log(eps + luminance_clamped)))
    )
    median_luminance = float(np_module.median(luminance_clamped))
    p05 = float(np_module.percentile(luminance_clamped, 5.0))
    p95 = float(np_module.percentile(luminance_clamped, 95.0))
    shadow_clip = float(np_module.mean(luminance_clamped <= (1.0 / 65535.0)))
    highlight_clip = float(np_module.mean(luminance_clamped >= (65534.0 / 65535.0)))
    if median_luminance < 0.35 and p95 < 0.85:
        key_type = "low-key"
    elif median_luminance > 0.65 and p05 > 0.15:
        key_type = "high-key"
    else:
        key_type = "normal-key"
    return {
        "key_type": key_type,
        "log_avg_lum": log_average,
        "median_lum": median_luminance,
        "p05": p05,
        "p95": p95,
        "shadow_clip_in": shadow_clip,
        "highlight_clip_in": highlight_clip,
    }


def _choose_auto_key_value(key_analysis, auto_brightness_options):
    """@brief Select Reinhard key value from key-analysis metrics.

    @details Chooses base key by scene class (`0.09/0.18/0.36`) and applies
    conservative under/over-exposure adaptation bounded by configured min/max
    key limits and automatic boost factor.
    @param key_analysis {dict[str, float|str]} Luminance key-analysis dictionary.
    @param auto_brightness_options {AutoBrightnessOptions} Parsed auto-brightness parameters.
    @return {float} Clamped key value `a`.
    @satisfies REQ-050, REQ-103
    """

    key_type = str(key_analysis["key_type"])
    if key_type == "low-key":
        key_value = DEFAULT_AB_LOW_KEY_VALUE
    elif key_type == "high-key":
        key_value = DEFAULT_AB_HIGH_KEY_VALUE
    else:
        key_value = DEFAULT_AB_NORMAL_KEY_VALUE

    under_hint = (
        float(key_analysis["p95"]) < 0.60 and float(key_analysis["median_lum"]) < 0.35
    )
    over_hint = (
        float(key_analysis["p05"]) > 0.40 and float(key_analysis["median_lum"]) > 0.65
    )

    if under_hint:
        key_value = min(
            key_value * auto_brightness_options.max_auto_boost_factor,
            auto_brightness_options.key_max,
        )
    if over_hint:
        key_value = max(
            key_value / auto_brightness_options.max_auto_boost_factor,
            auto_brightness_options.key_min,
        )

    return float(
        min(
            max(key_value, auto_brightness_options.key_min),
            auto_brightness_options.key_max,
        )
    )


def _reinhard_global_tonemap_luminance(
    np_module,
    luminance,
    key_value,
    white_point_percentile,
    eps,
):
    """@brief Apply Reinhard global tonemap on luminance with robust `Lwhite`.

    @details Executes photographic operator: `Lw_bar=exp(mean(log(eps+Y)))`,
    `L=(a/Lw_bar)*Y`, robust `Lwhite` from percentile of `L`, then burn-out
    compression `Ld=(L*(1+L/(Lwhite^2)))/(1+L)`.
    @param np_module {ModuleType} Imported numpy module.
    @param luminance {object} BT.709 luminance float tensor.
    @param key_value {float} Reinhard key value `a`.
    @param white_point_percentile {float} Percentile in `(0,100)` for robust white point.
    @param eps {float} Positive numerical stability guard.
    @return {tuple[object, dict[str, float]]} Tonemapped luminance tensor and debug statistics dictionary.
    @satisfies REQ-050, REQ-104
    """

    luminance_clamped = np_module.clip(luminance, 0.0, 1.0)
    lw_bar = float(np_module.exp(np_module.mean(np_module.log(eps + luminance_clamped))))
    scaled_luminance = (key_value / (lw_bar + eps)) * luminance_clamped
    lwhite = float(np_module.percentile(scaled_luminance, white_point_percentile))
    lwhite = max(lwhite, eps)
    ld = (scaled_luminance * (1.0 + (scaled_luminance / (lwhite * lwhite)))) / (
        1.0 + scaled_luminance
    )
    debug = {
        "Lw_bar": lw_bar,
        "a": float(key_value),
        "Lwhite": lwhite,
        "Ld_min": float(np_module.min(ld)),
        "Ld_max": float(np_module.max(ld)),
    }
    return np_module.clip(ld, 0.0, 1.0), debug


def _luminance_preserving_desaturate_to_fit(np_module, rgb_linear, luminance, eps):
    """@brief Desaturate only out-of-gamut pixels while preserving luminance.

    @details For pixels where any RGB channel exceeds `1.0`, computes minimal
    blend factor toward grayscale `(Y,Y,Y)` such that max channel becomes `<=1`
    while preserving BT.709 luminance of both endpoints.
    @param np_module {ModuleType} Imported numpy module.
    @param rgb_linear {object} Linear RGB float tensor.
    @param luminance {object} Target luminance tensor used for grayscale anchor.
    @param eps {float} Positive numerical stability guard.
    @return {object} Desaturated and clamped linear RGB tensor.
    @satisfies REQ-050, REQ-105
    """

    rgb_out = rgb_linear.copy()
    gray = np_module.stack([luminance, luminance, luminance], axis=-1)
    max_channel = np_module.max(rgb_out, axis=-1)
    mask = max_channel > 1.0
    if not bool(np_module.any(mask)):
        return np_module.clip(rgb_out, 0.0, 1.0)
    denominator = max_channel - luminance + eps
    blend = np_module.zeros_like(max_channel)
    blend[mask] = (max_channel[mask] - 1.0) / denominator[mask]
    blend = np_module.clip(blend, 0.0, 1.0)
    rgb_out = (1.0 - blend[..., None]) * rgb_out + blend[..., None] * gray
    return np_module.clip(rgb_out, 0.0, 1.0)


def _apply_mild_local_contrast_bgr_uint16(cv2_module, np_module, image_bgr_uint16, options):
    """@brief Apply optional mild CLAHE micro-contrast on 16-bit Y channel.

    @details Converts BGR16 to YCrCb, runs CLAHE on 16-bit Y with configured
    clip/tile controls, then blends original and CLAHE outputs using configured
    local-contrast strength.
    @param cv2_module {ModuleType} Imported cv2 module.
    @param np_module {ModuleType} Imported numpy module.
    @param image_bgr_uint16 {object} BGR uint16 image tensor.
    @param options {AutoBrightnessOptions} Parsed auto-brightness options.
    @return {object} BGR uint16 image tensor after optional local contrast.
    @satisfies REQ-050, REQ-105
    """

    strength = float(min(max(options.local_contrast_strength, 0.0), 1.0))
    if strength <= 0.0:
        return image_bgr_uint16
    ycrcb = cv2_module.cvtColor(image_bgr_uint16, cv2_module.COLOR_BGR2YCrCb)
    y_channel, cr_channel, cb_channel = cv2_module.split(ycrcb)
    clahe = cv2_module.createCLAHE(
        clipLimit=float(options.clahe_clip_limit),
        tileGridSize=tuple(options.clahe_tile_grid_size),
    )
    y_clahe = clahe.apply(y_channel)
    ycrcb_clahe = cv2_module.merge([y_clahe, cr_channel, cb_channel])
    bgr_clahe = cv2_module.cvtColor(ycrcb_clahe, cv2_module.COLOR_YCrCb2BGR)
    blended = cv2_module.addWeighted(
        image_bgr_uint16,
        1.0 - strength,
        bgr_clahe,
        strength,
        0.0,
    )
    return np_module.clip(blended, 0, 65535).astype(np_module.uint16)


def _rt_gamma2(np_module, values):
    """@brief Apply RawTherapee gamma2 transfer function.

    @details Implements the same piecewise gamma curve used in the attached
    auto-levels source for histogram-domain bright clipping normalization.
    @param np_module {ModuleType} Imported numpy module.
    @param values {object} Float tensor in linear domain.
    @return {object} Float tensor in gamma2 domain.
    @satisfies REQ-100
    """

    return np_module.where(
        values <= 0.00304,
        values * 12.92310,
        1.055
        * np_module.power(np_module.maximum(values, 1e-300), 1.0 / 2.4)
        - 0.055,
    )


def _rt_igamma2(np_module, values):
    """@brief Apply inverse RawTherapee gamma2 transfer function.

    @details Implements inverse piecewise gamma curve paired with `_rt_gamma2`
    for whiteclip/black normalization inside auto-levels.
    @param np_module {ModuleType} Imported numpy module.
    @param values {object} Float tensor in gamma2 domain.
    @return {object} Float tensor in linear domain.
    @satisfies REQ-100
    """

    return np_module.where(
        values <= 0.03928,
        values / 12.92310,
        np_module.power(
            np_module.maximum((values + 0.055) / 1.055, 1e-300),
            2.4,
        ),
    )


def _build_autoexp_histogram_rgb_uint16(np_module, image_rgb_uint16, histcompr):
    """@brief Build RGB auto-levels histogram from uint16 image tensor.

    @details Builds one RawTherapee-compatible luminance histogram from the
    post-merge RGB tensor using BT.709 luminance, compressed bins
    (`hist_size = 65536 >> histcompr`), and deterministic index clipping.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_uint16 {object} RGB uint16 image tensor.
    @param histcompr {int} Histogram compression shift in `[0, 15]`.
    @return {object} Histogram tensor.
    @satisfies REQ-100, REQ-117
    """

    hist_size = 65536 >> histcompr
    scale = 1.0 / float(1 << histcompr)
    luminance = (
        0.2126729 * image_rgb_uint16[..., 0].astype(np_module.float64)
        + 0.7151521 * image_rgb_uint16[..., 1].astype(np_module.float64)
        + 0.0721750 * image_rgb_uint16[..., 2].astype(np_module.float64)
    )
    histogram_index = np_module.clip(
        (luminance * scale).astype(np_module.int64), 0, hist_size - 1
    )
    return np_module.bincount(
        histogram_index.ravel(), minlength=hist_size
    ).astype(np_module.uint64)


def _compute_auto_levels_from_histogram(np_module, histogram, histcompr, clip_percent):
    """@brief Compute auto-levels gain metrics from histogram.

    @details Ports `get_autoexp_from_histogram` from attached source as-is in
    numeric behavior for one luminance histogram: octile spread, white/black
    clip, exposure compensation, brightness/contrast, and highlight compression
    metrics.
    @param np_module {ModuleType} Imported numpy module.
    @param histogram {object} Flattened histogram tensor.
    @param histcompr {int} Histogram compression shift.
    @param clip_percent {float} Clip percentage.
    @return {dict[str, int|float]} Auto-levels metrics dictionary.
    @satisfies REQ-100, REQ-117, REQ-118
    """

    rt_maxval = 65535.0
    rt_midgray = 0.1842
    histogram_flat = np_module.asarray(histogram, dtype=np_module.float64).ravel()
    expected = 65536 >> histcompr
    if histogram_flat.size != expected:
        raise ValueError(
            f"histogram size must be {expected} for histcompr={histcompr}"
        )

    total = float(histogram_flat.sum())
    weighted = float(
        np_module.dot(histogram_flat, np_module.arange(expected, dtype=np_module.float64))
    )
    average = weighted / total if total > 0 else 0.0
    if total <= 0.0:
        return {
            "expcomp": 0.0,
            "gain": 1.0,
            "black": 0,
            "brightness": 0,
            "contrast": 0,
            "hlcompr": 0,
            "hlcomprthresh": 0,
            "whiteclip": 0,
            "rawmax": 0,
            "shc": 0,
            "median": 0,
            "average": 0.0,
            "overex": 0,
            "ospread": 0.0,
        }

    cdf = np_module.cumsum(histogram_flat)
    median = int(np_module.searchsorted(cdf, total / 2.0, side="left"))
    if median == 0 or average < 1.0:
        return {
            "expcomp": 0.0,
            "gain": 1.0,
            "black": 0,
            "brightness": 0,
            "contrast": 0,
            "hlcompr": 0,
            "hlcomprthresh": 0,
            "whiteclip": 0,
            "rawmax": 0,
            "shc": 0,
            "median": median << histcompr,
            "average": average * (1 << histcompr),
            "overex": 0,
            "ospread": 0.0,
        }

    octile = np_module.zeros(8, dtype=np_module.float64)
    ospread = 0.0
    low_sum = 0.0
    high_sum = 0.0
    octile_count = 0
    histogram_index = 0
    average_index = min(int(average), expected)
    while histogram_index < average_index:
        if octile_count < 8:
            octile[octile_count] += histogram_flat[histogram_index]
            if octile[octile_count] > total / 8.0 or (
                octile_count == 7 and octile[octile_count] > total / 16.0
            ):
                octile[octile_count] = math.log1p(histogram_index) / math.log(2.0)
                octile_count += 1
        low_sum += histogram_flat[histogram_index]
        histogram_index += 1
    while histogram_index < expected:
        if octile_count < 8:
            octile[octile_count] += histogram_flat[histogram_index]
            if octile[octile_count] > total / 8.0 or (
                octile_count == 7 and octile[octile_count] > total / 16.0
            ):
                octile[octile_count] = math.log1p(histogram_index) / math.log(2.0)
                octile_count += 1
        high_sum += histogram_flat[histogram_index]
        histogram_index += 1

    if low_sum == 0 or high_sum == 0:
        return {
            "expcomp": 0.0,
            "gain": 1.0,
            "black": 0,
            "brightness": 0,
            "contrast": 0,
            "hlcompr": 0,
            "hlcomprthresh": 0,
            "whiteclip": 0,
            "rawmax": 0,
            "shc": 0,
            "median": median << histcompr,
            "average": average * (1 << histcompr),
            "overex": 0,
            "ospread": 0.0,
        }

    overex = 0
    guard = math.log1p(float(expected))
    if octile[6] > guard:
        octile[6] = 1.5 * octile[5] - 0.5 * octile[4]
        overex = 2
    if octile[7] > guard:
        octile[7] = 1.5 * octile[6] - 0.5 * octile[5]
        overex = 1
    octile_6 = float(octile[6])
    octile_7 = float(octile[7])
    for octile_index in range(1, 8):
        if octile[octile_index] == 0.0:
            octile[octile_index] = octile[octile_index - 1]
    for octile_index in range(1, 6):
        if octile_index > 2:
            denominator = max(0.5, (octile[octile_index + 1] - octile[3]))
        else:
            denominator = max(0.5, (octile[3] - octile[octile_index]))
        ospread += (octile[octile_index + 1] - octile[octile_index]) / denominator
    ospread /= 5.0
    if ospread <= 0.0:
        return {
            "expcomp": 0.0,
            "gain": 1.0,
            "black": 0,
            "brightness": 0,
            "contrast": 0,
            "hlcompr": 0,
            "hlcomprthresh": 0,
            "whiteclip": 0,
            "rawmax": 0,
            "shc": 0,
            "median": median << histcompr,
            "average": average * (1 << histcompr),
            "overex": overex,
            "ospread": ospread,
        }

    clipped = 0.0
    rawmax = expected - 1
    while rawmax > 1 and histogram_flat[rawmax] + clipped <= 0.0:
        clipped += histogram_flat[rawmax]
        rawmax -= 1

    clippable = int(total * clip_percent / 100.0)
    clipped = 0.0
    whiteclip = expected - 1
    while whiteclip > 1 and histogram_flat[whiteclip] + clipped <= clippable:
        clipped += histogram_flat[whiteclip]
        whiteclip -= 1

    clipped = 0.0
    shc = 0
    while shc < whiteclip - 1 and histogram_flat[shc] + clipped <= clippable:
        clipped += histogram_flat[shc]
        shc += 1

    rawmax <<= histcompr
    whiteclip <<= histcompr
    average *= (1 << histcompr)
    median <<= histcompr
    shc <<= histcompr

    expcomp1 = math.log(
        rt_midgray * rt_maxval / max(average - shc + rt_midgray * shc, 1e-12)
    ) / math.log(2.0)
    if overex == 0:
        expcomp2 = 0.5 * (
            (15.5 - histcompr - (2.0 * octile_7 - octile_6))
            + math.log(rt_maxval / rawmax) / math.log(2.0)
        )
    else:
        expcomp2 = 0.5 * (
            (15.5 - histcompr - (2.0 * octile[7] - octile[6]))
            + math.log(rt_maxval / rawmax) / math.log(2.0)
        )
    if abs(expcomp1) - abs(expcomp2) > 1.0:
        denominator = abs(expcomp1) + abs(expcomp2)
        expcomp = (
            expcomp1 * abs(expcomp2) + expcomp2 * abs(expcomp1)
        ) / max(denominator, 1e-12)
    else:
        expcomp = 0.5 * expcomp1 + 0.5 * expcomp2

    gain = math.exp(expcomp * math.log(2.0))
    corr = math.sqrt(gain * rt_maxval / rawmax)
    black = int(shc * corr)
    hlcomprthresh = 0
    comp = (gain * whiteclip / rt_maxval - 1.0) * 2.3
    hlcompr = int(100.0 * comp / (max(0.0, expcomp) + 1.0))
    hlcompr = max(0, min(100, hlcompr))

    midtmp = gain * math.sqrt(median * average) / rt_maxval
    if midtmp < 0.1:
        brightness = int((rt_midgray - midtmp) * 15.0 / max(midtmp, 1e-12))
    else:
        brightness = int(
            (rt_midgray - midtmp) / max(0.10833 - 0.0833 * midtmp, 1e-12) * 15.0
        )
    brightness = int(0.25 * max(0, brightness))

    contrast = int(50.0 * (1.1 - ospread))
    contrast = max(0, min(100, contrast))
    whiteclip_gamma = float(int(_rt_gamma2(np_module, whiteclip * corr / rt_maxval) * rt_maxval))

    gavg = 0.0
    value = 0.0
    increment = corr * (1 << histcompr)
    for histogram_index in range(expected):
        gavg += histogram_flat[histogram_index] * float(
            _rt_gamma2(np_module, value / rt_maxval) * rt_maxval
        )
        value += increment
    gavg /= total
    if black < gavg:
        max_whiteclip = (gavg - black) * 4.0 / 3.0 + black
        if whiteclip_gamma < max_whiteclip:
            whiteclip_gamma = max_whiteclip

    whiteclip_gamma = float(_rt_igamma2(np_module, whiteclip_gamma / rt_maxval) * rt_maxval)
    black = int((rt_maxval * black) / whiteclip_gamma) if whiteclip_gamma > 0 else 0
    expcomp = max(-5.0, min(12.0, float(expcomp)))
    brightness = max(-100, min(100, int(brightness)))
    return {
        "expcomp": float(expcomp),
        "gain": float(gain),
        "black": int(black),
        "brightness": int(brightness),
        "contrast": int(contrast),
        "hlcompr": int(hlcompr),
        "hlcomprthresh": int(hlcomprthresh),
        "whiteclip": int(whiteclip),
        "rawmax": int(rawmax),
        "shc": int(shc),
        "median": int(median),
        "average": float(average),
        "overex": int(overex),
        "ospread": float(ospread),
    }


def _apply_auto_levels_uint16(np_module, image_rgb_uint16, auto_levels_options):
    """@brief Apply auto-levels stage on RGB uint16 tensor.

    @details Executes auto-levels histogram analysis ported from attached source,
    applies gain derived from exposure compensation, conditionally runs
    highlight reconstruction, and optionally normalizes overflowing RGB triplets
    back into uint16 gamut.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_uint16 {object} RGB uint16 image tensor.
    @param auto_levels_options {AutoLevelsOptions} Parsed auto-levels options.
    @return {object} RGB uint16 tensor after auto-levels stage.
    @exception ValueError Raised when input tensor is not uint16 RGB.
    @satisfies REQ-100, REQ-101, REQ-102, REQ-119, REQ-120
    """

    if str(getattr(image_rgb_uint16, "dtype", "")) != "uint16":
        raise ValueError("Auto-levels input image must be uint16")
    if len(image_rgb_uint16.shape) != 3 or image_rgb_uint16.shape[2] != 3:
        raise ValueError("Auto-levels input image must be RGB uint16")
    histogram = _build_autoexp_histogram_rgb_uint16(
        np_module=np_module,
        image_rgb_uint16=image_rgb_uint16,
        histcompr=auto_levels_options.histcompr,
    )
    auto_levels_metrics = _compute_auto_levels_from_histogram(
        np_module=np_module,
        histogram=histogram,
        histcompr=auto_levels_options.histcompr,
        clip_percent=auto_levels_options.clip_percent,
    )
    gain = float(auto_levels_metrics["gain"])
    image_float = image_rgb_uint16.astype(np_module.float64) * gain
    if auto_levels_options.highlight_reconstruction_enabled:
        method = auto_levels_options.highlight_reconstruction_method
        if method == "Luminance Recovery":
            image_float = _hlrecovery_luminance_uint16(
                np_module=np_module,
                image_rgb=image_float,
                maxval=65535.0,
            )
        elif method == "CIELab Blending":
            image_float = _hlrecovery_cielab_uint16(
                np_module=np_module,
                image_rgb=image_float,
                maxval=65535.0,
            )
        elif method == "Blend":
            channel_max = np_module.max(image_float, axis=(0, 1))
            image_float = _hlrecovery_blend_uint16(
                np_module=np_module,
                image_rgb=image_float,
                hlmax=channel_max,
                maxval=65535.0,
            )
        elif method == "Color Propagation":
            image_float = _hlrecovery_color_propagation_uint16(
                np_module=np_module,
                image_rgb=image_float,
                maxval=65535.0,
            )
        elif method == "Inpaint Opposed":
            image_float = _hlrecovery_inpaint_opposed_uint16(
                np_module=np_module,
                image_rgb=image_float,
                gain_threshold=auto_levels_options.gain_threshold,
                maxval=65535.0,
            )
        else:
            raise ValueError(f"Unsupported highlight reconstruction method: {method}")
    if auto_levels_options.clip_out_of_gamut:
        image_float = _clip_auto_levels_out_of_gamut_uint16(
            np_module=np_module,
            image_rgb=image_float,
            maxval=65535.0,
        )
    return np_module.clip(np_module.round(image_float), 0.0, 65535.0).astype(
        np_module.uint16
    )


def _clip_auto_levels_out_of_gamut_uint16(np_module, image_rgb, maxval=65535.0):
    """@brief Normalize overflowing RGB triplets back into uint16 gamut.

    @details Computes per-pixel maximum channel value, derives one scale factor
    for overflowing pixels, and preserves RGB ratios while bounding the triplet
    to `maxval`.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on uint16 scale.
    @param maxval {float} Maximum allowed channel value.
    @return {object} RGB float tensor with no channel above `maxval`.
    @satisfies REQ-120
    """

    rgb = np_module.asarray(image_rgb, dtype=np_module.float64)
    channel_max = np_module.max(rgb, axis=-1, keepdims=True)
    scale = np_module.where(channel_max > maxval, maxval / channel_max, 1.0)
    return rgb * scale


def _hlrecovery_luminance_uint16(np_module, image_rgb, maxval=65535.0):
    """@brief Apply Luminance highlight reconstruction on uint16-like RGB tensor.

    @details Ports luminance method from attached source in RGB domain with
    clipped-channel chroma ratio scaling and masked reconstruction.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on uint16 scale.
    @param maxval {float} Maximum channel value.
    @return {object} Highlight-reconstructed RGB float tensor.
    @satisfies REQ-102
    """

    rgb = np_module.asarray(image_rgb, dtype=np_module.float64)
    red = rgb[..., 0]
    green = rgb[..., 1]
    blue = rgb[..., 2]
    mask = np_module.any(rgb > maxval, axis=-1)
    output = rgb.copy()
    if not np_module.any(mask):
        return output

    red_clip = np_module.minimum(red, maxval)
    green_clip = np_module.minimum(green, maxval)
    blue_clip = np_module.minimum(blue, maxval)
    luminance = red + green + blue
    chroma_c = 1.732050808 * (red - green)
    chroma_h = 2.0 * blue - red - green
    chroma_c_clip = 1.732050808 * (red_clip - green_clip)
    chroma_h_clip = 2.0 * blue_clip - red_clip - green_clip
    neq_mask = (red != green) & (green != blue)
    denominator = np_module.maximum(chroma_c * chroma_c + chroma_h * chroma_h, 1e-20)
    ratio = np_module.sqrt(
        (chroma_c_clip * chroma_c_clip + chroma_h_clip * chroma_h_clip) / denominator
    )
    ratio = np_module.where(neq_mask, ratio, 1.0)
    chroma_c2 = chroma_c * ratio
    chroma_h2 = chroma_h * ratio
    rec_red = luminance / 3.0 - chroma_h2 / 6.0 + chroma_c2 / 3.464101615
    rec_green = luminance / 3.0 - chroma_h2 / 6.0 - chroma_c2 / 3.464101615
    rec_blue = luminance / 3.0 + chroma_h2 / 3.0
    output[..., 0] = np_module.where(mask, rec_red, output[..., 0])
    output[..., 1] = np_module.where(mask, rec_green, output[..., 1])
    output[..., 2] = np_module.where(mask, rec_blue, output[..., 2])
    return output


def _hlrecovery_cielab_uint16(
    np_module, image_rgb, maxval=65535.0, xyz_cam=None, cam_xyz=None
):
    """@brief Apply CIELab blending highlight reconstruction on RGB tensor.

    @details Ports CIELab blending method from attached source with Lab-space
    channel repair under clipped highlights.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on uint16 scale.
    @param maxval {float} Maximum channel value.
    @param xyz_cam {object|None} Optional XYZ conversion matrix.
    @param cam_xyz {object|None} Optional inverse matrix.
    @return {object} Highlight-reconstructed RGB float tensor.
    @satisfies REQ-102
    """

    rgb = np_module.asarray(image_rgb, dtype=np_module.float64)
    if xyz_cam is None:
        xyz_cam = np_module.array(
            [
                [0.4124564, 0.3575761, 0.1804375],
                [0.2126729, 0.7151522, 0.0721750],
                [0.0193339, 0.1191920, 0.9503041],
            ],
            dtype=np_module.float64,
        ) * maxval
    else:
        xyz_cam = np_module.asarray(xyz_cam, dtype=np_module.float64)
    if cam_xyz is None:
        cam_xyz = np_module.linalg.inv(xyz_cam / maxval)
    cam_xyz = np_module.asarray(cam_xyz, dtype=np_module.float64)
    if cam_xyz.max() >= 10.0:
        cam_xyz = cam_xyz / maxval

    def _f_lab(values):
        values_r = values / maxval
        return np_module.where(
            values_r > 0.008856,
            np_module.cbrt(values_r),
            7.787036979 * values_r + (16.0 / 116.0),
        )

    def _f2xyz(values):
        return np_module.where(
            values > (24.0 / 116.0),
            np_module.power(values, 3.0),
            (values - (16.0 / 116.0)) / 7.787036979,
        )

    mask = np_module.any(rgb > maxval, axis=-1)
    output = rgb.copy()
    if not np_module.any(mask):
        return output
    clipped = np_module.minimum(rgb, maxval)
    yy = np_module.tensordot(rgb, xyz_cam[1], axes=([2], [0]))
    fy = _f_lab(yy)
    x_values = np_module.tensordot(clipped, xyz_cam[0], axes=([2], [0]))
    y_values = np_module.tensordot(clipped, xyz_cam[1], axes=([2], [0]))
    z_values = np_module.tensordot(clipped, xyz_cam[2], axes=([2], [0]))
    fx_c = _f_lab(x_values)
    fy_c = _f_lab(y_values)
    fz_c = _f_lab(z_values)
    fz = fy - fy_c + fz_c
    fx = fy + fx_c - fy_c
    zr = _f2xyz(fz) * maxval
    xr = _f2xyz(fx) * maxval
    x_axis = xr
    y_axis = yy
    z_axis = zr
    rec_red = (
        cam_xyz[0, 0] * x_axis + cam_xyz[0, 1] * y_axis + cam_xyz[0, 2] * z_axis
    )
    rec_green = (
        cam_xyz[1, 0] * x_axis + cam_xyz[1, 1] * y_axis + cam_xyz[1, 2] * z_axis
    )
    rec_blue = (
        cam_xyz[2, 0] * x_axis + cam_xyz[2, 1] * y_axis + cam_xyz[2, 2] * z_axis
    )
    output[..., 0] = np_module.where(mask, rec_red, output[..., 0])
    output[..., 1] = np_module.where(mask, rec_green, output[..., 1])
    output[..., 2] = np_module.where(mask, rec_blue, output[..., 2])
    return output


def _hlrecovery_blend_uint16(np_module, image_rgb, hlmax, maxval=65535.0):
    """@brief Apply Blend highlight reconstruction on RGB tensor.

    @details Ports blend method from attached source with quadratic channel blend
    and desaturation phase driven by clipping metrics.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on uint16 scale.
    @param hlmax {object} Channel maxima vector with shape `(3,)`.
    @param maxval {float} Maximum channel value.
    @return {object} Highlight-reconstructed RGB float tensor.
    @satisfies REQ-102
    """

    blend_trans = np_module.array(
        [
            [1.0, 1.0, 1.0],
            [1.7320508, -1.7320508, 0.0],
            [-1.0, -1.0, 2.0],
        ],
        dtype=np_module.float64,
    )
    blend_itrans = np_module.array(
        [
            [1.0, 0.8660254, -0.5],
            [1.0, -0.8660254, -0.5],
            [1.0, 0.0, 1.0],
        ],
        dtype=np_module.float64,
    )
    rgb = np_module.asarray(image_rgb, dtype=np_module.float64)
    hlmax_values = np_module.asarray(hlmax, dtype=np_module.float64)
    if hlmax_values.shape != (3,):
        raise ValueError("hlmax must contain exactly 3 values")
    output = rgb.copy()
    red = output[..., 0]
    green = output[..., 1]
    blue = output[..., 2]
    minpt = float(np_module.min(hlmax_values))
    maxave = float(np_module.mean(hlmax_values))
    clipthresh = 0.95
    fixthresh = 0.5
    satthresh = 0.5
    clip = np_module.minimum(maxave, hlmax_values)
    clippt = clipthresh * maxval
    fixpt = fixthresh * minpt
    desatpt = satthresh * maxave + (1.0 - satthresh) * maxval
    clipped_mask = (red > clippt) | (green > clippt) | (blue > clippt)
    if not np_module.any(clipped_mask):
        return output
    rgb_stack = np_module.stack([red, green, blue], axis=-1)
    cam0 = rgb_stack.copy()
    cam1 = np_module.minimum(cam0, maxval)
    lratio = np_module.sum(np_module.minimum(cam0, clip[None, None, :]), axis=-1)
    lab0 = np_module.tensordot(cam0, blend_trans.T, axes=([2], [0]))
    lab1 = np_module.tensordot(cam1, blend_trans.T, axes=([2], [0]))
    sum0 = lab0[..., 1] ** 2 + lab0[..., 2] ** 2
    sum1 = lab1[..., 1] ** 2 + lab1[..., 2] ** 2
    chratio = np_module.sqrt(np_module.maximum(sum1, 0.0) / np_module.maximum(sum0, 1e-20))
    lab0_adj = lab0.copy()
    lab0_adj[..., 1] *= chratio
    lab0_adj[..., 2] *= chratio
    rgb_conv = np_module.tensordot(lab0_adj, blend_itrans.T, axes=([2], [0])) / 3.0
    for channel_index, clip_channel in enumerate(clip):
        channel = output[..., channel_index]
        channel_rec = rgb_conv[..., channel_index]
        channel_mask = channel > fixpt
        frac_num = np_module.minimum(clip_channel, channel) - fixpt
        frac_den = max(clip_channel - fixpt, 1e-20)
        frac = np_module.square(frac_num / frac_den)
        blended = frac * channel_rec + (1.0 - frac) * channel
        output[..., channel_index] = np_module.where(
            channel_mask,
            np_module.minimum(maxave, blended),
            channel,
        )
    red_s = output[..., 0]
    green_s = output[..., 1]
    blue_s = output[..., 2]
    sum_rgb = np_module.maximum(red_s + green_s + blue_s, 1e-20)
    lratio = lratio / sum_rgb
    lightness = sum_rgb / 3.0
    chroma_c = lratio * 1.732050808 * (red_s - green_s)
    chroma_h = lratio * (2.0 * blue_s - red_s - green_s)
    output[..., 0] = lightness - chroma_h / 6.0 + chroma_c / 3.464101615
    output[..., 1] = lightness - chroma_h / 6.0 - chroma_c / 3.464101615
    output[..., 2] = lightness + chroma_h / 3.0
    red_s2 = output[..., 0]
    green_s2 = output[..., 1]
    blue_s2 = output[..., 2]
    lightness2 = (red_s2 + green_s2 + blue_s2) / 3.0
    desat_mask = lightness2 > desatpt
    lfrac = np_module.maximum(0.0, (maxave - lightness2) / max(maxave - desatpt, 1e-20))
    chroma_c2 = lfrac * 1.732050808 * (red_s2 - green_s2)
    chroma_h2 = lfrac * (2.0 * blue_s2 - red_s2 - green_s2)
    rec_red = lightness2 - chroma_h2 / 6.0 + chroma_c2 / 3.464101615
    rec_green = lightness2 - chroma_h2 / 6.0 - chroma_c2 / 3.464101615
    rec_blue = lightness2 + chroma_h2 / 3.0
    output[..., 0] = np_module.where(desat_mask, rec_red, output[..., 0])
    output[..., 1] = np_module.where(desat_mask, rec_green, output[..., 1])
    output[..., 2] = np_module.where(desat_mask, rec_blue, output[..., 2])
    return output


def _dilate_mask_uint16(np_module, mask):
    """@brief Expand one boolean mask by one Chebyshev pixel.

    @details Pads the mask by one pixel and OR-combines the `3x3` neighborhood
    so later highlight-reconstruction stages can estimate one border region
    around clipped pixels without external dependencies.
    @param np_module {ModuleType} Imported numpy module.
    @param mask {object} Boolean tensor with shape `H,W`.
    @return {object} Boolean tensor with the same shape as `mask`.
    @satisfies REQ-119
    """

    padded = np_module.pad(mask.astype(bool), 1, mode="constant", constant_values=False)
    dilated = np_module.zeros(mask.shape, dtype=bool)
    for row_offset in range(3):
        for col_offset in range(3):
            dilated |= padded[
                row_offset : row_offset + mask.shape[0],
                col_offset : col_offset + mask.shape[1],
            ]
    return dilated


def _box_mean_3x3_uint16(np_module, image_2d):
    """@brief Compute one deterministic `3x3` box mean over a 2D float tensor.

    @details Uses edge padding and exact neighborhood averaging to approximate
    RawTherapee local neighborhood probes needed by RGB-space color-propagation
    and inpaint-opposed highlight reconstruction.
    @param np_module {ModuleType} Imported numpy module.
    @param image_2d {object} Float tensor with shape `H,W`.
    @return {object} Float tensor with shape `H,W`.
    @satisfies REQ-119
    """

    source = np_module.asarray(image_2d, dtype=np_module.float64)
    padded = np_module.pad(source, 1, mode="edge")
    window_sum = np_module.zeros(source.shape, dtype=np_module.float64)
    for row_offset in range(3):
        for col_offset in range(3):
            window_sum += padded[
                row_offset : row_offset + source.shape[0],
                col_offset : col_offset + source.shape[1],
            ]
    return window_sum / 9.0


def _hlrecovery_color_propagation_uint16(np_module, image_rgb, maxval=65535.0):
    """@brief Apply Color Propagation highlight reconstruction on RGB tensor.

    @details Approximates RawTherapee `Color` recovery in post-merge RGB space:
    detect clipped channel regions, estimate one local opposite-channel
    reference from `3x3` means, derive one border chrominance offset, and fill
    clipped samples deterministically.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on uint16 scale.
    @param maxval {float} Maximum channel value.
    @return {object} Highlight-reconstructed RGB float tensor.
    @satisfies REQ-102, REQ-119
    """

    rgb = np_module.asarray(image_rgb, dtype=np_module.float64)
    output = rgb.copy()
    clip_level = 0.95 * maxval
    dark_floor = 0.25 * clip_level
    for channel_index in range(3):
        channel = output[..., channel_index]
        channel_mask = channel >= clip_level
        if not np_module.any(channel_mask):
            continue
        other_indices = [index for index in range(3) if index != channel_index]
        reference = 0.5 * (
            _box_mean_3x3_uint16(np_module, output[..., other_indices[0]])
            + _box_mean_3x3_uint16(np_module, output[..., other_indices[1]])
        )
        border_mask = _dilate_mask_uint16(np_module, channel_mask) & (~channel_mask)
        border_mask &= channel > dark_floor
        border_mask &= channel < clip_level
        chroma_offset = 0.0
        if np_module.any(border_mask):
            chroma_offset = float(
                np_module.mean(channel[border_mask] - reference[border_mask])
            )
        restored = reference + chroma_offset
        output[..., channel_index] = np_module.where(
            channel_mask,
            np_module.maximum(channel, restored),
            channel,
        )
    return output


def _hlrecovery_inpaint_opposed_uint16(
    np_module, image_rgb, gain_threshold, maxval=65535.0
):
    """@brief Apply Inpaint Opposed highlight reconstruction on RGB tensor.

    @details Approximates RawTherapee `Coloropp` recovery in post-merge RGB
    space: derive the RawTherapee clip threshold from `gain_threshold`,
    construct one cubic-root opposite-channel neighborhood predictor, estimate
    one border chrominance offset, and inpaint only pixels above the clip
    threshold.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on uint16 scale.
    @param gain_threshold {float} Positive Inpaint Opposed gain threshold.
    @param maxval {float} Maximum channel value.
    @return {object} Highlight-reconstructed RGB float tensor.
    @satisfies REQ-102, REQ-119
    """

    rgb = np_module.asarray(image_rgb, dtype=np_module.float64)
    output = rgb.copy()
    gain = 1.2 * float(gain_threshold)
    clip_level = (0.987 / max(gain, 1e-12)) * maxval
    clip_dark_levels = (0.03 * clip_level, 0.125 * clip_level, 0.03 * clip_level)
    for channel_index in range(3):
        channel = output[..., channel_index]
        channel_mask = channel >= clip_level
        if not np_module.any(channel_mask):
            continue
        local_means = []
        for source_channel in range(3):
            local_mean = _box_mean_3x3_uint16(np_module, output[..., source_channel])
            local_means.append(np_module.cbrt(np_module.maximum(local_mean, 0.0)))
        other_indices = [index for index in range(3) if index != channel_index]
        reference = np_module.power(
            0.5 * (local_means[other_indices[0]] + local_means[other_indices[1]]),
            3.0,
        )
        border_mask = _dilate_mask_uint16(np_module, channel_mask) & (~channel_mask)
        border_mask &= channel > clip_dark_levels[channel_index]
        border_mask &= channel < clip_level
        chroma_offset = 0.0
        if np_module.any(border_mask):
            chroma_offset = float(
                np_module.mean(channel[border_mask] - reference[border_mask])
            )
        restored = reference + chroma_offset
        output[..., channel_index] = np_module.where(
            channel_mask,
            np_module.maximum(channel, restored),
            channel,
        )
    return output


def _apply_auto_brightness_rgb_uint8(np_module, image_rgb_uint8, auto_brightness_options):
    """@brief Apply photographic BT.709 auto-brightness on uint16 RGB tensor.

    @details Executes 16-bit pipeline: normalize to float `[0,1]`, linearize
    sRGB, derive BT.709 luminance, classify key using log-average and
    percentiles, choose/override key value `a`, apply Reinhard global tonemap
    with robust percentile white-point, preserve chromaticity by luminance
    scaling, perform luminance-preserving anti-clipping desaturation, then
    de-linearize and restore uint16 output.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_uint8 {object} RGB uint16 image tensor.
    @param auto_brightness_options {AutoBrightnessOptions} Parsed auto-brightness parameters.
    @return {object} RGB uint16 image tensor after BT.709 auto-brightness.
    @exception ValueError Raised when input tensor is not uint16 RGB.
    @satisfies REQ-050, REQ-066, REQ-090, REQ-099, REQ-103, REQ-104, REQ-105
    """

    if str(getattr(image_rgb_uint8, "dtype", "")) != "uint16":
        raise ValueError("Auto-brightness input image must be uint16")
    if len(image_rgb_uint8.shape) != 3 or image_rgb_uint8.shape[2] != 3:
        raise ValueError("Auto-brightness input image must be RGB uint16")

    image_srgb = image_rgb_uint8.astype(np_module.float64) / 65535.0
    image_linear = _to_linear_srgb(np_module=np_module, image_srgb=image_srgb)
    luminance = _compute_bt709_luminance(np_module=np_module, linear_rgb=image_linear)
    key_analysis = _analyze_luminance_key(
        np_module=np_module,
        luminance=luminance,
        eps=auto_brightness_options.eps,
    )
    key_value = auto_brightness_options.key_value
    if key_value is None:
        key_value = _choose_auto_key_value(
            key_analysis=key_analysis,
            auto_brightness_options=auto_brightness_options,
        )
    else:
        key_value = float(
            min(
                max(float(key_value), auto_brightness_options.key_min),
                auto_brightness_options.key_max,
            )
        )
    luminance_mapped, _debug = _reinhard_global_tonemap_luminance(
        np_module=np_module,
        luminance=luminance,
        key_value=float(key_value),
        white_point_percentile=float(auto_brightness_options.white_point_percentile),
        eps=float(auto_brightness_options.eps),
    )
    luminance_scale = luminance_mapped / (luminance + auto_brightness_options.eps)
    bright_linear = image_linear * luminance_scale[..., None]
    bright_linear = _luminance_preserving_desaturate_to_fit(
        np_module=np_module,
        rgb_linear=bright_linear,
        luminance=luminance_mapped,
        eps=auto_brightness_options.eps,
    )
    bright_srgb = _from_linear_srgb(np_module=np_module, image_linear=bright_linear)
    return np_module.clip(
        np_module.round(bright_srgb * 65535.0), 0.0, 65535.0
    ).astype(np_module.uint16)



def _apply_validated_auto_adjust_pipeline(
    postprocessed_input, auto_adjust_output, imagemagick_command, auto_adjust_options
):
    """@brief Execute validated auto-adjust pipeline over temporary lossless 16-bit TIFF files.

    @details Uses ImageMagick to normalize source data to 16-bit-per-channel TIFF,
    applies deterministic denoise/level/sigmoidal/vibrance/high-pass overlay
    stages parameterized by shared auto-adjust knobs, and writes lossless
    auto-adjust output artifact consumed by JPG encoder.
    @param postprocessed_input {Path} Temporary postprocess image input path.
    @param auto_adjust_output {Path} Temporary auto-adjust output TIFF path.
    @param imagemagick_command {str} Resolved ImageMagick executable token.
    @param auto_adjust_options {AutoAdjustOptions} Shared auto-adjust knob values.
    @return {None} Side effects only.
    @exception subprocess.CalledProcessError Raised when ImageMagick returns non-zero.
    @satisfies REQ-073, REQ-077, REQ-086
    """

    auto_adjust_input_16 = auto_adjust_output.parent / "auto_adjust_input_16.tif"
    to_16_bit_command = [
        imagemagick_command,
        str(postprocessed_input),
        "-colorspace",
        "sRGB",
        "-depth",
        "16",
        "-compress",
        "LZW",
        str(auto_adjust_input_16),
    ]
    subprocess.run(to_16_bit_command, check=True)

    auto_adjust_command = [
        imagemagick_command,
        str(auto_adjust_input_16),
        "-depth",
        "16",
        "-selective-blur",
        f"0x{auto_adjust_options.blur_sigma:g}+{auto_adjust_options.blur_threshold_pct:g}%",
        "-channel",
        "RGB",
        "-level",
        f"{auto_adjust_options.level_low_pct:g}%,{auto_adjust_options.level_high_pct:g}%",
        "+channel",
        "-sigmoidal-contrast",
        f"{auto_adjust_options.sigmoid_contrast:g}x{(auto_adjust_options.sigmoid_midpoint * 100.0):g}%",
        "-colorspace",
        "HSL",
        "-channel",
        "G",
        "-gamma",
        f"{auto_adjust_options.saturation_gamma:g}",
        "+channel",
        "-colorspace",
        "sRGB",
        "(",
        "-clone",
        "0",
        "-clone",
        "0",
        "-blur",
        f"0x{auto_adjust_options.highpass_blur_sigma:g}",
        "-compose",
        "mathematics",
        "-define",
        "compose:args=0,1,-1,0.5",
        "-composite",
        "-colorspace",
        "gray",
        ")",
        "-compose",
        "Overlay",
        "-composite",
        "-depth",
        "16",
        "-compress",
        "LZW",
        str(auto_adjust_output),
    ]
    subprocess.run(auto_adjust_command, check=True)


def _clamp01(np_module, values):
    """@brief Clamp numeric image tensor values into `[0.0, 1.0]` interval.

    @details Applies vectorized clipping to ensure deterministic bounded values
    for OpenCV auto-adjust pipeline float-domain operations.
    @param np_module {ModuleType} Imported numpy module.
    @param values {object} Numeric tensor-like payload.
    @return {object} Clipped tensor payload.
    @satisfies REQ-075
    """

    return np_module.clip(values, 0.0, 1.0)


def _gaussian_kernel_2d(np_module, sigma, radius=None):
    """@brief Build normalized 2D Gaussian kernel.

    @details Creates deterministic Gaussian kernel used by selective blur stage;
    returns identity kernel when `sigma <= 0`.
    @param np_module {ModuleType} Imported numpy module.
    @param sigma {float} Gaussian sigma value.
    @param radius {int|None} Optional kernel radius override.
    @return {object} Normalized 2D kernel tensor.
    @satisfies REQ-075
    """

    if sigma <= 0:
        return np_module.array([[1.0]], dtype=np_module.float64)
    if radius is None:
        radius = max(1, int(np_module.ceil(3.0 * sigma)))
    axis = np_module.arange(-radius, radius + 1, dtype=np_module.float64)
    xx, yy = np_module.meshgrid(axis, axis)
    kernel = np_module.exp(-(xx**2 + yy**2) / (2.0 * sigma * sigma))
    kernel /= np_module.sum(kernel)
    return kernel


def _rgb_to_hsl(np_module, rgb):
    """@brief Convert RGB float tensor to HSL channels.

    @details Implements explicit HSL conversion for OpenCV auto-adjust saturation-gamma
    stage without delegating to external color-space helpers.
    @param np_module {ModuleType} Imported numpy module.
    @param rgb {object} RGB tensor in `[0.0, 1.0]`.
    @return {tuple[object, object, object]} `(h, s, l)` channel tensors.
    @satisfies REQ-075
    """

    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]
    cmax = np_module.maximum(np_module.maximum(r, g), b)
    cmin = np_module.minimum(np_module.minimum(r, g), b)
    delta = cmax - cmin
    lightness = 0.5 * (cmax + cmin)
    saturation = np_module.zeros_like(lightness)
    nonzero = delta > 1e-12
    saturation[nonzero] = delta[nonzero] / (
        1.0 - np_module.abs(2.0 * lightness[nonzero] - 1.0)
    )
    hue = np_module.zeros_like(lightness)
    mask_r = nonzero & (cmax == r)
    mask_g = nonzero & (cmax == g)
    mask_b = nonzero & (cmax == b)
    hue[mask_r] = ((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6.0
    hue[mask_g] = ((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2.0
    hue[mask_b] = ((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4.0
    hue = (hue / 6.0) % 1.0
    return (hue, saturation, lightness)


def _hue_to_rgb(np_module, p_values, q_values, t_values):
    """@brief Convert one hue-shift channel to RGB component.

    @details Evaluates piecewise hue interpolation branch used by HSL-to-RGB
    conversion in OpenCV auto-adjust pipeline.
    @param np_module {ModuleType} Imported numpy module.
    @param p_values {object} Lower chroma interpolation boundary.
    @param q_values {object} Upper chroma interpolation boundary.
    @param t_values {object} Hue-shifted channel tensor.
    @return {object} RGB component tensor.
    @satisfies REQ-075
    """

    t_values = t_values % 1.0
    output = np_module.empty_like(t_values)
    case1 = t_values < (1.0 / 6.0)
    case2 = (t_values >= (1.0 / 6.0)) & (t_values < 0.5)
    case3 = (t_values >= 0.5) & (t_values < (2.0 / 3.0))
    case4 = ~(case1 | case2 | case3)
    output[case1] = (
        p_values[case1] + (q_values[case1] - p_values[case1]) * 6.0 * t_values[case1]
    )
    output[case2] = q_values[case2]
    output[case3] = (
        p_values[case3]
        + (q_values[case3] - p_values[case3]) * ((2.0 / 3.0) - t_values[case3]) * 6.0
    )
    output[case4] = p_values[case4]
    return output


def _hsl_to_rgb(np_module, hue, saturation, lightness):
    """@brief Convert HSL channels to RGB float tensor.

    @details Reconstructs RGB tensor with explicit achromatic/chromatic branches
    for OpenCV auto-adjust saturation-gamma stage.
    @param np_module {ModuleType} Imported numpy module.
    @param hue {object} Hue channel tensor.
    @param saturation {object} Saturation channel tensor.
    @param lightness {object} Lightness channel tensor.
    @return {object} RGB tensor in `[0.0, 1.0]`.
    @satisfies REQ-075
    """

    rgb = np_module.zeros(hue.shape + (3,), dtype=np_module.float64)
    achromatic = saturation <= 1e-12
    rgb[achromatic, 0] = lightness[achromatic]
    rgb[achromatic, 1] = lightness[achromatic]
    rgb[achromatic, 2] = lightness[achromatic]
    chromatic = ~achromatic
    if np_module.any(chromatic):
        lightness_chromatic = lightness[chromatic]
        saturation_chromatic = saturation[chromatic]
        hue_chromatic = hue[chromatic]
        q_values = np_module.where(
            lightness_chromatic < 0.5,
            lightness_chromatic * (1.0 + saturation_chromatic),
            lightness_chromatic
            + saturation_chromatic
            - lightness_chromatic * saturation_chromatic,
        )
        p_values = 2.0 * lightness_chromatic - q_values
        rgb[chromatic, 0] = _hue_to_rgb(
            np_module, p_values, q_values, hue_chromatic + 1.0 / 3.0
        )
        rgb[chromatic, 1] = _hue_to_rgb(np_module, p_values, q_values, hue_chromatic)
        rgb[chromatic, 2] = _hue_to_rgb(
            np_module, p_values, q_values, hue_chromatic - 1.0 / 3.0
        )
    return _clamp01(np_module, rgb)


def _selective_blur_contrast_gated_vectorized(
    np_module, rgb, sigma=2.0, threshold_percent=10.0
):
    """@brief Execute contrast-gated selective blur stage.

    @details Applies vectorized contrast-gated neighborhood accumulation over
    Gaussian kernel offsets to emulate selective blur behavior.
    @param np_module {ModuleType} Imported numpy module.
    @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
    @param sigma {float} Gaussian sigma.
    @param threshold_percent {float} Luma-difference threshold percent.
    @return {object} Blurred RGB float tensor.
    @satisfies REQ-075
    """

    height, width, _channels = rgb.shape
    kernel = _gaussian_kernel_2d(np_module, sigma=sigma)
    radius = kernel.shape[0] // 2
    threshold = threshold_percent / 100.0
    gray = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    rgb_padded = np_module.pad(
        rgb, ((radius, radius), (radius, radius), (0, 0)), mode="reflect"
    )
    gray_padded = np_module.pad(
        gray, ((radius, radius), (radius, radius)), mode="reflect"
    )
    out_numerator = np_module.zeros_like(rgb)
    out_denominator = np_module.zeros_like(gray)
    for delta_y in range(2 * radius + 1):
        for delta_x in range(2 * radius + 1):
            weight = kernel[delta_y, delta_x]
            if weight <= 1e-5:
                continue
            shifted_gray = gray_padded[
                delta_y : delta_y + height, delta_x : delta_x + width
            ]
            shifted_rgb = rgb_padded[
                delta_y : delta_y + height, delta_x : delta_x + width, :
            ]
            mask = np_module.abs(shifted_gray - gray) <= threshold
            weighted_mask = mask * weight
            out_denominator += weighted_mask
            out_numerator += shifted_rgb * weighted_mask[..., None]
    valid = out_denominator > 1e-15
    output = np_module.where(
        valid[..., None], out_numerator / out_denominator[..., None], rgb
    )
    return _clamp01(np_module, output)


def _level_per_channel_adaptive(np_module, rgb, low_pct=0.1, high_pct=99.9):
    """@brief Execute adaptive per-channel level normalization.

    @details Applies percentile-based level stretching independently for each
    RGB channel.
    @param np_module {ModuleType} Imported numpy module.
    @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
    @param low_pct {float} Low percentile threshold.
    @param high_pct {float} High percentile threshold.
    @return {object} Level-normalized RGB float tensor.
    @satisfies REQ-075
    """

    output = np_module.empty_like(rgb)
    for channel_index in range(3):
        channel = rgb[..., channel_index]
        low_value = np_module.percentile(channel, low_pct)
        high_value = np_module.percentile(channel, high_pct)
        scale = 1.0 / max(high_value - low_value, 1e-12)
        output[..., channel_index] = (channel - low_value) * scale
    return _clamp01(np_module, output)


def _sigmoidal_contrast(np_module, rgb, contrast=3.0, midpoint=0.5):
    """@brief Execute sigmoidal contrast stage.

    @details Applies logistic remapping with bounded normalization for each RGB
    channel.
    @param np_module {ModuleType} Imported numpy module.
    @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
    @param contrast {float} Logistic slope.
    @param midpoint {float} Logistic midpoint.
    @return {object} Contrast-adjusted RGB float tensor.
    @satisfies REQ-075
    """

    x_values = _clamp01(np_module, rgb)

    def logistic(z_values):
        return 1.0 / (1.0 + np_module.exp(-z_values))

    low_bound = logistic(contrast * (0.0 - midpoint))
    high_bound = logistic(contrast * (1.0 - midpoint))
    mapped = logistic(contrast * (x_values - midpoint))
    mapped = (mapped - low_bound) / max(high_bound - low_bound, 1e-12)
    return _clamp01(np_module, mapped)


def _vibrance_hsl_gamma(np_module, rgb, saturation_gamma=0.8):
    """@brief Execute HSL saturation gamma stage.

    @details Converts RGB to HSL, applies saturation gamma transform, and
    converts back to RGB.
    @param np_module {ModuleType} Imported numpy module.
    @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
    @param saturation_gamma {float} Saturation gamma denominator value.
    @return {object} Saturation-adjusted RGB float tensor.
    @satisfies REQ-075
    """

    hue, saturation, lightness = _rgb_to_hsl(np_module, rgb)
    saturation = _clamp01(np_module, saturation) ** (1.0 / saturation_gamma)
    output = _hsl_to_rgb(np_module, hue, saturation, lightness)
    return _clamp01(np_module, output)


def _gaussian_blur_rgb(cv2_module, np_module, rgb, sigma):
    """@brief Execute RGB Gaussian blur with reflected border mode.

    @details Computes odd kernel size from sigma and applies OpenCV Gaussian
    blur preserving reflected border behavior.
    @param cv2_module {ModuleType} Imported cv2 module.
    @param np_module {ModuleType} Imported numpy module.
    @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
    @param sigma {float} Gaussian sigma.
    @return {object} Blurred RGB float tensor.
    @satisfies REQ-075
    """

    kernel_size = max(3, int(np_module.ceil(6.0 * sigma)) | 1)
    blurred = cv2_module.GaussianBlur(
        rgb,
        (kernel_size, kernel_size),
        sigmaX=sigma,
        sigmaY=sigma,
        borderType=cv2_module.BORDER_REFLECT,
    )
    return _clamp01(np_module, blurred)


def _high_pass_math_gray(cv2_module, np_module, rgb, blur_sigma=2.5):
    """@brief Execute high-pass math grayscale stage.

    @details Computes high-pass response as `A - B + 0.5` over RGB channels and
    converts to luminance grayscale tensor.
    @param cv2_module {ModuleType} Imported cv2 module.
    @param np_module {ModuleType} Imported numpy module.
    @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
    @param blur_sigma {float} Gaussian blur sigma for high-pass base.
    @return {object} Grayscale float tensor in `[0.0, 1.0]`.
    @satisfies REQ-075
    """

    blurred = _gaussian_blur_rgb(cv2_module, np_module, rgb, sigma=blur_sigma)
    high_pass = rgb - blurred + 0.5
    high_pass = _clamp01(np_module, high_pass)
    gray = (
        0.2126 * high_pass[..., 0]
        + 0.7152 * high_pass[..., 1]
        + 0.0722 * high_pass[..., 2]
    )
    return _clamp01(np_module, gray)


def _overlay_composite(np_module, base_rgb, overlay_gray):
    """@brief Execute overlay composite stage.

    @details Applies conditional overlay blend equation over RGB base and
    grayscale overlay tensors.
    @param np_module {ModuleType} Imported numpy module.
    @param base_rgb {object} Base RGB float tensor in `[0.0, 1.0]`.
    @param overlay_gray {object} Overlay grayscale tensor in `[0.0, 1.0]`.
    @return {object} Overlay-composited RGB float tensor.
    @satisfies REQ-075
    """

    source = np_module.repeat(overlay_gray[..., None], 3, axis=2)
    destination = base_rgb
    output = np_module.where(
        destination <= 0.5,
        2.0 * source * destination,
        1.0 - 2.0 * (1.0 - source) * (1.0 - destination),
    )
    return _clamp01(np_module, output)


def _apply_validated_auto_adjust_pipeline_opencv(
    input_file, output_file, cv2_module, np_module, auto_adjust_options
):
    """@brief Execute validated auto-adjust pipeline using OpenCV and numpy.

    @details Reads RGB image payload and enforces deterministic auto-adjust input
    normalization: `uint8` inputs are promoted to `uint16` using `value*257`,
    then explicit 16-bit-to-float normalization is applied. Executes selective
    blur, adaptive levels, sigmoidal contrast, HSL saturation gamma,
    high-pass/overlay stages, then restores float payload to 16-bit-per-channel
    RGB TIFF output, parameterized by shared auto-adjust knobs.
    @param input_file {Path} Source TIFF path.
    @param output_file {Path} Output TIFF path.
    @param cv2_module {ModuleType} Imported cv2 module.
    @param np_module {ModuleType} Imported numpy module.
    @param auto_adjust_options {AutoAdjustOptions} Shared auto-adjust knob values.
    @return {None} Side effects only.
    @exception OSError Raised when source file is missing.
    @exception RuntimeError Raised when OpenCV read/write fails or input dtype is unsupported.
    @satisfies REQ-073, REQ-075, REQ-077, REQ-087
    """

    if not input_file.exists():
        raise OSError(f"OpenCV auto-adjust input file not found: {input_file}")
    image_bgr = cv2_module.imread(str(input_file), cv2_module.IMREAD_UNCHANGED)
    if image_bgr is None:
        raise RuntimeError(f"OpenCV failed to read auto-adjust input: {input_file}")
    if len(image_bgr.shape) != 3 or image_bgr.shape[2] != 3:
        raise RuntimeError(
            f"OpenCV auto-adjust input must be 3-channel image: {input_file}"
        )
    dtype_name = str(getattr(image_bgr, "dtype", ""))
    if dtype_name == "uint8":
        image_bgr = (image_bgr.astype(np_module.uint16) * 257).astype(np_module.uint16)
    elif dtype_name != "uint16":
        raise RuntimeError(
            f"OpenCV auto-adjust input must be uint16 image: {input_file}"
        )
    rgb_float = (
        cv2_module.cvtColor(image_bgr, cv2_module.COLOR_BGR2RGB).astype(
            np_module.float64
        )
        / 65535.0
    )
    rgb_float = _selective_blur_contrast_gated_vectorized(
        np_module,
        rgb_float,
        sigma=auto_adjust_options.blur_sigma,
        threshold_percent=auto_adjust_options.blur_threshold_pct,
    )
    rgb_float = _level_per_channel_adaptive(
        np_module,
        rgb_float,
        low_pct=auto_adjust_options.level_low_pct,
        high_pct=auto_adjust_options.level_high_pct,
    )
    rgb_float = _sigmoidal_contrast(
        np_module,
        rgb_float,
        contrast=auto_adjust_options.sigmoid_contrast,
        midpoint=auto_adjust_options.sigmoid_midpoint,
    )
    rgb_float = _vibrance_hsl_gamma(
        np_module, rgb_float, saturation_gamma=auto_adjust_options.saturation_gamma
    )
    high_pass_gray = _high_pass_math_gray(
        cv2_module,
        np_module,
        rgb_float,
        blur_sigma=auto_adjust_options.highpass_blur_sigma,
    )
    rgb_float = _overlay_composite(np_module, rgb_float, high_pass_gray)
    output_rgb_u16 = np_module.clip(
        np_module.round(rgb_float * 65535.0), 0, 65535
    ).astype(np_module.uint16)
    output_bgr_u16 = cv2_module.cvtColor(output_rgb_u16, cv2_module.COLOR_RGB2BGR)
    if not cv2_module.imwrite(str(output_file), output_bgr_u16):
        raise RuntimeError(f"OpenCV failed to write auto-adjust output: {output_file}")


def _load_piexif_dependency():
    """@brief Resolve piexif runtime dependency for EXIF thumbnail refresh.

    @details Imports `piexif` module required for EXIF thumbnail regeneration and
    reinsertion; emits deterministic install guidance when dependency is missing.
    @return {ModuleType|None} Imported piexif module; `None` on dependency failure.
    @satisfies REQ-059, REQ-078
    """

    try:
        import piexif  # type: ignore
    except ModuleNotFoundError:
        print_error("Python dependency missing: piexif")
        print_error("Install dependencies with: uv pip install piexif")
        return None
    return piexif


def _encode_jpg(
    imageio_module,
    pil_image_module,
    merged_tiff,
    output_jpg,
    postprocess_options,
    imagemagick_command=None,
    auto_adjust_opencv_dependencies=None,
    numpy_module=None,
    piexif_module=None,
    source_exif_payload=None,
    source_orientation=1,
    ev_zero=0.0,
):
    """@brief Encode merged HDR TIFF payload into final JPG output.

    @details Loads merged image payload, normalizes to RGB uint16 tensor, executes
    optional auto-brightness stage, optional auto-levels stage, static
    post-gamma/brightness/contrast/saturation chain in uint16 precision, optional
    auto-adjust stage over temporary 16-bit TIFF intermediates, then performs one
    final uint16-to-uint8 conversion immediately before JPEG save.
    @param imageio_module {ModuleType} Imported imageio module with `imread` and `imwrite`.
    @param pil_image_module {ModuleType} Imported Pillow image module.
    @param merged_tiff {Path} Merged TIFF source path produced by selected backend.
    @param output_jpg {Path} Final JPG output path.
    @param postprocess_options {PostprocessOptions} Shared TIFF-to-JPG correction settings.
    @param imagemagick_command {str|None} Optional pre-resolved ImageMagick executable.
    @param auto_adjust_opencv_dependencies {tuple[ModuleType, ModuleType]|None} Optional `(cv2, numpy)` modules for OpenCV auto-adjust implementations.
    @param numpy_module {ModuleType|None} Optional numpy module for uint16-domain stages.
    @param piexif_module {ModuleType|None} Optional piexif module for EXIF thumbnail refresh.
    @param source_exif_payload {bytes|None} Serialized EXIF payload copied from input DNG.
    @param source_orientation {int} Source EXIF orientation value in range `1..8`.
    @param ev_zero {float} Selected EV center used for extraction and merge reference.
    @return {None} Side effects only.
    @exception RuntimeError Raised when numpy or auto-adjust mode dependencies are missing or auto-adjust mode value is unsupported.
    @satisfies REQ-012, REQ-013, REQ-050, REQ-058, REQ-066, REQ-069, REQ-073, REQ-074, REQ-075, REQ-077, REQ-078, REQ-086, REQ-087, REQ-090, REQ-100, REQ-101, REQ-102, REQ-103, REQ-104, REQ-105, REQ-106
    """

    del ev_zero
    merged_data = imageio_module.imread(str(merged_tiff))
    if numpy_module is not None:
        np_module = numpy_module
    elif auto_adjust_opencv_dependencies is not None:
        _cv2_module, np_module = auto_adjust_opencv_dependencies
        del _cv2_module
    else:
        try:
            import numpy as np_module  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError("Missing required dependency: numpy") from exc

    image_rgb_uint16 = _normalize_uint16_rgb_image(
        np_module=np_module,
        image_data=merged_data,
    )
    if postprocess_options.auto_brightness_enabled:
        image_rgb_uint16 = _apply_auto_brightness_rgb_uint8(
            np_module=np_module,
            image_rgb_uint8=image_rgb_uint16,
            auto_brightness_options=postprocess_options.auto_brightness_options,
        )
        if postprocess_options.auto_brightness_options.local_contrast_strength > 0.0:
            if auto_adjust_opencv_dependencies is not None:
                cv2_module, _opencv_np_module = auto_adjust_opencv_dependencies
                del _opencv_np_module
            else:
                try:
                    import cv2 as cv2_module  # type: ignore
                except ModuleNotFoundError as exc:
                    raise RuntimeError("Missing required dependency: opencv-python") from exc
            image_bgr_uint16 = cv2_module.cvtColor(image_rgb_uint16, cv2_module.COLOR_RGB2BGR)
            image_bgr_uint16 = _apply_mild_local_contrast_bgr_uint16(
                cv2_module=cv2_module,
                np_module=np_module,
                image_bgr_uint16=image_bgr_uint16,
                options=postprocess_options.auto_brightness_options,
            )
            image_rgb_uint16 = cv2_module.cvtColor(image_bgr_uint16, cv2_module.COLOR_BGR2RGB)
    if postprocess_options.auto_levels_enabled:
        image_rgb_uint16 = _apply_auto_levels_uint16(
            np_module=np_module,
            image_rgb_uint16=image_rgb_uint16,
            auto_levels_options=postprocess_options.auto_levels_options,
        )

    image_rgb_uint16 = _apply_static_postprocess_uint16(
        np_module=np_module,
        image_rgb_uint16=image_rgb_uint16,
        postprocess_options=postprocess_options,
    )

    if postprocess_options.auto_adjust_mode is not None:
        with tempfile.TemporaryDirectory(
            prefix="dng2jpg-auto-adjust-"
        ) as auto_adjust_temp_dir_raw:
            auto_adjust_temp_dir = Path(auto_adjust_temp_dir_raw)
            postprocessed_input = auto_adjust_temp_dir / "postprocessed_input.tif"
            auto_adjust_output = auto_adjust_temp_dir / "auto_adjust_output.tif"
            imageio_module.imwrite(str(postprocessed_input), image_rgb_uint16)
            if postprocess_options.auto_adjust_mode == "ImageMagick":
                if imagemagick_command is None:
                    imagemagick_command = _resolve_imagemagick_command()
                if imagemagick_command is None:
                    raise RuntimeError(
                        "Missing required dependency: ImageMagick executable (magick or convert)"
                    )
                _apply_validated_auto_adjust_pipeline(
                    postprocessed_input=postprocessed_input,
                    auto_adjust_output=auto_adjust_output,
                    imagemagick_command=imagemagick_command,
                    auto_adjust_options=postprocess_options.auto_adjust_options,
                )
            elif postprocess_options.auto_adjust_mode == "OpenCV":
                if auto_adjust_opencv_dependencies is None:
                    raise RuntimeError(
                        "Missing required dependencies: opencv-python and numpy"
                    )
                cv2_module, np_module = auto_adjust_opencv_dependencies
                _apply_validated_auto_adjust_pipeline_opencv(
                    input_file=postprocessed_input,
                    output_file=auto_adjust_output,
                    cv2_module=cv2_module,
                    np_module=np_module,
                    auto_adjust_options=postprocess_options.auto_adjust_options,
                )
            else:
                raise RuntimeError(
                    f"Unsupported auto-adjust mode: {postprocess_options.auto_adjust_mode}"
                )
            image_rgb_uint16 = _normalize_uint16_rgb_image(
                np_module=np_module,
                image_data=imageio_module.imread(str(auto_adjust_output)),
            )

    image_rgb_uint8 = _to_uint8_image_array(np_module=np_module, image_data=image_rgb_uint16)
    pil_image = pil_image_module.fromarray(image_rgb_uint8)
    if getattr(pil_image, "mode", "") != "RGB":
        pil_image = pil_image.convert("RGB")

    save_kwargs = {
        "format": "JPEG",
        "quality": _convert_compression_to_quality(postprocess_options.jpg_compression),
        "optimize": True,
    }
    if source_exif_payload is not None:
        save_kwargs["exif"] = source_exif_payload
    pil_image.save(str(output_jpg), **save_kwargs)
    if source_exif_payload is not None:
        if piexif_module is None:
            raise RuntimeError("Missing required dependency: piexif")
        _refresh_output_jpg_exif_thumbnail_after_save(
            pil_image_module=pil_image_module,
            piexif_module=piexif_module,
            output_jpg=output_jpg,
            source_exif_payload=source_exif_payload,
            source_orientation=source_orientation,
        )


def _collect_processing_errors(rawpy_module):
    """@brief Build deterministic tuple of recoverable processing exceptions.

    @details Combines common IO/value/subprocess errors with rawpy-specific
    decoding error classes when present in runtime module version.
    @param rawpy_module {ModuleType} Imported rawpy module.
    @return {tuple[type[BaseException], ...]} Ordered deduplicated exception class tuple.
    @satisfies REQ-059
    """

    classes = [OSError, ValueError, RuntimeError, subprocess.CalledProcessError]
    for class_name in (
        "LibRawError",
        "LibRawFileUnsupportedError",
        "LibRawIOError",
        "LibRawFatalError",
        "LibRawNonFatalError",
    ):
        candidate = getattr(rawpy_module, class_name, None)
        if isinstance(candidate, type):
            classes.append(candidate)

    deduplicated = []
    for class_type in classes:
        if class_type not in deduplicated:
            deduplicated.append(class_type)
    return tuple(deduplicated)


def _is_supported_runtime_os():
    """@brief Validate runtime platform support for `dng2jpg`.

    @details Accepts Linux runtime only; emits explicit non-Linux unsupported
    message that includes OS label (`Windows` or `MacOS`) for deterministic UX.
    @return {bool} `True` when runtime OS is Linux; `False` otherwise.
    @satisfies REQ-055, REQ-059
    """

    runtime_os = get_runtime_os()
    if runtime_os == "linux":
        return True

    runtime_label = _RUNTIME_OS_LABELS.get(runtime_os, runtime_os)
    print_error(
        f"dng2jpg is not available on {runtime_label}; this command is Linux-only."
    )
    return False


def run(args):
    """@brief Execute `dng2jpg` command pipeline.

    @details Parses command options, validates dependencies, detects source DNG
    bits-per-color from RAW metadata, resolves manual or automatic EV-zero center,
    resolves static or adaptive EV selector around resolved center using
    bit-derived EV ceilings, extracts three RAW brackets, executes selected
    `enfuse`, selected luminance-hdr-cli, selected OpenCV Mertens+Debevec, or
    selected HDR+ tile merge flow, writes JPG output, and guarantees temporary
    artifact cleanup through isolated temporary directory lifecycle.
    @param args {list[str]} Command argument vector excluding command token.
    @return {int} `0` on success; `1` on parse/validation/dependency/processing failure.
    @satisfies REQ-055, REQ-056, REQ-057, REQ-058, REQ-059, REQ-060, REQ-061, REQ-062, REQ-064, REQ-065, REQ-066, REQ-067, REQ-068, REQ-069, REQ-071, REQ-072, REQ-073, REQ-074, REQ-075, REQ-077, REQ-078, REQ-079, REQ-080, REQ-081, REQ-088, REQ-089, REQ-090, REQ-091, REQ-092, REQ-093, REQ-094, REQ-095, REQ-096, REQ-097, REQ-098, REQ-100, REQ-101, REQ-102, REQ-107, REQ-108, REQ-109, REQ-110, REQ-111, REQ-112, REQ-113, REQ-114, REQ-115
    """

    if not _is_supported_runtime_os():
        return 1

    parsed = _parse_run_options(args)
    if parsed is None:
        return 1

    (
        input_dng,
        output_jpg,
        ev_value,
        auto_ev_enabled,
        gamma_value,
        postprocess_options,
        enable_luminance,
        enable_opencv,
        luminance_options,
        opencv_merge_options,
        enable_hdr_plus,
        ev_zero,
        auto_zero_enabled,
        auto_zero_pct,
        auto_ev_pct,
    ) = parsed

    if input_dng.suffix.lower() != ".dng":
        print_error(f"Input file must have .dng extension: {input_dng}")
        return 1

    if not input_dng.exists() or not input_dng.is_file():
        print_error(f"Input DNG file not found: {input_dng}")
        return 1

    output_parent = output_jpg.parent
    if output_parent and not output_parent.exists():
        print_error(f"Output directory does not exist: {output_parent}")
        return 1

    if enable_luminance:
        if shutil.which("luminance-hdr-cli") is None:
            print_error("Missing required dependency: luminance-hdr-cli")
            return 1
    elif not enable_opencv and not enable_hdr_plus:
        if shutil.which("enfuse") is None:
            print_error("Missing required dependency: enfuse")
            return 1
    imagemagick_command = None
    auto_adjust_opencv_dependencies = None
    numpy_module = None
    if (
        postprocess_options.auto_brightness_enabled
        or postprocess_options.auto_levels_enabled
        or enable_hdr_plus
    ):
        numpy_module = _resolve_numpy_dependency()
        if numpy_module is None:
            return 1
    if postprocess_options.auto_adjust_mode == "OpenCV" or enable_opencv:
        auto_adjust_opencv_dependencies = _resolve_auto_adjust_opencv_dependencies()
        if auto_adjust_opencv_dependencies is None:
            return 1
    if postprocess_options.auto_adjust_mode == "ImageMagick":
        imagemagick_command = _resolve_imagemagick_command()
        if imagemagick_command is None:
            print_error(
                "Missing required dependency: ImageMagick executable (magick or convert)"
            )
            return 1

    dependencies = _load_image_dependencies()
    if dependencies is None:
        return 1

    rawpy_module, imageio_module, pil_image_module = dependencies
    source_exif_payload, source_exif_timestamp, source_orientation = (
        _extract_dng_exif_payload_and_timestamp(
            pil_image_module=pil_image_module,
            input_dng=input_dng,
        )
    )
    piexif_module = None
    if source_exif_payload is not None:
        piexif_module = _load_piexif_dependency()
        if piexif_module is None:
            return 1
    print_info(f"Reading DNG input: {input_dng}")
    print_info(f"Using gamma pair: {gamma_value[0]:g},{gamma_value[1]:g}")
    print_info(
        "Postprocess factors: "
        f"gamma={postprocess_options.post_gamma:g}, "
        f"brightness={postprocess_options.brightness:g}, "
        f"contrast={postprocess_options.contrast:g}, "
        f"saturation={postprocess_options.saturation:g}, "
        f"jpg-compression={postprocess_options.jpg_compression}, "
        f"auto-brightness={'enabled' if postprocess_options.auto_brightness_enabled else 'disabled'}, "
        f"auto-levels={'enabled' if postprocess_options.auto_levels_enabled else 'disabled'}, "
        f"auto-adjust={postprocess_options.auto_adjust_mode or 'disabled'}"
    )
    if postprocess_options.auto_brightness_enabled:
        resolved_ab_key = postprocess_options.auto_brightness_options.key_value
        if resolved_ab_key is None:
            resolved_ab_key = "auto"
        print_info(
            "Auto-brightness knobs: "
            f"key-value={resolved_ab_key}, "
            f"white-point-pct={postprocess_options.auto_brightness_options.white_point_percentile:g}, "
            f"key-min={postprocess_options.auto_brightness_options.key_min:g}, "
            f"key-max={postprocess_options.auto_brightness_options.key_max:g}, "
            f"max-auto-boost={postprocess_options.auto_brightness_options.max_auto_boost_factor:g}, "
            f"local-contrast-strength={postprocess_options.auto_brightness_options.local_contrast_strength:g}, "
            f"clahe-clip-limit={postprocess_options.auto_brightness_options.clahe_clip_limit:g}"
        )
    if postprocess_options.auto_levels_enabled:
        print_info(
            "Auto-levels knobs: "
            f"clip-pct={postprocess_options.auto_levels_options.clip_percent:g}, "
            "clip-out-of-gamut="
            f"{'enabled' if postprocess_options.auto_levels_options.clip_out_of_gamut else 'disabled'}, "
            f"highlight-reconstruction="
            f"{'enabled' if postprocess_options.auto_levels_options.highlight_reconstruction_enabled else 'disabled'}, "
            "highlight-reconstruction-method="
            f"{postprocess_options.auto_levels_options.highlight_reconstruction_method}, "
            f"gain-threshold={postprocess_options.auto_levels_options.gain_threshold:g}"
        )
    if enable_luminance:
        extra_args_text = ""
        if luminance_options.tmo_extra_args:
            extra_args_text = (
                f", tmoExtraArgs=[{' '.join(luminance_options.tmo_extra_args)}]"
            )
        print_info(
            "HDR backend: luminance-hdr-cli "
            f"(hdrModel={luminance_options.hdr_model}, "
            f"hdrWeight={luminance_options.hdr_weight}, "
            f"hdrResponseCurve={luminance_options.hdr_response_curve}, "
            f"tmo={luminance_options.tmo}{extra_args_text})"
        )
    elif enable_opencv:
        print_info(
            "HDR backend: OpenCV "
            f"(merge=Mertens+Debevec, debevecWhitePointPct={opencv_merge_options.debevec_white_point_percentile:g})"
        )
    elif enable_hdr_plus:
        print_info(
            "HDR backend: HDR+ "
            "(reference=ev_zero, temporal=tile L1 inverse-distance, spatial=raised-cosine)"
        )
    else:
        print_info("HDR backend: enfuse")

    processing_errors = _collect_processing_errors(rawpy_module)

    with tempfile.TemporaryDirectory(prefix="dng2jpg-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        merged_tiff = temp_dir / "merged_hdr.tif"

        try:
            with rawpy_module.imread(str(input_dng)) as raw_handle:
                bits_per_color = _detect_dng_bits_per_color(raw_handle)
                base_max_ev = _calculate_max_ev_from_bits(bits_per_color)
                preview_luminance_stats = None
                if auto_zero_enabled or auto_ev_enabled:
                    preview_luminance_stats = _extract_normalized_preview_luminance_stats(
                        raw_handle
                    )
                auto_zero_supported_values = _derive_supported_ev_zero_values(base_max_ev)
                resolved_ev_zero = _resolve_ev_zero(
                    raw_handle=raw_handle,
                    ev_zero=ev_zero,
                    auto_zero_enabled=auto_zero_enabled,
                    auto_zero_pct=auto_zero_pct,
                    base_max_ev=base_max_ev,
                    supported_ev_values_for_auto_zero=auto_zero_supported_values,
                    preview_luminance_stats=preview_luminance_stats,
                )
                supported_ev_values = _derive_supported_ev_values(
                    bits_per_color, ev_zero=resolved_ev_zero
                )
                max_bracket = supported_ev_values[-1]
                print_info(f"Detected DNG bits per color: {bits_per_color}")
                if auto_zero_enabled:
                    print_info("Using EV center mode: auto-zero")
                else:
                    print_info("Using EV center mode: manual")
                print_info(f"Using EV center (ev_zero): {resolved_ev_zero:g}")
                if auto_ev_enabled or auto_zero_enabled:
                    safe_zero_max = _calculate_safe_ev_zero_max(base_max_ev)
                    print_info(
                        "Bit-derived EV ceilings: "
                        f"BASE_MAX={base_max_ev:g} (formula: (bits_per_color-8)/2), "
                        f"SAFE_ZERO_MAX={safe_zero_max:g} "
                        "(formula: BASE_MAX-1), "
                        f"MAX_BRACKET={max_bracket:g} "
                        "(formula: BASE_MAX-abs(ev_zero))"
                    )
                effective_ev_value = _resolve_ev_value(
                    raw_handle=raw_handle,
                    ev_value=ev_value,
                    auto_ev_enabled=auto_ev_enabled,
                    auto_ev_pct=auto_ev_pct,
                    supported_ev_values=supported_ev_values,
                    ev_zero=resolved_ev_zero,
                    preview_luminance_stats=preview_luminance_stats,
                )
                print_info(
                    f"Using EV bracket delta: {effective_ev_value:g}"
                    + (" (adaptive)" if auto_ev_enabled else " (static)")
                )
                print_info(
                    "Export EV triplet: "
                    f"{(resolved_ev_zero-effective_ev_value):g}, {resolved_ev_zero:g}, {(resolved_ev_zero+effective_ev_value):g}"
                )
                multipliers = _build_exposure_multipliers(
                    effective_ev_value, ev_zero=resolved_ev_zero
                )
                bracket_paths = _write_bracket_images(
                    raw_handle=raw_handle,
                    imageio_module=imageio_module,
                    multipliers=multipliers,
                    gamma_value=gamma_value,
                    temp_dir=temp_dir,
                )
            if enable_luminance:
                _run_luminance_hdr_cli(
                    bracket_paths=bracket_paths,
                    output_hdr_tiff=merged_tiff,
                    ev_value=effective_ev_value,
                    ev_zero=resolved_ev_zero,
                    luminance_options=luminance_options,
                )
            elif enable_opencv:
                _run_opencv_hdr_merge(
                    bracket_paths=bracket_paths,
                    output_hdr_tiff=merged_tiff,
                    ev_value=effective_ev_value,
                    ev_zero=resolved_ev_zero,
                    opencv_merge_options=opencv_merge_options,
                    auto_adjust_opencv_dependencies=auto_adjust_opencv_dependencies,
                )
            elif enable_hdr_plus:
                if numpy_module is None:
                    raise RuntimeError("Missing required dependency: numpy")
                _run_hdr_plus_merge(
                    bracket_paths=bracket_paths,
                    output_hdr_tiff=merged_tiff,
                    imageio_module=imageio_module,
                    np_module=numpy_module,
                )
            else:
                _run_enfuse(bracket_paths=bracket_paths, merged_tiff=merged_tiff)
            _encode_jpg(
                imageio_module=imageio_module,
                pil_image_module=pil_image_module,
                merged_tiff=merged_tiff,
                output_jpg=output_jpg,
                postprocess_options=postprocess_options,
                imagemagick_command=imagemagick_command,
                auto_adjust_opencv_dependencies=auto_adjust_opencv_dependencies,
                numpy_module=numpy_module,
                piexif_module=piexif_module,
                source_exif_payload=source_exif_payload,
                source_orientation=source_orientation,
                ev_zero=resolved_ev_zero,
            )
            _sync_output_file_timestamps_from_exif(
                output_jpg=output_jpg,
                exif_timestamp=source_exif_timestamp,
            )
        except processing_errors as error:
            print_error(f"dng2jpg processing failed: {error}")
            return 1

    print_success(f"HDR JPG created: {output_jpg}")
    return 0
