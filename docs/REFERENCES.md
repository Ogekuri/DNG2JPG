# Files Structure
```
.
├── scripts
│   └── d2j.sh
└── src
    ├── dng2jpg
    │   ├── __init__.py
    │   ├── __main__.py
    │   ├── core.py
    │   └── dng2jpg.py
    └── shell_scripts
        ├── __init__.py
        └── utils.py
```

# d2j.sh | Shell | 83L | 6 symbols | 0 imports | 56 comments
> Path: `scripts/d2j.sh`

## Definitions

- var `FULL_PATH=$(readlink -f "$0")` (L19)
- var `SCRIPT_PATH=$(dirname "$FULL_PATH")` (L26)
- var `SCRIPT_NAME=$(basename "$FULL_PATH")` (L33)
- var `BASE_DIR=$(dirname "$SCRIPT_PATH")` (L39)
- var `PROJECT_ROOT=$(git -C "${BASE_DIR}" rev-parse --show-toplevel 2>/dev/null)` (L48)
- var `UV_TOOL="uv"` (L74)
## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`FULL_PATH`|var||19||
|`SCRIPT_PATH`|var||26||
|`SCRIPT_NAME`|var||33||
|`BASE_DIR`|var||39||
|`PROJECT_ROOT`|var||48||
|`UV_TOOL`|var||74||


---

# __init__.py | Python | 13L | 0 symbols | 1 imports | 7 comments
> Path: `src/dng2jpg/__init__.py`

## Imports
```
from .core import main  # noqa: F401
```


---

# __main__.py | Python | 11L | 0 symbols | 2 imports | 5 comments
> Path: `src/dng2jpg/__main__.py`

## Imports
```
from .core import main
import sys
```


---

# core.py | Python | 173L | 9 symbols | 14 imports | 3 comments
> Path: `src/dng2jpg/core.py`

## Imports
```
from __future__ import annotations
import sys
from pathlib import Path
from typing import Sequence
from . import __version__
from . import dng2jpg as ported
import json
import time
import json
import time
import json
from urllib import error, request
import platform
import subprocess
```

## Definitions

- var `PROGRAM = "dng2jpg"` (L14)
- var `OWNER = "Ogekuri"` (L15)
- var `REPOSITORY = "DNG2JPG"` (L16)
### fn `def _management_help() -> str` `priv` (L23-36)

### fn `def _write_version_cache(idle_delay_seconds: int) -> None` `priv` (L37-54)

### fn `def _should_skip_version_check(force: bool) -> bool` `priv` (L55-70)

### fn `def _check_online_version(force: bool) -> None` `priv` (L71-121)

### fn `def _run_management(command: list[str]) -> int` `priv` (L122-135)

### fn `def main(argv: Sequence[str] | None = None) -> int` (L136-173)

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`PROGRAM`|var|pub|14||
|`OWNER`|var|pub|15||
|`REPOSITORY`|var|pub|16||
|`_management_help`|fn|priv|23-36|def _management_help() -> str|
|`_write_version_cache`|fn|priv|37-54|def _write_version_cache(idle_delay_seconds: int) -> None|
|`_should_skip_version_check`|fn|priv|55-70|def _should_skip_version_check(force: bool) -> bool|
|`_check_online_version`|fn|priv|71-121|def _check_online_version(force: bool) -> None|
|`_run_management`|fn|priv|122-135|def _run_management(command: list[str]) -> int|
|`main`|fn|pub|136-173|def main(argv: Sequence[str] | None = None) -> int|


---

# dng2jpg.py | Python | 6173L | 195 symbols | 23 imports | 130 comments
> Path: `src/dng2jpg/dng2jpg.py`

## Imports
```
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
import rawpy  # type: ignore
import imageio.v3 as imageio  # type: ignore
import imageio  # type: ignore
from PIL import Image as pil_image  # type: ignore
import numpy as np_module  # type: ignore
from numpy.lib.stride_tricks import sliding_window_view  # type: ignore
import cv2  # type: ignore
import numpy as numpy_module  # type: ignore
import numpy as numpy_module  # type: ignore
import piexif  # type: ignore
import numpy as np_module  # type: ignore
import cv2 as cv2_module  # type: ignore
```

## Definitions

- var `PROGRAM = "dng2jpg"` (L31)
- var `DESCRIPTION = "Convert DNG to HDR-merged JPG with enfuse, luminance-hdr-cli, OpenCV, or HDR+ backend."` (L32)
- var `DEFAULT_GAMMA = (2.222, 4.5)` (L33)
- var `DEFAULT_POST_GAMMA = 1.0` (L34)
- var `DEFAULT_BRIGHTNESS = 1.0` (L35)
- var `DEFAULT_CONTRAST = 1.0` (L36)
- var `DEFAULT_SATURATION = 1.0` (L37)
- var `DEFAULT_JPG_COMPRESSION = 15` (L38)
- var `DEFAULT_AUTO_ZERO_PCT = 50.0` (L39)
- var `DEFAULT_AUTO_EV_PCT = 50.0` (L40)
- var `DEFAULT_AA_BLUR_SIGMA = 0.9` (L41)
- var `DEFAULT_AA_BLUR_THRESHOLD_PCT = 5.0` (L42)
- var `DEFAULT_AA_LEVEL_LOW_PCT = 0.1` (L43)
- var `DEFAULT_AA_LEVEL_HIGH_PCT = 99.9` (L44)
- var `DEFAULT_AA_SIGMOID_CONTRAST = 1.8` (L45)
- var `DEFAULT_AA_SIGMOID_MIDPOINT = 0.5` (L46)
- var `DEFAULT_AA_SATURATION_GAMMA = 0.8` (L47)
- var `DEFAULT_AA_HIGHPASS_BLUR_SIGMA = 2.0` (L48)
- var `DEFAULT_AB_KEY_VALUE = None` (L49)
- var `DEFAULT_AB_WHITE_POINT_PERCENTILE = 99.8` (L50)
- var `DEFAULT_AB_KEY_MIN = 0.045` (L51)
- var `DEFAULT_AB_KEY_MAX = 0.72` (L52)
- var `DEFAULT_AB_MAX_AUTO_BOOST_FACTOR = 1.25` (L53)
- var `DEFAULT_AB_LOCAL_CONTRAST_STRENGTH = 0.20` (L54)
- var `DEFAULT_AB_CLAHE_CLIP_LIMIT = 1.6` (L55)
- var `DEFAULT_AB_CLAHE_TILE_GRID_SIZE = (8, 8)` (L56)
- var `DEFAULT_AB_EPS = 1e-6` (L57)
- var `DEFAULT_AB_LOW_KEY_VALUE = 0.09` (L58)
- var `DEFAULT_AB_NORMAL_KEY_VALUE = 0.18` (L59)
- var `DEFAULT_AB_HIGH_KEY_VALUE = 0.36` (L60)
- var `DEFAULT_AL_CLIP_PERCENT = 0.02` (L61)
- var `DEFAULT_AL_HISTCOMPR = 3` (L62)
- var `DEFAULT_LUMINANCE_HDR_MODEL = "debevec"` (L68)
- var `DEFAULT_LUMINANCE_HDR_WEIGHT = "flat"` (L69)
- var `DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE = "srgb"` (L70)
- var `DEFAULT_LUMINANCE_TMO = "mantiuk08"` (L71)
- var `DEFAULT_REINHARD02_BRIGHTNESS = 1.25` (L72)
- var `DEFAULT_REINHARD02_CONTRAST = 0.85` (L73)
- var `DEFAULT_REINHARD02_SATURATION = 0.55` (L74)
- var `DEFAULT_MANTIUK08_CONTRAST = 1.2` (L75)
- var `DEFAULT_OPENCV_DEBEVEC_WHITE_POINT_PERCENTILE = 99.5` (L76)
- var `HDRPLUS_TILE_SIZE = 32` (L77)
- var `HDRPLUS_TILE_STRIDE = HDRPLUS_TILE_SIZE // 2` (L78)
- var `HDRPLUS_DOWNSAMPLED_TILE_SIZE = HDRPLUS_TILE_STRIDE` (L79)
- var `HDRPLUS_TEMPORAL_FACTOR = 8.0` (L80)
- var `HDRPLUS_TEMPORAL_MIN_DIST = 10` (L81)
- var `HDRPLUS_TEMPORAL_MAX_DIST = 300` (L82)
- var `EV_STEP = 0.25` (L83)
- var `MIN_SUPPORTED_BITS_PER_COLOR = 9` (L84)
- var `DEFAULT_DNG_BITS_PER_COLOR = 14` (L85)
- var `SUPPORTED_EV_VALUES = tuple(` (L86)
- var `AUTO_EV_LOW_PERCENTILE = 0.1` (L92)
- var `AUTO_EV_HIGH_PERCENTILE = 99.9` (L93)
- var `AUTO_EV_MEDIAN_PERCENTILE = 50.0` (L94)
- var `AUTO_EV_TARGET_SHADOW = 0.05` (L95)
- var `AUTO_EV_TARGET_HIGHLIGHT = 0.90` (L96)
- var `AUTO_EV_MEDIAN_TARGET = 0.5` (L97)
- var `AUTO_ZERO_SCENE_KEY_LOW_THRESHOLD = 0.35` (L98)
- var `AUTO_ZERO_SCENE_KEY_HIGH_THRESHOLD = 0.65` (L99)
- var `AUTO_ZERO_TARGET_LOW_KEY = 0.35` (L100)
- var `AUTO_ZERO_TARGET_HIGH_KEY = 0.65` (L101)
### class `class AutoAdjustOptions` `@dataclass(frozen=True)` (L285-312)
- @brief Hold shared auto-adjust knob values used by ImageMagick and OpenCV.
- @details Encapsulates validated knob values consumed by both auto-adjust implementations so both pipelines remain numerically aligned and backward compatible when no explicit overrides are provided.
- @param blur_sigma {float} Selective blur Gaussian sigma (`> 0`).
- @param blur_threshold_pct {float} Selective blur threshold percentage in `[0, 100]`.
- @param level_low_pct {float} Low percentile for level normalization in `[0, 100]`.
- @param level_high_pct {float} High percentile for level normalization in `[0, 100]`.
- @param sigmoid_contrast {float} Sigmoidal contrast slope (`> 0`).
- @param sigmoid_midpoint {float} Sigmoidal contrast midpoint in `[0, 1]`.
- @param saturation_gamma {float} HSL saturation gamma denominator (`> 0`).
- @param highpass_blur_sigma {float} High-pass Gaussian blur sigma (`> 0`).
- @return {None} Immutable dataclass container.
- @satisfies REQ-073, REQ-075, REQ-082, REQ-083, REQ-084, REQ-086, REQ-087

### class `class AutoBrightnessOptions` `@dataclass(frozen=True)` (L314-344)
- @brief Hold `--auto-brightness` knob values.
- @details Encapsulates parameters for the 16-bit BT.709 photographic tonemap pipeline: key-classification, key-value selection, robust white point, luminance-preserving anti-clipping desaturation, and optional mild CLAHE micro-contrast blending in the Y channel.
- @param key_value {float|None} Manual Reinhard key value override in `(0, +inf)`; `None` enables automatic key selection.
- @param white_point_percentile {float} Percentile in `(0, 100)` used to derive robust `Lwhite`.
- @param key_min {float} Minimum allowed key value clamp in `(0, +inf)`.
- @param key_max {float} Maximum allowed key value clamp in `(0, +inf)`.
- @param max_auto_boost_factor {float} Multiplicative adjustment factor for automatic key adaptation in `(0, +inf)`.
- @param local_contrast_strength {float} CLAHE blend factor in `[0, 1]`.
- @param clahe_clip_limit {float} OpenCV CLAHE clip limit in `(0, +inf)`.
- @param clahe_tile_grid_size {tuple[int, int]} OpenCV CLAHE tile grid size `(rows, cols)`, each `>=1`.
- @param eps {float} Positive numerical stability guard used in divisions and logarithms.
- @return {None} Immutable dataclass container.
- @satisfies REQ-050, REQ-065, REQ-088, REQ-089, REQ-090, REQ-103, REQ-104, REQ-105

### class `class AutoLevelsOptions` `@dataclass(frozen=True)` (L346-365)
- @brief Hold `--auto-levels` knob values.
- @details Encapsulates validated histogram-based auto-levels controls ported from the attached RawTherapee-oriented source and adapted for RGB uint16 stage execution in the current post-merge pipeline.
- @param clip_percent {float} Histogram clipping percentage in `[0, +inf)`.
- @param histcompr {int} Histogram compression shift in `[0, 15]`.
- @param highlight_reconstruction_enabled {bool} `True` when highlight reconstruction is enabled.
- @param highlight_reconstruction_method {str|None} Highlight reconstruction method (`Luminance`, `CIELab blending`, `Blend`) when enabled.
- @return {None} Immutable dataclass container.
- @satisfies REQ-100, REQ-101, REQ-102

### class `class PostprocessOptions` `@dataclass(frozen=True)` (L367-401)
- @brief Hold deterministic postprocessing option values.
- @details Encapsulates correction factors and JPEG compression level used by shared TIFF-to-JPG postprocessing for both HDR backends.
- @param post_gamma {float} Gamma correction factor for postprocessing stage.
- @param brightness {float} Brightness enhancement factor.
- @param contrast {float} Contrast enhancement factor.
- @param saturation {float} Saturation enhancement factor.
- @param jpg_compression {int} JPEG compression level in range `[0, 100]`.
- @param auto_brightness_enabled {bool} `True` when auto-brightness pre-stage is enabled.
- @param auto_brightness_options {AutoBrightnessOptions} Auto-brightness stage knobs.
- @param auto_levels_enabled {bool} `True` when auto-levels stage is enabled.
- @param auto_levels_options {AutoLevelsOptions} Auto-levels stage knobs.
- @param auto_adjust_mode {str|None} Optional auto-adjust implementation selector (`ImageMagick` or `OpenCV`).
- @param auto_adjust_options {AutoAdjustOptions} Shared auto-adjust knobs for `ImageMagick` and `OpenCV` implementations.
- @return {None} Immutable dataclass container.
- @satisfies REQ-050, REQ-065, REQ-066, REQ-069, REQ-071, REQ-072, REQ-073, REQ-075, REQ-082, REQ-083, REQ-084, REQ-086, REQ-087, REQ-088, REQ-089, REQ-090, REQ-100, REQ-101, REQ-102, REQ-103, REQ-104, REQ-105

### class `class LuminanceOptions` `@dataclass(frozen=True)` (L403-423)
- @brief Hold deterministic luminance-hdr-cli option values.
- @details Encapsulates luminance backend model and tone-mapping parameters forwarded to `luminance-hdr-cli` command generation.
- @param hdr_model {str} Luminance HDR model (`--hdrModel`).
- @param hdr_weight {str} Luminance weighting function (`--hdrWeight`).
- @param hdr_response_curve {str} Luminance response curve (`--hdrResponseCurve`).
- @param tmo {str} Tone-mapping operator (`--tmo`).
- @param tmo_extra_args {tuple[str, ...]} Explicit passthrough `--tmo*` option pairs in CLI order.
- @return {None} Immutable dataclass container.
- @satisfies REQ-061, REQ-067, REQ-068

### class `class OpenCvMergeOptions` `@dataclass(frozen=True)` (L425-439)
- @brief Hold deterministic OpenCV HDR merge option values.
- @details Encapsulates OpenCV merge controls used by the `--enable-opencv` backend. The backend computes exposure fusion (`MergeMertens`) and radiance merge (`MergeDebevec`) from the same uint16 bracket TIFF set, then blends both outputs in float domain before one uint16 conversion.
- @param debevec_white_point_percentile {float} Percentile in `(0, 100)` used to derive robust white-point normalization from Debevec luminance.
- @return {None} Immutable dataclass container.
- @satisfies REQ-108, REQ-109, REQ-110

### class `class AutoEvInputs` `@dataclass(frozen=True)` (L441-468)
- @brief Hold adaptive EV optimization scalar inputs.
- @details Stores normalized luminance percentiles and thresholds for deterministic adaptive EV optimization. The optimization function uses these scalar values to compute one clamped EV delta for bracket generation.
- @param p_low {float} Luminance at low percentile bound in `[0.0, 1.0]`.
- @param p_median {float} Median luminance in `[0.0, 1.0]`.
- @param p_high {float} Luminance at high percentile bound in `[0.0, 1.0]`.
- @param target_shadow {float} Target lower luminance guardrail in `(0.0, 1.0)`.
- @param target_highlight {float} Target upper luminance guardrail in `(0.0, 1.0)`.
- @param median_target {float} Preferred median-centered luminance target in `(0.0, 1.0)`.
- @param ev_zero {float} Resolved EV-zero center used as adaptive solver anchor.
- @param ev_values {tuple[float, ...]} Supported EV selector values derived from source DNG bit depth.
- @return {None} Immutable scalar container.
- @satisfies REQ-080, REQ-081, REQ-092, REQ-093, REQ-095, REQ-098

### fn `def _print_box_table(headers, rows, header_rows=())` `priv` (L469-505)
- @brief Print one Unicode box-drawing table.
- @details Computes deterministic column widths from headers and rows, then prints aligned borders and cells using Unicode line-drawing glyphs.
- @param headers {tuple[str, ...]} Table header labels in fixed output order.
- @param header_rows {tuple[tuple[str, ...], ...]} Additional physical header rows rendered before header/body separator.
- @param rows {tuple[tuple[str, ...], ...]} Table body rows with one value per column.
- @return {None} Writes formatted table to stdout.
- @satisfies REQ-070

### fn `def _border(left, middle, right)` `priv` (L489-491)
- @brief Print one Unicode box-drawing table.
- @details Computes deterministic column widths from headers and rows, then
prints aligned borders and cells using Unicode line-drawing glyphs.
- @param headers {tuple[str, ...]} Table header labels in fixed output order.
- @param header_rows {tuple[tuple[str, ...], ...]} Additional physical header rows rendered before header/body separator.
- @param rows {tuple[tuple[str, ...], ...]} Table body rows with one value per column.
- @return {None} Writes formatted table to stdout.
- @satisfies REQ-070

### fn `def _line(values)` `priv` (L492-495)

### fn `def _build_two_line_operator_rows(operator_entries)` `priv` (L506-522)
- @brief Build two-line physical rows for luminance operator table.
- @details Expands each logical operator entry into two physical rows while preserving the bordered three-column layout used by help rendering.
- @param operator_entries {tuple[tuple[str, str, str, str, str], ...]} Logical operator rows in `(operator, family, character, neutrality, when_to_use)` format.
- @return {tuple[tuple[str, str, str], ...]} Expanded physical rows for `_print_box_table`.
- @satisfies REQ-070

### fn `def print_help(version)` (L523-722)
- @brief Print help text for the `dng2jpg` command.
- @details Documents required positional arguments, required mutually exclusive exposure selectors (`--ev` or `--auto-ev`), optional RAW gamma controls, optional `--ev-zero` and `--auto-zero` selectors, shared postprocessing controls, backend selection including HDR+, and luminance-hdr-cli tone-mapping options.
- @param version {str} CLI version label to append in usage output.
- @return {None} Writes help text to stdout.
- @satisfies DES-008, REQ-056, REQ-063, REQ-069, REQ-070, REQ-071, REQ-072, REQ-073, REQ-075, REQ-082, REQ-083, REQ-084, REQ-088, REQ-089, REQ-090, REQ-091, REQ-094, REQ-097, REQ-100, REQ-101, REQ-102, REQ-111

### fn `def _calculate_max_ev_from_bits(bits_per_color)` `priv` (L770-788)
- @brief Compute EV ceiling from detected DNG bits per color.
- @details Implements `MAX=((bits_per_color-8)/2)` and validates minimum supported bit depth before computing clamp ceiling used by static and adaptive EV flows.
- @param bits_per_color {int} Detected source DNG bits per color.
- @return {float} Bit-derived EV ceiling.
- @exception ValueError Raised when bit depth is below supported minimum.
- @satisfies REQ-057, REQ-081, REQ-093, REQ-094, REQ-096

### fn `def _calculate_safe_ev_zero_max(base_max_ev)` `priv` (L789-801)
- @brief Compute safe absolute EV-zero ceiling preserving at least `±1EV` bracket.
- @details Derives `SAFE_ZERO_MAX=(BASE_MAX-1)` where `BASE_MAX=((bits_per_color-8)/2)`. Safe range guarantees `MAX_BRACKET=(BASE_MAX-abs(ev_zero)) >= 1`.
- @param base_max_ev {float} Bit-derived `BASE_MAX` value.
- @return {float} Safe absolute EV-zero ceiling.
- @satisfies REQ-093, REQ-094, REQ-096, REQ-097

### fn `def _derive_supported_ev_zero_values(base_max_ev)` `priv` (L802-818)
- @brief Derive non-negative EV-zero quantization set preserving `±1EV` bracket.
- @details Generates deterministic quarter-step tuple in `[0, SAFE_ZERO_MAX]`, where `SAFE_ZERO_MAX=max(0, BASE_MAX-1)` and `BASE_MAX=((bits_per_color-8)/2)`.
- @param base_max_ev {float} Bit-derived `BASE_MAX` value.
- @return {tuple[float, ...]} Supported non-negative EV-zero magnitudes including `0.0`.
- @satisfies REQ-093, REQ-094, REQ-096, REQ-097

### fn `def _derive_supported_ev_values(bits_per_color, ev_zero=0.0)` `priv` (L819-847)
- @brief Derive valid bracket EV selector set from bit depth and `ev_zero`.
- @details Builds deterministic EV selector tuple with fixed `0.25` step in closed range `[0.25, MAX_BRACKET]`, where `MAX_BRACKET=((bits_per_color-8)/2)-abs(ev_zero)`.
- @param bits_per_color {int} Detected source DNG bits per color.
- @param ev_zero {float} Central EV selector.
- @return {tuple[float, ...]} Supported bracket EV selector tuple.
- @exception ValueError Raised when bit-derived bracket EV ceiling cannot produce any selector values.
- @satisfies REQ-057, REQ-081, REQ-093, REQ-094, REQ-096

### fn `def _detect_dng_bits_per_color(raw_handle)` `priv` (L848-893)
- @brief Detect source DNG bits-per-color from RAW metadata.
- @details Prefers RAW sample container bit depth from `raw_handle.raw_image_visible.dtype.itemsize * 8` because the DNG white level can represent effective sensor range (for example `4000`) while RAW samples are still stored in a wider container (for example `uint16`). Falls back to `raw_handle.white_level` `bit_length` when container metadata is unavailable.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {int} Detected source DNG bits per color.
- @exception ValueError Raised when metadata is missing, non-numeric, or non-positive.
- @satisfies REQ-057, REQ-081, REQ-092, REQ-093

### fn `def _is_ev_value_on_supported_step(ev_value)` `priv` (L894-907)
- @brief Validate EV value belongs to fixed `0.25` step grid.
- @details Checks whether EV value can be represented as integer multiples of `0.25` using tolerance-based floating-point comparison.
- @param ev_value {float} Parsed EV numeric value.
- @return {bool} `True` when EV value is aligned to `0.25` step.
- @satisfies REQ-057

### fn `def _parse_ev_option(ev_raw)` `priv` (L908-939)
- @brief Parse and validate one EV option value.
- @details Converts token to `float`, enforces minimum `0.25`, and enforces fixed `0.25` granularity. Bit-depth upper-bound validation is deferred until RAW metadata is loaded from source DNG.
- @param ev_raw {str} EV token extracted from command arguments.
- @return {float|None} Parsed EV value when valid; `None` otherwise.
- @satisfies REQ-056, REQ-057

### fn `def _parse_ev_zero_option(ev_zero_raw)` `priv` (L940-970)
- @brief Parse and validate one `--ev-zero` option value.
- @details Converts token to `float`, enforces fixed `0.25` granularity, and defers bit-depth bound validation to RAW-metadata runtime stage.
- @param ev_zero_raw {str} EV-zero token extracted from command arguments.
- @return {float|None} Parsed EV-zero value when valid; `None` otherwise.
- @satisfies REQ-094

### fn `def _parse_auto_ev_option(auto_ev_raw)` `priv` (L971-988)
- @brief Parse and validate one `--auto-ev` option value.
- @details Accepts only boolean-like activator tokens (`1`, `true`, `yes`, `on`) and rejects all other values to keep deterministic CLI behavior.
- @param auto_ev_raw {str} Raw `--auto-ev` value token from CLI args.
- @return {bool|None} `True` when token enables adaptive mode; `None` on parse failure.
- @satisfies REQ-056

### fn `def _parse_auto_zero_option(auto_zero_raw)` `priv` (L989-1006)
- @brief Parse and validate one `--auto-zero` option value.
- @details Accepts only boolean-like activator tokens (`1`, `true`, `yes`, `on`) and rejects all other values to keep deterministic CLI behavior.
- @param auto_zero_raw {str} Raw `--auto-zero` value token from CLI args.
- @return {bool|None} `True` when token enables automatic EV-zero mode; `None` on parse failure.
- @satisfies REQ-094

### fn `def _parse_percentage_option(option_name, option_raw)` `priv` (L1007-1029)
- @brief Parse and validate one percentage option value.
- @details Converts option token to `float`, requires inclusive range `[0, 100]`, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {float|None} Parsed percentage value when valid; `None` otherwise.
- @satisfies REQ-081, REQ-094, REQ-097

### fn `def _parse_auto_brightness_option(auto_brightness_raw)` `priv` (L1030-1047)
- @brief Parse and validate one `--auto-brightness` option value.
- @details Accepts only boolean-like activator tokens (`1`, `true`, `yes`, `on`) and rejects all other values to keep deterministic CLI behavior.
- @param auto_brightness_raw {str} Raw `--auto-brightness` value token from CLI args.
- @return {bool|None} `True` when token enables auto-brightness; `None` on parse failure.
- @satisfies REQ-065, REQ-089

### fn `def _parse_auto_levels_option(auto_levels_raw)` `priv` (L1048-1065)
- @brief Parse and validate one `--auto-levels` option value.
- @details Accepts only boolean-like activator tokens (`1`, `true`, `yes`, `on`) and rejects all other values to keep deterministic CLI behavior.
- @param auto_levels_raw {str} Raw `--auto-levels` value token from CLI args.
- @return {bool|None} `True` when token enables auto-levels; `None` on parse failure.
- @satisfies REQ-100, REQ-101

### fn `def _clamp_ev_to_supported(ev_candidate, ev_values)` `priv` (L1066-1079)
- @brief Clamp one EV candidate to supported numeric interval.
- @details Applies lower/upper bound clamp to keep computed adaptive EV value inside configured EV bounds before command generation.
- @param ev_candidate {float} Candidate EV delta from adaptive optimization.
- @param ev_values {tuple[float, ...]} Sorted supported EV selector values.
- @return {float} Clamped EV delta in `[min(ev_values), max(ev_values)]`.
- @satisfies REQ-081, REQ-093

### fn `def _quantize_ev_to_supported(ev_value, ev_values)` `priv` (L1080-1101)
- @brief Quantize one EV value to nearest supported selector value.
- @details Chooses nearest value from `ev_values` to preserve deterministic three-bracket behavior in downstream static multiplier and HDR command construction paths.
- @param ev_value {float} Clamped EV value.
- @param ev_values {tuple[float, ...]} Sorted supported EV selector values.
- @return {float} Nearest supported EV selector value.
- @satisfies REQ-080, REQ-081, REQ-093

### fn `def _quantize_ev_toward_zero_step(ev_value, step=EV_STEP)` `priv` (L1102-1123)
- @brief Quantize one EV value toward zero using fixed step size.
- @details Converts EV value to step units, truncates fractional remainder toward zero, and reconstructs signed EV value using deterministic `0.25` precision rounding.
- @param ev_value {float} EV value to quantize.
- @param step {float} Quantization step size.
- @return {float} Quantized EV value with truncation toward zero.
- @satisfies REQ-081, REQ-097

### fn `def _apply_auto_percentage_scaling(ev_value, percentage)` `priv` (L1124-1138)
- @brief Apply percentage scaling to EV value with downward 0.25 quantization.
- @details Multiplies EV value by percentage in `[0,100]` and quantizes scaled result toward zero with fixed `0.25` step.
- @param ev_value {float} EV value before scaling.
- @param percentage {float} Percentage scaling factor in `[0,100]`.
- @return {float} Scaled EV value quantized toward zero.
- @satisfies REQ-081, REQ-097

### fn `def _extract_normalized_preview_luminance_stats(raw_handle)` `priv` (L1139-1198)
- @brief Extract normalized preview luminance percentiles from RAW handle.
- @details Generates one deterministic linear preview (`bright=1.0`, `output_bps=16`, camera white balance, no auto-bright, linear gamma, `user_flip=0`), computes luminance for each pixel, then returns normalized low/median/high percentiles by dividing with preview maximum luminance.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {tuple[float, float, float]} Normalized `(p_low, p_median, p_high)` in `(0,1)`.
- @exception ValueError Raised when preview extraction cannot produce valid luminance values.
- @satisfies REQ-080, REQ-081, REQ-092, REQ-093, REQ-097

### fn `def _percentile(percentile_value)` `priv` (L1173-1183)
- @brief Extract normalized preview luminance percentiles from RAW handle.
- @details Generates one deterministic linear preview (`bright=1.0`,
`output_bps=16`, camera white balance, no auto-bright, linear gamma,
`user_flip=0`), computes luminance for each pixel, then returns normalized
low/median/high percentiles by dividing with preview maximum luminance.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {tuple[float, float, float]} Normalized `(p_low, p_median, p_high)` in `(0,1)`.
- @exception ValueError Raised when preview extraction cannot produce valid luminance values.
- @satisfies REQ-080, REQ-081, REQ-092, REQ-093, REQ-097

### fn `def _coerce_positive_luminance(value, fallback)` `priv` (L1199-1218)
- @brief Coerce luminance scalar to positive range for logarithmic math.
- @details Converts input to float and enforces a strictly positive minimum. Returns fallback when conversion fails or result is non-positive.
- @param value {object} Candidate luminance scalar.
- @param fallback {float} Fallback positive luminance scalar.
- @return {float} Positive luminance value suitable for `log2`.
- @satisfies REQ-081

### fn `def _derive_scene_key_preserving_median_target(p_median)` `priv` (L1219-1237)
- @brief Derive scene-key-preserving median target for auto-zero optimization.
- @details Classifies scene key from normalized preview median luminance and maps it to a bounded median target preserving low-key/high-key intent while enabling exposure correction. Low-key medians map to a low-key target, high-key medians map to a high-key target, and mid-key medians map to neutral target `0.5`.
- @param p_median {float} Normalized median luminance in `(0.0, 1.0)`.
- @return {float} Scene-key-preserving median target in `(0.0, 1.0)`.
- @satisfies REQ-097, REQ-098

### fn `def _optimize_auto_zero(auto_ev_inputs)` `priv` (L1238-1261)
- @brief Compute optimal EV-zero center from normalized luminance statistics.
- @details Solves `ev_zero=log2(target_median/p_median)` using a scene-key-preserving target derived from preview median luminance, clamps result to `[-SAFE_ZERO_MAX,+SAFE_ZERO_MAX]` where `SAFE_ZERO_MAX=max(ev_values)`, and quantizes to nearest quarter-step represented by `ev_values` with sign preservation.
- @param auto_ev_inputs {AutoEvInputs} Adaptive EV scalar inputs.
- @return {float} Quantized EV-zero center.
- @satisfies REQ-094, REQ-095, REQ-097, REQ-098

### fn `def _optimize_adaptive_ev_delta(auto_ev_inputs)` `priv` (L1262-1291)
- @brief Compute adaptive EV delta from preview luminance statistics.
- @details Computes symmetric delta constraints around resolved EV-zero: `ev_shadow=max(0, log2(target_shadow/p_low)-ev_zero)` and `ev_high=max(0, ev_zero-log2(target_highlight/p_high))`, chooses maximum as safe symmetric bracket half-width, then clamps and quantizes to supported EV selector set.
- @param auto_ev_inputs {AutoEvInputs} Adaptive EV scalar inputs.
- @return {float} Quantized adaptive EV delta.
- @satisfies REQ-080, REQ-081, REQ-093, REQ-095

### fn `def _compute_auto_ev_value_from_stats(` `priv` (L1292-1297)

### fn `def _compute_auto_ev_value(raw_handle, supported_ev_values=None, ev_zero=0.0)` `priv` (L1325-1352)
- @brief Compute adaptive EV selector from normalized preview luminance stats.
- @brief Compute adaptive EV selector from RAW linear preview histogram.
- @details Builds adaptive-EV input container from already extracted normalized
percentiles and solves symmetric EV delta around resolved `ev_zero`.
- @details Extracts normalized luminance percentiles (`0.1`, `50.0`, `99.9`) from one linear RAW preview and computes symmetric adaptive EV delta around resolved `ev_zero`, then clamps and quantizes to bit-depth-derived selector bounds.
- @param p_low {float} Normalized low percentile luminance.
- @param p_median {float} Normalized median percentile luminance.
- @param p_high {float} Normalized high percentile luminance.
- @param supported_ev_values {tuple[float, ...]} Bit-depth-derived supported EV selector tuple.
- @param ev_zero {float} Resolved EV-zero center used as adaptive solver anchor.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @param supported_ev_values {tuple[float, ...]|None} Optional bit-derived EV selector tuple.
- @param ev_zero {float} Resolved EV-zero center used as adaptive solver anchor.
- @return {float} Adaptive EV selector value from bit-depth-derived selector set.
- @return {float} Adaptive EV selector value from bit-depth-derived selector set.
- @exception ValueError Raised when preview luminance extraction cannot produce valid values.
- @satisfies REQ-080, REQ-081, REQ-093, REQ-095
- @satisfies REQ-080, REQ-081, REQ-092, REQ-093, REQ-095, REQ-096

### fn `def _resolve_ev_zero(` `priv` (L1353-1360)

### fn `def _resolve_ev_value(` `priv` (L1411-1418)
- @brief Resolve EV-zero center from manual or automatic selector.
- @details Uses manual `--ev-zero` unless `--auto-zero` is enabled. In
automatic mode computes EV-zero from normalized median luminance and
quantizes to supported quarter-step values. Applies final safe-range clamp
preserving at least `±1EV` bracket margin.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @param ev_zero {float} Parsed manual EV-zero candidate.
- @param auto_zero_enabled {bool} Auto-zero selector state.
- @param auto_zero_pct {float} Percentage scaler applied to computed auto-zero result.
- @param base_max_ev {float} Bit-derived `BASE_MAX` limit.
- @param supported_ev_values_for_auto_zero {tuple[float, ...]} Supported non-negative EV-zero magnitudes for quantization.
- @param preview_luminance_stats {tuple[float, float, float]|None} Optional precomputed `(p_low, p_median, p_high)` tuple to avoid duplicate preview extraction.
- @return {float} Resolved EV-zero center.
- @exception ValueError Raised when resolved EV-zero is outside bit-derived safe range.
- @satisfies REQ-094, REQ-095, REQ-097, REQ-098

### fn `def _parse_luminance_text_option(option_name, option_raw)` `priv` (L1471-1491)
- @brief Resolve effective EV selector for static or adaptive mode.
- @brief Parse and validate non-empty luminance string option value.
- @details Returns explicit static `--ev` value when adaptive mode is not
enabled and validates it against bit-derived supported EV selectors. In
adaptive mode, computes EV from RAW linear preview statistics.
- @details Normalizes surrounding spaces, lowercases token, rejects empty values, and rejects ambiguous values that start with option prefix marker.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @param ev_value {float|None} Parsed static EV option value.
- @param auto_ev_enabled {bool} Adaptive mode selector state.
- @param auto_ev_pct {float} Percentage scaler applied to computed adaptive EV delta.
- @param supported_ev_values {tuple[float, ...]|None} Optional bit-derived EV selector tuple.
- @param ev_zero {float} Resolved EV-zero center used for adaptive EV solver anchoring.
- @param preview_luminance_stats {tuple[float, float, float]|None} Optional precomputed `(p_low, p_median, p_high)` tuple to avoid duplicate preview extraction.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {float} Effective EV selector value used for bracket multipliers.
- @return {str|None} Parsed normalized option token when valid; `None` otherwise.
- @exception ValueError Raised when no static EV is provided while adaptive mode is disabled.
- @satisfies REQ-056, REQ-057, REQ-080, REQ-081, REQ-092, REQ-093, REQ-095, REQ-096
- @satisfies REQ-061

### fn `def _parse_gamma_option(gamma_raw)` `priv` (L1492-1528)
- @brief Parse and validate one gamma option value pair.
- @details Accepts comma-separated positive float pair in `a,b` format with optional surrounding parentheses, normalizes to `(a, b)` tuple, and rejects malformed, non-numeric, or non-positive values.
- @param gamma_raw {str} Raw gamma token extracted from CLI args.
- @return {tuple[float, float]|None} Parsed gamma tuple when valid; `None` otherwise.
- @satisfies REQ-064

### fn `def _parse_positive_float_option(option_name, option_raw)` `priv` (L1529-1552)
- @brief Parse and validate one positive float option value.
- @details Converts option token to `float`, requires value greater than zero, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {float|None} Parsed positive float value when valid; `None` otherwise.
- @satisfies REQ-065

### fn `def _parse_tmo_passthrough_value(option_name, option_raw)` `priv` (L1553-1569)
- @brief Parse and validate one luminance `--tmo*` passthrough value.
- @details Rejects empty values and preserves original payload for transparent forwarding to `luminance-hdr-cli`.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {str|None} Original value when valid; `None` otherwise.
- @satisfies REQ-067

### fn `def _parse_jpg_compression_option(compression_raw)` `priv` (L1570-1592)
- @brief Parse and validate JPEG compression option value.
- @details Converts option token to `int`, requires inclusive range `[0, 100]`, and emits deterministic parse errors on malformed values.
- @param compression_raw {str} Raw compression token value from CLI args.
- @return {int|None} Parsed JPEG compression level when valid; `None` otherwise.
- @satisfies REQ-065

### fn `def _parse_float_exclusive_range_option(option_name, option_raw, min_value, max_value)` `priv` (L1593-1617)
- @brief Parse and validate one float option in an exclusive range.
- @details Converts option token to `float`, validates `min < value < max`, and emits deterministic parse errors on malformed or out-of-range values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @param min_value {float} Exclusive minimum bound.
- @param max_value {float} Exclusive maximum bound.
- @return {float|None} Parsed float value when valid; `None` otherwise.
- @satisfies REQ-065, REQ-089

### fn `def _parse_non_negative_float_option(option_name, option_raw)` `priv` (L1618-1640)
- @brief Parse and validate one non-negative float option value.
- @details Converts option token to `float`, requires value greater than or equal to zero, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {float|None} Parsed non-negative float value when valid; `None` otherwise.
- @satisfies REQ-065, REQ-089

### fn `def _parse_float_in_range_option(option_name, option_raw, min_value, max_value)` `priv` (L1641-1666)
- @brief Parse and validate one float option constrained to inclusive range.
- @details Converts option token to `float`, validates inclusive bounds, and emits deterministic parse errors on malformed or out-of-range values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @param min_value {float} Inclusive minimum bound.
- @param max_value {float} Inclusive maximum bound.
- @return {float|None} Parsed bounded float value when valid; `None` otherwise.
- @satisfies REQ-082, REQ-084

### fn `def _parse_auto_brightness_options(auto_brightness_raw_values)` `priv` (L1667-1768)
- @brief Parse and validate auto-brightness parameters.
- @details Parses optional key-value and compression controls for the photographic BT.709 16-bit tonemap pipeline and applies deterministic defaults for omitted auto-brightness options.
- @param auto_brightness_raw_values {dict[str, str]} Raw `--ab-*` option values keyed by long option name.
- @return {AutoBrightnessOptions|None} Parsed auto-brightness options or `None` on validation error.
- @satisfies REQ-088, REQ-089, REQ-103, REQ-104, REQ-105

### fn `def _parse_auto_levels_hr_method_option(auto_levels_method_raw)` `priv` (L1769-1800)
- @brief Parse auto-levels highlight reconstruction method option value.
- @details Validates case-insensitive method names and normalizes accepted values to canonical tokens used by runtime dispatch.
- @param auto_levels_method_raw {str} Raw `--al-highlight-reconstruction-method` option token.
- @return {str|None} Canonical method token or `None` on parse failure.
- @satisfies REQ-101, REQ-102

### fn `def _parse_auto_levels_options(auto_levels_raw_values)` `priv` (L1801-1840)
- @brief Parse and validate auto-levels parameters.
- @details Parses optional histogram clip percentage and optional mandatory highlight reconstruction method when reconstruction is enabled.
- @param auto_levels_raw_values {dict[str, str]} Raw `--al-*` option values keyed by long option name.
- @return {AutoLevelsOptions|None} Parsed auto-levels options or `None` on validation error.
- @satisfies REQ-100, REQ-101, REQ-102

### fn `def _parse_auto_adjust_options(auto_adjust_raw_values)` `priv` (L1841-1947)
- @brief Parse and validate shared auto-adjust knobs for both implementations.
- @details Applies defaults for omitted knobs, validates scalar/range constraints, and enforces level percentile ordering contract.
- @param auto_adjust_raw_values {dict[str, str]} Raw `--aa-*` option values keyed by long option name.
- @return {AutoAdjustOptions|None} Parsed shared auto-adjust options or `None` on validation error.
- @satisfies REQ-082, REQ-083, REQ-084

### fn `def _parse_auto_adjust_mode_option(auto_adjust_raw)` `priv` (L1948-1971)
- @brief Parse auto-adjust implementation selector option value.
- @details Accepts case-insensitive auto-adjust implementation names and normalizes to canonical values for runtime dispatch.
- @param auto_adjust_raw {str} Raw auto-adjust implementation token.
- @return {str|None} Canonical auto-adjust mode (`ImageMagick` or `OpenCV`) or `None` on parse failure.
- @satisfies REQ-065, REQ-073, REQ-075

### fn `def _resolve_default_postprocess(` `priv` (L1972-1976)

### fn `def _parse_run_options(args)` `priv` (L2024-2223)
- @brief Resolve backend-specific postprocess defaults.
- @brief Parse CLI args into input, output, and EV parameters.
- @details Selects neutral defaults for enfuse/OpenCV/HDR+ and non-tuned luminance
operators, and selects tuned defaults for luminance `reinhard02` and
`mantiuk08`.
- @details Supports positional file arguments, required mutually exclusive exposure selectors (`--ev=<value>`/`--ev <value>` or `--auto-ev[=<1|true|yes|on>]`), optional `--ev-zero=<value>` or `--ev-zero <value>`, optional `--auto-zero[=<1|true|yes|on>]`, optional `--auto-zero-pct=<0..100>`, optional `--auto-ev-pct=<0..100>`, optional `--gamma=<a,b>` or `--gamma <a,b>`, optional postprocess controls, optional auto-brightness stage and `--ab-*` knobs, optional auto-levels stage and `--al-*` knobs, optional shared auto-adjust knobs, required backend selector (`--enable-enfuse`, `--enable-luminance`, `--enable-opencv`, or `--enable-hdr-plus`), and luminance backend controls including explicit `--tmo*` passthrough options and optional auto-adjust implementation selector (`--auto-adjust <ImageMagick|OpenCV>`); rejects unknown options and invalid arity.
- @param enable_luminance {bool} Backend selector state.
- @param enable_opencv {bool} OpenCV backend selector state.
- @param enable_hdr_plus {bool} HDR+ backend selector state.
- @param luminance_tmo {str} Selected luminance tone-mapping operator.
- @param args {list[str]} Raw command argument vector.
- @return {tuple[float, float, float, float]} Defaults in `(post_gamma, brightness, contrast, saturation)` order.
- @return {tuple[Path, Path, float|None, bool, tuple[float, float], PostprocessOptions, bool, bool, LuminanceOptions, OpenCvMergeOptions, bool, float, bool, float, float]|None} Parsed `(input, output, ev, auto_ev, gamma, postprocess, enable_luminance, enable_opencv, luminance_options, opencv_merge_options, enable_hdr_plus, ev_zero, auto_zero_enabled, auto_zero_pct, auto_ev_pct)` tuple; `None` on parse failure.
- @satisfies REQ-069, REQ-071, REQ-072, REQ-091, REQ-107, REQ-111
- @satisfies REQ-055, REQ-056, REQ-057, REQ-060, REQ-061, REQ-064, REQ-065, REQ-067, REQ-069, REQ-071, REQ-072, REQ-073, REQ-075, REQ-079, REQ-080, REQ-081, REQ-082, REQ-083, REQ-084, REQ-085, REQ-087, REQ-088, REQ-089, REQ-090, REQ-091, REQ-094, REQ-097, REQ-107, REQ-108, REQ-111

### fn `def _load_image_dependencies()` `priv` (L2742-2779)
- @brief Load optional Python dependencies required by `dng2jpg`.
- @details Imports `rawpy` for RAW decoding and `imageio` for image IO using `imageio.v3` when available with fallback to top-level `imageio` module.
- @return {tuple[ModuleType, ModuleType, ModuleType]|None} `(rawpy_module, imageio_module, pil_image_module)` on success; `None` on missing dependency.
- @satisfies REQ-059, REQ-066, REQ-074

### fn `def _parse_exif_datetime_to_timestamp(datetime_raw)` `priv` (L2780-2810)
- @brief Parse one EXIF datetime token into POSIX timestamp.
- @details Normalizes scalar EXIF datetime input (`str` or `bytes`), trims optional null-terminated EXIF payload suffix, and parses strict EXIF format `YYYY:MM:DD HH:MM:SS` to generate filesystem timestamp.
- @param datetime_raw {str|bytes|object} EXIF datetime scalar.
- @return {float|None} Parsed POSIX timestamp; `None` when value is missing or invalid.
- @satisfies REQ-074, REQ-077

### fn `def _extract_dng_exif_payload_and_timestamp(pil_image_module, input_dng)` `priv` (L2811-2868)
- @brief Extract DNG EXIF payload bytes, preferred datetime timestamp, and source orientation.
- @details Opens input DNG via Pillow, suppresses known non-actionable `PIL.TiffImagePlugin` metadata warning for malformed TIFF tag `33723`, reads EXIF mapping without orientation mutation, serializes payload for JPEG save while source image handle is still open, resolves source orientation from EXIF tag `274`, and resolves filesystem timestamp priority: `DateTimeOriginal`(36867) > `DateTimeDigitized`(36868) > `DateTime`(306).
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @param input_dng {Path} Source DNG path.
- @return {tuple[bytes|None, float|None, int]} `(exif_payload, exif_timestamp, source_orientation)` with orientation defaulting to `1`.
- @satisfies REQ-066, REQ-074, REQ-077

### fn `def _resolve_thumbnail_transpose_map(pil_image_module)` `priv` (L2869-2900)
- @brief Build deterministic EXIF-orientation-to-transpose mapping.
- @details Resolves Pillow transpose constants from modern `Image.Transpose` namespace with fallback to legacy module-level constants.
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @return {dict[int, int]} Orientation-to-transpose mapping for values `2..8`.
- @satisfies REQ-077, REQ-078

### fn `def _apply_orientation_transform(pil_image_module, pil_image, source_orientation)` `priv` (L2901-2923)
- @brief Apply EXIF orientation transform to one image copy.
- @details Produces display-oriented pixels from source-oriented input while preserving the original image object and preserving orientation invariants in the main processing pipeline.
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @param pil_image {object} Pillow image-like object.
- @param source_orientation {int} EXIF orientation value in range `1..8`.
- @return {object} Transformed Pillow image object.
- @satisfies REQ-077, REQ-078

### fn `def _build_oriented_thumbnail_jpeg_bytes(` `priv` (L2924-2925)

### fn `def _coerce_exif_int_like_value(raw_value)` `priv` (L2954-2996)
- @brief Build refreshed JPEG thumbnail bytes from final JPG output.
- @brief Coerce integer-like EXIF scalar values to Python integers.
- @details Opens final JPG pixels, applies source-orientation-aware transform,
scales to bounded thumbnail size, and serializes deterministic JPEG thumbnail
payload for EXIF embedding.
- @details Converts scalar EXIF values represented as `int`, integer-valued `float`, ASCII-digit `str`, or ASCII-digit `bytes` (including trailing null-terminated variants) into deterministic Python `int`; returns `None` when conversion is not safe.
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @param output_jpg {Path} Final JPG path.
- @param source_orientation {int} EXIF orientation value in range `1..8`.
- @param raw_value {object} Candidate EXIF scalar value.
- @return {bytes} Serialized JPEG thumbnail payload.
- @return {int|None} Coerced integer value or `None` when not coercible.
- @exception OSError Raised when final JPG cannot be read.
- @satisfies REQ-077, REQ-078
- @satisfies REQ-066, REQ-077, REQ-078

### fn `def _normalize_ifd_integer_like_values_for_piexif_dump(piexif_module, exif_dict)` `priv` (L2997-3130)
- @brief Normalize integer-like IFD values before `piexif.dump`.
- @details Traverses EXIF IFD mappings (`0th`, `Exif`, `GPS`, `Interop`, `1st`) and coerces integer-like values that can trigger `piexif.dump` packing failures when represented as strings or other non-int scalars. Tuple/list values are normalized only when all items are integer-like. For integer sequence tag types, nested two-item pairs are flattened to a single integer sequence for `piexif.dump` compatibility. Scalar conversion is additionally constrained by `piexif.TAGS` integer field types when tag metadata is available.
- @param piexif_module {ModuleType} Imported piexif module.
- @param exif_dict {dict[str, object]} EXIF dictionary loaded via piexif.
- @return {None} Mutates `exif_dict` in place.
- @satisfies REQ-066, REQ-077, REQ-078

### fn `def _refresh_output_jpg_exif_thumbnail_after_save(` `priv` (L3131-3136)

### fn `def _set_output_file_timestamps(output_jpg, exif_timestamp)` `priv` (L3185-3199)
- @brief Refresh output JPG EXIF thumbnail while preserving source orientation.
- @brief Set output JPG atime and mtime from EXIF timestamp.
- @details Loads source EXIF payload, regenerates thumbnail from final JPG
pixels with orientation-aware transform, preserves source orientation in main
EXIF IFD, sets thumbnail orientation to identity, and re-inserts updated EXIF
payload into output JPG.
- @details Applies EXIF-derived POSIX timestamp to both access and modification times using `os.utime`.
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @param piexif_module {ModuleType} Imported piexif module.
- @param output_jpg {Path} Final JPG path.
- @param source_exif_payload {bytes} Serialized EXIF payload from source DNG.
- @param source_orientation {int} Source EXIF orientation value in range `1..8`.
- @param output_jpg {Path} Output JPG path.
- @param exif_timestamp {float} Source EXIF-derived POSIX timestamp.
- @return {None} Side effects only.
- @return {None} Side effects only.
- @exception RuntimeError Raised when EXIF thumbnail refresh fails.
- @exception OSError Raised when filesystem metadata update fails.
- @satisfies REQ-066, REQ-077, REQ-078
- @satisfies REQ-074, REQ-077

### fn `def _sync_output_file_timestamps_from_exif(output_jpg, exif_timestamp)` `priv` (L3200-3216)
- @brief Synchronize output JPG atime/mtime from optional EXIF timestamp.
- @details Provides one dedicated call site for filesystem timestamp sync and applies update only when EXIF datetime parsing produced a valid POSIX value.
- @param output_jpg {Path} Output JPG path.
- @param exif_timestamp {float|None} Source EXIF-derived POSIX timestamp.
- @return {None} Side effects only.
- @exception OSError Raised when filesystem metadata update fails.
- @satisfies REQ-074, REQ-077

### fn `def _build_exposure_multipliers(ev_value, ev_zero=0.0)` `priv` (L3217-3235)
- @brief Compute bracketing brightness multipliers from EV delta and center.
- @details Produces exactly three multipliers mapped to exposure stops `[ev_zero-ev, ev_zero, ev_zero+ev]` as powers of two for RAW postprocess brightness control.
- @param ev_value {float} Exposure bracket EV delta.
- @param ev_zero {float} Central bracket EV value.
- @return {tuple[float, float, float]} Multipliers in order `(under, base, over)`.
- @satisfies REQ-057, REQ-077, REQ-079, REQ-080, REQ-092, REQ-093, REQ-095

### fn `def _write_bracket_images(` `priv` (L3236-3237)

### fn `def _order_bracket_paths(bracket_paths)` `priv` (L3274-3299)
- @brief Materialize three bracket TIFF files from one RAW handle.
- @brief Validate and reorder bracket TIFF paths for deterministic backend argv.
- @details Invokes `raw.postprocess` with `output_bps=16`,
`use_camera_wb=True`, `no_auto_bright=True`, explicit `user_flip=0` to
disable implicit RAW orientation mutation, and configurable gamma pair for
deterministic HDR-oriented bracket extraction before merge.
- @details Enforces exact exposure order `<ev_minus.tif> <ev_zero.tif> <ev_plus.tif>` required by backend command generation and raises on missing labels.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @param imageio_module {ModuleType} Imported imageio module with `imwrite`.
- @param multipliers {tuple[float, float, float]} Ordered exposure multipliers.
- @param gamma_value {tuple[float, float]} Gamma pair forwarded to RAW postprocess.
- @param temp_dir {Path} Directory for intermediate TIFF artifacts.
- @param bracket_paths {list[Path]} Temporary bracket TIFF paths generated from RAW.
- @return {list[Path]} Ordered temporary TIFF file paths.
- @return {list[Path]} Reordered bracket path list in deterministic exposure order.
- @exception ValueError Raised when any expected bracket label is missing.
- @satisfies REQ-057, REQ-077, REQ-079, REQ-080
- @satisfies REQ-062, REQ-112

### fn `def _order_hdr_plus_reference_paths(bracket_paths)` `priv` (L3300-3315)
- @brief Reorder bracket TIFF paths into HDR+ reference-first frame order.
- @details Converts canonical bracket order `(ev_minus, ev_zero, ev_plus)` to source-algorithm frame order `(ev_zero, ev_minus, ev_plus)` so the central bracket acts as temporal reference frame `n=0`, matching HDR+ temporal merge semantics while preserving existing bracket export filenames.
- @param bracket_paths {list[Path]} Temporary bracket TIFF paths generated from RAW.
- @return {list[Path]} Ordered bracket paths in HDR+ reference-first order.
- @satisfies REQ-112

### fn `def _run_enfuse(bracket_paths, merged_tiff)` `priv` (L3316-3336)
- @brief Merge bracket TIFF files into one HDR TIFF via `enfuse`.
- @details Builds deterministic enfuse argv with LZW compression and executes subprocess in checked mode to propagate command failures.
- @param bracket_paths {list[Path]} Ordered intermediate exposure TIFF paths.
- @param merged_tiff {Path} Output merged TIFF target path.
- @return {None} Side effects only.
- @exception subprocess.CalledProcessError Raised when `enfuse` returns non-zero exit status.
- @satisfies REQ-058, REQ-077

### fn `def _run_luminance_hdr_cli(` `priv` (L3337-3338)

### fn `def _build_ev_times_from_ev_zero_and_delta(ev_zero, ev_delta)` `priv` (L3390-3417)
- @brief Merge bracket TIFF files into one HDR TIFF via `luminance-hdr-cli`.
- @brief Build deterministic exposure times array from EV center and EV delta.
- @details Builds deterministic luminance-hdr-cli argv using EV sequence
centered around zero-reference (`-ev_value,0,+ev_value`) even when extraction
uses non-zero `ev_zero`,
HDR model controls, tone-mapper controls, mandatory `--ldrTiff 16b`,
optional explicit `--tmo*` passthrough arguments, and ordered exposure
inputs (`ev_minus`, `ev_zero`, `ev_plus`), then writes to TIFF output path
used by shared postprocess conversion. Executes subprocess in output-TIFF
parent directory to isolate backend-generated sidecar artifacts (e.g. `.pp3`)
inside command temporary workspace lifecycle.
- @details Computes exposure times in stop space as `[2^(ev_zero-ev_delta), 2^ev_zero, 2^(ev_zero+ev_delta)]` mapped to bracket order `(ev_minus, ev_zero, ev_plus)` and returns `float32` vector suitable for OpenCV `MergeDebevec.process`.
- @param bracket_paths {list[Path]} Ordered intermediate exposure TIFF paths.
- @param output_hdr_tiff {Path} Output HDR TIFF target path.
- @param ev_value {float} EV bracket delta used to generate exposure files.
- @param ev_zero {float} Central EV used to generate exposure files.
- @param luminance_options {LuminanceOptions} Luminance backend command controls.
- @param ev_zero {float} Central EV used during bracket extraction.
- @param ev_delta {float} EV bracket delta used during bracket extraction.
- @return {None} Side effects only.
- @return {object} `numpy.float32` vector with length `3`.
- @exception subprocess.CalledProcessError Raised when `luminance-hdr-cli` returns non-zero exit status.
- @exception RuntimeError Raised when numpy dependency is unavailable.
- @satisfies REQ-060, REQ-061, REQ-062, REQ-067, REQ-068, REQ-077, REQ-080, REQ-095
- @satisfies REQ-108, REQ-109

### fn `def _normalize_debevec_hdr_to_unit_range(np_module, hdr_rgb_float32, white_point_percentile)` `priv` (L3418-3452)
- @brief Normalize Debevec HDR tensor to unit range with robust white point.
- @details Computes BT.709 luminance, extracts percentile-derived `Lwhite`, scales RGB tensor by `1/Lwhite`, and clamps into `[0,1]` to produce deterministic blend-ready Debevec contribution.
- @param np_module {ModuleType} Imported numpy module.
- @param hdr_rgb_float32 {object} Debevec output RGB tensor in float domain.
- @param white_point_percentile {float} White-point percentile in `(0,100)`.
- @return {object} Debevec RGB float tensor clamped to `[0,1]`.
- @satisfies REQ-109, REQ-110

### fn `def _run_opencv_hdr_merge(` `priv` (L3453-3459)

### fn `def _hdrplus_box_down2_uint16(np_module, frames_uint16)` `priv` (L3528-3555)
- @brief Merge bracket TIFF files into one HDR TIFF via OpenCV Mertens+Debevec.
- @brief Downsample HDR+ scalar frames with 2x2 box averaging.
- @details Loads deterministic bracket order, executes `MergeMertens` exposure
fusion and `MergeDebevec` radiance merge using EV-derived exposure times,
normalizes Debevec HDR with percentile robust white-point luminance scaling,
averages both outputs in float domain, then writes one RGB uint16 TIFF.
- @details Ports `box_down2` from `util.cpp` by reflect-padding odd image sizes to even extents, summing each 2x2 region in `uint32`, and dividing by `4` once to preserve integer averaging semantics.
- @param bracket_paths {list[Path]} Ordered intermediate exposure TIFF paths.
- @param output_hdr_tiff {Path} Output HDR TIFF target path.
- @param ev_value {float} EV bracket delta used to generate exposure files.
- @param ev_zero {float} Central EV used to generate exposure files.
- @param opencv_merge_options {OpenCvMergeOptions} OpenCV merge backend controls.
- @param auto_adjust_opencv_dependencies {tuple[ModuleType, ModuleType]|None} Optional `(cv2, numpy)` dependency tuple.
- @param np_module {ModuleType} Imported numpy module.
- @param frames_uint16 {object} Scalar frame tensor with shape `(N,H,W)`.
- @return {None} Side effects only.
- @return {object} Downsampled `uint16` tensor with shape `(N,ceil(H/2),ceil(W/2))`.
- @exception RuntimeError Raised when OpenCV/numpy dependencies are missing or bracket payloads are invalid.
- @satisfies REQ-077, REQ-107, REQ-108, REQ-109, REQ-110
- @satisfies REQ-112, REQ-113

### fn `def _hdrplus_luminance_proxy_uint16(np_module, frames_rgb_uint16)` `priv` (L3556-3573)
- @brief Convert RGB bracket tensor into scalar HDR+ merge proxy.
- @details Adapts single-channel Bayer merge input to aligned RGB bracket TIFF inputs by computing deterministic per-pixel arithmetic RGB mean, rounding to `uint16`, and preserving source 16-bit scale for subsequent `box_down2` and tile L1 distance steps.
- @param np_module {ModuleType} Imported numpy module.
- @param frames_rgb_uint16 {object} RGB frame tensor with shape `(N,H,W,3)`.
- @return {object} Scalar `uint16` tensor with shape `(N,H,W)`.
- @satisfies REQ-112, REQ-115

### fn `def _hdrplus_extract_overlapping_tiles(` `priv` (L3574-3579)

### fn `def _hdrplus_compute_temporal_weights(np_module, layer_tiles)` `priv` (L3632-3674)
- @brief Compute HDR+ temporal tile weights against reference frame.
- @details Ports `merge_temporal` weight equations from `merge.cpp` with alignment offsets fixed to zero: computes integer tile L1 distance over each 16x16 downsampled tile, derives `norm_dist = max(1, dist/8 - 10/8)`, applies hard cutoff when `norm_dist > 290`, and returns inverse-distance weights for alternate frames only.
- @param np_module {ModuleType} Imported numpy module.
- @param layer_tiles {object} Downsampled scalar tile tensor with shape `(N,Ty,Tx,16,16)`.
- @return {tuple[object, object]} `(weights, total_weight)` where `weights` has shape `(N-1,Ty,Tx)` and `total_weight` has shape `(Ty,Tx)`.
- @satisfies REQ-112, REQ-113

### fn `def _hdrplus_merge_temporal_rgb(np_module, full_tiles_rgb, weights, total_weight)` `priv` (L3675-3701)
- @brief Merge HDR+ full-resolution tiles across temporal dimension.
- @details Ports the temporal accumulation step from `merge.cpp` with zero alignment offsets by normalizing the reference tile and all alternate tiles with shared per-tile `total_weight`, while preserving RGB `uint16` content in float64 accumulation until the spatial merge stage.
- @param np_module {ModuleType} Imported numpy module.
- @param full_tiles_rgb {object} RGB tile tensor with shape `(N,Ty,Tx,32,32,3)`.
- @param weights {object} Alternate-frame weight tensor with shape `(N-1,Ty,Tx)`.
- @param total_weight {object} Reference-inclusive tile total weights with shape `(Ty,Tx)`.
- @return {object} Temporally merged RGB tile tensor with shape `(Ty,Tx,32,32,3)`.
- @satisfies REQ-112, REQ-113

### fn `def _hdrplus_merge_spatial_rgb(np_module, temporal_tiles, width, height)` `priv` (L3702-3772)
- @brief Blend HDR+ temporally merged tiles with raised-cosine overlap.
- @details Ports `merge_spatial` from `merge.cpp`: builds source raised-cosine weights over `32` samples, gathers four overlapping tiles for each output pixel using source index formulas derived from `tile_0`, `tile_1`, `idx_0`, and `idx_1`, then computes weighted RGB sum once and rounds/clamps to `uint16`.
- @param np_module {ModuleType} Imported numpy module.
- @param temporal_tiles {object} Temporally merged RGB tile tensor with shape `(Ty,Tx,32,32,3)`.
- @param width {int} Output image width.
- @param height {int} Output image height.
- @return {object} RGB `uint16` merged image tensor with shape `(H,W,3)`.
- @satisfies REQ-112, REQ-114

### fn `def _run_hdr_plus_merge(bracket_paths, output_hdr_tiff, imageio_module, np_module)` `priv` (L3773-3835)
- @brief Merge bracket TIFF files into one RGB uint16 TIFF via HDR+.
- @details Ports the source HDR+ merge pipeline from `merge.cpp` and `util.cpp` while intentionally omitting alignment stages per integration requirements: reorders bracket inputs into reference-first frame order `(ev_zero, ev_minus, ev_plus)`, computes scalar merge proxy from aligned RGB TIFFs, executes source `box_down2`, source temporal tile weighting with zero offsets, source temporal full-resolution tile accumulation, and source raised-cosine spatial blending, then writes one merged RGB `uint16` TIFF.
- @param bracket_paths {list[Path]} Temporary bracket TIFF paths generated from RAW.
- @param output_hdr_tiff {Path} Output HDR TIFF target path.
- @param imageio_module {ModuleType} Imported imageio module with `imread` and `imwrite`.
- @param np_module {ModuleType} Imported numpy module.
- @return {None} Side effects only.
- @exception RuntimeError Raised when bracket payloads are invalid.
- @satisfies REQ-077, REQ-111, REQ-112, REQ-113, REQ-114, REQ-115

### fn `def _convert_compression_to_quality(jpg_compression)` `priv` (L3836-3848)
- @brief Convert JPEG compression level to Pillow quality value.
- @details Maps inclusive compression range `[0, 100]` to inclusive quality range `[100, 1]` preserving deterministic inverse relation.
- @param jpg_compression {int} JPEG compression level.
- @return {int} Pillow quality value in `[1, 100]`.
- @satisfies REQ-065, REQ-066

### fn `def _resolve_imagemagick_command()` `priv` (L3849-3866)
- @brief Resolve ImageMagick executable name for current runtime.
- @details Probes `magick` first (ImageMagick 7+ preferred CLI), then `convert` (legacy-compatible CLI alias) to preserve auto-adjust-stage compatibility across distributions that package ImageMagick under different executable names.
- @return {str|None} Resolved executable token (`magick` or `convert`) or `None` when no supported executable is available.
- @satisfies REQ-059, REQ-073

### fn `def _resolve_auto_adjust_opencv_dependencies()` `priv` (L3867-3891)
- @brief Resolve OpenCV runtime dependencies for image-domain stages.
- @details Imports `cv2` and `numpy` modules required by OpenCV auto-adjust pipeline and returns `None` with deterministic error output when dependencies are missing.
- @return {tuple[ModuleType, ModuleType]|None} `(cv2_module, numpy_module)` when available; `None` on dependency failure.
- @satisfies REQ-059, REQ-073, REQ-075

### fn `def _resolve_numpy_dependency()` `priv` (L3892-3909)
- @brief Resolve numpy runtime dependency for auto-levels and auto-brightness.
- @details Imports `numpy` required by uint16-domain post-merge pre-stages and returns `None` with deterministic error output when dependency is missing.
- @return {ModuleType|None} Imported numpy module; `None` on dependency failure.
- @satisfies REQ-059, REQ-090, REQ-100

### fn `def _to_uint8_image_array(np_module, image_data)` `priv` (L3910-3956)
- @brief Convert image tensor to `uint8` range `[0,255]`.
- @details Normalizes integer or float image payloads into `uint8` preserving relative brightness scale: `uint16` uses `/257`, normalized float arrays in `[0,1]` use `*255`, and all paths clamp to inclusive byte range.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image tensor.
- @return {object} `uint8` image tensor.
- @satisfies REQ-066, REQ-090

### fn `def _to_uint16_image_array(np_module, image_data)` `priv` (L3957-4001)
- @brief Convert image tensor to `uint16` range `[0,65535]`.
- @details Normalizes integer or float image payloads into `uint16` preserving relative brightness scale: `uint8` uses `*257`, normalized float arrays in `[0,1]` use `*65535`, and all paths clamp to inclusive 16-bit range.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image tensor.
- @return {object} `uint16` image tensor.
- @satisfies REQ-066, REQ-090

### fn `def _normalize_uint16_rgb_image(np_module, image_data)` `priv` (L4002-4029)
- @brief Normalize image payload into RGB uint16 tensor.
- @details Converts input image payload to `uint16`, normalizes channel layout for static postprocess stages by expanding grayscale to one channel, replicating single-channel input to RGB, dropping alpha from RGBA input, and returning first three channels for deterministic RGB processing.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image tensor.
- @return {object} RGB uint16 image tensor with shape `(H,W,3)`.
- @exception ValueError Raised when normalized image has unsupported shape.
- @satisfies REQ-012, REQ-013, REQ-106

### fn `def _validate_uint16_rgb_stage_image(np_module, image_rgb_uint16, stage_label)` `priv` (L4030-4051)
- @brief Validate uint16 RGB tensor contract for static postprocess stages.
- @details Enforces deterministic guard rails for static uint16 postprocess steps by requiring dtype `uint16`, rank `3`, and channel count `3`.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_uint16 {object} Stage image payload to validate.
- @param stage_label {str} Diagnostic stage identifier for deterministic errors.
- @return {object} Validated RGB uint16 tensor.
- @exception ValueError Raised when stage tensor dtype or shape is unsupported.
- @satisfies REQ-012, REQ-013, REQ-106

### fn `def _apply_post_gamma_uint16(np_module, image_rgb_uint16, gamma_value)` `priv` (L4052-4088)
- @brief Apply static post-gamma over RGB uint16 tensor.
- @details Executes gamma transfer directly in uint16 domain using a 65536-step LUT (`index == input uint16 code value`) and returns uint16 output without intermediate byte quantization to preserve full 16-bit gradation.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_uint16 {object} RGB uint16 image tensor.
- @param gamma_value {float} Static post-gamma factor.
- @return {object} RGB uint16 tensor after gamma stage.
- @satisfies REQ-012, REQ-013

### fn `def _blend_uint16(np_module, base_uint16, target_uint16, factor)` `priv` (L4089-4107)
- @brief Blend two uint16 tensors with deterministic linear interpolation.
- @details Computes `base + factor*(target-base)` in float64, then rounds and clamps to uint16 to preserve deterministic postprocess factor behavior.
- @param np_module {ModuleType} Imported numpy module.
- @param base_uint16 {object} Base RGB uint16 tensor.
- @param target_uint16 {object} Target RGB uint16 tensor.
- @param factor {float} Interpolation factor.
- @return {object} RGB uint16 tensor after blend operation.
- @satisfies REQ-012, REQ-013

### fn `def _apply_brightness_uint16(np_module, image_rgb_uint16, brightness_factor)` `priv` (L4108-4137)
- @brief Apply static brightness factor on RGB uint16 tensor.
- @details Multiplies uint16 RGB channels by `brightness_factor` in float64 domain and applies deterministic clamp/round to uint16 without byte-domain conversion.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_uint16 {object} RGB uint16 image tensor.
- @param brightness_factor {float} Brightness scale factor.
- @return {object} RGB uint16 tensor after brightness stage.
- @satisfies REQ-012, REQ-013

### fn `def _apply_contrast_uint16(np_module, image_rgb_uint16, contrast_factor)` `priv` (L4138-4168)
- @brief Apply static contrast factor on RGB uint16 tensor.
- @details Applies contrast interpolation around luminance mean computed on float64 uint16 tensor (`output = mean + factor*(input-mean)`), then clamps and rounds to uint16.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_uint16 {object} RGB uint16 image tensor.
- @param contrast_factor {float} Contrast interpolation factor.
- @return {object} RGB uint16 tensor after contrast stage.
- @satisfies REQ-012, REQ-013

### fn `def _apply_saturation_uint16(np_module, image_rgb_uint16, saturation_factor)` `priv` (L4169-4204)
- @brief Apply static saturation factor on RGB uint16 tensor.
- @details Applies saturation interpolation around BT.709 luminance in float64 uint16 domain (`output = gray + factor*(input-gray)`), then clamps and rounds to uint16.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_uint16 {object} RGB uint16 image tensor.
- @param saturation_factor {float} Saturation interpolation factor.
- @return {object} RGB uint16 tensor after saturation stage.
- @satisfies REQ-012, REQ-013

### fn `def _apply_static_postprocess_uint16(np_module, image_rgb_uint16, postprocess_options)` `priv` (L4205-4245)
- @brief Execute static postprocess chain fully in uint16 precision.
- @details Applies post-gamma, brightness, contrast, and saturation in fixed order over RGB uint16 tensor and preserves uint16 output for downstream auto-adjust/final quantization stages.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_uint16 {object} RGB uint16 image tensor.
- @param postprocess_options {PostprocessOptions} Parsed postprocess controls.
- @return {object} RGB uint16 tensor after static postprocess chain.
- @satisfies REQ-012, REQ-013, REQ-106

### fn `def _to_linear_srgb(np_module, image_srgb)` `priv` (L4246-4263)
- @brief Convert sRGB tensor to linear-sRGB tensor.
- @details Applies IEC 61966-2-1 piecewise inverse transfer function on normalized channel values in `[0,1]`.
- @param np_module {ModuleType} Imported numpy module.
- @param image_srgb {object} Float image tensor in sRGB domain `[0,1]`.
- @return {object} Float image tensor in linear-sRGB domain `[0,1]`.
- @satisfies REQ-090, REQ-099

### fn `def _from_linear_srgb(np_module, image_linear)` `priv` (L4264-4281)
- @brief Convert linear-sRGB tensor to sRGB tensor.
- @details Applies IEC 61966-2-1 piecewise forward transfer function on normalized linear channel values in `[0,1]`.
- @param np_module {ModuleType} Imported numpy module.
- @param image_linear {object} Float image tensor in linear-sRGB domain `[0,1]`.
- @return {object} Float image tensor in sRGB domain `[0,1]`.
- @satisfies REQ-090, REQ-099

### fn `def _compute_bt709_luminance(np_module, linear_rgb)` `priv` (L4282-4299)
- @brief Compute BT.709 linear luminance from linear RGB tensor.
- @details Computes per-pixel luminance using BT.709 coefficients with RGB channel order: `0.2126*R + 0.7152*G + 0.0722*B`.
- @param np_module {ModuleType} Imported numpy module.
- @param linear_rgb {object} Linear-sRGB float tensor with shape `H,W,3`.
- @return {object} Float luminance tensor with shape `H,W`.
- @satisfies REQ-090, REQ-099

### fn `def _analyze_luminance_key(np_module, luminance, eps)` `priv` (L4300-4338)
- @brief Analyze luminance distribution and classify scene key.
- @details Computes log-average luminance, median, percentile tails, and clip proxies on normalized BT.709 luminance and classifies scene as `low-key`, `normal-key`, or `high-key` using conservative thresholds.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance {object} BT.709 luminance float tensor in `[0, 1]`.
- @param eps {float} Positive numerical stability guard.
- @return {dict[str, float|str]} Key analysis dictionary with key type, central statistics, tails, and clipping proxies.
- @satisfies REQ-050, REQ-103

### fn `def _choose_auto_key_value(key_analysis, auto_brightness_options)` `priv` (L4339-4384)
- @brief Select Reinhard key value from key-analysis metrics.
- @details Chooses base key by scene class (`0.09/0.18/0.36`) and applies conservative under/over-exposure adaptation bounded by configured min/max key limits and automatic boost factor.
- @param key_analysis {dict[str, float|str]} Luminance key-analysis dictionary.
- @param auto_brightness_options {AutoBrightnessOptions} Parsed auto-brightness parameters.
- @return {float} Clamped key value `a`.
- @satisfies REQ-050, REQ-103

### fn `def _reinhard_global_tonemap_luminance(` `priv` (L4385-4390)

### fn `def _luminance_preserving_desaturate_to_fit(np_module, rgb_linear, luminance, eps)` `priv` (L4424-4451)
- @brief Apply Reinhard global tonemap on luminance with robust `Lwhite`.
- @brief Desaturate only out-of-gamut pixels while preserving luminance.
- @details Executes photographic operator: `Lw_bar=exp(mean(log(eps+Y)))`,
`L=(a/Lw_bar)*Y`, robust `Lwhite` from percentile of `L`, then burn-out
compression `Ld=(L*(1+L/(Lwhite^2)))/(1+L)`.
- @details For pixels where any RGB channel exceeds `1.0`, computes minimal blend factor toward grayscale `(Y,Y,Y)` such that max channel becomes `<=1` while preserving BT.709 luminance of both endpoints.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance {object} BT.709 luminance float tensor.
- @param key_value {float} Reinhard key value `a`.
- @param white_point_percentile {float} Percentile in `(0,100)` for robust white point.
- @param eps {float} Positive numerical stability guard.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb_linear {object} Linear RGB float tensor.
- @param luminance {object} Target luminance tensor used for grayscale anchor.
- @param eps {float} Positive numerical stability guard.
- @return {tuple[object, dict[str, float]]} Tonemapped luminance tensor and debug statistics dictionary.
- @return {object} Desaturated and clamped linear RGB tensor.
- @satisfies REQ-050, REQ-104
- @satisfies REQ-050, REQ-105

### fn `def _apply_mild_local_contrast_bgr_uint16(cv2_module, np_module, image_bgr_uint16, options)` `priv` (L4452-4487)
- @brief Apply optional mild CLAHE micro-contrast on 16-bit Y channel.
- @details Converts BGR16 to YCrCb, runs CLAHE on 16-bit Y with configured clip/tile controls, then blends original and CLAHE outputs using configured local-contrast strength.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param image_bgr_uint16 {object} BGR uint16 image tensor.
- @param options {AutoBrightnessOptions} Parsed auto-brightness options.
- @return {object} BGR uint16 image tensor after optional local contrast.
- @satisfies REQ-050, REQ-105

### fn `def _rt_gamma2(np_module, values)` `priv` (L4488-4507)
- @brief Apply RawTherapee gamma2 transfer function.
- @details Implements the same piecewise gamma curve used in the attached auto-levels source for histogram-domain bright clipping normalization.
- @param np_module {ModuleType} Imported numpy module.
- @param values {object} Float tensor in linear domain.
- @return {object} Float tensor in gamma2 domain.
- @satisfies REQ-100

### fn `def _rt_igamma2(np_module, values)` `priv` (L4508-4528)
- @brief Apply inverse RawTherapee gamma2 transfer function.
- @details Implements inverse piecewise gamma curve paired with `_rt_gamma2` for whiteclip/black normalization inside auto-levels.
- @param np_module {ModuleType} Imported numpy module.
- @param values {object} Float tensor in gamma2 domain.
- @return {object} Float tensor in linear domain.
- @satisfies REQ-100

### fn `def _build_autoexp_histogram_rgb_uint16(np_module, image_rgb_uint16, histcompr)` `priv` (L4529-4555)
- @brief Build RGB auto-levels histogram from uint16 image tensor.
- @details Ports histogram accumulation logic from attached auto-levels source: per-channel histogram with `hist_size = 65536 >> histcompr`, channel sum accumulation, and deterministic index clipping.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_uint16 {object} RGB uint16 image tensor.
- @param histcompr {int} Histogram compression shift in `[0, 15]`.
- @return {object} Histogram tensor.
- @satisfies REQ-100

### fn `def _compute_auto_levels_from_histogram(np_module, histogram, histcompr, clip_percent)` `priv` (L4556-4755)
- @brief Compute auto-levels gain metrics from histogram.
- @details Ports `get_autoexp_from_histogram` from attached source as-is in numeric behavior for RGB uint16 histogram: octile spread, white/black clip, exposure compensation, brightness/contrast, and highlight compression metrics.
- @param np_module {ModuleType} Imported numpy module.
- @param histogram {object} Flattened histogram tensor.
- @param histcompr {int} Histogram compression shift.
- @param clip_percent {float} Clip percentage.
- @return {dict[str, int|float]} Auto-levels metrics dictionary.
- @satisfies REQ-100

### fn `def _apply_auto_levels_uint16(np_module, image_rgb_uint16, auto_levels_options)` `priv` (L4809-4872)
- @brief Apply auto-levels stage on RGB uint16 tensor.
- @details Executes auto-levels histogram analysis ported from attached source, applies gain derived from exposure compensation, and conditionally runs mandatory-method highlight reconstruction when enabled.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_uint16 {object} RGB uint16 image tensor.
- @param auto_levels_options {AutoLevelsOptions} Parsed auto-levels options.
- @return {object} RGB uint16 tensor after auto-levels stage.
- @exception ValueError Raised when input tensor is not uint16 RGB.
- @satisfies REQ-100, REQ-101, REQ-102

### fn `def _hlrecovery_luminance_uint16(np_module, image_rgb, maxval=65535.0)` `priv` (L4873-4918)
- @brief Apply Luminance highlight reconstruction on uint16-like RGB tensor.
- @details Ports luminance method from attached source in RGB domain with clipped-channel chroma ratio scaling and masked reconstruction.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on uint16 scale.
- @param maxval {float} Maximum channel value.
- @return {object} Highlight-reconstructed RGB float tensor.
- @satisfies REQ-102

### fn `def _hlrecovery_cielab_uint16(` `priv` (L4919-4920)

### fn `def _f_lab(values)` `priv` (L4953-4960)
- @brief Apply CIELab blending highlight reconstruction on RGB tensor.
- @details Ports CIELab blending method from attached source with Lab-space
channel repair under clipped highlights.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on uint16 scale.
- @param maxval {float} Maximum channel value.
- @param xyz_cam {object|None} Optional XYZ conversion matrix.
- @param cam_xyz {object|None} Optional inverse matrix.
- @return {object} Highlight-reconstructed RGB float tensor.
- @satisfies REQ-102

### fn `def _f2xyz(values)` `priv` (L4961-4967)

### fn `def _hlrecovery_blend_uint16(np_module, image_rgb, hlmax, maxval=65535.0)` `priv` (L5003-5105)
- @brief Apply Blend highlight reconstruction on RGB tensor.
- @details Ports blend method from attached source with quadratic channel blend and desaturation phase driven by clipping metrics.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on uint16 scale.
- @param hlmax {object} Channel maxima vector with shape `(3,)`.
- @param maxval {float} Maximum channel value.
- @return {object} Highlight-reconstructed RGB float tensor.
- @satisfies REQ-102

### fn `def _apply_auto_brightness_rgb_uint8(np_module, image_rgb_uint8, auto_brightness_options)` `priv` (L5106-5170)
- @brief Apply photographic BT.709 auto-brightness on uint16 RGB tensor.
- @details Executes 16-bit pipeline: normalize to float `[0,1]`, linearize sRGB, derive BT.709 luminance, classify key using log-average and percentiles, choose/override key value `a`, apply Reinhard global tonemap with robust percentile white-point, preserve chromaticity by luminance scaling, perform luminance-preserving anti-clipping desaturation, then de-linearize and restore uint16 output.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_uint8 {object} RGB uint16 image tensor.
- @param auto_brightness_options {AutoBrightnessOptions} Parsed auto-brightness parameters.
- @return {object} RGB uint16 image tensor after BT.709 auto-brightness.
- @exception ValueError Raised when input tensor is not uint16 RGB.
- @satisfies REQ-050, REQ-066, REQ-090, REQ-099, REQ-103, REQ-104, REQ-105

### fn `def _apply_validated_auto_adjust_pipeline(` `priv` (L5171-5172)

### fn `def _clamp01(np_module, values)` `priv` (L5253-5266)
- @brief Execute validated auto-adjust pipeline over temporary lossless 16-bit TIFF files.
- @brief Clamp numeric image tensor values into `[0.0, 1.0]` interval.
- @details Uses ImageMagick to normalize source data to 16-bit-per-channel TIFF,
applies deterministic denoise/level/sigmoidal/vibrance/high-pass overlay
stages parameterized by shared auto-adjust knobs, and writes lossless
auto-adjust output artifact consumed by JPG encoder.
- @details Applies vectorized clipping to ensure deterministic bounded values for OpenCV auto-adjust pipeline float-domain operations.
- @param postprocessed_input {Path} Temporary postprocess image input path.
- @param auto_adjust_output {Path} Temporary auto-adjust output TIFF path.
- @param imagemagick_command {str} Resolved ImageMagick executable token.
- @param auto_adjust_options {AutoAdjustOptions} Shared auto-adjust knob values.
- @param np_module {ModuleType} Imported numpy module.
- @param values {object} Numeric tensor-like payload.
- @return {None} Side effects only.
- @return {object} Clipped tensor payload.
- @exception subprocess.CalledProcessError Raised when ImageMagick returns non-zero.
- @satisfies REQ-073, REQ-077, REQ-086
- @satisfies REQ-075

### fn `def _gaussian_kernel_2d(np_module, sigma, radius=None)` `priv` (L5267-5289)
- @brief Build normalized 2D Gaussian kernel.
- @details Creates deterministic Gaussian kernel used by selective blur stage; returns identity kernel when `sigma <= 0`.
- @param np_module {ModuleType} Imported numpy module.
- @param sigma {float} Gaussian sigma value.
- @param radius {int|None} Optional kernel radius override.
- @return {object} Normalized 2D kernel tensor.
- @satisfies REQ-075

### fn `def _rgb_to_hsl(np_module, rgb)` `priv` (L5290-5323)
- @brief Convert RGB float tensor to HSL channels.
- @details Implements explicit HSL conversion for OpenCV auto-adjust saturation-gamma stage without delegating to external color-space helpers.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB tensor in `[0.0, 1.0]`.
- @return {tuple[object, object, object]} `(h, s, l)` channel tensors.
- @satisfies REQ-075

### fn `def _hue_to_rgb(np_module, p_values, q_values, t_values)` `priv` (L5324-5354)
- @brief Convert one hue-shift channel to RGB component.
- @details Evaluates piecewise hue interpolation branch used by HSL-to-RGB conversion in OpenCV auto-adjust pipeline.
- @param np_module {ModuleType} Imported numpy module.
- @param p_values {object} Lower chroma interpolation boundary.
- @param q_values {object} Upper chroma interpolation boundary.
- @param t_values {object} Hue-shifted channel tensor.
- @return {object} RGB component tensor.
- @satisfies REQ-075

### fn `def _hsl_to_rgb(np_module, hue, saturation, lightness)` `priv` (L5355-5395)
- @brief Convert HSL channels to RGB float tensor.
- @details Reconstructs RGB tensor with explicit achromatic/chromatic branches for OpenCV auto-adjust saturation-gamma stage.
- @param np_module {ModuleType} Imported numpy module.
- @param hue {object} Hue channel tensor.
- @param saturation {object} Saturation channel tensor.
- @param lightness {object} Lightness channel tensor.
- @return {object} RGB tensor in `[0.0, 1.0]`.
- @satisfies REQ-075

### fn `def _selective_blur_contrast_gated_vectorized(` `priv` (L5396-5397)

### fn `def _level_per_channel_adaptive(np_module, rgb, low_pct=0.1, high_pct=99.9)` `priv` (L5446-5468)
- @brief Execute contrast-gated selective blur stage.
- @brief Execute adaptive per-channel level normalization.
- @details Applies vectorized contrast-gated neighborhood accumulation over
Gaussian kernel offsets to emulate selective blur behavior.
- @details Applies percentile-based level stretching independently for each RGB channel.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param sigma {float} Gaussian sigma.
- @param threshold_percent {float} Luma-difference threshold percent.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param low_pct {float} Low percentile threshold.
- @param high_pct {float} High percentile threshold.
- @return {object} Blurred RGB float tensor.
- @return {object} Level-normalized RGB float tensor.
- @satisfies REQ-075
- @satisfies REQ-075

### fn `def _sigmoidal_contrast(np_module, rgb, contrast=3.0, midpoint=0.5)` `priv` (L5469-5493)
- @brief Execute sigmoidal contrast stage.
- @details Applies logistic remapping with bounded normalization for each RGB channel.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param contrast {float} Logistic slope.
- @param midpoint {float} Logistic midpoint.
- @return {object} Contrast-adjusted RGB float tensor.
- @satisfies REQ-075

### fn `def logistic(z_values)` (L5484-5486)
- @brief Execute sigmoidal contrast stage.
- @details Applies logistic remapping with bounded normalization for each RGB
channel.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param contrast {float} Logistic slope.
- @param midpoint {float} Logistic midpoint.
- @return {object} Contrast-adjusted RGB float tensor.
- @satisfies REQ-075

### fn `def _vibrance_hsl_gamma(np_module, rgb, saturation_gamma=0.8)` `priv` (L5494-5511)
- @brief Execute HSL saturation gamma stage.
- @details Converts RGB to HSL, applies saturation gamma transform, and converts back to RGB.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param saturation_gamma {float} Saturation gamma denominator value.
- @return {object} Saturation-adjusted RGB float tensor.
- @satisfies REQ-075

### fn `def _gaussian_blur_rgb(cv2_module, np_module, rgb, sigma)` `priv` (L5512-5535)
- @brief Execute RGB Gaussian blur with reflected border mode.
- @details Computes odd kernel size from sigma and applies OpenCV Gaussian blur preserving reflected border behavior.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param sigma {float} Gaussian sigma.
- @return {object} Blurred RGB float tensor.
- @satisfies REQ-075

### fn `def _high_pass_math_gray(cv2_module, np_module, rgb, blur_sigma=2.5)` `priv` (L5536-5559)
- @brief Execute high-pass math grayscale stage.
- @details Computes high-pass response as `A - B + 0.5` over RGB channels and converts to luminance grayscale tensor.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param blur_sigma {float} Gaussian blur sigma for high-pass base.
- @return {object} Grayscale float tensor in `[0.0, 1.0]`.
- @satisfies REQ-075

### fn `def _overlay_composite(np_module, base_rgb, overlay_gray)` `priv` (L5560-5581)
- @brief Execute overlay composite stage.
- @details Applies conditional overlay blend equation over RGB base and grayscale overlay tensors.
- @param np_module {ModuleType} Imported numpy module.
- @param base_rgb {object} Base RGB float tensor in `[0.0, 1.0]`.
- @param overlay_gray {object} Overlay grayscale tensor in `[0.0, 1.0]`.
- @return {object} Overlay-composited RGB float tensor.
- @satisfies REQ-075

### fn `def _apply_validated_auto_adjust_pipeline_opencv(` `priv` (L5582-5583)

### fn `def _load_piexif_dependency()` `priv` (L5662-5679)
- @brief Execute validated auto-adjust pipeline using OpenCV and numpy.
- @brief Resolve piexif runtime dependency for EXIF thumbnail refresh.
- @details Reads RGB image payload and enforces deterministic auto-adjust input
normalization: `uint8` inputs are promoted to `uint16` using `value*257`,
then explicit 16-bit-to-float normalization is applied. Executes selective
blur, adaptive levels, sigmoidal contrast, HSL saturation gamma,
high-pass/overlay stages, then restores float payload to 16-bit-per-channel
RGB TIFF output, parameterized by shared auto-adjust knobs.
- @details Imports `piexif` module required for EXIF thumbnail regeneration and reinsertion; emits deterministic install guidance when dependency is missing.
- @param input_file {Path} Source TIFF path.
- @param output_file {Path} Output TIFF path.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param auto_adjust_options {AutoAdjustOptions} Shared auto-adjust knob values.
- @return {None} Side effects only.
- @return {ModuleType|None} Imported piexif module; `None` on dependency failure.
- @exception OSError Raised when source file is missing.
- @exception RuntimeError Raised when OpenCV read/write fails or input dtype is unsupported.
- @satisfies REQ-073, REQ-075, REQ-077, REQ-087
- @satisfies REQ-059, REQ-078

### fn `def _encode_jpg(` `priv` (L5680-5692)

### fn `def _collect_processing_errors(rawpy_module)` `priv` (L5839-5867)
- @brief Build deterministic tuple of recoverable processing exceptions.
- @details Combines common IO/value/subprocess errors with rawpy-specific decoding error classes when present in runtime module version.
- @param rawpy_module {ModuleType} Imported rawpy module.
- @return {tuple[type[BaseException], ...]} Ordered deduplicated exception class tuple.
- @satisfies REQ-059

### fn `def _is_supported_runtime_os()` `priv` (L5868-5887)
- @brief Validate runtime platform support for `dng2jpg`.
- @details Accepts Linux runtime only; emits explicit non-Linux unsupported message that includes OS label (`Windows` or `MacOS`) for deterministic UX.
- @return {bool} `True` when runtime OS is Linux; `False` otherwise.
- @satisfies REQ-055, REQ-059

### fn `def run(args)` (L5888-6087)
- @brief Execute `dng2jpg` command pipeline.
- @details Parses command options, validates dependencies, detects source DNG bits-per-color from RAW metadata, resolves manual or automatic EV-zero center, resolves static or adaptive EV selector around resolved center using bit-derived EV ceilings, extracts three RAW brackets, executes selected `enfuse`, selected luminance-hdr-cli, selected OpenCV Mertens+Debevec, or selected HDR+ tile merge flow, writes JPG output, and guarantees temporary artifact cleanup through isolated temporary directory lifecycle.
- @param args {list[str]} Command argument vector excluding command token.
- @return {int} `0` on success; `1` on parse/validation/dependency/processing failure.
- @satisfies REQ-055, REQ-056, REQ-057, REQ-058, REQ-059, REQ-060, REQ-061, REQ-062, REQ-064, REQ-065, REQ-066, REQ-067, REQ-068, REQ-069, REQ-071, REQ-072, REQ-073, REQ-074, REQ-075, REQ-077, REQ-078, REQ-079, REQ-080, REQ-081, REQ-088, REQ-089, REQ-090, REQ-091, REQ-092, REQ-093, REQ-094, REQ-095, REQ-096, REQ-097, REQ-098, REQ-100, REQ-101, REQ-102, REQ-107, REQ-108, REQ-109, REQ-110, REQ-111, REQ-112, REQ-113, REQ-114, REQ-115

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`PROGRAM`|var|pub|31||
|`DESCRIPTION`|var|pub|32||
|`DEFAULT_GAMMA`|var|pub|33||
|`DEFAULT_POST_GAMMA`|var|pub|34||
|`DEFAULT_BRIGHTNESS`|var|pub|35||
|`DEFAULT_CONTRAST`|var|pub|36||
|`DEFAULT_SATURATION`|var|pub|37||
|`DEFAULT_JPG_COMPRESSION`|var|pub|38||
|`DEFAULT_AUTO_ZERO_PCT`|var|pub|39||
|`DEFAULT_AUTO_EV_PCT`|var|pub|40||
|`DEFAULT_AA_BLUR_SIGMA`|var|pub|41||
|`DEFAULT_AA_BLUR_THRESHOLD_PCT`|var|pub|42||
|`DEFAULT_AA_LEVEL_LOW_PCT`|var|pub|43||
|`DEFAULT_AA_LEVEL_HIGH_PCT`|var|pub|44||
|`DEFAULT_AA_SIGMOID_CONTRAST`|var|pub|45||
|`DEFAULT_AA_SIGMOID_MIDPOINT`|var|pub|46||
|`DEFAULT_AA_SATURATION_GAMMA`|var|pub|47||
|`DEFAULT_AA_HIGHPASS_BLUR_SIGMA`|var|pub|48||
|`DEFAULT_AB_KEY_VALUE`|var|pub|49||
|`DEFAULT_AB_WHITE_POINT_PERCENTILE`|var|pub|50||
|`DEFAULT_AB_KEY_MIN`|var|pub|51||
|`DEFAULT_AB_KEY_MAX`|var|pub|52||
|`DEFAULT_AB_MAX_AUTO_BOOST_FACTOR`|var|pub|53||
|`DEFAULT_AB_LOCAL_CONTRAST_STRENGTH`|var|pub|54||
|`DEFAULT_AB_CLAHE_CLIP_LIMIT`|var|pub|55||
|`DEFAULT_AB_CLAHE_TILE_GRID_SIZE`|var|pub|56||
|`DEFAULT_AB_EPS`|var|pub|57||
|`DEFAULT_AB_LOW_KEY_VALUE`|var|pub|58||
|`DEFAULT_AB_NORMAL_KEY_VALUE`|var|pub|59||
|`DEFAULT_AB_HIGH_KEY_VALUE`|var|pub|60||
|`DEFAULT_AL_CLIP_PERCENT`|var|pub|61||
|`DEFAULT_AL_HISTCOMPR`|var|pub|62||
|`DEFAULT_LUMINANCE_HDR_MODEL`|var|pub|68||
|`DEFAULT_LUMINANCE_HDR_WEIGHT`|var|pub|69||
|`DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE`|var|pub|70||
|`DEFAULT_LUMINANCE_TMO`|var|pub|71||
|`DEFAULT_REINHARD02_BRIGHTNESS`|var|pub|72||
|`DEFAULT_REINHARD02_CONTRAST`|var|pub|73||
|`DEFAULT_REINHARD02_SATURATION`|var|pub|74||
|`DEFAULT_MANTIUK08_CONTRAST`|var|pub|75||
|`DEFAULT_OPENCV_DEBEVEC_WHITE_POINT_PERCENTILE`|var|pub|76||
|`HDRPLUS_TILE_SIZE`|var|pub|77||
|`HDRPLUS_TILE_STRIDE`|var|pub|78||
|`HDRPLUS_DOWNSAMPLED_TILE_SIZE`|var|pub|79||
|`HDRPLUS_TEMPORAL_FACTOR`|var|pub|80||
|`HDRPLUS_TEMPORAL_MIN_DIST`|var|pub|81||
|`HDRPLUS_TEMPORAL_MAX_DIST`|var|pub|82||
|`EV_STEP`|var|pub|83||
|`MIN_SUPPORTED_BITS_PER_COLOR`|var|pub|84||
|`DEFAULT_DNG_BITS_PER_COLOR`|var|pub|85||
|`SUPPORTED_EV_VALUES`|var|pub|86||
|`AUTO_EV_LOW_PERCENTILE`|var|pub|92||
|`AUTO_EV_HIGH_PERCENTILE`|var|pub|93||
|`AUTO_EV_MEDIAN_PERCENTILE`|var|pub|94||
|`AUTO_EV_TARGET_SHADOW`|var|pub|95||
|`AUTO_EV_TARGET_HIGHLIGHT`|var|pub|96||
|`AUTO_EV_MEDIAN_TARGET`|var|pub|97||
|`AUTO_ZERO_SCENE_KEY_LOW_THRESHOLD`|var|pub|98||
|`AUTO_ZERO_SCENE_KEY_HIGH_THRESHOLD`|var|pub|99||
|`AUTO_ZERO_TARGET_LOW_KEY`|var|pub|100||
|`AUTO_ZERO_TARGET_HIGH_KEY`|var|pub|101||
|`AutoAdjustOptions`|class|pub|285-312|class AutoAdjustOptions|
|`AutoBrightnessOptions`|class|pub|314-344|class AutoBrightnessOptions|
|`AutoLevelsOptions`|class|pub|346-365|class AutoLevelsOptions|
|`PostprocessOptions`|class|pub|367-401|class PostprocessOptions|
|`LuminanceOptions`|class|pub|403-423|class LuminanceOptions|
|`OpenCvMergeOptions`|class|pub|425-439|class OpenCvMergeOptions|
|`AutoEvInputs`|class|pub|441-468|class AutoEvInputs|
|`_print_box_table`|fn|priv|469-505|def _print_box_table(headers, rows, header_rows=())|
|`_border`|fn|priv|489-491|def _border(left, middle, right)|
|`_line`|fn|priv|492-495|def _line(values)|
|`_build_two_line_operator_rows`|fn|priv|506-522|def _build_two_line_operator_rows(operator_entries)|
|`print_help`|fn|pub|523-722|def print_help(version)|
|`_calculate_max_ev_from_bits`|fn|priv|770-788|def _calculate_max_ev_from_bits(bits_per_color)|
|`_calculate_safe_ev_zero_max`|fn|priv|789-801|def _calculate_safe_ev_zero_max(base_max_ev)|
|`_derive_supported_ev_zero_values`|fn|priv|802-818|def _derive_supported_ev_zero_values(base_max_ev)|
|`_derive_supported_ev_values`|fn|priv|819-847|def _derive_supported_ev_values(bits_per_color, ev_zero=0.0)|
|`_detect_dng_bits_per_color`|fn|priv|848-893|def _detect_dng_bits_per_color(raw_handle)|
|`_is_ev_value_on_supported_step`|fn|priv|894-907|def _is_ev_value_on_supported_step(ev_value)|
|`_parse_ev_option`|fn|priv|908-939|def _parse_ev_option(ev_raw)|
|`_parse_ev_zero_option`|fn|priv|940-970|def _parse_ev_zero_option(ev_zero_raw)|
|`_parse_auto_ev_option`|fn|priv|971-988|def _parse_auto_ev_option(auto_ev_raw)|
|`_parse_auto_zero_option`|fn|priv|989-1006|def _parse_auto_zero_option(auto_zero_raw)|
|`_parse_percentage_option`|fn|priv|1007-1029|def _parse_percentage_option(option_name, option_raw)|
|`_parse_auto_brightness_option`|fn|priv|1030-1047|def _parse_auto_brightness_option(auto_brightness_raw)|
|`_parse_auto_levels_option`|fn|priv|1048-1065|def _parse_auto_levels_option(auto_levels_raw)|
|`_clamp_ev_to_supported`|fn|priv|1066-1079|def _clamp_ev_to_supported(ev_candidate, ev_values)|
|`_quantize_ev_to_supported`|fn|priv|1080-1101|def _quantize_ev_to_supported(ev_value, ev_values)|
|`_quantize_ev_toward_zero_step`|fn|priv|1102-1123|def _quantize_ev_toward_zero_step(ev_value, step=EV_STEP)|
|`_apply_auto_percentage_scaling`|fn|priv|1124-1138|def _apply_auto_percentage_scaling(ev_value, percentage)|
|`_extract_normalized_preview_luminance_stats`|fn|priv|1139-1198|def _extract_normalized_preview_luminance_stats(raw_handle)|
|`_percentile`|fn|priv|1173-1183|def _percentile(percentile_value)|
|`_coerce_positive_luminance`|fn|priv|1199-1218|def _coerce_positive_luminance(value, fallback)|
|`_derive_scene_key_preserving_median_target`|fn|priv|1219-1237|def _derive_scene_key_preserving_median_target(p_median)|
|`_optimize_auto_zero`|fn|priv|1238-1261|def _optimize_auto_zero(auto_ev_inputs)|
|`_optimize_adaptive_ev_delta`|fn|priv|1262-1291|def _optimize_adaptive_ev_delta(auto_ev_inputs)|
|`_compute_auto_ev_value_from_stats`|fn|priv|1292-1297|def _compute_auto_ev_value_from_stats(|
|`_compute_auto_ev_value`|fn|priv|1325-1352|def _compute_auto_ev_value(raw_handle, supported_ev_value...|
|`_resolve_ev_zero`|fn|priv|1353-1360|def _resolve_ev_zero(|
|`_resolve_ev_value`|fn|priv|1411-1418|def _resolve_ev_value(|
|`_parse_luminance_text_option`|fn|priv|1471-1491|def _parse_luminance_text_option(option_name, option_raw)|
|`_parse_gamma_option`|fn|priv|1492-1528|def _parse_gamma_option(gamma_raw)|
|`_parse_positive_float_option`|fn|priv|1529-1552|def _parse_positive_float_option(option_name, option_raw)|
|`_parse_tmo_passthrough_value`|fn|priv|1553-1569|def _parse_tmo_passthrough_value(option_name, option_raw)|
|`_parse_jpg_compression_option`|fn|priv|1570-1592|def _parse_jpg_compression_option(compression_raw)|
|`_parse_float_exclusive_range_option`|fn|priv|1593-1617|def _parse_float_exclusive_range_option(option_name, opti...|
|`_parse_non_negative_float_option`|fn|priv|1618-1640|def _parse_non_negative_float_option(option_name, option_...|
|`_parse_float_in_range_option`|fn|priv|1641-1666|def _parse_float_in_range_option(option_name, option_raw,...|
|`_parse_auto_brightness_options`|fn|priv|1667-1768|def _parse_auto_brightness_options(auto_brightness_raw_va...|
|`_parse_auto_levels_hr_method_option`|fn|priv|1769-1800|def _parse_auto_levels_hr_method_option(auto_levels_metho...|
|`_parse_auto_levels_options`|fn|priv|1801-1840|def _parse_auto_levels_options(auto_levels_raw_values)|
|`_parse_auto_adjust_options`|fn|priv|1841-1947|def _parse_auto_adjust_options(auto_adjust_raw_values)|
|`_parse_auto_adjust_mode_option`|fn|priv|1948-1971|def _parse_auto_adjust_mode_option(auto_adjust_raw)|
|`_resolve_default_postprocess`|fn|priv|1972-1976|def _resolve_default_postprocess(|
|`_parse_run_options`|fn|priv|2024-2223|def _parse_run_options(args)|
|`_load_image_dependencies`|fn|priv|2742-2779|def _load_image_dependencies()|
|`_parse_exif_datetime_to_timestamp`|fn|priv|2780-2810|def _parse_exif_datetime_to_timestamp(datetime_raw)|
|`_extract_dng_exif_payload_and_timestamp`|fn|priv|2811-2868|def _extract_dng_exif_payload_and_timestamp(pil_image_mod...|
|`_resolve_thumbnail_transpose_map`|fn|priv|2869-2900|def _resolve_thumbnail_transpose_map(pil_image_module)|
|`_apply_orientation_transform`|fn|priv|2901-2923|def _apply_orientation_transform(pil_image_module, pil_im...|
|`_build_oriented_thumbnail_jpeg_bytes`|fn|priv|2924-2925|def _build_oriented_thumbnail_jpeg_bytes(|
|`_coerce_exif_int_like_value`|fn|priv|2954-2996|def _coerce_exif_int_like_value(raw_value)|
|`_normalize_ifd_integer_like_values_for_piexif_dump`|fn|priv|2997-3130|def _normalize_ifd_integer_like_values_for_piexif_dump(pi...|
|`_refresh_output_jpg_exif_thumbnail_after_save`|fn|priv|3131-3136|def _refresh_output_jpg_exif_thumbnail_after_save(|
|`_set_output_file_timestamps`|fn|priv|3185-3199|def _set_output_file_timestamps(output_jpg, exif_timestamp)|
|`_sync_output_file_timestamps_from_exif`|fn|priv|3200-3216|def _sync_output_file_timestamps_from_exif(output_jpg, ex...|
|`_build_exposure_multipliers`|fn|priv|3217-3235|def _build_exposure_multipliers(ev_value, ev_zero=0.0)|
|`_write_bracket_images`|fn|priv|3236-3237|def _write_bracket_images(|
|`_order_bracket_paths`|fn|priv|3274-3299|def _order_bracket_paths(bracket_paths)|
|`_order_hdr_plus_reference_paths`|fn|priv|3300-3315|def _order_hdr_plus_reference_paths(bracket_paths)|
|`_run_enfuse`|fn|priv|3316-3336|def _run_enfuse(bracket_paths, merged_tiff)|
|`_run_luminance_hdr_cli`|fn|priv|3337-3338|def _run_luminance_hdr_cli(|
|`_build_ev_times_from_ev_zero_and_delta`|fn|priv|3390-3417|def _build_ev_times_from_ev_zero_and_delta(ev_zero, ev_de...|
|`_normalize_debevec_hdr_to_unit_range`|fn|priv|3418-3452|def _normalize_debevec_hdr_to_unit_range(np_module, hdr_r...|
|`_run_opencv_hdr_merge`|fn|priv|3453-3459|def _run_opencv_hdr_merge(|
|`_hdrplus_box_down2_uint16`|fn|priv|3528-3555|def _hdrplus_box_down2_uint16(np_module, frames_uint16)|
|`_hdrplus_luminance_proxy_uint16`|fn|priv|3556-3573|def _hdrplus_luminance_proxy_uint16(np_module, frames_rgb...|
|`_hdrplus_extract_overlapping_tiles`|fn|priv|3574-3579|def _hdrplus_extract_overlapping_tiles(|
|`_hdrplus_compute_temporal_weights`|fn|priv|3632-3674|def _hdrplus_compute_temporal_weights(np_module, layer_ti...|
|`_hdrplus_merge_temporal_rgb`|fn|priv|3675-3701|def _hdrplus_merge_temporal_rgb(np_module, full_tiles_rgb...|
|`_hdrplus_merge_spatial_rgb`|fn|priv|3702-3772|def _hdrplus_merge_spatial_rgb(np_module, temporal_tiles,...|
|`_run_hdr_plus_merge`|fn|priv|3773-3835|def _run_hdr_plus_merge(bracket_paths, output_hdr_tiff, i...|
|`_convert_compression_to_quality`|fn|priv|3836-3848|def _convert_compression_to_quality(jpg_compression)|
|`_resolve_imagemagick_command`|fn|priv|3849-3866|def _resolve_imagemagick_command()|
|`_resolve_auto_adjust_opencv_dependencies`|fn|priv|3867-3891|def _resolve_auto_adjust_opencv_dependencies()|
|`_resolve_numpy_dependency`|fn|priv|3892-3909|def _resolve_numpy_dependency()|
|`_to_uint8_image_array`|fn|priv|3910-3956|def _to_uint8_image_array(np_module, image_data)|
|`_to_uint16_image_array`|fn|priv|3957-4001|def _to_uint16_image_array(np_module, image_data)|
|`_normalize_uint16_rgb_image`|fn|priv|4002-4029|def _normalize_uint16_rgb_image(np_module, image_data)|
|`_validate_uint16_rgb_stage_image`|fn|priv|4030-4051|def _validate_uint16_rgb_stage_image(np_module, image_rgb...|
|`_apply_post_gamma_uint16`|fn|priv|4052-4088|def _apply_post_gamma_uint16(np_module, image_rgb_uint16,...|
|`_blend_uint16`|fn|priv|4089-4107|def _blend_uint16(np_module, base_uint16, target_uint16, ...|
|`_apply_brightness_uint16`|fn|priv|4108-4137|def _apply_brightness_uint16(np_module, image_rgb_uint16,...|
|`_apply_contrast_uint16`|fn|priv|4138-4168|def _apply_contrast_uint16(np_module, image_rgb_uint16, c...|
|`_apply_saturation_uint16`|fn|priv|4169-4204|def _apply_saturation_uint16(np_module, image_rgb_uint16,...|
|`_apply_static_postprocess_uint16`|fn|priv|4205-4245|def _apply_static_postprocess_uint16(np_module, image_rgb...|
|`_to_linear_srgb`|fn|priv|4246-4263|def _to_linear_srgb(np_module, image_srgb)|
|`_from_linear_srgb`|fn|priv|4264-4281|def _from_linear_srgb(np_module, image_linear)|
|`_compute_bt709_luminance`|fn|priv|4282-4299|def _compute_bt709_luminance(np_module, linear_rgb)|
|`_analyze_luminance_key`|fn|priv|4300-4338|def _analyze_luminance_key(np_module, luminance, eps)|
|`_choose_auto_key_value`|fn|priv|4339-4384|def _choose_auto_key_value(key_analysis, auto_brightness_...|
|`_reinhard_global_tonemap_luminance`|fn|priv|4385-4390|def _reinhard_global_tonemap_luminance(|
|`_luminance_preserving_desaturate_to_fit`|fn|priv|4424-4451|def _luminance_preserving_desaturate_to_fit(np_module, rg...|
|`_apply_mild_local_contrast_bgr_uint16`|fn|priv|4452-4487|def _apply_mild_local_contrast_bgr_uint16(cv2_module, np_...|
|`_rt_gamma2`|fn|priv|4488-4507|def _rt_gamma2(np_module, values)|
|`_rt_igamma2`|fn|priv|4508-4528|def _rt_igamma2(np_module, values)|
|`_build_autoexp_histogram_rgb_uint16`|fn|priv|4529-4555|def _build_autoexp_histogram_rgb_uint16(np_module, image_...|
|`_compute_auto_levels_from_histogram`|fn|priv|4556-4755|def _compute_auto_levels_from_histogram(np_module, histog...|
|`_apply_auto_levels_uint16`|fn|priv|4809-4872|def _apply_auto_levels_uint16(np_module, image_rgb_uint16...|
|`_hlrecovery_luminance_uint16`|fn|priv|4873-4918|def _hlrecovery_luminance_uint16(np_module, image_rgb, ma...|
|`_hlrecovery_cielab_uint16`|fn|priv|4919-4920|def _hlrecovery_cielab_uint16(|
|`_f_lab`|fn|priv|4953-4960|def _f_lab(values)|
|`_f2xyz`|fn|priv|4961-4967|def _f2xyz(values)|
|`_hlrecovery_blend_uint16`|fn|priv|5003-5105|def _hlrecovery_blend_uint16(np_module, image_rgb, hlmax,...|
|`_apply_auto_brightness_rgb_uint8`|fn|priv|5106-5170|def _apply_auto_brightness_rgb_uint8(np_module, image_rgb...|
|`_apply_validated_auto_adjust_pipeline`|fn|priv|5171-5172|def _apply_validated_auto_adjust_pipeline(|
|`_clamp01`|fn|priv|5253-5266|def _clamp01(np_module, values)|
|`_gaussian_kernel_2d`|fn|priv|5267-5289|def _gaussian_kernel_2d(np_module, sigma, radius=None)|
|`_rgb_to_hsl`|fn|priv|5290-5323|def _rgb_to_hsl(np_module, rgb)|
|`_hue_to_rgb`|fn|priv|5324-5354|def _hue_to_rgb(np_module, p_values, q_values, t_values)|
|`_hsl_to_rgb`|fn|priv|5355-5395|def _hsl_to_rgb(np_module, hue, saturation, lightness)|
|`_selective_blur_contrast_gated_vectorized`|fn|priv|5396-5397|def _selective_blur_contrast_gated_vectorized(|
|`_level_per_channel_adaptive`|fn|priv|5446-5468|def _level_per_channel_adaptive(np_module, rgb, low_pct=0...|
|`_sigmoidal_contrast`|fn|priv|5469-5493|def _sigmoidal_contrast(np_module, rgb, contrast=3.0, mid...|
|`logistic`|fn|pub|5484-5486|def logistic(z_values)|
|`_vibrance_hsl_gamma`|fn|priv|5494-5511|def _vibrance_hsl_gamma(np_module, rgb, saturation_gamma=...|
|`_gaussian_blur_rgb`|fn|priv|5512-5535|def _gaussian_blur_rgb(cv2_module, np_module, rgb, sigma)|
|`_high_pass_math_gray`|fn|priv|5536-5559|def _high_pass_math_gray(cv2_module, np_module, rgb, blur...|
|`_overlay_composite`|fn|priv|5560-5581|def _overlay_composite(np_module, base_rgb, overlay_gray)|
|`_apply_validated_auto_adjust_pipeline_opencv`|fn|priv|5582-5583|def _apply_validated_auto_adjust_pipeline_opencv(|
|`_load_piexif_dependency`|fn|priv|5662-5679|def _load_piexif_dependency()|
|`_encode_jpg`|fn|priv|5680-5692|def _encode_jpg(|
|`_collect_processing_errors`|fn|priv|5839-5867|def _collect_processing_errors(rawpy_module)|
|`_is_supported_runtime_os`|fn|priv|5868-5887|def _is_supported_runtime_os()|
|`run`|fn|pub|5888-6087|def run(args)|


---

# __init__.py | Python | 0L | 0 symbols | 0 imports | 0 comments
> Path: `src/shell_scripts/__init__.py`


---

# utils.py | Python | 28L | 4 symbols | 2 imports | 2 comments
> Path: `src/shell_scripts/utils.py`

## Imports
```
import platform
import sys
```

## Definitions

### fn `def get_runtime_os()` (L8-18)

### fn `def print_error(message)` (L19-22)

### fn `def print_info(message)` (L23-26)

### fn `def print_success(message)` (L27-28)

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`get_runtime_os`|fn|pub|8-18|def get_runtime_os()|
|`print_error`|fn|pub|19-22|def print_error(message)|
|`print_info`|fn|pub|23-26|def print_info(message)|
|`print_success`|fn|pub|27-28|def print_success(message)|

