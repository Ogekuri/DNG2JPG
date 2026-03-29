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

# dng2jpg.py | Python | 4687L | 151 symbols | 19 imports | 102 comments
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
from PIL import ImageEnhance as pil_enhance  # type: ignore
import cv2  # type: ignore
import numpy as numpy_module  # type: ignore
import piexif  # type: ignore
```

## Definitions

- var `PROGRAM = "shellscripts"` (L30)
- var `DESCRIPTION = "Convert DNG to HDR-merged JPG with optional luminance-hdr-cli backend."` (L31)
- var `DEFAULT_GAMMA = (2.222, 4.5)` (L32)
- var `DEFAULT_POST_GAMMA = 1.0` (L33)
- var `DEFAULT_BRIGHTNESS = 1.0` (L34)
- var `DEFAULT_CONTRAST = 1.0` (L35)
- var `DEFAULT_SATURATION = 1.0` (L36)
- var `DEFAULT_JPG_COMPRESSION = 15` (L37)
- var `DEFAULT_AUTO_ZERO_PCT = 50.0` (L38)
- var `DEFAULT_AUTO_EV_PCT = 50.0` (L39)
- var `DEFAULT_AA_BLUR_SIGMA = 0.9` (L40)
- var `DEFAULT_AA_BLUR_THRESHOLD_PCT = 5.0` (L41)
- var `DEFAULT_AA_LEVEL_LOW_PCT = 0.1` (L42)
- var `DEFAULT_AA_LEVEL_HIGH_PCT = 99.9` (L43)
- var `DEFAULT_AA_SIGMOID_CONTRAST = 1.8` (L44)
- var `DEFAULT_AA_SIGMOID_MIDPOINT = 0.5` (L45)
- var `DEFAULT_AA_SATURATION_GAMMA = 0.8` (L46)
- var `DEFAULT_AA_HIGHPASS_BLUR_SIGMA = 2.0` (L47)
- var `DEFAULT_AL_CLIP_PCT = 0.1` (L48)
- var `DEFAULT_AB_TARGET_GREY = 0.18` (L49)
- var `DEFAULT_AB_MAX_GAIN = 4.0` (L50)
- var `DEFAULT_AB_MIN_GAIN = 0.95` (L51)
- var `DEFAULT_AB_P98_HIGHLIGHT_MAX = 0.90` (L52)
- var `DEFAULT_AB_CORRECTION_STRENGTH = 0.35` (L53)
- var `DEFAULT_AB_MAX_EV_CORRECTION = 0.5` (L54)
- var `DEFAULT_LUMINANCE_HDR_MODEL = "debevec"` (L55)
- var `DEFAULT_LUMINANCE_HDR_WEIGHT = "flat"` (L56)
- var `DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE = "srgb"` (L57)
- var `DEFAULT_LUMINANCE_TMO = "mantiuk08"` (L58)
- var `DEFAULT_REINHARD02_BRIGHTNESS = 1.25` (L59)
- var `DEFAULT_REINHARD02_CONTRAST = 0.85` (L60)
- var `DEFAULT_REINHARD02_SATURATION = 0.55` (L61)
- var `DEFAULT_MANTIUK08_CONTRAST = 1.2` (L62)
- var `EV_STEP = 0.25` (L63)
- var `MIN_SUPPORTED_BITS_PER_COLOR = 9` (L64)
- var `DEFAULT_DNG_BITS_PER_COLOR = 14` (L65)
- var `SUPPORTED_EV_VALUES = tuple(` (L66)
- var `AUTO_EV_LOW_PERCENTILE = 0.1` (L72)
- var `AUTO_EV_HIGH_PERCENTILE = 99.9` (L73)
- var `AUTO_EV_MEDIAN_PERCENTILE = 50.0` (L74)
- var `AUTO_EV_TARGET_SHADOW = 0.05` (L75)
- var `AUTO_EV_TARGET_HIGHLIGHT = 0.90` (L76)
- var `AUTO_EV_MEDIAN_TARGET = 0.5` (L77)
- var `AUTO_ZERO_SCENE_KEY_LOW_THRESHOLD = 0.35` (L78)
- var `AUTO_ZERO_SCENE_KEY_HIGH_THRESHOLD = 0.65` (L79)
- var `AUTO_ZERO_TARGET_LOW_KEY = 0.35` (L80)
- var `AUTO_ZERO_TARGET_HIGH_KEY = 0.65` (L81)
### class `class AutoAdjustOptions` `@dataclass(frozen=True)` (L265-292)
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

### class `class AutoBrightnessOptions` `@dataclass(frozen=True)` (L294-311)
- @brief Hold `--auto-brightness` knob values.
- @details Encapsulates validated auto-brightness parameters for the BT.709 linear-sRGB luminance pipeline with light EV-domain correction and highlight-safe global gain cap.
- @param target_grey {float} Linear BT.709 middle-grey luminance target in `(0, 1)`.
- @param correction_strength {float} EV-domain correction multiplier in `(0, +inf)`.
- @param max_ev_correction {float} Positive EV correction clamp in `(0, +inf)`.
- @return {None} Immutable dataclass container.
- @satisfies REQ-065, REQ-088, REQ-089, REQ-090

### class `class AutoLevelsOptions` `@dataclass(frozen=True)` (L313-330)
- @brief Hold `--auto-levels` knob values.
- @details Encapsulates validated auto-levels parameters for RGB uint16 percentile clipping and optional highlight reconstruction stage inserted between auto-brightness and static postprocess factors.
- @param clip_pct {float} Per-side clipping percentage in `[0, 50)`.
- @param highlight_reconstruction_enabled {bool} `True` when highlight reconstruction is enabled.
- @param highlight_reconstruction_method {str|None} Reconstruction method token when enabled.
- @return {None} Immutable dataclass container.
- @satisfies REQ-053, REQ-054, REQ-055, REQ-056, REQ-057

### class `class PostprocessOptions` `@dataclass(frozen=True)` (L332-366)
- @brief Hold deterministic postprocessing option values.
- @details Encapsulates correction factors and JPEG compression level used by shared TIFF-to-JPG postprocessing for both HDR backends.
- @param post_gamma {float} Gamma correction factor for postprocessing stage.
- @param brightness {float} Brightness enhancement factor.
- @param contrast {float} Contrast enhancement factor.
- @param saturation {float} Saturation enhancement factor.
- @param jpg_compression {int} JPEG compression level in range `[0, 100]`.
- @param auto_brightness_enabled {bool} `True` when auto-brightness pre-stage is enabled.
- @param auto_brightness_options {AutoBrightnessOptions} Auto-brightness stage knobs.
- @param auto_adjust_mode {str|None} Optional auto-adjust implementation selector (`ImageMagick` or `OpenCV`).
- @param auto_adjust_options {AutoAdjustOptions} Shared auto-adjust knobs for `ImageMagick` and `OpenCV` implementations.
- @param auto_levels_enabled {bool} `True` when auto-levels stage is enabled.
- @param auto_levels_options {AutoLevelsOptions} Auto-levels stage knobs.
- @return {None} Immutable dataclass container.
- @satisfies REQ-053, REQ-054, REQ-055, REQ-056, REQ-057, REQ-065, REQ-066, REQ-069, REQ-071, REQ-072, REQ-073, REQ-075, REQ-082, REQ-083, REQ-084, REQ-086, REQ-087, REQ-088, REQ-089, REQ-090

### class `class LuminanceOptions` `@dataclass(frozen=True)` (L368-388)
- @brief Hold deterministic luminance-hdr-cli option values.
- @details Encapsulates luminance backend model and tone-mapping parameters forwarded to `luminance-hdr-cli` command generation.
- @param hdr_model {str} Luminance HDR model (`--hdrModel`).
- @param hdr_weight {str} Luminance weighting function (`--hdrWeight`).
- @param hdr_response_curve {str} Luminance response curve (`--hdrResponseCurve`).
- @param tmo {str} Tone-mapping operator (`--tmo`).
- @param tmo_extra_args {tuple[str, ...]} Explicit passthrough `--tmo*` option pairs in CLI order.
- @return {None} Immutable dataclass container.
- @satisfies REQ-061, REQ-067, REQ-068

### class `class AutoEvInputs` `@dataclass(frozen=True)` (L390-417)
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

### fn `def _print_box_table(headers, rows, header_rows=())` `priv` (L418-454)
- @brief Print one Unicode box-drawing table.
- @details Computes deterministic column widths from headers and rows, then prints aligned borders and cells using Unicode line-drawing glyphs.
- @param headers {tuple[str, ...]} Table header labels in fixed output order.
- @param header_rows {tuple[tuple[str, ...], ...]} Additional physical header rows rendered before header/body separator.
- @param rows {tuple[tuple[str, ...], ...]} Table body rows with one value per column.
- @return {None} Writes formatted table to stdout.
- @satisfies REQ-070

### fn `def _border(left, middle, right)` `priv` (L438-440)
- @brief Print one Unicode box-drawing table.
- @details Computes deterministic column widths from headers and rows, then
prints aligned borders and cells using Unicode line-drawing glyphs.
- @param headers {tuple[str, ...]} Table header labels in fixed output order.
- @param header_rows {tuple[tuple[str, ...], ...]} Additional physical header rows rendered before header/body separator.
- @param rows {tuple[tuple[str, ...], ...]} Table body rows with one value per column.
- @return {None} Writes formatted table to stdout.
- @satisfies REQ-070

### fn `def _line(values)` `priv` (L441-444)

### fn `def _build_two_line_operator_rows(operator_entries)` `priv` (L455-471)
- @brief Build two-line physical rows for luminance operator table.
- @details Expands each logical operator entry into two physical rows while preserving the bordered three-column layout used by help rendering.
- @param operator_entries {tuple[tuple[str, str, str, str, str], ...]} Logical operator rows in `(operator, family, character, neutrality, when_to_use)` format.
- @return {tuple[tuple[str, str, str], ...]} Expanded physical rows for `_print_box_table`.
- @satisfies REQ-070

### fn `def print_help(version)` (L472-671)
- @brief Print help text for the `dng2jpg` command.
- @details Documents required positional arguments, required mutually exclusive exposure selectors (`--ev` or `--auto-ev`), optional RAW gamma controls, optional `--ev-zero` and `--auto-zero` selectors, shared postprocessing controls, backend selection, and luminance-hdr-cli tone-mapping options.
- @param version {str} CLI version label to append in usage output.
- @return {None} Writes help text to stdout.
- @satisfies DES-008, REQ-053, REQ-054, REQ-055, REQ-056, REQ-057, REQ-063, REQ-069, REQ-070, REQ-071, REQ-072, REQ-073, REQ-075, REQ-082, REQ-083, REQ-084, REQ-088, REQ-089, REQ-090, REQ-091, REQ-094, REQ-097

### fn `def _calculate_max_ev_from_bits(bits_per_color)` `priv` (L678-696)
- @brief Compute EV ceiling from detected DNG bits per color.
- @details Implements `MAX=((bits_per_color-8)/2)` and validates minimum supported bit depth before computing clamp ceiling used by static and adaptive EV flows.
- @param bits_per_color {int} Detected source DNG bits per color.
- @return {float} Bit-derived EV ceiling.
- @exception ValueError Raised when bit depth is below supported minimum.
- @satisfies REQ-057, REQ-081, REQ-093, REQ-094, REQ-096

### fn `def _calculate_safe_ev_zero_max(base_max_ev)` `priv` (L697-709)
- @brief Compute safe absolute EV-zero ceiling preserving at least `±1EV` bracket.
- @details Derives `SAFE_ZERO_MAX=(BASE_MAX-1)` where `BASE_MAX=((bits_per_color-8)/2)`. Safe range guarantees `MAX_BRACKET=(BASE_MAX-abs(ev_zero)) >= 1`.
- @param base_max_ev {float} Bit-derived `BASE_MAX` value.
- @return {float} Safe absolute EV-zero ceiling.
- @satisfies REQ-093, REQ-094, REQ-096, REQ-097

### fn `def _derive_supported_ev_zero_values(base_max_ev)` `priv` (L710-726)
- @brief Derive non-negative EV-zero quantization set preserving `±1EV` bracket.
- @details Generates deterministic quarter-step tuple in `[0, SAFE_ZERO_MAX]`, where `SAFE_ZERO_MAX=max(0, BASE_MAX-1)` and `BASE_MAX=((bits_per_color-8)/2)`.
- @param base_max_ev {float} Bit-derived `BASE_MAX` value.
- @return {tuple[float, ...]} Supported non-negative EV-zero magnitudes including `0.0`.
- @satisfies REQ-093, REQ-094, REQ-096, REQ-097

### fn `def _derive_supported_ev_values(bits_per_color, ev_zero=0.0)` `priv` (L727-755)
- @brief Derive valid bracket EV selector set from bit depth and `ev_zero`.
- @details Builds deterministic EV selector tuple with fixed `0.25` step in closed range `[0.25, MAX_BRACKET]`, where `MAX_BRACKET=((bits_per_color-8)/2)-abs(ev_zero)`.
- @param bits_per_color {int} Detected source DNG bits per color.
- @param ev_zero {float} Central EV selector.
- @return {tuple[float, ...]} Supported bracket EV selector tuple.
- @exception ValueError Raised when bit-derived bracket EV ceiling cannot produce any selector values.
- @satisfies REQ-057, REQ-081, REQ-093, REQ-094, REQ-096

### fn `def _detect_dng_bits_per_color(raw_handle)` `priv` (L756-801)
- @brief Detect source DNG bits-per-color from RAW metadata.
- @details Prefers RAW sample container bit depth from `raw_handle.raw_image_visible.dtype.itemsize * 8` because the DNG white level can represent effective sensor range (for example `4000`) while RAW samples are still stored in a wider container (for example `uint16`). Falls back to `raw_handle.white_level` `bit_length` when container metadata is unavailable.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {int} Detected source DNG bits per color.
- @exception ValueError Raised when metadata is missing, non-numeric, or non-positive.
- @satisfies REQ-057, REQ-081, REQ-092, REQ-093

### fn `def _is_ev_value_on_supported_step(ev_value)` `priv` (L802-815)
- @brief Validate EV value belongs to fixed `0.25` step grid.
- @details Checks whether EV value can be represented as integer multiples of `0.25` using tolerance-based floating-point comparison.
- @param ev_value {float} Parsed EV numeric value.
- @return {bool} `True` when EV value is aligned to `0.25` step.
- @satisfies REQ-057

### fn `def _parse_ev_option(ev_raw)` `priv` (L816-847)
- @brief Parse and validate one EV option value.
- @details Converts token to `float`, enforces minimum `0.25`, and enforces fixed `0.25` granularity. Bit-depth upper-bound validation is deferred until RAW metadata is loaded from source DNG.
- @param ev_raw {str} EV token extracted from command arguments.
- @return {float|None} Parsed EV value when valid; `None` otherwise.
- @satisfies REQ-056, REQ-057

### fn `def _parse_ev_zero_option(ev_zero_raw)` `priv` (L848-878)
- @brief Parse and validate one `--ev-zero` option value.
- @details Converts token to `float`, enforces fixed `0.25` granularity, and defers bit-depth bound validation to RAW-metadata runtime stage.
- @param ev_zero_raw {str} EV-zero token extracted from command arguments.
- @return {float|None} Parsed EV-zero value when valid; `None` otherwise.
- @satisfies REQ-094

### fn `def _parse_auto_ev_option(auto_ev_raw)` `priv` (L879-896)
- @brief Parse and validate one `--auto-ev` option value.
- @details Accepts only boolean-like activator tokens (`1`, `true`, `yes`, `on`) and rejects all other values to keep deterministic CLI behavior.
- @param auto_ev_raw {str} Raw `--auto-ev` value token from CLI args.
- @return {bool|None} `True` when token enables adaptive mode; `None` on parse failure.
- @satisfies REQ-056

### fn `def _parse_auto_zero_option(auto_zero_raw)` `priv` (L897-914)
- @brief Parse and validate one `--auto-zero` option value.
- @details Accepts only boolean-like activator tokens (`1`, `true`, `yes`, `on`) and rejects all other values to keep deterministic CLI behavior.
- @param auto_zero_raw {str} Raw `--auto-zero` value token from CLI args.
- @return {bool|None} `True` when token enables automatic EV-zero mode; `None` on parse failure.
- @satisfies REQ-094

### fn `def _parse_percentage_option(option_name, option_raw)` `priv` (L915-937)
- @brief Parse and validate one percentage option value.
- @details Converts option token to `float`, requires inclusive range `[0, 100]`, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {float|None} Parsed percentage value when valid; `None` otherwise.
- @satisfies REQ-081, REQ-094, REQ-097

### fn `def _parse_auto_brightness_option(auto_brightness_raw)` `priv` (L938-955)
- @brief Parse and validate one `--auto-brightness` option value.
- @details Accepts only boolean-like activator tokens (`1`, `true`, `yes`, `on`) and rejects all other values to keep deterministic CLI behavior.
- @param auto_brightness_raw {str} Raw `--auto-brightness` value token from CLI args.
- @return {bool|None} `True` when token enables auto-brightness; `None` on parse failure.
- @satisfies REQ-065, REQ-089

### fn `def _parse_auto_levels_option(auto_levels_raw)` `priv` (L956-973)
- @brief Parse and validate one `--auto-levels` option value.
- @details Accepts only boolean-like activator tokens (`1`, `true`, `yes`, `on`) and rejects all other values to keep deterministic CLI behavior.
- @param auto_levels_raw {str} Raw `--auto-levels` value token from CLI args.
- @return {bool|None} `True` when token enables auto-levels; `None` on parse failure.
- @satisfies REQ-053, REQ-054

### fn `def _parse_auto_levels_highlight_reconstruction_option(option_raw)` `priv` (L974-993)
- @brief Parse and validate `--al-highlight-reconstruction` boolean option.
- @details Accepts deterministic boolean-like tokens for explicit enable/disable of auto-level highlight reconstruction behavior.
- @param option_raw {str} Raw option value token from CLI args.
- @return {bool|None} Parsed boolean value when valid; `None` otherwise.
- @satisfies REQ-056, REQ-057

### fn `def _parse_auto_levels_highlight_reconstruction_method(option_raw)` `priv` (L994-1023)
- @brief Parse and validate `--al-highlight-reconstruction-method` option.
- @details Accepts case-insensitive highlight reconstruction method names and normalizes them to canonical runtime selector tokens.
- @param option_raw {str} Raw method token from CLI args.
- @return {str|None} Canonical method token when valid; `None` otherwise.
- @satisfies REQ-056, REQ-057

### fn `def _clamp_ev_to_supported(ev_candidate, ev_values)` `priv` (L1024-1037)
- @brief Clamp one EV candidate to supported numeric interval.
- @details Applies lower/upper bound clamp to keep computed adaptive EV value inside configured EV bounds before command generation.
- @param ev_candidate {float} Candidate EV delta from adaptive optimization.
- @param ev_values {tuple[float, ...]} Sorted supported EV selector values.
- @return {float} Clamped EV delta in `[min(ev_values), max(ev_values)]`.
- @satisfies REQ-081, REQ-093

### fn `def _quantize_ev_to_supported(ev_value, ev_values)` `priv` (L1038-1059)
- @brief Quantize one EV value to nearest supported selector value.
- @details Chooses nearest value from `ev_values` to preserve deterministic three-bracket behavior in downstream static multiplier and HDR command construction paths.
- @param ev_value {float} Clamped EV value.
- @param ev_values {tuple[float, ...]} Sorted supported EV selector values.
- @return {float} Nearest supported EV selector value.
- @satisfies REQ-080, REQ-081, REQ-093

### fn `def _quantize_ev_toward_zero_step(ev_value, step=EV_STEP)` `priv` (L1060-1081)
- @brief Quantize one EV value toward zero using fixed step size.
- @details Converts EV value to step units, truncates fractional remainder toward zero, and reconstructs signed EV value using deterministic `0.25` precision rounding.
- @param ev_value {float} EV value to quantize.
- @param step {float} Quantization step size.
- @return {float} Quantized EV value with truncation toward zero.
- @satisfies REQ-081, REQ-097

### fn `def _apply_auto_percentage_scaling(ev_value, percentage)` `priv` (L1082-1096)
- @brief Apply percentage scaling to EV value with downward 0.25 quantization.
- @details Multiplies EV value by percentage in `[0,100]` and quantizes scaled result toward zero with fixed `0.25` step.
- @param ev_value {float} EV value before scaling.
- @param percentage {float} Percentage scaling factor in `[0,100]`.
- @return {float} Scaled EV value quantized toward zero.
- @satisfies REQ-081, REQ-097

### fn `def _extract_normalized_preview_luminance_stats(raw_handle)` `priv` (L1097-1156)
- @brief Extract normalized preview luminance percentiles from RAW handle.
- @details Generates one deterministic linear preview (`bright=1.0`, `output_bps=16`, camera white balance, no auto-bright, linear gamma, `user_flip=0`), computes luminance for each pixel, then returns normalized low/median/high percentiles by dividing with preview maximum luminance.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {tuple[float, float, float]} Normalized `(p_low, p_median, p_high)` in `(0,1)`.
- @exception ValueError Raised when preview extraction cannot produce valid luminance values.
- @satisfies REQ-080, REQ-081, REQ-092, REQ-093, REQ-097

### fn `def _percentile(percentile_value)` `priv` (L1131-1141)
- @brief Extract normalized preview luminance percentiles from RAW handle.
- @details Generates one deterministic linear preview (`bright=1.0`,
`output_bps=16`, camera white balance, no auto-bright, linear gamma,
`user_flip=0`), computes luminance for each pixel, then returns normalized
low/median/high percentiles by dividing with preview maximum luminance.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {tuple[float, float, float]} Normalized `(p_low, p_median, p_high)` in `(0,1)`.
- @exception ValueError Raised when preview extraction cannot produce valid luminance values.
- @satisfies REQ-080, REQ-081, REQ-092, REQ-093, REQ-097

### fn `def _coerce_positive_luminance(value, fallback)` `priv` (L1157-1176)
- @brief Coerce luminance scalar to positive range for logarithmic math.
- @details Converts input to float and enforces a strictly positive minimum. Returns fallback when conversion fails or result is non-positive.
- @param value {object} Candidate luminance scalar.
- @param fallback {float} Fallback positive luminance scalar.
- @return {float} Positive luminance value suitable for `log2`.
- @satisfies REQ-081

### fn `def _derive_scene_key_preserving_median_target(p_median)` `priv` (L1177-1195)
- @brief Derive scene-key-preserving median target for auto-zero optimization.
- @details Classifies scene key from normalized preview median luminance and maps it to a bounded median target preserving low-key/high-key intent while enabling exposure correction. Low-key medians map to a low-key target, high-key medians map to a high-key target, and mid-key medians map to neutral target `0.5`.
- @param p_median {float} Normalized median luminance in `(0.0, 1.0)`.
- @return {float} Scene-key-preserving median target in `(0.0, 1.0)`.
- @satisfies REQ-097, REQ-098

### fn `def _optimize_auto_zero(auto_ev_inputs)` `priv` (L1196-1219)
- @brief Compute optimal EV-zero center from normalized luminance statistics.
- @details Solves `ev_zero=log2(target_median/p_median)` using a scene-key-preserving target derived from preview median luminance, clamps result to `[-SAFE_ZERO_MAX,+SAFE_ZERO_MAX]` where `SAFE_ZERO_MAX=max(ev_values)`, and quantizes to nearest quarter-step represented by `ev_values` with sign preservation.
- @param auto_ev_inputs {AutoEvInputs} Adaptive EV scalar inputs.
- @return {float} Quantized EV-zero center.
- @satisfies REQ-094, REQ-095, REQ-097, REQ-098

### fn `def _optimize_adaptive_ev_delta(auto_ev_inputs)` `priv` (L1220-1249)
- @brief Compute adaptive EV delta from preview luminance statistics.
- @details Computes symmetric delta constraints around resolved EV-zero: `ev_shadow=max(0, log2(target_shadow/p_low)-ev_zero)` and `ev_high=max(0, ev_zero-log2(target_highlight/p_high))`, chooses maximum as safe symmetric bracket half-width, then clamps and quantizes to supported EV selector set.
- @param auto_ev_inputs {AutoEvInputs} Adaptive EV scalar inputs.
- @return {float} Quantized adaptive EV delta.
- @satisfies REQ-080, REQ-081, REQ-093, REQ-095

### fn `def _compute_auto_ev_value_from_stats(` `priv` (L1250-1255)

### fn `def _compute_auto_ev_value(raw_handle, supported_ev_values=None, ev_zero=0.0)` `priv` (L1283-1310)
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

### fn `def _resolve_ev_zero(` `priv` (L1311-1318)

### fn `def _resolve_ev_value(` `priv` (L1369-1376)
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

### fn `def _parse_luminance_text_option(option_name, option_raw)` `priv` (L1429-1449)
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

### fn `def _parse_gamma_option(gamma_raw)` `priv` (L1450-1486)
- @brief Parse and validate one gamma option value pair.
- @details Accepts comma-separated positive float pair in `a,b` format with optional surrounding parentheses, normalizes to `(a, b)` tuple, and rejects malformed, non-numeric, or non-positive values.
- @param gamma_raw {str} Raw gamma token extracted from CLI args.
- @return {tuple[float, float]|None} Parsed gamma tuple when valid; `None` otherwise.
- @satisfies REQ-064

### fn `def _parse_positive_float_option(option_name, option_raw)` `priv` (L1487-1510)
- @brief Parse and validate one positive float option value.
- @details Converts option token to `float`, requires value greater than zero, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {float|None} Parsed positive float value when valid; `None` otherwise.
- @satisfies REQ-065

### fn `def _parse_tmo_passthrough_value(option_name, option_raw)` `priv` (L1511-1527)
- @brief Parse and validate one luminance `--tmo*` passthrough value.
- @details Rejects empty values and preserves original payload for transparent forwarding to `luminance-hdr-cli`.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {str|None} Original value when valid; `None` otherwise.
- @satisfies REQ-067

### fn `def _parse_jpg_compression_option(compression_raw)` `priv` (L1528-1550)
- @brief Parse and validate JPEG compression option value.
- @details Converts option token to `int`, requires inclusive range `[0, 100]`, and emits deterministic parse errors on malformed values.
- @param compression_raw {str} Raw compression token value from CLI args.
- @return {int|None} Parsed JPEG compression level when valid; `None` otherwise.
- @satisfies REQ-065

### fn `def _parse_float_exclusive_range_option(option_name, option_raw, min_value, max_value)` `priv` (L1551-1575)
- @brief Parse and validate one float option in an exclusive range.
- @details Converts option token to `float`, validates `min < value < max`, and emits deterministic parse errors on malformed or out-of-range values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @param min_value {float} Exclusive minimum bound.
- @param max_value {float} Exclusive maximum bound.
- @return {float|None} Parsed float value when valid; `None` otherwise.
- @satisfies REQ-065, REQ-089

### fn `def _parse_non_negative_float_option(option_name, option_raw)` `priv` (L1576-1598)
- @brief Parse and validate one non-negative float option value.
- @details Converts option token to `float`, requires value greater than or equal to zero, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {float|None} Parsed non-negative float value when valid; `None` otherwise.
- @satisfies REQ-065, REQ-089

### fn `def _parse_float_in_range_option(option_name, option_raw, min_value, max_value)` `priv` (L1599-1624)
- @brief Parse and validate one float option constrained to inclusive range.
- @details Converts option token to `float`, validates inclusive bounds, and emits deterministic parse errors on malformed or out-of-range values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @param min_value {float} Inclusive minimum bound.
- @param max_value {float} Inclusive maximum bound.
- @return {float|None} Parsed bounded float value when valid; `None` otherwise.
- @satisfies REQ-082, REQ-084

### fn `def _parse_auto_brightness_options(auto_brightness_raw_values)` `priv` (L1625-1648)
- @brief Parse and validate auto-brightness parameters.
- @details Parses optional linear BT.709 target-grey selector and applies deterministic defaults for omitted auto-brightness options.
- @param auto_brightness_raw_values {dict[str, str]} Raw `--ab-*` option values keyed by long option name.
- @return {AutoBrightnessOptions|None} Parsed auto-brightness options or `None` on validation error.
- @satisfies REQ-088, REQ-089

### fn `def _parse_auto_levels_options(auto_levels_raw_values)` `priv` (L1649-1716)
- @brief Parse and validate auto-levels parameters.
- @details Parses optional clip percentage and optional highlight reconstruction controls, applies deterministic defaults for omitted values, and validates required method binding when reconstruction is enabled.
- @param auto_levels_raw_values {dict[str, str]} Raw `--al-*` option values keyed by long option name.
- @return {AutoLevelsOptions|None} Parsed auto-levels options or `None` on validation error.
- @satisfies REQ-054, REQ-055, REQ-056, REQ-057

### fn `def _parse_auto_adjust_options(auto_adjust_raw_values)` `priv` (L1717-1823)
- @brief Parse and validate shared auto-adjust knobs for both implementations.
- @details Applies defaults for omitted knobs, validates scalar/range constraints, and enforces level percentile ordering contract.
- @param auto_adjust_raw_values {dict[str, str]} Raw `--aa-*` option values keyed by long option name.
- @return {AutoAdjustOptions|None} Parsed shared auto-adjust options or `None` on validation error.
- @satisfies REQ-082, REQ-083, REQ-084

### fn `def _parse_auto_adjust_mode_option(auto_adjust_raw)` `priv` (L1824-1847)
- @brief Parse auto-adjust implementation selector option value.
- @details Accepts case-insensitive auto-adjust implementation names and normalizes to canonical values for runtime dispatch.
- @param auto_adjust_raw {str} Raw auto-adjust implementation token.
- @return {str|None} Canonical auto-adjust mode (`ImageMagick` or `OpenCV`) or `None` on parse failure.
- @satisfies REQ-065, REQ-073, REQ-075

### fn `def _resolve_default_postprocess(enable_luminance, luminance_tmo)` `priv` (L1848-1890)
- @brief Resolve backend-specific postprocess defaults.
- @details Selects neutral defaults for enfuse and non-tuned luminance operators, and selects tuned defaults for luminance `reinhard02` and `mantiuk08`.
- @param enable_luminance {bool} Backend selector state.
- @param luminance_tmo {str} Selected luminance tone-mapping operator.
- @return {tuple[float, float, float, float]} Defaults in `(post_gamma, brightness, contrast, saturation)` order.
- @satisfies REQ-069, REQ-071, REQ-072, REQ-091

### fn `def _parse_run_options(args)` `priv` (L1891-2090)
- @brief Parse CLI args into input, output, and EV parameters.
- @details Supports positional file arguments, required mutually exclusive exposure selectors (`--ev=<value>`/`--ev <value>` or `--auto-ev[=<1|true|yes|on>]`), optional `--ev-zero=<value>` or `--ev-zero <value>`, optional `--auto-zero[=<1|true|yes|on>]`, optional `--auto-zero-pct=<0..100>`, optional `--auto-ev-pct=<0..100>`, optional `--gamma=<a,b>` or `--gamma <a,b>`, optional postprocess controls, optional auto-brightness stage and `--ab-target-grey` knob, optional auto-levels stage and `--al-*` knobs, optional shared auto-adjust knobs, required backend selector (`--enable-enfuse` or `--enable-luminance`), and luminance backend controls including explicit `--tmo*` passthrough options and optional auto-adjust implementation selector (`--auto-adjust <ImageMagick|OpenCV>`); rejects unknown options and invalid arity.
- @param args {list[str]} Raw command argument vector.
- @return {tuple[Path, Path, float|None, bool, tuple[float, float], PostprocessOptions, bool, LuminanceOptions, float, bool, float, float]|None} Parsed `(input, output, ev, auto_ev, gamma, postprocess, enable_luminance, luminance_options, ev_zero, auto_zero_enabled, auto_zero_pct, auto_ev_pct)` tuple; `None` on parse failure.
- @satisfies REQ-053, REQ-054, REQ-055, REQ-056, REQ-057, REQ-060, REQ-061, REQ-064, REQ-065, REQ-067, REQ-069, REQ-071, REQ-072, REQ-073, REQ-075, REQ-079, REQ-080, REQ-081, REQ-082, REQ-083, REQ-084, REQ-085, REQ-087, REQ-088, REQ-089, REQ-090, REQ-091, REQ-094, REQ-097

### fn `def _load_image_dependencies()` `priv` (L2610-2648)
- @brief Load optional Python dependencies required by `dng2jpg`.
- @details Imports `rawpy` for RAW decoding and `imageio` for image IO using `imageio.v3` when available with fallback to top-level `imageio` module.
- @return {tuple[ModuleType, ModuleType, ModuleType, ModuleType]|None} `(rawpy_module, imageio_module, pil_image_module, pil_enhance_module)` on success; `None` on missing dependency.
- @satisfies REQ-059, REQ-066, REQ-074

### fn `def _parse_exif_datetime_to_timestamp(datetime_raw)` `priv` (L2649-2679)
- @brief Parse one EXIF datetime token into POSIX timestamp.
- @details Normalizes scalar EXIF datetime input (`str` or `bytes`), trims optional null-terminated EXIF payload suffix, and parses strict EXIF format `YYYY:MM:DD HH:MM:SS` to generate filesystem timestamp.
- @param datetime_raw {str|bytes|object} EXIF datetime scalar.
- @return {float|None} Parsed POSIX timestamp; `None` when value is missing or invalid.
- @satisfies REQ-074, REQ-077

### fn `def _extract_dng_exif_payload_and_timestamp(pil_image_module, input_dng)` `priv` (L2680-2737)
- @brief Extract DNG EXIF payload bytes, preferred datetime timestamp, and source orientation.
- @details Opens input DNG via Pillow, suppresses known non-actionable `PIL.TiffImagePlugin` metadata warning for malformed TIFF tag `33723`, reads EXIF mapping without orientation mutation, serializes payload for JPEG save while source image handle is still open, resolves source orientation from EXIF tag `274`, and resolves filesystem timestamp priority: `DateTimeOriginal`(36867) > `DateTimeDigitized`(36868) > `DateTime`(306).
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @param input_dng {Path} Source DNG path.
- @return {tuple[bytes|None, float|None, int]} `(exif_payload, exif_timestamp, source_orientation)` with orientation defaulting to `1`.
- @satisfies REQ-066, REQ-074, REQ-077

### fn `def _resolve_thumbnail_transpose_map(pil_image_module)` `priv` (L2738-2769)
- @brief Build deterministic EXIF-orientation-to-transpose mapping.
- @details Resolves Pillow transpose constants from modern `Image.Transpose` namespace with fallback to legacy module-level constants.
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @return {dict[int, int]} Orientation-to-transpose mapping for values `2..8`.
- @satisfies REQ-077, REQ-078

### fn `def _apply_orientation_transform(pil_image_module, pil_image, source_orientation)` `priv` (L2770-2792)
- @brief Apply EXIF orientation transform to one image copy.
- @details Produces display-oriented pixels from source-oriented input while preserving the original image object and preserving orientation invariants in the main processing pipeline.
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @param pil_image {object} Pillow image-like object.
- @param source_orientation {int} EXIF orientation value in range `1..8`.
- @return {object} Transformed Pillow image object.
- @satisfies REQ-077, REQ-078

### fn `def _build_oriented_thumbnail_jpeg_bytes(` `priv` (L2793-2794)

### fn `def _coerce_exif_int_like_value(raw_value)` `priv` (L2823-2865)
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

### fn `def _normalize_ifd_integer_like_values_for_piexif_dump(piexif_module, exif_dict)` `priv` (L2866-2999)
- @brief Normalize integer-like IFD values before `piexif.dump`.
- @details Traverses EXIF IFD mappings (`0th`, `Exif`, `GPS`, `Interop`, `1st`) and coerces integer-like values that can trigger `piexif.dump` packing failures when represented as strings or other non-int scalars. Tuple/list values are normalized only when all items are integer-like. For integer sequence tag types, nested two-item pairs are flattened to a single integer sequence for `piexif.dump` compatibility. Scalar conversion is additionally constrained by `piexif.TAGS` integer field types when tag metadata is available.
- @param piexif_module {ModuleType} Imported piexif module.
- @param exif_dict {dict[str, object]} EXIF dictionary loaded via piexif.
- @return {None} Mutates `exif_dict` in place.
- @satisfies REQ-066, REQ-077, REQ-078

### fn `def _refresh_output_jpg_exif_thumbnail_after_save(` `priv` (L3000-3005)

### fn `def _set_output_file_timestamps(output_jpg, exif_timestamp)` `priv` (L3054-3068)
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

### fn `def _sync_output_file_timestamps_from_exif(output_jpg, exif_timestamp)` `priv` (L3069-3085)
- @brief Synchronize output JPG atime/mtime from optional EXIF timestamp.
- @details Provides one dedicated call site for filesystem timestamp sync and applies update only when EXIF datetime parsing produced a valid POSIX value.
- @param output_jpg {Path} Output JPG path.
- @param exif_timestamp {float|None} Source EXIF-derived POSIX timestamp.
- @return {None} Side effects only.
- @exception OSError Raised when filesystem metadata update fails.
- @satisfies REQ-074, REQ-077

### fn `def _build_exposure_multipliers(ev_value, ev_zero=0.0)` `priv` (L3086-3104)
- @brief Compute bracketing brightness multipliers from EV delta and center.
- @details Produces exactly three multipliers mapped to exposure stops `[ev_zero-ev, ev_zero, ev_zero+ev]` as powers of two for RAW postprocess brightness control.
- @param ev_value {float} Exposure bracket EV delta.
- @param ev_zero {float} Central bracket EV value.
- @return {tuple[float, float, float]} Multipliers in order `(under, base, over)`.
- @satisfies REQ-057, REQ-077, REQ-079, REQ-080, REQ-092, REQ-093, REQ-095

### fn `def _write_bracket_images(` `priv` (L3105-3106)

### fn `def _order_bracket_paths(bracket_paths)` `priv` (L3143-3168)
- @brief Materialize three bracket TIFF files from one RAW handle.
- @brief Validate and reorder bracket TIFF paths for deterministic backend argv.
- @details Invokes `raw.postprocess` with `output_bps=16`,
`use_camera_wb=True`, `no_auto_bright=True`, explicit `user_flip=0` to
disable implicit RAW orientation mutation, and configurable gamma pair for
deterministic HDR-oriented bracket extraction before merge.
- @details Enforces exact exposure order `<ev_minus.tif> <ev_zero.tif> <ev_plus.tif>` required by luminance-hdr-cli command generation and raises on missing labels.
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
- @satisfies REQ-062

### fn `def _run_enfuse(bracket_paths, merged_tiff)` `priv` (L3169-3189)
- @brief Merge bracket TIFF files into one HDR TIFF via `enfuse`.
- @details Builds deterministic enfuse argv with LZW compression and executes subprocess in checked mode to propagate command failures.
- @param bracket_paths {list[Path]} Ordered intermediate exposure TIFF paths.
- @param merged_tiff {Path} Output merged TIFF target path.
- @return {None} Side effects only.
- @exception subprocess.CalledProcessError Raised when `enfuse` returns non-zero exit status.
- @satisfies REQ-058, REQ-077

### fn `def _run_luminance_hdr_cli(` `priv` (L3190-3191)

### fn `def _convert_compression_to_quality(jpg_compression)` `priv` (L3243-3255)
- @brief Merge bracket TIFF files into one HDR TIFF via `luminance-hdr-cli`.
- @brief Convert JPEG compression level to Pillow quality value.
- @details Builds deterministic luminance-hdr-cli argv using EV sequence
centered around zero-reference (`-ev_value,0,+ev_value`) even when extraction
uses non-zero `ev_zero`,
HDR model controls, tone-mapper controls, mandatory `--ldrTiff 16b`,
optional explicit `--tmo*` passthrough arguments, and ordered exposure
inputs (`ev_minus`, `ev_zero`, `ev_plus`), then writes to TIFF output path
used by shared postprocess conversion. Executes subprocess in output-TIFF
parent directory to isolate backend-generated sidecar artifacts (e.g. `.pp3`)
inside command temporary workspace lifecycle.
- @details Maps inclusive compression range `[0, 100]` to inclusive quality range `[100, 1]` preserving deterministic inverse relation.
- @param bracket_paths {list[Path]} Ordered intermediate exposure TIFF paths.
- @param output_hdr_tiff {Path} Output HDR TIFF target path.
- @param ev_value {float} EV bracket delta used to generate exposure files.
- @param ev_zero {float} Central EV used to generate exposure files.
- @param luminance_options {LuminanceOptions} Luminance backend command controls.
- @param jpg_compression {int} JPEG compression level.
- @return {None} Side effects only.
- @return {int} Pillow quality value in `[1, 100]`.
- @exception subprocess.CalledProcessError Raised when `luminance-hdr-cli` returns non-zero exit status.
- @satisfies REQ-060, REQ-061, REQ-062, REQ-067, REQ-068, REQ-077, REQ-080, REQ-095
- @satisfies REQ-065, REQ-066

### fn `def _resolve_imagemagick_command()` `priv` (L3256-3273)
- @brief Resolve ImageMagick executable name for current runtime.
- @details Probes `magick` first (ImageMagick 7+ preferred CLI), then `convert` (legacy-compatible CLI alias) to preserve auto-adjust-stage compatibility across distributions that package ImageMagick under different executable names.
- @return {str|None} Resolved executable token (`magick` or `convert`) or `None` when no supported executable is available.
- @satisfies REQ-059, REQ-073

### fn `def _resolve_auto_adjust_opencv_dependencies()` `priv` (L3274-3298)
- @brief Resolve OpenCV runtime dependencies for image-domain stages.
- @details Imports `cv2` and `numpy` modules required by OpenCV auto-adjust pipeline, auto-brightness pre-stage, and auto-levels pre-stage execution, and returns `None` with deterministic error output when dependencies are missing.
- @return {tuple[ModuleType, ModuleType]|None} `(cv2_module, numpy_module)` when available; `None` on dependency failure.
- @satisfies REQ-053, REQ-055, REQ-056, REQ-057, REQ-059, REQ-073, REQ-075, REQ-090

### fn `def _to_uint8_image_array(np_module, image_data)` `priv` (L3299-3345)
- @brief Convert image tensor to `uint8` range `[0,255]`.
- @details Normalizes integer or float image payloads into `uint8` preserving relative brightness scale: `uint16` uses `/257`, normalized float arrays in `[0,1]` use `*255`, and all paths clamp to inclusive byte range.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image tensor.
- @return {object} `uint8` image tensor.
- @satisfies REQ-066, REQ-090

### fn `def _to_uint16_image_array(np_module, image_data)` `priv` (L3346-3390)
- @brief Convert image tensor to `uint16` range `[0,65535]`.
- @details Normalizes integer or float image payloads into `uint16` preserving relative brightness scale: `uint8` uses `*257`, normalized float arrays in `[0,1]` use `*65535`, and all paths clamp to inclusive 16-bit range.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image tensor.
- @return {object} `uint16` image tensor.
- @satisfies REQ-066, REQ-090

### fn `def _to_linear_srgb(np_module, image_srgb)` `priv` (L3391-3408)
- @brief Convert sRGB tensor to linear-sRGB tensor.
- @details Applies IEC 61966-2-1 piecewise inverse transfer function on normalized channel values in `[0,1]`.
- @param np_module {ModuleType} Imported numpy module.
- @param image_srgb {object} Float image tensor in sRGB domain `[0,1]`.
- @return {object} Float image tensor in linear-sRGB domain `[0,1]`.
- @satisfies REQ-090, REQ-099

### fn `def _from_linear_srgb(np_module, image_linear)` `priv` (L3409-3426)
- @brief Convert linear-sRGB tensor to sRGB tensor.
- @details Applies IEC 61966-2-1 piecewise forward transfer function on normalized linear channel values in `[0,1]`.
- @param np_module {ModuleType} Imported numpy module.
- @param image_linear {object} Float image tensor in linear-sRGB domain `[0,1]`.
- @return {object} Float image tensor in sRGB domain `[0,1]`.
- @satisfies REQ-090, REQ-099

### fn `def _compute_bt709_luminance(np_module, linear_rgb)` `priv` (L3427-3444)
- @brief Compute BT.709 linear luminance from linear RGB tensor.
- @details Computes per-pixel luminance using BT.709 coefficients with RGB channel order: `0.2126*R + 0.7152*G + 0.0722*B`.
- @param np_module {ModuleType} Imported numpy module.
- @param linear_rgb {object} Linear-sRGB float tensor with shape `H,W,3`.
- @return {object} Float luminance tensor with shape `H,W`.
- @satisfies REQ-090, REQ-099

### fn `def _apply_highlight_rolloff(np_module, linear_rgb)` `priv` (L3445-3463)
- @brief Apply global highlight rolloff on linear RGB tensor.
- @details Applies Reinhard-style two-step rolloff when any channel exceeds `1.0`, then clamps to `[0,1]`.
- @param np_module {ModuleType} Imported numpy module.
- @param linear_rgb {object} Linear-sRGB float tensor.
- @return {object} Rolloff-compressed linear-sRGB float tensor.
- @satisfies REQ-090

### fn `def _apply_auto_brightness_rgb_uint8(` `priv` (L3464-3465)

### fn `def _reconstruct_highlights_luminance(np_module, linear_rgb, clipped_mask)` `priv` (L3523-3549)
- @brief Apply BT.709 linear-sRGB auto-brightness on uint16 RGB tensor.
- @brief Reconstruct clipped highlights using luminance-preserving scaling.
- @details Executes pipeline: uint16 normalization to `[0,1]` in float64,
sRGB linearization, BT.709 luminance extraction, percentile statistics
(`p50`, `p98`), raw gain `target_grey/p50`, EV-domain light correction
`clamp(log2(raw_gain)*correction_strength,0,+max_ev_correction)`,
global gain `2^ev` constrained by fixed gain cap `4.0` and highlight-safe
cap `max(0.95,0.90/max(p98,1e-7))`, highlight rolloff, inverse sRGB
transfer, and uint16 restoration.
- @details Computes channel luminance before clipping and rescales clipped pixels to preserve luminance while constraining channels to `[0,1]`.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_uint8 {object} RGB uint16 image tensor.
- @param auto_brightness_options {AutoBrightnessOptions} Parsed auto-brightness parameters.
- @param np_module {ModuleType} Imported numpy module.
- @param linear_rgb {object} Linear RGB float tensor in `[0,1]`.
- @param clipped_mask {object} Boolean clipped-pixel mask.
- @return {object} RGB uint16 image tensor after BT.709 auto-brightness.
- @return {object} Highlight-reconstructed linear RGB tensor.
- @exception ValueError Raised when input tensor is not uint16 RGB.
- @satisfies REQ-066, REQ-090, REQ-099
- @satisfies REQ-056, REQ-057

### fn `def _reconstruct_highlights_cielab_blending(cv2_module, np_module, linear_rgb, clipped_mask)` `priv` (L3550-3583)
- @brief Reconstruct clipped highlights using CIELab chroma blending.
- @details Converts linear RGB to Lab space, attenuates chroma channels in clipped regions, and restores RGB from blended Lab payload.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param linear_rgb {object} Linear RGB float tensor in `[0,1]`.
- @param clipped_mask {object} Boolean clipped-pixel mask.
- @return {object} Highlight-reconstructed linear RGB tensor.
- @satisfies REQ-056, REQ-057

### fn `def _reconstruct_highlights_blend(np_module, linear_rgb, clipped_mask)` `priv` (L3584-3607)
- @brief Reconstruct clipped highlights using source-neighborhood blending.
- @details Blends clipped pixels with per-row and per-column neighborhood means to reduce hard clipping artifacts while preserving local color tendencies.
- @param np_module {ModuleType} Imported numpy module.
- @param linear_rgb {object} Linear RGB float tensor in `[0,1]`.
- @param clipped_mask {object} Boolean clipped-pixel mask.
- @return {object} Highlight-reconstructed linear RGB tensor.
- @satisfies REQ-056, REQ-057

### fn `def _apply_auto_levels_rgb_uint16(` `priv` (L3608-3609)

### fn `def _apply_validated_auto_adjust_pipeline(` `priv` (L3674-3675)
- @brief Apply auto-levels stage on RGB uint16 tensor.
- @details Executes percentile clipping in linear domain using one per-side
clip percentage and optional highlight reconstruction with required method.
Returns uint16 payload preserving high bit-depth path compatibility.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_uint16 {object} RGB uint16 image tensor.
- @param auto_levels_options {AutoLevelsOptions} Parsed auto-levels parameters.
- @return {object} RGB uint16 image tensor after auto-levels stage.
- @exception ValueError Raised when input tensor is not uint16 RGB.
- @exception RuntimeError Raised when highlight reconstruction method is invalid.
- @satisfies REQ-053, REQ-055, REQ-056, REQ-057

### fn `def _clamp01(np_module, values)` `priv` (L3756-3769)
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

### fn `def _gaussian_kernel_2d(np_module, sigma, radius=None)` `priv` (L3770-3792)
- @brief Build normalized 2D Gaussian kernel.
- @details Creates deterministic Gaussian kernel used by selective blur stage; returns identity kernel when `sigma <= 0`.
- @param np_module {ModuleType} Imported numpy module.
- @param sigma {float} Gaussian sigma value.
- @param radius {int|None} Optional kernel radius override.
- @return {object} Normalized 2D kernel tensor.
- @satisfies REQ-075

### fn `def _rgb_to_hsl(np_module, rgb)` `priv` (L3793-3826)
- @brief Convert RGB float tensor to HSL channels.
- @details Implements explicit HSL conversion for OpenCV auto-adjust saturation-gamma stage without delegating to external color-space helpers.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB tensor in `[0.0, 1.0]`.
- @return {tuple[object, object, object]} `(h, s, l)` channel tensors.
- @satisfies REQ-075

### fn `def _hue_to_rgb(np_module, p_values, q_values, t_values)` `priv` (L3827-3857)
- @brief Convert one hue-shift channel to RGB component.
- @details Evaluates piecewise hue interpolation branch used by HSL-to-RGB conversion in OpenCV auto-adjust pipeline.
- @param np_module {ModuleType} Imported numpy module.
- @param p_values {object} Lower chroma interpolation boundary.
- @param q_values {object} Upper chroma interpolation boundary.
- @param t_values {object} Hue-shifted channel tensor.
- @return {object} RGB component tensor.
- @satisfies REQ-075

### fn `def _hsl_to_rgb(np_module, hue, saturation, lightness)` `priv` (L3858-3898)
- @brief Convert HSL channels to RGB float tensor.
- @details Reconstructs RGB tensor with explicit achromatic/chromatic branches for OpenCV auto-adjust saturation-gamma stage.
- @param np_module {ModuleType} Imported numpy module.
- @param hue {object} Hue channel tensor.
- @param saturation {object} Saturation channel tensor.
- @param lightness {object} Lightness channel tensor.
- @return {object} RGB tensor in `[0.0, 1.0]`.
- @satisfies REQ-075

### fn `def _selective_blur_contrast_gated_vectorized(` `priv` (L3899-3900)

### fn `def _level_per_channel_adaptive(np_module, rgb, low_pct=0.1, high_pct=99.9)` `priv` (L3949-3971)
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

### fn `def _sigmoidal_contrast(np_module, rgb, contrast=3.0, midpoint=0.5)` `priv` (L3972-3996)
- @brief Execute sigmoidal contrast stage.
- @details Applies logistic remapping with bounded normalization for each RGB channel.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param contrast {float} Logistic slope.
- @param midpoint {float} Logistic midpoint.
- @return {object} Contrast-adjusted RGB float tensor.
- @satisfies REQ-075

### fn `def logistic(z_values)` (L3987-3989)
- @brief Execute sigmoidal contrast stage.
- @details Applies logistic remapping with bounded normalization for each RGB
channel.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param contrast {float} Logistic slope.
- @param midpoint {float} Logistic midpoint.
- @return {object} Contrast-adjusted RGB float tensor.
- @satisfies REQ-075

### fn `def _vibrance_hsl_gamma(np_module, rgb, saturation_gamma=0.8)` `priv` (L3997-4014)
- @brief Execute HSL saturation gamma stage.
- @details Converts RGB to HSL, applies saturation gamma transform, and converts back to RGB.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param saturation_gamma {float} Saturation gamma denominator value.
- @return {object} Saturation-adjusted RGB float tensor.
- @satisfies REQ-075

### fn `def _gaussian_blur_rgb(cv2_module, np_module, rgb, sigma)` `priv` (L4015-4038)
- @brief Execute RGB Gaussian blur with reflected border mode.
- @details Computes odd kernel size from sigma and applies OpenCV Gaussian blur preserving reflected border behavior.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param sigma {float} Gaussian sigma.
- @return {object} Blurred RGB float tensor.
- @satisfies REQ-075

### fn `def _high_pass_math_gray(cv2_module, np_module, rgb, blur_sigma=2.5)` `priv` (L4039-4062)
- @brief Execute high-pass math grayscale stage.
- @details Computes high-pass response as `A - B + 0.5` over RGB channels and converts to luminance grayscale tensor.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param blur_sigma {float} Gaussian blur sigma for high-pass base.
- @return {object} Grayscale float tensor in `[0.0, 1.0]`.
- @satisfies REQ-075

### fn `def _overlay_composite(np_module, base_rgb, overlay_gray)` `priv` (L4063-4084)
- @brief Execute overlay composite stage.
- @details Applies conditional overlay blend equation over RGB base and grayscale overlay tensors.
- @param np_module {ModuleType} Imported numpy module.
- @param base_rgb {object} Base RGB float tensor in `[0.0, 1.0]`.
- @param overlay_gray {object} Overlay grayscale tensor in `[0.0, 1.0]`.
- @return {object} Overlay-composited RGB float tensor.
- @satisfies REQ-075

### fn `def _apply_validated_auto_adjust_pipeline_opencv(` `priv` (L4085-4086)

### fn `def _load_piexif_dependency()` `priv` (L4165-4182)
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

### fn `def _encode_jpg(` `priv` (L4183-4195)

### fn `def _collect_processing_errors(rawpy_module)` `priv` (L4413-4441)
- @brief Encode merged HDR TIFF payload into final JPG output.
- @brief Build deterministic tuple of recoverable processing exceptions.
- @details Loads merged image payload, keeps 16-bit depth when source
dynamic range exceeds JPEG-native depth if auto-brightness or auto-levels is enabled,
optionally executes BT.709 linear-sRGB auto-brightness pre-stage, optionally
executes auto-levels stage, preserves
resolved `ev_zero` as extraction/merge reference only without additional
brightness compensation at encode stage, then applies shared
gamma/brightness/contrast/saturation postprocessing over resulting image,
optionally executes auto-adjust stage over temporary lossless 16-bit TIFF
intermediates, and writes JPEG with configured compression level for both
HDR backends.
- @details Combines common IO/value/subprocess errors with rawpy-specific decoding error classes when present in runtime module version.
- @param imageio_module {ModuleType} Imported imageio module with `imread` and `imwrite`.
- @param pil_image_module {ModuleType} Imported Pillow image module.
- @param pil_enhance_module {ModuleType} Imported Pillow ImageEnhance module.
- @param merged_tiff {Path} Merged TIFF source path produced by `enfuse`.
- @param output_jpg {Path} Final JPG output path.
- @param postprocess_options {PostprocessOptions} Shared TIFF-to-JPG correction settings.
- @param imagemagick_command {str|None} Optional pre-resolved ImageMagick executable.
- @param auto_adjust_opencv_dependencies {tuple[ModuleType, ModuleType]|None} Optional `(cv2, numpy)` modules for OpenCV auto-adjust implementations.
- @param piexif_module {ModuleType|None} Optional piexif module for EXIF thumbnail refresh.
- @param source_exif_payload {bytes|None} Serialized EXIF payload copied from input DNG.
- @param source_orientation {int} Source EXIF orientation value in range `1..8`.
- @param ev_zero {float} Selected EV center used for extraction and merge reference.
- @param rawpy_module {ModuleType} Imported rawpy module.
- @return {None} Side effects only.
- @return {tuple[type[BaseException], ...]} Ordered deduplicated exception class tuple.
- @exception RuntimeError Raised when auto-adjust mode dependencies are missing or auto-adjust mode value is unsupported.
- @satisfies REQ-053, REQ-055, REQ-056, REQ-057, REQ-058, REQ-066, REQ-069, REQ-073, REQ-074, REQ-075, REQ-077, REQ-078, REQ-086, REQ-087, REQ-090
- @satisfies REQ-059

### fn `def _is_supported_runtime_os()` `priv` (L4442-4461)
- @brief Validate runtime platform support for `dng2jpg`.
- @details Accepts Linux runtime only; emits explicit non-Linux unsupported message that includes OS label (`Windows` or `MacOS`) for deterministic UX.
- @return {bool} `True` when runtime OS is Linux; `False` otherwise.
- @satisfies REQ-055, REQ-059

### fn `def run(args)` (L4462-4661)
- @brief Execute `dng2jpg` command pipeline.
- @details Parses command options, validates dependencies, detects source DNG bits-per-color from RAW metadata, resolves manual or automatic EV-zero center, resolves static or adaptive EV selector around resolved center using bit-derived EV ceilings, extracts three RAW brackets, executes selected `enfuse` flow or selected luminance-hdr-cli flow, writes JPG output, and guarantees temporary artifact cleanup through isolated temporary directory lifecycle.
- @param args {list[str]} Command argument vector excluding command token.
- @return {int} `0` on success; `1` on parse/validation/dependency/processing failure.
- @satisfies REQ-053, REQ-054, REQ-055, REQ-056, REQ-057, REQ-058, REQ-059, REQ-060, REQ-061, REQ-062, REQ-064, REQ-065, REQ-066, REQ-067, REQ-068, REQ-069, REQ-071, REQ-072, REQ-073, REQ-074, REQ-075, REQ-077, REQ-078, REQ-079, REQ-080, REQ-081, REQ-088, REQ-089, REQ-090, REQ-091, REQ-092, REQ-093, REQ-094, REQ-095, REQ-096, REQ-097, REQ-098

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`PROGRAM`|var|pub|30||
|`DESCRIPTION`|var|pub|31||
|`DEFAULT_GAMMA`|var|pub|32||
|`DEFAULT_POST_GAMMA`|var|pub|33||
|`DEFAULT_BRIGHTNESS`|var|pub|34||
|`DEFAULT_CONTRAST`|var|pub|35||
|`DEFAULT_SATURATION`|var|pub|36||
|`DEFAULT_JPG_COMPRESSION`|var|pub|37||
|`DEFAULT_AUTO_ZERO_PCT`|var|pub|38||
|`DEFAULT_AUTO_EV_PCT`|var|pub|39||
|`DEFAULT_AA_BLUR_SIGMA`|var|pub|40||
|`DEFAULT_AA_BLUR_THRESHOLD_PCT`|var|pub|41||
|`DEFAULT_AA_LEVEL_LOW_PCT`|var|pub|42||
|`DEFAULT_AA_LEVEL_HIGH_PCT`|var|pub|43||
|`DEFAULT_AA_SIGMOID_CONTRAST`|var|pub|44||
|`DEFAULT_AA_SIGMOID_MIDPOINT`|var|pub|45||
|`DEFAULT_AA_SATURATION_GAMMA`|var|pub|46||
|`DEFAULT_AA_HIGHPASS_BLUR_SIGMA`|var|pub|47||
|`DEFAULT_AL_CLIP_PCT`|var|pub|48||
|`DEFAULT_AB_TARGET_GREY`|var|pub|49||
|`DEFAULT_AB_MAX_GAIN`|var|pub|50||
|`DEFAULT_AB_MIN_GAIN`|var|pub|51||
|`DEFAULT_AB_P98_HIGHLIGHT_MAX`|var|pub|52||
|`DEFAULT_AB_CORRECTION_STRENGTH`|var|pub|53||
|`DEFAULT_AB_MAX_EV_CORRECTION`|var|pub|54||
|`DEFAULT_LUMINANCE_HDR_MODEL`|var|pub|55||
|`DEFAULT_LUMINANCE_HDR_WEIGHT`|var|pub|56||
|`DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE`|var|pub|57||
|`DEFAULT_LUMINANCE_TMO`|var|pub|58||
|`DEFAULT_REINHARD02_BRIGHTNESS`|var|pub|59||
|`DEFAULT_REINHARD02_CONTRAST`|var|pub|60||
|`DEFAULT_REINHARD02_SATURATION`|var|pub|61||
|`DEFAULT_MANTIUK08_CONTRAST`|var|pub|62||
|`EV_STEP`|var|pub|63||
|`MIN_SUPPORTED_BITS_PER_COLOR`|var|pub|64||
|`DEFAULT_DNG_BITS_PER_COLOR`|var|pub|65||
|`SUPPORTED_EV_VALUES`|var|pub|66||
|`AUTO_EV_LOW_PERCENTILE`|var|pub|72||
|`AUTO_EV_HIGH_PERCENTILE`|var|pub|73||
|`AUTO_EV_MEDIAN_PERCENTILE`|var|pub|74||
|`AUTO_EV_TARGET_SHADOW`|var|pub|75||
|`AUTO_EV_TARGET_HIGHLIGHT`|var|pub|76||
|`AUTO_EV_MEDIAN_TARGET`|var|pub|77||
|`AUTO_ZERO_SCENE_KEY_LOW_THRESHOLD`|var|pub|78||
|`AUTO_ZERO_SCENE_KEY_HIGH_THRESHOLD`|var|pub|79||
|`AUTO_ZERO_TARGET_LOW_KEY`|var|pub|80||
|`AUTO_ZERO_TARGET_HIGH_KEY`|var|pub|81||
|`AutoAdjustOptions`|class|pub|265-292|class AutoAdjustOptions|
|`AutoBrightnessOptions`|class|pub|294-311|class AutoBrightnessOptions|
|`AutoLevelsOptions`|class|pub|313-330|class AutoLevelsOptions|
|`PostprocessOptions`|class|pub|332-366|class PostprocessOptions|
|`LuminanceOptions`|class|pub|368-388|class LuminanceOptions|
|`AutoEvInputs`|class|pub|390-417|class AutoEvInputs|
|`_print_box_table`|fn|priv|418-454|def _print_box_table(headers, rows, header_rows=())|
|`_border`|fn|priv|438-440|def _border(left, middle, right)|
|`_line`|fn|priv|441-444|def _line(values)|
|`_build_two_line_operator_rows`|fn|priv|455-471|def _build_two_line_operator_rows(operator_entries)|
|`print_help`|fn|pub|472-671|def print_help(version)|
|`_calculate_max_ev_from_bits`|fn|priv|678-696|def _calculate_max_ev_from_bits(bits_per_color)|
|`_calculate_safe_ev_zero_max`|fn|priv|697-709|def _calculate_safe_ev_zero_max(base_max_ev)|
|`_derive_supported_ev_zero_values`|fn|priv|710-726|def _derive_supported_ev_zero_values(base_max_ev)|
|`_derive_supported_ev_values`|fn|priv|727-755|def _derive_supported_ev_values(bits_per_color, ev_zero=0.0)|
|`_detect_dng_bits_per_color`|fn|priv|756-801|def _detect_dng_bits_per_color(raw_handle)|
|`_is_ev_value_on_supported_step`|fn|priv|802-815|def _is_ev_value_on_supported_step(ev_value)|
|`_parse_ev_option`|fn|priv|816-847|def _parse_ev_option(ev_raw)|
|`_parse_ev_zero_option`|fn|priv|848-878|def _parse_ev_zero_option(ev_zero_raw)|
|`_parse_auto_ev_option`|fn|priv|879-896|def _parse_auto_ev_option(auto_ev_raw)|
|`_parse_auto_zero_option`|fn|priv|897-914|def _parse_auto_zero_option(auto_zero_raw)|
|`_parse_percentage_option`|fn|priv|915-937|def _parse_percentage_option(option_name, option_raw)|
|`_parse_auto_brightness_option`|fn|priv|938-955|def _parse_auto_brightness_option(auto_brightness_raw)|
|`_parse_auto_levels_option`|fn|priv|956-973|def _parse_auto_levels_option(auto_levels_raw)|
|`_parse_auto_levels_highlight_reconstruction_option`|fn|priv|974-993|def _parse_auto_levels_highlight_reconstruction_option(op...|
|`_parse_auto_levels_highlight_reconstruction_method`|fn|priv|994-1023|def _parse_auto_levels_highlight_reconstruction_method(op...|
|`_clamp_ev_to_supported`|fn|priv|1024-1037|def _clamp_ev_to_supported(ev_candidate, ev_values)|
|`_quantize_ev_to_supported`|fn|priv|1038-1059|def _quantize_ev_to_supported(ev_value, ev_values)|
|`_quantize_ev_toward_zero_step`|fn|priv|1060-1081|def _quantize_ev_toward_zero_step(ev_value, step=EV_STEP)|
|`_apply_auto_percentage_scaling`|fn|priv|1082-1096|def _apply_auto_percentage_scaling(ev_value, percentage)|
|`_extract_normalized_preview_luminance_stats`|fn|priv|1097-1156|def _extract_normalized_preview_luminance_stats(raw_handle)|
|`_percentile`|fn|priv|1131-1141|def _percentile(percentile_value)|
|`_coerce_positive_luminance`|fn|priv|1157-1176|def _coerce_positive_luminance(value, fallback)|
|`_derive_scene_key_preserving_median_target`|fn|priv|1177-1195|def _derive_scene_key_preserving_median_target(p_median)|
|`_optimize_auto_zero`|fn|priv|1196-1219|def _optimize_auto_zero(auto_ev_inputs)|
|`_optimize_adaptive_ev_delta`|fn|priv|1220-1249|def _optimize_adaptive_ev_delta(auto_ev_inputs)|
|`_compute_auto_ev_value_from_stats`|fn|priv|1250-1255|def _compute_auto_ev_value_from_stats(|
|`_compute_auto_ev_value`|fn|priv|1283-1310|def _compute_auto_ev_value(raw_handle, supported_ev_value...|
|`_resolve_ev_zero`|fn|priv|1311-1318|def _resolve_ev_zero(|
|`_resolve_ev_value`|fn|priv|1369-1376|def _resolve_ev_value(|
|`_parse_luminance_text_option`|fn|priv|1429-1449|def _parse_luminance_text_option(option_name, option_raw)|
|`_parse_gamma_option`|fn|priv|1450-1486|def _parse_gamma_option(gamma_raw)|
|`_parse_positive_float_option`|fn|priv|1487-1510|def _parse_positive_float_option(option_name, option_raw)|
|`_parse_tmo_passthrough_value`|fn|priv|1511-1527|def _parse_tmo_passthrough_value(option_name, option_raw)|
|`_parse_jpg_compression_option`|fn|priv|1528-1550|def _parse_jpg_compression_option(compression_raw)|
|`_parse_float_exclusive_range_option`|fn|priv|1551-1575|def _parse_float_exclusive_range_option(option_name, opti...|
|`_parse_non_negative_float_option`|fn|priv|1576-1598|def _parse_non_negative_float_option(option_name, option_...|
|`_parse_float_in_range_option`|fn|priv|1599-1624|def _parse_float_in_range_option(option_name, option_raw,...|
|`_parse_auto_brightness_options`|fn|priv|1625-1648|def _parse_auto_brightness_options(auto_brightness_raw_va...|
|`_parse_auto_levels_options`|fn|priv|1649-1716|def _parse_auto_levels_options(auto_levels_raw_values)|
|`_parse_auto_adjust_options`|fn|priv|1717-1823|def _parse_auto_adjust_options(auto_adjust_raw_values)|
|`_parse_auto_adjust_mode_option`|fn|priv|1824-1847|def _parse_auto_adjust_mode_option(auto_adjust_raw)|
|`_resolve_default_postprocess`|fn|priv|1848-1890|def _resolve_default_postprocess(enable_luminance, lumina...|
|`_parse_run_options`|fn|priv|1891-2090|def _parse_run_options(args)|
|`_load_image_dependencies`|fn|priv|2610-2648|def _load_image_dependencies()|
|`_parse_exif_datetime_to_timestamp`|fn|priv|2649-2679|def _parse_exif_datetime_to_timestamp(datetime_raw)|
|`_extract_dng_exif_payload_and_timestamp`|fn|priv|2680-2737|def _extract_dng_exif_payload_and_timestamp(pil_image_mod...|
|`_resolve_thumbnail_transpose_map`|fn|priv|2738-2769|def _resolve_thumbnail_transpose_map(pil_image_module)|
|`_apply_orientation_transform`|fn|priv|2770-2792|def _apply_orientation_transform(pil_image_module, pil_im...|
|`_build_oriented_thumbnail_jpeg_bytes`|fn|priv|2793-2794|def _build_oriented_thumbnail_jpeg_bytes(|
|`_coerce_exif_int_like_value`|fn|priv|2823-2865|def _coerce_exif_int_like_value(raw_value)|
|`_normalize_ifd_integer_like_values_for_piexif_dump`|fn|priv|2866-2999|def _normalize_ifd_integer_like_values_for_piexif_dump(pi...|
|`_refresh_output_jpg_exif_thumbnail_after_save`|fn|priv|3000-3005|def _refresh_output_jpg_exif_thumbnail_after_save(|
|`_set_output_file_timestamps`|fn|priv|3054-3068|def _set_output_file_timestamps(output_jpg, exif_timestamp)|
|`_sync_output_file_timestamps_from_exif`|fn|priv|3069-3085|def _sync_output_file_timestamps_from_exif(output_jpg, ex...|
|`_build_exposure_multipliers`|fn|priv|3086-3104|def _build_exposure_multipliers(ev_value, ev_zero=0.0)|
|`_write_bracket_images`|fn|priv|3105-3106|def _write_bracket_images(|
|`_order_bracket_paths`|fn|priv|3143-3168|def _order_bracket_paths(bracket_paths)|
|`_run_enfuse`|fn|priv|3169-3189|def _run_enfuse(bracket_paths, merged_tiff)|
|`_run_luminance_hdr_cli`|fn|priv|3190-3191|def _run_luminance_hdr_cli(|
|`_convert_compression_to_quality`|fn|priv|3243-3255|def _convert_compression_to_quality(jpg_compression)|
|`_resolve_imagemagick_command`|fn|priv|3256-3273|def _resolve_imagemagick_command()|
|`_resolve_auto_adjust_opencv_dependencies`|fn|priv|3274-3298|def _resolve_auto_adjust_opencv_dependencies()|
|`_to_uint8_image_array`|fn|priv|3299-3345|def _to_uint8_image_array(np_module, image_data)|
|`_to_uint16_image_array`|fn|priv|3346-3390|def _to_uint16_image_array(np_module, image_data)|
|`_to_linear_srgb`|fn|priv|3391-3408|def _to_linear_srgb(np_module, image_srgb)|
|`_from_linear_srgb`|fn|priv|3409-3426|def _from_linear_srgb(np_module, image_linear)|
|`_compute_bt709_luminance`|fn|priv|3427-3444|def _compute_bt709_luminance(np_module, linear_rgb)|
|`_apply_highlight_rolloff`|fn|priv|3445-3463|def _apply_highlight_rolloff(np_module, linear_rgb)|
|`_apply_auto_brightness_rgb_uint8`|fn|priv|3464-3465|def _apply_auto_brightness_rgb_uint8(|
|`_reconstruct_highlights_luminance`|fn|priv|3523-3549|def _reconstruct_highlights_luminance(np_module, linear_r...|
|`_reconstruct_highlights_cielab_blending`|fn|priv|3550-3583|def _reconstruct_highlights_cielab_blending(cv2_module, n...|
|`_reconstruct_highlights_blend`|fn|priv|3584-3607|def _reconstruct_highlights_blend(np_module, linear_rgb, ...|
|`_apply_auto_levels_rgb_uint16`|fn|priv|3608-3609|def _apply_auto_levels_rgb_uint16(|
|`_apply_validated_auto_adjust_pipeline`|fn|priv|3674-3675|def _apply_validated_auto_adjust_pipeline(|
|`_clamp01`|fn|priv|3756-3769|def _clamp01(np_module, values)|
|`_gaussian_kernel_2d`|fn|priv|3770-3792|def _gaussian_kernel_2d(np_module, sigma, radius=None)|
|`_rgb_to_hsl`|fn|priv|3793-3826|def _rgb_to_hsl(np_module, rgb)|
|`_hue_to_rgb`|fn|priv|3827-3857|def _hue_to_rgb(np_module, p_values, q_values, t_values)|
|`_hsl_to_rgb`|fn|priv|3858-3898|def _hsl_to_rgb(np_module, hue, saturation, lightness)|
|`_selective_blur_contrast_gated_vectorized`|fn|priv|3899-3900|def _selective_blur_contrast_gated_vectorized(|
|`_level_per_channel_adaptive`|fn|priv|3949-3971|def _level_per_channel_adaptive(np_module, rgb, low_pct=0...|
|`_sigmoidal_contrast`|fn|priv|3972-3996|def _sigmoidal_contrast(np_module, rgb, contrast=3.0, mid...|
|`logistic`|fn|pub|3987-3989|def logistic(z_values)|
|`_vibrance_hsl_gamma`|fn|priv|3997-4014|def _vibrance_hsl_gamma(np_module, rgb, saturation_gamma=...|
|`_gaussian_blur_rgb`|fn|priv|4015-4038|def _gaussian_blur_rgb(cv2_module, np_module, rgb, sigma)|
|`_high_pass_math_gray`|fn|priv|4039-4062|def _high_pass_math_gray(cv2_module, np_module, rgb, blur...|
|`_overlay_composite`|fn|priv|4063-4084|def _overlay_composite(np_module, base_rgb, overlay_gray)|
|`_apply_validated_auto_adjust_pipeline_opencv`|fn|priv|4085-4086|def _apply_validated_auto_adjust_pipeline_opencv(|
|`_load_piexif_dependency`|fn|priv|4165-4182|def _load_piexif_dependency()|
|`_encode_jpg`|fn|priv|4183-4195|def _encode_jpg(|
|`_collect_processing_errors`|fn|priv|4413-4441|def _collect_processing_errors(rawpy_module)|
|`_is_supported_runtime_os`|fn|priv|4442-4461|def _is_supported_runtime_os()|
|`run`|fn|pub|4462-4661|def run(args)|


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

