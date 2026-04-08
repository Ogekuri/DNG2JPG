#!/usr/bin/env python3
"""@brief Convert one DNG file into one HDR-merged JPG output.

@details Implements single-pass neutral linear RAW extraction with one
maximum-resolution RGB base image, applies normalized camera white-balance
gains in float domain, derives three synthetic exposures (`ev_zero-ev`,
`ev_zero`, `ev_zero+ev`) by NumPy EV scaling, emits one
diagnostic source-gamma line from RAW metadata without feeding it into the
numeric pipeline, merges through selected `luminance-hdr-cli`, selected OpenCV
(`Debevec`, `Robertson`, `Mertens`), or selected HDR+ tile-based flow with
deterministic parameters, then writes final JPG to user-selected output path.
Temporary workspace artifacts are isolated in a temporary directory and
removed automatically on success and failure, while optional debug checkpoints
persist in the output directory when `--debug` is enabled.
    @satisfies PRJ-001, PRJ-002, DES-003, DES-008, DES-009, REQ-008, REQ-009, REQ-010, REQ-012, REQ-013, REQ-014, REQ-018, REQ-020, REQ-032, REQ-034, REQ-037, REQ-041, REQ-052, REQ-100, REQ-106, REQ-108, REQ-109, REQ-110, REQ-111, REQ-112, REQ-113, REQ-114, REQ-115, REQ-141, REQ-142, REQ-143, REQ-144, REQ-145, REQ-146, REQ-148, REQ-149, REQ-152, REQ-153, REQ-154, REQ-157, REQ-158, REQ-159, REQ-160, REQ-163, REQ-164, REQ-165
"""

import inspect
import os
import shlex
import shutil
import subprocess
import tempfile
import textwrap
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
DESCRIPTION = (
    "Convert DNG to HDR-merged JPG with luminance-hdr-cli, OpenCV, or HDR+ backend."
)
DEFAULT_POST_GAMMA = 1.0
DEFAULT_POST_GAMMA_MODE = "numeric"
DEFAULT_POST_GAMMA_AUTO_TARGET_GRAY = 0.5
DEFAULT_POST_GAMMA_AUTO_LUMA_MIN = 0.01
DEFAULT_POST_GAMMA_AUTO_LUMA_MAX = 0.99
DEFAULT_POST_GAMMA_AUTO_LUT_SIZE = 256
DEFAULT_BRIGHTNESS = 1.0
DEFAULT_CONTRAST = 1.0
DEFAULT_SATURATION = 1.0
DEFAULT_JPG_COMPRESSION = 15
DEFAULT_AUTO_EV_SHADOW_CLIPPING = 20.0
DEFAULT_AUTO_EV_HIGHLIGHT_CLIPPING = 20.0
DEFAULT_AUTO_EV_STEP = 0.1
DEFAULT_AA_BLUR_SIGMA = 0.9
DEFAULT_AA_BLUR_THRESHOLD_PCT = 5.0
DEFAULT_AA_LEVEL_LOW_PCT = 0.1
DEFAULT_AA_LEVEL_HIGH_PCT = 99.9
DEFAULT_AA_ENABLE_LOCAL_CONTRAST = True
DEFAULT_AA_LOCAL_CONTRAST_STRENGTH = 0.20
DEFAULT_AA_CLAHE_CLIP_LIMIT = 1.6
DEFAULT_AA_CLAHE_TILE_GRID_SIZE = (8, 8)
DEFAULT_AA_SIGMOID_CONTRAST = 1.8
DEFAULT_AA_SIGMOID_MIDPOINT = 0.5
DEFAULT_AA_SATURATION_GAMMA = 0.8
DEFAULT_AA_HIGHPASS_BLUR_SIGMA = 2.0
DEFAULT_AB_KEY_VALUE = None
DEFAULT_AB_WHITE_POINT_PERCENTILE = 99.8
DEFAULT_AB_A_MIN = 0.045
DEFAULT_AB_A_MAX = 0.72
DEFAULT_AB_MAX_AUTO_BOOST_FACTOR = 1.25
DEFAULT_AB_ENABLE_LUMINANCE_PRESERVING_DESAT = True
DEFAULT_AB_EPS = 1e-6
DEFAULT_AB_LOW_KEY_VALUE = 0.09
DEFAULT_AB_NORMAL_KEY_VALUE = 0.18
DEFAULT_AB_HIGH_KEY_VALUE = 0.36
DEFAULT_AL_CLIP_PERCENT = 0.02
DEFAULT_AL_CLIP_OUT_OF_GAMUT = True
DEFAULT_AL_GAIN_THRESHOLD = 1.0
DEFAULT_AL_HISTCOMPR = 3
_AUTO_LEVELS_CODE_BIN_COUNT = 1 << 16
_AUTO_LEVELS_CODE_MAX = float(_AUTO_LEVELS_CODE_BIN_COUNT - 1)
_AUTO_LEVELS_RT_MIDGRAY = 0.1842
_AUTO_LEVELS_RT_CURVE_MIN_POLY_POINTS = 1000
_AUTO_LEVELS_LUMINANCE_WEIGHTS = (
    0.2126729,
    0.7151521,
    0.0721750,
)
_AUTO_LEVELS_TONECURVE_LUMINANCE_WEIGHTS = (
    0.299,
    0.587,
    0.114,
)
_AUTO_LEVELS_BLEND_CLIP_THRESHOLD = 0.95
_AUTO_LEVELS_BLEND_FIX_THRESHOLD = 0.5
_AUTO_LEVELS_BLEND_SATURATION_THRESHOLD = 0.5
_AUTO_LEVELS_COLOR_PROPAGATION_DARK_FLOOR = 0.25
_AUTO_LEVELS_INPAINT_GAIN_MULTIPLIER = 1.2
_AUTO_LEVELS_INPAINT_CLIP_RATIO = 0.987
_AUTO_LEVELS_HIGHLIGHT_METHODS = (
    "Luminance Recovery",
    "CIELab Blending",
    "Blend",
    "Color Propagation",
    "Inpaint Opposed",
)
DEFAULT_LUMINANCE_HDR_MODEL = "debevec"
DEFAULT_LUMINANCE_HDR_WEIGHT = "flat"
DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE = "linear"
DEFAULT_LUMINANCE_TMO = "mantiuk08"
DEFAULT_AUTO_ADJUST_ENABLED = True
HDR_MERGE_MODE_LUMINANCE = "Luminace-HDR"
HDR_MERGE_MODE_OPENCV_MERGE = "OpenCV-Merge"
HDR_MERGE_MODE_OPENCV_TONEMAP = "OpenCV-Tonemap"
HDR_MERGE_MODE_HDR_PLUS = "HDR-Plus"
WHITE_BALANCE_MODE_SIMPLE = "Simple"
WHITE_BALANCE_MODE_GRAYWORLD = "GrayworldWB"
WHITE_BALANCE_MODE_IA = "IA"
WHITE_BALANCE_MODE_COLOR_CONSTANCY = "ColorConstancy"
WHITE_BALANCE_MODE_TTL = "TTL"
RAW_WHITE_BALANCE_MODE_GREEN = "GREEN"
RAW_WHITE_BALANCE_MODE_MAX = "MAX"
RAW_WHITE_BALANCE_MODE_MIN = "MIN"
RAW_WHITE_BALANCE_MODE_MEAN = "MEAN"
DEFAULT_RAW_WHITE_BALANCE_MODE = RAW_WHITE_BALANCE_MODE_MEAN
WHITE_BALANCE_ANALYSIS_SOURCE_EV_ZERO = "ev-zero"
WHITE_BALANCE_ANALYSIS_SOURCE_LINEAR_BASE = "linear-base"
OPENCV_TONEMAP_MAP_DRAGO = "drago"
OPENCV_TONEMAP_MAP_REINHARD = "reinhard"
OPENCV_TONEMAP_MAP_MANTIUK = "mantiuk"
OPENCV_MERGE_ALGORITHM_DEBEVEC = "Debevec"
OPENCV_MERGE_ALGORITHM_ROBERTSON = "Robertson"
OPENCV_MERGE_ALGORITHM_MERTENS = "Mertens"
DEFAULT_REINHARD02_POST_GAMMA = 0.9
DEFAULT_REINHARD02_BRIGHTNESS = 1.3
DEFAULT_REINHARD02_CONTRAST = 0.75
DEFAULT_REINHARD02_SATURATION = 0.7
DEFAULT_MANTIUK08_POST_GAMMA = 0.8
DEFAULT_MANTIUK08_BRIGHTNESS = 0.8
DEFAULT_MANTIUK08_CONTRAST = 1.1
DEFAULT_MANTIUK08_SATURATION = 1.05
DEFAULT_HDRPLUS_POST_GAMMA = 0.8
DEFAULT_HDRPLUS_BRIGHTNESS = 0.9
DEFAULT_HDRPLUS_CONTRAST = 1.0
DEFAULT_HDRPLUS_SATURATION = 1.0
DEFAULT_OPENCV_DEBEVEC_POST_GAMMA = 1.0
DEFAULT_OPENCV_DEBEVEC_BRIGHTNESS = 1.0
DEFAULT_OPENCV_DEBEVEC_CONTRAST = 1.5
DEFAULT_OPENCV_DEBEVEC_SATURATION = 1.05
DEFAULT_OPENCV_DEBEVEC_TONEMAP_GAMMA = 1.0
DEFAULT_OPENCV_ROBERTSON_POST_GAMMA = 1.0
DEFAULT_OPENCV_ROBERTSON_BRIGHTNESS = 1.0
DEFAULT_OPENCV_ROBERTSON_CONTRAST = 1.4
DEFAULT_OPENCV_ROBERTSON_SATURATION = 1.05
DEFAULT_OPENCV_ROBERTSON_TONEMAP_GAMMA = 0.9
DEFAULT_OPENCV_MERTENS_POST_GAMMA = 1.0
DEFAULT_OPENCV_MERTENS_BRIGHTNESS = 0.9
DEFAULT_OPENCV_MERTENS_CONTRAST = 1.3
DEFAULT_OPENCV_MERTENS_SATURATION = 1.1
DEFAULT_OPENCV_MERTENS_TONEMAP_GAMMA = 0.8
DEFAULT_OPENCV_POST_GAMMA = DEFAULT_OPENCV_ROBERTSON_POST_GAMMA
DEFAULT_OPENCV_BRIGHTNESS = DEFAULT_OPENCV_ROBERTSON_BRIGHTNESS
DEFAULT_OPENCV_CONTRAST = DEFAULT_OPENCV_ROBERTSON_CONTRAST
DEFAULT_OPENCV_SATURATION = DEFAULT_OPENCV_ROBERTSON_SATURATION
DEFAULT_OPENCV_MERGE_ALGORITHM = OPENCV_MERGE_ALGORITHM_ROBERTSON
DEFAULT_OPENCV_TONEMAP_ENABLED = True
DEFAULT_OPENCV_TONEMAP_GAMMA = DEFAULT_OPENCV_ROBERTSON_TONEMAP_GAMMA
DEFAULT_OPENCV_TONEMAP_DRAGO_SATURATION = 1.0
DEFAULT_OPENCV_TONEMAP_DRAGO_BIAS = 0.85
DEFAULT_OPENCV_TONEMAP_REINHARD_INTENSITY = 0.0
DEFAULT_OPENCV_TONEMAP_REINHARD_LIGHT_ADAPT = 0.0
DEFAULT_OPENCV_TONEMAP_REINHARD_COLOR_ADAPT = 0.0
DEFAULT_OPENCV_TONEMAP_MANTIUK_SCALE = 0.7
DEFAULT_OPENCV_TONEMAP_MANTIUK_SATURATION = 1.0
DEFAULT_HDRPLUS_PROXY_MODE = "rggb"
DEFAULT_HDRPLUS_SEARCH_RADIUS = 4
DEFAULT_HDRPLUS_TEMPORAL_FACTOR = 8.0
DEFAULT_HDRPLUS_TEMPORAL_MIN_DIST = 10.0
DEFAULT_HDRPLUS_TEMPORAL_MAX_DIST = 300.0
HDRPLUS_TILE_SIZE = 32
HDRPLUS_TILE_STRIDE = HDRPLUS_TILE_SIZE // 2
HDRPLUS_DOWNSAMPLED_TILE_SIZE = HDRPLUS_TILE_STRIDE
HDRPLUS_ALIGNMENT_LEVELS = 3
HDRPLUS_ALIGNMENT_DOWNSAMPLE_RATE = 4
HDRPLUS_TEMPORAL_FACTOR = DEFAULT_HDRPLUS_TEMPORAL_FACTOR
HDRPLUS_TEMPORAL_MIN_DIST = DEFAULT_HDRPLUS_TEMPORAL_MIN_DIST
HDRPLUS_TEMPORAL_MAX_DIST = DEFAULT_HDRPLUS_TEMPORAL_MAX_DIST
_HDRPLUS_PROXY_MODES = ("rggb", "bt709", "mean")
MIN_SUPPORTED_BITS_PER_COLOR = 9
_EV_SELECTION_EPS = 1e-9
_RUNTIME_OS_LABELS = {
    "windows": "Windows",
    "darwin": "MacOS",
}
_EXIF_TAG_ORIENTATION = 274
_EXIF_TAG_DATETIME = 306
_EXIF_TAG_DATETIME_ORIGINAL = 36867
_EXIF_TAG_DATETIME_DIGITIZED = 36868
_EXIF_TAG_EXPOSURE_TIME = 33434
_EXIF_IFD_POINTER = 34665
_EXIF_VALID_ORIENTATIONS = (1, 2, 3, 4, 5, 6, 7, 8)
_THUMBNAIL_MAX_SIZE = (256, 256)
_AUTO_ADJUST_KNOB_OPTIONS = (
    "--aa-blur-sigma",
    "--aa-blur-threshold-pct",
    "--aa-level-low-pct",
    "--aa-level-high-pct",
    "--aa-enable-local-contrast",
    "--aa-local-contrast-strength",
    "--aa-clahe-clip-limit",
    "--aa-clahe-tile-grid-size",
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
    "--ab-enable-luminance-preserving-desat",
    "--ab-eps",
)
_POST_GAMMA_AUTO_KNOB_OPTIONS = (
    "--post-gamma-auto-target-gray",
    "--post-gamma-auto-luma-min",
    "--post-gamma-auto-luma-max",
    "--post-gamma-auto-lut-size",
)
_HDRPLUS_KNOB_OPTIONS = (
    "--hdrplus-proxy-mode",
    "--hdrplus-search-radius",
    "--hdrplus-temporal-factor",
    "--hdrplus-temporal-min-dist",
    "--hdrplus-temporal-max-dist",
)
_OPENCV_KNOB_OPTIONS = (
    "--opencv-merge-algorithm",
    "--opencv-tonemap",
    "--opencv-tonemap-gamma",
)
_OPENCV_TONEMAP_SELECTOR_OPTIONS = (
    "--tonemap-drago",
    "--tonemap-reinhard",
    "--tonemap-mantiuk",
)
_OPENCV_TONEMAP_KNOB_OPTIONS = (
    "--tonemap-drago-saturation",
    "--tonemap-drago-bias",
    "--tonemap-reinhard-intensity",
    "--tonemap-reinhard-light_adapt",
    "--tonemap-reinhard-color_adapt",
    "--tonemap-mantiuk-scale",
    "--tonemap-mantiuk-saturation",
)
_HDR_MERGE_MODES = (
    HDR_MERGE_MODE_LUMINANCE,
    HDR_MERGE_MODE_OPENCV_MERGE,
    HDR_MERGE_MODE_OPENCV_TONEMAP,
    HDR_MERGE_MODE_HDR_PLUS,
)
_OPENCV_TONEMAP_MAPS = (
    OPENCV_TONEMAP_MAP_DRAGO,
    OPENCV_TONEMAP_MAP_REINHARD,
    OPENCV_TONEMAP_MAP_MANTIUK,
)
_WHITE_BALANCE_MODES = (
    WHITE_BALANCE_MODE_SIMPLE,
    WHITE_BALANCE_MODE_GRAYWORLD,
    WHITE_BALANCE_MODE_IA,
    WHITE_BALANCE_MODE_COLOR_CONSTANCY,
    WHITE_BALANCE_MODE_TTL,
)
_WHITE_BALANCE_ANALYSIS_SOURCES = (
    WHITE_BALANCE_ANALYSIS_SOURCE_EV_ZERO,
    WHITE_BALANCE_ANALYSIS_SOURCE_LINEAR_BASE,
)
_RAW_WHITE_BALANCE_MODES = (
    RAW_WHITE_BALANCE_MODE_GREEN,
    RAW_WHITE_BALANCE_MODE_MAX,
    RAW_WHITE_BALANCE_MODE_MIN,
    RAW_WHITE_BALANCE_MODE_MEAN,
)
_OPENCV_MERGE_ALGORITHMS = (
    OPENCV_MERGE_ALGORITHM_DEBEVEC,
    OPENCV_MERGE_ALGORITHM_ROBERTSON,
    OPENCV_MERGE_ALGORITHM_MERTENS,
)
_AUTO_LEVELS_KNOB_OPTIONS = (
    "--al-clip-pct",
    "--al-clip-out-of-gamut",
    "--al-highlight-reconstruction",
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
    """@brief Hold validated knob values for the sole auto-adjust pipeline.

    @details Encapsulates selective-blur, adaptive-level, CLAHE-luma,
    sigmoidal-contrast, vibrance, and high-pass controls consumed by the single
    float-domain auto-adjust implementation.
    @param blur_sigma {float} Selective blur Gaussian sigma (`> 0`).
    @param blur_threshold_pct {float} Selective blur threshold percentage in `[0, 100]`.
    @param level_low_pct {float} Low percentile for level normalization in `[0, 100]`.
    @param level_high_pct {float} High percentile for level normalization in `[0, 100]`.
    @param enable_local_contrast {bool} `True` enables CLAHE-luma stage in the auto-adjust pipeline.
    @param local_contrast_strength {float} CLAHE-luma blend factor in `[0, 1]`.
    @param clahe_clip_limit {float} CLAHE clip limit in `(0, +inf)`.
    @param clahe_tile_grid_size {tuple[int, int]} CLAHE tile grid size `(rows, cols)`, each `>=1`.
    @param sigmoid_contrast {float} Sigmoidal contrast slope (`> 0`).
    @param sigmoid_midpoint {float} Sigmoidal contrast midpoint in `[0, 1]`.
    @param saturation_gamma {float} HSL saturation gamma denominator (`> 0`).
    @param highpass_blur_sigma {float} High-pass Gaussian blur sigma (`> 0`).
    @return {None} Immutable dataclass container.
    @satisfies REQ-051, REQ-073, REQ-075, REQ-082, REQ-083, REQ-084, REQ-086, REQ-087, REQ-123, REQ-125, REQ-136, REQ-137
    """

    blur_sigma: float = DEFAULT_AA_BLUR_SIGMA
    blur_threshold_pct: float = DEFAULT_AA_BLUR_THRESHOLD_PCT
    level_low_pct: float = DEFAULT_AA_LEVEL_LOW_PCT
    level_high_pct: float = DEFAULT_AA_LEVEL_HIGH_PCT
    enable_local_contrast: bool = DEFAULT_AA_ENABLE_LOCAL_CONTRAST
    local_contrast_strength: float = DEFAULT_AA_LOCAL_CONTRAST_STRENGTH
    clahe_clip_limit: float = DEFAULT_AA_CLAHE_CLIP_LIMIT
    clahe_tile_grid_size: tuple[int, int] = DEFAULT_AA_CLAHE_TILE_GRID_SIZE
    sigmoid_contrast: float = DEFAULT_AA_SIGMOID_CONTRAST
    sigmoid_midpoint: float = DEFAULT_AA_SIGMOID_MIDPOINT
    saturation_gamma: float = DEFAULT_AA_SATURATION_GAMMA
    highpass_blur_sigma: float = DEFAULT_AA_HIGHPASS_BLUR_SIGMA


@dataclass(frozen=True)
class AutoBrightnessOptions:
    """@brief Hold `--auto-brightness` knob values.

    @details Encapsulates parameters for the 16-bit BT.709 photographic
    tonemap pipeline: key-classification, key-value selection, robust white
    point, optional luminance-preserving anti-clipping desaturation, and
    numerical stability control for float-domain luminance processing.
    @param key_value {float|None} Manual Reinhard key value override in `(0, +inf)`; `None` enables automatic key selection.
    @param white_point_percentile {float} Percentile in `(0, 100)` used to derive robust `Lwhite`.
    @param a_min {float} Minimum allowed automatic key value clamp in `(0, +inf)`.
    @param a_max {float} Maximum allowed automatic key value clamp in `(0, +inf)`.
    @param max_auto_boost_factor {float} Multiplicative adjustment factor for automatic key adaptation in `(0, +inf)`.
    @param enable_luminance_preserving_desat {bool} `True` enables minimal grayscale blending for out-of-gamut linear RGB triplets.
    @param eps {float} Positive numerical stability guard used in divisions and logarithms.
    @return {None} Immutable dataclass container.
    @satisfies REQ-050, REQ-065, REQ-088, REQ-089, REQ-090, REQ-103, REQ-104, REQ-105, REQ-124, REQ-135
    """

    key_value: float | None = DEFAULT_AB_KEY_VALUE
    white_point_percentile: float = DEFAULT_AB_WHITE_POINT_PERCENTILE
    a_min: float = DEFAULT_AB_A_MIN
    a_max: float = DEFAULT_AB_A_MAX
    max_auto_boost_factor: float = DEFAULT_AB_MAX_AUTO_BOOST_FACTOR
    enable_luminance_preserving_desat: bool = (
        DEFAULT_AB_ENABLE_LUMINANCE_PRESERVING_DESAT
    )
    eps: float = DEFAULT_AB_EPS


@dataclass(frozen=True)
class AutoLevelsOptions:
    """@brief Hold `--auto-levels` knob values.

    @details Encapsulates validated histogram-based auto-levels controls ported
    from the attached RawTherapee-oriented source and adapted for normalized
    RGB float stage execution in the current post-merge pipeline.
    @param clip_percent {float} Histogram clipping percentage in `[0, +inf)`.
    @param clip_out_of_gamut {bool} `True` to normalize overflowing RGB triplets back into normalized gamut after tonal transform/reconstruction.
    @param histcompr {int} Histogram compression shift in `[0, 15]`.
    @param highlight_reconstruction_enabled {bool} `True` when highlight reconstruction is explicitly enabled.
    @param highlight_reconstruction_method {str} Highlight reconstruction method selector.
    @param gain_threshold {float} Inpaint Opposed gain threshold in `(0, +inf)`.
    @return {None} Immutable dataclass container.
    @satisfies REQ-100, REQ-101, REQ-102, REQ-116, REQ-120, REQ-165
    """

    clip_percent: float = DEFAULT_AL_CLIP_PERCENT
    clip_out_of_gamut: bool = DEFAULT_AL_CLIP_OUT_OF_GAMUT
    histcompr: int = DEFAULT_AL_HISTCOMPR
    highlight_reconstruction_enabled: bool = False
    highlight_reconstruction_method: str = "Inpaint Opposed"
    gain_threshold: float = DEFAULT_AL_GAIN_THRESHOLD


@dataclass(frozen=True)
class PostGammaAutoOptions:
    """@brief Hold `--post-gamma=auto` knob values.

    @details Encapsulates mean-luminance anchoring controls for the dedicated
    auto-gamma replacement stage in static postprocess execution.
    @param target_gray {float} Mid-gray anchor target in `(0,1)`.
    @param luma_min {float} Lower luminance guard in `(0,1)` for gamma solving.
    @param luma_max {float} Upper luminance guard in `(0,1)` for gamma solving.
    @param lut_size {int} Floating-point LUT size (`>=2`) for gamma mapping.
    @return {None} Immutable dataclass container.
    @satisfies REQ-177, REQ-179
    """

    target_gray: float = DEFAULT_POST_GAMMA_AUTO_TARGET_GRAY
    luma_min: float = DEFAULT_POST_GAMMA_AUTO_LUMA_MIN
    luma_max: float = DEFAULT_POST_GAMMA_AUTO_LUMA_MAX
    lut_size: int = DEFAULT_POST_GAMMA_AUTO_LUT_SIZE


@dataclass(frozen=True)
class MergeGammaOption:
    """@brief Hold requested merge-gamma CLI selector state.

    @details Encodes the user-facing `--gamma` request independently from the
    backend-resolved transfer so parsing stays deterministic and runtime can
    emit exact request diagnostics. `mode="auto"` selects EXIF/source-driven
    resolution. `mode="custom"` requires both custom parameters.
    @param mode {str} Canonical selector in `{"auto","custom"}`.
    @param linear_coeff {float|None} Custom linear-segment coefficient for Rec.709-style transfer.
    @param exponent {float|None} Custom exponent for Rec.709-style transfer.
    @return {None} Immutable dataclass container.
    @satisfies REQ-020
    """

    mode: str = "auto"
    linear_coeff: float | None = None
    exponent: float | None = None


@dataclass(frozen=True)
class ResolvedMergeGamma:
    """@brief Hold one resolved merge-output transfer function payload.

    @details Captures the backend-local transfer applied after OpenCV/HDR+
    merge normalization. `transfer` selects one implementation family:
    `linear`, `srgb`, `power`, or `rec709`. `param_a` and `param_b` carry
    transfer-specific numeric parameters for deterministic diagnostics and
    backend execution.
    @param request {MergeGammaOption} Original parsed user selector.
    @param transfer {str} Resolved transfer family identifier.
    @param label {str} Deterministic human-readable transfer label.
    @param param_a {float|None} First resolved transfer parameter when required.
    @param param_b {float|None} Second resolved transfer parameter when required.
    @param evidence {str} Resolution evidence token.
    @return {None} Immutable dataclass container.
    @satisfies REQ-169, REQ-170, REQ-171
    """

    request: MergeGammaOption
    transfer: str
    label: str
    param_a: float | None
    param_b: float | None
    evidence: str


@dataclass(frozen=True)
class ExifGammaTags:
    """@brief Hold EXIF tags relevant to auto merge-gamma resolution.

    @details Encapsulates normalized EXIF color-space, interoperability,
    image-model, and image-make tokens extracted from the source RAW/DNG
    container via `exifread` binary stream processing. The payload is consumed
    only by merge-gamma resolution and diagnostics and never mutates bracket
    extraction.
    @param color_space {str|None} Normalized EXIF `ColorSpace` token.
    @param interoperability_index {str|None} Normalized EXIF interoperability token.
    @param image_model {str|None} Normalized EXIF `Image Model` token.
    @param image_make {str|None} Normalized EXIF `Image Make` token.
    @return {None} Immutable dataclass container.
    @satisfies REQ-169, REQ-172, REQ-173
    """

    color_space: str | None
    interoperability_index: str | None
    image_model: str | None = None
    image_make: str | None = None


@dataclass(frozen=True)
class OpenCvTonemapOptions:
    """@brief Hold deterministic OpenCV-Tonemap backend option values.

    @details Encapsulates one mandatory OpenCV tone-map algorithm selector and
    optional algorithm-specific parameters for the `--hdr-merge=OpenCV-Tonemap`
    backend. The backend executes one selected algorithm only, uses fixed
    OpenCV tone-map `gamma=1.0` for linear-image processing, and applies merge
    gamma only as the backend-final step.
    @param tonemap_map {str} Selected OpenCV tone-map algorithm in `{"drago","reinhard","mantiuk"}`.
    @param drago_saturation {float} Drago saturation parameter.
    @param drago_bias {float} Drago bias parameter.
    @param reinhard_intensity {float} Reinhard intensity parameter.
    @param reinhard_light_adapt {float} Reinhard light adaptation parameter in `[0,1]`.
    @param reinhard_color_adapt {float} Reinhard color adaptation parameter in `[0,1]`.
    @param mantiuk_scale {float} Mantiuk scale parameter.
    @param mantiuk_saturation {float} Mantiuk saturation parameter.
    @return {None} Immutable dataclass container.
    @satisfies REQ-190, REQ-193, REQ-194, REQ-195, REQ-196, REQ-198
    """

    tonemap_map: str
    drago_saturation: float = DEFAULT_OPENCV_TONEMAP_DRAGO_SATURATION
    drago_bias: float = DEFAULT_OPENCV_TONEMAP_DRAGO_BIAS
    reinhard_intensity: float = DEFAULT_OPENCV_TONEMAP_REINHARD_INTENSITY
    reinhard_light_adapt: float = DEFAULT_OPENCV_TONEMAP_REINHARD_LIGHT_ADAPT
    reinhard_color_adapt: float = DEFAULT_OPENCV_TONEMAP_REINHARD_COLOR_ADAPT
    mantiuk_scale: float = DEFAULT_OPENCV_TONEMAP_MANTIUK_SCALE
    mantiuk_saturation: float = DEFAULT_OPENCV_TONEMAP_MANTIUK_SATURATION


@dataclass(frozen=True)
class PostprocessOptions:
    """@brief Hold deterministic postprocessing option values.

    @details Encapsulates correction factors and JPEG compression level used by
    shared TIFF-to-JPG postprocessing for both HDR backends, including
    `--post-gamma=auto` replacement-stage controls.
    @param post_gamma {float} Numeric gamma correction factor for static numeric mode.
    @param post_gamma_mode {str} Static gamma selector in `{"numeric","auto"}`.
    @param post_gamma_auto_options {PostGammaAutoOptions} Auto-gamma replacement stage knobs.
    @param brightness {float} Brightness enhancement factor.
    @param contrast {float} Contrast enhancement factor.
    @param saturation {float} Saturation enhancement factor.
    @param jpg_compression {int} JPEG compression level in range `[0, 100]`.
    @param auto_brightness_enabled {bool} `True` when the post-static auto-brightness stage is enabled.
    @param auto_brightness_options {AutoBrightnessOptions} Auto-brightness stage knobs.
    @param auto_levels_enabled {bool} `True` when auto-levels stage is enabled.
    @param auto_levels_options {AutoLevelsOptions} Auto-levels stage knobs.
    @param auto_adjust_enabled {bool} `True` when the auto-adjust stage is enabled.
    @param auto_adjust_options {AutoAdjustOptions} Knobs for the sole auto-adjust implementation.
    @param debug_enabled {bool} `True` when persistent debug TIFF checkpoints are enabled.
    @param merge_gamma_option {MergeGammaOption} Parsed merge-gamma request applied only by OpenCV and HDR+ backends.
    @param raw_white_balance_mode {str} RAW camera WB normalization mode in `{"GREEN","MAX","MIN","MEAN"}`.
    @param white_balance_mode {str|None} Optional white-balance mode applied to bracket triplet before HDR merge backend execution.
    @param white_balance_analysis_source {str} White-balance analysis image selector in `{"ev-zero","linear-base"}`.
    @param opencv_tonemap_options {OpenCvTonemapOptions|None} Optional OpenCV-Tonemap backend selector and knob payload.
    @return {None} Immutable dataclass container.
    @satisfies REQ-020, REQ-050, REQ-065, REQ-066, REQ-069, REQ-071, REQ-072, REQ-073, REQ-075, REQ-082, REQ-083, REQ-084, REQ-086, REQ-087, REQ-088, REQ-089, REQ-090, REQ-100, REQ-101, REQ-102, REQ-103, REQ-104, REQ-105, REQ-146, REQ-176, REQ-179, REQ-181, REQ-182, REQ-190, REQ-194, REQ-195, REQ-196, REQ-199, REQ-203
    """

    post_gamma: float
    brightness: float
    contrast: float
    saturation: float
    jpg_compression: int
    post_gamma_mode: str = DEFAULT_POST_GAMMA_MODE
    post_gamma_auto_options: PostGammaAutoOptions = field(
        default_factory=PostGammaAutoOptions
    )
    auto_brightness_enabled: bool = False
    auto_brightness_options: AutoBrightnessOptions = field(
        default_factory=AutoBrightnessOptions
    )
    auto_levels_enabled: bool = False
    auto_levels_options: AutoLevelsOptions = field(default_factory=AutoLevelsOptions)
    auto_adjust_enabled: bool = DEFAULT_AUTO_ADJUST_ENABLED
    auto_adjust_options: AutoAdjustOptions = field(default_factory=AutoAdjustOptions)
    debug_enabled: bool = False
    merge_gamma_option: MergeGammaOption = field(default_factory=MergeGammaOption)
    raw_white_balance_mode: str = DEFAULT_RAW_WHITE_BALANCE_MODE
    white_balance_mode: str | None = None
    white_balance_analysis_source: str = WHITE_BALANCE_ANALYSIS_SOURCE_EV_ZERO
    opencv_tonemap_options: OpenCvTonemapOptions | None = None


@dataclass(frozen=True)
class DebugArtifactContext:
    """@brief Hold persistent debug-checkpoint output metadata.

    @details Stores the source input stem and destination directory used to emit
    debug TIFF checkpoints outside the temporary workspace. The suffix counter
    remains external so orchestration can map checkpoints to exact pipeline
    stages in execution order.
    @param output_dir {Path} Destination directory for persistent debug TIFF files.
    @param input_stem {str} Source DNG stem used as the filename prefix.
    @return {None} Immutable debug output metadata container.
    @satisfies DES-009, REQ-146, REQ-147, REQ-149
    """

    output_dir: Path
    input_stem: str


@dataclass(frozen=True)
class SourceGammaInfo:
    """@brief Hold one source-gamma diagnostic payload derived from RAW metadata.

    @details Encapsulates one deterministic runtime diagnostic resolved from RAW
    metadata only. The payload is observational and MUST NOT participate in HDR
    bracket extraction, HDR merge dispatch, or static postprocess state
    resolution.
    @param label {str} Deterministic source-gamma classification label.
    @param gamma_value {float|None} Numeric gamma value when derivable; `None` when metadata cannot resolve one.
    @param evidence {str} Metadata field or hint bundle used to classify the label.
    @return {None} Immutable dataclass container.
    @satisfies REQ-157, REQ-163, REQ-164
    """

    label: str
    gamma_value: float | None
    evidence: str


@dataclass(frozen=True)
class LuminanceOptions:
    """@brief Hold deterministic luminance-hdr-cli option values.

    @details Encapsulates luminance backend model and tone-mapping parameters
    forwarded to `luminance-hdr-cli` command generation. The response-curve
    payload is constrained to the repository linear HDR bracket contract.
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

    @details Encapsulates OpenCV merge controls used by the
    `--hdr-merge=OpenCV-Merge` backend. Debevec and Robertson linearize the
    extracted float brackets and execute `Merge* -> Tonemap` on backend-local
    radiance payloads, Mertens executes exposure fusion on float brackets with
    OpenCV-equivalent output rescaling plus optional simple tonemap, and all
    external interfaces stay RGB float `[0,1]`.
    @param merge_algorithm {str} Canonical OpenCV merge algorithm in `{"Debevec","Robertson","Mertens"}`.
    @param tonemap_enabled {bool} `True` enables simple OpenCV gamma tone mapping for Debevec/Robertson/Mertens outputs.
    @param tonemap_gamma {float} Positive gamma value passed to `cv2.createTonemap`; parser defaults are algorithm-specific (`Debevec=1.0`, `Robertson=0.9`, `Mertens=0.8`).
    @return {None} Immutable dataclass container.
    @satisfies REQ-108, REQ-109, REQ-110, REQ-141, REQ-142, REQ-143, REQ-144, REQ-152, REQ-153, REQ-154
    """

    merge_algorithm: str = DEFAULT_OPENCV_MERGE_ALGORITHM
    tonemap_enabled: bool = DEFAULT_OPENCV_TONEMAP_ENABLED
    tonemap_gamma: float = DEFAULT_OPENCV_TONEMAP_GAMMA


@dataclass(frozen=True)
class HdrPlusOptions:
    """@brief Hold deterministic HDR+ merge option values.

    @details Encapsulates the user-facing RGB-to-scalar proxy selection,
    hierarchical alignment search radius, and temporal weight controls used by
    the HDR+ backend port. Temporal values remain expressed in the historical
    16-bit code-domain units so CLI defaults, parsing, and runtime diagnostics
    stay unchanged while normalized float32 runtime controls are derived later.
    @param proxy_mode {str} Scalar proxy mode selector in `{"rggb","bt709","mean"}`.
    @param search_radius {int} Per-layer alignment search radius in pixels; candidate offsets span `[-search_radius, search_radius-1]`.
    @param temporal_factor {float} User-facing denominator stretch factor defined on historical 16-bit code-domain tile L1 distance.
    @param temporal_min_dist {float} User-facing distance floor defined on historical 16-bit code-domain tile L1 distance.
    @param temporal_max_dist {float} User-facing distance ceiling defined on historical 16-bit code-domain tile L1 distance.
    @return {None} Immutable dataclass container.
    @satisfies REQ-126, REQ-127, REQ-128, REQ-130, REQ-131, REQ-138
    """

    proxy_mode: str = DEFAULT_HDRPLUS_PROXY_MODE
    search_radius: int = DEFAULT_HDRPLUS_SEARCH_RADIUS
    temporal_factor: float = DEFAULT_HDRPLUS_TEMPORAL_FACTOR
    temporal_min_dist: float = DEFAULT_HDRPLUS_TEMPORAL_MIN_DIST
    temporal_max_dist: float = DEFAULT_HDRPLUS_TEMPORAL_MAX_DIST


@dataclass(frozen=True)
class HdrPlusTemporalRuntimeOptions:
    """@brief Hold HDR+ temporal controls remapped for normalized distance inputs.

    @details Converts user-facing temporal CLI values into runtime controls
    consumed by normalized float32 `[0,1]` tile L1 distances. The denominator
    stretch factor and distance floor are scaled from the historical 16-bit
    code-domain units, while the cutoff remains stored in the post-normalized
    comparison space so the existing weight curve stays numerically equivalent.
    @param distance_factor {float} Normalized-distance denominator stretch factor.
    @param min_distance {float} Normalized-distance floor before inverse-distance attenuation starts.
    @param max_weight_distance {float} Dimensionless cutoff threshold applied after normalization.
    @return {None} Immutable dataclass container.
    @satisfies REQ-114, REQ-131, REQ-138
    """

    distance_factor: float
    min_distance: float
    max_weight_distance: float


@dataclass(frozen=True)
class JointAutoEvSolution:
    """@brief Hold one resolved automatic exposure plan.

    @details Stores the selected `ev_zero`, the selected symmetric bracket
    half-span `ev_delta`, the heuristic name that supplied `ev_zero`, and the
    full ordered iteration trace used to stop bracket expansion. Side effects:
    none.
    @param ev_zero {float} Selected central EV value.
    @param ev_delta {float} Selected symmetric bracket half-span.
    @param selected_source {str} Heuristic label chosen for `ev_zero`.
    @param iteration_steps {tuple[AutoEvIterationStep, ...]} Ordered clipping-evaluation steps from iterative bracket expansion.
    @return {None} Immutable automatic exposure plan container.
    @satisfies REQ-008, REQ-009, REQ-032, REQ-052, REQ-167, REQ-168
    """

    ev_zero: float
    ev_delta: float
    selected_source: str
    iteration_steps: tuple["AutoEvIterationStep", ...]


@dataclass(frozen=True)
class AutoEvIterationStep:
    """@brief Hold one iterative bracket-evaluation step.

    @details Stores one tested `ev_delta` together with the measured shadow and
    highlight clipping percentages derived from unclipped bracket images at
    `ev_zero-ev_delta` and `ev_zero+ev_delta`. Side effects: none.
    @param ev_delta {float} Tested symmetric bracket half-span.
    @param shadow_clipping_pct {float} Percentage of minus-image pixels with any channel `<=0`.
    @param highlight_clipping_pct {float} Percentage of plus-image pixels with any channel `>=1`.
    @return {None} Immutable bracket-step container.
    @satisfies REQ-167, REQ-168
    """

    ev_delta: float
    shadow_clipping_pct: float
    highlight_clipping_pct: float


@dataclass(frozen=True)
class AutoEvOptions:
    """@brief Hold automatic exposure bracket-search controls.

    @details Encapsulates the iterative bracket-search thresholds and step size
    used by automatic exposure planning. Thresholds are expressed as percentages
    in `0..100`; step is a positive EV increment. Side effects: none.
    @param shadow_clipping_pct {float} Shadow clipping stop threshold in percent.
    @param highlight_clipping_pct {float} Highlight clipping stop threshold in percent.
    @param step {float} Positive EV increment used by iterative bracket expansion.
    @return {None} Immutable automatic exposure option container.
    @satisfies REQ-019, REQ-166, REQ-167
    """

    shadow_clipping_pct: float = DEFAULT_AUTO_EV_SHADOW_CLIPPING
    highlight_clipping_pct: float = DEFAULT_AUTO_EV_HIGHLIGHT_CLIPPING
    step: float = DEFAULT_AUTO_EV_STEP


@dataclass(frozen=True)
class AutoZeroEvaluation:
    """@brief Hold the three exposure-measure EV evaluations.

    @details Stores the entropy-optimized candidate (`ev_best`), the ETTR
    candidate (`ev_ettr`), and the detail-preservation candidate (`ev_detail`)
    computed from one normalized linear RGB float image.
    Values are rounded to one decimal place before downstream selection.
    @param ev_best {float} Entropy-optimized EV candidate.
    @param ev_ettr {float} ETTR EV candidate.
    @param ev_detail {float} Detail-preservation EV candidate.
    @return {None} Immutable center-heuristic evaluation container.
    @satisfies REQ-008, REQ-032, REQ-052
    """

    ev_best: float
    ev_ettr: float
    ev_detail: float


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


def _print_help_section(title):
    """@brief Print one numbered help section title.

    @details Emits one blank separator line followed by one deterministic
    section title so conversion help stays ordered by pipeline execution step.
    Complexity: O(1). Side effects: stdout writes only.
    @param title {str} Section title text already normalized for display order.
    @return {None} Writes formatted section title to stdout.
    @satisfies REQ-017, REQ-155
    """

    print()
    print(title)


def _print_help_option(option_label, description, detail_lines=()):
    """@brief Print one aligned conversion-help option block.

    @details Renders one option label and wrapped description using a fixed
    indentation grid, then renders any continuation detail lines under the same
    description column. Complexity: O(n) in total output characters. Side
    effects: stdout writes only.
    @param option_label {str} Left-column option label or positional argument label.
    @param description {str} Primary description line for the option block.
    @param detail_lines {tuple[str, ...]|list[str]} Additional wrapped lines aligned under the description column.
    @return {None} Writes formatted option block to stdout.
    @satisfies REQ-017, REQ-155, REQ-156
    """

    label_width = 34
    prefix = f"  {option_label.ljust(label_width)}"
    wrap_width = 88
    wrapped_description = textwrap.wrap(
        description,
        width=wrap_width,
        break_long_words=False,
        break_on_hyphens=False,
    )
    if not wrapped_description:
        wrapped_description = [""]
    print(f"{prefix}{wrapped_description[0]}")
    continuation_prefix = "  " + (" " * label_width)
    for line in wrapped_description[1:]:
        print(f"{continuation_prefix}{line}")
    for detail_line in detail_lines:
        wrapped_detail = textwrap.wrap(
            detail_line,
            width=wrap_width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        if not wrapped_detail:
            wrapped_detail = [""]
        for line in wrapped_detail:
            print(f"{continuation_prefix}{line}")


def print_help(version):
    """@brief Print help text for the `dng2jpg` command.

    @details Renders conversion help in pipeline execution order. Groups each
    processing stage with the selectors and knobs that configure that stage,
    documents allowed values and activation conditions for every accepted
    conversion option, and prints effective omitted-value defaults using aligned
    indentation and stable table formatting. Complexity: O(n) in emitted
    characters. Side effects: stdout writes only.
    @param version {str} CLI version label to append in usage output.
    @return {None} Writes help text to stdout.
    @satisfies DES-008, REQ-017, REQ-018, REQ-019, REQ-020, REQ-021, REQ-022, REQ-023, REQ-024, REQ-025, REQ-033, REQ-100, REQ-101, REQ-102, REQ-107, REQ-111, REQ-124, REQ-125, REQ-127, REQ-128, REQ-135, REQ-141, REQ-143, REQ-146, REQ-155, REQ-156, REQ-176, REQ-179, REQ-181, REQ-182, REQ-189, REQ-190, REQ-194, REQ-195, REQ-196, REQ-203
    """

    postprocess_default_rows = (
        (
            HDR_MERGE_MODE_LUMINANCE,
            "generic",
            f"{DEFAULT_POST_GAMMA:g} / {DEFAULT_BRIGHTNESS:g} / {DEFAULT_CONTRAST:g} / {DEFAULT_SATURATION:g}",
        ),
        (
            HDR_MERGE_MODE_LUMINANCE,
            "reinhard02",
            f"{DEFAULT_REINHARD02_POST_GAMMA:g} / {DEFAULT_REINHARD02_BRIGHTNESS:g} / {DEFAULT_REINHARD02_CONTRAST:g} / {DEFAULT_REINHARD02_SATURATION:g}",
        ),
        (
            HDR_MERGE_MODE_LUMINANCE,
            "mantiuk08",
            f"{DEFAULT_MANTIUK08_POST_GAMMA:g} / {DEFAULT_MANTIUK08_BRIGHTNESS:g} / {DEFAULT_MANTIUK08_CONTRAST:g} / {DEFAULT_MANTIUK08_SATURATION:g}",
        ),
        (
            HDR_MERGE_MODE_OPENCV_MERGE,
            OPENCV_MERGE_ALGORITHM_DEBEVEC,
            f"{DEFAULT_OPENCV_DEBEVEC_POST_GAMMA:g} / {DEFAULT_OPENCV_DEBEVEC_BRIGHTNESS:g} / {DEFAULT_OPENCV_DEBEVEC_CONTRAST:g} / {DEFAULT_OPENCV_DEBEVEC_SATURATION:g}",
        ),
        (
            HDR_MERGE_MODE_OPENCV_MERGE,
            OPENCV_MERGE_ALGORITHM_ROBERTSON,
            f"{DEFAULT_OPENCV_ROBERTSON_POST_GAMMA:g} / {DEFAULT_OPENCV_ROBERTSON_BRIGHTNESS:g} / {DEFAULT_OPENCV_ROBERTSON_CONTRAST:g} / {DEFAULT_OPENCV_ROBERTSON_SATURATION:g}",
        ),
        (
            HDR_MERGE_MODE_OPENCV_MERGE,
            OPENCV_MERGE_ALGORITHM_MERTENS,
            f"{DEFAULT_OPENCV_MERTENS_POST_GAMMA:g} / {DEFAULT_OPENCV_MERTENS_BRIGHTNESS:g} / {DEFAULT_OPENCV_MERTENS_CONTRAST:g} / {DEFAULT_OPENCV_MERTENS_SATURATION:g}",
        ),
        (
            HDR_MERGE_MODE_HDR_PLUS,
            "generic",
            f"{DEFAULT_HDRPLUS_POST_GAMMA:g} / {DEFAULT_HDRPLUS_BRIGHTNESS:g} / {DEFAULT_HDRPLUS_CONTRAST:g} / {DEFAULT_HDRPLUS_SATURATION:g}",
        ),
    )

    print(f"Usage: {PROGRAM} <input.dng> <output.jpg> [options] ({version})")
    print(
        "       Value options MUST use the `--option=value` form; the separated `--option value` form is rejected."
    )
    print(
        "       Optional-boolean knobs accept bare flag form as `true` or explicit `0|1|false|true|no|yes|off|on`."
    )

    _print_help_section("Step 1 - Inputs and command surface")
    _print_help_option(
        "<input.dng>",
        "Input DNG path. Required. Existing file with `.dng` suffix.",
    )
    _print_help_option(
        "<output.jpg>",
        "Output JPG path. Required. Parent directory must already exist.",
    )
    _print_help_option(
        "--help",
        "Show this conversion help. Top-level `dng2jpg --help` prints management help first, then this conversion help.",
    )

    _print_help_section("Step 2 - Exposure planning and RAW bracket extraction")
    _print_help_option(
        "--ev=<value>",
        "Static symmetric bracket EV delta as one finite numeric value `>= 0`.",
        (
            "Mutually exclusive with enabled `--auto-ev`.",
            "The exposure-measure EV triplet is still computed and printed.",
        ),
    )
    _print_help_option(
        "--auto-ev=<enable|disable>",
        "Automatic symmetric exposure planner that selects `ev_zero` from the exposure-measure EV triplet and derives `ev_delta` through iterative clipping-threshold expansion.",
        (
            "Default: `enable` when `--ev` is omitted; `disable` when `--ev` is provided.",
            "Rejected when combined with `--ev` or `--ev-zero`.",
        ),
    )
    _print_help_option(
        "--ev-zero=<value>",
        "Static central bracket EV as one finite numeric value.",
        (
            "Accepted only together with `--ev`.",
            "No bit-depth-derived upper bound is enforced.",
        ),
    )
    _print_help_option(
        "--auto-ev-shadow-clipping=<0..100>",
        f"Shadow clipping stop threshold in percent for iterative bracket expansion. Default: `{DEFAULT_AUTO_EV_SHADOW_CLIPPING:g}`.",
    )
    _print_help_option(
        "--auto-ev-highlight-clipping=<0..100>",
        f"Highlight clipping stop threshold in percent for iterative bracket expansion. Default: `{DEFAULT_AUTO_EV_HIGHLIGHT_CLIPPING:g}`.",
    )
    _print_help_option(
        "--auto-ev-step=<value>",
        f"Positive EV increment used by iterative bracket expansion. Default: `{DEFAULT_AUTO_EV_STEP:g}`.",
    )
    _print_help_option(
        "--white-balance=<GREEN|MAX|MIN|MEAN>",
        "RAW camera white-balance normalization mode used during linear-base extraction before bracket arithmetic.",
        (
            "Allowed values: " + ", ".join(_RAW_WHITE_BALANCE_MODES) + ".",
            f"Default: `{DEFAULT_RAW_WHITE_BALANCE_MODE}`.",
        ),
    )

    _print_help_section(
        "Step 3 - Optional white-balance stage and HDR backend selection"
    )
    _print_help_option(
        "--auto-white-balance=<mode>",
        "Optional bracket white-balance stage executed after bracket extraction and before HDR merge backend selection.",
        (
            "Allowed values: "
            + ", ".join(_WHITE_BALANCE_MODES)
            + ".",
            "Default: disabled (stage skipped when omitted).",
        ),
    )
    _print_help_option(
        "--white-balance-analysis-source=<source>",
        "Optional white-balance analysis payload selector used when white-balance stage is enabled.",
        (
            "Allowed values: "
            + ", ".join(_WHITE_BALANCE_ANALYSIS_SOURCES)
            + ".",
            f"Default: `{WHITE_BALANCE_ANALYSIS_SOURCE_EV_ZERO}`.",
        ),
    )
    _print_help_option(
        f"--hdr-merge=<{HDR_MERGE_MODE_LUMINANCE}|{HDR_MERGE_MODE_OPENCV_MERGE}|{HDR_MERGE_MODE_OPENCV_TONEMAP}|{HDR_MERGE_MODE_HDR_PLUS}>",
        f"Select HDR merge backend. Default: `{HDR_MERGE_MODE_OPENCV_MERGE}`.",
    )
    _print_help_option(
        "--gamma=<auto|a,b>",
        f"HDR merge-output transfer selector for `{HDR_MERGE_MODE_OPENCV_MERGE}`, `{HDR_MERGE_MODE_OPENCV_TONEMAP}`, and `{HDR_MERGE_MODE_HDR_PLUS}` final backend-local output stage.",
        (
            "Default: `auto`.",
            "Use `--gamma=auto` to resolve source transfer from RAW/DNG EXIF evidence.",
            "Use `--gamma=<linear_coeff,exponent>` for custom Rec.709-style transfer.",
        ),
    )
    _print_help_option(
        "--opencv-merge-algorithm=<name>",
        f"OpenCV merge algorithm. Effective only when `--hdr-merge={HDR_MERGE_MODE_OPENCV_MERGE}`.",
        (
            f"Allowed values: {', '.join(_OPENCV_MERGE_ALGORITHMS)}.",
            f"Default: `{DEFAULT_OPENCV_MERGE_ALGORITHM}`.",
        ),
    )
    _print_help_option(
        "--opencv-tonemap=<bool>",
        "Enable simple OpenCV gamma tone mapping for OpenCV merge outputs.",
        (f"Default: `{'true' if DEFAULT_OPENCV_TONEMAP_ENABLED else 'false'}`.",),
    )
    _print_help_option(
        "--opencv-tonemap-gamma=<value>",
        "Positive gamma used by OpenCV simple tone mapping. Effective only when OpenCV tone mapping is enabled.",
        (
            f"Default by algorithm: `{OPENCV_MERGE_ALGORITHM_DEBEVEC}={DEFAULT_OPENCV_DEBEVEC_TONEMAP_GAMMA:g}`, "
            f"`{OPENCV_MERGE_ALGORITHM_ROBERTSON}={DEFAULT_OPENCV_ROBERTSON_TONEMAP_GAMMA:g}`, "
            f"`{OPENCV_MERGE_ALGORITHM_MERTENS}={DEFAULT_OPENCV_MERTENS_TONEMAP_GAMMA:g}`.",
        ),
    )
    _print_help_option(
        "--tonemap-drago",
        f"Select OpenCV Drago tone mapping for `{HDR_MERGE_MODE_OPENCV_TONEMAP}`. Exactly one OpenCV-Tonemap selector is required.",
    )
    _print_help_option(
        "--tonemap-reinhard",
        f"Select OpenCV Reinhard tone mapping for `{HDR_MERGE_MODE_OPENCV_TONEMAP}`. Exactly one OpenCV-Tonemap selector is required.",
    )
    _print_help_option(
        "--tonemap-mantiuk",
        f"Select OpenCV Mantiuk tone mapping for `{HDR_MERGE_MODE_OPENCV_TONEMAP}`. Exactly one OpenCV-Tonemap selector is required.",
    )
    _print_help_option(
        "--tonemap-drago-saturation=<value>",
        f"Drago saturation parameter. Effective only when `--hdr-merge={HDR_MERGE_MODE_OPENCV_TONEMAP}` and `--tonemap-drago` are selected. Default: `{DEFAULT_OPENCV_TONEMAP_DRAGO_SATURATION:g}`.",
    )
    _print_help_option(
        "--tonemap-drago-bias=<0..1>",
        f"Drago bias parameter. Effective only when `--hdr-merge={HDR_MERGE_MODE_OPENCV_TONEMAP}` and `--tonemap-drago` are selected. Default: `{DEFAULT_OPENCV_TONEMAP_DRAGO_BIAS:g}`.",
    )
    _print_help_option(
        "--tonemap-reinhard-intensity=<value>",
        f"Reinhard intensity parameter. Effective only when `--hdr-merge={HDR_MERGE_MODE_OPENCV_TONEMAP}` and `--tonemap-reinhard` are selected. Default: `{DEFAULT_OPENCV_TONEMAP_REINHARD_INTENSITY:g}`.",
    )
    _print_help_option(
        "--tonemap-reinhard-light_adapt=<0..1>",
        f"Reinhard light adaptation parameter. Effective only when `--hdr-merge={HDR_MERGE_MODE_OPENCV_TONEMAP}` and `--tonemap-reinhard` are selected. Default: `{DEFAULT_OPENCV_TONEMAP_REINHARD_LIGHT_ADAPT:g}`.",
    )
    _print_help_option(
        "--tonemap-reinhard-color_adapt=<0..1>",
        f"Reinhard color adaptation parameter. Effective only when `--hdr-merge={HDR_MERGE_MODE_OPENCV_TONEMAP}` and `--tonemap-reinhard` are selected. Default: `{DEFAULT_OPENCV_TONEMAP_REINHARD_COLOR_ADAPT:g}`.",
    )
    _print_help_option(
        "--tonemap-mantiuk-scale=<value>",
        f"Mantiuk scale parameter. Effective only when `--hdr-merge={HDR_MERGE_MODE_OPENCV_TONEMAP}` and `--tonemap-mantiuk` are selected. Default: `{DEFAULT_OPENCV_TONEMAP_MANTIUK_SCALE:g}`.",
    )
    _print_help_option(
        "--tonemap-mantiuk-saturation=<value>",
        f"Mantiuk saturation parameter. Effective only when `--hdr-merge={HDR_MERGE_MODE_OPENCV_TONEMAP}` and `--tonemap-mantiuk` are selected. Default: `{DEFAULT_OPENCV_TONEMAP_MANTIUK_SATURATION:g}`.",
    )
    _print_help_option(
        "--hdrplus-proxy-mode=<name>",
        "HDR+ scalar proxy mode. Effective only when `--hdr-merge=HDR-Plus`.",
        (
            f"Allowed values: {', '.join(_HDRPLUS_PROXY_MODES)}.",
            f"Default: `{DEFAULT_HDRPLUS_PROXY_MODE}`.",
        ),
    )
    _print_help_option(
        "--hdrplus-search-radius=<value>",
        f"HDR+ per-layer alignment search radius; integer `> 0`. Effective only when `--hdr-merge=HDR-Plus`. Default: `{DEFAULT_HDRPLUS_SEARCH_RADIUS}`.",
    )
    _print_help_option(
        "--hdrplus-temporal-factor=<value>",
        f"HDR+ temporal inverse-distance stretch factor; `> 0`. Effective only when `--hdr-merge=HDR-Plus`. Default: `{DEFAULT_HDRPLUS_TEMPORAL_FACTOR:g}`.",
    )
    _print_help_option(
        "--hdrplus-temporal-min-dist=<value>",
        f"HDR+ temporal weight floor; `>= 0`. Effective only when `--hdr-merge=HDR-Plus`. Default: `{DEFAULT_HDRPLUS_TEMPORAL_MIN_DIST:g}`.",
    )
    _print_help_option(
        "--hdrplus-temporal-max-dist=<value>",
        f"HDR+ temporal cutoff threshold; must be `> --hdrplus-temporal-min-dist`. Effective only when `--hdr-merge=HDR-Plus`. Default: `{DEFAULT_HDRPLUS_TEMPORAL_MAX_DIST:g}`.",
    )
    _print_help_option(
        "--luminance-hdr-model=<name>",
        f"Luminance HDR model text forwarded to `luminance-hdr-cli`. Effective only when `--hdr-merge={HDR_MERGE_MODE_LUMINANCE}`. Default: `{DEFAULT_LUMINANCE_HDR_MODEL}`.",
    )
    _print_help_option(
        "--luminance-hdr-weight=<name>",
        f"Luminance weighting function text forwarded to `luminance-hdr-cli`. Effective only when `--hdr-merge={HDR_MERGE_MODE_LUMINANCE}`. Default: `{DEFAULT_LUMINANCE_HDR_WEIGHT}`.",
    )
    _print_help_option(
        "--luminance-hdr-response-curve=<name>",
        "Luminance response-curve selector constrained to the repository "
        f"linear HDR contract. Effective only when `--hdr-merge={HDR_MERGE_MODE_LUMINANCE}`. "
        f"Only accepted value: `{DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE}`.",
    )
    _print_help_option(
        "--luminance-tmo=<name>",
        f"Luminance tone-mapping operator. Effective only when `--hdr-merge={HDR_MERGE_MODE_LUMINANCE}`. Default: `{DEFAULT_LUMINANCE_TMO}`.",
    )
    _print_help_option(
        "--tmo*=<value>",
        f"Forward explicit `luminance-hdr-cli --tmo*` parameters unchanged. Effective only when `--hdr-merge={HDR_MERGE_MODE_LUMINANCE}`.",
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

    _print_help_section("Step 4 - Auto-brightness stage")
    _print_help_option(
        "--auto-brightness=<enable|disable>",
        "Enable or disable the auto-brightness stage executed after static postprocess and before auto-levels.",
        ("Default: `enable`.",),
    )
    _print_help_option(
        "--ab-key-value=<value>",
        "Manual Reinhard key value `a`; must be `> 0`.",
        ("Omit to enable automatic low-key / normal-key / high-key selection.",),
    )
    _print_help_option(
        "--ab-white-point-pct=<(0,100)>",
        f"Percentile for robust white-point burn-out compression. Effective only when auto-brightness resolves to enable. Default: `{DEFAULT_AB_WHITE_POINT_PERCENTILE:g}`.",
    )
    _print_help_option(
        "--ab-key-min=<value>",
        f"Minimum automatic key-value clamp; `> 0`. Effective only when auto-brightness resolves to enable. Default: `{DEFAULT_AB_A_MIN:g}`.",
    )
    _print_help_option(
        "--ab-key-max=<value>",
        f"Maximum automatic key-value clamp; `> 0`. Effective only when auto-brightness resolves to enable. Default: `{DEFAULT_AB_A_MAX:g}`.",
    )
    _print_help_option(
        "--ab-max-auto-boost=<value>",
        f"Automatic key adaptation factor; `> 0`. Effective only when auto-brightness resolves to enable. Default: `{DEFAULT_AB_MAX_AUTO_BOOST_FACTOR:g}`.",
    )
    _print_help_option(
        "--ab-enable-luminance-preserving-desat[=<bool>]",
        "Enable luminance-preserving anti-clipping desaturation. Effective only when auto-brightness resolves to enable.",
        (
            f"Default: `{'true' if DEFAULT_AB_ENABLE_LUMINANCE_PRESERVING_DESAT else 'false'}`.",
            "Bare flag form is equivalent to `true`.",
        ),
    )
    _print_help_option(
        "--ab-eps=<value>",
        f"Positive numerical guard for logarithms and divisions. Effective only when auto-brightness resolves to enable. Default: `{DEFAULT_AB_EPS:g}`.",
    )

    _print_help_section("Step 5 - Auto-levels stage")
    _print_help_option(
        "--auto-levels=<enable|disable>",
        "Enable or disable the auto-levels stage executed after static postprocess and optional auto-brightness.",
        ("Default: `enable`.",),
    )
    _print_help_option(
        "--al-clip-pct=<value>",
        f"Histogram clipping percentage; `>= 0`. Effective only when auto-levels resolves to enable. Default: `{DEFAULT_AL_CLIP_PERCENT:g}`.",
    )
    _print_help_option(
        "--al-clip-out-of-gamut[=<bool>]",
        "Normalize overflowing RGB triplets after auto-levels tonal transformation and optional highlight reconstruction. Effective only when auto-levels resolves to enable.",
        (
            f"Default: `{'true' if DEFAULT_AL_CLIP_OUT_OF_GAMUT else 'false'}`.",
            "Bare flag form is equivalent to `true`.",
        ),
    )
    _print_help_option(
        "--al-highlight-reconstruction[=<bool>]",
        "Enable or disable highlight reconstruction after the auto-levels tonal transformation. Effective only when auto-levels resolves to enable.",
        (
            "Bare flag form is equivalent to `true`.",
            "Default: `false`.",
        ),
    )
    _print_help_option(
        "--al-highlight-reconstruction-method=<name>",
        "Select one RawTherapee-aligned highlight reconstruction method. Effective only when auto-levels resolves to enable.",
        (
            "Allowed values: " + ", ".join(_AUTO_LEVELS_HIGHLIGHT_METHODS) + ".",
            "Default when omitted: `Inpaint Opposed`.",
        ),
    )
    _print_help_option(
        "--al-gain-threshold=<value>",
        f"Inpaint Opposed gain threshold; `> 0`. Effective only when auto-levels resolves to enable. Default: `{DEFAULT_AL_GAIN_THRESHOLD:g}`.",
    )

    _print_help_section("Step 6 - Static postprocess stage")
    _print_help_option(
        "--post-gamma=<value|auto>",
        "Postprocess gamma selector. Use a positive float for numeric static gamma or `auto` to replace numeric static gamma/brightness/contrast/saturation with one dedicated auto-gamma stage.",
    )
    _print_help_option(
        "--post-gamma-auto-target-gray=<value>",
        f"Auto-gamma gray-anchor target in `(0,1)`. Effective only when `--post-gamma=auto`. Default: `{DEFAULT_POST_GAMMA_AUTO_TARGET_GRAY:g}`.",
    )
    _print_help_option(
        "--post-gamma-auto-luma-min=<value>",
        f"Auto-gamma lower luminance guard in `(0,1)`. Effective only when `--post-gamma=auto`. Default: `{DEFAULT_POST_GAMMA_AUTO_LUMA_MIN:g}`.",
    )
    _print_help_option(
        "--post-gamma-auto-luma-max=<value>",
        f"Auto-gamma upper luminance guard in `(0,1)`. Effective only when `--post-gamma=auto`. Default: `{DEFAULT_POST_GAMMA_AUTO_LUMA_MAX:g}`.",
    )
    _print_help_option(
        "--post-gamma-auto-lut-size=<value>",
        f"Auto-gamma LUT sample size; integer `>=2`. Effective only when `--post-gamma=auto`. Default: `{DEFAULT_POST_GAMMA_AUTO_LUT_SIZE}`.",
    )
    _print_help_option(
        "--brightness=<value>",
        "Postprocess brightness factor; positive float. When omitted, resolves from selected backend and backend variant.",
    )
    _print_help_option(
        "--contrast=<value>",
        "Postprocess contrast factor; positive float. When omitted, resolves from selected backend and backend variant.",
    )
    _print_help_option(
        "--saturation=<value>",
        "Postprocess saturation factor; positive float. When omitted, resolves from selected backend and backend variant.",
    )
    print()
    print("  Static postprocess defaults when omitted:")
    _print_box_table(
        ("Backend", "Variant", "post-gamma / brightness / contrast / saturation"),
        postprocess_default_rows,
    )

    _print_help_section("Step 7 - Auto-adjust stage")
    _print_help_option(
        "--auto-adjust=<enable|disable>",
        "Enable or disable the auto-adjust stage executed after static postprocess and before final JPEG quantization.",
        ("Default: `enable`.",),
    )
    _print_help_option(
        "--aa-blur-sigma=<value>",
        f"Selective blur sigma; `> 0`. Effective only when auto-adjust resolves to enable. Default: `{DEFAULT_AA_BLUR_SIGMA:g}`.",
    )
    _print_help_option(
        "--aa-blur-threshold-pct=<0..100>",
        f"Selective blur threshold percentile. Effective only when auto-adjust resolves to enable. Default: `{DEFAULT_AA_BLUR_THRESHOLD_PCT:g}`.",
    )
    _print_help_option(
        "--aa-level-low-pct=<0..100>",
        f"Level low percentile; must stay `< --aa-level-high-pct`. Effective only when auto-adjust resolves to enable. Default: `{DEFAULT_AA_LEVEL_LOW_PCT:g}`.",
    )
    _print_help_option(
        "--aa-level-high-pct=<0..100>",
        f"Level high percentile; must stay `> --aa-level-low-pct`. Effective only when auto-adjust resolves to enable. Default: `{DEFAULT_AA_LEVEL_HIGH_PCT:g}`.",
    )
    _print_help_option(
        "--aa-enable-local-contrast[=<bool>]",
        "Enable float-domain CLAHE-luma local contrast stage. Effective only when auto-adjust resolves to enable.",
        (
            f"Default: `{'true' if DEFAULT_AA_ENABLE_LOCAL_CONTRAST else 'false'}`.",
            "Bare flag form is equivalent to `true`.",
        ),
    )
    _print_help_option(
        "--aa-local-contrast-strength=<0..1>",
        f"CLAHE-luma blend factor. Effective only when auto-adjust resolves to enable. Default: `{DEFAULT_AA_LOCAL_CONTRAST_STRENGTH:g}`.",
    )
    _print_help_option(
        "--aa-clahe-clip-limit=<value>",
        f"CLAHE clip limit; `> 0`. Effective only when auto-adjust resolves to enable. Default: `{DEFAULT_AA_CLAHE_CLIP_LIMIT:g}`.",
    )
    _print_help_option(
        "--aa-clahe-tile-grid-size=<rows>x<cols>",
        f"CLAHE tile grid size with both dimensions `>= 1`. Effective only when auto-adjust resolves to enable. Default: `{DEFAULT_AA_CLAHE_TILE_GRID_SIZE[0]}x{DEFAULT_AA_CLAHE_TILE_GRID_SIZE[1]}`.",
    )
    _print_help_option(
        "--aa-sigmoid-contrast=<value>",
        f"Sigmoidal contrast slope; `> 0`. Effective only when auto-adjust resolves to enable. Default: `{DEFAULT_AA_SIGMOID_CONTRAST:g}`.",
    )
    _print_help_option(
        "--aa-sigmoid-midpoint=<0..1>",
        f"Sigmoidal midpoint in `[0,1]`. Effective only when auto-adjust resolves to enable. Default: `{DEFAULT_AA_SIGMOID_MIDPOINT:g}`.",
    )
    _print_help_option(
        "--aa-saturation-gamma=<value>",
        f"HSL saturation gamma denominator; `> 0`. Effective only when auto-adjust resolves to enable. Default: `{DEFAULT_AA_SATURATION_GAMMA:g}`.",
    )
    _print_help_option(
        "--aa-highpass-blur-sigma=<value>",
        f"High-pass blur sigma; `> 0`. Effective only when auto-adjust resolves to enable. Default: `{DEFAULT_AA_HIGHPASS_BLUR_SIGMA:g}`.",
    )

    _print_help_section("Step 8 - Final JPEG, EXIF refresh, and debug artifacts")
    _print_help_option(
        "--jpg-compression=<0..100>",
        f"JPEG compression level for the final save stage. Default: `{DEFAULT_JPG_COMPRESSION}`.",
    )
    _print_help_option(
        "--debug",
        "Persist TIFF16 checkpoints for executed float pipeline stages in the output JPG directory. Does not change the final JPG destination.",
    )
    _print_help_option(
        "[platform]",
        "Conversion command is available on Linux only.",
    )


def _validate_supported_bits_per_color(bits_per_color):
    """@brief Validate supported minimum DNG bits-per-color contract.

    @details Enforces repository minimum bit-depth support independently from
    exposure range planning and raises deterministic failure when source DNG
    metadata exposes a lower precision container.
    @param bits_per_color {int} Detected source DNG bits per color.
    @return {None} Validation completion without payload.
    @exception ValueError Raised when bit depth is below supported minimum.
    @satisfies REQ-027
    """

    if bits_per_color < MIN_SUPPORTED_BITS_PER_COLOR:
        raise ValueError(
            f"Unsupported bits_per_color={bits_per_color}; expected >= {MIN_SUPPORTED_BITS_PER_COLOR}"
        )


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
    @satisfies REQ-026, REQ-027
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
    """@brief Validate EV value is a finite numeric scalar.

    @details Performs finite-number validation only. Step-based validation was
    removed from manual exposure planning.
    @param ev_value {float} Parsed EV numeric value.
    @return {bool} `True` when EV value is finite.
    @satisfies REQ-030
    """

    return math.isfinite(float(ev_value))


def _parse_ev_option(ev_raw):
    """@brief Parse and validate one EV option value.

    @details Converts token to `float`, enforces finiteness and non-negativity,
    and preserves the parsed static bracket half-span without applying any
    bit-depth-derived upper-bound contract.
    @param ev_raw {str} EV token extracted from command arguments.
    @return {float|None} Parsed EV value when valid; `None` otherwise.
    @satisfies REQ-030
    """

    try:
        ev_value = float(ev_raw)
    except ValueError:
        print_error(f"Invalid --ev value: {ev_raw}")
        print_error("Allowed values: finite numeric >= 0")
        return None

    if ev_value < 0.0 or not _is_ev_value_on_supported_step(ev_value):
        print_error(f"Unsupported --ev value: {ev_raw}")
        print_error("Allowed values: finite numeric >= 0")
        return None

    return float(ev_value)


def _parse_ev_zero_option(ev_zero_raw):
    """@brief Parse and validate one `--ev-zero` option value.

    @details Converts token to `float`, enforces finiteness, and preserves
    static center EV value without applying bit-depth-derived upper bounds.
    @param ev_zero_raw {str} EV-zero token extracted from command arguments.
    @return {float|None} Parsed EV-zero value when valid; `None` otherwise.
    @satisfies REQ-018, REQ-030
    """

    try:
        ev_zero_value = float(ev_zero_raw)
    except ValueError:
        print_error(f"Invalid --ev-zero value: {ev_zero_raw}")
        print_error("Allowed values: finite numeric")
        return None

    if not _is_ev_value_on_supported_step(ev_zero_value):
        print_error(f"Unsupported --ev-zero value: {ev_zero_raw}")
        print_error("Allowed values: finite numeric")
        return None

    return float(ev_zero_value)


def _parse_auto_ev_option(auto_ev_raw):
    """@brief Parse and validate one `--auto-ev` option value.

    @details Accepts only explicit enable/disable tokens to keep deterministic
    CLI behavior and unambiguous exclusivity handling with `--ev`.
    @param auto_ev_raw {str} Raw `--auto-ev` value token from CLI args.
    @return {bool|None} Parsed enable-state value; `None` on parse failure.
    @satisfies CTN-003, REQ-009
    """

    auto_ev_text = auto_ev_raw.strip().lower()
    if auto_ev_text == "enable":
        return True
    if auto_ev_text == "disable":
        return False
    print_error(f"Invalid --auto-ev value: {auto_ev_raw}")
    print_error("Allowed values: enable, disable")
    return None


def _parse_percentage_option(option_name, option_raw):
    """@brief Parse and validate one percentage option value.

    @details Converts option token to `float`, requires inclusive range
    `[0, 100]`, and emits deterministic parse errors on malformed values.
    @param option_name {str} Long-option identifier used in error messages.
    @param option_raw {str} Raw option token value from CLI args.
    @return {float|None} Parsed percentage value when valid; `None` otherwise.
    @satisfies REQ-019, REQ-030
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

    @details Accepts only explicit enable/disable tokens to keep deterministic
    toggle behavior for stage activation.
    @param auto_brightness_raw {str} Raw `--auto-brightness` value token from CLI args.
    @return {bool|None} Parsed enable-state value; `None` on parse failure.
    @satisfies REQ-065, REQ-089
    """

    auto_brightness_text = auto_brightness_raw.strip().lower()
    if auto_brightness_text == "enable":
        return True
    if auto_brightness_text == "disable":
        return False
    print_error(f"Invalid --auto-brightness value: {auto_brightness_raw}")
    print_error("Allowed values: enable, disable")
    return None


def _parse_auto_levels_option(auto_levels_raw):
    """@brief Parse and validate one `--auto-levels` option value.

    @details Accepts only explicit enable/disable tokens to keep deterministic
    toggle behavior for stage activation.
    @param auto_levels_raw {str} Raw `--auto-levels` value token from CLI args.
    @return {bool|None} Parsed enable-state value; `None` on parse failure.
    @satisfies REQ-100, REQ-101
    """

    auto_levels_text = auto_levels_raw.strip().lower()
    if auto_levels_text == "enable":
        return True
    if auto_levels_text == "disable":
        return False
    print_error(f"Invalid --auto-levels value: {auto_levels_raw}")
    print_error("Allowed values: enable, disable")
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


def _parse_opencv_merge_algorithm_option(algorithm_raw):
    """@brief Parse OpenCV merge algorithm selector.

    @details Accepts case-insensitive OpenCV algorithm names, normalizes them
    to canonical runtime tokens, and rejects unsupported values with
    deterministic diagnostics.
    @param algorithm_raw {str} Raw `--opencv-merge-algorithm` selector token.
    @return {str|None} Canonical OpenCV merge algorithm token or `None` on parse failure.
    @satisfies REQ-108, REQ-141
    """

    normalized = algorithm_raw.strip().lower()
    mapping = {
        OPENCV_MERGE_ALGORITHM_DEBEVEC.lower(): OPENCV_MERGE_ALGORITHM_DEBEVEC,
        OPENCV_MERGE_ALGORITHM_ROBERTSON.lower(): OPENCV_MERGE_ALGORITHM_ROBERTSON,
        OPENCV_MERGE_ALGORITHM_MERTENS.lower(): OPENCV_MERGE_ALGORITHM_MERTENS,
    }
    resolved = mapping.get(normalized)
    if resolved is not None:
        return resolved
    print_error(f"Invalid --opencv-merge-algorithm value: {algorithm_raw}")
    print_error("Allowed values: " + ", ".join(_OPENCV_MERGE_ALGORITHMS))
    return None


def _resolve_default_opencv_tonemap_gamma(merge_algorithm):
    """@brief Resolve OpenCV tone-map gamma default from merge algorithm.

    @details Maps `Debevec`, `Robertson`, and `Mertens` to deterministic
    default gamma values used when `--opencv-tonemap-gamma` is omitted.
    Unknown values fall back to the repository default merge algorithm profile.
    @param merge_algorithm {str} Resolved OpenCV merge algorithm selector.
    @return {float} Default OpenCV tone-map gamma for the selected algorithm.
    @satisfies REQ-141, REQ-143
    """

    defaults = {
        OPENCV_MERGE_ALGORITHM_DEBEVEC: DEFAULT_OPENCV_DEBEVEC_TONEMAP_GAMMA,
        OPENCV_MERGE_ALGORITHM_ROBERTSON: DEFAULT_OPENCV_ROBERTSON_TONEMAP_GAMMA,
        OPENCV_MERGE_ALGORITHM_MERTENS: DEFAULT_OPENCV_MERTENS_TONEMAP_GAMMA,
    }
    return defaults.get(
        merge_algorithm,
        defaults[DEFAULT_OPENCV_MERGE_ALGORITHM],
    )


def _parse_opencv_merge_backend_options(opencv_raw_values):
    """@brief Parse and validate OpenCV HDR merge knob values.

    @details Applies OpenCV defaults for algorithm selector, tone-map toggle,
    and tone-map gamma, validates allowed values, and returns one immutable
    backend option container for downstream merge dispatch.
    @param opencv_raw_values {dict[str, str]} Raw `--opencv-*` option values keyed by long option name.
    @return {OpenCvMergeOptions|None} Parsed OpenCV merge options or `None` on validation error.
    @satisfies REQ-141, REQ-143
    """

    options = OpenCvMergeOptions()
    merge_algorithm = options.merge_algorithm
    tonemap_enabled = options.tonemap_enabled
    tonemap_gamma = options.tonemap_gamma
    tonemap_gamma_set = False

    if "--opencv-merge-algorithm" in opencv_raw_values:
        parsed = _parse_opencv_merge_algorithm_option(
            opencv_raw_values["--opencv-merge-algorithm"]
        )
        if parsed is None:
            return None
        merge_algorithm = parsed

    if "--opencv-tonemap" in opencv_raw_values:
        parsed = _parse_explicit_boolean_option(
            "--opencv-tonemap", opencv_raw_values["--opencv-tonemap"]
        )
        if parsed is None:
            return None
        tonemap_enabled = parsed

    if "--opencv-tonemap-gamma" in opencv_raw_values:
        parsed = _parse_positive_float_option(
            "--opencv-tonemap-gamma", opencv_raw_values["--opencv-tonemap-gamma"]
        )
        if parsed is None:
            return None
        tonemap_gamma = parsed
        tonemap_gamma_set = True

    if not tonemap_gamma_set:
        tonemap_gamma = _resolve_default_opencv_tonemap_gamma(merge_algorithm)

    return OpenCvMergeOptions(
        merge_algorithm=merge_algorithm,
        tonemap_enabled=tonemap_enabled,
        tonemap_gamma=tonemap_gamma,
    )


def _parse_opencv_tonemap_backend_options(
    tonemap_selector_options,
    tonemap_knob_raw_values,
):
    """@brief Parse and validate OpenCV-Tonemap backend selector and knobs.

    @details Requires exactly one selector in `--tonemap-drago`,
    `--tonemap-reinhard`, `--tonemap-mantiuk`, applies deterministic defaults
    for optional algorithm-specific knobs, and rejects knobs that do not belong
    to the selected algorithm.
    @param tonemap_selector_options {list[str]} Ordered list of selected OpenCV-Tonemap selector options.
    @param tonemap_knob_raw_values {dict[str, str]} Raw `--tonemap-*` knob payloads keyed by option name.
    @return {OpenCvTonemapOptions|None} Parsed OpenCV-Tonemap options or `None` on validation failure.
    @satisfies REQ-190, REQ-194, REQ-195, REQ-196
    """

    selector_count = len(tonemap_selector_options)
    if selector_count != 1:
        print_error(
            "OpenCV-Tonemap requires exactly one selector: "
            + ", ".join(_OPENCV_TONEMAP_SELECTOR_OPTIONS)
        )
        return None

    selector = tonemap_selector_options[0]
    selector_map = {
        "--tonemap-drago": OPENCV_TONEMAP_MAP_DRAGO,
        "--tonemap-reinhard": OPENCV_TONEMAP_MAP_REINHARD,
        "--tonemap-mantiuk": OPENCV_TONEMAP_MAP_MANTIUK,
    }
    tonemap_map = selector_map.get(selector)
    if tonemap_map is None:
        print_error(f"Unknown OpenCV-Tonemap selector: {selector}")
        return None

    options = OpenCvTonemapOptions(tonemap_map=tonemap_map)
    drago_saturation = options.drago_saturation
    drago_bias = options.drago_bias
    reinhard_intensity = options.reinhard_intensity
    reinhard_light_adapt = options.reinhard_light_adapt
    reinhard_color_adapt = options.reinhard_color_adapt
    mantiuk_scale = options.mantiuk_scale
    mantiuk_saturation = options.mantiuk_saturation

    if "--tonemap-drago-saturation" in tonemap_knob_raw_values:
        parsed = _parse_positive_float_option(
            "--tonemap-drago-saturation",
            tonemap_knob_raw_values["--tonemap-drago-saturation"],
        )
        if parsed is None:
            return None
        drago_saturation = parsed
    if "--tonemap-drago-bias" in tonemap_knob_raw_values:
        parsed = _parse_float_in_range_option(
            "--tonemap-drago-bias",
            tonemap_knob_raw_values["--tonemap-drago-bias"],
            0.0,
            1.0,
        )
        if parsed is None:
            return None
        drago_bias = parsed
    if "--tonemap-reinhard-intensity" in tonemap_knob_raw_values:
        parsed = _parse_non_negative_float_option(
            "--tonemap-reinhard-intensity",
            tonemap_knob_raw_values["--tonemap-reinhard-intensity"],
        )
        if parsed is None:
            return None
        reinhard_intensity = parsed
    if "--tonemap-reinhard-light_adapt" in tonemap_knob_raw_values:
        parsed = _parse_float_in_range_option(
            "--tonemap-reinhard-light_adapt",
            tonemap_knob_raw_values["--tonemap-reinhard-light_adapt"],
            0.0,
            1.0,
        )
        if parsed is None:
            return None
        reinhard_light_adapt = parsed
    if "--tonemap-reinhard-color_adapt" in tonemap_knob_raw_values:
        parsed = _parse_float_in_range_option(
            "--tonemap-reinhard-color_adapt",
            tonemap_knob_raw_values["--tonemap-reinhard-color_adapt"],
            0.0,
            1.0,
        )
        if parsed is None:
            return None
        reinhard_color_adapt = parsed
    if "--tonemap-mantiuk-scale" in tonemap_knob_raw_values:
        parsed = _parse_positive_float_option(
            "--tonemap-mantiuk-scale",
            tonemap_knob_raw_values["--tonemap-mantiuk-scale"],
        )
        if parsed is None:
            return None
        mantiuk_scale = parsed
    if "--tonemap-mantiuk-saturation" in tonemap_knob_raw_values:
        parsed = _parse_positive_float_option(
            "--tonemap-mantiuk-saturation",
            tonemap_knob_raw_values["--tonemap-mantiuk-saturation"],
        )
        if parsed is None:
            return None
        mantiuk_saturation = parsed

    for knob_name in tonemap_knob_raw_values:
        if tonemap_map == OPENCV_TONEMAP_MAP_DRAGO and knob_name.startswith(
            "--tonemap-reinhard-"
        ):
            print_error(
                f"OpenCV-Tonemap knob {knob_name} requires --tonemap-reinhard selector"
            )
            return None
        if tonemap_map == OPENCV_TONEMAP_MAP_DRAGO and knob_name.startswith(
            "--tonemap-mantiuk-"
        ):
            print_error(
                f"OpenCV-Tonemap knob {knob_name} requires --tonemap-mantiuk selector"
            )
            return None
        if tonemap_map == OPENCV_TONEMAP_MAP_REINHARD and knob_name.startswith(
            "--tonemap-drago-"
        ):
            print_error(
                f"OpenCV-Tonemap knob {knob_name} requires --tonemap-drago selector"
            )
            return None
        if tonemap_map == OPENCV_TONEMAP_MAP_REINHARD and knob_name.startswith(
            "--tonemap-mantiuk-"
        ):
            print_error(
                f"OpenCV-Tonemap knob {knob_name} requires --tonemap-mantiuk selector"
            )
            return None
        if tonemap_map == OPENCV_TONEMAP_MAP_MANTIUK and knob_name.startswith(
            "--tonemap-drago-"
        ):
            print_error(
                f"OpenCV-Tonemap knob {knob_name} requires --tonemap-drago selector"
            )
            return None
        if tonemap_map == OPENCV_TONEMAP_MAP_MANTIUK and knob_name.startswith(
            "--tonemap-reinhard-"
        ):
            print_error(
                f"OpenCV-Tonemap knob {knob_name} requires --tonemap-reinhard selector"
            )
            return None

    return OpenCvTonemapOptions(
        tonemap_map=tonemap_map,
        drago_saturation=drago_saturation,
        drago_bias=drago_bias,
        reinhard_intensity=reinhard_intensity,
        reinhard_light_adapt=reinhard_light_adapt,
        reinhard_color_adapt=reinhard_color_adapt,
        mantiuk_scale=mantiuk_scale,
        mantiuk_saturation=mantiuk_saturation,
    )


def _extract_normalized_preview_luminance_stats(raw_handle):
    """@brief Extract normalized preview luminance percentiles from RAW handle.

    @details Generates one deterministic linear preview (`bright=1.0`,
    `output_bps=16`, camera white balance, no auto-bright, linear gamma,
    `user_flip=0`), computes luminance for each pixel, then returns normalized
    low/median/high percentiles by dividing with preview maximum luminance.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @return {tuple[float, float, float]} Normalized `(p_low, p_median, p_high)` in `(0,1)`.
    @exception ValueError Raised when preview extraction cannot produce valid luminance values.
    @satisfies REQ-009
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

    p_low_raw = _percentile(0.1)
    p_median_raw = _percentile(50.0)
    p_high_raw = _percentile(99.9)

    max_luminance = max(flat_luminance)
    if max_luminance <= 0.0:
        raise ValueError("Adaptive preview maximum luminance is not positive")

    epsilon = 1e-9
    p_low = max(epsilon, min(1.0 - epsilon, p_low_raw / max_luminance))
    p_high = max(epsilon, min(1.0 - epsilon, p_high_raw / max_luminance))
    p_median = max(epsilon, min(1.0 - epsilon, p_median_raw / max_luminance))
    return (p_low, p_median, p_high)


def _extract_camera_whitebalance_rgb_triplet(raw_handle):
    """@brief Extract one `(R,G,B)` camera white-balance triplet from RAW metadata.

    @details Reads `rawpy` camera white-balance payload, validates finite
    positive coefficients, and returns the first three channels as one RGB
    triplet used for float-domain gain normalization. Falls back to unit triplet
    when metadata is missing or invalid. Complexity: O(1). Side effects: none.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @return {tuple[float, float, float]} Positive finite `(r, g, b)` coefficients.
    @satisfies REQ-031, REQ-158, REQ-183
    """

    wb_raw = getattr(raw_handle, "camera_whitebalance", None)
    if wb_raw is None:
        return (1.0, 1.0, 1.0)
    try:
        wb_sequence = list(wb_raw)
    except TypeError:
        return (1.0, 1.0, 1.0)
    if len(wb_sequence) < 3:
        return (1.0, 1.0, 1.0)
    triplet = []
    for coefficient in wb_sequence[:3]:
        try:
            numeric = float(coefficient)
        except (TypeError, ValueError):
            return (1.0, 1.0, 1.0)
        if not math.isfinite(numeric) or numeric <= 0.0:
            return (1.0, 1.0, 1.0)
        triplet.append(numeric)
    return (triplet[0], triplet[1], triplet[2])


def _normalize_white_balance_gains_rgb(
    np_module,
    camera_wb_rgb,
    raw_white_balance_mode=DEFAULT_RAW_WHITE_BALANCE_MODE,
):
    """@brief Normalize one RAW camera WB gain triplet by selected mode.

    @details Converts one camera white-balance RGB triplet to float64 and
    normalizes coefficients by one mode-specific divisor: `GREEN` uses the
    green coefficient, `MAX` uses the triplet maximum,
    `MIN` uses the triplet minimum, and `MEAN` uses the arithmetic mean.
    Invalid vectors resolve to unit gains. Complexity: O(1). Side effects:
    none.
    @param np_module {ModuleType} Imported numpy module.
    @param camera_wb_rgb {tuple[float, float, float]} Positive finite camera WB RGB triplet.
    @param raw_white_balance_mode {str} RAW WB normalization mode selector.
    @return {object} Float64 RGB gain vector normalized by selected mode divisor.
    @exception ValueError Raised when the mode selector is unsupported.
    @satisfies REQ-031, REQ-158, REQ-183, REQ-203, REQ-204, REQ-205, REQ-206, REQ-207
    """

    wb_vector = np_module.asarray(camera_wb_rgb, dtype=np_module.float64)
    if wb_vector.shape != (3,):
        return np_module.asarray([1.0, 1.0, 1.0], dtype=np_module.float64)
    if not bool(np_module.all(np_module.isfinite(wb_vector))):
        return np_module.asarray([1.0, 1.0, 1.0], dtype=np_module.float64)
    if not bool(np_module.all(wb_vector > 0.0)):
        return np_module.asarray([1.0, 1.0, 1.0], dtype=np_module.float64)

    resolved_mode = str(raw_white_balance_mode).strip().upper()
    if resolved_mode == RAW_WHITE_BALANCE_MODE_GREEN:
        normalization_divisor = float(wb_vector[1])
    elif resolved_mode == RAW_WHITE_BALANCE_MODE_MAX:
        normalization_divisor = float(np_module.max(wb_vector))
    elif resolved_mode == RAW_WHITE_BALANCE_MODE_MIN:
        normalization_divisor = float(np_module.min(wb_vector))
    elif resolved_mode == RAW_WHITE_BALANCE_MODE_MEAN:
        normalization_divisor = float(np_module.mean(wb_vector))
    else:
        raise ValueError(f"Unsupported --white-balance value: {raw_white_balance_mode}")

    if not math.isfinite(normalization_divisor) or normalization_divisor <= 0.0:
        return np_module.asarray([1.0, 1.0, 1.0], dtype=np_module.float64)
    normalized = wb_vector / normalization_divisor
    if not np_module.all(np_module.isfinite(normalized)):
        return np_module.asarray([1.0, 1.0, 1.0], dtype=np_module.float64)
    normalized = np_module.maximum(normalized, 1e-12)
    return normalized.astype(np_module.float64, copy=False)


def _apply_normalized_white_balance_to_rgb_float(np_module, image_rgb_float, normalized_gains_rgb):
    """@brief Apply normalized RGB white-balance gains to one RGB float tensor.

    @details Broadcast-multiplies normalized RGB gains over one RGB float image
    in float64 precision and returns float32 without explicit clipping or
    range normalization, preserving headroom for downstream EV scaling and
    clipping stages.
    Complexity: O(H*W). Side effects: none.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} RGB float tensor.
    @param normalized_gains_rgb {object} RGB normalized gain vector with shape `(3,)`.
    @return {object} White-balanced RGB float32 tensor without stage-local clipping.
    @satisfies REQ-031, REQ-158, REQ-183
    """

    normalized_rgb = _ensure_three_channel_float_array_no_range_adjust(
        np_module=np_module,
        image_data=image_rgb_float,
    )
    gains = np_module.asarray(normalized_gains_rgb, dtype=np_module.float64).reshape((1, 1, 3))
    balanced = normalized_rgb * gains
    return balanced.astype(np_module.float32, copy=False)


def _build_rawpy_neutral_postprocess_kwargs(raw_handle):
    """@brief Build deterministic neutral `rawpy.postprocess` keyword arguments.

    @details Produces one neutral linear extraction payload with fixed fields
    (`gamma`, `no_auto_bright`, `output_bps`, `use_camera_wb`, `user_wb`,
    `output_color=rawpy.ColorSpace.raw`, `no_auto_scale`, `user_flip`) for
    deterministic RAW extraction without camera-WB application in postprocess.
    Complexity: O(1). Side effects: imports `rawpy` when module discovery from
    the handle does not expose `ColorSpace`.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @return {dict[str, object]} Keyword argument mapping for neutral RAW extraction.
    @exception RuntimeError Raised when `rawpy.ColorSpace.raw` cannot be resolved.
    @satisfies REQ-010
    """

    rawpy_module = inspect.getmodule(raw_handle)
    if rawpy_module is None:
        rawpy_module = inspect.getmodule(getattr(raw_handle, "postprocess", None))
    if rawpy_module is None or getattr(rawpy_module, "ColorSpace", None) is None:
        try:
            rawpy_module = __import__("rawpy")
        except ModuleNotFoundError as exc:
            raise RuntimeError("Missing required dependency: rawpy") from exc
    color_space = getattr(rawpy_module, "ColorSpace", None)
    raw_color = getattr(color_space, "raw", None) if color_space is not None else None
    if raw_color is None:
        raise RuntimeError("rawpy.ColorSpace.raw is unavailable")

    postprocess_kwargs = {
        "gamma": (1.0, 1.0),
        "no_auto_bright": True,
        "output_bps": 16,
        "use_camera_wb": False,
        "user_wb": [1.0, 1.0, 1.0, 1.0],
        "output_color": raw_color,
        "no_auto_scale": True,
        "user_flip": 0,
    }
    return postprocess_kwargs


def _extract_sensor_dynamic_range_max(raw_handle, np_module):
    """@brief Compute one sensor dynamic-range normalization denominator.

    @details Reads RAW metadata `white_level` and `black_level_per_channel`,
    computes `dynamic_range_max = white_level - mean(black_level_per_channel)`,
    and validates a finite positive result for neutral RAW-base normalization.
    Falls back to `white_level` when black-level payload is unavailable or
    invalid. Complexity: O(C) where C is black-level channel count. Side
    effects: none.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @param np_module {ModuleType} Imported numpy module.
    @return {float} Positive finite dynamic-range denominator.
    @exception ValueError Raised when `white_level` metadata is missing or non-positive.
    @satisfies REQ-158
    """

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
        white_level_float = float(white_level_value)
    except (TypeError, ValueError):
        raise ValueError(
            f"RAW metadata white_level is non-numeric: {white_level_value!r}"
        ) from None
    if not math.isfinite(white_level_float) or white_level_float <= 0.0:
        raise ValueError(
            f"RAW metadata white_level must be finite and positive: {white_level_float!r}"
        )

    black_levels_raw = getattr(raw_handle, "black_level_per_channel", None)
    if black_levels_raw is None:
        black_level_mean = 0.0
    else:
        try:
            black_levels_vector = np_module.asarray(black_levels_raw, dtype=np_module.float64)
        except (TypeError, ValueError):
            black_levels_vector = np_module.asarray([], dtype=np_module.float64)
        if black_levels_vector.size == 0:
            black_level_mean = 0.0
        else:
            black_level_mean = float(np_module.mean(black_levels_vector))
            if not math.isfinite(black_level_mean):
                black_level_mean = 0.0
    dynamic_range_max = white_level_float - black_level_mean
    if not math.isfinite(dynamic_range_max) or dynamic_range_max <= 0.0:
        dynamic_range_max = white_level_float
    if not math.isfinite(dynamic_range_max) or dynamic_range_max <= 0.0:
        raise ValueError("RAW metadata dynamic range is non-positive")
    return float(dynamic_range_max)


def _extract_base_rgb_linear_float(
    raw_handle,
    np_module,
    raw_white_balance_mode=DEFAULT_RAW_WHITE_BALANCE_MODE,
):
    """@brief Extract one linear normalized RGB base image from one RAW handle.

    @details Executes exactly one neutral linear `rawpy.postprocess` call with
    deterministic no-auto/no-camera-WB parameters, converts output to float,
    normalizes by sensor dynamic range `white_level - mean(black_level_per_channel)`,
    extracts camera WB metadata gains, normalizes gains by one selected mode
    (`GREEN`, `MAX`, `MIN`, `MEAN`), and applies those gains in float domain
    without explicit clipping. Complexity: O(H*W). Side effects: one RAW
    postprocess invocation.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @param np_module {ModuleType} Imported numpy module.
    @param raw_white_balance_mode {str} RAW WB normalization mode selector.
    @return {object} White-balanced RGB float tensor derived from neutral extraction.
    @satisfies REQ-010, REQ-031, REQ-158, REQ-203, REQ-204, REQ-205, REQ-206, REQ-207
    @see _extract_normalized_preview_luminance_stats
    """

    postprocess_kwargs = _build_rawpy_neutral_postprocess_kwargs(raw_handle=raw_handle)
    base_rgb = raw_handle.postprocess(**postprocess_kwargs)
    dynamic_range_max = _extract_sensor_dynamic_range_max(
        raw_handle=raw_handle,
        np_module=np_module,
    )
    base_rgb_float = np_module.asarray(base_rgb, dtype=np_module.float32)
    normalized_base_rgb = base_rgb_float / np_module.float32(dynamic_range_max)
    camera_wb_rgb = _extract_camera_whitebalance_rgb_triplet(raw_handle=raw_handle)
    normalized_gains_rgb = _normalize_white_balance_gains_rgb(
        np_module=np_module,
        camera_wb_rgb=camera_wb_rgb,
        raw_white_balance_mode=raw_white_balance_mode,
    )
    return _apply_normalized_white_balance_to_rgb_float(
        np_module=np_module,
        image_rgb_float=normalized_base_rgb,
        normalized_gains_rgb=normalized_gains_rgb,
    )


def _normalize_source_gamma_label(label_raw):
    """@brief Normalize one source-gamma label token.

    @details Trims surrounding whitespace, collapses empty values to `unknown`,
    and preserves the remaining token verbatim for deterministic runtime
    diagnostics.
    @param label_raw {object} Candidate label payload derived from RAW metadata.
    @return {str} Normalized diagnostic label.
    @satisfies REQ-163, REQ-164
    """

    if label_raw is None:
        return "unknown"
    label_text = str(label_raw).strip()
    if not label_text:
        return "unknown"
    return label_text


def _decode_raw_metadata_text(metadata_raw):
    """@brief Decode one RAW metadata token to deterministic text.

    @details Accepts `bytes`, `bytearray`, `str`, and sequence-like metadata
    payloads, strips null terminators, joins sequence entries with `/`, and
    returns `None` when no stable textual representation exists.
    @param metadata_raw {object} Candidate RAW metadata payload.
    @return {str|None} Normalized text token or `None`.
    @satisfies REQ-163
    """

    if metadata_raw is None:
        return None
    if isinstance(metadata_raw, (bytes, bytearray)):
        decoded = bytes(metadata_raw).decode("utf-8", errors="ignore")
        normalized = decoded.replace("\x00", "").strip()
        return normalized or None
    if isinstance(metadata_raw, str):
        normalized = metadata_raw.replace("\x00", "").strip()
        return normalized or None
    if isinstance(metadata_raw, (tuple, list)):
        parts = []
        for item in metadata_raw:
            part = _decode_raw_metadata_text(item)
            if part:
                parts.append(part)
        if not parts:
            return None
        return "/".join(parts)
    return None


def _classify_explicit_source_gamma(raw_handle):
    """@brief Classify source gamma from explicit profile or color-space metadata.

    @details Inspects common RAW metadata attributes that can already carry an
    explicit transfer-function declaration, maps recognized tokens to
    deterministic label/gamma pairs, and returns `None` when no explicit
    classification is available.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @return {SourceGammaInfo|None} Classified explicit profile diagnostic or `None`.
    @satisfies REQ-157, REQ-163
    """

    explicit_fields = (
        "color_space",
        "output_color",
        "profile_name",
        "icc_profile_name",
        "color_profile",
    )
    field_values = []
    for field_name in explicit_fields:
        field_text = _decode_raw_metadata_text(getattr(raw_handle, field_name, None))
        if field_text:
            field_values.append(field_text)
    if not field_values:
        return None
    combined_text = " ".join(field_values).lower()
    explicit_profiles = (
        ("srgb", "sRGB", 2.2),
        ("rec709", "Rec.709", 2.2),
        ("bt709", "BT.709", 2.2),
        ("adobe", "Adobe RGB", 2.2),
        ("display p3", "Display P3", 2.2),
        ("prophoto", "ProPhoto RGB", 1.8),
        ("linear", "Linear", 1.0),
    )
    for token, label, gamma_value in explicit_profiles:
        if token in combined_text:
            return SourceGammaInfo(
                label=label,
                gamma_value=gamma_value,
                evidence="explicit-profile",
            )
    return SourceGammaInfo(
        label=_normalize_source_gamma_label(field_values[0]),
        gamma_value=None,
        evidence="explicit-profile",
    )


def _classify_tone_curve_gamma(raw_handle):
    """@brief Classify source gamma from `rawpy.tone_curve` metadata.

    @details Reads the optional tone-curve payload, estimates one effective
    power-law gamma from valid interior samples, and suppresses the result when
    the curve is absent, too short, degenerate, or non-finite.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @return {SourceGammaInfo|None} Tone-curve diagnostic or `None`.
    @satisfies REQ-157, REQ-163
    """

    tone_curve = getattr(raw_handle, "tone_curve", None)
    if tone_curve is None or len(tone_curve) < 16:
        return None
    max_index = float(len(tone_curve) - 1)
    max_value = max(float(max(tone_curve)), 0.0)
    if max_index <= 0.0 or max_value <= 0.0:
        return None
    gamma_estimates = []
    for sample_point in (0.25, 0.50, 0.75):
        sample_index = int(round(sample_point * max_index))
        if sample_index <= 0 or sample_index >= len(tone_curve):
            continue
        x_value = sample_index / max_index
        y_value = float(tone_curve[sample_index]) / max_value
        if x_value <= 0.0 or y_value <= 0.0 or y_value >= 1.0:
            continue
        gamma_estimates.append(math.log(x_value) / math.log(y_value))
    if not gamma_estimates:
        return None
    gamma_value = sum(gamma_estimates) / len(gamma_estimates)
    if not math.isfinite(gamma_value) or gamma_value <= 0.0:
        return None
    rounded_gamma = round(gamma_value, 4)
    if abs(rounded_gamma - 1.0) <= 0.1:
        label = "Linear"
    elif abs(rounded_gamma - 1.8) <= 0.2:
        label = "Tone curve gamma 1.8"
    elif abs(rounded_gamma - 2.2) <= 0.2:
        label = "Tone curve gamma 2.2"
    else:
        label = "Tone curve gamma"
    return SourceGammaInfo(
        label=label,
        gamma_value=rounded_gamma,
        evidence="tone-curve",
    )


def _has_nonzero_matrix(matrix_raw):
    """@brief Determine whether one RAW metadata matrix carries non-zero values.

    @details Iterates nested list/tuple/numpy-like matrix payloads and returns
    `True` when any element coerces to a finite non-zero scalar.
    @param matrix_raw {object} Candidate RAW metadata matrix.
    @return {bool} `True` when matrix evidence is non-zero.
    @satisfies REQ-163
    """

    if matrix_raw is None:
        return False
    if isinstance(matrix_raw, (tuple, list)):
        return any(_has_nonzero_matrix(item) for item in matrix_raw)
    try:
        matrix_value = float(matrix_raw)
    except (TypeError, ValueError):
        return False
    return math.isfinite(matrix_value) and matrix_value != 0.0


def _classify_matrix_hint_gamma(raw_handle):
    """@brief Classify source gamma from matrix and color-description hints.

    @details Uses `rgb_xyz_matrix`, `color_matrix`, and `color_desc` as weaker
    evidence than explicit profiles or tone curves. Numeric gamma remains
    undetermined for this class of evidence.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @return {SourceGammaInfo|None} Matrix-hint diagnostic or `None`.
    @satisfies REQ-157, REQ-163
    """

    rgb_xyz_present = _has_nonzero_matrix(getattr(raw_handle, "rgb_xyz_matrix", None))
    color_matrix_present = _has_nonzero_matrix(getattr(raw_handle, "color_matrix", None))
    color_desc = _decode_raw_metadata_text(getattr(raw_handle, "color_desc", None))
    if not rgb_xyz_present and not color_matrix_present and color_desc is None:
        return None
    if color_desc:
        label = f"Camera color metadata ({color_desc})"
    elif rgb_xyz_present and color_matrix_present:
        label = "Camera color metadata"
    elif rgb_xyz_present:
        label = "RGB-XYZ metadata"
    else:
        label = "Color matrix metadata"
    return SourceGammaInfo(
        label=label,
        gamma_value=None,
        evidence="matrix-hint",
    )


def _extract_source_gamma_info(raw_handle):
    """@brief Derive source-gamma diagnostics from RAW metadata only.

    @details Applies deterministic evidence priority: explicit profile or
    color-space metadata first, then `rawpy.tone_curve`, then weaker camera
    color-matrix hints (`rgb_xyz_matrix`, `color_matrix`, `color_desc`), and
    finally emits `unknown` when no metadata source can support classification.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @return {SourceGammaInfo} Deterministic source-gamma diagnostic payload.
    @satisfies REQ-157, REQ-163
    """

    explicit_info = _classify_explicit_source_gamma(raw_handle)
    if explicit_info is not None:
        return explicit_info
    tone_curve_info = _classify_tone_curve_gamma(raw_handle)
    if tone_curve_info is not None:
        return tone_curve_info
    matrix_hint_info = _classify_matrix_hint_gamma(raw_handle)
    if matrix_hint_info is not None:
        return matrix_hint_info
    return SourceGammaInfo(
        label="unknown",
        gamma_value=None,
        evidence="insufficient-metadata",
    )


def _describe_source_gamma_info(source_gamma_info):
    """@brief Format one deterministic source-gamma runtime diagnostic line.

    @details Renders one stable `print_info` payload that always includes both a
    source-gamma label and a numeric gamma value or the literal
    `undetermined`.
    @param source_gamma_info {SourceGammaInfo} Derived source-gamma metadata payload.
    @return {str} Deterministic runtime diagnostic line.
    @satisfies REQ-164
    """

    gamma_text = "undetermined"
    if source_gamma_info.gamma_value is not None:
        gamma_text = f"{source_gamma_info.gamma_value:g}"
    return (
        "Source gamma info: "
        f"label={source_gamma_info.label}; "
        f"gamma={gamma_text}; "
        f"evidence={source_gamma_info.evidence}"
    )


def _coerce_positive_luminance(value, fallback):
    """@brief Coerce luminance scalar to positive range for logarithmic math.

    @details Converts input to float and enforces a strictly positive minimum.
    Returns fallback when conversion fails or result is non-positive.
    @param value {object} Candidate luminance scalar.
    @param fallback {float} Fallback positive luminance scalar.
    @return {float} Positive luminance value suitable for `log2`.
    @satisfies REQ-031
    """

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return fallback
    if numeric_value <= 0.0:
        return fallback
    return numeric_value


def _calculate_bt709_luminance(np_module, image_rgb_float):
    """@brief Convert one normalized RGB float image to BT.709 luminance.

    @details Normalizes the input image to the repository RGB float contract and
    computes luminance in the linear gamma=`1` domain using BT.709 coefficients
    `(0.2126, 0.7152, 0.0722)`. Complexity: O(H*W). Side effects: none.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} Input image payload convertible to normalized RGB float `[0,1]`.
    @return {object} Linear luminance tensor with shape `(H,W)` and dtype `float32`.
    @satisfies REQ-008, REQ-032
    """

    normalized_rgb = _normalize_float_rgb_image(
        np_module=np_module,
        image_data=image_rgb_float,
    )
    return (
        (0.2126 * normalized_rgb[:, :, 0])
        + (0.7152 * normalized_rgb[:, :, 1])
        + (0.0722 * normalized_rgb[:, :, 2])
    ).astype(np_module.float32)


def _smoothstep(np_module, values, edge0, edge1):
    """@brief Evaluate one smoothstep ramp with clamped normalized input.

    @details Computes the cubic Hermite interpolation `t*t*(3-2*t)` over input
    values normalized into `[0,1]` using denominator `max(edge1-edge0, 1e-6)`.
    Complexity: O(N). Side effects: none.
    @param np_module {ModuleType} Imported numpy module.
    @param values {object} Numeric tensor evaluated element-wise.
    @param edge0 {float} Lower transition edge.
    @param edge1 {float} Upper transition edge.
    @return {object} Float tensor with values in `[0,1]`.
    @satisfies REQ-032
    """

    denominator = max(float(edge1) - float(edge0), 1e-6)
    normalized = np_module.clip((values - float(edge0)) / denominator, 0.0, 1.0)
    return normalized * normalized * (3.0 - (2.0 * normalized))


def _calculate_entropy_optimized_ev(_cv2_module, np_module, luminance_float):
    """@brief Compute the entropy-optimized EV candidate on linear luminance.

    @details Sweeps EV values in range `[-3.0,+3.0]` with step `0.1`, scales the
    normalized linear luminance by `2**EV`, clips into `[0,1]`, converts the
    clipped image directly to 8-bit linear code values, evaluates histogram
    entropy with clipping penalties, and returns the highest-score EV rounded to
    one decimal place. Complexity: O(K*H*W)` where `K=61`. Side effects: none.
    @param cv2_module {ModuleType|None} Optional OpenCV module retained for call compatibility.
    @param np_module {ModuleType} Imported numpy module.
    @param luminance_float {object} Linear luminance tensor normalized to `[0,1]`.
    @return {float} Entropy-optimized EV candidate rounded to one decimal place.
    @satisfies REQ-032
    """

    best_ev = 0.0
    max_score = -float("inf")
    alpha = 50.0
    beta = 20.0
    candidate_values = np_module.arange(-3.0, 3.1, 0.1, dtype=np_module.float32)
    for ev_value in candidate_values:
        simulated = np_module.clip(
            luminance_float.astype(np_module.float32) * (2.0 ** float(ev_value)),
            0.0,
            1.0,
        )
        luminance_8bit = (simulated * 255.0).astype(np_module.uint8)
        histogram = np_module.bincount(luminance_8bit.ravel(), minlength=256)
        histogram = histogram.astype(np_module.float64)
        histogram_sum = float(histogram.sum())
        if histogram_sum <= 0.0:
            continue
        probabilities = histogram / histogram_sum
        non_zero_probabilities = probabilities[probabilities > 0.0]
        entropy = -float(
            np_module.sum(non_zero_probabilities * np_module.log2(non_zero_probabilities))
        )
        p_0 = float(probabilities[0])
        p_255 = float(probabilities[255])
        score = entropy - (alpha * (p_255**2)) - (beta * (p_0**2))
        if score > max_score:
            max_score = score
            best_ev = float(ev_value)
    return round(best_ev, 1)


def _calculate_ettr_ev(np_module, luminance_float):
    """@brief Compute the ETTR EV candidate on linear luminance.

    @details Evaluates the `99`th percentile of normalized linear luminance,
    targets that percentile to `0.90`, computes `log2(target/L99)`, and returns
    the result rounded to one decimal place. Fully black inputs return `0.0`.
    Complexity: O(H*W log(H*W)) due to percentile extraction. Side effects:
    none.
    @param np_module {ModuleType} Imported numpy module.
    @param luminance_float {object} Linear luminance tensor normalized to `[0,1]`.
    @return {float} ETTR EV candidate rounded to one decimal place.
    @satisfies REQ-032
    """

    luminance_p99 = float(np_module.percentile(luminance_float, 99.0))
    if luminance_p99 <= 0.0:
        return 0.0
    return round(math.log2(0.90 / luminance_p99), 1)


def _calculate_detail_preservation_ev(_cv2_module, np_module, luminance_float):
    """@brief Compute the detail-preservation EV candidate on linear luminance.

    @details Builds local-detail weights from Sobel gradients on
    `log(luminance+eps)`, suppresses flat regions below the `40`th percentile,
    estimates a heuristic noise floor from the `1`st percentile, sweeps EV in
    `[-3.0,+3.0]` with step `0.1`, and maximizes preserved weighted detail while
    penalizing highlight clipping and shadow crushing. Returns the best EV
    rounded to one decimal place. Complexity: O(K*H*W)` where `K=61`. Side
    effects: none.
    @param cv2_module {ModuleType} Imported OpenCV module.
    @param np_module {ModuleType} Imported numpy module.
    @param luminance_float {object} Linear luminance tensor normalized to `[0,1]`.
    @return {float} Detail-preservation EV candidate rounded to one decimal place.
    @satisfies REQ-032
    """

    luminance_float32 = np_module.array(luminance_float, dtype=np_module.float32, copy=False)
    epsilon = 1e-6
    log_luminance = np_module.log(luminance_float32 + epsilon)
    if min(log_luminance.shape) < 2:
        detail_map = np_module.zeros_like(log_luminance, dtype=np_module.float32)
    else:
        gradient_y, gradient_x = np_module.gradient(log_luminance)
        detail_map = np_module.sqrt((gradient_x * gradient_x) + (gradient_y * gradient_y))
    texture_threshold = float(np_module.percentile(detail_map, 40.0))
    detail_map = np_module.where(detail_map >= texture_threshold, detail_map, 0.0).astype(
        np_module.float32
    )
    detail_sum = float(detail_map.sum())
    if detail_sum <= 0.0:
        return 0.0
    weights = detail_map / (detail_sum + epsilon)
    p1 = float(np_module.percentile(luminance_float32, 1.0))
    noise_floor = float(np_module.clip(max(0.005, p1 * 0.5), 0.005, 0.02))
    shadow_target = max(noise_floor + 0.03, 0.05)
    highlight_knee = 0.98
    lambda_high = 4.0
    lambda_shadow = 1.5
    best_ev = 0.0
    best_score = -float("inf")
    candidate_values = np_module.arange(-3.0, 3.1, 0.1, dtype=np_module.float32)
    for ev_value in candidate_values:
        simulated = luminance_float32 * (2.0 ** float(ev_value))
        shadow_weight = _smoothstep(
            np_module=np_module,
            values=simulated,
            edge0=noise_floor,
            edge1=shadow_target,
        )
        highlight_weight = 1.0 - _smoothstep(
            np_module=np_module,
            values=simulated,
            edge0=highlight_knee,
            edge1=1.0,
        )
        preserved_detail = float(np_module.sum(weights * shadow_weight * highlight_weight))
        clipped_fraction = float(np_module.sum(weights[simulated >= 1.0]))
        crushed_fraction = float(np_module.sum(weights[simulated <= noise_floor]))
        score = preserved_detail - (lambda_high * clipped_fraction) - (
            lambda_shadow * crushed_fraction
        )
        if score > best_score:
            best_score = score
            best_ev = float(ev_value)
    return round(best_ev, 1)


def _calculate_auto_zero_evaluations(cv2_module, np_module, image_rgb_float):
    """@brief Compute the three automatic EV-zero candidate evaluations.

    @details Migrates `calcola_correzioni_ev(immagine_float)` from the external
    prototype into the current pipeline, adapts it to the repository linear
    gamma=`1` RGB float contract, computes BT.709 luminance, evaluates
    `ev_best`, `ev_ettr`, and `ev_detail`, and returns all three rounded
    candidates without applying selector quantization. Complexity: dominated by
    the EV sweeps in entropy/detail evaluation. Side effects: none.
    @param cv2_module {ModuleType} Imported OpenCV module.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} Input image payload convertible to normalized RGB float `[0,1]`.
    @return {AutoZeroEvaluation} Candidate EV evaluations on the normalized linear image.
    @satisfies REQ-008, REQ-032
    """

    luminance_float = _calculate_bt709_luminance(
        np_module=np_module,
        image_rgb_float=image_rgb_float,
    )
    return AutoZeroEvaluation(
        ev_best=_calculate_entropy_optimized_ev(
            cv2_module,
            np_module,
            luminance_float,
        ),
        ev_ettr=_calculate_ettr_ev(
            np_module=np_module,
            luminance_float=luminance_float,
        ),
        ev_detail=_calculate_detail_preservation_ev(
            cv2_module,
            np_module,
            luminance_float,
        ),
    )


def _select_ev_zero_candidate(evaluations):
    """@brief Select `ev_zero` from the exposure-measure EV triplet.

    @details Selects the minimum absolute-value EV candidate using deterministic
    tie-break order `abs(value) -> declaration order -> numeric value` without
    applying bit-depth-derived clamping.
    @param evaluations {AutoZeroEvaluation} Exposure-measure EV values.
    @return {tuple[float, str]} Selected `(ev_zero, source_label)` pair.
    @satisfies REQ-032
    """

    candidates = (
        ("ev_best", evaluations.ev_best),
        ("ev_ettr", evaluations.ev_ettr),
        ("ev_detail", evaluations.ev_detail),
    )
    best = None
    for index, (label, raw_value) in enumerate(candidates):
        candidate_value = float(raw_value)
        sort_key = (round(abs(candidate_value), 9), index, round(candidate_value, 9))
        if best is None or sort_key < best[0]:
            best = (sort_key, candidate_value, label)
    if best is None:
        raise ValueError("Exposure-measure EV selection requires at least one candidate")
    _, selected_value, selected_label = best
    return (selected_value, selected_label)



def _build_unclipped_bracket_images_from_linear_base_float(
    np_module,
    base_rgb_float,
    ev_delta,
    ev_zero,
):
    """@brief Build unclipped bracket tensors from the shared linear base image.

    @details Applies exposure multipliers for `ev_zero-ev_delta`, `ev_zero`, and
    `ev_zero+ev_delta` without clipping to `[0,1]`.
    @param np_module {ModuleType} Imported numpy module.
    @param base_rgb_float {object} Normalized linear base RGB tensor.
    @param ev_delta {float} Symmetric bracket half-span.
    @param ev_zero {float} Bracket center EV.
    @return {tuple[object, object, object]} Unclipped `(ev_minus, ev_zero, ev_plus)` tensors.
    @satisfies REQ-167
    """

    normalized_base = _normalize_float_rgb_image(
        np_module=np_module,
        image_data=base_rgb_float,
    ).astype(np_module.float32, copy=False)
    minus_multiplier, center_multiplier, plus_multiplier = _build_exposure_multipliers(
        ev_delta,
        ev_zero=ev_zero,
    )
    return (
        normalized_base * minus_multiplier,
        normalized_base * center_multiplier,
        normalized_base * plus_multiplier,
    )



def _measure_any_channel_highlight_clipping_pct(np_module, image_rgb_float):
    """@brief Measure highlight clipping percentage for one RGB image.

    @details Counts pixels where any RGB channel is greater than or equal to
    `1` and returns the result in percent.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} RGB image tensor.
    @return {float} Highlight clipping percentage in `0..100`.
    @satisfies REQ-168
    """

    return round(
        float(np_module.mean(np_module.any(image_rgb_float >= 1.0, axis=2)) * 100.0),
        6,
    )



def _measure_any_channel_shadow_clipping_pct(np_module, image_rgb_float):
    """@brief Measure shadow clipping percentage for one RGB image.

    @details Counts pixels where any RGB channel is less than or equal to `0`
    and returns the result in percent.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} RGB image tensor.
    @return {float} Shadow clipping percentage in `0..100`.
    @satisfies REQ-168
    """

    return round(
        float(np_module.mean(np_module.any(image_rgb_float <= 0.0, axis=2)) * 100.0),
        6,
    )



def _resolve_joint_auto_ev_solution(
    auto_ev_options,
    auto_adjust_dependencies=None,
    base_rgb_float=None,
):
    """@brief Resolve the automatic symmetric exposure plan.

    @details Loads numeric dependencies, computes the exposure-measure EV
    triplet from one normalized linear base image, selects `ev_zero` by minimum
    absolute value, and expands bracket half-span iteratively until clipping
    thresholds are reached.
    @param auto_ev_options {AutoEvOptions} Automatic clipping thresholds and EV increment.
    @param auto_adjust_dependencies {tuple[ModuleType, ModuleType]|None} Optional `(cv2_module, numpy_module)` tuple.
    @param base_rgb_float {object|None} Optional precomputed normalized linear base RGB image.
    @return {JointAutoEvSolution} Selected joint automatic exposure solution.
    @exception RuntimeError Raised when required `cv2` or `numpy` dependencies are unavailable.
    @satisfies REQ-008, REQ-009, REQ-031, REQ-032, REQ-037, REQ-052, REQ-167, REQ-168
    """

    if auto_adjust_dependencies is None:
        np_module = _resolve_numpy_dependency()
        if np_module is None:
            raise RuntimeError("Missing required dependency: numpy")
        cv2_module = None
    else:
        resolved_dependencies = auto_adjust_dependencies
        if resolved_dependencies is None:
            raise RuntimeError("Missing required dependency tuple")
        cv2_module, np_module = resolved_dependencies
    if base_rgb_float is None:
        raise ValueError("Automatic exposure planning requires base_rgb_float")
    evaluations = _calculate_auto_zero_evaluations(
        cv2_module=cv2_module,
        np_module=np_module,
        image_rgb_float=base_rgb_float,
    )
    selected_ev_zero, selected_source = _select_ev_zero_candidate(
        evaluations=evaluations,
    )
    ev_delta = float(auto_ev_options.step)
    iteration_steps = []
    while True:
        ev_minus, _ev_center, ev_plus = _build_unclipped_bracket_images_from_linear_base_float(
            np_module=np_module,
            base_rgb_float=base_rgb_float,
            ev_delta=ev_delta,
            ev_zero=selected_ev_zero,
        )
        shadow_pct = _measure_any_channel_shadow_clipping_pct(np_module, ev_minus)
        highlight_pct = _measure_any_channel_highlight_clipping_pct(np_module, ev_plus)
        iteration_steps.append(
            AutoEvIterationStep(
                ev_delta=round(ev_delta, 6),
                shadow_clipping_pct=shadow_pct,
                highlight_clipping_pct=highlight_pct,
            )
        )
        if (
            highlight_pct >= auto_ev_options.highlight_clipping_pct
            or shadow_pct > auto_ev_options.shadow_clipping_pct
        ):
            break
        ev_delta += auto_ev_options.step
    print_info(f"Exposure Misure EV ev_best: {evaluations.ev_best:+.1f} EV")
    print_info(f"Exposure Misure EV ev_ettr: {evaluations.ev_ettr:+.1f} EV")
    print_info(f"Exposure Misure EV ev_detail: {evaluations.ev_detail:+.1f} EV")
    print_info(
        "Exposure planning selected ev_zero: "
        f"{selected_ev_zero:+.6f} EV (source={selected_source})"
    )
    for step in iteration_steps:
        print_info(
            "Bracket step: "
            f"ev_delta={step.ev_delta:.6f}, "
            f"shadow_clipping_pct={step.shadow_clipping_pct:.6f}, "
            f"highlight_clipping_pct={step.highlight_clipping_pct:.6f}"
        )
    print_info(
        "Exposure planning selected bracket half-span: "
        f"{iteration_steps[-1].ev_delta:.6f} EV"
    )
    return JointAutoEvSolution(
        ev_zero=round(selected_ev_zero, 6),
        ev_delta=round(iteration_steps[-1].ev_delta, 6),
        selected_source=selected_source,
        iteration_steps=tuple(iteration_steps),
    )


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


def _parse_luminance_response_curve_option(option_raw):
    """@brief Parse one luminance response-curve selector under the linear backend contract.

    @details Normalizes one raw `--luminance-hdr-response-curve` token through
    the shared luminance text parser, then enforces the repository luminance
    backend contract requiring deterministic `linear` response-curve forwarding.
    Complexity: `O(n)` in token length. Side effects: emits deterministic parse
    diagnostics on invalid values.
    @param option_raw {str} Raw CLI payload for `--luminance-hdr-response-curve`.
    @return {str|None} Canonical `linear` token when valid; `None` otherwise.
    @satisfies REQ-011
    """

    option_value = _parse_luminance_text_option(
        "--luminance-hdr-response-curve", option_raw
    )
    if option_value is None:
        return None
    if option_value != DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE:
        print_error(
            "--luminance-hdr-response-curve only accepts "
            f"`{DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE}`"
        )
        return None
    return option_value


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


def _parse_post_gamma_selector_option(option_raw):
    """@brief Parse `--post-gamma` selector as numeric factor or `auto`.

    @details Accepts one positive float token for numeric static gamma mode or
    literal `auto` for auto-gamma replacement mode.
    @param option_raw {str} Raw `--post-gamma` value token from CLI args.
    @return {tuple[float, str]|None} `(post_gamma_value, mode)` where `mode` is `numeric` or `auto`; `None` on parse failure.
    @satisfies REQ-176
    """

    normalized = str(option_raw).strip()
    if not normalized:
        print_error("Invalid --post-gamma value: empty value")
        return None
    if normalized.lower() == "auto":
        return (DEFAULT_POST_GAMMA, "auto")
    parsed = _parse_positive_float_option("--post-gamma", normalized)
    if parsed is None:
        return None
    return (parsed, "numeric")


def _parse_positive_int_option(option_name, option_raw):
    """@brief Parse and validate one positive integer option value.

    @details Converts option token to `int`, requires value greater than zero,
    and emits deterministic parse errors on malformed values.
    @param option_name {str} Long-option identifier used in error messages.
    @param option_raw {str} Raw option token value from CLI args.
    @return {int|None} Parsed positive integer value when valid; `None` otherwise.
    @satisfies REQ-127, REQ-130
    """

    try:
        option_value = int(option_raw)
    except ValueError:
        print_error(f"Invalid {option_name} value: {option_raw}")
        return None

    if option_value <= 0:
        print_error(f"Invalid {option_name} value: {option_raw}")
        print_error(f"{option_name} must be greater than zero.")
        return None
    return option_value


def _parse_post_gamma_auto_options(post_gamma_auto_raw_values):
    """@brief Parse and validate post-gamma auto replacement knobs.

    @details Applies deterministic defaults for omitted knobs, validates
    target-gray and luminance guards as exclusive `(0,1)` bounds, validates LUT
    size as integer `>=2`, and enforces `luma_min < luma_max`.
    @param post_gamma_auto_raw_values {dict[str, str]} Raw `--post-gamma-auto-*` option values keyed by long option name.
    @return {PostGammaAutoOptions|None} Parsed auto-gamma options or `None` on validation error.
    @satisfies REQ-177, REQ-179
    """

    options = PostGammaAutoOptions()
    target_gray = options.target_gray
    luma_min = options.luma_min
    luma_max = options.luma_max
    lut_size = options.lut_size

    if "--post-gamma-auto-target-gray" in post_gamma_auto_raw_values:
        parsed = _parse_float_exclusive_range_option(
            "--post-gamma-auto-target-gray",
            post_gamma_auto_raw_values["--post-gamma-auto-target-gray"],
            0.0,
            1.0,
        )
        if parsed is None:
            return None
        target_gray = parsed
    if "--post-gamma-auto-luma-min" in post_gamma_auto_raw_values:
        parsed = _parse_float_exclusive_range_option(
            "--post-gamma-auto-luma-min",
            post_gamma_auto_raw_values["--post-gamma-auto-luma-min"],
            0.0,
            1.0,
        )
        if parsed is None:
            return None
        luma_min = parsed
    if "--post-gamma-auto-luma-max" in post_gamma_auto_raw_values:
        parsed = _parse_float_exclusive_range_option(
            "--post-gamma-auto-luma-max",
            post_gamma_auto_raw_values["--post-gamma-auto-luma-max"],
            0.0,
            1.0,
        )
        if parsed is None:
            return None
        luma_max = parsed
    if luma_min >= luma_max:
        print_error(
            "Invalid post-gamma auto guards: --post-gamma-auto-luma-min must be lower than --post-gamma-auto-luma-max"
        )
        return None
    if "--post-gamma-auto-lut-size" in post_gamma_auto_raw_values:
        parsed = _parse_positive_int_option(
            "--post-gamma-auto-lut-size",
            post_gamma_auto_raw_values["--post-gamma-auto-lut-size"],
        )
        if parsed is None:
            return None
        if parsed < 2:
            print_error(
                "Invalid --post-gamma-auto-lut-size value: "
                f"{post_gamma_auto_raw_values['--post-gamma-auto-lut-size']}"
            )
            print_error("--post-gamma-auto-lut-size must be greater than or equal to 2.")
            return None
        lut_size = parsed

    return PostGammaAutoOptions(
        target_gray=target_gray,
        luma_min=luma_min,
        luma_max=luma_max,
        lut_size=lut_size,
    )


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


def _parse_positive_int_pair_option(option_name, option_raw):
    """@brief Parse and validate one positive integer pair option value.

    @details Accepts `rowsxcols`, `rowsXcols`, or `rows,cols`, converts both
    tokens to `int`, requires each value to be greater than zero, and emits
    deterministic parse errors on malformed values.
    @param option_name {str} Long-option identifier used in error messages.
    @param option_raw {str} Raw option token value from CLI args.
    @return {tuple[int, int]|None} Parsed positive integer pair when valid; `None` otherwise.
    @satisfies REQ-065, REQ-125
    """

    normalized_value = option_raw.lower().replace("x", ",")
    parts = [part.strip() for part in normalized_value.split(",")]
    if len(parts) != 2 or parts[0] == "" or parts[1] == "":
        print_error(f"Invalid {option_name} value: {option_raw}")
        print_error(f"Expected format: {option_name}=<rows>x<cols>")
        return None
    try:
        rows = int(parts[0])
        cols = int(parts[1])
    except ValueError:
        print_error(f"Invalid {option_name} value: {option_raw}")
        print_error("Tile grid size values must be integers.")
        return None
    if rows <= 0 or cols <= 0:
        print_error(f"Invalid {option_name} value: {option_raw}")
        print_error("Tile grid size values must be greater than zero.")
        return None
    return (rows, cols)


def _parse_auto_brightness_options(auto_brightness_raw_values):
    """@brief Parse and validate auto-brightness parameters.

    @details Parses optional controls for the original photographic BT.709
    float-domain tonemap pipeline and applies deterministic defaults for omitted
    auto-brightness options.
    @param auto_brightness_raw_values {dict[str, str]} Raw `--ab-*` option values keyed by long option name.
    @return {AutoBrightnessOptions|None} Parsed auto-brightness options or `None` on validation error.
    @satisfies REQ-088, REQ-089, REQ-103, REQ-104, REQ-105, REQ-124, REQ-135
    """

    defaults = AutoBrightnessOptions()
    key_value = defaults.key_value
    white_point_percentile = defaults.white_point_percentile
    a_min = defaults.a_min
    a_max = defaults.a_max
    max_auto_boost_factor = defaults.max_auto_boost_factor
    enable_luminance_preserving_desat = defaults.enable_luminance_preserving_desat
    eps = defaults.eps

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
        a_min = parsed

    if "--ab-key-max" in auto_brightness_raw_values:
        parsed = _parse_positive_float_option(
            "--ab-key-max", auto_brightness_raw_values["--ab-key-max"]
        )
        if parsed is None:
            return None
        a_max = parsed

    if a_min > a_max:
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

    if "--ab-enable-luminance-preserving-desat" in auto_brightness_raw_values:
        parsed = _parse_explicit_boolean_option(
            "--ab-enable-luminance-preserving-desat",
            auto_brightness_raw_values["--ab-enable-luminance-preserving-desat"],
        )
        if parsed is None:
            return None
        enable_luminance_preserving_desat = parsed

    if "--ab-eps" in auto_brightness_raw_values:
        parsed = _parse_positive_float_option(
            "--ab-eps", auto_brightness_raw_values["--ab-eps"]
        )
        if parsed is None:
            return None
        eps = parsed

    return AutoBrightnessOptions(
        key_value=key_value,
        white_point_percentile=white_point_percentile,
        a_min=a_min,
        a_max=a_max,
        max_auto_boost_factor=max_auto_boost_factor,
        enable_luminance_preserving_desat=enable_luminance_preserving_desat,
        eps=eps,
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
    explicit highlight reconstruction toggle, optional highlight
    reconstruction method, and Inpaint Opposed gain threshold using
    RawTherapee-aligned defaults.
    @param auto_levels_raw_values {dict[str, str]} Raw `--al-*` option values keyed by long option name.
    @return {AutoLevelsOptions|None} Parsed auto-levels options or `None` on validation error.
    @satisfies REQ-100, REQ-101, REQ-102, REQ-116, REQ-120
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

    if "--al-highlight-reconstruction" in auto_levels_raw_values:
        parsed = _parse_explicit_boolean_option(
            "--al-highlight-reconstruction",
            auto_levels_raw_values["--al-highlight-reconstruction"],
        )
        if parsed is None:
            return None
        highlight_reconstruction_enabled = parsed

    if "--al-highlight-reconstruction-method" in auto_levels_raw_values:
        parsed = _parse_auto_levels_hr_method_option(
            auto_levels_raw_values["--al-highlight-reconstruction-method"]
        )
        if parsed is None:
            return None
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
    """@brief Parse and validate auto-adjust knobs.

    @details Applies defaults for omitted knobs, validates scalar/range
    constraints, validates CLAHE-luma controls, and enforces level percentile
    ordering contract.
    @param auto_adjust_raw_values {dict[str, str]} Raw `--aa-*` option values keyed by long option name.
    @return {AutoAdjustOptions|None} Parsed shared auto-adjust options or `None` on validation error.
    @satisfies REQ-051, REQ-082, REQ-083, REQ-084, REQ-123, REQ-125
    """

    options = AutoAdjustOptions()
    blur_sigma = options.blur_sigma
    blur_threshold_pct = options.blur_threshold_pct
    level_low_pct = options.level_low_pct
    level_high_pct = options.level_high_pct
    enable_local_contrast = options.enable_local_contrast
    local_contrast_strength = options.local_contrast_strength
    clahe_clip_limit = options.clahe_clip_limit
    clahe_tile_grid_size = options.clahe_tile_grid_size
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
    if "--aa-enable-local-contrast" in auto_adjust_raw_values:
        parsed = _parse_explicit_boolean_option(
            "--aa-enable-local-contrast",
            auto_adjust_raw_values["--aa-enable-local-contrast"],
        )
        if parsed is None:
            return None
        enable_local_contrast = parsed
    if "--aa-local-contrast-strength" in auto_adjust_raw_values:
        parsed = _parse_float_in_range_option(
            "--aa-local-contrast-strength",
            auto_adjust_raw_values["--aa-local-contrast-strength"],
            0.0,
            1.0,
        )
        if parsed is None:
            return None
        local_contrast_strength = parsed
    if "--aa-clahe-clip-limit" in auto_adjust_raw_values:
        parsed = _parse_positive_float_option(
            "--aa-clahe-clip-limit",
            auto_adjust_raw_values["--aa-clahe-clip-limit"],
        )
        if parsed is None:
            return None
        clahe_clip_limit = parsed
    if "--aa-clahe-tile-grid-size" in auto_adjust_raw_values:
        parsed = _parse_positive_int_pair_option(
            "--aa-clahe-tile-grid-size",
            auto_adjust_raw_values["--aa-clahe-tile-grid-size"],
        )
        if parsed is None:
            return None
        clahe_tile_grid_size = parsed
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
        enable_local_contrast=enable_local_contrast,
        local_contrast_strength=local_contrast_strength,
        clahe_clip_limit=clahe_clip_limit,
        clahe_tile_grid_size=clahe_tile_grid_size,
        sigmoid_contrast=sigmoid_contrast,
        sigmoid_midpoint=sigmoid_midpoint,
        saturation_gamma=saturation_gamma,
        highpass_blur_sigma=highpass_blur_sigma,
    )


def _parse_hdrplus_proxy_mode_option(proxy_mode_raw):
    """@brief Parse HDR+ scalar proxy mode selector.

    @details Accepts case-insensitive proxy mode names, normalizes to canonical
    lowercase spelling, and rejects unsupported values with deterministic
    diagnostics.
    @param proxy_mode_raw {str} Raw HDR+ proxy mode token from CLI args.
    @return {str|None} Canonical proxy mode token or `None` on parse failure.
    @satisfies REQ-126, REQ-127, REQ-130
    """

    proxy_mode = proxy_mode_raw.strip().lower()
    if proxy_mode in _HDRPLUS_PROXY_MODES:
        return proxy_mode
    print_error(f"Invalid --hdrplus-proxy-mode value: {proxy_mode_raw}")
    print_error("Allowed values: " + ", ".join(_HDRPLUS_PROXY_MODES))
    return None


def _parse_hdrplus_options(hdrplus_raw_values):
    """@brief Parse and validate HDR+ merge knob values.

    @details Applies source-matching defaults for omitted knobs, validates the
    RGB-to-scalar proxy selector, alignment search radius, and temporal weight
    parameters, and rejects inconsistent temporal threshold combinations.
    @param hdrplus_raw_values {dict[str, str]} Raw `--hdrplus-*` option values keyed by long option name.
    @return {HdrPlusOptions|None} Parsed HDR+ options or `None` on validation error.
    @satisfies REQ-126, REQ-127, REQ-128, REQ-130
    """

    options = HdrPlusOptions()
    proxy_mode = options.proxy_mode
    search_radius = options.search_radius
    temporal_factor = options.temporal_factor
    temporal_min_dist = options.temporal_min_dist
    temporal_max_dist = options.temporal_max_dist

    if "--hdrplus-proxy-mode" in hdrplus_raw_values:
        parsed = _parse_hdrplus_proxy_mode_option(
            hdrplus_raw_values["--hdrplus-proxy-mode"]
        )
        if parsed is None:
            return None
        proxy_mode = parsed

    if "--hdrplus-search-radius" in hdrplus_raw_values:
        parsed = _parse_positive_int_option(
            "--hdrplus-search-radius",
            hdrplus_raw_values["--hdrplus-search-radius"],
        )
        if parsed is None:
            return None
        search_radius = parsed

    if "--hdrplus-temporal-factor" in hdrplus_raw_values:
        parsed = _parse_positive_float_option(
            "--hdrplus-temporal-factor",
            hdrplus_raw_values["--hdrplus-temporal-factor"],
        )
        if parsed is None:
            return None
        temporal_factor = parsed

    if "--hdrplus-temporal-min-dist" in hdrplus_raw_values:
        parsed = _parse_non_negative_float_option(
            "--hdrplus-temporal-min-dist",
            hdrplus_raw_values["--hdrplus-temporal-min-dist"],
        )
        if parsed is None:
            return None
        temporal_min_dist = parsed

    if "--hdrplus-temporal-max-dist" in hdrplus_raw_values:
        parsed = _parse_positive_float_option(
            "--hdrplus-temporal-max-dist",
            hdrplus_raw_values["--hdrplus-temporal-max-dist"],
        )
        if parsed is None:
            return None
        temporal_max_dist = parsed

    if temporal_max_dist <= temporal_min_dist:
        print_error(
            "Invalid HDR+ temporal thresholds: --hdrplus-temporal-max-dist must be greater than --hdrplus-temporal-min-dist"
        )
        return None

    return HdrPlusOptions(
        proxy_mode=proxy_mode,
        search_radius=search_radius,
        temporal_factor=temporal_factor,
        temporal_min_dist=temporal_min_dist,
        temporal_max_dist=temporal_max_dist,
    )


def _apply_merge_gamma_float_no_clip(np_module, image_rgb_float, resolved_merge_gamma):
    """@brief Apply resolved merge-gamma transfer without any input/output clipping.

    @details Executes the same transfer families as `_apply_merge_gamma_float`
    but intentionally avoids lower-bound clipping to preserve unbounded positive
    and negative float dynamic range for OpenCV-Tonemap backend execution.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} Backend RGB float tensor.
    @param resolved_merge_gamma {ResolvedMergeGamma} Resolved merge-gamma payload.
    @return {object} RGB float32 tensor after transfer evaluation.
    @satisfies REQ-197, REQ-198
    """

    image_rgb = _ensure_three_channel_float_array_no_bounds(
        np_module=np_module,
        image_data=image_rgb_float,
    )
    if resolved_merge_gamma.transfer == "linear":
        return image_rgb.astype(np_module.float32, copy=False)
    if resolved_merge_gamma.transfer == "srgb":
        encoded = np_module.empty_like(image_rgb, dtype=np_module.float64)
        low_mask = image_rgb <= 0.0031308
        encoded[low_mask] = image_rgb[low_mask] * 12.92
        high_mask = ~low_mask
        encoded[high_mask] = (
            1.055 * np_module.power(np_module.maximum(image_rgb[high_mask], 0.0), 1.0 / 2.4)
        ) - 0.055
        return encoded.astype(np_module.float32)
    if resolved_merge_gamma.transfer == "power":
        if resolved_merge_gamma.param_a is None:
            raise ValueError("Resolved power merge gamma is missing exponent")
        exponent = 1.0 / float(resolved_merge_gamma.param_a)
        return np_module.sign(image_rgb) * np_module.power(
            np_module.abs(image_rgb),
            exponent,
        ).astype(np_module.float32)
    if resolved_merge_gamma.transfer == "rec709":
        if resolved_merge_gamma.param_a is None or resolved_merge_gamma.param_b is None:
            raise ValueError("Resolved Rec.709 merge gamma is missing parameters")
        linear_coeff = float(resolved_merge_gamma.param_a)
        exponent = float(resolved_merge_gamma.param_b)
        encoded = np_module.empty_like(image_rgb, dtype=np_module.float64)
        low_mask = image_rgb < 0.018
        encoded[low_mask] = image_rgb[low_mask] * linear_coeff
        high_mask = ~low_mask
        encoded[high_mask] = (
            1.099
            * np_module.sign(image_rgb[high_mask])
            * np_module.power(np_module.abs(image_rgb[high_mask]), exponent)
        ) - 0.099
        return encoded.astype(np_module.float32)
    raise ValueError(f"Unsupported merge gamma transfer: {resolved_merge_gamma.transfer}")


def _parse_auto_adjust_option(auto_adjust_raw):
    """@brief Parse auto-adjust enable selector option value.

    @details Accepts case-insensitive `enable` and `disable` tokens and maps
    them to the resolved auto-adjust stage state.
    @param auto_adjust_raw {str} Raw auto-adjust enable token.
    @return {bool|None} `True` when auto-adjust is enabled; `False` when disabled; `None` on parse failure.
    @satisfies REQ-065, REQ-073, REQ-075
    """

    auto_adjust_text = auto_adjust_raw.strip()
    if not auto_adjust_text:
        print_error("Invalid --auto-adjust value: empty value")
        return None
    auto_adjust_text_lower = auto_adjust_text.lower()
    if auto_adjust_text_lower == "enable":
        return True
    if auto_adjust_text_lower == "disable":
        return False
    print_error(f"Invalid --auto-adjust value: {auto_adjust_raw}")
    print_error("Allowed values: enable, disable")
    return None


def _parse_raw_white_balance_mode_option(raw_white_balance_mode_raw):
    """@brief Parse RAW white-balance normalization mode selector option value.

    @details Accepts case-insensitive RAW white-balance normalization mode
    selectors and normalizes them to canonical runtime names.
    @param raw_white_balance_mode_raw {str} Raw `--white-balance` selector token.
    @return {str|None} Canonical RAW white-balance normalization mode or `None` on parse failure.
    @satisfies REQ-203
    """

    mode_text = str(raw_white_balance_mode_raw).strip()
    if not mode_text:
        print_error("Invalid --white-balance value: empty value")
        return None
    mapping = {
        RAW_WHITE_BALANCE_MODE_GREEN.lower(): RAW_WHITE_BALANCE_MODE_GREEN,
        RAW_WHITE_BALANCE_MODE_MAX.lower(): RAW_WHITE_BALANCE_MODE_MAX,
        RAW_WHITE_BALANCE_MODE_MIN.lower(): RAW_WHITE_BALANCE_MODE_MIN,
        RAW_WHITE_BALANCE_MODE_MEAN.lower(): RAW_WHITE_BALANCE_MODE_MEAN,
    }
    resolved_mode = mapping.get(mode_text.lower())
    if resolved_mode is not None:
        return resolved_mode
    print_error(f"Invalid --white-balance value: {raw_white_balance_mode_raw}")
    print_error("Allowed values: " + ", ".join(_RAW_WHITE_BALANCE_MODES))
    return None


def _parse_white_balance_mode_option(white_balance_raw):
    """@brief Parse white-balance mode selector option value.

    @details Accepts case-insensitive white-balance selector names and
    normalizes them to canonical runtime mode names.
    @param white_balance_raw {str} Raw `--auto-white-balance` selector token.
    @return {str|None} Canonical white-balance mode or `None` on parse failure.
    @satisfies REQ-181, REQ-183
    """

    white_balance_text = str(white_balance_raw).strip()
    if not white_balance_text:
        print_error("Invalid --auto-white-balance value: empty value")
        return None
    mapping = {
        WHITE_BALANCE_MODE_SIMPLE.lower(): WHITE_BALANCE_MODE_SIMPLE,
        WHITE_BALANCE_MODE_GRAYWORLD.lower(): WHITE_BALANCE_MODE_GRAYWORLD,
        WHITE_BALANCE_MODE_IA.lower(): WHITE_BALANCE_MODE_IA,
        WHITE_BALANCE_MODE_COLOR_CONSTANCY.lower(): WHITE_BALANCE_MODE_COLOR_CONSTANCY,
        WHITE_BALANCE_MODE_TTL.lower(): WHITE_BALANCE_MODE_TTL,
    }
    resolved_mode = mapping.get(white_balance_text.lower())
    if resolved_mode is not None:
        return resolved_mode
    print_error(f"Invalid --auto-white-balance value: {white_balance_raw}")
    print_error("Allowed values: " + ", ".join(_WHITE_BALANCE_MODES))
    return None


def _parse_white_balance_analysis_source_option(analysis_source_raw):
    """@brief Parse white-balance analysis source selector option value.

    @details Accepts case-insensitive white-balance analysis-source selector
    names and normalizes them to canonical runtime selector names.
    @param analysis_source_raw {str} Raw `--white-balance-analysis-source` selector token.
    @return {str|None} Canonical analysis-source selector or `None` on parse failure.
    @satisfies REQ-199
    """

    analysis_source_text = str(analysis_source_raw).strip()
    if not analysis_source_text:
        print_error("Invalid --white-balance-analysis-source value: empty value")
        return None
    mapping = {
        WHITE_BALANCE_ANALYSIS_SOURCE_EV_ZERO.lower(): WHITE_BALANCE_ANALYSIS_SOURCE_EV_ZERO,
        WHITE_BALANCE_ANALYSIS_SOURCE_LINEAR_BASE.lower(): WHITE_BALANCE_ANALYSIS_SOURCE_LINEAR_BASE,
    }
    resolved_source = mapping.get(analysis_source_text.lower())
    if resolved_source is not None:
        return resolved_source
    print_error(
        f"Invalid --white-balance-analysis-source value: {analysis_source_raw}"
    )
    print_error(
        "Allowed values: " + ", ".join(_WHITE_BALANCE_ANALYSIS_SOURCES)
    )
    return None


def _parse_hdr_merge_option(hdr_merge_raw):
    """@brief Parse HDR backend selector option value.

    @details Accepts case-insensitive backend selector names and normalizes
    them to canonical runtime mode names.
    @param hdr_merge_raw {str} Raw `--hdr-merge` selector token.
    @return {str|None} Canonical HDR merge mode or `None` on parse failure.
    @satisfies CTN-002, REQ-023, REQ-024, REQ-107, REQ-111, REQ-189
    """

    hdr_merge_text = hdr_merge_raw.strip()
    if not hdr_merge_text:
        print_error("Invalid --hdr-merge value: empty value")
        return None
    normalized = hdr_merge_text.lower()
    mapping = {
        HDR_MERGE_MODE_LUMINANCE.lower(): HDR_MERGE_MODE_LUMINANCE,
        HDR_MERGE_MODE_OPENCV_MERGE.lower(): HDR_MERGE_MODE_OPENCV_MERGE,
        HDR_MERGE_MODE_OPENCV_TONEMAP.lower(): HDR_MERGE_MODE_OPENCV_TONEMAP,
        HDR_MERGE_MODE_HDR_PLUS.lower(): HDR_MERGE_MODE_HDR_PLUS,
    }
    resolved = mapping.get(normalized)
    if resolved is not None:
        return resolved
    print_error(f"Invalid --hdr-merge value: {hdr_merge_raw}")
    print_error(
        f"Allowed values: {HDR_MERGE_MODE_LUMINANCE}, {HDR_MERGE_MODE_OPENCV_MERGE}, {HDR_MERGE_MODE_OPENCV_TONEMAP}, {HDR_MERGE_MODE_HDR_PLUS}"
    )
    return None


def _resolve_default_postprocess(
    hdr_merge_mode,
    luminance_tmo,
    opencv_merge_algorithm=DEFAULT_OPENCV_MERGE_ALGORITHM,
):
    """@brief Resolve backend-specific postprocess defaults.

    @details Selects backend-specific defaults. Uses algorithm-specific OpenCV
    defaults keyed by resolved `Debevec|Robertson|Mertens`, luminance-operator-
    specific defaults for `Luminace-HDR` (`mantiuk08`, `reinhard02`),
    configured defaults for `HDR-Plus`, and generic fallback defaults for
    untuned luminance operators. Complexity: O(1). Side effects: none.
    @param hdr_merge_mode {str} Canonical HDR merge mode selector.
    @param luminance_tmo {str} Selected luminance tone-mapping operator.
    @param opencv_merge_algorithm {str} Resolved OpenCV merge algorithm selector.
    @return {tuple[float, float, float, float]} Defaults in `(post_gamma, brightness, contrast, saturation)` order.
    @satisfies DES-006, DES-008, REQ-145
    """

    if hdr_merge_mode == HDR_MERGE_MODE_OPENCV_MERGE:
        opencv_defaults = {
            OPENCV_MERGE_ALGORITHM_DEBEVEC: (
                DEFAULT_OPENCV_DEBEVEC_POST_GAMMA,
                DEFAULT_OPENCV_DEBEVEC_BRIGHTNESS,
                DEFAULT_OPENCV_DEBEVEC_CONTRAST,
                DEFAULT_OPENCV_DEBEVEC_SATURATION,
            ),
            OPENCV_MERGE_ALGORITHM_ROBERTSON: (
                DEFAULT_OPENCV_ROBERTSON_POST_GAMMA,
                DEFAULT_OPENCV_ROBERTSON_BRIGHTNESS,
                DEFAULT_OPENCV_ROBERTSON_CONTRAST,
                DEFAULT_OPENCV_ROBERTSON_SATURATION,
            ),
            OPENCV_MERGE_ALGORITHM_MERTENS: (
                DEFAULT_OPENCV_MERTENS_POST_GAMMA,
                DEFAULT_OPENCV_MERTENS_BRIGHTNESS,
                DEFAULT_OPENCV_MERTENS_CONTRAST,
                DEFAULT_OPENCV_MERTENS_SATURATION,
            ),
        }
        return opencv_defaults.get(
            opencv_merge_algorithm,
            opencv_defaults[DEFAULT_OPENCV_MERGE_ALGORITHM],
        )

    if hdr_merge_mode == HDR_MERGE_MODE_HDR_PLUS:
        return (
            DEFAULT_HDRPLUS_POST_GAMMA,
            DEFAULT_HDRPLUS_BRIGHTNESS,
            DEFAULT_HDRPLUS_CONTRAST,
            DEFAULT_HDRPLUS_SATURATION,
        )

    if hdr_merge_mode != HDR_MERGE_MODE_LUMINANCE:
        return (
            DEFAULT_POST_GAMMA,
            DEFAULT_BRIGHTNESS,
            DEFAULT_CONTRAST,
            DEFAULT_SATURATION,
        )

    if luminance_tmo == "reinhard02":
        return (
            DEFAULT_REINHARD02_POST_GAMMA,
            DEFAULT_REINHARD02_BRIGHTNESS,
            DEFAULT_REINHARD02_CONTRAST,
            DEFAULT_REINHARD02_SATURATION,
        )
    if luminance_tmo == "mantiuk08":
        return (
            DEFAULT_MANTIUK08_POST_GAMMA,
            DEFAULT_MANTIUK08_BRIGHTNESS,
            DEFAULT_MANTIUK08_CONTRAST,
            DEFAULT_MANTIUK08_SATURATION,
        )

    return (
        DEFAULT_POST_GAMMA,
        DEFAULT_BRIGHTNESS,
        DEFAULT_CONTRAST,
        DEFAULT_SATURATION,
    )


def _parse_gamma_option(option_value):
    """@brief Parse one `--gamma` selector into normalized request state.

    @details Accepts literal `auto` or one comma-separated pair
    `<linear_coeff,exponent>`. Both numeric values must be finite and strictly
    positive. Returns `None` after deterministic diagnostics on invalid payload.
    @param option_value {str} Raw `--gamma` value.
    @return {MergeGammaOption|None} Parsed request dataclass on success; `None` on validation failure.
    @satisfies REQ-020
    """

    normalized_text = str(option_value).strip()
    if normalized_text == "auto":
        return MergeGammaOption(mode="auto")
    components = [component.strip() for component in normalized_text.split(",")]
    if len(components) != 2:
        print_error("Invalid --gamma value: expected `auto` or `<linear_coeff,exponent>`")
        return None
    try:
        linear_coeff = float(components[0])
        exponent = float(components[1])
    except ValueError:
        print_error("Invalid --gamma value: expected numeric `<linear_coeff,exponent>`")
        return None
    if (
        not math.isfinite(linear_coeff)
        or not math.isfinite(exponent)
        or linear_coeff <= 0.0
        or exponent <= 0.0
    ):
        print_error("Invalid --gamma value: coefficients must be finite and > 0")
        return None
    return MergeGammaOption(
        mode="custom",
        linear_coeff=linear_coeff,
        exponent=exponent,
    )


def _decode_exif_text_value(exif_value):
    """@brief Normalize one EXIF scalar payload to deterministic stripped text.

    @details Accepts bytes, rationals, enums, or generic scalar-like values and
    returns one normalized text token for merge-gamma auto resolution.
    Complexity: O(len(value_text)). Side effects: none.
    @param exif_value {object} Raw EXIF payload.
    @return {str|None} Normalized text token or `None` when payload is absent/empty.
    @satisfies REQ-169
    """

    if exif_value is None:
        return None
    if isinstance(exif_value, bytes):
        decoded_value = exif_value.decode("utf-8", errors="ignore").strip("\x00 ").strip()
        return decoded_value or None
    value_text = str(exif_value).strip()
    return value_text or None


def _exiftool_color_space_fallback(input_dng):
    """@brief Extract color-space evidence via exiftool subprocess fallback.

    @details Invokes `exiftool -j -ColorSpace` as a subprocess to recover
    color-space metadata from MakerNotes or vendor-specific IFDs that
    `exifread` cannot parse (e.g., Canon MakerNotes embedded in DNG).
    Maps exiftool text labels to EXIF-compatible numeric tokens:
    `Adobe RGB` -> `"2"`, `sRGB` -> `"1"`. Returns `None` when exiftool
    is unavailable, times out, or yields no color-space evidence.
    Complexity: O(1) subprocess invocation. Side effects: read-only.
    @param input_dng {Path} Source RAW/DNG file path.
    @return {str|None} EXIF-compatible numeric `ColorSpace` token or `None`.
    @satisfies REQ-169
    """

    try:
        import json
        import subprocess  # noqa: S404

        proc = subprocess.run(  # noqa: S603, S607
            ["exiftool", "-j", "-ColorSpace", str(input_dng)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode != 0:
            return None
        data = json.loads(proc.stdout)
        if not data:
            return None
        entry = data[0]
        for tag_key in entry:
            if tag_key.lower() in ("sourcefile",):
                continue
            tag_value = str(entry[tag_key]).strip().lower()
            if tag_value == "adobe rgb":
                return "2"
            if tag_value in ("srgb", "srgb iec61966-2.1"):
                return "1"
        return None
    except (
        OSError,
        ValueError,
        TypeError,
        AttributeError,
        FileNotFoundError,
    ):
        return None
    except Exception:  # noqa: BLE001
        return None


def _extract_exif_gamma_tags(input_dng):
    """@brief Extract EXIF color-space metadata relevant to auto merge gamma.

    @details Opens the source RAW/DNG file as a binary stream via
    `exifread.process_file` and normalizes `EXIF ColorSpace`,
    `Interop InteroperabilityIndex`, `Image Model`, and `Image Make` tags for
    deterministic auto transfer resolution. When `exifread` yields no
    `ColorSpace` evidence, falls back to `exiftool` subprocess extraction
    to recover vendor-specific MakerNotes color-space data (e.g., Canon DNG).
    Does not use Pillow for this extraction. Complexity: O(file_size).
    Side effects: none (read-only file access).
    @param input_dng {Path} Source RAW/DNG file path.
    @return {ExifGammaTags} Normalized EXIF merge-gamma evidence payload.
    @satisfies REQ-169, REQ-172, REQ-173
    """

    try:
        import exifread  # type: ignore
    except ImportError:
        return ExifGammaTags(
            color_space=None, interoperability_index=None,
            image_model=None, image_make=None,
        )
    try:
        with open(str(input_dng), "rb") as raw_file:
            tags = exifread.process_file(raw_file, details=False)
        color_space_raw = tags.get("EXIF ColorSpace")
        color_space_value = (
            str(color_space_raw).strip() if color_space_raw is not None else None
        )
        if color_space_value == "":
            color_space_value = None
        interop_index_raw = tags.get("Interop InteroperabilityIndex")
        interop_index_value = (
            str(interop_index_raw).strip()
            if interop_index_raw is not None
            else None
        )
        if interop_index_value == "":
            interop_index_value = None
        image_model_raw = tags.get("Image Model")
        image_model_value = (
            str(image_model_raw).strip() if image_model_raw is not None else None
        )
        if image_model_value == "":
            image_model_value = None
        image_make_raw = tags.get("Image Make")
        image_make_value = (
            str(image_make_raw).strip() if image_make_raw is not None else None
        )
        if image_make_value == "":
            image_make_value = None
        if color_space_value is None:
            exiftool_color_space = _exiftool_color_space_fallback(input_dng)
            if exiftool_color_space is not None:
                color_space_value = exiftool_color_space
        return ExifGammaTags(
            color_space=color_space_value,
            interoperability_index=interop_index_value,
            image_model=image_model_value,
            image_make=image_make_value,
        )
    except (OSError, ValueError, TypeError, AttributeError):
        return ExifGammaTags(
            color_space=None, interoperability_index=None,
            image_model=None, image_make=None,
        )


def _resolve_auto_merge_gamma(exif_gamma_tags, source_gamma_info):
    """@brief Resolve auto merge-output transfer from EXIF-first metadata evidence.

    @details Applies deterministic priority: EXIF `ColorSpace==1` selects sRGB,
    EXIF `ColorSpace==2` or interoperability token containing `R03` selects
    Adobe RGB power gamma `2.19921875`, and unresolved cases default to sRGB
    transfer as fallback.
    @param exif_gamma_tags {ExifGammaTags} Normalized EXIF color-space evidence.
    @param source_gamma_info {SourceGammaInfo} Derived source-gamma diagnostic
        payload (retained for backward compatibility; not used for resolution).
    @return {ResolvedMergeGamma} Resolved auto transfer payload.
    @satisfies REQ-169
    """

    auto_request = MergeGammaOption(mode="auto")
    color_space = exif_gamma_tags.color_space
    interop_index = exif_gamma_tags.interoperability_index
    if color_space == "1":
        return ResolvedMergeGamma(
            request=auto_request,
            transfer="srgb",
            label="sRGB",
            param_a=None,
            param_b=None,
            evidence="exif-colorspace=1",
        )
    if color_space == "2" or (
        interop_index is not None and "R03" in interop_index.upper()
    ):
        return ResolvedMergeGamma(
            request=auto_request,
            transfer="power",
            label="Adobe RGB",
            param_a=2.19921875,
            param_b=None,
            evidence="exif-adobe-rgb",
        )
    return ResolvedMergeGamma(
        request=auto_request,
        transfer="srgb",
        label="sRGB",
        param_a=None,
        param_b=None,
        evidence="unresolved-default-srgb",
    )


def _describe_resolved_merge_gamma(resolved_merge_gamma):
    """@brief Format one deterministic merge-gamma runtime diagnostic line.

    @details Renders one stable diagnostic payload including request mode,
    resolved transfer family, label, explicit linear-segment parameters,
    explicit curve-segment parameters, and evidence token.
    @param resolved_merge_gamma {ResolvedMergeGamma} Resolved merge-gamma payload.
    @return {str} Deterministic runtime diagnostic line.
    @satisfies REQ-171
    """

    def _format_gamma_number(value):
        """@brief Format one finite gamma parameter for deterministic diagnostics.

        @details Serializes one numeric gamma parameter with stable decimal
        precision, preserving exact repository-relevant constants such as
        `2.19921875` while avoiding scientific notation and insignificant
        trailing zeroes.
        @param value {float} Numeric gamma parameter to serialize.
        @return {str} Stable decimal representation for runtime diagnostics.
        @satisfies REQ-171
        """

        return format(float(value), ".15g")

    linear_text = "linear=none"
    curve_text = "curve=none"
    params_text = "-"
    if resolved_merge_gamma.transfer == "srgb":
        linear_text = "linear(scale=12.92,limit=0.0031308)"
        curve_text = "curve(scale=1.055,power=1/2.4,offset=-0.055)"
    elif resolved_merge_gamma.transfer == "power":
        if resolved_merge_gamma.param_a is None:
            raise ValueError("Resolved power merge gamma is missing exponent")
        exponent_text = _format_gamma_number(resolved_merge_gamma.param_a)
        curve_text = f"curve(power=1/{exponent_text})"
        params_text = exponent_text
    elif resolved_merge_gamma.transfer == "rec709":
        if resolved_merge_gamma.param_a is None or resolved_merge_gamma.param_b is None:
            raise ValueError("Resolved Rec.709 merge gamma is missing parameters")
        linear_coeff_text = _format_gamma_number(resolved_merge_gamma.param_a)
        exponent_text = _format_gamma_number(resolved_merge_gamma.param_b)
        linear_text = f"linear(scale={linear_coeff_text},limit=0.018)"
        curve_text = (
            "curve("
            f"scale=1.099,power={exponent_text},offset=-0.099)"
        )
        params_text = f"{linear_coeff_text},{exponent_text}"
    return (
        "Merge gamma: "
        f"request={resolved_merge_gamma.request.mode}; "
        f"transfer={resolved_merge_gamma.transfer}; "
        f"label={resolved_merge_gamma.label}; "
        f"params={params_text}; "
        f"{linear_text}; "
        f"{curve_text}; "
        f"evidence={resolved_merge_gamma.evidence}"
    )


def _describe_exif_gamma_tags(exif_gamma_tags):
    """@brief Format one deterministic EXIF merge-gamma input diagnostic line.

    @details Renders one stable runtime payload exposing the normalized EXIF
    `ColorSpace`, `InteroperabilityIndex`, `ImageModel`, `ImageMake`, and a
    human-readable `ColorProfile` label derived from `ColorSpace` and
    `InteroperabilityIndex`. Mapping: `ColorSpace==1` -> `sRGB`,
    `ColorSpace==2` or `InteroperabilityIndex` containing `R03` -> `Adobe RGB`,
    `ColorSpace==65535` -> `Uncalibrated`, otherwise `Unknown`. Missing values
    are rendered as `missing`.
    @param exif_gamma_tags {ExifGammaTags} Normalized EXIF merge-gamma evidence payload.
    @return {str} Deterministic runtime diagnostic line.
    @satisfies REQ-172
    """

    color_space_text = exif_gamma_tags.color_space or "missing"
    interop_text = exif_gamma_tags.interoperability_index or "missing"
    model_text = exif_gamma_tags.image_model or "missing"
    make_text = exif_gamma_tags.image_make or "missing"
    color_space = exif_gamma_tags.color_space
    interop_index = exif_gamma_tags.interoperability_index
    if color_space == "1":
        color_profile_label = "sRGB"
    elif color_space == "2" or (
        interop_index is not None and "R03" in interop_index.upper()
    ):
        color_profile_label = "Adobe RGB"
    elif color_space == "65535":
        color_profile_label = "Uncalibrated"
    elif color_space is None:
        color_profile_label = "Unknown"
    else:
        color_profile_label = "Unknown"
    return (
        "Merge gamma EXIF inputs: "
        f"ColorSpace={color_space_text}; "
        f"InteroperabilityIndex={interop_text}; "
        f"ImageModel={model_text}; "
        f"ImageMake={make_text}; "
        f"ColorProfile={color_profile_label}"
    )


def _ensure_three_channel_float_array_no_clip(np_module, image_data):
    """@brief Normalize one image payload to three-channel float tensor without upper clipping.

    @details Converts arbitrary numeric image payloads into RGB `float64`,
    preserving finite positive values above `1.0`, clearing non-finite and
    negative values only, expanding grayscale/single-channel inputs to RGB, and
    dropping alpha channels. Used exclusively by backend-final merge-gamma
    application to avoid unnecessary clipping around transfer evaluation.
    @param np_module {ModuleType} Imported numpy module.
    @param image_data {object} Numeric image payload.
    @return {object} RGB `float64` tensor with shape `(H,W,3)` and lower bound `0`.
    @exception ValueError Raised when the input shape cannot be normalized to RGB.
    @satisfies REQ-170
    """

    numeric_data = np_module.asarray(image_data, dtype=np_module.float64)
    finite_mask = np_module.isfinite(numeric_data)
    numeric_data = np_module.where(finite_mask, numeric_data, 0.0)
    numeric_data = np_module.maximum(numeric_data, 0.0)
    if len(numeric_data.shape) == 2:
        numeric_data = numeric_data[:, :, None]
    if len(numeric_data.shape) == 3 and numeric_data.shape[2] == 1:
        numeric_data = np_module.repeat(numeric_data, 3, axis=2)
    if len(numeric_data.shape) == 3 and numeric_data.shape[2] == 4:
        numeric_data = numeric_data[:, :, :3]
    if len(numeric_data.shape) != 3 or numeric_data.shape[2] < 3:
        raise ValueError("Float stage input image has unsupported shape")
    if numeric_data.shape[2] > 3:
        numeric_data = numeric_data[:, :, :3]
    return numeric_data


def _ensure_three_channel_float_array_no_bounds(np_module, image_data):
    """@brief Normalize one image payload to RGB float tensor without clipping bounds.

    @details Converts numeric image payloads into RGB `float64`, preserves
    finite values on the full float range without lower/upper clipping,
    expands grayscale/single-channel data to RGB, drops alpha, and raises on
    non-finite payloads to avoid silent range mutations.
    @param np_module {ModuleType} Imported numpy module.
    @param image_data {object} Numeric image payload.
    @return {object} RGB `float64` tensor with shape `(H,W,3)` and unbounded finite range.
    @exception ValueError Raised when image shape is unsupported or contains non-finite values.
    @satisfies REQ-198
    """

    numeric_data = np_module.asarray(image_data, dtype=np_module.float64)
    if not bool(np_module.all(np_module.isfinite(numeric_data))):
        raise ValueError("OpenCV-Tonemap backend received non-finite float values")
    if len(numeric_data.shape) == 2:
        numeric_data = numeric_data[:, :, None]
    if len(numeric_data.shape) == 3 and numeric_data.shape[2] == 1:
        numeric_data = np_module.repeat(numeric_data, 3, axis=2)
    if len(numeric_data.shape) == 3 and numeric_data.shape[2] == 4:
        numeric_data = numeric_data[:, :, :3]
    if len(numeric_data.shape) != 3 or numeric_data.shape[2] < 3:
        raise ValueError("Float stage input image has unsupported shape")
    if numeric_data.shape[2] > 3:
        numeric_data = numeric_data[:, :, :3]
    return numeric_data


def _apply_merge_gamma_float(np_module, image_rgb_float, resolved_merge_gamma):
    """@brief Apply one resolved merge-output transfer without extra clipping.

    @details Executes backend-final transfer encoding on positive float-domain
    RGB values after backend normalization. The helper intentionally avoids
    upper clipping before and after transfer evaluation so highlight headroom is
    preserved until the shared downstream pipeline chooses its own bounds.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} Backend-normalized RGB float tensor.
    @param resolved_merge_gamma {ResolvedMergeGamma} Resolved merge-gamma payload.
    @return {object} RGB float32 tensor after merge-gamma transfer.
    @satisfies REQ-170
    """

    if resolved_merge_gamma.transfer == "linear":
        return _ensure_three_channel_float_array_no_clip(
            np_module=np_module,
            image_data=image_rgb_float,
        ).astype(np_module.float32)
    image_rgb = _ensure_three_channel_float_array_no_clip(
        np_module=np_module,
        image_data=image_rgb_float,
    )
    if resolved_merge_gamma.transfer == "srgb":
        low_mask = image_rgb <= 0.0031308
        encoded = np_module.empty_like(image_rgb, dtype=np_module.float64)
        encoded[low_mask] = image_rgb[low_mask] * 12.92
        encoded[~low_mask] = (
            1.055 * np_module.power(image_rgb[~low_mask], 1.0 / 2.4)
        ) - 0.055
        return encoded.astype(np_module.float32)
    if resolved_merge_gamma.transfer == "power":
        if resolved_merge_gamma.param_a is None:
            raise ValueError("Resolved power merge gamma is missing exponent")
        return np_module.power(
            image_rgb,
            1.0 / float(resolved_merge_gamma.param_a),
        ).astype(np_module.float32)
    if resolved_merge_gamma.transfer == "rec709":
        if resolved_merge_gamma.param_a is None or resolved_merge_gamma.param_b is None:
            raise ValueError("Resolved Rec.709 merge gamma is missing parameters")
        linear_coeff = float(resolved_merge_gamma.param_a)
        exponent = float(resolved_merge_gamma.param_b)
        low_mask = image_rgb < 0.018
        encoded = np_module.empty_like(image_rgb, dtype=np_module.float64)
        encoded[low_mask] = image_rgb[low_mask] * linear_coeff
        encoded[~low_mask] = (
            1.099 * np_module.power(image_rgb[~low_mask], exponent)
        ) - 0.099
        return encoded.astype(np_module.float32)
    raise ValueError(f"Unsupported merge gamma transfer: {resolved_merge_gamma.transfer}")


def _parse_run_options(args):
    """@brief Parse CLI args into input, output, and EV parameters.

    @details Supports positional file arguments, static exposure selectors
    (`--ev=<value>`/`--ev <value>` plus optional `--ev-zero=<value>`),
    automatic exposure selector (`--auto-ev[=<enable|disable>]`) with explicit
    mutual exclusion against `--ev`, optional automatic exposure clipping and
    step controls, optional RAW white-balance normalization selector
    (`--white-balance=<GREEN|MAX|MIN|MEAN>`),
    optional white-balance selector (`--auto-white-balance=<mode>`) applied to
    bracket triplet before backend merge when enabled,
    optional postprocess controls including `--post-gamma=<value|auto>` and
    optional `--post-gamma-auto-*` knobs,
    optional auto-brightness stage and
    `--ab-*` knobs, optional auto-levels stage and `--al-*` knobs,
    optional shared auto-adjust knobs, optional backend selector
    (`--hdr-merge=<Luminace-HDR|OpenCV-Merge|OpenCV-Tonemap|HDR-Plus>` default `OpenCV-Merge`),
    OpenCV backend controls, OpenCV-Tonemap backend controls, HDR+ backend controls, and luminance backend controls
    including explicit `--tmo*` passthrough options and optional
    auto-adjust enable selector (`--auto-adjust <enable|disable>`), plus
    optional `--debug` persistent checkpoint emission; parses
    `--gamma=<auto|linear_coeff,exponent>` merge-output transfer selector
    defaulting to `auto` when omitted, rejects unknown options, and rejects
    invalid arity.
    @param args {list[str]} Raw command argument vector.
    @return {tuple[Path, Path, float|None, bool, PostprocessOptions, bool, bool, LuminanceOptions, OpenCvMergeOptions, HdrPlusOptions, bool, float, bool, AutoEvOptions]|None} Parsed `(input, output, ev, auto_ev, postprocess, enable_luminance, enable_opencv, luminance_options, opencv_merge_options, hdrplus_options, enable_hdr_plus, ev_zero, ev_zero_specified, auto_ev_options)` tuple; `None` on parse failure.
    @satisfies CTN-002, CTN-003, REQ-007, REQ-008, REQ-009, REQ-018, REQ-020, REQ-022, REQ-023, REQ-024, REQ-025, REQ-100, REQ-101, REQ-107, REQ-111, REQ-125, REQ-135, REQ-141, REQ-143, REQ-146, REQ-176, REQ-179, REQ-180, REQ-181, REQ-183, REQ-189, REQ-190, REQ-191, REQ-194, REQ-195, REQ-196, REQ-203
    """

    positional = []
    ev_value = None
    auto_ev_enabled = None
    ev_zero = 0.0
    ev_zero_specified = False
    auto_ev_options = AutoEvOptions()
    post_gamma = DEFAULT_POST_GAMMA
    post_gamma_mode = DEFAULT_POST_GAMMA_MODE
    brightness = DEFAULT_BRIGHTNESS
    contrast = DEFAULT_CONTRAST
    saturation = DEFAULT_SATURATION
    jpg_compression = DEFAULT_JPG_COMPRESSION
    post_gamma_set = False
    brightness_set = False
    contrast_set = False
    saturation_set = False
    auto_brightness_enabled = True
    auto_brightness_raw_values = {}
    auto_levels_enabled = True
    auto_levels_raw_values = {}
    auto_adjust_enabled = DEFAULT_AUTO_ADJUST_ENABLED
    auto_adjust_raw_values = {}
    post_gamma_auto_raw_values = {}
    debug_enabled = False
    raw_white_balance_mode = DEFAULT_RAW_WHITE_BALANCE_MODE
    white_balance_mode = None
    white_balance_analysis_source = WHITE_BALANCE_ANALYSIS_SOURCE_EV_ZERO
    hdr_merge_mode = HDR_MERGE_MODE_OPENCV_MERGE
    opencv_raw_values = {}
    opencv_tonemap_selector_options = []
    opencv_tonemap_knob_raw_values = {}
    merge_gamma_option = MergeGammaOption(mode="auto")
    hdrplus_raw_values = {}
    luminance_hdr_model = DEFAULT_LUMINANCE_HDR_MODEL
    luminance_hdr_weight = DEFAULT_LUMINANCE_HDR_WEIGHT
    luminance_hdr_response_curve = DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE
    luminance_tmo = DEFAULT_LUMINANCE_TMO
    luminance_tmo_extra_args = []
    luminance_option_specified = False
    auto_ev_option_specified = False
    idx = 0

    while idx < len(args):
        token = args[idx]
        if token.startswith("--hdr-merge="):
            parsed_hdr_merge_mode = _parse_hdr_merge_option(token.split("=", 1)[1])
            if parsed_hdr_merge_mode is None:
                return None
            hdr_merge_mode = parsed_hdr_merge_mode
            idx += 1
            continue

        if token.startswith("--hdrplus-"):
            if "=" not in token:
                print_error(f"Missing value for {token}")
                return None
            option_name, option_value = token.split("=", 1)
            if option_name not in _HDRPLUS_KNOB_OPTIONS:
                print_error(f"Unknown option: {option_name}")
                return None
            hdrplus_raw_values[option_name] = option_value
            idx += 1
            continue

        if token.startswith("--opencv-"):
            if "=" not in token:
                print_error(f"Missing value for {token}")
                return None
            option_name, option_value = token.split("=", 1)
            if option_name not in _OPENCV_KNOB_OPTIONS:
                print_error(f"Unknown option: {option_name}")
                return None
            opencv_raw_values[option_name] = option_value
            idx += 1
            continue

        if token in _OPENCV_TONEMAP_SELECTOR_OPTIONS:
            opencv_tonemap_selector_options.append(token)
            idx += 1
            continue

        if token.startswith("--tonemap-"):
            if "=" not in token:
                print_error(f"Missing value for {token}")
                return None
            option_name, option_value = token.split("=", 1)
            if option_name not in _OPENCV_TONEMAP_KNOB_OPTIONS:
                print_error(f"Unknown option: {option_name}")
                return None
            opencv_tonemap_knob_raw_values[option_name] = option_value
            idx += 1
            continue

        if token == "--debug":
            debug_enabled = True
            idx += 1
            continue

        if token.startswith("--auto-adjust="):
            parsed_auto_adjust_enabled = _parse_auto_adjust_option(
                token.split("=", 1)[1]
            )
            if parsed_auto_adjust_enabled is None:
                return None
            auto_adjust_enabled = parsed_auto_adjust_enabled
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
            if token == "--ab-enable-luminance-preserving-desat":
                auto_brightness_raw_values[token] = "true"
                idx += 1
                continue
            if token.startswith("--ab-enable-luminance-preserving-desat="):
                option_name, option_value = token.split("=", 1)
                auto_brightness_raw_values[option_name] = option_value
                idx += 1
                continue
            if "=" not in token:
                print_error(f"Missing value for {token}")
                return None
            option_name, option_value = token.split("=", 1)
            if option_name not in _AUTO_BRIGHTNESS_KNOB_OPTIONS:
                print_error(f"Unknown option: {option_name}")
                return None
            auto_brightness_raw_values[option_name] = option_value
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
            if token in (
                "--al-clip-out-of-gamut",
                "--al-highlight-reconstruction",
            ):
                auto_levels_raw_values[token] = "true"
                idx += 1
                continue
            if token.startswith("--al-clip-out-of-gamut=") or token.startswith(
                "--al-highlight-reconstruction="
            ):
                option_name, option_value = token.split("=", 1)
                auto_levels_raw_values[option_name] = option_value
                idx += 1
                continue
            if "=" not in token:
                print_error(f"Missing value for {token}")
                return None
            option_name, option_value = token.split("=", 1)
            if option_name not in _AUTO_LEVELS_KNOB_OPTIONS:
                print_error(f"Unknown option: {option_name}")
                return None
            auto_levels_raw_values[option_name] = option_value
            idx += 1
            continue

        if token.startswith("--aa-"):
            if token == "--aa-enable-local-contrast":
                auto_adjust_raw_values[token] = "true"
                idx += 1
                continue
            if token.startswith("--aa-enable-local-contrast="):
                option_name, option_value = token.split("=", 1)
                auto_adjust_raw_values[option_name] = option_value
                idx += 1
                continue
            if "=" not in token:
                print_error(f"Missing value for {token}")
                return None
            option_name, option_value = token.split("=", 1)

            if option_name not in _AUTO_ADJUST_KNOB_OPTIONS:
                print_error(f"Unknown option: {option_name}")
                return None
            auto_adjust_raw_values[option_name] = option_value
            idx += 1
            continue

        if token.startswith("--white-balance="):
            parsed_raw_white_balance_mode = _parse_raw_white_balance_mode_option(
                token.split("=", 1)[1]
            )
            if parsed_raw_white_balance_mode is None:
                return None
            raw_white_balance_mode = parsed_raw_white_balance_mode
            idx += 1
            continue

        if token.startswith("--auto-white-balance="):
            parsed_white_balance_mode = _parse_white_balance_mode_option(
                token.split("=", 1)[1]
            )
            if parsed_white_balance_mode is None:
                return None
            white_balance_mode = parsed_white_balance_mode
            idx += 1
            continue

        if token.startswith("--white-balance-analysis-source="):
            parsed_white_balance_analysis_source = (
                _parse_white_balance_analysis_source_option(
                    token.split("=", 1)[1]
                )
            )
            if parsed_white_balance_analysis_source is None:
                return None
            white_balance_analysis_source = parsed_white_balance_analysis_source
            idx += 1
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

        if token.startswith("--luminance-hdr-response-curve="):
            parsed_value = _parse_luminance_response_curve_option(
                token.split("=", 1)[1]
            )
            if parsed_value is None:
                return None
            luminance_hdr_response_curve = parsed_value
            luminance_option_specified = True
            idx += 1
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

            if "=" not in token:
                print_error(f"Missing value for {token}")
                return None
            option_name, option_value = token.split("=", 1)

            parsed_value = _parse_tmo_passthrough_value(option_name, option_value)
            if parsed_value is None:
                return None
            luminance_tmo_extra_args.extend((option_name, parsed_value))
            luminance_option_specified = True
            idx += 1
            continue

        if token.startswith("--ev="):
            parsed_ev = _parse_ev_option(token.split("=", 1)[1])
            if parsed_ev is None:
                return None
            ev_value = parsed_ev
            idx += 1
            continue

        if token.startswith("--auto-ev="):
            parsed_auto_ev = _parse_auto_ev_option(token.split("=", 1)[1])
            if parsed_auto_ev is None:
                return None
            auto_ev_enabled = parsed_auto_ev
            auto_ev_option_specified = True
            idx += 1
            continue

        if token == "--auto-zero" or token.startswith("--auto-zero="):
            print_error("Removed option: --auto-zero")
            return None

        if token == "--auto-zero-pct" or token.startswith("--auto-zero-pct="):
            print_error("Removed option: --auto-zero-pct")
            return None

        if token in (
            "--auto-ev-shadow-target",
            "--auto-ev-highlight-target",
            "--auto-ev-pct",
        ) or token.startswith(
            (
                "--auto-ev-shadow-target=",
                "--auto-ev-highlight-target=",
                "--auto-ev-pct=",
            )
        ):
            print_error(f"Removed option: {token.split('=', 1)[0]}")
            return None

        if token.startswith("--auto-ev-shadow-clipping="):
            parsed_threshold = _parse_percentage_option(
                "--auto-ev-shadow-clipping", token.split("=", 1)[1]
            )
            if parsed_threshold is None:
                return None
            auto_ev_options = AutoEvOptions(
                shadow_clipping_pct=parsed_threshold,
                highlight_clipping_pct=auto_ev_options.highlight_clipping_pct,
                step=auto_ev_options.step,
            )
            idx += 1
            continue

        if token.startswith("--auto-ev-highlight-clipping="):
            parsed_threshold = _parse_percentage_option(
                "--auto-ev-highlight-clipping", token.split("=", 1)[1]
            )
            if parsed_threshold is None:
                return None
            auto_ev_options = AutoEvOptions(
                shadow_clipping_pct=auto_ev_options.shadow_clipping_pct,
                highlight_clipping_pct=parsed_threshold,
                step=auto_ev_options.step,
            )
            idx += 1
            continue

        if token.startswith("--auto-ev-step="):
            parsed_step = _parse_positive_float_option(
                "--auto-ev-step", token.split("=", 1)[1]
            )
            if parsed_step is None:
                return None
            auto_ev_options = AutoEvOptions(
                shadow_clipping_pct=auto_ev_options.shadow_clipping_pct,
                highlight_clipping_pct=auto_ev_options.highlight_clipping_pct,
                step=parsed_step,
            )
            idx += 1
            continue

        if token.startswith("--ev-zero="):
            parsed_ev_zero = _parse_ev_zero_option(token.split("=", 1)[1])
            if parsed_ev_zero is None:
                return None
            ev_zero = parsed_ev_zero
            ev_zero_specified = True
            idx += 1
            continue

        if token.startswith("--gamma="):
            merge_gamma_option = _parse_gamma_option(token.split("=", 1)[1])
            if merge_gamma_option is None:
                return None
            idx += 1
            continue

        if token.startswith("--post-gamma="):
            parsed_post_gamma_selector = _parse_post_gamma_selector_option(
                token.split("=", 1)[1]
            )
            if parsed_post_gamma_selector is None:
                return None
            post_gamma, post_gamma_mode = parsed_post_gamma_selector
            post_gamma_set = True
            idx += 1
            continue

        if token.startswith("--post-gamma-auto-"):
            if "=" not in token:
                print_error(f"Missing value for {token}")
                return None
            option_name, option_value = token.split("=", 1)
            if option_name not in _POST_GAMMA_AUTO_KNOB_OPTIONS:
                print_error(f"Unknown option: {option_name}")
                return None
            post_gamma_auto_raw_values[option_name] = option_value
            idx += 1
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
            "[--ev=<value>] [--auto-ev=<enable|disable>] [--ev-zero=<value>]"
        )
        return None

    if auto_ev_enabled is None:
        auto_ev_enabled = ev_value is None
    if ev_value is not None and auto_ev_option_specified:
        print_error("--auto-ev cannot be combined with --ev")
        return None
    if ev_value is None and not auto_ev_enabled:
        print_error("No exposure mode selected: provide --ev or --auto-ev enable.")
        return None
    if ev_zero_specified and ev_value is None:
        if auto_ev_option_specified and auto_ev_enabled:
            print_error("--ev-zero cannot be combined with --auto-ev")
        else:
            print_error("--ev-zero requires --ev")
        return None

    if hdr_merge_mode not in _HDR_MERGE_MODES:
        print_error(f"Invalid --hdr-merge value: {hdr_merge_mode}")
        return None

    if luminance_option_specified and hdr_merge_mode != HDR_MERGE_MODE_LUMINANCE:
        print_error(f"Luminance options require --hdr-merge {HDR_MERGE_MODE_LUMINANCE}")
        return None

    if not auto_adjust_enabled and auto_adjust_raw_values:
        invalid_knob = next(iter(auto_adjust_raw_values))
        print_error(
            f"Auto-adjust knob {invalid_knob} requires --auto-adjust enable"
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
    if hdr_merge_mode != HDR_MERGE_MODE_HDR_PLUS and hdrplus_raw_values:
        invalid_knob = next(iter(hdrplus_raw_values))
        print_error(f"HDR+ knob {invalid_knob} requires --hdr-merge {HDR_MERGE_MODE_HDR_PLUS}")
        return None
    if hdr_merge_mode != HDR_MERGE_MODE_OPENCV_MERGE and opencv_raw_values:
        invalid_knob = next(iter(opencv_raw_values))
        print_error(
            f"OpenCV knob {invalid_knob} requires --hdr-merge {HDR_MERGE_MODE_OPENCV_MERGE}"
        )
        return None
    if (
        hdr_merge_mode != HDR_MERGE_MODE_OPENCV_TONEMAP
        and (
            opencv_tonemap_selector_options
            or opencv_tonemap_knob_raw_values
        )
    ):
        if opencv_tonemap_selector_options:
            invalid_knob = opencv_tonemap_selector_options[0]
        else:
            invalid_knob = next(iter(opencv_tonemap_knob_raw_values))
        print_error(
            f"OpenCV-Tonemap option {invalid_knob} requires --hdr-merge {HDR_MERGE_MODE_OPENCV_TONEMAP}"
        )
        return None

    opencv_merge_options = _parse_opencv_merge_backend_options(opencv_raw_values)
    if opencv_merge_options is None:
        return None
    opencv_tonemap_options = None
    if hdr_merge_mode == HDR_MERGE_MODE_OPENCV_TONEMAP:
        opencv_tonemap_options = _parse_opencv_tonemap_backend_options(
            tonemap_selector_options=opencv_tonemap_selector_options,
            tonemap_knob_raw_values=opencv_tonemap_knob_raw_values,
        )
        if opencv_tonemap_options is None:
            return None
    (
        backend_post_gamma,
        backend_brightness,
        backend_contrast,
        backend_saturation,
    ) = _resolve_default_postprocess(
        hdr_merge_mode,
        luminance_tmo,
        opencv_merge_algorithm=opencv_merge_options.merge_algorithm,
    )
    if not post_gamma_set:
        post_gamma = backend_post_gamma
    if (
        post_gamma_mode != "auto"
        and post_gamma_auto_raw_values
    ):
        invalid_knob = next(iter(post_gamma_auto_raw_values))
        print_error(f"Post-gamma auto knob {invalid_knob} requires --post-gamma=auto")
        return None
    post_gamma_auto_options = _parse_post_gamma_auto_options(post_gamma_auto_raw_values)
    if post_gamma_auto_options is None:
        return None
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
    hdrplus_options = _parse_hdrplus_options(hdrplus_raw_values)
    if hdrplus_options is None:
        return None

    enable_luminance = hdr_merge_mode == HDR_MERGE_MODE_LUMINANCE
    enable_opencv = hdr_merge_mode == HDR_MERGE_MODE_OPENCV_MERGE
    enable_hdr_plus = hdr_merge_mode == HDR_MERGE_MODE_HDR_PLUS

    return (
        Path(positional[0]),
        Path(positional[1]),
        ev_value,
        auto_ev_enabled,
        PostprocessOptions(
            post_gamma=post_gamma,
            post_gamma_mode=post_gamma_mode,
            post_gamma_auto_options=post_gamma_auto_options,
            brightness=brightness,
            contrast=contrast,
            saturation=saturation,
            jpg_compression=jpg_compression,
            auto_brightness_enabled=auto_brightness_enabled,
            auto_brightness_options=auto_brightness_options,
            auto_levels_enabled=auto_levels_enabled,
            auto_levels_options=auto_levels_options,
            auto_adjust_enabled=auto_adjust_enabled,
            auto_adjust_options=auto_adjust_options,
            debug_enabled=debug_enabled,
            merge_gamma_option=merge_gamma_option,
            raw_white_balance_mode=raw_white_balance_mode,
            white_balance_mode=white_balance_mode,
            white_balance_analysis_source=white_balance_analysis_source,
            opencv_tonemap_options=opencv_tonemap_options,
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
        opencv_merge_options,
        hdrplus_options,
        enable_hdr_plus,
        ev_zero,
        ev_zero_specified,
        auto_ev_options,
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


def _parse_exif_exposure_time_to_seconds(exposure_raw):
    """@brief Parse one EXIF exposure-time token into positive seconds.

    @details Normalizes scalar or rational-like EXIF `ExposureTime` payloads from
    Pillow metadata into one positive Python `float` measured in seconds.
    Accepted forms include numeric scalars, two-item `(numerator, denominator)`
    pairs, and objects exposing `numerator`/`denominator` attributes.
    @param exposure_raw {object} EXIF `ExposureTime` scalar or rational-like payload.
    @return {float|None} Positive exposure time in seconds; `None` when missing or invalid.
    @satisfies REQ-161
    """

    if exposure_raw is None:
        return None
    if isinstance(exposure_raw, (list, tuple)):
        if len(exposure_raw) == 2:
            numerator, denominator = exposure_raw
            try:
                exposure_seconds = float(numerator) / float(denominator)
            except (TypeError, ValueError, ZeroDivisionError):
                return None
            return exposure_seconds if exposure_seconds > 0.0 else None
        if len(exposure_raw) == 1:
            exposure_raw = exposure_raw[0]
    numerator = getattr(exposure_raw, "numerator", None)
    denominator = getattr(exposure_raw, "denominator", None)
    if numerator is not None and denominator is not None:
        try:
            exposure_seconds = float(numerator) / float(denominator)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
        return exposure_seconds if exposure_seconds > 0.0 else None
    if isinstance(exposure_raw, bool):
        return None
    if isinstance(exposure_raw, (int, float)):
        exposure_seconds = float(exposure_raw)
        return exposure_seconds if exposure_seconds > 0.0 else None
    if isinstance(exposure_raw, bytes):
        try:
            exposure_text = exposure_raw.decode("ascii").strip()
        except UnicodeDecodeError:
            return None
    elif isinstance(exposure_raw, str):
        exposure_text = exposure_raw.strip()
    else:
        return None
    exposure_text = exposure_text.rstrip("\x00")
    if not exposure_text:
        return None
    if "/" in exposure_text:
        numerator_text, denominator_text = exposure_text.split("/", 1)
        try:
            exposure_seconds = float(numerator_text) / float(denominator_text)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
        return exposure_seconds if exposure_seconds > 0.0 else None
    try:
        exposure_seconds = float(exposure_text)
    except ValueError:
        return None
    return exposure_seconds if exposure_seconds > 0.0 else None


def _extract_dng_exif_payload_and_timestamp(pil_image_module, input_dng):
    """@brief Extract DNG EXIF payload bytes, preferred datetime timestamp, source orientation, and exposure time.

    @details Opens input DNG via Pillow, suppresses known non-actionable
    `PIL.TiffImagePlugin` metadata warning for malformed TIFF tag `33723`, reads
    EXIF mapping without orientation mutation, serializes payload for JPEG save
    while source image handle is still open, resolves source orientation from
    EXIF tag `274`, resolves datetime/exposure metadata from the top-level EXIF
    mapping with fallback to the nested EXIF IFD (`34665`) when Pillow omits
    those tags from the root mapping, parses EXIF `ExposureTime` to positive
    seconds, and resolves filesystem timestamp priority:
    `DateTimeOriginal`(36867) > `DateTimeDigitized`(36868) > `DateTime`(306).
    @param pil_image_module {ModuleType} Imported Pillow Image module.
    @param input_dng {Path} Source DNG path.
    @return {tuple[bytes|None, float|None, int, float|None]} `(exif_payload, exif_timestamp, source_orientation, exposure_time_seconds)` with orientation defaulting to `1`.
    @satisfies REQ-066, REQ-074, REQ-077, REQ-161
    """

    if not hasattr(pil_image_module, "open"):
        return (None, None, 1, None)
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r".*tag 33723 had too many entries.*",
                category=UserWarning,
            )
            with pil_image_module.open(str(input_dng)) as source_image:
                if not hasattr(source_image, "getexif"):
                    return (None, None, 1, None)
                exif_data = source_image.getexif()
                if exif_data is None:
                    return (None, None, 1, None)
                exif_payload = (
                    exif_data.tobytes() if hasattr(exif_data, "tobytes") else None
                )

                exif_ifd_data = None
                if hasattr(exif_data, "get_ifd"):
                    try:
                        exif_ifd_data = exif_data.get_ifd(_EXIF_IFD_POINTER)
                    except (KeyError, TypeError, ValueError, AttributeError):
                        exif_ifd_data = None

                def _read_exif_value(exif_tag):
                    """@brief Resolve one EXIF value from root EXIF data with nested-IFD fallback.

                    @details Reads the requested EXIF tag from the top-level Pillow
                    EXIF mapping first, then falls back to the nested EXIF IFD payload
                    when available. Complexity: O(1). Side effects: none.
                    @param exif_tag {int} Numeric EXIF tag identifier.
                    @return {object|None} Raw EXIF value or `None` when absent in both locations.
                    @satisfies REQ-161
                    """

                    root_value = exif_data.get(exif_tag)
                    if root_value is not None:
                        return root_value
                    if exif_ifd_data is None or not hasattr(exif_ifd_data, "get"):
                        return None
                    return exif_ifd_data.get(exif_tag)

                source_orientation = 1
                orientation_raw = _read_exif_value(_EXIF_TAG_ORIENTATION)
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
                        _read_exif_value(exif_tag)
                    )
                    if exif_timestamp is not None:
                        break
                exposure_time_seconds = _parse_exif_exposure_time_to_seconds(
                    _read_exif_value(_EXIF_TAG_EXPOSURE_TIME)
                )
                return (
                    exif_payload,
                    exif_timestamp,
                    source_orientation,
                    exposure_time_seconds,
                )
    except (OSError, ValueError, TypeError, AttributeError):
        return (None, None, 1, None)


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
    pil_image_module, final_image_rgb_uint8, source_orientation
):
    """@brief Build refreshed JPEG thumbnail bytes from final quantized JPG pixels.

    @details Creates a Pillow image from the final RGB uint8 array that is saved
    as the output JPG, applies source-orientation-aware transform, scales to the
    bounded thumbnail size, and serializes deterministic JPEG thumbnail payload
    for EXIF embedding without re-reading the output file.
    @param pil_image_module {ModuleType} Imported Pillow Image module.
    @param final_image_rgb_uint8 {numpy.ndarray} Final RGB uint8 array used for JPG save.
    @param source_orientation {int} EXIF orientation value in range `1..8`.
    @return {bytes} Serialized JPEG thumbnail payload.
    @satisfies REQ-041, REQ-078
    """

    output_image = pil_image_module.fromarray(final_image_rgb_uint8)
    if getattr(output_image, "mode", "") != "RGB":
        output_image = output_image.convert("RGB")
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
    final_image_rgb_uint8,
    source_exif_payload,
    source_orientation,
):
    """@brief Refresh output JPG EXIF thumbnail while preserving source orientation.

    @details Loads source EXIF payload, regenerates thumbnail from the final
    quantized RGB uint8 image used for JPG save, preserves source orientation in
    main EXIF IFD, sets thumbnail orientation to identity, and re-inserts updated
    EXIF payload into output JPG before any filesystem timestamp synchronization.
    @param pil_image_module {ModuleType} Imported Pillow Image module.
    @param piexif_module {ModuleType} Imported piexif module.
    @param output_jpg {Path} Final JPG path.
    @param final_image_rgb_uint8 {numpy.ndarray} Final RGB uint8 array used for JPG save.
    @param source_exif_payload {bytes} Serialized EXIF payload from source DNG.
    @param source_orientation {int} Source EXIF orientation value in range `1..8`.
    @return {None} Side effects only.
    @exception RuntimeError Raised when EXIF thumbnail refresh fails.
    @satisfies REQ-014, REQ-041, REQ-078
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
            final_image_rgb_uint8=final_image_rgb_uint8,
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
    applies update only when EXIF datetime parsing produced a valid POSIX value
    after refreshed EXIF metadata has already been written to the output JPG.
    @param output_jpg {Path} Output JPG path.
    @param exif_timestamp {float|None} Source EXIF-derived POSIX timestamp.
    @return {None} Side effects only.
    @exception OSError Raised when filesystem metadata update fails.
    @satisfies REQ-014, REQ-074, REQ-077
    """

    if exif_timestamp is None:
        return
    _set_output_file_timestamps(output_jpg=output_jpg, exif_timestamp=exif_timestamp)


def _build_exposure_multipliers(ev_value, ev_zero=0.0):
    """@brief Compute bracketing brightness multipliers from EV delta and center.

    @details Produces exactly three multipliers mapped to exposure stops
    `[ev_zero-ev, ev_zero, ev_zero+ev]` as powers of two for float-domain HDR
    base-image scaling.
    @param ev_value {float} Exposure bracket EV delta.
    @param ev_zero {float} Central bracket EV value.
    @return {tuple[float, float, float]} Multipliers in order `(under, base, over)`.
    @satisfies REQ-009, REQ-159, REQ-160
    """

    return (
        2 ** (ev_zero - ev_value),
        2**ev_zero,
        2 ** (ev_zero + ev_value),
    )


def _build_bracket_images_from_linear_base_float(np_module, base_rgb_float, multipliers):
    """@brief Build normalized HDR brackets from one linear RGB base tensor.

    @details Broadcast-multiplies one linear RGB base tensor by the ordered EV
    multiplier triplet `(ev_minus, ev_zero, ev_plus)`, clamps each result into
    `[0,1]`, and returns float32 bracket tensors in canonical downstream order.
    The input base tensor range is preserved before EV scaling to avoid
    stage-local pre-clipping. Complexity: O(3*H*W). Side effects: none.
    @param np_module {ModuleType} Imported numpy module.
    @param base_rgb_float {object} Linear RGB float tensor.
    @param multipliers {tuple[float, float, float]} Ordered EV multipliers.
    @return {list[object]} Ordered RGB float32 bracket tensors.
    @satisfies REQ-159, REQ-160
    """

    linear_base = _ensure_three_channel_float_array_no_range_adjust(
        np_module=np_module,
        image_data=base_rgb_float,
    ).astype(np_module.float32, copy=False)
    bracket_images_float = []
    for multiplier in multipliers:
        scaled = np_module.clip(
            linear_base.astype(np_module.float64) * float(multiplier),
            0.0,
            1.0,
        )
        bracket_images_float.append(scaled.astype(np_module.float32))
    return bracket_images_float


def _build_white_balance_analysis_image_from_linear_base_float(
    np_module,
    base_rgb_float,
    ev_zero,
):
    """@brief Build unclipped white-balance analysis image from linear base and EV center.

    @details Converts the shared linear base tensor to RGB float without range
    clipping and multiplies it by `2^ev_zero` to produce one unclipped analysis
    payload independent from bracket clipping side effects.
    @param np_module {ModuleType} Imported numpy module.
    @param base_rgb_float {object} Shared linear base RGB tensor.
    @param ev_zero {float} Resolved center EV.
    @return {object} RGB float32 analysis image without stage-local clipping.
    @satisfies REQ-183, REQ-200
    """

    normalized_base = _ensure_three_channel_float_array_no_range_adjust(
        np_module=np_module,
        image_data=base_rgb_float,
    ).astype(np_module.float64, copy=False)
    center_multiplier = float(2 ** float(ev_zero))
    return (normalized_base * center_multiplier).astype(np_module.float32, copy=False)


def _validate_white_balance_triplet_shape(np_module, bracket_images_float):
    """@brief Validate white-balance bracket triplet shape contract.

    @details Normalizes each bracket to RGB float32 and verifies that all three
    bracket tensors share identical shape so one EV0-derived correction payload
    can be applied deterministically to every bracket.
    @param np_module {ModuleType} Imported numpy module.
    @param bracket_images_float {Sequence[object]} Candidate bracket tensors.
    @return {tuple[object, object, object]} Normalized `(ev_minus, ev_zero, ev_plus)` RGB float32 tensors.
    @exception ValueError Raised when bracket count is not three or shapes differ.
    @satisfies REQ-183
    """

    if len(bracket_images_float) != 3:
        raise ValueError("White-balance stage requires exactly three bracket images")
    normalized_triplet = tuple(
        _normalize_float_rgb_image(
            np_module=np_module,
            image_data=bracket_image,
        ).astype(np_module.float32, copy=False)
        for bracket_image in bracket_images_float
    )
    reference_shape = normalized_triplet[0].shape
    if normalized_triplet[1].shape != reference_shape or normalized_triplet[2].shape != reference_shape:
        raise ValueError("White-balance stage requires bracket images with identical shapes")
    return normalized_triplet


def _build_xphoto_analysis_image_rgb_float(np_module, analysis_image_rgb_float):
    """@brief Build deterministic real-image xphoto analysis payload.

    @details Converts one analysis image to RGB float, preserves values above
    `1.0`, replaces non-finite values with `0`, removes negatives, and applies
    deterministic pyramid downsampling (`::2`) until maximum side is `<=1024`.
    This removes fixed proxy-size assumptions while keeping xphoto estimation
    stable and bounded in memory.
    @param np_module {ModuleType} Imported numpy module.
    @param analysis_image_rgb_float {object} Analysis RGB float tensor.
    @return {object} Downsampled RGB float32 analysis payload.
    @satisfies REQ-183, REQ-184, REQ-185, REQ-186
    """

    analysis_rgb = _ensure_three_channel_float_array_no_range_adjust(
        np_module=np_module,
        image_data=analysis_image_rgb_float,
    ).astype(np_module.float64, copy=False)
    finite_mask = np_module.isfinite(analysis_rgb)
    analysis_rgb = np_module.where(finite_mask, analysis_rgb, 0.0)
    analysis_rgb = np_module.maximum(analysis_rgb, 0.0)
    while max(analysis_rgb.shape[0], analysis_rgb.shape[1]) > 1024:
        analysis_rgb = analysis_rgb[::2, ::2, :]
    return analysis_rgb.astype(np_module.float32, copy=False)


def _build_white_balance_robust_analysis_mask(np_module, analysis_rgb_float):
    """@brief Build robust white-balance mask excluding near-black and near-saturated pixels.

    @details Builds a deterministic per-pixel mask using finite and non-negative
    RGB values, excludes near-black pixels (`max_channel<=1e-3`), excludes
    near-saturated pixels (`max_channel>=0.995`), and applies fallback tiers to
    guarantee at least one valid pixel for downstream statistics.
    @param np_module {ModuleType} Imported numpy module.
    @param analysis_rgb_float {object} Analysis RGB float tensor.
    @return {object} Boolean mask with shape `(H,W)`.
    @satisfies REQ-187, REQ-188
    """

    analysis_rgb = _ensure_three_channel_float_array_no_range_adjust(
        np_module=np_module,
        image_data=analysis_rgb_float,
    ).astype(np_module.float64, copy=False)
    finite_mask = np_module.all(np_module.isfinite(analysis_rgb), axis=2)
    non_negative_mask = np_module.all(analysis_rgb >= 0.0, axis=2)
    channel_max = np_module.max(analysis_rgb, axis=2)
    robust_mask = (
        finite_mask
        & non_negative_mask
        & (channel_max > 1e-3)
        & (channel_max < 0.995)
    )
    if not bool(np_module.any(robust_mask)):
        robust_mask = finite_mask & non_negative_mask & (channel_max > 1e-3)
    if not bool(np_module.any(robust_mask)):
        robust_mask = finite_mask & non_negative_mask
    return robust_mask


def _extract_white_balance_channel_gains_from_xphoto(
    cv2_module,
    np_module,
    wb_algorithm,
    analysis_image_rgb_float,
):
    """@brief Derive per-channel white-balance gains from one OpenCV xphoto algorithm.

    @details Builds one real-image analysis payload with deterministic pyramid
    downsampling, performs one backend-local normalization to `[0,1]` for xphoto
    quantization only, executes xphoto `balanceWhite(...)`, and derives one gain
    vector from channel means `balanced/original`. Gains are finite positive
    float64 values.
    @param cv2_module {ModuleType} Imported OpenCV module.
    @param np_module {ModuleType} Imported numpy module.
    @param wb_algorithm {object} OpenCV xphoto white-balance instance.
    @param analysis_image_rgb_float {object} EV0 RGB float tensor.
    @return {object} Channel gains vector with shape `(3,)`.
    @exception RuntimeError Raised when xphoto result shape is invalid.
    @satisfies REQ-183, REQ-184, REQ-185, REQ-186, REQ-201
    """

    analysis_payload_rgb = _build_xphoto_analysis_image_rgb_float(
        np_module=np_module,
        analysis_image_rgb_float=analysis_image_rgb_float,
    )
    payload_scale = float(np_module.percentile(analysis_payload_rgb, 99.5))
    if not math.isfinite(payload_scale) or payload_scale <= 1e-12:
        payload_scale = 1.0
    scaled_payload_rgb = np_module.clip(
        analysis_payload_rgb.astype(np_module.float64, copy=False) / payload_scale,
        0.0,
        1.0,
    ).astype(np_module.float32, copy=False)
    analysis_payload_bgr_uint8 = cv2_module.cvtColor(
        _to_uint8_image_array(
            np_module=np_module,
            image_data=scaled_payload_rgb,
        ),
        cv2_module.COLOR_RGB2BGR,
    )
    balanced_payload_bgr_uint8 = wb_algorithm.balanceWhite(analysis_payload_bgr_uint8)
    source_payload_rgb_float = _normalize_float_rgb_image(
        np_module=np_module,
        image_data=cv2_module.cvtColor(analysis_payload_bgr_uint8, cv2_module.COLOR_BGR2RGB),
    ).astype(np_module.float64, copy=False)
    balanced_payload_rgb_float = _normalize_float_rgb_image(
        np_module=np_module,
        image_data=cv2_module.cvtColor(balanced_payload_bgr_uint8, cv2_module.COLOR_BGR2RGB),
    ).astype(np_module.float64, copy=False)
    source_mean = np_module.mean(source_payload_rgb_float, axis=(0, 1))
    balanced_mean = np_module.mean(balanced_payload_rgb_float, axis=(0, 1))
    source_mean = np_module.maximum(source_mean, 1e-12)
    gains = balanced_mean / source_mean
    gains = np_module.where(np_module.isfinite(gains), gains, 1.0)
    gains = np_module.maximum(gains, 1e-12)
    if gains.shape != (3,):
        raise RuntimeError("White-balance gain extraction returned invalid channel vector")
    return gains.astype(np_module.float64, copy=False)


def _estimate_xphoto_white_balance_gains_rgb(
    cv2_module,
    np_module,
    white_balance_mode,
    analysis_image_rgb_float,
):
    """@brief Estimate EV0-derived white-balance gains using OpenCV xphoto modes.

    @details Creates one OpenCV xphoto white-balance instance for `Simple`,
    `GrayworldWB`, or `IA`, applies optional mode-specific setup, and derives
    one channel-gain vector from EV0 analysis only.
    @param cv2_module {ModuleType} Imported OpenCV module.
    @param np_module {ModuleType} Imported numpy module.
    @param white_balance_mode {str} Canonical white-balance mode selector.
    @param analysis_image_rgb_float {object} EV0 RGB float tensor.
    @return {object} Channel gains vector with shape `(3,)`.
    @exception RuntimeError Raised when required xphoto API is unavailable.
    @exception ValueError Raised when mode is unsupported for xphoto estimation.
    @satisfies REQ-183, REQ-184, REQ-185, REQ-186
    """

    xphoto_module = getattr(cv2_module, "xphoto", None)
    if xphoto_module is None:
        raise RuntimeError("OpenCV xphoto module is unavailable for white-balance stage")
    if white_balance_mode == WHITE_BALANCE_MODE_SIMPLE:
        factory = getattr(xphoto_module, "createSimpleWB", None)
        if factory is None:
            raise RuntimeError("OpenCV xphoto SimpleWB is unavailable")
        wb_algorithm = factory()
    elif white_balance_mode == WHITE_BALANCE_MODE_GRAYWORLD:
        factory = getattr(xphoto_module, "createGrayworldWB", None)
        if factory is None:
            raise RuntimeError("OpenCV xphoto GrayworldWB is unavailable")
        wb_algorithm = factory()
    elif white_balance_mode == WHITE_BALANCE_MODE_IA:
        factory = getattr(xphoto_module, "createLearningBasedWB", None)
        if factory is None:
            raise RuntimeError("OpenCV xphoto LearningBasedWB is unavailable")
        wb_algorithm = factory()
        set_hist_bins = getattr(wb_algorithm, "setHistBinNum", None)
        if callable(set_hist_bins):
            set_hist_bins(256)
    else:
        raise ValueError(f"Unsupported xphoto white-balance mode: {white_balance_mode}")
    return _extract_white_balance_channel_gains_from_xphoto(
        cv2_module=cv2_module,
        np_module=np_module,
        wb_algorithm=wb_algorithm,
        analysis_image_rgb_float=analysis_image_rgb_float,
    )


def _estimate_color_constancy_white_balance_gains_rgb(
    np_module,
    skimage_color_module,
    analysis_image_rgb_float,
):
    """@brief Estimate EV0-derived white-balance gains using scikit-image color constancy.

    @details Normalizes the analysis image to RGB float, builds one robust mask
    excluding near-black and near-saturated pixels, converts masked RGB data to
    one scalar luminance map via `skimage.color.rgb2gray(...)`, computes masked
    channel and luminance means, and derives one Von-Kries-like gain vector
    `luma_mean/channel_mean`.
    @param np_module {ModuleType} Imported numpy module.
    @param skimage_color_module {ModuleType} Imported scikit-image color module.
    @param analysis_image_rgb_float {object} EV0 RGB float tensor.
    @return {object} Channel gains vector with shape `(3,)`.
    @satisfies REQ-183, REQ-187
    """

    analysis_rgb = _ensure_three_channel_float_array_no_range_adjust(
        np_module=np_module,
        image_data=analysis_image_rgb_float,
    ).astype(np_module.float64, copy=False)
    robust_mask = _build_white_balance_robust_analysis_mask(
        np_module=np_module,
        analysis_rgb_float=analysis_rgb,
    )
    masked_rgb = analysis_rgb[robust_mask]
    luminance = skimage_color_module.rgb2gray(masked_rgb.reshape((-1, 1, 3)))
    luminance_mean = float(np_module.mean(luminance))
    channel_means = np_module.mean(masked_rgb, axis=0)
    channel_means = np_module.maximum(channel_means, 1e-12)
    gains = luminance_mean / channel_means
    gains = np_module.where(np_module.isfinite(gains), gains, 1.0)
    gains = np_module.maximum(gains, 1e-12)
    return gains.astype(np_module.float64, copy=False)


def _estimate_ttl_white_balance_gains_rgb(np_module, analysis_image_rgb_float):
    """@brief Estimate EV0-derived TTL white-balance gains using channel averages.

    @details Normalizes the analysis image to RGB float, builds one robust mask
    excluding near-black and near-saturated pixels, computes masked channel
    means `(R,G,B)`, computes global gray average as `(R+G+B)/3`, and derives
    channel gains as `gray/channel_mean` without clipping for downstream
    float-domain application.
    @param np_module {ModuleType} Imported numpy module.
    @param analysis_image_rgb_float {object} EV0 RGB float tensor.
    @return {object} Channel gains vector with shape `(3,)`.
    @satisfies REQ-183, REQ-188
    """

    analysis_rgb = _ensure_three_channel_float_array_no_range_adjust(
        np_module=np_module,
        image_data=analysis_image_rgb_float,
    ).astype(np_module.float64, copy=False)
    robust_mask = _build_white_balance_robust_analysis_mask(
        np_module=np_module,
        analysis_rgb_float=analysis_rgb,
    )
    masked_rgb = analysis_rgb[robust_mask]
    channel_means = np_module.mean(masked_rgb, axis=0)
    channel_means = np_module.maximum(channel_means, 1e-12)
    gray_mean = float(np_module.mean(channel_means))
    gains = gray_mean / channel_means
    gains = np_module.where(np_module.isfinite(gains), gains, 1.0)
    gains = np_module.maximum(gains, 1e-12)
    return gains.astype(np_module.float64, copy=False)


def _apply_channel_gains_to_white_balance_triplet(
    np_module,
    bracket_triplet_rgb_float,
    channel_gains,
):
    """@brief Apply one shared channel-gain vector to all three bracket images.

    @details Broadcast-multiplies RGB channels of each bracket with the same
    gain vector to enforce identical white-balance transform across
    `(ev_minus, ev_zero, ev_plus)` without stage-local clipping.
    @param np_module {ModuleType} Imported numpy module.
    @param bracket_triplet_rgb_float {tuple[object, object, object]} Normalized RGB bracket tensors.
    @param channel_gains {object} Channel gains vector `(r_gain, g_gain, b_gain)`.
    @return {list[object]} White-balanced bracket tensors in canonical order.
    @satisfies REQ-183, REQ-184, REQ-185, REQ-186, REQ-187, REQ-188
    """

    gains_rgb = np_module.asarray(channel_gains, dtype=np_module.float64).reshape((1, 1, 3))
    balanced_triplet = []
    for bracket_image_rgb in bracket_triplet_rgb_float:
        balanced_triplet.append(
            (
                bracket_image_rgb.astype(np_module.float64, copy=False)
                * gains_rgb
            ).astype(np_module.float32)
        )
    return balanced_triplet


def _apply_white_balance_to_bracket_triplet(
    bracket_images_float,
    white_balance_mode,
    white_balance_analysis_image_float,
    auto_adjust_dependencies,
):
    """@brief Apply optional analysis-image-derived white-balance correction to bracket triplet.

    @details Keeps the stage disabled when `white_balance_mode` is `None`. When
    enabled, analyzes one configured analysis image, derives one correction
    payload by selected mode, and applies identical correction to all three
    brackets before HDR merge.
    @param bracket_images_float {Sequence[object]} Ordered RGB float bracket tensors `(ev_minus, ev_zero, ev_plus)`.
    @param white_balance_mode {str|None} Optional canonical white-balance mode selector.
    @param white_balance_analysis_image_float {object} Selected white-balance analysis RGB float tensor.
    @param auto_adjust_dependencies {tuple[ModuleType, ModuleType]|None} Optional `(cv2, numpy)` dependency tuple.
    @return {list[object]} Ordered bracket tensors after optional white-balance stage.
    @exception RuntimeError Raised when required dependencies are missing.
    @exception ValueError Raised when mode is unsupported or bracket contract is invalid.
    @satisfies REQ-182, REQ-183, REQ-184, REQ-185, REQ-186, REQ-187, REQ-188, REQ-200
    """

    if white_balance_mode is None:
        return [bracket_image for bracket_image in bracket_images_float]
    if auto_adjust_dependencies is not None:
        cv2_module, np_module = auto_adjust_dependencies
    else:
        numpy_module = _resolve_numpy_dependency()
        if numpy_module is None:
            raise RuntimeError("Missing required dependency: numpy")
        cv2_module = None
        np_module = numpy_module
    normalized_triplet = _validate_white_balance_triplet_shape(
        np_module=np_module,
        bracket_images_float=bracket_images_float,
    )
    analysis_rgb = _ensure_three_channel_float_array_no_range_adjust(
        np_module=np_module,
        image_data=white_balance_analysis_image_float,
    ).astype(np_module.float32, copy=False)
    if white_balance_mode in (
        WHITE_BALANCE_MODE_SIMPLE,
        WHITE_BALANCE_MODE_GRAYWORLD,
        WHITE_BALANCE_MODE_IA,
    ):
        if cv2_module is None:
            resolved_dependencies = _resolve_auto_adjust_dependencies()
            if resolved_dependencies is None:
                raise RuntimeError(
                    "Missing required dependencies: opencv-contrib-python and numpy"
                )
            cv2_module, np_module = resolved_dependencies
        channel_gains = _estimate_xphoto_white_balance_gains_rgb(
            cv2_module=cv2_module,
            np_module=np_module,
            white_balance_mode=white_balance_mode,
            analysis_image_rgb_float=analysis_rgb,
        )
    elif white_balance_mode == WHITE_BALANCE_MODE_COLOR_CONSTANCY:
        try:
            from skimage import color as skimage_color_module  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Missing required dependency: scikit-image"
            ) from exc
        channel_gains = _estimate_color_constancy_white_balance_gains_rgb(
            np_module=np_module,
            skimage_color_module=skimage_color_module,
            analysis_image_rgb_float=analysis_rgb,
        )
    elif white_balance_mode == WHITE_BALANCE_MODE_TTL:
        channel_gains = _estimate_ttl_white_balance_gains_rgb(
            np_module=np_module,
            analysis_image_rgb_float=analysis_rgb,
        )
    else:
        raise ValueError(f"Unsupported --auto-white-balance mode: {white_balance_mode}")
    return _apply_channel_gains_to_white_balance_triplet(
        np_module=np_module,
        bracket_triplet_rgb_float=normalized_triplet,
        channel_gains=channel_gains,
    )


def _extract_bracket_images_float(
    raw_handle,
    np_module,
    multipliers,
    base_rgb_float=None,
    raw_white_balance_mode=DEFAULT_RAW_WHITE_BALANCE_MODE,
):
    """@brief Extract three normalized RGB float brackets from one RAW handle.

    @details Reuses an optional precomputed normalized linear base tensor when
    available, otherwise executes one deterministic linear camera-WB-aware RAW
    postprocess call, and derives canonical bracket tensors by NumPy EV
    scaling and `[0,1]` clipping without exposing TIFF artifacts outside this
    step. Complexity: O(H*W). Side effects: at most one RAW postprocess
    invocation.
    @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
    @param np_module {ModuleType} Imported numpy module.
    @param multipliers {tuple[float, float, float]} Ordered exposure multipliers.
    @param base_rgb_float {object|None} Optional precomputed normalized linear RGB float base tensor.
    @param raw_white_balance_mode {str} RAW WB normalization mode selector used when base extraction executes in this function.
    @return {list[object]} Ordered RGB float bracket tensors.
    @satisfies REQ-010, REQ-157, REQ-158, REQ-159, REQ-160, REQ-203, REQ-204, REQ-205, REQ-206, REQ-207
    """

    labels = ("ev_minus", "ev_zero", "ev_plus")
    if base_rgb_float is None:
        base_rgb_float = _extract_base_rgb_linear_float(
            raw_handle=raw_handle,
            np_module=np_module,
            raw_white_balance_mode=raw_white_balance_mode,
        )
    bracket_images_float = _build_bracket_images_from_linear_base_float(
        np_module=np_module,
        base_rgb_float=base_rgb_float,
        multipliers=multipliers,
    )
    for label, multiplier in zip(labels, multipliers):
        print_info(f"Extracting bracket {label}: ev-scale={multiplier:.4f}x from linear base")
    return bracket_images_float


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


def _format_external_command_for_log(command):
    """@brief Format one external command argv into deterministic shell-like text.

    @details Converts one sequence of raw argv tokens into one reproducible
    shell-style command string using POSIX quoting rules so runtime diagnostics
    can report the exact external command syntax and parameters without relying
    on shell execution. Complexity: `O(n)` in total token length. Side effects:
    none.
    @param command {Sequence[str]} External command argv tokens in execution order.
    @return {str} One shell-quoted command string suitable for runtime logging.
    @satisfies REQ-011
    """

    return shlex.join(command)


def _run_luminance_hdr_cli(
    bracket_images_float,
    temp_dir,
    imageio_module,
    np_module,
    ev_value,
    ev_zero,
    luminance_options,
):
    """@brief Merge bracket float images into one RGB float image via `luminance-hdr-cli`.

    @details Builds deterministic luminance-hdr-cli argv using EV sequence
    centered around zero-reference (`-ev_value,0,+ev_value`) even when extraction
    uses non-zero `ev_zero`, serializes float inputs to local float32 TIFFs,
    forwards deterministic HDR/TMO arguments including `--ldrTiff 32b` to force
    float32 output, emits one runtime log line with the full executed command
    syntax and parameters, isolates sidecar artifacts in a backend-specific
    temporary directory, then reloads the produced float32 TIFF and normalizes
    it back to DNG2JPG RGB float `[0,1]` working format.
    @param bracket_images_float {Sequence[object]} Ordered RGB float bracket tensors.
    @param temp_dir {Path} Temporary workspace root.
    @param imageio_module {ModuleType} Imported imageio module with `imread` and `imwrite`.
    @param np_module {ModuleType} Imported numpy module.
    @param ev_value {float} EV bracket delta used to generate exposure files.
    @param ev_zero {float} Central EV used to generate exposure files.
    @param luminance_options {LuminanceOptions} Luminance backend command controls.
    @return {object} Normalized RGB float merged image.
    @exception subprocess.CalledProcessError Raised when `luminance-hdr-cli` returns non-zero exit status.
    @satisfies REQ-011, REQ-033, REQ-034, REQ-035, REQ-174, REQ-175
    """

    backend_dir = temp_dir / "luminance"
    backend_dir.mkdir(parents=True, exist_ok=True)
    bracket_paths = _materialize_bracket_tiffs_from_float(
        imageio_module=imageio_module,
        np_module=np_module,
        bracket_images_float=bracket_images_float,
        temp_dir=backend_dir,
    )
    output_hdr_tiff = backend_dir / "merged_hdr.tif"
    ordered_paths = _order_bracket_paths(bracket_paths)
    command = [
        "luminance-hdr-cli",
        "-e",
        f"{-ev_value:g},0,{ev_value:g}",
        "-g",
        "1",
        "-S",
        "1",
        "-G",
        "1",
        "--hdrModel",
        luminance_options.hdr_model,
        "--hdrWeight",
        luminance_options.hdr_weight,
        "--hdrResponseCurve",
        luminance_options.hdr_response_curve,
        "--tmo",
        luminance_options.tmo,
        "--ldrTiff",
        "32b",
        *luminance_options.tmo_extra_args,
        "-o",
        str(output_hdr_tiff),
        *[str(path) for path in ordered_paths],
    ]
    print_info(
        "Luminance-HDR command: "
        f"{_format_external_command_for_log(command)}"
    )
    original_working_directory = Path.cwd()
    backend_working_directory = output_hdr_tiff.parent
    try:
        os.chdir(backend_working_directory)
        subprocess.run(command, check=True)
    finally:
        os.chdir(original_working_directory)
    return _normalize_float_rgb_image(
        np_module=np_module,
        image_data=imageio_module.imread(str(output_hdr_tiff)),
    )


def _build_opencv_radiance_exposure_times(
    source_exposure_time_seconds,
    ev_zero,
    ev_delta,
):
    """@brief Build OpenCV radiance exposure times in seconds from EXIF exposure and EV offsets.

    @details Computes OpenCV Debevec/Robertson exposure times in seconds from the
    extracted RAW EXIF `ExposureTime` associated with the linear base image and
    maps them to bracket order `(ev_minus, ev_zero, ev_plus)` as
    `t_raw*2^(ev_zero-ev_delta)`, `t_raw*2^ev_zero`, and `t_raw*2^(ev_zero+ev_delta)`.
    @param source_exposure_time_seconds {float} Positive source EXIF exposure time in seconds.
    @param ev_zero {float} Central EV used during bracket extraction.
    @param ev_delta {float} EV bracket delta used during bracket extraction.
    @return {object} `numpy.float32` vector with length `3`.
    @exception RuntimeError Raised when numpy dependency is unavailable.
    @exception ValueError Raised when source exposure time is missing or invalid.
    @satisfies REQ-109, REQ-142, REQ-161
    """

    try:
        import numpy as np_module  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing required dependency: numpy") from exc
    if source_exposure_time_seconds is None or float(source_exposure_time_seconds) <= 0.0:
        raise ValueError("Missing valid EXIF ExposureTime for OpenCV radiance merge")
    exposure_seconds = float(source_exposure_time_seconds)
    return np_module.array(
        [
            exposure_seconds * (2 ** (ev_zero - ev_delta)),
            exposure_seconds * (2**ev_zero),
            exposure_seconds * (2 ** (ev_zero + ev_delta)),
        ],
        dtype=np_module.float32,
    )


def _build_ev_times_from_ev_zero_and_delta(ev_zero, ev_delta):
    """@brief Build deterministic unit-base exposure times array from EV center and EV delta.

    @details Delegates to the OpenCV radiance exposure-time helper using unit
    source exposure `1.0` second so tests and compatibility callers can verify
    deterministic stop-space mapping without EXIF metadata dependency.
    @param ev_zero {float} Central EV used during bracket extraction.
    @param ev_delta {float} EV bracket delta used during bracket extraction.
    @return {object} `numpy.float32` vector with length `3`.
    @exception RuntimeError Raised when numpy dependency is unavailable.
    @satisfies REQ-109, REQ-142
    """

    return _build_opencv_radiance_exposure_times(
        source_exposure_time_seconds=1.0,
        ev_zero=ev_zero,
        ev_delta=ev_delta,
    )


def _normalize_opencv_hdr_to_unit_range(np_module, hdr_rgb_float32):
    """@brief Normalize OpenCV HDR tensor to unit range with deterministic bounds.

    @details Normalizes arbitrary OpenCV HDR or fusion output to one congruent
    RGB float contract. Negative and non-finite values are cleared via
    `np.maximum(0.0)` floor, and values above unit range are scaled down by
    global maximum; no final `[0,1]` clipping is applied because the
    floor-and-scale sequence guarantees the output is bounded within `[0,1]`
    deterministically.
    @param np_module {ModuleType} Imported numpy module.
    @param hdr_rgb_float32 {object} OpenCV HDR or fusion RGB tensor.
    @return {object} Normalized RGB float tensor bounded within `[0,1]` by floor-and-scale normalization.
    @satisfies REQ-110, REQ-143, REQ-144
    """

    hdr_rgb_float64 = np_module.array(hdr_rgb_float32, dtype=np_module.float64)
    finite_mask = np_module.isfinite(hdr_rgb_float64)
    hdr_rgb_float64 = np_module.where(finite_mask, hdr_rgb_float64, 0.0)
    hdr_rgb_float64 = np_module.maximum(hdr_rgb_float64, 0.0)
    max_value = float(np_module.max(hdr_rgb_float64)) if hdr_rgb_float64.size else 0.0
    if max_value > 1.0:
        hdr_rgb_float64 = hdr_rgb_float64 / max_value
    normalized = hdr_rgb_float64
    return normalized.astype(np_module.float32)


def _run_opencv_merge_mertens(
    cv2_module,
    np_module,
    exposures_float,
    tonemap_enabled,
    tonemap_gamma,
):
    """@brief Execute OpenCV Mertens exposure fusion path.

    @details Runs `cv2.createMergeMertens().process(...)` on RGB float
    brackets that already share one identical merge-gamma transfer curve,
    rescales the float result by `255` to match OpenCV exposure-fusion
    brightness semantics observed on `uint8` inputs, optionally applies OpenCV
    simple gamma tonemap with user-configured gamma, and then normalizes the
    result to the repository RGB float contract.
    @param cv2_module {ModuleType} Imported OpenCV module.
    @param np_module {ModuleType} Imported numpy module.
    @param exposures_float {list[object]} Ordered RGB float bracket tensors preconditioned with one identical merge-gamma transfer.
    @param tonemap_enabled {bool} `True` enables simple OpenCV tone mapping.
    @param tonemap_gamma {float} Positive gamma passed to `createTonemap`.
    @return {object} Normalized RGB float tensor.
    @satisfies REQ-108, REQ-110, REQ-143, REQ-144, REQ-154
    """

    fusion_rgb = cv2_module.createMergeMertens().process(exposures_float)
    fusion_rgb = np_module.array(fusion_rgb, dtype=np_module.float32) * 255.0
    if tonemap_enabled:
        tonemap = cv2_module.createTonemap(float(tonemap_gamma))
        fusion_rgb = tonemap.process(fusion_rgb)
    return _normalize_opencv_hdr_to_unit_range(
        np_module=np_module,
        hdr_rgb_float32=fusion_rgb,
    )


def _estimate_opencv_camera_response(
    cv2_module,
    exposures_radiance_uint8,
    exposure_times,
    merge_algorithm,
):
    """@brief Estimate OpenCV inverse camera response for Debevec or Robertson radiance merge.

    @details Selects the OpenCV calibrator matching the requested radiance merge
    algorithm and computes one inverse camera response tensor from backend-local
    `uint8` bracket views derived from the shared linear float contract by the
    caller. This preserves the repository-wide RGB float `[0,1]` interface
    while satisfying the OpenCV radiance path requirement for `CV_8U`
    calibrator inputs. Time complexity: `O(n*p)` where `n` is bracket count and
    `p` is pixels per bracket. Side effects: none.
    @param cv2_module {ModuleType} Imported OpenCV module.
    @param exposures_radiance_uint8 {list[object]} Ordered backend-local RGB `uint8` bracket tensors.
    @param exposure_times {object} OpenCV exposure-time vector.
    @param merge_algorithm {str} Canonical OpenCV merge algorithm token.
    @return {object} OpenCV response tensor compatible with Debevec/Robertson merge calls.
    @exception RuntimeError Raised when `merge_algorithm` is unsupported.
    @satisfies REQ-153, REQ-162
    """

    if merge_algorithm == OPENCV_MERGE_ALGORITHM_DEBEVEC:
        calibrator = cv2_module.createCalibrateDebevec()
    elif merge_algorithm == OPENCV_MERGE_ALGORITHM_ROBERTSON:
        calibrator = cv2_module.createCalibrateRobertson()
    else:
        raise RuntimeError(f"Unsupported OpenCV merge algorithm: {merge_algorithm}")
    return calibrator.process(exposures_radiance_uint8, times=exposure_times)


def _run_opencv_merge_radiance(
    cv2_module,
    np_module,
    exposures_linear_float,
    exposure_times,
    merge_algorithm,
    tonemap_enabled,
    tonemap_gamma,
):
    """@brief Execute OpenCV radiance HDR path for Debevec or Robertson.

    @details Follows the OpenCV tutorial flow by estimating inverse camera
    response with the matching `CalibrateDebevec` or `CalibrateRobertson`
    implementation before `MergeDebevec` or `MergeRobertson`. OpenCV requires
    the radiance path to consume backend-local `uint8` bracket payloads when
    calibrated `response` is supplied, so this helper quantizes the shared
    linear float brackets only inside the backend step, preserving float
    repository interfaces at entry and exit. Then it applies simple OpenCV
    gamma tone mapping when enabled; otherwise normalizes the radiance map
    directly to the repository RGB float contract. Time complexity: `O(n*p)`.
    Side effects: none.
    @param cv2_module {ModuleType} Imported OpenCV module.
    @param np_module {ModuleType} Imported numpy module.
    @param exposures_linear_float {list[object]} Ordered linear RGB float bracket tensors.
    @param exposure_times {object} OpenCV exposure-time vector.
    @param merge_algorithm {str} Canonical OpenCV merge algorithm token.
    @param tonemap_enabled {bool} `True` enables simple OpenCV tone mapping.
    @param tonemap_gamma {float} Positive gamma passed to `createTonemap`.
    @return {object} Normalized RGB float tensor.
    @exception RuntimeError Raised when `merge_algorithm` is unsupported.
    @satisfies REQ-108, REQ-109, REQ-110, REQ-143, REQ-144, REQ-152, REQ-153, REQ-162
    """

    exposures_radiance_uint8 = [
        _to_uint8_image_array(
            np_module=np_module,
            image_data=exposure_linear_float,
        )
        for exposure_linear_float in exposures_linear_float
    ]
    response = _estimate_opencv_camera_response(
        cv2_module=cv2_module,
        exposures_radiance_uint8=exposures_radiance_uint8,
        exposure_times=exposure_times,
        merge_algorithm=merge_algorithm,
    )
    if merge_algorithm == OPENCV_MERGE_ALGORITHM_DEBEVEC:
        hdr_rgb = cv2_module.createMergeDebevec().process(
            exposures_radiance_uint8,
            times=exposure_times,
            response=response,
        )
    elif merge_algorithm == OPENCV_MERGE_ALGORITHM_ROBERTSON:
        hdr_rgb = cv2_module.createMergeRobertson().process(
            exposures_radiance_uint8,
            times=exposure_times,
            response=response,
        )
    else:
        raise RuntimeError(f"Unsupported OpenCV merge algorithm: {merge_algorithm}")

    hdr_rgb = np_module.array(hdr_rgb, dtype=np_module.float32)
    if tonemap_enabled:
        tonemap = cv2_module.createTonemap(float(tonemap_gamma))
        hdr_rgb = tonemap.process(hdr_rgb)
    return _normalize_opencv_hdr_to_unit_range(
        np_module=np_module,
        hdr_rgb_float32=hdr_rgb,
    )


def _normalize_debevec_hdr_to_unit_range(np_module, hdr_rgb_float32, white_point_percentile):
    """@brief Preserve legacy Debevec normalization helper contract.

    @details Keeps the historical helper name as one compatibility adapter for
    tests and references while delegating to the unified OpenCV normalization
    contract used by Debevec, Robertson, and Mertens outputs.
    @param np_module {ModuleType} Imported numpy module.
    @param hdr_rgb_float32 {object} OpenCV HDR RGB tensor.
    @param white_point_percentile {float} Unused legacy parameter retained for compatibility.
    @return {object} Normalized RGB float tensor clamped to `[0,1]`.
    @satisfies REQ-144
    """

    del white_point_percentile
    return _normalize_opencv_hdr_to_unit_range(
        np_module=np_module,
        hdr_rgb_float32=hdr_rgb_float32,
    )


def _run_opencv_tonemap_backend(
    bracket_images_float,
    opencv_tonemap_options,
    auto_adjust_dependencies,
    resolved_merge_gamma,
):
    """@brief Execute OpenCV-Tonemap backend on ev-zero only.

    @details Selects bracket index `1` (`ev_zero`) as the only tone-map input,
    dispatches exactly one OpenCV tone-map implementation (`Drago`, `Reinhard`,
    or `Mantiuk`) with fixed OpenCV `gamma=1.0`, preserves float-domain dynamic
    range without backend-local clipping, and applies merge gamma strictly as
    backend-final step.
    @param bracket_images_float {Sequence[object]} Ordered RGB float bracket tensors `(ev_minus, ev_zero, ev_plus)`.
    @param opencv_tonemap_options {OpenCvTonemapOptions} OpenCV-Tonemap selector and knob payload.
    @param auto_adjust_dependencies {tuple[ModuleType, ModuleType]|None} Optional `(cv2, numpy)` dependency tuple.
    @param resolved_merge_gamma {ResolvedMergeGamma} Backend-final merge-output transfer payload.
    @return {object} OpenCV-Tonemap RGB float tensor after backend-final merge gamma.
    @exception RuntimeError Raised when OpenCV/numpy dependencies are missing.
    @exception ValueError Raised when bracket payload or selector is invalid.
    @satisfies REQ-192, REQ-193, REQ-194, REQ-195, REQ-196, REQ-197, REQ-198
    """

    if len(bracket_images_float) != 3:
        raise ValueError("OpenCV-Tonemap requires exactly three bracket images")
    if auto_adjust_dependencies is not None:
        cv2_module, np_module = auto_adjust_dependencies
    else:
        resolved_dependencies = _resolve_auto_adjust_dependencies()
        if resolved_dependencies is None:
            raise RuntimeError("Missing required dependencies: opencv-python and numpy")
        cv2_module, np_module = resolved_dependencies

    ev_zero_rgb = _ensure_three_channel_float_array_no_clip(
        np_module=np_module,
        image_data=bracket_images_float[1],
    ).astype(np_module.float32, copy=False)

    if opencv_tonemap_options.tonemap_map == OPENCV_TONEMAP_MAP_DRAGO:
        tonemap = cv2_module.createTonemapDrago(
            gamma=1.0,
            saturation=float(opencv_tonemap_options.drago_saturation),
            bias=float(opencv_tonemap_options.drago_bias),
        )
    elif opencv_tonemap_options.tonemap_map == OPENCV_TONEMAP_MAP_REINHARD:
        tonemap = cv2_module.createTonemapReinhard(
            gamma=1.0,
            intensity=float(opencv_tonemap_options.reinhard_intensity),
            light_adapt=float(opencv_tonemap_options.reinhard_light_adapt),
            color_adapt=float(opencv_tonemap_options.reinhard_color_adapt),
        )
    elif opencv_tonemap_options.tonemap_map == OPENCV_TONEMAP_MAP_MANTIUK:
        tonemap = cv2_module.createTonemapMantiuk(
            gamma=1.0,
            scale=float(opencv_tonemap_options.mantiuk_scale),
            saturation=float(opencv_tonemap_options.mantiuk_saturation),
        )
    else:
        raise ValueError(
            f"Unsupported OpenCV-Tonemap selector: {opencv_tonemap_options.tonemap_map}"
        )

    tonemapped_rgb = np_module.asarray(
        tonemap.process(ev_zero_rgb),
        dtype=np_module.float32,
    )
    return _apply_merge_gamma_float_no_clip(
        np_module=np_module,
        image_rgb_float=tonemapped_rgb,
        resolved_merge_gamma=resolved_merge_gamma,
    )


def _derive_opencv_tonemap_enabled(postprocess_options):
    """@brief Resolve OpenCV-Tonemap backend enable state from parsed options.

    @details Returns `True` only when one OpenCV-Tonemap selector payload is
    present in postprocess options. This helper centralizes backend-enable
    derivation for parse output compatibility and run-time dispatch.
    @param postprocess_options {PostprocessOptions} Parsed postprocess payload.
    @return {bool} `True` when OpenCV-Tonemap backend is selected.
    @satisfies REQ-189, REQ-190
    """

    return postprocess_options.opencv_tonemap_options is not None


def _run_opencv_merge_backend(
    bracket_images_float,
    ev_value,
    ev_zero,
    source_exposure_time_seconds,
    opencv_merge_options,
    auto_adjust_dependencies,
    resolved_merge_gamma=None,
):
    """@brief Merge bracket float images into one RGB float image via OpenCV.

    @details Accepts three RGB float bracket tensors ordered as `(ev_minus,
    ev_zero, ev_plus)`, forwards them to backend dispatch without entry
    re-normalization or clipping, derives OpenCV radiance exposure times in
    seconds from EXIF `ExposureTime` for Debevec/Robertson or dispatches
    Mertens directly, and returns one congruent normalized RGB float image.
    Debevec and Robertson consume the shared linear HDR bracket contract
    directly with calibrated inverse response and apply resolved merge gamma
    as one backend-final output step, while Mertens first applies one
    identical resolved merge-gamma transfer to each bracket input, executes
    exposure fusion, and optionally applies OpenCV simple tonemap on fused
    output before final normalization.
    @param bracket_images_float {Sequence[object]} Ordered RGB float bracket tensors.
    @param ev_value {float} EV bracket delta used to generate exposure files.
    @param ev_zero {float} Central EV used to generate exposure files.
    @param source_exposure_time_seconds {float|None} Positive EXIF `ExposureTime` in seconds for the extracted linear base image.
    @param opencv_merge_options {OpenCvMergeOptions} OpenCV merge backend controls.
    @param auto_adjust_dependencies {tuple[ModuleType, ModuleType]|None} Optional `(cv2, numpy)` dependency tuple.
    @param resolved_merge_gamma {ResolvedMergeGamma} Backend-final merge-output transfer payload.
    @return {object} Normalized RGB float merged image.
    @exception RuntimeError Raised when OpenCV/numpy dependencies are missing or bracket payloads are invalid.
    @satisfies REQ-107, REQ-108, REQ-109, REQ-110, REQ-142, REQ-143, REQ-144, REQ-152, REQ-153, REQ-154, REQ-160, REQ-161, REQ-162, REQ-170
    """

    if resolved_merge_gamma is None:
        resolved_merge_gamma = ResolvedMergeGamma(
            request=MergeGammaOption(mode="auto"),
            transfer="linear",
            label="Linear",
            param_a=None,
            param_b=None,
            evidence="default-linear",
        )

    if auto_adjust_dependencies is not None:
        cv2_module, np_module = auto_adjust_dependencies
    else:
        resolved_dependencies = _resolve_auto_adjust_dependencies()
        if resolved_dependencies is None:
            raise RuntimeError("Missing required dependencies: opencv-python and numpy")
        cv2_module, np_module = resolved_dependencies

    exposures_float = [
        image_rgb_float.astype(np_module.float32, copy=False)
        for image_rgb_float in bracket_images_float
    ]

    if opencv_merge_options.merge_algorithm == OPENCV_MERGE_ALGORITHM_MERTENS:
        exposures_mertens_gamma = [
            _apply_merge_gamma_float(
                np_module=np_module,
                image_rgb_float=exposure_float,
                resolved_merge_gamma=resolved_merge_gamma,
            )
            for exposure_float in exposures_float
        ]
        merged_rgb_float = _run_opencv_merge_mertens(
            cv2_module=cv2_module,
            np_module=np_module,
            exposures_float=exposures_mertens_gamma,
            tonemap_enabled=opencv_merge_options.tonemap_enabled,
            tonemap_gamma=opencv_merge_options.tonemap_gamma,
        )
        return merged_rgb_float
    exposure_times = _build_opencv_radiance_exposure_times(
        source_exposure_time_seconds=source_exposure_time_seconds,
        ev_zero=ev_zero,
        ev_delta=ev_value,
    )
    merged_rgb_float = _run_opencv_merge_radiance(
        cv2_module=cv2_module,
        np_module=np_module,
        exposures_linear_float=exposures_float,
        exposure_times=exposure_times,
        merge_algorithm=opencv_merge_options.merge_algorithm,
        tonemap_enabled=opencv_merge_options.tonemap_enabled,
        tonemap_gamma=opencv_merge_options.tonemap_gamma,
    )
    return _apply_merge_gamma_float(
        np_module=np_module,
        image_rgb_float=merged_rgb_float,
        resolved_merge_gamma=resolved_merge_gamma,
    )


def _hdrplus_box_down2_float32(np_module, frames_float32):
    """@brief Downsample HDR+ scalar frames with 2x2 box averaging in float domain.

    @details Ports `box_down2` from `util.cpp` for repository HDR+ execution by
    reflect-padding odd image sizes to even extents, summing each 2x2 region,
    and multiplying by `0.25` once. Input and output stay in float domain to
    preserve the repository-wide HDR+ internal arithmetic contract.
    @param np_module {ModuleType} Imported numpy module.
    @param frames_float32 {object} Scalar float tensor with shape `(N,H,W)`.
    @return {object} Downsampled float tensor with shape `(N,ceil(H/2),ceil(W/2))`.
    @satisfies REQ-112, REQ-113, REQ-129
    """

    pad_bottom = int(frames_float32.shape[1] % 2)
    pad_right = int(frames_float32.shape[2] % 2)
    padded_frames = np_module.pad(
        frames_float32,
        ((0, 0), (0, pad_bottom), (0, pad_right)),
        mode="reflect",
    )
    summed = (
        padded_frames[:, 0::2, 0::2]
        + padded_frames[:, 0::2, 1::2]
        + padded_frames[:, 1::2, 0::2]
        + padded_frames[:, 1::2, 1::2]
    )
    return (summed * 0.25).astype(np_module.float32)


def _hdrplus_gauss_down4_float32(np_module, frames_float32):
    """@brief Downsample HDR+ scalar frames by `4` with the source 5x5 Gaussian kernel.

    @details Ports `gauss_down4` from `util.cpp`: applies the integer kernel
    with coefficients summing to `159`, uses reflect padding to emulate
    `mirror_interior`, then samples every fourth pixel in both axes. Input and
    output remain float to keep HDR+ alignment math in floating point.
    @param np_module {ModuleType} Imported numpy module.
    @param frames_float32 {object} Scalar float tensor with shape `(N,H,W)`.
    @return {object} Downsampled float tensor with shape `(N,ceil(H/4),ceil(W/4))`.
    @satisfies REQ-112, REQ-113, REQ-129
    """

    from numpy.lib.stride_tricks import sliding_window_view  # type: ignore

    kernel = np_module.array(
        [
            [2.0, 4.0, 5.0, 4.0, 2.0],
            [4.0, 9.0, 12.0, 9.0, 4.0],
            [5.0, 12.0, 15.0, 12.0, 5.0],
            [4.0, 9.0, 12.0, 9.0, 4.0],
            [2.0, 4.0, 5.0, 4.0, 2.0],
        ],
        dtype=np_module.float32,
    ) / 159.0
    padded_frames = np_module.pad(
        frames_float32,
        ((0, 0), (2, 2), (2, 2)),
        mode="reflect",
    )
    windows = sliding_window_view(
        padded_frames,
        window_shape=(5, 5),
        axis=(1, 2),
    )
    filtered = np_module.tensordot(
        windows,
        kernel,
        axes=((-2, -1), (0, 1)),
    ).astype(np_module.float32)
    return filtered[
        :,
        ::HDRPLUS_ALIGNMENT_DOWNSAMPLE_RATE,
        ::HDRPLUS_ALIGNMENT_DOWNSAMPLE_RATE,
    ]


def _hdrplus_build_scalar_proxy_float32(np_module, frames_rgb_float32, hdrplus_options):
    """@brief Convert RGB bracket tensors into the scalar HDR+ source-domain proxy.

    @details Adapts normalized RGB float32 brackets to the original
    single-channel HDR+ merge domain without any uint16 staging. Mode `rggb`
    approximates Bayer energy with weights `(0.25, 0.5, 0.25)`; mode `bt709`
    uses luminance weights `(0.2126, 0.7152, 0.0722)`; mode `mean` uses
    arithmetic RGB average. Output remains normalized float32 to preserve
    downstream alignment and merge precision.
    @param np_module {ModuleType} Imported numpy module.
    @param frames_rgb_float32 {object} Normalized RGB float32 frame tensor with shape `(N,H,W,3)`.
    @param hdrplus_options {HdrPlusOptions} HDR+ proxy/alignment/temporal controls.
    @return {object} Normalized scalar float32 tensor with shape `(N,H,W)`.
    @satisfies REQ-112, REQ-126, REQ-128, REQ-129, REQ-140
    """

    rgb_float32 = np_module.array(frames_rgb_float32, dtype=np_module.float32, copy=False)
    if hdrplus_options.proxy_mode == "rggb":
        return (
            (0.25 * rgb_float32[..., 0])
            + (0.5 * rgb_float32[..., 1])
            + (0.25 * rgb_float32[..., 2])
        ).astype(np_module.float32)
    if hdrplus_options.proxy_mode == "bt709":
        return (
            (0.2126 * rgb_float32[..., 0])
            + (0.7152 * rgb_float32[..., 1])
            + (0.0722 * rgb_float32[..., 2])
        ).astype(np_module.float32)
    return np_module.mean(rgb_float32, axis=-1, dtype=np_module.float32).astype(
        np_module.float32
    )


def _hdrplus_compute_tile_start_positions(np_module, axis_length, tile_stride, pad_margin):
    """@brief Compute HDR+ tile start coordinates for one image axis.

    @details Reproduces the source overlap geometry used by the Python HDR+
    port: tile starts advance by `tile_stride` and include the leading virtual
    tile at `-tile_stride`, represented by positive indices inside the padded
    tensor.
    @param np_module {ModuleType} Imported numpy module.
    @param axis_length {int} Source image extent for the selected axis.
    @param tile_stride {int} Tile stride in pixels.
    @param pad_margin {int} Reflect padding added on both sides of the axis.
    @return {object} `int32` axis start-position vector with shape `(T,)`.
    @satisfies REQ-112, REQ-115
    """

    tile_count = int(math.ceil(axis_length / float(tile_stride)))
    return pad_margin - tile_stride + (
        np_module.arange(tile_count + 1, dtype=np_module.int32) * tile_stride
    )


def _hdrplus_trunc_divide_int32(np_module, values_int32, divisor):
    """@brief Divide signed HDR+ offsets with truncation toward zero.

    @details Emulates C++ integer division semantics used by the source code for
    negative offsets, which differs from Python floor division. This helper is
    required for the source-consistent `offset / 2` conversion between full and
    downsampled tile domains.
    @param np_module {ModuleType} Imported numpy module.
    @param values_int32 {object} Signed integer tensor.
    @param divisor {int} Positive divisor.
    @return {object} Signed integer tensor truncated toward zero.
    @satisfies REQ-113, REQ-114
    """

    return np_module.trunc(
        values_int32.astype(np_module.float32) / float(divisor)
    ).astype(np_module.int32)


def _hdrplus_compute_alignment_bounds(search_radius):
    """@brief Derive source-equivalent hierarchical HDR+ alignment bounds.

    @details Reconstructs the source `min_3/min_2/min_1` and
    `max_3/max_2/max_1` recurrences for the fixed three-level pyramid and
    search offsets `[-search_radius, search_radius-1]`.
    @param search_radius {int} Per-layer alignment search radius.
    @return {tuple[tuple[int, int], ...]} Bound pairs in coarse-to-fine order.
    @satisfies REQ-113
    """

    min_bounds = [0]
    max_bounds = [0]
    search_min = -search_radius
    search_max = search_radius - 1
    for _ in range(HDRPLUS_ALIGNMENT_LEVELS - 1):
        min_bounds.append(
            (HDRPLUS_ALIGNMENT_DOWNSAMPLE_RATE * min_bounds[-1]) + search_min
        )
        max_bounds.append(
            (HDRPLUS_ALIGNMENT_DOWNSAMPLE_RATE * max_bounds[-1]) + search_max
        )
    return tuple(zip(min_bounds, max_bounds))


def _hdrplus_compute_alignment_margin(search_radius, divisor=1):
    """@brief Compute safe reflect-padding margin for HDR+ alignment offsets.

    @details Converts the fixed three-level search radius into a conservative
    full-resolution offset bound and optionally scales it down for lower
    pyramid levels via truncation-toward-zero division.
    @param search_radius {int} Per-layer alignment search radius.
    @param divisor {int} Positive scale divisor applied to the full-resolution bound.
    @return {int} Non-negative padding margin in pixels.
    @satisfies REQ-113
    """

    full_margin = 2 * search_radius * sum(
        HDRPLUS_ALIGNMENT_DOWNSAMPLE_RATE**level
        for level in range(HDRPLUS_ALIGNMENT_LEVELS)
    )
    return int(math.ceil(full_margin / float(divisor)))


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


def _hdrplus_extract_aligned_tiles(
    np_module,
    frames_array,
    tile_size,
    tile_stride,
    pad_margin,
    alignment_offsets,
):
    """@brief Extract HDR+ tiles after applying per-tile alignment offsets.

    @details Builds tile coordinate grids from the padded frame tensor, adds the
    per-tile `(x,y)` offsets resolved by hierarchical alignment, and gathers the
    aligned scalar or RGB tiles needed by temporal distance evaluation and
    temporal accumulation.
    @param np_module {ModuleType} Imported numpy module.
    @param frames_array {object} Frame tensor with shape `(N,H,W)` or `(N,H,W,C)`.
    @param tile_size {int} Square tile edge length.
    @param tile_stride {int} Tile stride between adjacent overlapping tiles.
    @param pad_margin {int} Reflect padding added on each image edge.
    @param alignment_offsets {object} Signed integer offset tensor with shape `(N,Ty,Tx,2)`.
    @return {object} Aligned tile tensor with shape `(N,Ty,Tx,tile_size,tile_size[,C])`.
    @satisfies REQ-113, REQ-114
    """

    start_positions_y = _hdrplus_compute_tile_start_positions(
        np_module=np_module,
        axis_length=int(frames_array.shape[1]),
        tile_stride=tile_stride,
        pad_margin=pad_margin,
    )
    start_positions_x = _hdrplus_compute_tile_start_positions(
        np_module=np_module,
        axis_length=int(frames_array.shape[2]),
        tile_stride=tile_stride,
        pad_margin=pad_margin,
    )
    row_offsets = np_module.arange(tile_size, dtype=np_module.int32)
    col_offsets = np_module.arange(tile_size, dtype=np_module.int32)
    if frames_array.ndim == 3:
        padded_frames = np_module.pad(
            frames_array,
            ((0, 0), (pad_margin, pad_margin), (pad_margin, pad_margin)),
            mode="reflect",
        )
        frame_indices = np_module.arange(frames_array.shape[0], dtype=np_module.int32)[
            :, None, None, None, None
        ]
        row_indices = (
            start_positions_y[None, :, None, None, None]
            + alignment_offsets[..., 1][:, :, :, None, None]
            + row_offsets[None, None, None, :, None]
        )
        col_indices = (
            start_positions_x[None, None, :, None, None]
            + alignment_offsets[..., 0][:, :, :, None, None]
            + col_offsets[None, None, None, None, :]
        )
        return padded_frames[frame_indices, row_indices, col_indices]
    padded_frames = np_module.pad(
        frames_array,
        ((0, 0), (pad_margin, pad_margin), (pad_margin, pad_margin), (0, 0)),
        mode="reflect",
    )
    frame_indices = np_module.arange(frames_array.shape[0], dtype=np_module.int32)[
        :, None, None, None, None
    ]
    row_indices = (
        start_positions_y[None, :, None, None, None]
        + alignment_offsets[..., 1][:, :, :, None, None]
        + row_offsets[None, None, None, :, None]
    )
    col_indices = (
        start_positions_x[None, None, :, None, None]
        + alignment_offsets[..., 0][:, :, :, None, None]
        + col_offsets[None, None, None, None, :]
    )
    return padded_frames[frame_indices, row_indices, col_indices, :]


def _hdrplus_align_layer(
    np_module,
    reference_layer,
    alternate_layer,
    prev_alignment,
    prev_min,
    prev_max,
    search_radius,
):
    """@brief Resolve one HDR+ alignment layer for one alternate frame.

    @details Ports `align_layer` from `align.cpp`: propagates the coarser
    alignment estimate via `prev_tile`, scales it by the fixed downsample rate
    `4`, evaluates all candidate offsets in `[-search_radius, search_radius-1]`
    using per-tile L1 distance over `16x16` tiles, and returns the minimizing
    offset for each tile.
    @param np_module {ModuleType} Imported numpy module.
    @param reference_layer {object} Reference scalar layer with shape `(H,W)`.
    @param alternate_layer {object} Alternate scalar layer with shape `(H,W)`.
    @param prev_alignment {object} Previous-layer alignment tensor with shape `(Ty,Tx,2)`.
    @param prev_min {int} Minimum previous-layer offset bound used before upscaling.
    @param prev_max {int} Maximum previous-layer offset bound used before upscaling.
    @param search_radius {int} Per-layer alignment search radius.
    @return {object} Signed integer alignment tensor with shape `(Ty,Tx,2)`.
    @satisfies REQ-112, REQ-113, REQ-129
    """

    pad_margin = (
        HDRPLUS_DOWNSAMPLED_TILE_SIZE
        + _hdrplus_compute_alignment_margin(search_radius=search_radius, divisor=2)
    )
    reference_tiles = _hdrplus_extract_overlapping_tiles(
        np_module=np_module,
        frames_array=reference_layer[None, ...],
        tile_size=HDRPLUS_DOWNSAMPLED_TILE_SIZE,
        tile_stride=HDRPLUS_DOWNSAMPLED_TILE_SIZE // 2,
        pad_margin=pad_margin,
    )[0].astype(np_module.float32)
    tile_count_y = int(reference_tiles.shape[0])
    tile_count_x = int(reference_tiles.shape[1])
    prev_tile_y = _hdrplus_trunc_divide_int32(
        np_module=np_module,
        values_int32=np_module.arange(tile_count_y, dtype=np_module.int32) - 1,
        divisor=HDRPLUS_ALIGNMENT_DOWNSAMPLE_RATE,
    )
    prev_tile_x = _hdrplus_trunc_divide_int32(
        np_module=np_module,
        values_int32=np_module.arange(tile_count_x, dtype=np_module.int32) - 1,
        divisor=HDRPLUS_ALIGNMENT_DOWNSAMPLE_RATE,
    )
    prev_tile_y = np_module.clip(prev_tile_y, 0, prev_alignment.shape[0] - 1)
    prev_tile_x = np_module.clip(prev_tile_x, 0, prev_alignment.shape[1] - 1)
    base_offsets = (
        HDRPLUS_ALIGNMENT_DOWNSAMPLE_RATE
        * np_module.clip(
            prev_alignment[prev_tile_y[:, None], prev_tile_x[None, :]],
            prev_min,
            prev_max,
        ).astype(np_module.int32)
    )
    best_scores = None
    best_offsets = None
    for offset_y in range(-search_radius, search_radius):
        for offset_x in range(-search_radius, search_radius):
            candidate_offsets = base_offsets + np_module.array(
                [offset_x, offset_y],
                dtype=np_module.int32,
            )
            candidate_tiles = _hdrplus_extract_aligned_tiles(
                np_module=np_module,
                frames_array=alternate_layer[None, ...],
                tile_size=HDRPLUS_DOWNSAMPLED_TILE_SIZE,
                tile_stride=HDRPLUS_DOWNSAMPLED_TILE_SIZE // 2,
                pad_margin=pad_margin,
                alignment_offsets=candidate_offsets[None, ...],
            )[0].astype(np_module.float32)
            scores = np_module.sum(
                np_module.abs(candidate_tiles - reference_tiles),
                axis=(-2, -1),
                dtype=np_module.float64,
            )
            if best_scores is None:
                best_scores = scores
                best_offsets = candidate_offsets
                continue
            update_mask = scores < best_scores
            best_scores = np_module.where(update_mask, scores, best_scores)
            best_offsets = np_module.where(
                update_mask[..., None],
                candidate_offsets,
                best_offsets,
            )
    if best_offsets is None:
        raise RuntimeError("HDR+ alignment search failed to initialize any candidate offset")
    return best_offsets.astype(np_module.int32)


def _hdrplus_align_layers(np_module, scalar_frames, hdrplus_options):
    """@brief Resolve hierarchical HDR+ tile alignment for all alternate frames.

    @details Ports `align.cpp` at the algorithm level: builds the source
    alignment pyramid `box_down2 -> gauss_down4 -> gauss_down4`, computes
    coarse-to-fine tile alignments for each alternate frame against reference
    frame `n=0`, and lifts the finest layer offsets back to full-resolution
    coordinates by factor `2`.
    @param np_module {ModuleType} Imported numpy module.
    @param scalar_frames {object} Normalized scalar float32 tensor with shape `(N,H,W)`.
    @param hdrplus_options {HdrPlusOptions} HDR+ proxy/alignment/temporal controls.
    @return {object} Full-resolution `int32` alignment tensor with shape `(N,Ty,Tx,2)`.
    @satisfies REQ-112, REQ-113, REQ-128, REQ-129, REQ-139
    """

    layer_0 = _hdrplus_box_down2_float32(np_module=np_module, frames_float32=scalar_frames)
    layer_1 = _hdrplus_gauss_down4_float32(np_module=np_module, frames_float32=layer_0)
    layer_2 = _hdrplus_gauss_down4_float32(np_module=np_module, frames_float32=layer_1)
    bounds = _hdrplus_compute_alignment_bounds(hdrplus_options.search_radius)
    layer0_starts_y = _hdrplus_compute_tile_start_positions(
        np_module=np_module,
        axis_length=int(layer_0.shape[1]),
        tile_stride=HDRPLUS_DOWNSAMPLED_TILE_SIZE // 2,
        pad_margin=HDRPLUS_DOWNSAMPLED_TILE_SIZE,
    )
    layer0_starts_x = _hdrplus_compute_tile_start_positions(
        np_module=np_module,
        axis_length=int(layer_0.shape[2]),
        tile_stride=HDRPLUS_DOWNSAMPLED_TILE_SIZE // 2,
        pad_margin=HDRPLUS_DOWNSAMPLED_TILE_SIZE,
    )
    layer2_starts_y = _hdrplus_compute_tile_start_positions(
        np_module=np_module,
        axis_length=int(layer_2.shape[1]),
        tile_stride=HDRPLUS_DOWNSAMPLED_TILE_SIZE // 2,
        pad_margin=HDRPLUS_DOWNSAMPLED_TILE_SIZE,
    )
    layer2_starts_x = _hdrplus_compute_tile_start_positions(
        np_module=np_module,
        axis_length=int(layer_2.shape[2]),
        tile_stride=HDRPLUS_DOWNSAMPLED_TILE_SIZE // 2,
        pad_margin=HDRPLUS_DOWNSAMPLED_TILE_SIZE,
    )
    alignments = np_module.zeros(
        (
            scalar_frames.shape[0],
            len(layer0_starts_y),
            len(layer0_starts_x),
            2,
        ),
        dtype=np_module.int32,
    )
    zero_alignment = np_module.zeros(
        (len(layer2_starts_y), len(layer2_starts_x), 2),
        dtype=np_module.int32,
    )
    for frame_index in range(1, scalar_frames.shape[0]):
        alignment_2 = _hdrplus_align_layer(
            np_module=np_module,
            reference_layer=layer_2[0],
            alternate_layer=layer_2[frame_index],
            prev_alignment=zero_alignment,
            prev_min=bounds[0][0],
            prev_max=bounds[0][1],
            search_radius=hdrplus_options.search_radius,
        )
        alignment_1 = _hdrplus_align_layer(
            np_module=np_module,
            reference_layer=layer_1[0],
            alternate_layer=layer_1[frame_index],
            prev_alignment=alignment_2,
            prev_min=bounds[1][0],
            prev_max=bounds[1][1],
            search_radius=hdrplus_options.search_radius,
        )
        alignment_0 = _hdrplus_align_layer(
            np_module=np_module,
            reference_layer=layer_0[0],
            alternate_layer=layer_0[frame_index],
            prev_alignment=alignment_1,
            prev_min=bounds[2][0],
            prev_max=bounds[2][1],
            search_radius=hdrplus_options.search_radius,
        )
        alignments[frame_index] = (2 * alignment_0).astype(np_module.int32)
    return alignments


def _hdrplus_resolve_temporal_runtime_options(hdrplus_options):
    """@brief Remap HDR+ temporal CLI knobs for normalized float32 distance inputs.

    @details Converts user-facing temporal controls defined on the historical
    16-bit code-domain into runtime controls consumed by normalized float32
    `[0,1]` tile distances. The factor and floor are scaled by `1/65535`
    through pure linear rescaling; the cutoff remains expressed in the
    post-normalized comparison space so the current inverse-distance weight
    curve remains numerically equivalent while diagnostics still print the
    original CLI values.
    @param hdrplus_options {HdrPlusOptions} User-facing HDR+ proxy/alignment/temporal controls.
    @return {HdrPlusTemporalRuntimeOptions} Normalized runtime temporal controls.
    @satisfies REQ-114, REQ-131, REQ-138
    """

    code_domain_scale = 1.0 / 65535.0
    return HdrPlusTemporalRuntimeOptions(
        distance_factor=float(hdrplus_options.temporal_factor * code_domain_scale),
        min_distance=float(hdrplus_options.temporal_min_dist * code_domain_scale),
        max_weight_distance=float(
            hdrplus_options.temporal_max_dist - hdrplus_options.temporal_min_dist
        ),
    )


def _hdrplus_compute_temporal_weights(
    np_module,
    downsampled_scalar_frames,
    alignment_offsets,
    hdrplus_options,
):
    """@brief Compute HDR+ temporal tile weights against the aligned reference frame.

    @details Ports `merge_temporal` from `merge.cpp`: extracts reference tiles
    from the downsampled scalar layer, applies resolved per-tile alignment
    offsets to alternate frames in the same layer domain, computes average tile
    L1 distance on normalized float32 inputs, remaps user-facing temporal knobs
    into normalized runtime controls, derives inverse-distance weights without
    extra radiometric renormalization, and adds the implicit reference weight
    `1.0`.
    @param np_module {ModuleType} Imported numpy module.
    @param downsampled_scalar_frames {object} Downsampled normalized scalar float32 tensor with shape `(N,H,W)`.
    @param alignment_offsets {object} Full-resolution `int32` alignment tensor with shape `(N,Ty,Tx,2)`.
    @param hdrplus_options {HdrPlusOptions} HDR+ proxy/alignment/temporal controls.
    @return {tuple[object, object]} `(weights, total_weight)` where `weights` has shape `(N-1,Ty,Tx)` and `total_weight` has shape `(Ty,Tx)`.
    @satisfies REQ-112, REQ-114, REQ-128, REQ-129, REQ-138
    """

    temporal_runtime_options = _hdrplus_resolve_temporal_runtime_options(
        hdrplus_options=hdrplus_options
    )
    reference_tiles = _hdrplus_extract_overlapping_tiles(
        np_module=np_module,
        frames_array=downsampled_scalar_frames[0:1],
        tile_size=HDRPLUS_DOWNSAMPLED_TILE_SIZE,
        tile_stride=HDRPLUS_DOWNSAMPLED_TILE_SIZE // 2,
        pad_margin=HDRPLUS_DOWNSAMPLED_TILE_SIZE
        + _hdrplus_compute_alignment_margin(
            search_radius=hdrplus_options.search_radius,
            divisor=2,
        ),
    )[0].astype(np_module.float32)
    if downsampled_scalar_frames.shape[0] <= 1:
        total_weight = np_module.ones(reference_tiles.shape[:2], dtype=np_module.float32)
        return (
            np_module.zeros((0,) + reference_tiles.shape[:2], dtype=np_module.float32),
            total_weight,
        )
    layer_alignment_offsets = _hdrplus_trunc_divide_int32(
        np_module=np_module,
        values_int32=alignment_offsets[1:],
        divisor=2,
    )
    alternate_tiles = _hdrplus_extract_aligned_tiles(
        np_module=np_module,
        frames_array=downsampled_scalar_frames[1:],
        tile_size=HDRPLUS_DOWNSAMPLED_TILE_SIZE,
        tile_stride=HDRPLUS_DOWNSAMPLED_TILE_SIZE // 2,
        pad_margin=HDRPLUS_DOWNSAMPLED_TILE_SIZE
        + _hdrplus_compute_alignment_margin(
            search_radius=hdrplus_options.search_radius,
            divisor=2,
        ),
        alignment_offsets=layer_alignment_offsets,
    ).astype(np_module.float32)
    distances = np_module.sum(
        np_module.abs(alternate_tiles - reference_tiles[None, ...]),
        axis=(-2, -1),
        dtype=np_module.float64,
    ).astype(np_module.float32) / np_module.float32(
        HDRPLUS_DOWNSAMPLED_TILE_SIZE * HDRPLUS_DOWNSAMPLED_TILE_SIZE
    )
    norm_dist = np_module.maximum(
        np_module.float32(1.0),
        (distances - temporal_runtime_options.min_distance)
        / temporal_runtime_options.distance_factor,
    ).astype(np_module.float32)
    weights = np_module.where(
        norm_dist > temporal_runtime_options.max_weight_distance,
        np_module.float32(0.0),
        np_module.float32(1.0) / norm_dist,
    ).astype(
        np_module.float32
    )
    total_weight = (
        np_module.sum(weights, axis=0, dtype=np_module.float32) + np_module.float32(1.0)
    ).astype(np_module.float32)
    return (weights, total_weight)


def _hdrplus_merge_temporal_rgb(
    np_module,
    frames_rgb_float32,
    alignment_offsets,
    weights,
    total_weight,
    hdrplus_options,
):
    """@brief Merge HDR+ full-resolution RGB tiles across the temporal dimension.

    @details Ports the temporal accumulation phase of `merge.cpp`: extracts the
    reference `32x32` tile stack, applies resolved full-resolution alignment
    offsets to alternate RGB frames, normalizes all contributions with the
    shared per-tile `total_weight`, and preserves float arithmetic until the
    spatial merge stage.
    @param np_module {ModuleType} Imported numpy module.
    @param frames_rgb_float32 {object} Normalized RGB float32 tensor with shape `(N,H,W,3)`.
    @param alignment_offsets {object} Full-resolution `int32` alignment tensor with shape `(N,Ty,Tx,2)`.
    @param weights {object} Alternate-frame weight tensor with shape `(N-1,Ty,Tx)`.
    @param total_weight {object} Reference-inclusive tile total weights with shape `(Ty,Tx)`.
    @param hdrplus_options {HdrPlusOptions} HDR+ proxy/alignment/temporal controls.
    @return {object} Temporally merged normalized RGB float32 tile tensor with shape `(Ty,Tx,32,32,3)`.
    @satisfies REQ-112, REQ-114, REQ-129, REQ-140
    """

    pad_margin = HDRPLUS_TILE_SIZE + _hdrplus_compute_alignment_margin(
        search_radius=hdrplus_options.search_radius,
    )
    reference_tiles = _hdrplus_extract_overlapping_tiles(
        np_module=np_module,
        frames_array=frames_rgb_float32[0:1],
        tile_size=HDRPLUS_TILE_SIZE,
        tile_stride=HDRPLUS_TILE_STRIDE,
        pad_margin=pad_margin,
    )[0].astype(np_module.float32)
    total_weight_expanded = total_weight[..., None, None, None].astype(np_module.float32)
    merged_tiles = reference_tiles / total_weight_expanded
    if frames_rgb_float32.shape[0] <= 1:
        return merged_tiles.astype(np_module.float32)
    alternate_tiles = _hdrplus_extract_aligned_tiles(
        np_module=np_module,
        frames_array=frames_rgb_float32[1:],
        tile_size=HDRPLUS_TILE_SIZE,
        tile_stride=HDRPLUS_TILE_STRIDE,
        pad_margin=pad_margin,
        alignment_offsets=alignment_offsets[1:],
    ).astype(np_module.float32)
    merged_tiles += np_module.sum(
        alternate_tiles * weights[..., None, None, None],
        axis=0,
        dtype=np_module.float32,
    ) / total_weight_expanded
    return merged_tiles.astype(np_module.float32)


def _hdrplus_merge_spatial_rgb(np_module, temporal_tiles, width, height):
    """@brief Blend HDR+ temporally merged tiles with raised-cosine overlap.

    @details Ports `merge_spatial` from `merge.cpp`: builds source
    raised-cosine weights over `32` samples, gathers four overlapping tiles for
    each output pixel using source index formulas derived from `tile_0`,
    `tile_1`, `idx_0`, and `idx_1`, then computes one weighted RGB sum and
    returns the continuous normalized float32 result without stage-local
    `[0,1]` clipping or quantized lattice projection.
    @param np_module {ModuleType} Imported numpy module.
    @param temporal_tiles {object} Temporally merged normalized RGB float32 tile tensor with shape `(Ty,Tx,32,32,3)`.
    @param width {int} Output image width.
    @param height {int} Output image height.
    @return {object} Normalized RGB float32 merged image tensor with shape `(H,W,3)`.
    @satisfies REQ-112, REQ-115, REQ-129, REQ-140
    """

    positions = np_module.arange(HDRPLUS_TILE_SIZE, dtype=np_module.float32)
    weight_1d = (
        0.5
        - 0.5
        * np_module.cos(
            (2.0 * np_module.pi * (positions + np_module.float32(0.5)))
            / np_module.float32(HDRPLUS_TILE_SIZE)
        )
    ).astype(np_module.float32)
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
    ).astype(np_module.float32)
    return merged_image


def _run_hdr_plus_merge(
    bracket_images_float,
    np_module,
    hdrplus_options,
    resolved_merge_gamma=None,
):
    """@brief Merge bracket float images into one RGB float image via HDR+.

    @details Ports the source HDR+ merge pipeline from `align.cpp`, `merge.cpp`,
    and `util.cpp` onto repository RGB float brackets: reorders inputs into
    reference-first frame order `(ev_zero, ev_minus, ev_plus)`, normalizes each
    bracket to RGB float32 `[0,1]`, executes scalar proxy generation,
    hierarchical alignment, source `box_down2`, temporal weighting, temporal
    RGB merge, raised-cosine spatial blending, and returns one normalized RGB
    float32 image without any HDR+-local uint16 conversion.
    @param bracket_images_float {Sequence[object]} Ordered RGB float bracket tensors.
    @param np_module {ModuleType} Imported numpy module.
    @param hdrplus_options {HdrPlusOptions} HDR+ proxy/alignment/temporal controls.
    @param resolved_merge_gamma {ResolvedMergeGamma} Backend-final merge-output transfer payload.
    @return {object} Normalized RGB float32 merged image.
    @exception RuntimeError Raised when bracket payloads are invalid.
    @satisfies REQ-111, REQ-112, REQ-113, REQ-114, REQ-115, REQ-126, REQ-129, REQ-138, REQ-139, REQ-140, REQ-170
    """

    if resolved_merge_gamma is None:
        resolved_merge_gamma = ResolvedMergeGamma(
            request=MergeGammaOption(mode="auto"),
            transfer="linear",
            label="Linear",
            param_a=None,
            param_b=None,
            evidence="default-linear",
        )

    ordered_images = [
        bracket_images_float[1],
        bracket_images_float[0],
        bracket_images_float[2],
    ]
    frames_rgb_float32 = np_module.stack(
        [
            _normalize_float_rgb_image(
                np_module=np_module,
                image_data=frame_data,
            ).astype(np_module.float32, copy=False)
            for frame_data in ordered_images
        ],
        axis=0,
    ).astype(np_module.float32, copy=False)
    if frames_rgb_float32.shape[0] < 2:
        raise RuntimeError("HDR+ merge requires at least two aligned frames")
    scalar_frames = _hdrplus_build_scalar_proxy_float32(
        np_module=np_module,
        frames_rgb_float32=frames_rgb_float32,
        hdrplus_options=hdrplus_options,
    )
    alignment_offsets = _hdrplus_align_layers(
        np_module=np_module,
        scalar_frames=scalar_frames,
        hdrplus_options=hdrplus_options,
    )
    downsampled_scalar_frames = _hdrplus_box_down2_float32(
        np_module=np_module,
        frames_float32=scalar_frames,
    )
    weights, total_weight = _hdrplus_compute_temporal_weights(
        np_module=np_module,
        downsampled_scalar_frames=downsampled_scalar_frames,
        alignment_offsets=alignment_offsets,
        hdrplus_options=hdrplus_options,
    )
    temporal_tiles = _hdrplus_merge_temporal_rgb(
        np_module=np_module,
        frames_rgb_float32=frames_rgb_float32,
        alignment_offsets=alignment_offsets,
        weights=weights,
        total_weight=total_weight,
        hdrplus_options=hdrplus_options,
    )
    merged_rgb_float32 = _hdrplus_merge_spatial_rgb(
        np_module=np_module,
        temporal_tiles=temporal_tiles,
        width=int(frames_rgb_float32.shape[2]),
        height=int(frames_rgb_float32.shape[1]),
    )
    return _apply_merge_gamma_float(
        np_module=np_module,
        image_rgb_float=np_module.asarray(merged_rgb_float32, dtype=np_module.float32),
        resolved_merge_gamma=resolved_merge_gamma,
    )


def _convert_compression_to_quality(jpg_compression):
    """@brief Convert JPEG compression level to Pillow quality value.

    @details Maps inclusive compression range `[0, 100]` to inclusive quality
    range `[100, 1]` preserving deterministic inverse relation.
    @param jpg_compression {int} JPEG compression level.
    @return {int} Pillow quality value in `[1, 100]`.
    @satisfies REQ-065, REQ-066
    """

    return max(1, min(100, 100 - jpg_compression))
def _collect_missing_external_executables(
    *,
    enable_luminance,
):
    """@brief Collect missing external executables required by resolved runtime options.

    @details Evaluates the selected backend to derive the exact external
    executable set needed by this invocation, then probes each command on
    `PATH` and returns a deterministic missing-command tuple for preflight
    failure reporting before processing starts.
    @param enable_luminance {bool} `True` when luminance backend is selected.
    @return {tuple[str, ...]} Ordered tuple of missing executable labels.
    @satisfies CTN-005
    """

    missing_dependencies = []
    if enable_luminance and shutil.which("luminance-hdr-cli") is None:
        missing_dependencies.append("luminance-hdr-cli")
    return tuple(missing_dependencies)


def _resolve_auto_adjust_dependencies():
    """@brief Resolve OpenCV and numpy runtime dependencies for image-domain stages.

    @details Imports `cv2` and `numpy` modules required by the auto-adjust
    pipeline, the OpenCV HDR backend, white-balance stage execution, and the
    automatic EV-zero evaluation, and returns `None` with deterministic error
    output when dependencies are missing.
    @return {tuple[ModuleType, ModuleType]|None} `(cv2_module, numpy_module)` when available; `None` on dependency failure.
    @satisfies REQ-037, REQ-059, REQ-073, REQ-075, REQ-184, REQ-185, REQ-186
    """

    try:
        import cv2  # type: ignore
    except ModuleNotFoundError:
        print_error("Python dependency missing: opencv-python")
        print_error(
            "Install dependencies with: uv pip install opencv-contrib-python numpy"
        )
        return None
    try:
        import numpy as numpy_module  # type: ignore
    except ModuleNotFoundError:
        print_error("Python dependency missing: numpy")
        print_error(
            "Install dependencies with: uv pip install opencv-contrib-python numpy"
        )
        return None
    return (cv2, numpy_module)


def _resolve_numpy_dependency():
    """@brief Resolve numpy runtime dependency for float-interface image stages.

    @details Imports `numpy` required by bracket float normalization, in-memory
    merge orchestration, float-domain post-merge stages, and TIFF16 adaptation
    helpers, and returns `None` with deterministic error output when the
    dependency is missing.
    @return {ModuleType|None} Imported numpy module; `None` on dependency failure.
    @satisfies REQ-010, REQ-012, REQ-059, REQ-100
    """

    try:
        import numpy as numpy_module  # type: ignore
    except ModuleNotFoundError:
        print_error("Python dependency missing: numpy")
        print_error("Install dependencies with: uv pip install numpy")
        return None
    return numpy_module


def _to_float32_image_array(np_module, image_data):
    """@brief Convert image tensor to normalized `float32` range `[0,1]`.

    @details Normalizes integer or float image payloads into RGB-stage
    `float32` tensors. `uint16` uses `/65535`, `uint8` uses `/255`, floating
    inputs outside `[0,1]` are interpreted on the closest integer image scale
    (`255` or `65535`) and then clamped.
    @param np_module {ModuleType} Imported numpy module.
    @param image_data {object} Numeric image tensor.
    @return {object} Normalized `float32` image tensor.
    @satisfies REQ-010, REQ-012, REQ-106
    """

    dtype_name = str(getattr(image_data, "dtype", ""))
    if dtype_name == "float32":
        numeric_data = np_module.array(image_data, dtype=np_module.float32, copy=False)
    elif dtype_name == "uint16":
        numeric_data = image_data.astype(np_module.float32) / 65535.0
    elif dtype_name == "uint8":
        numeric_data = image_data.astype(np_module.float32) / 255.0
    else:
        numeric_data = np_module.array(image_data, dtype=np_module.float32)
        minimum_value = float(np_module.min(numeric_data)) if numeric_data.size else 0.0
        maximum_value = float(np_module.max(numeric_data)) if numeric_data.size else 0.0
        if minimum_value >= 0.0 and maximum_value > 1.0:
            if maximum_value <= 255.0:
                numeric_data = numeric_data / 255.0
            elif maximum_value <= 65535.0:
                numeric_data = numeric_data / 65535.0
    return np_module.clip(numeric_data, 0.0, 1.0).astype(np_module.float32)


def _normalize_float_rgb_image(np_module, image_data):
    """@brief Normalize image payload into RGB `float32` tensor.

    @details Converts input image payload to normalized `float32`, expands
    grayscale to one channel, replicates single-channel input to RGB, drops
    alpha from RGBA input, and returns exactly three channels for deterministic
    float-stage processing.
    @param np_module {ModuleType} Imported numpy module.
    @param image_data {object} Numeric image tensor.
    @return {object} RGB `float32` tensor with shape `(H,W,3)` and range `[0,1]`.
    @exception ValueError Raised when normalized image has unsupported shape.
    @satisfies REQ-010, REQ-012, REQ-106
    """

    normalized = _to_float32_image_array(np_module=np_module, image_data=image_data)
    if len(normalized.shape) == 2:
        normalized = normalized[:, :, None]
    if len(normalized.shape) == 3 and normalized.shape[2] == 1:
        normalized = np_module.repeat(normalized, 3, axis=2)
    if len(normalized.shape) == 3 and normalized.shape[2] == 4:
        normalized = normalized[:, :, :3]
    if len(normalized.shape) != 3 or normalized.shape[2] < 3:
        raise ValueError("Float stage input image has unsupported shape")
    if normalized.shape[2] > 3:
        normalized = normalized[:, :, :3]
    return normalized.astype(np_module.float32, copy=False)


def _write_rgb_float_tiff16(imageio_module, np_module, output_path, image_rgb_float):
    """@brief Serialize one RGB float tensor as 16-bit TIFF payload.

    @details Normalizes the source image to RGB float, clamps to `[0,1]`
    before quantization to ensure correct uint16 scaling when upstream pipeline
    stages emit unbounded float values, converts to `uint16`, and writes the
    result through `imageio`. This helper localizes float-to-TIFF16 adaptation
    inside steps that depend on file-based tools.
    @param imageio_module {ModuleType} Imported imageio module with `imwrite`.
    @param np_module {ModuleType} Imported numpy module.
    @param output_path {Path} Output TIFF path.
    @param image_rgb_float {object} RGB float tensor, potentially unbounded.
    @return {None} Side effects only.
    @satisfies REQ-106
    """

    normalized = _normalize_float_rgb_image(
        np_module=np_module,
        image_data=image_rgb_float,
    )
    normalized = np_module.clip(normalized, 0.0, 1.0)
    imageio_module.imwrite(
        str(output_path),
        _to_uint16_image_array(np_module=np_module, image_data=normalized),
    )


def _write_rgb_float_tiff32(imageio_module, np_module, output_path, image_rgb_float):
    """@brief Serialize one RGB float tensor as float32 TIFF payload.

    @details Normalizes the source image to RGB float32 `[0,1]` and writes
    it directly as a float32 TIFF through `imageio`, preserving full
    floating-point precision without quantization. Used by the luminance
    backend to provide float32 bracket inputs to `luminance-hdr-cli`.
    @param imageio_module {ModuleType} Imported imageio module with `imwrite`.
    @param np_module {ModuleType} Imported numpy module.
    @param output_path {Path} Output TIFF path.
    @param image_rgb_float {object} RGB float tensor in `[0,1]`.
    @return {None} Side effects only.
    @satisfies REQ-011, REQ-174
    """

    normalized = _normalize_float_rgb_image(
        np_module=np_module,
        image_data=image_rgb_float,
    )
    imageio_module.imwrite(
        str(output_path),
        normalized.astype(np_module.float32, copy=False),
    )


def _write_debug_rgb_float_tiff(
    imageio_module,
    np_module,
    debug_context,
    stage_suffix,
    image_rgb_float,
):
    """@brief Persist one debug checkpoint TIFF from normalized RGB float data.

    @details Serializes one normalized RGB float `[0,1]` tensor into TIFF16
    using the persistent debug output directory and canonical filename pattern
    `<input-stem><stage-suffix>.tiff`. The helper keeps checkpoint files outside
    the temporary workspace lifecycle so they survive command completion.
    @param imageio_module {ModuleType} Imported imageio module with `imwrite`.
    @param np_module {ModuleType} Imported numpy module.
    @param debug_context {DebugArtifactContext|None} Persistent debug output metadata; `None` disables emission.
    @param stage_suffix {str} Progressive stage suffix such as `_2.0_hdr-merge`.
    @param image_rgb_float {object} RGB float tensor on normalized `[0,1]` scale.
    @return {Path|None} Written TIFF path; `None` when debug output is disabled.
    @satisfies DES-009, REQ-147, REQ-149
    """

    if debug_context is None:
        return None
    debug_context.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = debug_context.output_dir / f"{debug_context.input_stem}{stage_suffix}.tiff"
    _write_rgb_float_tiff16(
        imageio_module=imageio_module,
        np_module=np_module,
        output_path=output_path,
        image_rgb_float=image_rgb_float,
    )
    return output_path


def _build_debug_artifact_context(output_jpg, input_dng, postprocess_options):
    """@brief Build persistent debug output metadata for one command invocation.

    @details Returns `None` when debug mode is disabled. When enabled, the
    helper derives the output directory from the final JPG destination and uses
    the source DNG stem as the canonical debug filename prefix.
    @param output_jpg {Path} Final JPG destination path.
    @param input_dng {Path} Source DNG input path.
    @param postprocess_options {PostprocessOptions} Parsed postprocess controls including debug flag.
    @return {DebugArtifactContext|None} Persistent debug output metadata or `None` when debug mode is disabled.
    @satisfies REQ-146, REQ-147, REQ-149
    """

    if not postprocess_options.debug_enabled:
        return None
    return DebugArtifactContext(
        output_dir=output_jpg.parent,
        input_stem=input_dng.stem,
    )


def _format_debug_ev_suffix_value(ev_value):
    """@brief Format one EV value token for debug checkpoint filenames.

    @details Emits a signed decimal representation that preserves quarter-step
    EV precision while keeping integer-valued stops on one decimal place for
    stable filenames such as `+1.0`, `+0.5`, or `-0.25`.
    @param ev_value {float} EV value expressed in stop units.
    @return {str} Signed decimal token for debug filename suffixes.
    @satisfies REQ-147, REQ-148
    """

    normalized_value = 0.0 if abs(float(ev_value)) < 1e-9 else float(ev_value)
    formatted = f"{normalized_value:+.2f}".rstrip("0")
    if formatted.endswith("."):
        formatted += "0"
    return formatted


def _materialize_bracket_tiffs_from_float(
    imageio_module,
    np_module,
    bracket_images_float,
    temp_dir,
):
    """@brief Write canonical bracket TIFF files from RGB float images.

    @details Emits `ev_minus.tif`, `ev_zero.tif`, and `ev_plus.tif` into the
    provided temporary directory using float32 TIFF encoding derived from
    normalized RGB float images. The helper is used only by file-oriented merge
    backends requiring float32 TIFF inputs.
    @param imageio_module {ModuleType} Imported imageio module with `imwrite`.
    @param np_module {ModuleType} Imported numpy module.
    @param bracket_images_float {Sequence[object]} Ordered RGB float bracket tensors.
    @param temp_dir {Path} Temporary directory for TIFF artifacts.
    @return {list[Path]} Ordered canonical TIFF paths.
    @satisfies REQ-011, REQ-034, REQ-174
    """

    labels = ("ev_minus", "ev_zero", "ev_plus")
    bracket_paths = []
    for label, image_rgb_float in zip(labels, bracket_images_float):
        output_path = temp_dir / f"{label}.tif"
        _write_rgb_float_tiff32(
            imageio_module=imageio_module,
            np_module=np_module,
            output_path=output_path,
            image_rgb_float=image_rgb_float,
        )
        bracket_paths.append(output_path)
    return bracket_paths


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


def _apply_post_gamma_float(np_module, image_rgb_float, gamma_value):
    """@brief Apply static post-gamma over RGB float tensor.

    @details Executes the legacy static gamma equation on RGB float
    data (`output = input^(1/gamma)`) without intermediate stage-local `[0,1]`
    clipping, preserving float headroom for downstream pipeline stages.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} RGB float image tensor.
    @param gamma_value {float} Static post-gamma factor.
    @return {object} RGB float tensor after gamma stage without stage-local clipping.
    @satisfies REQ-012, REQ-013, REQ-132, REQ-134
    """

    validated_input = _ensure_three_channel_float_array_no_range_adjust(
        np_module=np_module,
        image_data=image_rgb_float,
    )
    if gamma_value == 1.0:
        return validated_input
    adjusted = np_module.power(
        validated_input.astype(np_module.float64),
        1.0 / float(gamma_value),
    )
    return adjusted.astype(np_module.float32)


def _build_auto_post_gamma_lut_float(np_module, gamma_value, lut_size):
    """@brief Build one floating-point LUT for auto-gamma mapping.

    @details Generates one evenly sampled domain in `[0,1]` and evaluates
    `output = input^gamma` over that domain using float precision only.
    @param np_module {ModuleType} Imported numpy module.
    @param gamma_value {float} Resolved auto-gamma exponent.
    @param lut_size {int} LUT sample count (`>=2`).
    @return {tuple[object, object]} LUT domain and mapped values as float arrays.
    @satisfies REQ-178
    """

    lut_domain = np_module.linspace(0.0, 1.0, int(lut_size), dtype=np_module.float64)
    lut_values = np_module.power(lut_domain, float(gamma_value))
    return lut_domain, lut_values


def _ensure_three_channel_float_array_no_range_adjust(np_module, image_data):
    """@brief Normalize one image payload to three-channel float tensor without range clipping.

    @details Converts numeric image payloads into RGB `float64` while preserving
    original numeric range, expands grayscale and single-channel input to RGB,
    and drops alpha channels.
    @param np_module {ModuleType} Imported numpy module.
    @param image_data {object} Numeric image payload.
    @return {object} RGB `float64` tensor with shape `(H,W,3)`.
    @exception ValueError Raised when the input shape cannot be normalized to RGB.
    @satisfies REQ-178
    """

    numeric_data = np_module.asarray(image_data, dtype=np_module.float64)
    if len(numeric_data.shape) == 2:
        numeric_data = numeric_data[:, :, None]
    if len(numeric_data.shape) == 3 and numeric_data.shape[2] == 1:
        numeric_data = np_module.repeat(numeric_data, 3, axis=2)
    if len(numeric_data.shape) == 3 and numeric_data.shape[2] == 4:
        numeric_data = numeric_data[:, :, :3]
    if len(numeric_data.shape) != 3 or numeric_data.shape[2] < 3:
        raise ValueError("Float stage input image has unsupported shape")
    if numeric_data.shape[2] > 3:
        numeric_data = numeric_data[:, :, :3]
    return numeric_data


def _apply_auto_post_gamma_float(np_module, image_rgb_float, post_gamma_auto_options):
    """@brief Apply mean-luminance anchored auto-gamma over RGB float tensor.

    @details Computes grayscale mean luminance from normalized RGB float input,
    solves `gamma=log(target_gray)/log(mean_luminance)` when mean luminance is
    strictly within configured guards, otherwise returns input unchanged with
    resolved gamma `1.0`, then applies one floating-point LUT-domain mapping
    `output=input^gamma` without quantized intermediates or stage-local
    clipping.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} RGB float image tensor.
    @param post_gamma_auto_options {PostGammaAutoOptions} Auto-gamma replacement stage knobs.
    @return {tuple[object, float]} RGB float tensor and resolved gamma value.
    @satisfies REQ-177, REQ-178
    """

    validated_input = _ensure_three_channel_float_array_no_range_adjust(
        np_module=np_module,
        image_data=image_rgb_float,
    )
    luminance = (
        (0.2126 * validated_input[:, :, 0])
        + (0.7152 * validated_input[:, :, 1])
        + (0.0722 * validated_input[:, :, 2])
    )
    mean_luminance = float(np_module.mean(luminance)) if luminance.size else 0.0
    if (
        mean_luminance <= float(post_gamma_auto_options.luma_min)
        or mean_luminance >= float(post_gamma_auto_options.luma_max)
    ):
        return (validated_input.astype(np_module.float32), 1.0)
    resolved_gamma = math.log(float(post_gamma_auto_options.target_gray)) / math.log(
        mean_luminance
    )
    lut_domain, lut_values = _build_auto_post_gamma_lut_float(
        np_module=np_module,
        gamma_value=resolved_gamma,
        lut_size=post_gamma_auto_options.lut_size,
    )
    flattened_input = validated_input.astype(np_module.float64, copy=False).reshape(-1)
    mapped_flat = np_module.interp(flattened_input, lut_domain, lut_values)
    mapped = mapped_flat.reshape(validated_input.shape).astype(np_module.float32)
    return (mapped, float(resolved_gamma))


def _apply_brightness_float(np_module, image_rgb_float, brightness_factor):
    """@brief Apply static brightness factor on RGB float tensor.

    @details Executes the legacy brightness equation on RGB float
    data (`output = factor * input`) without intermediate stage-local `[0,1]`
    clipping, preserving float headroom for downstream pipeline stages.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} RGB float image tensor.
    @param brightness_factor {float} Brightness scale factor.
    @return {object} RGB float tensor after brightness stage without stage-local clipping.
    @satisfies REQ-012, REQ-013, REQ-132, REQ-134
    """

    validated_input = _ensure_three_channel_float_array_no_range_adjust(
        np_module=np_module,
        image_data=image_rgb_float,
    )
    if brightness_factor == 1.0:
        return validated_input
    adjusted = validated_input.astype(np_module.float64) * float(brightness_factor)
    return adjusted.astype(np_module.float32)


def _apply_contrast_float(np_module, image_rgb_float, contrast_factor):
    """@brief Apply static contrast factor on RGB float tensor.

    @details Executes the legacy contrast equation on RGB float data
    (`output = mean + factor * (input - mean)`), where `mean` remains the
    per-channel global image average, without stage-local clipping.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} RGB float image tensor.
    @param contrast_factor {float} Contrast interpolation factor.
    @return {object} RGB float tensor after contrast stage without stage-local clipping.
    @satisfies REQ-012, REQ-013, REQ-132, REQ-134
    """

    validated_input = _ensure_three_channel_float_array_no_range_adjust(
        np_module=np_module,
        image_data=image_rgb_float,
    )
    if contrast_factor == 1.0:
        return validated_input
    image_float = validated_input.astype(np_module.float64)
    channel_mean = np_module.mean(image_float, axis=(0, 1), keepdims=True)
    adjusted = channel_mean + float(contrast_factor) * (image_float - channel_mean)
    return adjusted.astype(np_module.float32)


def _apply_saturation_float(np_module, image_rgb_float, saturation_factor):
    """@brief Apply static saturation factor on RGB float tensor.

    @details Executes the legacy saturation equation on RGB float
    data using BT.709 grayscale (`output = gray + factor * (input - gray)`)
    without intermediate stage-local `[0,1]` clipping, preserving float
    headroom for downstream pipeline stages.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} RGB float image tensor.
    @param saturation_factor {float} Saturation interpolation factor.
    @return {object} RGB float tensor after saturation stage without stage-local clipping.
    @satisfies REQ-012, REQ-013, REQ-132, REQ-134
    """

    validated_input = _ensure_three_channel_float_array_no_range_adjust(
        np_module=np_module,
        image_data=image_rgb_float,
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
    return adjusted.astype(np_module.float32)


def _apply_static_postprocess_float(
    np_module,
    image_rgb_float,
    postprocess_options,
    imageio_module=None,
    debug_context=None,
):
    """@brief Execute static postprocess chain with float-only stage internals.

    @details Accepts one normalized RGB float tensor and executes static
    postprocess in strict order `gamma->brightness->contrast->saturation`,
    where gamma is either numeric static gamma or auto-gamma replacement when
    `--post-gamma=auto` is selected. Bypasses numeric static stage when all
    numeric factors are neutral (`1.0`), executes only non-neutral numeric
    substages in order, runs all intermediate calculations in float domain
    without stage-local `[0,1]` clipping on gamma/brightness/saturation
    stages, optionally emits persistent debug TIFF checkpoints after each
    executed static substage, and eliminates the prior float->uint16->float
    adaptation cycle from this step.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} RGB float tensor.
    @param postprocess_options {PostprocessOptions} Parsed postprocess controls.
    @param imageio_module {ModuleType|None} Optional imageio module used for debug TIFF checkpoint emission.
    @param debug_context {DebugArtifactContext|None} Optional persistent debug output metadata.
    @return {object} RGB float tensor after static postprocess chain.
    @satisfies REQ-012, REQ-013, REQ-132, REQ-134, REQ-148, REQ-176, REQ-177, REQ-178
    """

    processed = _ensure_three_channel_float_array_no_range_adjust(
        np_module=np_module,
        image_data=image_rgb_float,
    ).astype(np_module.float32, copy=False)
    gamma_value = float(postprocess_options.post_gamma)
    brightness_factor = float(postprocess_options.brightness)
    contrast_factor = float(postprocess_options.contrast)
    saturation_factor = float(postprocess_options.saturation)
    gamma_stage_executed = False
    if postprocess_options.post_gamma_mode == "auto":
        processed, _resolved_auto_gamma = _apply_auto_post_gamma_float(
            np_module=np_module,
            image_rgb_float=processed,
            post_gamma_auto_options=postprocess_options.post_gamma_auto_options,
        )
        gamma_stage_executed = True
        if imageio_module is not None and debug_context is not None:
            _write_debug_rgb_float_tiff(
                imageio_module=imageio_module,
                np_module=np_module,
                debug_context=debug_context,
                stage_suffix="_3.0_static_correction_auto_gamma",
                image_rgb_float=processed,
            )
    elif gamma_value != 1.0:
        processed = _apply_post_gamma_float(
            np_module=np_module,
            image_rgb_float=processed,
            gamma_value=gamma_value,
        )
        gamma_stage_executed = True
        if imageio_module is not None and debug_context is not None:
            _write_debug_rgb_float_tiff(
                imageio_module=imageio_module,
                np_module=np_module,
                debug_context=debug_context,
                stage_suffix="_3.1_static_correction_gamma",
                image_rgb_float=processed,
            )
    static_stage_enabled = gamma_stage_executed or any(
        factor != 1.0
        for factor in (
            brightness_factor,
            contrast_factor,
            saturation_factor,
        )
    )
    if not static_stage_enabled:
        return processed
    if brightness_factor != 1.0:
        processed = _apply_brightness_float(
            np_module=np_module,
            image_rgb_float=processed,
            brightness_factor=brightness_factor,
        )
        if imageio_module is not None and debug_context is not None:
            _write_debug_rgb_float_tiff(
                imageio_module=imageio_module,
                np_module=np_module,
                debug_context=debug_context,
                stage_suffix="_3.2_static_correction_brightness",
                image_rgb_float=processed,
            )
    if contrast_factor != 1.0:
        processed = _apply_contrast_float(
            np_module=np_module,
            image_rgb_float=processed,
            contrast_factor=contrast_factor,
        )
        if imageio_module is not None and debug_context is not None:
            _write_debug_rgb_float_tiff(
                imageio_module=imageio_module,
                np_module=np_module,
                debug_context=debug_context,
                stage_suffix="_3.3_static_correction_contrast",
                image_rgb_float=processed,
            )
    if saturation_factor != 1.0:
        processed = _apply_saturation_float(
            np_module=np_module,
            image_rgb_float=processed,
            saturation_factor=saturation_factor,
        )
        if imageio_module is not None and debug_context is not None:
            _write_debug_rgb_float_tiff(
                imageio_module=imageio_module,
                np_module=np_module,
                debug_context=debug_context,
                stage_suffix="_3.4_static_correction_saturation",
                image_rgb_float=processed,
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
    `low-key`, `normal-key`, or `high-key` using the thresholds from
    `/tmp/auto-brightness.py`.
    @param np_module {ModuleType} Imported numpy module.
    @param luminance {object} BT.709 luminance float tensor in `[0, 1]`.
    @param eps {float} Positive numerical stability guard.
    @return {dict[str, float|str]} Key analysis dictionary with key type, central statistics, tails, and clipping proxies.
    @satisfies REQ-050, REQ-103, REQ-121
    """

    luminance_clamped = np_module.clip(luminance, 0.0, 1.0)
    log_average = float(
        np_module.exp(np_module.mean(np_module.log(eps + luminance_clamped)))
    )
    median_luminance = float(np_module.median(luminance_clamped))
    p05 = float(np_module.percentile(luminance_clamped, 5.0))
    p95 = float(np_module.percentile(luminance_clamped, 95.0))
    shadow_clip = float(np_module.mean(luminance_clamped <= (1.0 / 255.0)))
    highlight_clip = float(np_module.mean(luminance_clamped >= (254.0 / 255.0)))
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
    conservative under/over-exposure adaptation bounded by configured automatic
    key limits and automatic boost factor.
    @param key_analysis {dict[str, float|str]} Luminance key-analysis dictionary.
    @param auto_brightness_options {AutoBrightnessOptions} Parsed auto-brightness parameters.
    @return {float} Clamped key value `a`.
    @satisfies REQ-050, REQ-103, REQ-122
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
            auto_brightness_options.a_max,
        )
    if over_hint:
        key_value = max(
            key_value / auto_brightness_options.max_auto_boost_factor,
            auto_brightness_options.a_min,
        )

    return float(
        min(
            max(key_value, auto_brightness_options.a_min),
            auto_brightness_options.a_max,
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
    """@brief Apply legacy uint16 CLAHE micro-contrast on 16-bit Y channel.

    @details Converts BGR16 to YCrCb, runs CLAHE on 16-bit Y with configured
    clip/tile controls, then blends original and CLAHE outputs using configured
    local-contrast strength. Retained as quantized reference implementation for
    float-domain CLAHE-luma equivalence verification.
    @param cv2_module {ModuleType} Imported cv2 module.
    @param np_module {ModuleType} Imported numpy module.
    @param image_bgr_uint16 {object} BGR uint16 image tensor.
    @param options {AutoAdjustOptions} Parsed auto-adjust CLAHE options.
    @return {object} BGR uint16 image tensor after optional local contrast.
    @satisfies REQ-125, REQ-137
    """

    if not options.enable_local_contrast:
        return image_bgr_uint16
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


def _quantize_clahe_luminance_bins(np_module, luminance_values, histogram_size):
    """@brief Map normalized luminance samples onto CLAHE histogram addresses.

    @details Computes OpenCV-compatible histogram bin addresses from normalized
    float luminance without materializing an intermediate uint16 image plane.
    Rounds against the `[0, hist_size-1]` lattice preserved by the historical
    uint16 reference so tile histograms remain semantically aligned while the
    active path stays in float-domain image buffers.
    @param np_module {ModuleType} Imported numpy module.
    @param luminance_values {object} Normalized luminance tensor in `[0,1]`.
    @param histogram_size {int} Number of CLAHE histogram bins.
    @return {object} `int32` tensor of histogram bin addresses.
    @satisfies REQ-136, REQ-137
    """

    max_bin = float(histogram_size - 1)
    scaled = np_module.clip(
        np_module.rint(
            np_module.asarray(luminance_values, dtype=np_module.float64) * max_bin
        ),
        0.0,
        max_bin,
    )
    return scaled.astype(np_module.int32)


def _build_clahe_float_tile_histogram(np_module, luminance_tile, histogram_size):
    """@brief Build one CLAHE histogram from a float luminance tile.

    @details Converts one normalized luminance tile into one dense histogram
    using the preserved 16-bit CLAHE lattice and returns per-bin population
    counts for downstream clipping and CDF generation.
    @param np_module {ModuleType} Imported numpy module.
    @param luminance_tile {object} Tile luminance tensor in `[0,1]`.
    @param histogram_size {int} Number of CLAHE histogram bins.
    @return {object} Dense histogram tensor with one count per CLAHE bin.
    @satisfies REQ-136, REQ-137
    """

    histogram_index = _quantize_clahe_luminance_bins(
        np_module=np_module,
        luminance_values=luminance_tile,
        histogram_size=histogram_size,
    )
    histogram = np_module.bincount(histogram_index.ravel(), minlength=histogram_size)
    return histogram.astype(np_module.int64, copy=False)


def _clip_clahe_histogram(np_module, histogram, clip_limit, tile_population):
    """@brief Clip one CLAHE histogram with OpenCV-compatible redistribution.

    @details Normalizes the user clip limit by tile population and histogram
    size, applies the same integer clip ceiling used by OpenCV CLAHE, then
    redistributes clipped mass through uniform batch fill plus residual stride
    increments. Output preserves the original total tile population.
    @param np_module {ModuleType} Imported numpy module.
    @param histogram {object} Dense tile histogram tensor.
    @param clip_limit {float} User-provided CLAHE clip limit.
    @param tile_population {int} Number of pixels contained in the tile.
    @return {object} Clipped histogram tensor after redistributed excess mass.
    @satisfies REQ-136, REQ-137
    """

    clipped_histogram = np_module.asarray(histogram, dtype=np_module.int64).copy()
    histogram_size = int(clipped_histogram.size)
    if clip_limit <= 0.0:
        return clipped_histogram
    effective_clip_limit = max(
        int(float(clip_limit) * float(tile_population) / float(histogram_size)),
        1,
    )
    over_limit = clipped_histogram > effective_clip_limit
    if not bool(np_module.any(over_limit)):
        return clipped_histogram
    clipped_mass = int(
        np_module.sum(clipped_histogram[over_limit] - effective_clip_limit)
    )
    clipped_histogram[over_limit] = effective_clip_limit
    if clipped_mass <= 0:
        return clipped_histogram
    redistribution_batch = clipped_mass // histogram_size
    residual = clipped_mass - (redistribution_batch * histogram_size)
    if redistribution_batch > 0:
        clipped_histogram += redistribution_batch
    if residual > 0:
        residual_step = max(histogram_size // residual, 1)
        residual_index = np_module.arange(
            0,
            histogram_size,
            residual_step,
            dtype=np_module.int64,
        )[:residual]
        clipped_histogram[residual_index] += 1
    return clipped_histogram


def _build_clahe_float_lut(np_module, histogram, tile_population):
    """@brief Convert one clipped CLAHE histogram into one normalized LUT.

    @details Builds one cumulative distribution from the clipped histogram and
    normalizes it by tile population so the resulting lookup table maps each
    histogram address directly into one float luminance output in `[0,1]`.
    Uses `float32` storage to limit per-tile memory while preserving normalized
    luminance precision required by the active float pipeline.
    @param np_module {ModuleType} Imported numpy module.
    @param histogram {object} Clipped histogram tensor.
    @param tile_population {int} Number of pixels contained in the tile.
    @return {object} Normalized CLAHE lookup-table tensor in `[0,1]`.
    @satisfies REQ-136, REQ-137
    """

    cdf = np_module.cumsum(np_module.asarray(histogram, dtype=np_module.float64))
    lut = np_module.clip(cdf / float(tile_population), 0.0, 1.0)
    return lut.astype(np_module.float32)


def _pad_clahe_luminance_float(np_module, luminance_float, tile_grid_size):
    """@brief Pad luminance plane to an even CLAHE tile lattice.

    @details Reproduces OpenCV CLAHE tiling rules by extending only the bottom
    and right borders to the next multiple of the configured tile grid. Uses
    reflect-101 semantics when the axis length is greater than one and edge
    replication for single-pixel axes where reflection is undefined.
    @param np_module {ModuleType} Imported numpy module.
    @param luminance_float {object} Luminance tensor in `[0,1]`.
    @param tile_grid_size {tuple[int, int]} OpenCV-compatible tile-grid tuple.
    @return {tuple[object, int, int]} Padded luminance tensor, tile height, and
    tile width.
    @satisfies REQ-136, REQ-137
    """

    tiles_x, tiles_y = tuple(int(value) for value in tile_grid_size)
    height, width = luminance_float.shape
    pad_bottom = (tiles_y - (height % tiles_y)) % tiles_y
    pad_right = (tiles_x - (width % tiles_x)) % tiles_x
    padded = np_module.asarray(luminance_float, dtype=np_module.float64)
    if pad_bottom > 0:
        row_pad_mode = "reflect" if padded.shape[0] > 1 else "edge"
        padded = np_module.pad(
            padded,
            ((0, pad_bottom), (0, 0)),
            mode=row_pad_mode,
        )
    if pad_right > 0:
        col_pad_mode = "reflect" if padded.shape[1] > 1 else "edge"
        padded = np_module.pad(
            padded,
            ((0, 0), (0, pad_right)),
            mode=col_pad_mode,
        )
    tile_height = padded.shape[0] // tiles_y
    tile_width = padded.shape[1] // tiles_x
    return padded, tile_height, tile_width


def _build_clahe_axis_interpolation(np_module, axis_length, tile_size, tile_count):
    """@brief Precompute CLAHE neighbor indices and bilinear weights per axis.

    @details Recreates OpenCV CLAHE interpolation coordinates by locating each
    sample relative to adjacent tile centers using `coord / tile_size - 0.5`.
    Returned weights remain unchanged after edge clamping so border pixels map
    to the closest tile exactly as the historical uint16 reference does.
    @param np_module {ModuleType} Imported numpy module.
    @param axis_length {int} Number of samples on the axis.
    @param tile_size {int} Size of each padded tile on the axis.
    @param tile_count {int} Number of tiles on the axis.
    @return {tuple[object, object, object, object]} Lower indices, upper
    indices, lower weights, and upper weights.
    @satisfies REQ-136, REQ-137
    """

    axis_position = (
        np_module.arange(axis_length, dtype=np_module.float64) / float(tile_size)
    ) - 0.5
    lower_index = np_module.floor(axis_position).astype(np_module.int32)
    upper_index = lower_index + 1
    upper_weight = axis_position - lower_index
    lower_weight = 1.0 - upper_weight
    lower_index = np_module.clip(lower_index, 0, tile_count - 1)
    upper_index = np_module.clip(upper_index, 0, tile_count - 1)
    return lower_index, upper_index, lower_weight, upper_weight


def _build_clahe_tile_luts_float(np_module, luminance_float, clip_limit, tile_grid_size, histogram_size):
    """@brief Build per-tile CLAHE lookup tables from float luminance input.

    @details Pads the luminance plane to the CLAHE lattice, then builds one
    histogram, clipped histogram, and normalized LUT per tile in call order.
    Stores LUTs in one dense `(tiles_y, tiles_x, hist_size)` tensor used by the
    bilinear tile interpolation stage.
    @param np_module {ModuleType} Imported numpy module.
    @param luminance_float {object} Luminance tensor in `[0,1]`.
    @param clip_limit {float} User-provided CLAHE clip limit.
    @param tile_grid_size {tuple[int, int]} OpenCV-compatible tile-grid tuple.
    @param histogram_size {int} Number of CLAHE histogram bins.
    @return {tuple[object, int, int]} LUT tensor, tile height, and tile width.
    @satisfies REQ-136, REQ-137
    """

    padded_luminance, tile_height, tile_width = _pad_clahe_luminance_float(
        np_module=np_module,
        luminance_float=luminance_float,
        tile_grid_size=tile_grid_size,
    )
    tiles_x, tiles_y = tuple(int(value) for value in tile_grid_size)
    tile_population = int(tile_height * tile_width)
    tile_luts = np_module.empty(
        (tiles_y, tiles_x, histogram_size),
        dtype=np_module.float32,
    )
    for tile_y in range(tiles_y):
        row_start = tile_y * tile_height
        row_end = row_start + tile_height
        for tile_x in range(tiles_x):
            col_start = tile_x * tile_width
            col_end = col_start + tile_width
            tile_histogram = _build_clahe_float_tile_histogram(
                np_module=np_module,
                luminance_tile=padded_luminance[row_start:row_end, col_start:col_end],
                histogram_size=histogram_size,
            )
            clipped_histogram = _clip_clahe_histogram(
                np_module=np_module,
                histogram=tile_histogram,
                clip_limit=clip_limit,
                tile_population=tile_population,
            )
            tile_luts[tile_y, tile_x] = _build_clahe_float_lut(
                np_module=np_module,
                histogram=clipped_histogram,
                tile_population=tile_population,
            )
    return tile_luts, tile_height, tile_width


def _interpolate_clahe_bilinear_float(np_module, luminance_float, tile_luts, tile_height, tile_width):
    """@brief Bilinearly interpolate CLAHE LUT outputs across adjacent tiles.

    @details Samples the four neighboring tile LUTs for each original-image row
    using OpenCV-compatible tile-center geometry and blends those per-pixel
    outputs with bilinear weights. Processes one row at a time to avoid one
    extra full-image histogram-address buffer.
    @param np_module {ModuleType} Imported numpy module.
    @param luminance_float {object} Original luminance tensor in `[0,1]`.
    @param tile_luts {object} Per-tile LUT tensor.
    @param tile_height {int} Padded tile height.
    @param tile_width {int} Padded tile width.
    @return {object} Equalized luminance tensor in `[0,1]`.
    @satisfies REQ-136, REQ-137
    """

    height, width = luminance_float.shape
    tiles_y, tiles_x, histogram_size = tile_luts.shape
    row_low, row_high, row_low_weight, row_high_weight = (
        _build_clahe_axis_interpolation(
            np_module=np_module,
            axis_length=height,
            tile_size=tile_height,
            tile_count=tiles_y,
        )
    )
    col_low, col_high, col_low_weight, col_high_weight = (
        _build_clahe_axis_interpolation(
            np_module=np_module,
            axis_length=width,
            tile_size=tile_width,
            tile_count=tiles_x,
        )
    )
    equalized_luminance = np_module.empty((height, width), dtype=np_module.float64)
    for row_index in range(height):
        lut_bins = _quantize_clahe_luminance_bins(
            np_module=np_module,
            luminance_values=luminance_float[row_index],
            histogram_size=histogram_size,
        )
        top_left = tile_luts[row_low[row_index], col_low, lut_bins]
        top_right = tile_luts[row_low[row_index], col_high, lut_bins]
        bottom_left = tile_luts[row_high[row_index], col_low, lut_bins]
        bottom_right = tile_luts[row_high[row_index], col_high, lut_bins]
        top_mix = (col_low_weight * top_left) + (col_high_weight * top_right)
        bottom_mix = (col_low_weight * bottom_left) + (col_high_weight * bottom_right)
        equalized_luminance[row_index] = (
            row_low_weight[row_index] * top_mix
        ) + (row_high_weight[row_index] * bottom_mix)
    return _clamp01(np_module, equalized_luminance)


def _apply_clahe_luminance_float(np_module, luminance_float, clip_limit, tile_grid_size):
    """@brief Execute native float-domain CLAHE on one luminance plane.

    @details Builds per-tile histograms and normalized LUTs with OpenCV-like
    clip-limit normalization, then reconstructs one equalized luminance plane
    via bilinear interpolation between adjacent tiles. Keeps the luminance plane
    in normalized float representation throughout the active path.
    @param np_module {ModuleType} Imported numpy module.
    @param luminance_float {object} Luminance tensor in `[0,1]`.
    @param clip_limit {float} User-provided CLAHE clip limit.
    @param tile_grid_size {tuple[int, int]} OpenCV-compatible tile-grid tuple.
    @return {object} Equalized luminance tensor in `[0,1]`.
    @satisfies REQ-136, REQ-137
    """

    histogram_size = 1 << 16
    tile_luts, tile_height, tile_width = _build_clahe_tile_luts_float(
        np_module=np_module,
        luminance_float=luminance_float,
        clip_limit=clip_limit,
        tile_grid_size=tile_grid_size,
        histogram_size=histogram_size,
    )
    return _interpolate_clahe_bilinear_float(
        np_module=np_module,
        luminance_float=luminance_float,
        tile_luts=tile_luts,
        tile_height=tile_height,
        tile_width=tile_width,
    )


def _reconstruct_rgb_from_ycrcb_luma_float(cv2_module, np_module, luminance_float, cr_channel, cb_channel):
    """@brief Reconstruct RGB float output from YCrCb float channels.

    @details Creates one float32 YCrCb tensor from one equalized luminance plane
    plus preserved Cr/Cb channels, converts it back to RGB with OpenCV color
    transforms only, and returns one clamped float64 RGB tensor for downstream
    blending in the auto-adjust pipeline.
    @param cv2_module {ModuleType} Imported cv2 module.
    @param np_module {ModuleType} Imported numpy module.
    @param luminance_float {object} Equalized luminance tensor in `[0,1]`.
    @param cr_channel {object} Preserved YCrCb Cr channel.
    @param cb_channel {object} Preserved YCrCb Cb channel.
    @return {object} Reconstructed RGB float tensor in `[0,1]`.
    @satisfies REQ-136, REQ-137
    """

    ycrcb_float = np_module.empty(luminance_float.shape + (3,), dtype=np_module.float32)
    ycrcb_float[..., 0] = np_module.asarray(luminance_float, dtype=np_module.float32)
    ycrcb_float[..., 1] = np_module.asarray(cr_channel, dtype=np_module.float32)
    ycrcb_float[..., 2] = np_module.asarray(cb_channel, dtype=np_module.float32)
    rgb_float = cv2_module.cvtColor(ycrcb_float, cv2_module.COLOR_YCrCb2RGB)
    return _clamp01(np_module, rgb_float.astype(np_module.float64))


def _apply_clahe_luma_rgb_float(cv2_module, np_module, image_rgb_float, auto_adjust_options):
    """@brief Apply CLAHE-luma local contrast directly on RGB float buffers.

    @details Converts normalized RGB float input to float YCrCb, runs one native
    NumPy CLAHE implementation on the luminance plane with OpenCV-compatible
    tiling, clip-limit normalization, clipping, redistribution, and bilinear
    tile interpolation, then reconstructs one RGB float CLAHE candidate from
    preserved chroma plus mapped luminance and blends that candidate with the
    original float RGB image using configured strength. OpenCV is used only for
    RGB<->YCrCb color conversion; the active CLAHE path performs no uint16
    image-plane round-trip.
    @param cv2_module {ModuleType} Imported cv2 module.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} RGB float tensor in `[0,1]`.
    @param auto_adjust_options {AutoAdjustOptions} Parsed auto-adjust CLAHE controls.
    @return {object} RGB float tensor after optional CLAHE-luma stage.
    @satisfies REQ-123, REQ-125, REQ-136, REQ-137
    """

    rgb_float = _clamp01(
        np_module,
        np_module.asarray(image_rgb_float, dtype=np_module.float64),
    )
    if not auto_adjust_options.enable_local_contrast:
        return rgb_float
    strength = float(min(max(auto_adjust_options.local_contrast_strength, 0.0), 1.0))
    if strength <= 0.0:
        return rgb_float

    ycrcb_float = cv2_module.cvtColor(
        rgb_float.astype(np_module.float32),
        cv2_module.COLOR_RGB2YCrCb,
    )
    equalized_luminance = _apply_clahe_luminance_float(
        np_module=np_module,
        luminance_float=np_module.asarray(ycrcb_float[..., 0], dtype=np_module.float64),
        clip_limit=float(auto_adjust_options.clahe_clip_limit),
        tile_grid_size=tuple(auto_adjust_options.clahe_tile_grid_size),
    )
    rgb_clahe = _reconstruct_rgb_from_ycrcb_luma_float(
        cv2_module=cv2_module,
        np_module=np_module,
        luminance_float=equalized_luminance,
        cr_channel=ycrcb_float[..., 1],
        cb_channel=ycrcb_float[..., 2],
    )
    blended = ((1.0 - strength) * rgb_float) + (strength * rgb_clahe)
    return _clamp01(np_module, blended)


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


def _auto_levels_index_to_normalized_value(histogram_value, histcompr):
    """@brief Convert one compressed histogram coordinate to normalized scale.

    @details Maps one RawTherapee histogram bin coordinate or derived statistic
    from the fixed `2^16` histogram family to normalized `[0,1]` intensity
    units using the exact lower-edge scaling of the original code domain. This
    helper centralizes pure scale conversion and keeps algorithmic thresholds in
    `_compute_auto_levels_from_histogram(...)` domain-independent.
    @param histogram_value {int|float} Histogram index or statistic expressed in compressed-bin units.
    @param histcompr {int} Histogram compression shift in `[0, 15]`.
    @return {float} Normalized value in `[0, +inf)`.
    @satisfies REQ-100, REQ-117, REQ-118
    """

    return float(histogram_value) * float(1 << histcompr) / _AUTO_LEVELS_CODE_MAX


def _auto_levels_normalized_to_legacy_code_value(value):
    """@brief Convert one normalized auto-levels scalar to legacy code scale.

    @details Multiplies one normalized scalar by the legacy `2^16-1` ceiling.
    Scope is restricted to compatibility mirrors returned by
    `_compute_auto_levels_from_histogram(...)` and to transitional adapter
    paths. Production auto-levels math must remain in normalized float units.
    @param value {int|float} Normalized scalar.
    @return {float} Legacy code-domain scalar.
    @note Scope: compatibility-only.
    @satisfies REQ-100, REQ-118
    """

    return float(value) * _AUTO_LEVELS_CODE_MAX


def _auto_levels_normalized_to_legacy_code(np_module, values):
    """@brief Convert normalized auto-levels tensors to legacy code scale.

    @details Multiplies normalized float tensors by the legacy `2^16-1`
    ceiling. This helper exists only for compatibility adapters that preserve
    deterministic legacy unit-test hooks while the production path remains
    float-native.
    @param np_module {ModuleType} Imported numpy module.
    @param values {object} Normalized scalar or tensor.
    @return {object} Float64 tensor on legacy code scale.
    @note Scope: compatibility-only.
    @satisfies REQ-100
    """

    return np_module.asarray(values, dtype=np_module.float64) * _AUTO_LEVELS_CODE_MAX


def _auto_levels_legacy_code_to_normalized(np_module, values):
    """@brief Convert legacy code-domain tensors to normalized float scale.

    @details Divides legacy `2^16-1`-scaled float tensors by the code ceiling.
    Scope is restricted to transitional compatibility adapters and legacy unit
    test hooks. Production auto-levels math must not depend on this helper.
    @param np_module {ModuleType} Imported numpy module.
    @param values {object} Legacy code-domain scalar or tensor.
    @return {object} Float64 tensor on normalized scale.
    @note Scope: compatibility-only.
    @satisfies REQ-100
    """

    return np_module.asarray(values, dtype=np_module.float64) / _AUTO_LEVELS_CODE_MAX


def _pack_auto_levels_metrics(
    *,
    expcomp,
    gain,
    black,
    brightness,
    contrast,
    hlcompr,
    hlcomprthresh,
    whiteclip,
    rawmax,
    shc,
    median,
    average,
    overex,
    ospread,
):
    """@brief Assemble normalized and compatibility auto-levels metrics.

    @details Stores the authoritative normalized-domain metrics under
    `*_normalized` keys while mirroring the historical code-domain values under
    legacy key names so existing callers and deterministic tests remain stable
    during the float-native migration. Algorithmic controls (`expcomp`,
    `brightness`, `contrast`, `hlcompr`, `ospread`) remain unscaled because
    they are not pure code-domain quantities.
    @param expcomp {float} Exposure compensation in EV.
    @param gain {float} Exposure gain factor.
    @param black {float} Normalized clipped black point.
    @param brightness {int} RawTherapee brightness control.
    @param contrast {int} RawTherapee contrast control.
    @param hlcompr {int} RawTherapee highlight-compression control.
    @param hlcomprthresh {int} RawTherapee highlight-compression threshold control.
    @param whiteclip {float} Normalized clipped white point.
    @param rawmax {float} Normalized maximum occupied histogram coordinate.
    @param shc {float} Normalized clipped shadow coordinate.
    @param median {float} Normalized histogram median.
    @param average {float} Normalized histogram average.
    @param overex {int} Overexposure classification flag from RawTherapee logic.
    @param ospread {float} Octile spread metric.
    @return {dict[str, int|float]} Metrics dictionary with normalized and compatibility fields.
    @satisfies REQ-100, REQ-117, REQ-118
    """

    return {
        "expcomp": float(expcomp),
        "gain": float(gain),
        "black_normalized": float(black),
        "brightness": int(brightness),
        "contrast": int(contrast),
        "hlcompr": int(hlcompr),
        "hlcomprthresh": int(hlcomprthresh),
        "whiteclip_normalized": float(whiteclip),
        "rawmax_normalized": float(rawmax),
        "shc_normalized": float(shc),
        "median_normalized": float(median),
        "average_normalized": float(average),
        "overex": int(overex),
        "ospread": float(ospread),
        "black": int(_auto_levels_normalized_to_legacy_code_value(black)),
        "whiteclip": int(_auto_levels_normalized_to_legacy_code_value(whiteclip)),
        "rawmax": int(_auto_levels_normalized_to_legacy_code_value(rawmax)),
        "shc": int(_auto_levels_normalized_to_legacy_code_value(shc)),
        "median": int(_auto_levels_normalized_to_legacy_code_value(median)),
        "average": float(_auto_levels_normalized_to_legacy_code_value(average)),
    }


def _build_autoexp_histogram_rgb_float(np_module, image_rgb_float, histcompr):
    """@brief Build RGB auto-levels histogram from normalized float image tensor.

    @details Builds one RawTherapee-compatible luminance histogram from the
    post-merge RGB float tensor directly in normalized units, applies the
    RawTherapee BT.709 luminance coefficients, maps luminance to the fixed
    `2^(16-histcompr)` histogram family without creating an intermediate
    `*65535` working tensor, and clips indices deterministically.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} RGB float tensor in `[0,1]`.
    @param histcompr {int} Histogram compression shift in `[0, 15]`.
    @return {object} Histogram tensor.
    @satisfies REQ-100, REQ-117
    """

    hist_size = _AUTO_LEVELS_CODE_BIN_COUNT >> histcompr
    bin_width = float(1 << histcompr) / _AUTO_LEVELS_CODE_MAX
    normalized = _normalize_float_rgb_image(
        np_module=np_module,
        image_data=image_rgb_float,
    ).astype(np_module.float64)
    luminance = (
        _AUTO_LEVELS_LUMINANCE_WEIGHTS[0] * normalized[..., 0]
        + _AUTO_LEVELS_LUMINANCE_WEIGHTS[1] * normalized[..., 1]
        + _AUTO_LEVELS_LUMINANCE_WEIGHTS[2] * normalized[..., 2]
    )
    histogram_index = np_module.clip(
        (luminance / bin_width).astype(np_module.int64),
        0,
        hist_size - 1,
    )
    return np_module.bincount(
        histogram_index.ravel(), minlength=hist_size
    ).astype(np_module.uint64)


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

    hist_size = _AUTO_LEVELS_CODE_BIN_COUNT >> histcompr
    scale = 1.0 / float(1 << histcompr)
    luminance = (
        _AUTO_LEVELS_LUMINANCE_WEIGHTS[0]
        * image_rgb_uint16[..., 0].astype(np_module.float64)
        + _AUTO_LEVELS_LUMINANCE_WEIGHTS[1]
        * image_rgb_uint16[..., 1].astype(np_module.float64)
        + _AUTO_LEVELS_LUMINANCE_WEIGHTS[2]
        * image_rgb_uint16[..., 2].astype(np_module.float64)
    )
    histogram_index = np_module.clip(
        (luminance * scale).astype(np_module.int64),
        0,
        hist_size - 1,
    )
    return np_module.bincount(
        histogram_index.ravel(), minlength=hist_size
    ).astype(np_module.uint64)


def _compute_auto_levels_from_histogram(np_module, histogram, histcompr, clip_percent):
    """@brief Compute auto-levels gain metrics from histogram.

    @details Ports `get_autoexp_from_histogram` from attached source as-is in
    numeric behavior for one luminance histogram: octile spread, white/black
    clip, exposure compensation, brightness/contrast, and highlight compression
    metrics. All scale-dependent intermediates are derived in normalized units.
    The returned dictionary exposes normalized-domain metrics under
    `*_normalized` keys and preserves legacy code-domain mirrors under the
    historical key names for deterministic compatibility.
    @param np_module {ModuleType} Imported numpy module.
    @param histogram {object} Flattened histogram tensor.
    @param histcompr {int} Histogram compression shift.
    @param clip_percent {float} Clip percentage.
    @return {dict[str, int|float]} Auto-levels metrics dictionary.
    @satisfies REQ-100, REQ-117, REQ-118
    """

    histogram_flat = np_module.asarray(histogram, dtype=np_module.float64).ravel()
    hist_size = _AUTO_LEVELS_CODE_BIN_COUNT >> histcompr
    if histogram_flat.size != hist_size:
        raise ValueError(
            f"histogram size must be {hist_size} for histcompr={histcompr}"
        )

    total = float(histogram_flat.sum())
    weighted = float(
        np_module.dot(
            histogram_flat,
            np_module.arange(hist_size, dtype=np_module.float64),
        )
    )
    average_index = weighted / total if total > 0 else 0.0
    if total <= 0.0:
        return _pack_auto_levels_metrics(
            expcomp=0.0,
            gain=1.0,
            black=0.0,
            brightness=0,
            contrast=0,
            hlcompr=0,
            hlcomprthresh=0,
            whiteclip=0.0,
            rawmax=0.0,
            shc=0.0,
            median=0.0,
            average=0.0,
            overex=0,
            ospread=0.0,
        )

    cdf = np_module.cumsum(histogram_flat)
    median_index = int(np_module.searchsorted(cdf, total / 2.0, side="left"))
    if median_index == 0 or average_index < 1.0:
        return _pack_auto_levels_metrics(
            expcomp=0.0,
            gain=1.0,
            black=0.0,
            brightness=0,
            contrast=0,
            hlcompr=0,
            hlcomprthresh=0,
            whiteclip=0.0,
            rawmax=0.0,
            shc=0.0,
            median=_auto_levels_index_to_normalized_value(median_index, histcompr),
            average=_auto_levels_index_to_normalized_value(average_index, histcompr),
            overex=0,
            ospread=0.0,
        )

    octile = np_module.zeros(8, dtype=np_module.float64)
    ospread = 0.0
    low_sum = 0.0
    high_sum = 0.0
    octile_count = 0
    histogram_index = 0
    average_loop_limit = min(int(average_index), hist_size)
    while histogram_index < average_loop_limit:
        if octile_count < 8:
            octile[octile_count] += histogram_flat[histogram_index]
            if octile[octile_count] > total / 8.0 or (
                octile_count == 7 and octile[octile_count] > total / 16.0
            ):
                octile[octile_count] = math.log1p(histogram_index) / math.log(2.0)
                octile_count += 1
        low_sum += histogram_flat[histogram_index]
        histogram_index += 1
    while histogram_index < hist_size:
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
        return _pack_auto_levels_metrics(
            expcomp=0.0,
            gain=1.0,
            black=0.0,
            brightness=0,
            contrast=0,
            hlcompr=0,
            hlcomprthresh=0,
            whiteclip=0.0,
            rawmax=0.0,
            shc=0.0,
            median=_auto_levels_index_to_normalized_value(median_index, histcompr),
            average=_auto_levels_index_to_normalized_value(average_index, histcompr),
            overex=0,
            ospread=0.0,
        )

    overex = 0
    guard = math.log1p(float(hist_size))
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
        return _pack_auto_levels_metrics(
            expcomp=0.0,
            gain=1.0,
            black=0.0,
            brightness=0,
            contrast=0,
            hlcompr=0,
            hlcomprthresh=0,
            whiteclip=0.0,
            rawmax=0.0,
            shc=0.0,
            median=_auto_levels_index_to_normalized_value(median_index, histcompr),
            average=_auto_levels_index_to_normalized_value(average_index, histcompr),
            overex=overex,
            ospread=ospread,
        )

    clipped = 0.0
    rawmax_index = hist_size - 1
    while rawmax_index > 1 and histogram_flat[rawmax_index] + clipped <= 0.0:
        clipped += histogram_flat[rawmax_index]
        rawmax_index -= 1

    clippable = int(total * clip_percent / 100.0)
    clipped = 0.0
    whiteclip_index = hist_size - 1
    while (
        whiteclip_index > 1
        and histogram_flat[whiteclip_index] + clipped <= clippable
    ):
        clipped += histogram_flat[whiteclip_index]
        whiteclip_index -= 1

    clipped = 0.0
    shc_index = 0
    while (
        shc_index < whiteclip_index - 1
        and histogram_flat[shc_index] + clipped <= clippable
    ):
        clipped += histogram_flat[shc_index]
        shc_index += 1

    rawmax = _auto_levels_index_to_normalized_value(rawmax_index, histcompr)
    whiteclip = _auto_levels_index_to_normalized_value(whiteclip_index, histcompr)
    average = _auto_levels_index_to_normalized_value(average_index, histcompr)
    median = _auto_levels_index_to_normalized_value(median_index, histcompr)
    shc = _auto_levels_index_to_normalized_value(shc_index, histcompr)

    expcomp1 = math.log(
        _AUTO_LEVELS_RT_MIDGRAY
        / max(average - shc + _AUTO_LEVELS_RT_MIDGRAY * shc, 1e-12)
    ) / math.log(2.0)
    hist_log_span = math.log(float(hist_size), 2.0) - 0.5
    if overex == 0:
        expcomp2 = 0.5 * (
            (hist_log_span - (2.0 * octile_7 - octile_6))
            - math.log(max(rawmax, 1e-12), 2.0)
        )
    else:
        expcomp2 = 0.5 * (
            (hist_log_span - (2.0 * octile[7] - octile[6]))
            - math.log(max(rawmax, 1e-12), 2.0)
        )
    if abs(expcomp1) - abs(expcomp2) > 1.0:
        denominator = abs(expcomp1) + abs(expcomp2)
        expcomp = (
            expcomp1 * abs(expcomp2) + expcomp2 * abs(expcomp1)
        ) / max(denominator, 1e-12)
    else:
        expcomp = 0.5 * expcomp1 + 0.5 * expcomp2

    gain = math.exp(expcomp * math.log(2.0))
    corr = math.sqrt(gain / max(rawmax, 1e-12))
    black = shc * corr
    hlcomprthresh = 0
    comp = (gain * whiteclip - 1.0) * 2.3
    hlcompr = int(100.0 * comp / (max(0.0, expcomp) + 1.0))
    hlcompr = max(0, min(100, hlcompr))

    midtmp = gain * math.sqrt(median * average)
    if midtmp < 0.1:
        brightness = int(
            (_AUTO_LEVELS_RT_MIDGRAY - midtmp) * 15.0 / max(midtmp, 1e-12)
        )
    else:
        brightness = int(
            (_AUTO_LEVELS_RT_MIDGRAY - midtmp)
            / max(0.10833 - 0.0833 * midtmp, 1e-12)
            * 15.0
        )
    brightness = int(0.25 * max(0, brightness))

    contrast = int(50.0 * (1.1 - ospread))
    contrast = max(0, min(100, contrast))
    whiteclip_gamma = (
        math.floor(float(_rt_gamma2(np_module, whiteclip * corr)) * _AUTO_LEVELS_CODE_MAX)
        / _AUTO_LEVELS_CODE_MAX
    )

    gavg = 0.0
    value = 0.0
    increment = corr * (float(1 << histcompr) / _AUTO_LEVELS_CODE_MAX)
    for histogram_index in range(hist_size):
        gavg += histogram_flat[histogram_index] * float(
            _rt_gamma2(np_module, value)
        )
        value += increment
    gavg /= total
    if black < gavg:
        max_whiteclip = (gavg - black) * 4.0 / 3.0 + black
        if whiteclip_gamma < max_whiteclip:
            whiteclip_gamma = max_whiteclip

    whiteclip_gamma = float(_rt_igamma2(np_module, whiteclip_gamma))
    black = black / whiteclip_gamma if whiteclip_gamma > 0 else 0.0
    expcomp = max(-5.0, min(12.0, float(expcomp)))
    brightness = max(-100, min(100, int(brightness)))
    return _pack_auto_levels_metrics(
        expcomp=float(expcomp),
        gain=float(gain),
        black=black,
        brightness=int(brightness),
        contrast=int(contrast),
        hlcompr=int(hlcompr),
        hlcomprthresh=int(hlcomprthresh),
        whiteclip=whiteclip,
        rawmax=rawmax,
        shc=shc,
        median=median,
        average=average,
        overex=int(overex),
        ospread=float(ospread),
    )


def _rt_simplebasecurve_scalar(x_value, black, shadow_recovery):
    """@brief Evaluate RawTherapee `simplebasecurve` for one normalized sample.

    @details Ports the `CurveFactory::simplebasecurve(...)` path used by
    RawTherapee to derive the shadow tone factor curve. Input and output stay in
    normalized float space; no uint16 buffer staging is introduced.
    @param x_value {float} Normalized sample coordinate.
    @param black {float} Normalized clipped black point.
    @param shadow_recovery {float} Shadow recovery strength.
    @return {float} Normalized curve output for the sample.
    @satisfies REQ-100, REQ-119
    """

    def _basel(x_input, slope_start, slope_end):
        if x_input == 0.0:
            return 0.0
        numerator = math.sqrt(
            (slope_start - 1.0) * (slope_start - slope_end) * 0.5
        )
        denominator = 1.0 - slope_end
        k_value = numerator / denominator
        l_value = ((slope_start - slope_end) / denominator) + k_value
        log_x = math.log(x_input)
        return (
            slope_end * x_input
            + (1.0 - slope_end)
            * (2.0 - math.exp(k_value * log_x))
            * math.exp(l_value * log_x)
        )

    def _baseu(x_input, slope_start, slope_end):
        return 1.0 - _basel(1.0 - x_input, slope_start, slope_end)

    def _cupper(x_input, slope_value, highlight_recovery):
        if highlight_recovery > 1.0:
            return _baseu(
                x_input,
                slope_value,
                2.0 * (highlight_recovery - 1.0) / slope_value,
            )
        x1_value = (1.0 - highlight_recovery) / slope_value
        x2_value = x1_value + highlight_recovery
        if x_input >= x2_value:
            return 1.0
        if x_input < x1_value:
            return x_input * slope_value
        return (
            1.0
            - highlight_recovery
            + highlight_recovery
            * _baseu((x_input - x1_value) / highlight_recovery, slope_value, 0.0)
        )

    def _clower(x_input, slope_value, shadow_value):
        return 1.0 - _cupper(1.0 - x_input, slope_value, shadow_value)

    def _clower2(x_input, slope_value, shadow_value):
        x1_value = shadow_value / 1.5 + 0.00001
        if x_input > x1_value or shadow_value < 0.001:
            return 1.0 - (1.0 - x_input) * slope_value
        y1_value = 1.0 - (1.0 - x1_value) * slope_value
        x_ratio = 1.0 - x_input / x1_value
        return (
            y1_value
            + slope_value * (x_input - x1_value)
            - (1.0 - slope_value) * (x_ratio * x_ratio) * (x_ratio * x_ratio)
        )

    if black == 0.0:
        return x_value
    if black < 0.0:
        midpoint = 0.5
        slope_value = 1.0 + black
        midpoint_value = -black + midpoint * slope_value
        if x_value > midpoint:
            return midpoint_value + (x_value - midpoint) * slope_value
        return midpoint_value * _clower2(
            x_value / midpoint,
            slope_value * midpoint / midpoint_value,
            2.0 - shadow_recovery,
        )
    slope_value = 1.0 / (1.0 - black)
    midpoint = black + (1.0 - black) * 0.25
    midpoint_value = (midpoint - black) * slope_value
    if x_value <= midpoint:
        return _clower(
            x_value / midpoint,
            slope_value * midpoint / midpoint_value,
            shadow_recovery,
        ) * midpoint_value
    return midpoint_value + (x_value - midpoint) * slope_value


def _build_rt_nurbs_curve_lut(np_module, x_points, y_points, sample_count):
    """@brief Build one RawTherapee-style NURBS diagonal-curve LUT.

    @details Ports the `DiagonalCurve` NURBS polygonization path used by
    RawTherapee for the brightness and contrast curves inside
    `CurveFactory::complexCurve(...)`, then resamples the resulting polyline on
    one dense normalized LUT.
    @param np_module {ModuleType} Imported numpy module.
    @param x_points {tuple[float, ...]|list[float]} Ordered control-point x coordinates.
    @param y_points {tuple[float, ...]|list[float]} Ordered control-point y coordinates.
    @param sample_count {int} Output LUT length.
    @return {object} Dense normalized float64 LUT.
    @exception ValueError Raised when control-point arrays are invalid.
    @satisfies REQ-100, REQ-119
    """

    if len(x_points) != len(y_points):
        raise ValueError("NURBS x/y control point counts must match")
    if len(x_points) < 2:
        raise ValueError("NURBS curve requires at least two control points")

    if len(x_points) == 2:
        samples = np_module.linspace(0.0, 1.0, sample_count, dtype=np_module.float64)
        return np_module.interp(
            samples,
            np_module.asarray(x_points, dtype=np_module.float64),
            np_module.asarray(y_points, dtype=np_module.float64),
        ).astype(np_module.float64)

    ppn = min(_AUTO_LEVELS_RT_CURVE_MIN_POLY_POINTS, 65500)
    point_count = len(x_points)
    subcurve_x = []
    subcurve_y = []
    subcurve_lengths = []
    total_length = 0.0
    point_index = 0

    while point_index < point_count - 1:
        if point_index == 0:
            first_x = float(x_points[point_index])
            first_y = float(y_points[point_index])
            point_index += 1
        else:
            first_x = 0.5 * float(x_points[point_index - 1] + x_points[point_index])
            first_y = 0.5 * float(y_points[point_index - 1] + y_points[point_index])
        subcurve_x.append(first_x)
        subcurve_y.append(first_y)

        control_x = float(x_points[point_index])
        control_y = float(y_points[point_index])
        point_index += 1
        subcurve_x.append(control_x)
        subcurve_y.append(control_y)

        if point_index == point_count - 1:
            third_x = float(x_points[point_index])
            third_y = float(y_points[point_index])
        else:
            third_x = 0.5 * float(x_points[point_index - 1] + x_points[point_index])
            third_y = 0.5 * float(y_points[point_index - 1] + y_points[point_index])
        subcurve_x.append(third_x)
        subcurve_y.append(third_y)

        first_leg = math.hypot(control_x - first_x, control_y - first_y)
        second_leg = math.hypot(third_x - control_x, third_y - control_y)
        curve_length = first_leg + second_leg
        subcurve_lengths.append(curve_length)
        total_length += curve_length

    if total_length <= 0.0:
        samples = np_module.linspace(0.0, 1.0, sample_count, dtype=np_module.float64)
        return np_module.interp(
            samples,
            np_module.asarray(x_points, dtype=np_module.float64),
            np_module.asarray(y_points, dtype=np_module.float64),
        ).astype(np_module.float64)

    poly_x = []
    poly_y = []
    if float(x_points[0]) > 0.0:
        poly_x.append(0.0)
        poly_y.append(float(y_points[0]))

    subcurve_count = len(subcurve_lengths)
    for subcurve_index in range(subcurve_count):
        offset = subcurve_index * 3
        x1_value = subcurve_x[offset]
        y1_value = subcurve_y[offset]
        x2_value = subcurve_x[offset + 1]
        y2_value = subcurve_y[offset + 1]
        x3_value = subcurve_x[offset + 2]
        y3_value = subcurve_y[offset + 2]
        nbr_points = int(
            ((ppn + point_count - 2) * subcurve_lengths[subcurve_index])
            / total_length
        )
        nbr_points = max(2, nbr_points)
        increment = 1.0 / float(nbr_points - 1)
        if subcurve_index == 0:
            poly_x.append(x1_value)
            poly_y.append(y1_value)
        for point_offset in range(1, nbr_points - 1):
            t_value = point_offset * increment
            t_squared = t_value * t_value
            t_reverse = 1.0 - t_value
            reverse_squared = t_reverse * t_reverse
            reverse_double_t = t_reverse * 2.0 * t_value
            poly_x.append(
                reverse_squared * x1_value
                + reverse_double_t * x2_value
                + t_squared * x3_value
            )
            poly_y.append(
                reverse_squared * y1_value
                + reverse_double_t * y2_value
                + t_squared * y3_value
            )
        poly_x.append(x3_value)
        poly_y.append(y3_value)

    poly_x.append(3.0)
    poly_y.append(float(y_points[-1]))
    samples = np_module.linspace(0.0, 1.0, sample_count, dtype=np_module.float64)
    return np_module.clip(
        np_module.interp(
            samples,
            np_module.asarray(poly_x, dtype=np_module.float64),
            np_module.asarray(poly_y, dtype=np_module.float64),
        ),
        0.0,
        1.0,
    ).astype(np_module.float64)


def _sample_auto_levels_lut_float(
    np_module,
    lut_values,
    indices,
    *,
    clip_below=True,
    clip_above=True,
):
    """@brief Sample one dense float LUT with RawTherapee-style interpolation.

    @details Replicates `LUT<float>::operator[](float)` semantics for scalar or
    tensor indices, including optional clipping or edge extrapolation, while
    keeping the surrounding pipeline in normalized float arrays.
    @param np_module {ModuleType} Imported numpy module.
    @param lut_values {object} One-dimensional float LUT.
    @param indices {object} Scalar or tensor of float lookup coordinates.
    @param clip_below {bool} `True` to clip values below the lower bound.
    @param clip_above {bool} `True` to clip values above the upper bound.
    @return {object} LUT-sampled float tensor.
    @satisfies REQ-100, REQ-119
    """

    lut = np_module.asarray(lut_values, dtype=np_module.float64)
    lookup = np_module.asarray(indices, dtype=np_module.float64)
    max_index = float(lut.size - 1)
    effective_lookup = lookup
    if clip_below:
        effective_lookup = np_module.maximum(effective_lookup, 0.0)
    if clip_above:
        effective_lookup = np_module.minimum(effective_lookup, max_index)
    base_index = effective_lookup.astype(np_module.int64)
    base_index = np_module.clip(base_index, 0, lut.size - 2)
    fraction = effective_lookup - base_index.astype(np_module.float64)
    lower = lut[base_index]
    upper = lut[base_index + 1]
    return lower + (upper - lower) * fraction


def _build_auto_levels_full_histogram_rgb_float(np_module, image_rgb_float):
    """@brief Build the full 16-bit luminance histogram for auto-levels curves.

    @details Builds the uncompressed `0..65535` luminance histogram required by
    the RawTherapee `complexCurve(...)` contrast-centering step while preserving
    float-only image buffers.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} Normalized RGB float tensor.
    @return {object} Full-resolution uint64 histogram.
    @satisfies REQ-100, REQ-119
    """

    normalized = _normalize_float_rgb_image(
        np_module=np_module,
        image_data=image_rgb_float,
    ).astype(np_module.float64)
    luminance = (
        _AUTO_LEVELS_TONECURVE_LUMINANCE_WEIGHTS[0] * normalized[..., 0]
        + _AUTO_LEVELS_TONECURVE_LUMINANCE_WEIGHTS[1] * normalized[..., 1]
        + _AUTO_LEVELS_TONECURVE_LUMINANCE_WEIGHTS[2] * normalized[..., 2]
    )
    histogram_index = np_module.clip(
        (luminance * _AUTO_LEVELS_CODE_MAX).astype(np_module.int64),
        0,
        _AUTO_LEVELS_CODE_BIN_COUNT - 1,
    )
    return np_module.bincount(
        histogram_index.ravel(),
        minlength=_AUTO_LEVELS_CODE_BIN_COUNT,
    ).astype(np_module.uint64)


def _rt_hlcurve_float(np_module, exp_scale, comp, hlrange, levels_code):
    """@brief Evaluate RawTherapee highlight-curve overflow branch.

    @details Ports `CurveFactory::hlcurve(...)` for channel samples above the
    dense LUT range while staying in float arithmetic and code-value units only
    for the local formula evaluation.
    @param np_module {ModuleType} Imported numpy module.
    @param exp_scale {float} Exposure scaling factor `2^expcomp`.
    @param comp {float} Highlight-compression coefficient.
    @param hlrange {float} Highlight range in RawTherapee code units.
    @param levels_code {object} Code-domain sample tensor.
    @return {object} Tone factors for the overflow samples.
    @satisfies REQ-100, REQ-119
    """

    if comp <= 0.0:
        return np_module.full_like(
            np_module.asarray(levels_code, dtype=np_module.float64),
            float(exp_scale),
            dtype=np_module.float64,
        )
    levels = np_module.asarray(levels_code, dtype=np_module.float64)
    value = levels + (float(hlrange) - float(_AUTO_LEVELS_CODE_BIN_COUNT))
    value = np_module.where(value == 0.0, 0.000001, value)
    y_value = value * float(exp_scale) / float(hlrange)
    y_value *= float(comp)
    y_value = np_module.where(y_value <= -1.0, -0.999999, y_value)
    ratio = float(hlrange) / (value * float(comp))
    return np_module.log1p(y_value) * ratio


def _build_auto_levels_tone_curve_state(np_module, image_rgb_float, auto_levels_metrics):
    """@brief Build RawTherapee-equivalent auto-levels curve state.

    @details Ports the curve-building path of `CurveFactory::complexCurve(...)`
    into normalized float execution: full-resolution histogram, highlight curve,
    shadow curve, brightness curve, contrast curve, and inverse-gamma output
    tonecurve. Shadow compression remains fixed to RawTherapee default `0`.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} Normalized RGB float tensor.
    @param auto_levels_metrics {dict[str, int|float]} Metrics from `_compute_auto_levels_from_histogram(...)`.
    @return {dict[str, object]} Tone-curve state dictionary.
    @satisfies REQ-100, REQ-118, REQ-119
    """

    histogram = _build_auto_levels_full_histogram_rgb_float(
        np_module=np_module,
        image_rgb_float=image_rgb_float,
    ).astype(np_module.float64)
    gain = float(auto_levels_metrics.get("gain", 1.0))
    expcomp = float(
        auto_levels_metrics.get(
            "expcomp",
            math.log(max(gain, 1e-12), 2.0),
        )
    )
    black = float(
        auto_levels_metrics.get(
            "black_normalized",
            float(auto_levels_metrics.get("black", 0.0)) / _AUTO_LEVELS_CODE_MAX,
        )
    )
    brightness = int(auto_levels_metrics.get("brightness", 0))
    contrast = int(auto_levels_metrics.get("contrast", 0))
    hlcompr = int(auto_levels_metrics.get("hlcompr", 0))
    hlcomprthresh = int(auto_levels_metrics.get("hlcomprthresh", 0))

    brightness_curve = None
    if brightness != 0:
        if brightness > 0:
            x_points = (0.0, 0.1, 0.7, 1.0)
            y_points = (
                0.0,
                0.1 + brightness / 150.0,
                min(1.0, 0.7 + brightness / 300.0),
                1.0,
            )
        else:
            x_points = (
                0.0,
                max(0.0, 0.1 - brightness / 150.0),
                0.7 - brightness / 300.0,
                1.0,
            )
            y_points = (0.0, 0.1, 0.7, 1.0)
        brightness_curve = _build_rt_nurbs_curve_lut(
            np_module=np_module,
            x_points=x_points,
            y_points=y_points,
            sample_count=_AUTO_LEVELS_CODE_BIN_COUNT,
        )

    exp_scale = math.pow(2.0, expcomp)
    comp = (max(0.0, expcomp) + 1.0) * float(hlcompr) / 100.0
    shoulder = (
        (float(_AUTO_LEVELS_CODE_BIN_COUNT) / max(1.0, exp_scale))
        * (float(hlcomprthresh) / 200.0)
    ) + 0.1
    hlrange = float(_AUTO_LEVELS_CODE_BIN_COUNT) - shoulder

    highlight_curve = np_module.full(
        _AUTO_LEVELS_CODE_BIN_COUNT,
        exp_scale,
        dtype=np_module.float64,
    )
    if comp > 0.0:
        start_index = min(
            _AUTO_LEVELS_CODE_BIN_COUNT,
            max(0, int(shoulder) + 1),
        )
        if start_index < _AUTO_LEVELS_CODE_BIN_COUNT:
            curve_indices = np_module.arange(
                start_index,
                _AUTO_LEVELS_CODE_BIN_COUNT,
                dtype=np_module.float64,
            )
            r_value = ((curve_indices - shoulder) * comp) / (
                float(_AUTO_LEVELS_CODE_BIN_COUNT) - shoulder
            )
            highlight_curve[start_index:] = np_module.log1p(
                r_value * exp_scale
            ) / r_value

    shadow_curve = np_module.ones(
        _AUTO_LEVELS_CODE_BIN_COUNT,
        dtype=np_module.float64,
    )
    if black != 0.0:
        normalized_codes = (
            np_module.arange(_AUTO_LEVELS_CODE_BIN_COUNT, dtype=np_module.float64)
            / _AUTO_LEVELS_CODE_MAX
        )
        first_value = 1.0 / _AUTO_LEVELS_CODE_MAX
        shadow_curve[0] = _rt_simplebasecurve_scalar(
            first_value,
            black,
            0.0,
        ) / first_value
        shadow_curve[1:] = np_module.asarray(
            [
                _rt_simplebasecurve_scalar(float(value), black, 0.0) / float(value)
                for value in normalized_codes[1:]
            ],
            dtype=np_module.float64,
        )

    code_indices = np_module.arange(
        _AUTO_LEVELS_CODE_BIN_COUNT,
        dtype=np_module.float64,
    )
    gamma_curve = _rt_gamma2(
        np_module,
        code_indices / _AUTO_LEVELS_CODE_MAX,
    ).astype(np_module.float64)
    if brightness_curve is not None:
        dcurve = np_module.clip(
            _sample_auto_levels_lut_float(
                np_module=np_module,
                lut_values=brightness_curve,
                indices=gamma_curve * _AUTO_LEVELS_CODE_MAX,
            ),
            0.0,
            1.0,
        )
    else:
        dcurve = gamma_curve

    if contrast != 0:
        highlighted_codes = code_indices * highlight_curve
        shadow_factors = _sample_auto_levels_lut_float(
            np_module=np_module,
            lut_values=shadow_curve,
            indices=highlighted_codes,
        )
        contrasted_input = shadow_factors * highlighted_codes
        dcurve_samples = _sample_auto_levels_lut_float(
            np_module=np_module,
            lut_values=dcurve,
            indices=contrasted_input,
        )
        histogram_sum = float(histogram.sum())
        average_luminance = float(
            np_module.dot(dcurve_samples, histogram) / max(histogram_sum, 1.0)
        )
        contrast_curve = _build_rt_nurbs_curve_lut(
            np_module=np_module,
            x_points=(
                0.0,
                average_luminance
                - average_luminance * (0.6 - contrast / 250.0),
                average_luminance
                + (1.0 - average_luminance) * (0.6 - contrast / 250.0),
                1.0,
            ),
            y_points=(
                0.0,
                average_luminance
                - average_luminance * (0.6 + contrast / 250.0),
                average_luminance
                + (1.0 - average_luminance) * (0.6 + contrast / 250.0),
                1.0,
            ),
            sample_count=_AUTO_LEVELS_CODE_BIN_COUNT,
        )
        dcurve = _sample_auto_levels_lut_float(
            np_module=np_module,
            lut_values=contrast_curve,
            indices=dcurve * _AUTO_LEVELS_CODE_MAX,
        )

    tone_curve = _rt_igamma2(np_module, dcurve).astype(np_module.float64)
    return {
        "highlight_curve": highlight_curve,
        "shadow_curve": shadow_curve,
        "tone_curve": tone_curve,
        "exp_scale": float(exp_scale),
        "comp": float(comp),
        "hlrange": float(hlrange),
    }


def _apply_auto_levels_tonal_transform_float(
    np_module,
    image_rgb_float,
    auto_levels_metrics,
):
    """@brief Apply RawTherapee-equivalent auto-levels tonal transformation.

    @details Executes the float-domain port of RawTherapee auto-levels tone
    processing in the same stage order as `rgbProc(...)`: highlight curve,
    shadow curve, then output tonecurve. Exposure scaling is carried by the
    highlight curve baseline instead of a separate gain-only multiply. Mixed
    overflow pixels remain on the RawTherapee per-channel path; the function
    does not bypass tone mapping for partially out-of-gamut triplets.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} Normalized RGB float tensor.
    @param auto_levels_metrics {dict[str, int|float]} Metrics from `_compute_auto_levels_from_histogram(...)`.
    @return {object} Tonally transformed RGB float tensor.
    @satisfies REQ-100, REQ-119
    """

    normalized_input = _normalize_float_rgb_image(
        np_module=np_module,
        image_data=image_rgb_float,
    ).astype(np_module.float64)
    tone_curve_state = _build_auto_levels_tone_curve_state(
        np_module=np_module,
        image_rgb_float=normalized_input,
        auto_levels_metrics=auto_levels_metrics,
    )
    image_code = normalized_input * _AUTO_LEVELS_CODE_MAX
    highlight_curve = tone_curve_state["highlight_curve"]
    exp_scale = float(tone_curve_state["exp_scale"])
    comp = float(tone_curve_state["comp"])
    hlrange = float(tone_curve_state["hlrange"])

    channel_factors = []
    for channel_index in range(3):
        channel_code = image_code[..., channel_index]
        tone_factor = _sample_auto_levels_lut_float(
            np_module=np_module,
            lut_values=highlight_curve,
            indices=channel_code,
        )
        if comp > 0.0:
            tone_factor = np_module.where(
                channel_code <= _AUTO_LEVELS_CODE_MAX,
                tone_factor,
                _rt_hlcurve_float(
                    np_module=np_module,
                    exp_scale=exp_scale,
                    comp=comp,
                    hlrange=hlrange,
                    levels_code=channel_code,
                ),
            )
        channel_factors.append(tone_factor)
    highlight_factor = (
        channel_factors[0] + channel_factors[1] + channel_factors[2]
    ) / 3.0
    image_code *= highlight_factor[..., None]

    black_normalized = float(
        auto_levels_metrics.get(
            "black_normalized",
            float(auto_levels_metrics.get("black", 0.0)) / _AUTO_LEVELS_CODE_MAX,
        )
    )
    if black_normalized != 0.0:
        luminance_code = (
            _AUTO_LEVELS_TONECURVE_LUMINANCE_WEIGHTS[0] * image_code[..., 0]
            + _AUTO_LEVELS_TONECURVE_LUMINANCE_WEIGHTS[1] * image_code[..., 1]
            + _AUTO_LEVELS_TONECURVE_LUMINANCE_WEIGHTS[2] * image_code[..., 2]
        )
        shadow_factor = _sample_auto_levels_lut_float(
            np_module=np_module,
            lut_values=tone_curve_state["shadow_curve"],
            indices=luminance_code,
        )
        image_code *= shadow_factor[..., None]

    return _sample_auto_levels_lut_float(
        np_module=np_module,
        lut_values=tone_curve_state["tone_curve"],
        indices=image_code,
    )


def _auto_levels_has_full_tone_metrics(auto_levels_metrics):
    """@brief Check whether auto-levels metrics support full tone processing.

    @details Verifies the presence of the full RawTherapee-compatible metric set
    consumed by `_apply_auto_levels_tonal_transform_float(...)`. Legacy tests
    may monkeypatch `_compute_auto_levels_from_histogram(...)` with partial
    dictionaries containing only `gain`; such patched metrics must keep the
    historical gain-only fallback path.
    @param auto_levels_metrics {dict[str, int|float]} Histogram-derived metrics dictionary.
    @return {bool} `True` when all full tone-transform metrics are present.
    @satisfies REQ-100, REQ-119
    """

    required_keys = (
        "expcomp",
        "black_normalized",
        "brightness",
        "contrast",
        "hlcompr",
        "hlcomprthresh",
    )
    return all(metric_key in auto_levels_metrics for metric_key in required_keys)


def _call_auto_levels_compat_helper(
    np_module,
    primary_callable,
    legacy_name,
    scaled_argument_names,
    **kwargs,
):
    """@brief Invoke float-native helper while honoring patched legacy aliases.

    @details Selects the float-native helper for normal execution. If a legacy
    `_uint16` alias has been monkeypatched away from its built-in compatibility
    shim, converts designated normalized arguments to legacy code scale,
    delegates to the patched callable, and maps the returned tensor back to
    normalized scale. This preserves deterministic legacy unit-test hooks
    without reintroducing code-domain math into the production auto-levels
    pipeline.
    @param np_module {ModuleType} Imported numpy module.
    @param primary_callable {object} Float-native helper callable.
    @param legacy_name {str} Legacy module attribute name.
    @param scaled_argument_names {set[str]} Keyword names requiring normalized<->legacy scaling in compatibility mode.
    @param kwargs {dict[str, object]} Helper keyword arguments.
    @return {object} Normalized RGB float tensor returned by the selected helper.
    @satisfies REQ-100, REQ-102, REQ-119, REQ-120
    """

    legacy_callable = globals().get(legacy_name)
    default_legacy = _AUTO_LEVELS_LEGACY_HELPER_DEFAULTS.get(legacy_name)
    if legacy_callable is not None and legacy_callable is not default_legacy:
        legacy_kwargs = {}
        for key, value in kwargs.items():
            if key in scaled_argument_names:
                legacy_kwargs[key] = _auto_levels_normalized_to_legacy_code(
                    np_module=np_module,
                    values=value,
                )
            elif key == "maxval":
                legacy_kwargs[key] = _auto_levels_normalized_to_legacy_code_value(
                    value
                )
            else:
                legacy_kwargs[key] = value
        legacy_result = legacy_callable(np_module=np_module, **legacy_kwargs)
        return _auto_levels_legacy_code_to_normalized(
            np_module=np_module,
            values=legacy_result,
        )
    return primary_callable(np_module=np_module, **kwargs)


def _apply_auto_levels_float(np_module, image_rgb_float, auto_levels_options):
    """@brief Apply auto-levels stage on RGB float tensor.

    @details Executes RawTherapee-compatible histogram analysis on a normalized
    RGB float tensor, applies the full float-domain tonal transformation driven
    by exposure, black, brightness, contrast, and highlight-compression
    metrics, conditionally runs float-native highlight reconstruction, and
    optionally clips overflowing RGB triplets with RawTherapee film-like gamut
    logic without any production uint16 staging buffers; no final stage-local
    `[0,1]` clipping is applied beyond the optional gamut clip.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} RGB float tensor.
    @param auto_levels_options {AutoLevelsOptions} Parsed auto-levels options.
    @return {object} RGB float tensor after auto-levels stage without final stage-local clipping.
    @satisfies REQ-100, REQ-101, REQ-102, REQ-119, REQ-120, REQ-165
    """

    normalized_input = _normalize_float_rgb_image(
        np_module=np_module,
        image_data=image_rgb_float,
    )
    histogram = _build_autoexp_histogram_rgb_float(
        np_module=np_module,
        image_rgb_float=normalized_input,
        histcompr=auto_levels_options.histcompr,
    )
    auto_levels_metrics = _compute_auto_levels_from_histogram(
        np_module=np_module,
        histogram=histogram,
        histcompr=auto_levels_options.histcompr,
        clip_percent=auto_levels_options.clip_percent,
    )
    if _auto_levels_has_full_tone_metrics(auto_levels_metrics):
        image_float = _apply_auto_levels_tonal_transform_float(
            np_module=np_module,
            image_rgb_float=normalized_input,
            auto_levels_metrics=auto_levels_metrics,
        )
    else:
        gain = float(auto_levels_metrics.get("gain", 1.0))
        image_float = normalized_input.astype(np_module.float64) * gain
    if auto_levels_options.highlight_reconstruction_enabled:
        method = auto_levels_options.highlight_reconstruction_method
        if method == "Luminance Recovery":
            image_float = _call_auto_levels_compat_helper(
                np_module=np_module,
                primary_callable=_hlrecovery_luminance_float,
                legacy_name="_hlrecovery_luminance_uint16",
                scaled_argument_names={"image_rgb"},
                image_rgb=image_float,
                maxval=1.0,
            )
        elif method == "CIELab Blending":
            image_float = _call_auto_levels_compat_helper(
                np_module=np_module,
                primary_callable=_hlrecovery_cielab_float,
                legacy_name="_hlrecovery_cielab_uint16",
                scaled_argument_names={"image_rgb"},
                image_rgb=image_float,
                maxval=1.0,
            )
        elif method == "Blend":
            image_float = _call_auto_levels_compat_helper(
                np_module=np_module,
                primary_callable=_hlrecovery_blend_float,
                legacy_name="_hlrecovery_blend_uint16",
                scaled_argument_names={"image_rgb", "hlmax"},
                image_rgb=image_float,
                hlmax=np_module.max(image_float, axis=(0, 1)),
                maxval=1.0,
            )
        elif method == "Color Propagation":
            image_float = _call_auto_levels_compat_helper(
                np_module=np_module,
                primary_callable=_hlrecovery_color_propagation_float,
                legacy_name="_hlrecovery_color_propagation_uint16",
                scaled_argument_names={"image_rgb"},
                image_rgb=image_float,
                maxval=1.0,
            )
        elif method == "Inpaint Opposed":
            image_float = _call_auto_levels_compat_helper(
                np_module=np_module,
                primary_callable=_hlrecovery_inpaint_opposed_float,
                legacy_name="_hlrecovery_inpaint_opposed_uint16",
                scaled_argument_names={"image_rgb"},
                image_rgb=image_float,
                gain_threshold=auto_levels_options.gain_threshold,
                maxval=1.0,
            )
        else:
            raise ValueError(f"Unsupported highlight reconstruction method: {method}")
    if auto_levels_options.clip_out_of_gamut:
        image_float = _call_auto_levels_compat_helper(
            np_module=np_module,
            primary_callable=_clip_auto_levels_out_of_gamut_float,
            legacy_name="_clip_auto_levels_out_of_gamut_uint16",
            scaled_argument_names={"image_rgb"},
            image_rgb=image_float,
            maxval=1.0,
        )
    return image_float.astype(np_module.float32)


def _clip_auto_levels_out_of_gamut_float(np_module, image_rgb, maxval=1.0):
    """@brief Clip overflowing RGB triplets with RawTherapee film-like gamut logic.

    @details Ports RawTherapee `filmlike_clip(...)` to normalized float space.
    Negative channels are clamped to `0` first. Overflowing triplets then use
    the Adobe-style hue-stable diagonal clipping family instead of isotropic
    normalization so dominant-channel ordering and cross-channel interpolation
    follow RawTherapee semantics.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on normalized scale.
    @param maxval {float} Maximum allowed channel value.
    @return {object} RGB float tensor with no channel above `maxval`.
    @satisfies REQ-165
    """

    rgb = np_module.asarray(image_rgb, dtype=np_module.float64)
    output = np_module.maximum(rgb, 0.0)
    red = output[..., 0]
    green = output[..., 1]
    blue = output[..., 2]
    source_red = red.copy()
    source_green = green.copy()
    source_blue = blue.copy()
    overflow_mask = np_module.logical_or(
        source_red > maxval,
        np_module.logical_or(source_green > maxval, source_blue > maxval),
    )
    if not np_module.any(overflow_mask):
        return output

    def _filmlike_clip_rgb_tone(primary, middle, lower):
        """@brief Apply one ordered RawTherapee diagonal gamut clip branch.

        @details Clamps the dominant and lower channels to `maxval`, then
        reconstructs the middle channel by linearly interpolating across the
        unclipped diagonal exactly like RawTherapee `filmlike_clip_rgb_tone`.
        Division-by-zero only occurs on degenerate equal-channel cases that are
        dispatched away by the branch predicates, but one safe fallback is kept
        for deterministic vectorized execution.
        @param primary {object} Dominant-channel tensor for one branch.
        @param middle {object} Middle-ranked channel tensor for one branch.
        @param lower {object} Lowest-ranked channel tensor for one branch.
        @return {tuple[object, object, object]} Branch-clipped `(primary, middle, lower)` tensors.
        @satisfies REQ-165
        """

        primary_clipped = np_module.minimum(primary, maxval)
        lower_clipped = np_module.minimum(lower, maxval)
        denominator = primary - lower
        safe_denominator = np_module.where(
            denominator != 0.0,
            denominator,
            1.0,
        )
        middle_clipped = lower_clipped + (
            (primary_clipped - lower_clipped) * (middle - lower) / safe_denominator
        )
        middle_clipped = np_module.where(
            denominator != 0.0,
            middle_clipped,
            np_module.minimum(middle, maxval),
        )
        return primary_clipped, middle_clipped, lower_clipped

    case_1 = overflow_mask & (source_red >= source_green) & (source_green > source_blue)
    if np_module.any(case_1):
        r_case, g_case, b_case = _filmlike_clip_rgb_tone(
            red[case_1],
            green[case_1],
            blue[case_1],
        )
        red[case_1] = r_case
        green[case_1] = g_case
        blue[case_1] = b_case

    case_2 = overflow_mask & (source_red >= source_green) & (source_blue > source_red)
    if np_module.any(case_2):
        b_case, r_case, g_case = _filmlike_clip_rgb_tone(
            blue[case_2],
            red[case_2],
            green[case_2],
        )
        red[case_2] = r_case
        green[case_2] = g_case
        blue[case_2] = b_case

    case_3 = (
        overflow_mask
        & (source_red >= source_green)
        & ~(source_green > source_blue)
        & ~(source_blue > source_red)
        & (source_blue > source_green)
    )
    if np_module.any(case_3):
        r_case, b_case, g_case = _filmlike_clip_rgb_tone(
            red[case_3],
            blue[case_3],
            green[case_3],
        )
        red[case_3] = r_case
        green[case_3] = g_case
        blue[case_3] = b_case

    case_4 = (
        overflow_mask
        & (source_red >= source_green)
        & ~(source_green > source_blue)
        & ~(source_blue > source_red)
        & ~(source_blue > source_green)
    )
    if np_module.any(case_4):
        red[case_4] = np_module.minimum(red[case_4], maxval)
        green[case_4] = np_module.minimum(green[case_4], maxval)
        blue[case_4] = green[case_4]

    case_5 = overflow_mask & ~(source_red >= source_green) & (source_red >= source_blue)
    if np_module.any(case_5):
        g_case, r_case, b_case = _filmlike_clip_rgb_tone(
            green[case_5],
            red[case_5],
            blue[case_5],
        )
        red[case_5] = r_case
        green[case_5] = g_case
        blue[case_5] = b_case

    case_6 = (
        overflow_mask
        & ~(source_red >= source_green)
        & ~(source_red >= source_blue)
        & (source_blue > source_green)
    )
    if np_module.any(case_6):
        b_case, g_case, r_case = _filmlike_clip_rgb_tone(
            blue[case_6],
            green[case_6],
            red[case_6],
        )
        red[case_6] = r_case
        green[case_6] = g_case
        blue[case_6] = b_case

    case_7 = (
        overflow_mask
        & ~(source_red >= source_green)
        & ~(source_red >= source_blue)
        & ~(source_blue > source_green)
    )
    if np_module.any(case_7):
        g_case, b_case, r_case = _filmlike_clip_rgb_tone(
            green[case_7],
            blue[case_7],
            red[case_7],
        )
        red[case_7] = r_case
        green[case_7] = g_case
        blue[case_7] = b_case

    return output


def _clip_auto_levels_out_of_gamut_uint16(
    np_module, image_rgb, maxval=_AUTO_LEVELS_CODE_MAX
):
    """@brief Compatibility adapter for the legacy gamut-clip helper name.

    @details Converts legacy code-domain float tensors to normalized scale,
    delegates to `_clip_auto_levels_out_of_gamut_float(...)`, and rescales the
    result back to legacy code units. This shim exists only for transitional
    internal references and deterministic legacy unit-test hooks.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on legacy code scale.
    @param maxval {float} Maximum allowed legacy code-domain value.
    @return {object} RGB float tensor on legacy code scale.
    @deprecated Use `_clip_auto_levels_out_of_gamut_float`.
    @satisfies REQ-165
    """

    clipped = _clip_auto_levels_out_of_gamut_float(
        np_module=np_module,
        image_rgb=_auto_levels_legacy_code_to_normalized(
            np_module=np_module,
            values=image_rgb,
        ),
        maxval=float(maxval) / _AUTO_LEVELS_CODE_MAX,
    )
    return _auto_levels_normalized_to_legacy_code(
        np_module=np_module,
        values=clipped,
    )


def _hlrecovery_luminance_float(np_module, image_rgb, maxval=1.0):
    """@brief Apply Luminance highlight reconstruction on normalized RGB tensor.

    @details Ports luminance method from attached source in RGB domain with
    clipped-channel chroma ratio scaling and masked reconstruction.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on normalized scale.
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
        (chroma_c_clip * chroma_c_clip + chroma_h_clip * chroma_h_clip)
        / denominator
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


def _hlrecovery_luminance_uint16(np_module, image_rgb, maxval=_AUTO_LEVELS_CODE_MAX):
    """@brief Compatibility adapter for legacy luminance recovery helper name.

    @details Converts legacy code-domain float tensors to normalized scale,
    delegates to `_hlrecovery_luminance_float(...)`, and rescales the result
    back to legacy code units. This shim exists only for transitional internal
    references and deterministic legacy unit-test hooks.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on legacy code scale.
    @param maxval {float} Maximum legacy code-domain value.
    @return {object} Highlight-reconstructed RGB float tensor on legacy code scale.
    @deprecated Use `_hlrecovery_luminance_float`.
    @satisfies REQ-102
    """

    recovered = _hlrecovery_luminance_float(
        np_module=np_module,
        image_rgb=_auto_levels_legacy_code_to_normalized(
            np_module=np_module,
            values=image_rgb,
        ),
        maxval=float(maxval) / _AUTO_LEVELS_CODE_MAX,
    )
    return _auto_levels_normalized_to_legacy_code(
        np_module=np_module,
        values=recovered,
    )


def _hlrecovery_cielab_float(
    np_module, image_rgb, maxval=1.0, xyz_cam=None, cam_xyz=None
):
    """@brief Apply CIELab blending highlight reconstruction on RGB tensor.

    @details Ports CIELab blending method from attached source with Lab-space
    channel repair under clipped highlights.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on normalized scale.
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


def _hlrecovery_cielab_uint16(
    np_module, image_rgb, maxval=_AUTO_LEVELS_CODE_MAX, xyz_cam=None, cam_xyz=None
):
    """@brief Compatibility adapter for legacy CIELab helper name.

    @details Converts legacy code-domain float tensors to normalized scale,
    delegates to `_hlrecovery_cielab_float(...)`, and rescales the result back
    to legacy code units. This shim exists only for transitional internal
    references and deterministic legacy unit-test hooks.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on legacy code scale.
    @param maxval {float} Maximum legacy code-domain value.
    @param xyz_cam {object|None} Optional XYZ conversion matrix.
    @param cam_xyz {object|None} Optional inverse matrix.
    @return {object} Highlight-reconstructed RGB float tensor on legacy code scale.
    @deprecated Use `_hlrecovery_cielab_float`.
    @satisfies REQ-102
    """

    recovered = _hlrecovery_cielab_float(
        np_module=np_module,
        image_rgb=_auto_levels_legacy_code_to_normalized(
            np_module=np_module,
            values=image_rgb,
        ),
        maxval=float(maxval) / _AUTO_LEVELS_CODE_MAX,
        xyz_cam=xyz_cam,
        cam_xyz=cam_xyz,
    )
    return _auto_levels_normalized_to_legacy_code(
        np_module=np_module,
        values=recovered,
    )


def _hlrecovery_blend_float(np_module, image_rgb, hlmax, maxval=1.0):
    """@brief Apply Blend highlight reconstruction on RGB tensor.

    @details Ports blend method from attached source with quadratic channel blend
    and desaturation phase driven by clipping metrics.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on normalized scale.
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
    clip = np_module.minimum(maxave, hlmax_values)
    clippt = _AUTO_LEVELS_BLEND_CLIP_THRESHOLD * maxval
    fixpt = _AUTO_LEVELS_BLEND_FIX_THRESHOLD * minpt
    desatpt = (
        _AUTO_LEVELS_BLEND_SATURATION_THRESHOLD * maxave
        + (1.0 - _AUTO_LEVELS_BLEND_SATURATION_THRESHOLD) * maxval
    )
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
    lfrac = np_module.maximum(
        0.0,
        (maxave - lightness2) / max(maxave - desatpt, 1e-20),
    )
    chroma_c2 = lfrac * 1.732050808 * (red_s2 - green_s2)
    chroma_h2 = lfrac * (2.0 * blue_s2 - red_s2 - green_s2)
    rec_red = lightness2 - chroma_h2 / 6.0 + chroma_c2 / 3.464101615
    rec_green = lightness2 - chroma_h2 / 6.0 - chroma_c2 / 3.464101615
    rec_blue = lightness2 + chroma_h2 / 3.0
    output[..., 0] = np_module.where(desat_mask, rec_red, output[..., 0])
    output[..., 1] = np_module.where(desat_mask, rec_green, output[..., 1])
    output[..., 2] = np_module.where(desat_mask, rec_blue, output[..., 2])
    return output


def _hlrecovery_blend_uint16(
    np_module, image_rgb, hlmax, maxval=_AUTO_LEVELS_CODE_MAX
):
    """@brief Compatibility adapter for legacy Blend helper name.

    @details Converts legacy code-domain float tensors to normalized scale,
    delegates to `_hlrecovery_blend_float(...)`, and rescales the result back
    to legacy code units. This shim exists only for transitional internal
    references and deterministic legacy unit-test hooks.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on legacy code scale.
    @param hlmax {object} Legacy code-domain channel maxima vector.
    @param maxval {float} Maximum legacy code-domain value.
    @return {object} Highlight-reconstructed RGB float tensor on legacy code scale.
    @deprecated Use `_hlrecovery_blend_float`.
    @satisfies REQ-102
    """

    recovered = _hlrecovery_blend_float(
        np_module=np_module,
        image_rgb=_auto_levels_legacy_code_to_normalized(
            np_module=np_module,
            values=image_rgb,
        ),
        hlmax=_auto_levels_legacy_code_to_normalized(
            np_module=np_module,
            values=hlmax,
        ),
        maxval=float(maxval) / _AUTO_LEVELS_CODE_MAX,
    )
    return _auto_levels_normalized_to_legacy_code(
        np_module=np_module,
        values=recovered,
    )


def _dilate_mask_float(np_module, mask):
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


def _box_mean_3x3_float(np_module, image_2d):
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


def _hlrecovery_color_propagation_float(np_module, image_rgb, maxval=1.0):
    """@brief Apply Color Propagation highlight reconstruction on RGB tensor.

    @details Approximates RawTherapee `Color` recovery in post-merge RGB space:
    detect clipped channel regions, estimate one local opposite-channel
    reference from `3x3` means, derive one border chrominance offset, and fill
    clipped samples deterministically.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on normalized scale.
    @param maxval {float} Maximum channel value.
    @return {object} Highlight-reconstructed RGB float tensor.
    @satisfies REQ-102, REQ-119
    """

    rgb = np_module.asarray(image_rgb, dtype=np_module.float64)
    output = rgb.copy()
    clip_level = _AUTO_LEVELS_BLEND_CLIP_THRESHOLD * maxval
    dark_floor = _AUTO_LEVELS_COLOR_PROPAGATION_DARK_FLOOR * clip_level
    for channel_index in range(3):
        channel = output[..., channel_index]
        channel_mask = channel >= clip_level
        if not np_module.any(channel_mask):
            continue
        other_indices = [index for index in range(3) if index != channel_index]
        reference = 0.5 * (
            _box_mean_3x3_float(np_module, output[..., other_indices[0]])
            + _box_mean_3x3_float(np_module, output[..., other_indices[1]])
        )
        border_mask = _dilate_mask_float(np_module, channel_mask) & (~channel_mask)
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


def _hlrecovery_color_propagation_uint16(
    np_module, image_rgb, maxval=_AUTO_LEVELS_CODE_MAX
):
    """@brief Compatibility adapter for legacy Color Propagation helper name.

    @details Converts legacy code-domain float tensors to normalized scale,
    delegates to `_hlrecovery_color_propagation_float(...)`, and rescales the
    result back to legacy code units. This shim exists only for transitional
    internal references and deterministic legacy unit-test hooks.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on legacy code scale.
    @param maxval {float} Maximum legacy code-domain value.
    @return {object} Highlight-reconstructed RGB float tensor on legacy code scale.
    @deprecated Use `_hlrecovery_color_propagation_float`.
    @satisfies REQ-102, REQ-119
    """

    recovered = _hlrecovery_color_propagation_float(
        np_module=np_module,
        image_rgb=_auto_levels_legacy_code_to_normalized(
            np_module=np_module,
            values=image_rgb,
        ),
        maxval=float(maxval) / _AUTO_LEVELS_CODE_MAX,
    )
    return _auto_levels_normalized_to_legacy_code(
        np_module=np_module,
        values=recovered,
    )


def _hlrecovery_inpaint_opposed_float(
    np_module, image_rgb, gain_threshold, maxval=1.0
):
    """@brief Apply Inpaint Opposed highlight reconstruction on RGB tensor.

    @details Approximates RawTherapee `Coloropp` recovery in post-merge RGB
    space: derive the RawTherapee clip threshold from `gain_threshold`,
    construct one cubic-root opposite-channel neighborhood predictor, estimate
    one border chrominance offset, and inpaint only pixels above the clip
    threshold.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on normalized scale.
    @param gain_threshold {float} Positive Inpaint Opposed gain threshold.
    @param maxval {float} Maximum channel value.
    @return {object} Highlight-reconstructed RGB float tensor.
    @satisfies REQ-102, REQ-119
    """

    rgb = np_module.asarray(image_rgb, dtype=np_module.float64)
    output = rgb.copy()
    gain = _AUTO_LEVELS_INPAINT_GAIN_MULTIPLIER * float(gain_threshold)
    clip_level = (_AUTO_LEVELS_INPAINT_CLIP_RATIO / max(gain, 1e-12)) * maxval
    clip_dark_levels = (0.03 * clip_level, 0.125 * clip_level, 0.03 * clip_level)
    for channel_index in range(3):
        channel = output[..., channel_index]
        channel_mask = channel >= clip_level
        if not np_module.any(channel_mask):
            continue
        local_means = []
        for source_channel in range(3):
            local_mean = _box_mean_3x3_float(np_module, output[..., source_channel])
            local_means.append(np_module.cbrt(np_module.maximum(local_mean, 0.0)))
        other_indices = [index for index in range(3) if index != channel_index]
        reference = np_module.power(
            0.5 * (local_means[other_indices[0]] + local_means[other_indices[1]]),
            3.0,
        )
        border_mask = _dilate_mask_float(np_module, channel_mask) & (~channel_mask)
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


def _hlrecovery_inpaint_opposed_uint16(
    np_module, image_rgb, gain_threshold, maxval=_AUTO_LEVELS_CODE_MAX
):
    """@brief Compatibility adapter for legacy Inpaint Opposed helper name.

    @details Converts legacy code-domain float tensors to normalized scale,
    delegates to `_hlrecovery_inpaint_opposed_float(...)`, and rescales the
    result back to legacy code units. This shim exists only for transitional
    internal references and deterministic legacy unit-test hooks.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb {object} RGB float tensor on legacy code scale.
    @param gain_threshold {float} Positive Inpaint Opposed gain threshold.
    @param maxval {float} Maximum legacy code-domain value.
    @return {object} Highlight-reconstructed RGB float tensor on legacy code scale.
    @deprecated Use `_hlrecovery_inpaint_opposed_float`.
    @satisfies REQ-102, REQ-119
    """

    recovered = _hlrecovery_inpaint_opposed_float(
        np_module=np_module,
        image_rgb=_auto_levels_legacy_code_to_normalized(
            np_module=np_module,
            values=image_rgb,
        ),
        gain_threshold=gain_threshold,
        maxval=float(maxval) / _AUTO_LEVELS_CODE_MAX,
    )
    return _auto_levels_normalized_to_legacy_code(
        np_module=np_module,
        values=recovered,
    )


_AUTO_LEVELS_LEGACY_HELPER_DEFAULTS = {
    "_clip_auto_levels_out_of_gamut_uint16": _clip_auto_levels_out_of_gamut_uint16,
    "_hlrecovery_luminance_uint16": _hlrecovery_luminance_uint16,
    "_hlrecovery_cielab_uint16": _hlrecovery_cielab_uint16,
    "_hlrecovery_blend_uint16": _hlrecovery_blend_uint16,
    "_hlrecovery_color_propagation_uint16": _hlrecovery_color_propagation_uint16,
    "_hlrecovery_inpaint_opposed_uint16": _hlrecovery_inpaint_opposed_uint16,
}


def _apply_auto_brightness_rgb_float(
    np_module,
    image_rgb_float,
    auto_brightness_options,
):
    """@brief Apply original photographic auto-brightness flow on RGB float tensor.

    @details Executes `/tmp/auto-brightness.py` step order over normalized RGB
    float input: linearize sRGB, derive BT.709 luminance, classify key using
    normalized distribution thresholds, choose or override key value `a`,
    apply Reinhard global tonemap with robust percentile white-point, preserve
    chromaticity by luminance scaling, optionally desaturate only overflowing
    linear RGB pixels, then re-encode to sRGB without any CLAHE substep or
    final stage-local `[0,1]` output clipping.
    @param np_module {ModuleType} Imported numpy module.
    @param image_rgb_float {object} RGB float tensor.
    @param auto_brightness_options {AutoBrightnessOptions} Parsed auto-brightness parameters.
    @return {object} RGB float tensor after BT.709 auto-brightness without stage-local clipping.
    @satisfies REQ-050, REQ-103, REQ-104, REQ-105, REQ-121, REQ-122
    """

    image_srgb = _normalize_float_rgb_image(
        np_module=np_module,
        image_data=image_rgb_float,
    ).astype(np_module.float64)
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
        key_value = float(key_value)
    luminance_mapped, _debug = _reinhard_global_tonemap_luminance(
        np_module=np_module,
        luminance=luminance,
        key_value=float(key_value),
        white_point_percentile=float(auto_brightness_options.white_point_percentile),
        eps=float(auto_brightness_options.eps),
    )
    luminance_scale = luminance_mapped / (luminance + auto_brightness_options.eps)
    bright_linear = image_linear * luminance_scale[..., None]
    if auto_brightness_options.enable_luminance_preserving_desat:
        bright_linear = _luminance_preserving_desaturate_to_fit(
            np_module=np_module,
            rgb_linear=bright_linear,
            luminance=luminance_mapped,
            eps=auto_brightness_options.eps,
        )
    bright_srgb = _from_linear_srgb(np_module=np_module, image_linear=bright_linear)
    return bright_srgb.astype(np_module.float32)



def _clamp01(np_module, values):
    """@brief Clamp numeric image tensor values into `[0.0, 1.0]` interval.

    @details Applies vectorized clipping to ensure deterministic bounded values
    for auto-adjust float-domain operations.
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

    @details Implements explicit HSL conversion for auto-adjust saturation-gamma
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
    conversion in the auto-adjust pipeline.
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
    for the auto-adjust saturation-gamma stage.
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


def _apply_validated_auto_adjust_pipeline(
    image_rgb_float,
    cv2_module,
    np_module,
    auto_adjust_options,
    imageio_module=None,
    debug_context=None,
):
    """@brief Execute the validated auto-adjust pipeline.

    @details Accepts one normalized RGB float image, executes selective blur,
    adaptive levels, float-domain CLAHE-luma, sigmoidal contrast, HSL
    saturation gamma, and high-pass/overlay stages entirely in float domain,
    optionally persists progressive debug checkpoints, and returns normalized
    RGB float output without any file round-trip.
    @param image_rgb_float {object} RGB float tensor.
    @param cv2_module {ModuleType} Imported cv2 module.
    @param np_module {ModuleType} Imported numpy module.
    @param auto_adjust_options {AutoAdjustOptions} Shared auto-adjust knob values.
    @param imageio_module {ModuleType|None} Optional imageio module used for debug TIFF checkpoint emission.
    @param debug_context {DebugArtifactContext|None} Optional persistent debug output metadata.
    @return {object} RGB float tensor after auto-adjust.
    @satisfies REQ-051, REQ-075, REQ-106, REQ-123, REQ-136, REQ-137, REQ-148
    """

    rgb_float = _normalize_float_rgb_image(
        np_module=np_module,
        image_data=image_rgb_float,
    ).astype(np_module.float64)
    rgb_float = _selective_blur_contrast_gated_vectorized(
        np_module,
        rgb_float,
        sigma=auto_adjust_options.blur_sigma,
        threshold_percent=auto_adjust_options.blur_threshold_pct,
    )
    if imageio_module is not None and debug_context is not None:
        _write_debug_rgb_float_tiff(
            imageio_module=imageio_module,
            np_module=np_module,
            debug_context=debug_context,
            stage_suffix="_6.1_auto-adjust_blur",
            image_rgb_float=rgb_float,
        )
    rgb_float = _level_per_channel_adaptive(
        np_module,
        rgb_float,
        low_pct=auto_adjust_options.level_low_pct,
        high_pct=auto_adjust_options.level_high_pct,
    )
    if imageio_module is not None and debug_context is not None:
        _write_debug_rgb_float_tiff(
            imageio_module=imageio_module,
            np_module=np_module,
            debug_context=debug_context,
            stage_suffix="_6.2_auto-adjust_level",
            image_rgb_float=rgb_float,
        )
    rgb_float = _apply_clahe_luma_rgb_float(
        cv2_module=cv2_module,
        np_module=np_module,
        image_rgb_float=rgb_float,
        auto_adjust_options=auto_adjust_options,
    )
    if imageio_module is not None and debug_context is not None:
        _write_debug_rgb_float_tiff(
            imageio_module=imageio_module,
            np_module=np_module,
            debug_context=debug_context,
            stage_suffix="_6.3_auto-adjust_clahe-luma",
            image_rgb_float=rgb_float,
        )
    rgb_float = _sigmoidal_contrast(
        np_module,
        rgb_float,
        contrast=auto_adjust_options.sigmoid_contrast,
        midpoint=auto_adjust_options.sigmoid_midpoint,
    )
    if imageio_module is not None and debug_context is not None:
        _write_debug_rgb_float_tiff(
            imageio_module=imageio_module,
            np_module=np_module,
            debug_context=debug_context,
            stage_suffix="_6.4_auto-adjust_sigmoid",
            image_rgb_float=rgb_float,
        )
    rgb_float = _vibrance_hsl_gamma(
        np_module, rgb_float, saturation_gamma=auto_adjust_options.saturation_gamma
    )
    if imageio_module is not None and debug_context is not None:
        _write_debug_rgb_float_tiff(
            imageio_module=imageio_module,
            np_module=np_module,
            debug_context=debug_context,
            stage_suffix="_6.5_auto-adjust_vibrance",
            image_rgb_float=rgb_float,
        )
    high_pass_gray = _high_pass_math_gray(
        cv2_module,
        np_module,
        rgb_float,
        blur_sigma=auto_adjust_options.highpass_blur_sigma,
    )
    rgb_float = _overlay_composite(np_module, rgb_float, high_pass_gray)
    rgb_float = np_module.clip(rgb_float, 0.0, 1.0).astype(np_module.float32)
    if imageio_module is not None and debug_context is not None:
        _write_debug_rgb_float_tiff(
            imageio_module=imageio_module,
            np_module=np_module,
            debug_context=debug_context,
            stage_suffix="_6.6_auto-adjust_high-pass",
            image_rgb_float=rgb_float,
        )
    return rgb_float


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
    merged_image_float,
    output_jpg,
    postprocess_options,
    auto_adjust_dependencies=None,
    numpy_module=None,
    piexif_module=None,
    source_exif_payload=None,
    source_orientation=1,
    debug_context=None,
):
    """@brief Encode merged HDR float payload into final JPG output.

    @details Accepts one normalized RGB float image from the selected merge
    backend, executes static postprocess stage (numeric
    gamma/brightness/contrast/saturation or auto-gamma replacement),
    optional auto-brightness stage, optional auto-levels stage, optional
    auto-adjust stage, and then performs exactly one float-to-uint8
    conversion immediately before JPEG save. When debug context is present, the
    function emits persistent TIFF16 checkpoints after each executed stage.
    @param imageio_module {ModuleType} Imported imageio module with `imread` and `imwrite`.
    @param pil_image_module {ModuleType} Imported Pillow image module.
    @param merged_image_float {object} Merged RGB float image produced by selected backend.
    @param output_jpg {Path} Final JPG output path.
    @param postprocess_options {PostprocessOptions} Shared TIFF-to-JPG correction settings.
    @param auto_adjust_dependencies {tuple[ModuleType, ModuleType]|None} Optional `(cv2, numpy)` modules for the auto-adjust implementation.
    @param numpy_module {ModuleType|None} Optional numpy module for float-domain stages.
    @param piexif_module {ModuleType|None} Optional piexif module for EXIF thumbnail refresh.
    @param source_exif_payload {bytes|None} Serialized EXIF payload copied from input DNG.
    @param source_orientation {int} Source EXIF orientation value in range `1..8`.
    @param debug_context {DebugArtifactContext|None} Optional persistent debug output metadata.
    @return {None} Side effects only.
    @exception RuntimeError Raised when numpy or auto-adjust dependencies are missing.
    @satisfies REQ-012, REQ-013, REQ-014, REQ-041, REQ-050, REQ-069, REQ-073, REQ-074, REQ-075, REQ-078, REQ-100, REQ-101, REQ-102, REQ-103, REQ-104, REQ-105, REQ-106, REQ-123, REQ-132, REQ-133, REQ-134, REQ-148, REQ-176
    """

    if numpy_module is not None:
        np_module = numpy_module
    elif auto_adjust_dependencies is not None:
        _cv2_module, np_module = auto_adjust_dependencies
        del _cv2_module
    else:
        try:
            import numpy as np_module  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError("Missing required dependency: numpy") from exc

    image_rgb_float = _normalize_float_rgb_image(
        np_module=np_module,
        image_data=merged_image_float,
    )
    image_rgb_float = _apply_static_postprocess_float(
        np_module=np_module,
        image_rgb_float=image_rgb_float,
        postprocess_options=postprocess_options,
        **(
            {
                "imageio_module": imageio_module,
                "debug_context": debug_context,
            }
            if debug_context is not None
            else {}
        ),
    )

    if postprocess_options.auto_brightness_enabled:
        image_rgb_float = _apply_auto_brightness_rgb_float(
            np_module=np_module,
            image_rgb_float=image_rgb_float,
            auto_brightness_options=postprocess_options.auto_brightness_options,
        )
        if debug_context is not None:
            _write_debug_rgb_float_tiff(
                imageio_module=imageio_module,
                np_module=np_module,
                debug_context=debug_context,
                stage_suffix="_4.0_auto-brightness",
                image_rgb_float=image_rgb_float,
            )
    if postprocess_options.auto_levels_enabled:
        image_rgb_float = _apply_auto_levels_float(
            np_module=np_module,
            image_rgb_float=image_rgb_float,
            auto_levels_options=postprocess_options.auto_levels_options,
        )
        if debug_context is not None:
            _write_debug_rgb_float_tiff(
                imageio_module=imageio_module,
                np_module=np_module,
                debug_context=debug_context,
                stage_suffix="_5.0_auto-levels",
                image_rgb_float=image_rgb_float,
            )

    if postprocess_options.auto_adjust_enabled:
        if auto_adjust_dependencies is None:
            raise RuntimeError("Missing required dependencies: opencv-python and numpy")
        cv2_module, np_module = auto_adjust_dependencies
        image_rgb_float = _apply_validated_auto_adjust_pipeline(
            image_rgb_float=image_rgb_float,
            cv2_module=cv2_module,
            np_module=np_module,
            auto_adjust_options=postprocess_options.auto_adjust_options,
            **(
                {
                    "imageio_module": imageio_module,
                    "debug_context": debug_context,
                }
                if debug_context is not None
                else {}
            ),
        )

    image_rgb_float = np_module.clip(image_rgb_float, 0.0, 1.0)
    final_image_rgb_uint8 = _to_uint8_image_array(
        np_module=np_module,
        image_data=image_rgb_float,
    )
    pil_image = pil_image_module.fromarray(final_image_rgb_uint8)
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
            final_image_rgb_uint8=final_image_rgb_uint8,
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
    bits-per-color from RAW metadata, resolves manual or automatic EV-zero
    center, resolves static or adaptive EV selector, extracts one linear HDR
    base image using selected RAW WB normalization mode and derives three
    normalized RGB float brackets, executes the selected HDR backend with float
    input/output interfaces,
    executes the float-interface post-merge pipeline, optionally emits
    persistent debug TIFF checkpoints for executed stages, writes the final
    JPG, and guarantees temporary artifact cleanup through isolated temporary
    directory lifecycle.
    @param args {list[str]} Command argument vector excluding command token.
    @return {int} `0` on success; `1` on parse/validation/dependency/processing failure.
    @satisfies PRJ-001, CTN-001, CTN-004, CTN-005, REQ-010, REQ-011, REQ-012, REQ-013, REQ-014, REQ-015, REQ-050, REQ-052, REQ-100, REQ-106, REQ-107, REQ-108, REQ-109, REQ-110, REQ-111, REQ-112, REQ-113, REQ-114, REQ-115, REQ-126, REQ-127, REQ-128, REQ-129, REQ-131, REQ-132, REQ-133, REQ-134, REQ-138, REQ-139, REQ-140, REQ-146, REQ-147, REQ-148, REQ-149, REQ-157, REQ-158, REQ-159, REQ-160, REQ-181, REQ-182, REQ-183, REQ-184, REQ-185, REQ-186, REQ-187, REQ-188, REQ-189, REQ-190, REQ-191, REQ-192, REQ-193, REQ-194, REQ-195, REQ-196, REQ-197, REQ-198, REQ-203, REQ-204, REQ-205, REQ-206, REQ-207
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
        postprocess_options,
        enable_luminance,
        enable_opencv,
        luminance_options,
        opencv_merge_options,
        hdrplus_options,
        enable_hdr_plus,
        ev_zero,
        ev_zero_specified,
        auto_ev_options,
    ) = parsed
    enable_opencv_tonemap = _derive_opencv_tonemap_enabled(postprocess_options)

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
    debug_context = _build_debug_artifact_context(
        output_jpg=output_jpg,
        input_dng=input_dng,
        postprocess_options=postprocess_options,
    )

    missing_external_executables = _collect_missing_external_executables(
        enable_luminance=enable_luminance,
    )
    if missing_external_executables:
        for executable in missing_external_executables:
            print_error(f"Missing required dependency: {executable}")
        return 1
    auto_adjust_dependencies = None
    numpy_module = _resolve_numpy_dependency()
    if numpy_module is None:
        return 1
    if (
        postprocess_options.auto_adjust_enabled
        or enable_opencv
        or enable_opencv_tonemap
        or auto_ev_enabled
    ):
        auto_adjust_dependencies = _resolve_auto_adjust_dependencies()
        if auto_adjust_dependencies is None:
            return 1

    dependencies = _load_image_dependencies()
    if dependencies is None:
        return 1

    rawpy_module, imageio_module, pil_image_module = dependencies
    (
        source_exif_payload,
        source_exif_timestamp,
        source_orientation,
        source_exposure_time_seconds,
    ) = (
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
    post_gamma_text = (
        "auto"
        if postprocess_options.post_gamma_mode == "auto"
        else f"{postprocess_options.post_gamma:g}"
    )
    print_info(
        "Postprocess factors: "
        f"gamma={post_gamma_text}, "
        f"brightness={postprocess_options.brightness:g}, "
        f"contrast={postprocess_options.contrast:g}, "
        f"saturation={postprocess_options.saturation:g}, "
        f"jpg-compression={postprocess_options.jpg_compression}, "
        f"auto-brightness={'enabled' if postprocess_options.auto_brightness_enabled else 'disabled'}, "
        f"auto-levels={'enabled' if postprocess_options.auto_levels_enabled else 'disabled'}, "
        f"auto-adjust={'enabled' if postprocess_options.auto_adjust_enabled else 'disabled'}, "
        f"debug={'enabled' if postprocess_options.debug_enabled else 'disabled'}"
    )
    print_info(
        "RAW WB normalization: "
        f"mode={postprocess_options.raw_white_balance_mode}"
    )
    if postprocess_options.white_balance_mode is None:
        print_info("White-balance stage: disabled")
    else:
        print_info(
            "White-balance stage: "
            f"mode={postprocess_options.white_balance_mode}, "
            f"analysis-source={postprocess_options.white_balance_analysis_source}"
        )
    if postprocess_options.post_gamma_mode == "auto":
        print_info(
            "Post-gamma auto knobs: "
            f"target-gray={postprocess_options.post_gamma_auto_options.target_gray:g}, "
            f"luma-min={postprocess_options.post_gamma_auto_options.luma_min:g}, "
            f"luma-max={postprocess_options.post_gamma_auto_options.luma_max:g}, "
            f"lut-size={postprocess_options.post_gamma_auto_options.lut_size}"
        )
    if postprocess_options.auto_brightness_enabled:
        resolved_ab_key = postprocess_options.auto_brightness_options.key_value
        if resolved_ab_key is None:
            resolved_ab_key = "auto"
        print_info(
            "Auto-brightness knobs: "
            f"key-value={resolved_ab_key}, "
            f"white-point-pct={postprocess_options.auto_brightness_options.white_point_percentile:g}, "
            f"key-min={postprocess_options.auto_brightness_options.a_min:g}, "
            f"key-max={postprocess_options.auto_brightness_options.a_max:g}, "
            f"max-auto-boost={postprocess_options.auto_brightness_options.max_auto_boost_factor:g}, "
            "luminance-preserving-desat="
            f"{'enabled' if postprocess_options.auto_brightness_options.enable_luminance_preserving_desat else 'disabled'}, "
            f"eps={postprocess_options.auto_brightness_options.eps:g}"
        )
    if postprocess_options.auto_adjust_enabled:
        print_info(
            "Auto-adjust knobs: "
            f"blur-sigma={postprocess_options.auto_adjust_options.blur_sigma:g}, "
            f"blur-threshold-pct={postprocess_options.auto_adjust_options.blur_threshold_pct:g}, "
            f"level-low-pct={postprocess_options.auto_adjust_options.level_low_pct:g}, "
            f"level-high-pct={postprocess_options.auto_adjust_options.level_high_pct:g}, "
            "local-contrast="
            f"{'enabled' if postprocess_options.auto_adjust_options.enable_local_contrast else 'disabled'}, "
            f"local-contrast-strength={postprocess_options.auto_adjust_options.local_contrast_strength:g}, "
            f"clahe-clip-limit={postprocess_options.auto_adjust_options.clahe_clip_limit:g}, "
            "clahe-tile-grid-size="
            f"{postprocess_options.auto_adjust_options.clahe_tile_grid_size[0]}x"
            f"{postprocess_options.auto_adjust_options.clahe_tile_grid_size[1]}, "
            f"sigmoid-contrast={postprocess_options.auto_adjust_options.sigmoid_contrast:g}, "
            f"sigmoid-midpoint={postprocess_options.auto_adjust_options.sigmoid_midpoint:g}, "
            f"saturation-gamma={postprocess_options.auto_adjust_options.saturation_gamma:g}, "
            f"highpass-blur-sigma={postprocess_options.auto_adjust_options.highpass_blur_sigma:g}"
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
            f"HDR backend: {HDR_MERGE_MODE_OPENCV_MERGE} "
            f"(algorithm={opencv_merge_options.merge_algorithm}, "
            f"tonemap={'enabled' if opencv_merge_options.tonemap_enabled else 'disabled'}, "
            f"tonemapGamma={opencv_merge_options.tonemap_gamma:g})"
        )
    elif enable_opencv_tonemap:
        opencv_tonemap_options = postprocess_options.opencv_tonemap_options
        if opencv_tonemap_options is None:
            raise RuntimeError("Missing OpenCV-Tonemap selector configuration")
        if opencv_tonemap_options.tonemap_map == OPENCV_TONEMAP_MAP_DRAGO:
            tonemap_details = (
                f"drago-saturation={opencv_tonemap_options.drago_saturation:g}, "
                f"drago-bias={opencv_tonemap_options.drago_bias:g}"
            )
        elif opencv_tonemap_options.tonemap_map == OPENCV_TONEMAP_MAP_REINHARD:
            tonemap_details = (
                f"reinhard-intensity={opencv_tonemap_options.reinhard_intensity:g}, "
                f"reinhard-light_adapt={opencv_tonemap_options.reinhard_light_adapt:g}, "
                f"reinhard-color_adapt={opencv_tonemap_options.reinhard_color_adapt:g}"
            )
        else:
            tonemap_details = (
                f"mantiuk-scale={opencv_tonemap_options.mantiuk_scale:g}, "
                f"mantiuk-saturation={opencv_tonemap_options.mantiuk_saturation:g}"
            )
        print_info(
            f"HDR backend: {HDR_MERGE_MODE_OPENCV_TONEMAP} "
            f"(map={opencv_tonemap_options.tonemap_map}, gamma=1.0, {tonemap_details})"
        )
    elif enable_hdr_plus:
        print_info(
            "HDR backend: HDR+ "
            f"(proxy={hdrplus_options.proxy_mode}, "
            f"searchRadius={hdrplus_options.search_radius}, "
            f"temporalFactor={hdrplus_options.temporal_factor:g}, "
            f"temporalMinDist={hdrplus_options.temporal_min_dist:g}, "
            f"temporalMaxDist={hdrplus_options.temporal_max_dist:g}, "
            "reference=ev_zero, temporal=tile L1 inverse-distance, spatial=raised-cosine)"
        )
    processing_errors = _collect_processing_errors(rawpy_module)

    with tempfile.TemporaryDirectory(prefix="dng2jpg-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)

        try:
            with rawpy_module.imread(str(input_dng)) as raw_handle:
                source_gamma_info = _extract_source_gamma_info(raw_handle)
                bits_per_color = _detect_dng_bits_per_color(raw_handle)
                _validate_supported_bits_per_color(bits_per_color)
                base_rgb_float = None
                effective_ev_value = None
                print_info(_describe_source_gamma_info(source_gamma_info))
                exif_gamma_tags = _extract_exif_gamma_tags(
                    input_dng=input_dng,
                )
                print_info(_describe_exif_gamma_tags(exif_gamma_tags))
                merge_gamma_option = postprocess_options.merge_gamma_option
                if merge_gamma_option.mode == "auto":
                    print_info("Merge gamma request: auto")
                    resolved_merge_gamma = _resolve_auto_merge_gamma(
                        exif_gamma_tags=exif_gamma_tags,
                        source_gamma_info=source_gamma_info,
                    )
                else:
                    if (
                        merge_gamma_option.linear_coeff is None
                        or merge_gamma_option.exponent is None
                    ):
                        raise ValueError("Custom merge gamma request is incomplete")
                    print_info(
                        "Merge gamma request: custom "
                        f"linear_coeff={float(merge_gamma_option.linear_coeff):g}, "
                        f"exponent={float(merge_gamma_option.exponent):g}"
                    )
                    resolved_merge_gamma = ResolvedMergeGamma(
                        request=merge_gamma_option,
                        transfer="rec709",
                        label="Rec.709 custom",
                        param_a=float(merge_gamma_option.linear_coeff),
                        param_b=float(merge_gamma_option.exponent),
                        evidence="cli-custom",
                    )
                print_info(_describe_resolved_merge_gamma(resolved_merge_gamma))
                if auto_ev_enabled:
                    base_rgb_float = _extract_base_rgb_linear_float(
                        raw_handle=raw_handle,
                        np_module=numpy_module,
                        raw_white_balance_mode=postprocess_options.raw_white_balance_mode,
                    )
                    joint_solution = _resolve_joint_auto_ev_solution(
                        auto_ev_options=auto_ev_options,
                        auto_adjust_dependencies=auto_adjust_dependencies,
                        base_rgb_float=base_rgb_float,
                    )
                    resolved_ev_zero = joint_solution.ev_zero
                    effective_ev_value = joint_solution.ev_delta
                else:
                    if base_rgb_float is None:
                        base_rgb_float = _extract_base_rgb_linear_float(
                            raw_handle=raw_handle,
                            np_module=numpy_module,
                            raw_white_balance_mode=postprocess_options.raw_white_balance_mode,
                        )
                    evaluations = _calculate_auto_zero_evaluations(
                        cv2_module=None,
                        np_module=numpy_module,
                        image_rgb_float=base_rgb_float,
                    )
                    print_info(f"Exposure Misure EV ev_best: {evaluations.ev_best:+.1f} EV")
                    print_info(f"Exposure Misure EV ev_ettr: {evaluations.ev_ettr:+.1f} EV")
                    print_info(f"Exposure Misure EV ev_detail: {evaluations.ev_detail:+.1f} EV")
                    if ev_zero_specified:
                        resolved_ev_zero = ev_zero
                    else:
                        resolved_ev_zero, _selected_source = _select_ev_zero_candidate(
                            evaluations=evaluations,
                        )
                print_info(f"Detected DNG bits per color: {bits_per_color}")
                if auto_ev_enabled:
                    print_info("Using exposure mode: auto")
                    print_info(f"Using selected EV center (ev_zero): {resolved_ev_zero:g}")
                else:
                    print_info("Using exposure mode: static")
                    print_info(f"Using selected EV center (ev_zero): {resolved_ev_zero:g}")
                    if ev_value is None:
                        raise ValueError("Missing static EV value")
                    effective_ev_value = ev_value
                if effective_ev_value is None:
                    raise ValueError("Missing resolved EV delta")
                print_info(
                    f"Using EV bracket delta: {effective_ev_value:g}"
                    + (" (auto)" if auto_ev_enabled else " (static)")
                )
                print_info(
                    "Export EV triplet: "
                    f"{(resolved_ev_zero-effective_ev_value):g}, {resolved_ev_zero:g}, {(resolved_ev_zero+effective_ev_value):g}"
                )
                if enable_opencv and (
                    opencv_merge_options.merge_algorithm
                    in (
                        OPENCV_MERGE_ALGORITHM_DEBEVEC,
                        OPENCV_MERGE_ALGORITHM_ROBERTSON,
                    )
                ):
                    if source_exposure_time_seconds is None or source_exposure_time_seconds <= 0.0:
                        raise RuntimeError(
                            "OpenCV Debevec/Robertson requires valid source EXIF ExposureTime"
                        )
                    opencv_radiance_times = _build_opencv_radiance_exposure_times(
                        source_exposure_time_seconds=source_exposure_time_seconds,
                        ev_zero=resolved_ev_zero,
                        ev_delta=effective_ev_value,
                    )
                    print_info(
                        "OpenCV radiance EXIF exposure: "
                        f"{source_exposure_time_seconds:g} s"
                    )
                    print_info(
                        "OpenCV radiance exposure formula: "
                        "t_raw*2^(ev_zero-ev_delta), t_raw*2^ev_zero, t_raw*2^(ev_zero+ev_delta)"
                    )
                    print_info(
                        "OpenCV radiance exposure times [s]: "
                        f"{opencv_radiance_times[0]:g}, {opencv_radiance_times[1]:g}, {opencv_radiance_times[2]:g}"
                    )
                multipliers = _build_exposure_multipliers(
                    effective_ev_value, ev_zero=resolved_ev_zero
                )
                bracket_images_float = _extract_bracket_images_float(
                    raw_handle=raw_handle,
                    np_module=numpy_module,
                    multipliers=multipliers,
                    base_rgb_float=base_rgb_float,
                    raw_white_balance_mode=postprocess_options.raw_white_balance_mode,
                )
                if postprocess_options.white_balance_mode is not None:
                    if (
                        postprocess_options.white_balance_analysis_source
                        == WHITE_BALANCE_ANALYSIS_SOURCE_LINEAR_BASE
                    ):
                        if base_rgb_float is None:
                            raise RuntimeError(
                                "White-balance linear-base analysis requires extracted linear base"
                            )
                        white_balance_analysis_image_float = (
                            _build_white_balance_analysis_image_from_linear_base_float(
                                np_module=numpy_module,
                                base_rgb_float=base_rgb_float,
                                ev_zero=resolved_ev_zero,
                            )
                        )
                    elif (
                        postprocess_options.white_balance_analysis_source
                        == WHITE_BALANCE_ANALYSIS_SOURCE_EV_ZERO
                    ):
                        white_balance_analysis_image_float = bracket_images_float[1]
                    else:
                        raise ValueError(
                            "Unsupported --white-balance-analysis-source value: "
                            f"{postprocess_options.white_balance_analysis_source}"
                        )
                    bracket_images_float = _apply_white_balance_to_bracket_triplet(
                        bracket_images_float=bracket_images_float,
                        white_balance_mode=postprocess_options.white_balance_mode,
                        white_balance_analysis_image_float=white_balance_analysis_image_float,
                        auto_adjust_dependencies=auto_adjust_dependencies,
                    )
                if debug_context is not None:
                    extraction_suffixes = (
                        "_1.1_ev_min"
                        + _format_debug_ev_suffix_value(
                            resolved_ev_zero - effective_ev_value
                        ),
                        "_1.2_ev_zero"
                        + _format_debug_ev_suffix_value(resolved_ev_zero),
                        "_1.3_ev_max"
                        + _format_debug_ev_suffix_value(
                            resolved_ev_zero + effective_ev_value
                        ),
                    )
                    for stage_suffix, bracket_image_float in zip(
                        extraction_suffixes, bracket_images_float
                    ):
                        _write_debug_rgb_float_tiff(
                            imageio_module=imageio_module,
                            np_module=numpy_module,
                            debug_context=debug_context,
                            stage_suffix=stage_suffix,
                            image_rgb_float=bracket_image_float,
                        )
            if enable_luminance:
                merged_image_float = _run_luminance_hdr_cli(
                    bracket_images_float=bracket_images_float,
                    temp_dir=temp_dir,
                    imageio_module=imageio_module,
                    np_module=numpy_module,
                    ev_value=effective_ev_value,
                    ev_zero=resolved_ev_zero,
                    luminance_options=luminance_options,
                )
            elif enable_opencv:
                merged_image_float = _run_opencv_merge_backend(
                    bracket_images_float=bracket_images_float,
                    ev_value=effective_ev_value,
                    ev_zero=resolved_ev_zero,
                    source_exposure_time_seconds=source_exposure_time_seconds,
                    opencv_merge_options=opencv_merge_options,
                    auto_adjust_dependencies=auto_adjust_dependencies,
                    resolved_merge_gamma=resolved_merge_gamma,
                )
            elif enable_opencv_tonemap:
                if postprocess_options.opencv_tonemap_options is None:
                    raise RuntimeError("Missing OpenCV-Tonemap selector configuration")
                merged_image_float = _run_opencv_tonemap_backend(
                    bracket_images_float=bracket_images_float,
                    opencv_tonemap_options=postprocess_options.opencv_tonemap_options,
                    auto_adjust_dependencies=auto_adjust_dependencies,
                    resolved_merge_gamma=resolved_merge_gamma,
                )
            elif enable_hdr_plus:
                merged_image_float = _run_hdr_plus_merge(
                    bracket_images_float=bracket_images_float,
                    np_module=numpy_module,
                    hdrplus_options=hdrplus_options,
                    resolved_merge_gamma=resolved_merge_gamma,
                )
            else:
                raise RuntimeError("No HDR merge backend enabled")
            if debug_context is not None:
                _write_debug_rgb_float_tiff(
                    imageio_module=imageio_module,
                    np_module=numpy_module,
                    debug_context=debug_context,
                    stage_suffix="_2.0_hdr-merge",
                    image_rgb_float=merged_image_float,
                )
            _encode_jpg(
                imageio_module=imageio_module,
                pil_image_module=pil_image_module,
                merged_image_float=merged_image_float,
                output_jpg=output_jpg,
                postprocess_options=postprocess_options,
                auto_adjust_dependencies=auto_adjust_dependencies,
                numpy_module=numpy_module,
                piexif_module=piexif_module,
                source_exif_payload=source_exif_payload,
                source_orientation=source_orientation,
                debug_context=debug_context,
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
