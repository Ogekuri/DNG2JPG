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

# core.py | Python | 225L | 9 symbols | 14 imports | 8 comments
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
### fn `def _management_help() -> str` `priv` (L27-40)
- @brief Idle-delay applied after any latest-release check error.

### fn `def _write_version_cache(idle_delay_seconds: int) -> None` `priv` (L41-72)
- @brief Persist latest-release cache metadata as JSON.
- @details Computes `last_check_*` and `idle_time_*` fields from the current epoch, creates the cache parent directory when missing, and rewrites the cache JSON atomically via `Path.write_text`. Complexity: O(1). Side effects: directory creation and cache file overwrite.
- @param idle_delay_seconds {int} Idle-delay in seconds added to the current epoch to derive the next `idle_time_epoch`.
- @return {None} No return value.
- @throws {OSError} Directory creation or cache-file write failure.
- @satisfies REQ-016, REQ-150, REQ-151
- @post `_VERSION_CACHE_FILE` stores the latest check epoch and derived idle-time metadata.

### fn `def _should_skip_version_check(force: bool) -> bool` `priv` (L73-100)
- @brief Evaluate whether cached idle-time suppresses a network version check.
- @details Returns `False` when forced, when the cache file is absent, when cache JSON decoding fails, or when `idle_time_epoch` is missing/invalid. Returns `True` only when the current epoch is strictly earlier than the cached idle-time. Complexity: O(1). Side effect: cache-file read.
- @param force {bool} Bypass flag that disables cache suppression when true.
- @return {bool} True if the current invocation must skip the network check; False otherwise.
- @throws {None} Cache read and decode failures are converted to `False`.
- @satisfies REQ-016

### fn `def _check_online_version(force: bool) -> None` `priv` (L101-173)
- @brief Execute the latest-release check and refresh cache idle-time policy.
- @details Skips the network request when `_should_skip_version_check(...)` returns true. Otherwise performs one GitHub latest-release API request, normalizes the returned tag name, assigns idle-delay `3600` seconds after a successful attempt, assigns idle-delay `86400` seconds after any handled request/parsing error, rewrites the cache JSON after every attempted API call, and then emits the status or error message. Complexity: O(1). Side effects: network I/O, cache-file rewrite, stdout/stderr output.
- @param force {bool} Bypass flag that forces a network request even when the cache idle-time is still active.
- @return {None} No return value.
- @throws {OSError} Cache-file rewrite failure after a completed API attempt.
- @see _should_skip_version_check
- @see _write_version_cache
- @satisfies REQ-016, REQ-150, REQ-151

### fn `def _run_management(command: list[str]) -> int` `priv` (L174-187)

### fn `def main(argv: Sequence[str] | None = None) -> int` (L188-225)

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`PROGRAM`|var|pub|14||
|`OWNER`|var|pub|15||
|`REPOSITORY`|var|pub|16||
|`_management_help`|fn|priv|27-40|def _management_help() -> str|
|`_write_version_cache`|fn|priv|41-72|def _write_version_cache(idle_delay_seconds: int) -> None|
|`_should_skip_version_check`|fn|priv|73-100|def _should_skip_version_check(force: bool) -> bool|
|`_check_online_version`|fn|priv|101-173|def _check_online_version(force: bool) -> None|
|`_run_management`|fn|priv|174-187|def _run_management(command: list[str]) -> int|
|`main`|fn|pub|188-225|def main(argv: Sequence[str] | None = None) -> int|


---

# dng2jpg.py | Python | 9289L | 287 symbols | 24 imports | 198 comments
> Path: `src/dng2jpg/dng2jpg.py`

## Imports
```
import os
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
import rawpy  # type: ignore
import imageio.v3 as imageio  # type: ignore
import imageio  # type: ignore
from PIL import Image as pil_image  # type: ignore
import numpy as np_module  # type: ignore
from numpy.lib.stride_tricks import sliding_window_view  # type: ignore
from numpy.lib.stride_tricks import sliding_window_view  # type: ignore
import cv2  # type: ignore
import numpy as numpy_module  # type: ignore
import numpy as numpy_module  # type: ignore
import piexif  # type: ignore
import numpy as np_module  # type: ignore
```

## Definitions

- var `PROGRAM = "dng2jpg"` (L35)
- var `DESCRIPTION = (` (L36)
- var `DEFAULT_GAMMA = (2.222, 4.5)` (L39)
- var `DEFAULT_POST_GAMMA = 1.0` (L40)
- var `DEFAULT_BRIGHTNESS = 1.0` (L41)
- var `DEFAULT_CONTRAST = 1.0` (L42)
- var `DEFAULT_SATURATION = 1.0` (L43)
- var `DEFAULT_JPG_COMPRESSION = 15` (L44)
- var `DEFAULT_AUTO_ZERO_PCT = 50.0` (L45)
- var `DEFAULT_AUTO_EV_PCT = 50.0` (L46)
- var `DEFAULT_AA_BLUR_SIGMA = 0.9` (L47)
- var `DEFAULT_AA_BLUR_THRESHOLD_PCT = 5.0` (L48)
- var `DEFAULT_AA_LEVEL_LOW_PCT = 0.1` (L49)
- var `DEFAULT_AA_LEVEL_HIGH_PCT = 99.9` (L50)
- var `DEFAULT_AA_ENABLE_LOCAL_CONTRAST = True` (L51)
- var `DEFAULT_AA_LOCAL_CONTRAST_STRENGTH = 0.20` (L52)
- var `DEFAULT_AA_CLAHE_CLIP_LIMIT = 1.6` (L53)
- var `DEFAULT_AA_CLAHE_TILE_GRID_SIZE = (8, 8)` (L54)
- var `DEFAULT_AA_SIGMOID_CONTRAST = 1.8` (L55)
- var `DEFAULT_AA_SIGMOID_MIDPOINT = 0.5` (L56)
- var `DEFAULT_AA_SATURATION_GAMMA = 0.8` (L57)
- var `DEFAULT_AA_HIGHPASS_BLUR_SIGMA = 2.0` (L58)
- var `DEFAULT_AB_KEY_VALUE = None` (L59)
- var `DEFAULT_AB_WHITE_POINT_PERCENTILE = 99.8` (L60)
- var `DEFAULT_AB_A_MIN = 0.045` (L61)
- var `DEFAULT_AB_A_MAX = 0.72` (L62)
- var `DEFAULT_AB_MAX_AUTO_BOOST_FACTOR = 1.25` (L63)
- var `DEFAULT_AB_ENABLE_LUMINANCE_PRESERVING_DESAT = True` (L64)
- var `DEFAULT_AB_EPS = 1e-6` (L65)
- var `DEFAULT_AB_LOW_KEY_VALUE = 0.09` (L66)
- var `DEFAULT_AB_NORMAL_KEY_VALUE = 0.18` (L67)
- var `DEFAULT_AB_HIGH_KEY_VALUE = 0.36` (L68)
- var `DEFAULT_AL_CLIP_PERCENT = 0.02` (L69)
- var `DEFAULT_AL_CLIP_OUT_OF_GAMUT = True` (L70)
- var `DEFAULT_AL_GAIN_THRESHOLD = 1.0` (L71)
- var `DEFAULT_AL_HISTCOMPR = 3` (L72)
- var `DEFAULT_LUMINANCE_HDR_MODEL = "debevec"` (L94)
- var `DEFAULT_LUMINANCE_HDR_WEIGHT = "flat"` (L95)
- var `DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE = "srgb"` (L96)
- var `DEFAULT_LUMINANCE_TMO = "mantiuk08"` (L97)
- var `DEFAULT_AUTO_ADJUST_ENABLED = True` (L98)
- var `HDR_MERGE_MODE_LUMINANCE = "Luminace-HDR"` (L99)
- var `HDR_MERGE_MODE_OPENCV = "OpenCV"` (L100)
- var `HDR_MERGE_MODE_HDR_PLUS = "HDR-Plus"` (L101)
- var `OPENCV_MERGE_ALGORITHM_DEBEVEC = "Debevec"` (L102)
- var `OPENCV_MERGE_ALGORITHM_ROBERTSON = "Robertson"` (L103)
- var `OPENCV_MERGE_ALGORITHM_MERTENS = "Mertens"` (L104)
- var `DEFAULT_REINHARD02_BRIGHTNESS = 1.25` (L105)
- var `DEFAULT_REINHARD02_CONTRAST = 0.85` (L106)
- var `DEFAULT_REINHARD02_SATURATION = 0.55` (L107)
- var `DEFAULT_MANTIUK08_CONTRAST = 1.2` (L108)
- var `DEFAULT_OPENCV_POST_GAMMA = 1.0` (L109)
- var `DEFAULT_OPENCV_BRIGHTNESS = 1.0` (L110)
- var `DEFAULT_OPENCV_CONTRAST = 1.0` (L111)
- var `DEFAULT_OPENCV_SATURATION = 1.0` (L112)
- var `DEFAULT_OPENCV_MERGE_ALGORITHM = OPENCV_MERGE_ALGORITHM_ROBERTSON` (L113)
- var `DEFAULT_OPENCV_TONEMAP_ENABLED = True` (L114)
- var `DEFAULT_OPENCV_TONEMAP_GAMMA = 2.2` (L115)
- var `DEFAULT_HDRPLUS_PROXY_MODE = "rggb"` (L116)
- var `DEFAULT_HDRPLUS_SEARCH_RADIUS = 4` (L117)
- var `DEFAULT_HDRPLUS_TEMPORAL_FACTOR = 8.0` (L118)
- var `DEFAULT_HDRPLUS_TEMPORAL_MIN_DIST = 10.0` (L119)
- var `DEFAULT_HDRPLUS_TEMPORAL_MAX_DIST = 300.0` (L120)
- var `HDRPLUS_TILE_SIZE = 32` (L121)
- var `HDRPLUS_TILE_STRIDE = HDRPLUS_TILE_SIZE // 2` (L122)
- var `HDRPLUS_DOWNSAMPLED_TILE_SIZE = HDRPLUS_TILE_STRIDE` (L123)
- var `HDRPLUS_ALIGNMENT_LEVELS = 3` (L124)
- var `HDRPLUS_ALIGNMENT_DOWNSAMPLE_RATE = 4` (L125)
- var `HDRPLUS_TEMPORAL_FACTOR = DEFAULT_HDRPLUS_TEMPORAL_FACTOR` (L126)
- var `HDRPLUS_TEMPORAL_MIN_DIST = DEFAULT_HDRPLUS_TEMPORAL_MIN_DIST` (L127)
- var `HDRPLUS_TEMPORAL_MAX_DIST = DEFAULT_HDRPLUS_TEMPORAL_MAX_DIST` (L128)
- var `EV_STEP = 0.25` (L130)
- var `MIN_SUPPORTED_BITS_PER_COLOR = 9` (L131)
- var `DEFAULT_DNG_BITS_PER_COLOR = 14` (L132)
- var `SUPPORTED_EV_VALUES = tuple(` (L133)
- var `AUTO_EV_LOW_PERCENTILE = 0.1` (L139)
- var `AUTO_EV_HIGH_PERCENTILE = 99.9` (L140)
- var `AUTO_EV_MEDIAN_PERCENTILE = 50.0` (L141)
- var `AUTO_EV_TARGET_SHADOW = 0.05` (L142)
- var `AUTO_EV_TARGET_HIGHLIGHT = 0.90` (L143)
- var `AUTO_EV_MEDIAN_TARGET = 0.5` (L144)
- var `AUTO_ZERO_SCENE_KEY_LOW_THRESHOLD = 0.35` (L145)
- var `AUTO_ZERO_SCENE_KEY_HIGH_THRESHOLD = 0.65` (L146)
- var `AUTO_ZERO_TARGET_LOW_KEY = 0.35` (L147)
- var `AUTO_ZERO_TARGET_HIGH_KEY = 0.65` (L148)
### class `class AutoAdjustOptions` `@dataclass(frozen=True)` (L362-397)
- @brief Hold validated knob values for the sole auto-adjust pipeline.
- @details Encapsulates selective-blur, adaptive-level, CLAHE-luma, sigmoidal-contrast, vibrance, and high-pass controls consumed by the single float-domain auto-adjust implementation.
- @param blur_sigma {float} Selective blur Gaussian sigma (`> 0`).
- @param blur_threshold_pct {float} Selective blur threshold percentage in `[0, 100]`.
- @param level_low_pct {float} Low percentile for level normalization in `[0, 100]`.
- @param level_high_pct {float} High percentile for level normalization in `[0, 100]`.
- @param enable_local_contrast {bool} `True` enables CLAHE-luma stage in the auto-adjust pipeline.
- @param local_contrast_strength {float} CLAHE-luma blend factor in `[0, 1]`.
- @param clahe_clip_limit {float} CLAHE clip limit in `(0, +inf)`.
- @param clahe_tile_grid_size {tuple[int, int]} CLAHE tile grid size `(rows, cols)`, each `>=1`.
- @param sigmoid_contrast {float} Sigmoidal contrast slope (`> 0`).
- @param sigmoid_midpoint {float} Sigmoidal contrast midpoint in `[0, 1]`.
- @param saturation_gamma {float} HSL saturation gamma denominator (`> 0`).
- @param highpass_blur_sigma {float} High-pass Gaussian blur sigma (`> 0`).
- @return {None} Immutable dataclass container.
- @satisfies REQ-051, REQ-073, REQ-075, REQ-082, REQ-083, REQ-084, REQ-086, REQ-087, REQ-123, REQ-125, REQ-136, REQ-137

### class `class AutoBrightnessOptions` `@dataclass(frozen=True)` (L399-427)
- @brief Hold `--auto-brightness` knob values.
- @details Encapsulates parameters for the 16-bit BT.709 photographic tonemap pipeline: key-classification, key-value selection, robust white point, optional luminance-preserving anti-clipping desaturation, and numerical stability control for float-domain luminance processing.
- @param key_value {float|None} Manual Reinhard key value override in `(0, +inf)`; `None` enables automatic key selection.
- @param white_point_percentile {float} Percentile in `(0, 100)` used to derive robust `Lwhite`.
- @param a_min {float} Minimum allowed automatic key value clamp in `(0, +inf)`.
- @param a_max {float} Maximum allowed automatic key value clamp in `(0, +inf)`.
- @param max_auto_boost_factor {float} Multiplicative adjustment factor for automatic key adaptation in `(0, +inf)`.
- @param enable_luminance_preserving_desat {bool} `True` enables minimal grayscale blending for out-of-gamut linear RGB triplets.
- @param eps {float} Positive numerical stability guard used in divisions and logarithms.
- @return {None} Immutable dataclass container.
- @satisfies REQ-050, REQ-065, REQ-088, REQ-089, REQ-090, REQ-103, REQ-104, REQ-105, REQ-124, REQ-135

### class `class AutoLevelsOptions` `@dataclass(frozen=True)` (L429-452)
- @brief Hold `--auto-levels` knob values.
- @details Encapsulates validated histogram-based auto-levels controls ported from the attached RawTherapee-oriented source and adapted for normalized RGB float stage execution in the current post-merge pipeline.
- @param clip_percent {float} Histogram clipping percentage in `[0, +inf)`.
- @param clip_out_of_gamut {bool} `True` to normalize overflowing RGB triplets back into normalized gamut after gain/reconstruction.
- @param histcompr {int} Histogram compression shift in `[0, 15]`.
- @param highlight_reconstruction_enabled {bool} `True` when highlight reconstruction is enabled.
- @param highlight_reconstruction_method {str} Highlight reconstruction method selector.
- @param gain_threshold {float} Inpaint Opposed gain threshold in `(0, +inf)`.
- @return {None} Immutable dataclass container.
- @satisfies REQ-100, REQ-101, REQ-102, REQ-116

### class `class PostprocessOptions` `@dataclass(frozen=True)` (L454-490)
- @brief Hold deterministic postprocessing option values.
- @details Encapsulates correction factors and JPEG compression level used by shared TIFF-to-JPG postprocessing for both HDR backends.
- @param post_gamma {float} Gamma correction factor for postprocessing stage.
- @param brightness {float} Brightness enhancement factor.
- @param contrast {float} Contrast enhancement factor.
- @param saturation {float} Saturation enhancement factor.
- @param jpg_compression {int} JPEG compression level in range `[0, 100]`.
- @param auto_brightness_enabled {bool} `True` when the post-static auto-brightness stage is enabled.
- @param auto_brightness_options {AutoBrightnessOptions} Auto-brightness stage knobs.
- @param auto_levels_enabled {bool} `True` when auto-levels stage is enabled.
- @param auto_levels_options {AutoLevelsOptions} Auto-levels stage knobs.
- @param auto_adjust_enabled {bool} `True` when the auto-adjust stage is enabled.
- @param auto_adjust_options {AutoAdjustOptions} Knobs for the sole auto-adjust implementation.
- @param debug_enabled {bool} `True` when persistent debug TIFF checkpoints are enabled.
- @return {None} Immutable dataclass container.
- @satisfies REQ-050, REQ-065, REQ-066, REQ-069, REQ-071, REQ-072, REQ-073, REQ-075, REQ-082, REQ-083, REQ-084, REQ-086, REQ-087, REQ-088, REQ-089, REQ-090, REQ-100, REQ-101, REQ-102, REQ-103, REQ-104, REQ-105, REQ-146

### class `class DebugArtifactContext` `@dataclass(frozen=True)` (L492-508)
- @brief Hold persistent debug-checkpoint output metadata.
- @details Stores the source input stem and destination directory used to emit debug TIFF checkpoints outside the temporary workspace. The suffix counter remains external so orchestration can map checkpoints to exact pipeline stages in execution order.
- @param output_dir {Path} Destination directory for persistent debug TIFF files.
- @param input_stem {str} Source DNG stem used as the filename prefix.
- @return {None} Immutable debug output metadata container.
- @satisfies DES-009, REQ-146, REQ-147, REQ-149

### class `class LuminanceOptions` `@dataclass(frozen=True)` (L510-530)
- @brief Hold deterministic luminance-hdr-cli option values.
- @details Encapsulates luminance backend model and tone-mapping parameters forwarded to `luminance-hdr-cli` command generation.
- @param hdr_model {str} Luminance HDR model (`--hdrModel`).
- @param hdr_weight {str} Luminance weighting function (`--hdrWeight`).
- @param hdr_response_curve {str} Luminance response curve (`--hdrResponseCurve`).
- @param tmo {str} Tone-mapping operator (`--tmo`).
- @param tmo_extra_args {tuple[str, ...]} Explicit passthrough `--tmo*` option pairs in CLI order.
- @return {None} Immutable dataclass container.
- @satisfies REQ-061, REQ-067, REQ-068

### class `class OpenCvMergeOptions` `@dataclass(frozen=True)` (L532-552)
- @brief Hold deterministic OpenCV HDR merge option values.
- @details Encapsulates OpenCV merge controls used by the `--hdr-merge=OpenCV` backend. Debevec and Robertson linearize the extracted float brackets and execute `Merge* -> Tonemap` directly on float inputs, Mertens executes exposure fusion directly on float brackets with OpenCV-equivalent output rescaling, and all external interfaces stay RGB float `[0,1]`.
- @param merge_algorithm {str} Canonical OpenCV merge algorithm in `{"Debevec","Robertson","Mertens"}`.
- @param tonemap_enabled {bool} `True` enables simple OpenCV gamma tone mapping for Debevec/Robertson outputs.
- @param tonemap_gamma {float} Positive gamma value passed to `cv2.createTonemap`; `2.2` matches standard display brightness.
- @return {None} Immutable dataclass container.
- @satisfies REQ-108, REQ-109, REQ-110, REQ-141, REQ-142, REQ-143, REQ-144, REQ-152, REQ-153, REQ-154

### class `class HdrPlusOptions` `@dataclass(frozen=True)` (L554-577)
- @brief Hold deterministic HDR+ merge option values.
- @details Encapsulates the user-facing RGB-to-scalar proxy selection, hierarchical alignment search radius, and temporal weight controls used by the HDR+ backend port. Temporal values remain expressed in the historical 16-bit code-domain units so CLI defaults, parsing, and runtime diagnostics stay unchanged while normalized float32 runtime controls are derived later.
- @param proxy_mode {str} Scalar proxy mode selector in `{"rggb","bt709","mean"}`.
- @param search_radius {int} Per-layer alignment search radius in pixels; candidate offsets span `[-search_radius, search_radius-1]`.
- @param temporal_factor {float} User-facing denominator stretch factor defined on historical 16-bit code-domain tile L1 distance.
- @param temporal_min_dist {float} User-facing distance floor defined on historical 16-bit code-domain tile L1 distance.
- @param temporal_max_dist {float} User-facing distance ceiling defined on historical 16-bit code-domain tile L1 distance.
- @return {None} Immutable dataclass container.
- @satisfies REQ-126, REQ-127, REQ-128, REQ-130, REQ-131, REQ-138

### class `class HdrPlusTemporalRuntimeOptions` `@dataclass(frozen=True)` (L579-598)
- @brief Hold HDR+ temporal controls remapped for normalized distance inputs.
- @details Converts user-facing temporal CLI values into runtime controls consumed by normalized float32 `[0,1]` tile L1 distances. The denominator stretch factor and distance floor are scaled from the historical 16-bit code-domain units, while the cutoff remains stored in the post-normalized comparison space so the existing weight curve stays numerically equivalent.
- @param distance_factor {float} Normalized-distance denominator stretch factor.
- @param min_distance {float} Normalized-distance floor before inverse-distance attenuation starts.
- @param max_weight_distance {float} Dimensionless cutoff threshold applied after normalization.
- @return {None} Immutable dataclass container.
- @satisfies REQ-114, REQ-131, REQ-138

### class `class AutoEvInputs` `@dataclass(frozen=True)` (L600-627)
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
- @satisfies REQ-009

### class `class AutoZeroEvaluation` `@dataclass(frozen=True)` (L629-647)
- @brief Hold the three automatic EV-zero candidate evaluations.
- @details Stores the entropy-optimized candidate (`miglior_ev`), the ETTR candidate (`ev_ettr`), and the detail-preservation candidate (`ev_dettaglio`) computed from one normalized linear RGB float image. Values are rounded to one decimal place before downstream selection.
- @param miglior_ev {float} Entropy-optimized EV candidate.
- @param ev_ettr {float} ETTR EV candidate.
- @param ev_dettaglio {float} Detail-preservation EV candidate.
- @return {None} Immutable auto-zero evaluation container.
- @satisfies REQ-008, REQ-032, REQ-052

### fn `def _print_box_table(headers, rows, header_rows=())` `priv` (L648-684)
- @brief Print one Unicode box-drawing table.
- @details Computes deterministic column widths from headers and rows, then prints aligned borders and cells using Unicode line-drawing glyphs.
- @param headers {tuple[str, ...]} Table header labels in fixed output order.
- @param header_rows {tuple[tuple[str, ...], ...]} Additional physical header rows rendered before header/body separator.
- @param rows {tuple[tuple[str, ...], ...]} Table body rows with one value per column.
- @return {None} Writes formatted table to stdout.
- @satisfies REQ-070

### fn `def _border(left, middle, right)` `priv` (L668-670)
- @brief Print one Unicode box-drawing table.
- @details Computes deterministic column widths from headers and rows, then
prints aligned borders and cells using Unicode line-drawing glyphs.
- @param headers {tuple[str, ...]} Table header labels in fixed output order.
- @param header_rows {tuple[tuple[str, ...], ...]} Additional physical header rows rendered before header/body separator.
- @param rows {tuple[tuple[str, ...], ...]} Table body rows with one value per column.
- @return {None} Writes formatted table to stdout.
- @satisfies REQ-070

### fn `def _line(values)` `priv` (L671-674)

### fn `def _build_two_line_operator_rows(operator_entries)` `priv` (L685-701)
- @brief Build two-line physical rows for luminance operator table.
- @details Expands each logical operator entry into two physical rows while preserving the bordered three-column layout used by help rendering.
- @param operator_entries {tuple[tuple[str, str, str, str, str], ...]} Logical operator rows in `(operator, family, character, neutrality, when_to_use)` format.
- @return {tuple[tuple[str, str, str], ...]} Expanded physical rows for `_print_box_table`.
- @satisfies REQ-070

### fn `def _print_help_section(title)` `priv` (L702-716)
- @brief Print one numbered help section title.
- @details Emits one blank separator line followed by one deterministic section title so conversion help stays ordered by pipeline execution step. Complexity: O(1). Side effects: stdout writes only.
- @param title {str} Section title text already normalized for display order.
- @return {None} Writes formatted section title to stdout.
- @satisfies REQ-017, REQ-155

### fn `def _print_help_option(option_label, description, detail_lines=())` `priv` (L717-758)
- @brief Print one aligned conversion-help option block.
- @details Renders one option label and wrapped description using a fixed indentation grid, then renders any continuation detail lines under the same description column. Complexity: O(n) in total output characters. Side effects: stdout writes only.
- @param option_label {str} Left-column option label or positional argument label.
- @param description {str} Primary description line for the option block.
- @param detail_lines {tuple[str, ...]|list[str]} Additional wrapped lines aligned under the description column.
- @return {None} Writes formatted option block to stdout.
- @satisfies REQ-017, REQ-155, REQ-156

### fn `def print_help(version)` (L759-958)
- @brief Print help text for the `dng2jpg` command.
- @details Renders conversion help in pipeline execution order. Groups each processing stage with the selectors and knobs that configure that stage, documents allowed values and activation conditions for every accepted conversion option, and prints effective omitted-value defaults using aligned indentation and stable table formatting. Complexity: O(n) in emitted characters. Side effects: stdout writes only.
- @param version {str} CLI version label to append in usage output.
- @return {None} Writes help text to stdout.
- @satisfies DES-008, REQ-017, REQ-018, REQ-019, REQ-020, REQ-021, REQ-022, REQ-023, REQ-024, REQ-025, REQ-033, REQ-100, REQ-101, REQ-102, REQ-107, REQ-111, REQ-124, REQ-125, REQ-127, REQ-128, REQ-135, REQ-141, REQ-143, REQ-146, REQ-155, REQ-156

### fn `def _calculate_max_ev_from_bits(bits_per_color)` `priv` (L1129-1147)
- @brief Compute EV ceiling from detected DNG bits per color.
- @details Implements `MAX=((bits_per_color-8)/2)` and validates minimum supported bit depth before computing clamp ceiling used by static and adaptive EV flows.
- @param bits_per_color {int} Detected source DNG bits per color.
- @return {float} Bit-derived EV ceiling.
- @exception ValueError Raised when bit depth is below supported minimum.
- @satisfies REQ-057, REQ-081, REQ-093, REQ-094, REQ-096

### fn `def _calculate_safe_ev_zero_max(base_max_ev)` `priv` (L1148-1160)
- @brief Compute safe absolute EV-zero ceiling preserving at least `±1EV` bracket.
- @details Derives `SAFE_ZERO_MAX=(BASE_MAX-1)` where `BASE_MAX=((bits_per_color-8)/2)`. Safe range guarantees `MAX_BRACKET=(BASE_MAX-abs(ev_zero)) >= 1`.
- @param base_max_ev {float} Bit-derived `BASE_MAX` value.
- @return {float} Safe absolute EV-zero ceiling.
- @satisfies DES-003, REQ-018, REQ-030

### fn `def _derive_supported_ev_zero_values(base_max_ev)` `priv` (L1161-1177)
- @brief Derive non-negative EV-zero quantization set preserving `±1EV` bracket.
- @details Generates deterministic quarter-step tuple in `[0, SAFE_ZERO_MAX]`, where `SAFE_ZERO_MAX=max(0, BASE_MAX-1)` and `BASE_MAX=((bits_per_color-8)/2)`.
- @param base_max_ev {float} Bit-derived `BASE_MAX` value.
- @return {tuple[float, ...]} Supported non-negative EV-zero magnitudes including `0.0`.
- @satisfies DES-003, REQ-018, REQ-030

### fn `def _derive_supported_ev_values(bits_per_color, ev_zero=0.0)` `priv` (L1178-1206)
- @brief Derive valid bracket EV selector set from bit depth and `ev_zero`.
- @details Builds deterministic EV selector tuple with fixed `0.25` step in closed range `[0.25, MAX_BRACKET]`, where `MAX_BRACKET=((bits_per_color-8)/2)-abs(ev_zero)`.
- @param bits_per_color {int} Detected source DNG bits per color.
- @param ev_zero {float} Central EV selector.
- @return {tuple[float, ...]} Supported bracket EV selector tuple.
- @exception ValueError Raised when bit-derived bracket EV ceiling cannot produce any selector values.
- @satisfies REQ-057, REQ-081, REQ-093, REQ-094, REQ-096

### fn `def _detect_dng_bits_per_color(raw_handle)` `priv` (L1207-1252)
- @brief Detect source DNG bits-per-color from RAW metadata.
- @details Prefers RAW sample container bit depth from `raw_handle.raw_image_visible.dtype.itemsize * 8` because the DNG white level can represent effective sensor range (for example `4000`) while RAW samples are still stored in a wider container (for example `uint16`). Falls back to `raw_handle.white_level` `bit_length` when container metadata is unavailable.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {int} Detected source DNG bits per color.
- @exception ValueError Raised when metadata is missing, non-numeric, or non-positive.
- @satisfies REQ-057, REQ-081, REQ-092, REQ-093

### fn `def _is_ev_value_on_supported_step(ev_value)` `priv` (L1253-1266)
- @brief Validate EV value belongs to fixed `0.25` step grid.
- @details Checks whether EV value can be represented as integer multiples of `0.25` using tolerance-based floating-point comparison.
- @param ev_value {float} Parsed EV numeric value.
- @return {bool} `True` when EV value is aligned to `0.25` step.
- @satisfies REQ-057

### fn `def _parse_ev_option(ev_raw)` `priv` (L1267-1298)
- @brief Parse and validate one EV option value.
- @details Converts token to `float`, enforces minimum `0.25`, and enforces fixed `0.25` granularity. Bit-depth upper-bound validation is deferred until RAW metadata is loaded from source DNG.
- @param ev_raw {str} EV token extracted from command arguments.
- @return {float|None} Parsed EV value when valid; `None` otherwise.
- @satisfies REQ-056, REQ-057

### fn `def _parse_ev_zero_option(ev_zero_raw)` `priv` (L1299-1329)
- @brief Parse and validate one `--ev-zero` option value.
- @details Converts token to `float`, enforces fixed `0.25` granularity, and defers bit-depth bound validation to RAW-metadata runtime stage.
- @param ev_zero_raw {str} EV-zero token extracted from command arguments.
- @return {float|None} Parsed EV-zero value when valid; `None` otherwise.
- @satisfies REQ-094

### fn `def _parse_auto_ev_option(auto_ev_raw)` `priv` (L1330-1349)
- @brief Parse and validate one `--auto-ev` option value.
- @details Accepts only explicit enable/disable tokens to keep deterministic CLI behavior and unambiguous precedence handling with `--ev`.
- @param auto_ev_raw {str} Raw `--auto-ev` value token from CLI args.
- @return {bool|None} Parsed enable-state value; `None` on parse failure.
- @satisfies REQ-056, CTN-003

### fn `def _parse_auto_zero_option(auto_zero_raw)` `priv` (L1350-1369)
- @brief Parse and validate one `--auto-zero` option value.
- @details Accepts only explicit enable/disable tokens to keep deterministic CLI behavior and unambiguous precedence handling with `--ev-zero`.
- @param auto_zero_raw {str} Raw `--auto-zero` value token from CLI args.
- @return {bool|None} Parsed enable-state value; `None` on parse failure.
- @satisfies REQ-018

### fn `def _parse_percentage_option(option_name, option_raw)` `priv` (L1370-1392)
- @brief Parse and validate one percentage option value.
- @details Converts option token to `float`, requires inclusive range `[0, 100]`, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {float|None} Parsed percentage value when valid; `None` otherwise.
- @satisfies REQ-019, REQ-030

### fn `def _parse_auto_brightness_option(auto_brightness_raw)` `priv` (L1393-1412)
- @brief Parse and validate one `--auto-brightness` option value.
- @details Accepts only explicit enable/disable tokens to keep deterministic toggle behavior for stage activation.
- @param auto_brightness_raw {str} Raw `--auto-brightness` value token from CLI args.
- @return {bool|None} Parsed enable-state value; `None` on parse failure.
- @satisfies REQ-065, REQ-089

### fn `def _parse_auto_levels_option(auto_levels_raw)` `priv` (L1413-1432)
- @brief Parse and validate one `--auto-levels` option value.
- @details Accepts only explicit enable/disable tokens to keep deterministic toggle behavior for stage activation.
- @param auto_levels_raw {str} Raw `--auto-levels` value token from CLI args.
- @return {bool|None} Parsed enable-state value; `None` on parse failure.
- @satisfies REQ-100, REQ-101

### fn `def _parse_explicit_boolean_option(option_name, option_raw)` `priv` (L1433-1453)
- @brief Parse one explicit boolean option value.
- @details Accepts canonical true/false token families to keep deterministic toggle parsing for CLI knobs that support both enabling and disabling.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {bool|None} Parsed boolean value; `None` on parse failure.
- @satisfies REQ-101

### fn `def _parse_opencv_merge_algorithm_option(algorithm_raw)` `priv` (L1454-1478)
- @brief Parse OpenCV merge algorithm selector.
- @details Accepts case-insensitive OpenCV algorithm names, normalizes them to canonical runtime tokens, and rejects unsupported values with deterministic diagnostics.
- @param algorithm_raw {str} Raw `--opencv-merge-algorithm` selector token.
- @return {str|None} Canonical OpenCV merge algorithm token or `None` on parse failure.
- @satisfies REQ-108, REQ-141

### fn `def _parse_opencv_options(opencv_raw_values)` `priv` (L1479-1525)
- @brief Parse and validate OpenCV HDR merge knob values.
- @details Applies OpenCV defaults for algorithm selector, tone-map toggle, and tone-map gamma, validates allowed values, and returns one immutable backend option container for downstream merge dispatch.
- @param opencv_raw_values {dict[str, str]} Raw `--opencv-*` option values keyed by long option name.
- @return {OpenCvMergeOptions|None} Parsed OpenCV merge options or `None` on validation error.
- @satisfies REQ-141, REQ-143

### fn `def _clamp_ev_to_supported(ev_candidate, ev_values)` `priv` (L1526-1539)
- @brief Clamp one EV candidate to supported numeric interval.
- @details Applies lower/upper bound clamp to keep computed adaptive EV value inside configured EV bounds before command generation.
- @param ev_candidate {float} Candidate EV delta from adaptive optimization.
- @param ev_values {tuple[float, ...]} Sorted supported EV selector values.
- @return {float} Clamped EV delta in `[min(ev_values), max(ev_values)]`.
- @satisfies REQ-081, REQ-093

### fn `def _quantize_ev_to_supported(ev_value, ev_values)` `priv` (L1540-1561)
- @brief Quantize one EV value to nearest supported selector value.
- @details Chooses nearest value from `ev_values` to preserve deterministic three-bracket behavior in downstream static multiplier and HDR command construction paths.
- @param ev_value {float} Clamped EV value.
- @param ev_values {tuple[float, ...]} Sorted supported EV selector values.
- @return {float} Nearest supported EV selector value.
- @satisfies REQ-080, REQ-081, REQ-093

### fn `def _quantize_ev_toward_zero_step(ev_value, step=EV_STEP)` `priv` (L1562-1583)
- @brief Quantize one EV value toward zero using fixed step size.
- @details Converts EV value to step units, truncates fractional remainder toward zero, and reconstructs signed EV value using deterministic `0.25` precision rounding.
- @param ev_value {float} EV value to quantize.
- @param step {float} Quantization step size.
- @return {float} Quantized EV value with truncation toward zero.
- @satisfies REQ-081, REQ-097

### fn `def _apply_auto_percentage_scaling(ev_value, percentage)` `priv` (L1584-1598)
- @brief Apply percentage scaling to EV value with downward 0.25 quantization.
- @details Multiplies EV value by percentage in `[0,100]` and quantizes scaled result toward zero with fixed `0.25` step.
- @param ev_value {float} EV value before scaling.
- @param percentage {float} Percentage scaling factor in `[0,100]`.
- @return {float} Scaled EV value quantized toward zero.
- @satisfies REQ-081, REQ-097

### fn `def _extract_normalized_preview_luminance_stats(raw_handle)` `priv` (L1599-1658)
- @brief Extract normalized preview luminance percentiles from RAW handle.
- @details Generates one deterministic linear preview (`bright=1.0`, `output_bps=16`, camera white balance, no auto-bright, linear gamma, `user_flip=0`), computes luminance for each pixel, then returns normalized low/median/high percentiles by dividing with preview maximum luminance.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {tuple[float, float, float]} Normalized `(p_low, p_median, p_high)` in `(0,1)`.
- @exception ValueError Raised when preview extraction cannot produce valid luminance values.
- @satisfies REQ-009

### fn `def _percentile(percentile_value)` `priv` (L1633-1643)
- @brief Extract normalized preview luminance percentiles from RAW handle.
- @details Generates one deterministic linear preview (`bright=1.0`,
`output_bps=16`, camera white balance, no auto-bright, linear gamma,
`user_flip=0`), computes luminance for each pixel, then returns normalized
low/median/high percentiles by dividing with preview maximum luminance.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {tuple[float, float, float]} Normalized `(p_low, p_median, p_high)` in `(0,1)`.
- @exception ValueError Raised when preview extraction cannot produce valid luminance values.
- @satisfies REQ-009

### fn `def _extract_base_rgb_linear_float(raw_handle, np_module)` `priv` (L1659-1687)
- @brief Extract one linear normalized RGB base image from one RAW handle.
- @details Executes exactly one `rawpy.postprocess` call with deterministic parameters `bright=1.0`, `output_bps=16`, `use_camera_wb=True`, `no_auto_bright=True`, `gamma=(1.0,1.0)`, and `user_flip=0`, then normalizes the demosaiced maximum-resolution RGB output to float `[0,1]`. Complexity: O(H*W). Side effects: one RAW postprocess invocation.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @param np_module {ModuleType} Imported numpy module.
- @return {object} Normalized RGB float tensor in `[0,1]`.
- @see _extract_normalized_preview_luminance_stats
- @satisfies REQ-010, REQ-158

### fn `def _coerce_positive_luminance(value, fallback)` `priv` (L1688-1707)
- @brief Coerce luminance scalar to positive range for logarithmic math.
- @details Converts input to float and enforces a strictly positive minimum. Returns fallback when conversion fails or result is non-positive.
- @param value {object} Candidate luminance scalar.
- @param fallback {float} Fallback positive luminance scalar.
- @return {float} Positive luminance value suitable for `log2`.
- @satisfies REQ-081

### fn `def _calculate_bt709_luminance(np_module, image_rgb_float)` `priv` (L1708-1730)
- @brief Convert one normalized RGB float image to BT.709 luminance.
- @details Normalizes the input image to the repository RGB float contract and computes luminance in the linear gamma=`1` domain using BT.709 coefficients `(0.2126, 0.7152, 0.0722)`. Complexity: O(H*W). Side effects: none.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} Input image payload convertible to normalized RGB float `[0,1]`.
- @return {object} Linear luminance tensor with shape `(H,W)` and dtype `float32`.
- @satisfies REQ-008, REQ-032

### fn `def _smoothstep(np_module, values, edge0, edge1)` `priv` (L1731-1749)
- @brief Evaluate one smoothstep ramp with clamped normalized input.
- @details Computes the cubic Hermite interpolation `t*t*(3-2*t)` over input values normalized into `[0,1]` using denominator `max(edge1-edge0, 1e-6)`. Complexity: O(N). Side effects: none.
- @param np_module {ModuleType} Imported numpy module.
- @param values {object} Numeric tensor evaluated element-wise.
- @param edge0 {float} Lower transition edge.
- @param edge1 {float} Upper transition edge.
- @return {object} Float tensor with values in `[0,1]`.
- @satisfies REQ-032

### fn `def _calculate_entropy_optimized_ev(cv2_module, np_module, luminance_float)` `priv` (L1750-1795)
- @brief Compute the entropy-optimized EV candidate on linear luminance.
- @details Sweeps EV values in range `[-3.0,+3.0]` with step `0.1`, scales the normalized linear luminance by `2**EV`, clips into `[0,1]`, converts the clipped image directly to 8-bit linear code values, evaluates histogram entropy with clipping penalties, and returns the highest-score EV rounded to one decimal place. Complexity: O(K*H*W)` where `K=61`. Side effects: none.
- @param cv2_module {ModuleType} Imported OpenCV module.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Linear luminance tensor normalized to `[0,1]`.
- @return {float} Entropy-optimized EV candidate rounded to one decimal place.
- @satisfies REQ-032

### fn `def _calculate_ettr_ev(np_module, luminance_float)` `priv` (L1796-1815)
- @brief Compute the ETTR EV candidate on linear luminance.
- @details Evaluates the `99`th percentile of normalized linear luminance, targets that percentile to `0.90`, computes `log2(target/L99)`, and returns the result rounded to one decimal place. Fully black inputs return `0.0`. Complexity: O(H*W log(H*W)) due to percentile extraction. Side effects: none.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Linear luminance tensor normalized to `[0,1]`.
- @return {float} ETTR EV candidate rounded to one decimal place.
- @satisfies REQ-032

### fn `def _calculate_detail_preservation_ev(cv2_module, np_module, luminance_float)` `priv` (L1816-1882)
- @brief Compute the detail-preservation EV candidate on linear luminance.
- @details Builds local-detail weights from Sobel gradients on `log(luminance+eps)`, suppresses flat regions below the `40`th percentile, estimates a heuristic noise floor from the `1`st percentile, sweeps EV in `[-3.0,+3.0]` with step `0.1`, and maximizes preserved weighted detail while penalizing highlight clipping and shadow crushing. Returns the best EV rounded to one decimal place. Complexity: O(K*H*W)` where `K=61`. Side effects: none.
- @param cv2_module {ModuleType} Imported OpenCV module.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Linear luminance tensor normalized to `[0,1]`.
- @return {float} Detail-preservation EV candidate rounded to one decimal place.
- @satisfies REQ-032

### fn `def _calculate_auto_zero_evaluations(cv2_module, np_module, image_rgb_float)` `priv` (L1883-1920)
- @brief Compute the three automatic EV-zero candidate evaluations.
- @details Migrates `calcola_correzioni_ev(immagine_float)` from the external prototype into the current pipeline, adapts it to the repository linear gamma=`1` RGB float contract, computes BT.709 luminance, evaluates `miglior_ev`, `ev_ettr`, and `ev_dettaglio`, and returns all three rounded candidates without applying selector quantization. Complexity: dominated by the EV sweeps in entropy/detail evaluation. Side effects: none.
- @param cv2_module {ModuleType} Imported OpenCV module.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} Input image payload convertible to normalized RGB float `[0,1]`.
- @return {AutoZeroEvaluation} Candidate EV evaluations on the normalized linear image.
- @satisfies REQ-008, REQ-032

### fn `def _evaluate_auto_zero_exposure(cv2_module, np_module, image_rgb_float)` `priv` (L1921-1954)
- @brief Evaluate automatic EV-zero candidates and print the selected value.
- @details Computes the migrated `miglior_ev`, `ev_ettr`, and `ev_dettaglio` candidates on the normalized linear RGB float image, prints each candidate and the selected minimum EV using deterministic diagnostics, and returns the selected value. Complexity: delegated to `_calculate_auto_zero_evaluations`. Side effects: writes diagnostics through `print_info`.
- @param cv2_module {ModuleType} Imported OpenCV module.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} Input image payload convertible to normalized RGB float `[0,1]`.
- @return {float} Minimum candidate EV selected for downstream auto-zero scaling.
- @satisfies REQ-008, REQ-032, REQ-052

### fn `def _optimize_adaptive_ev_delta(auto_ev_inputs)` `priv` (L1955-1984)
- @brief Compute adaptive EV delta from preview luminance statistics.
- @details Computes symmetric delta constraints around resolved EV-zero: `ev_shadow=max(0, log2(target_shadow/p_low)-ev_zero)` and `ev_high=max(0, ev_zero-log2(target_highlight/p_high))`, chooses maximum as safe symmetric bracket half-width, then clamps and quantizes to supported EV selector set.
- @param auto_ev_inputs {AutoEvInputs} Adaptive EV scalar inputs.
- @return {float} Quantized adaptive EV delta.
- @satisfies REQ-080, REQ-081, REQ-093, REQ-095

### fn `def _compute_auto_ev_value_from_stats(` `priv` (L1985-1990)

### fn `def _compute_auto_ev_value(raw_handle, supported_ev_values=None, ev_zero=0.0)` `priv` (L2018-2045)
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

### fn `def _resolve_ev_zero(` `priv` (L2046-2055)

### fn `def _resolve_ev_value(` `priv` (L2119-2126)
- @brief Resolve EV-zero center from manual or automatic selector.
- @details Uses manual `--ev-zero` unless `--auto-zero` is enabled. In
automatic mode evaluates `miglior_ev`, `ev_ettr`, and `ev_dettaglio` on the
normalized linear gamma=`1` RGB float base image migrated from the external
prototype, selects the minimum candidate, clamps it to the safe bit-derived
range, applies percentage scaling, and validates the final result against
`SAFE_ZERO_MAX`.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @param ev_zero {float} Parsed manual EV-zero candidate.
- @param auto_zero_enabled {bool} Auto-zero selector state.
- @param auto_zero_pct {float} Percentage scaler applied to computed auto-zero result.
- @param base_max_ev {float} Bit-derived `BASE_MAX` limit.
- @param supported_ev_values_for_auto_zero {tuple[float, ...]} Supported non-negative EV-zero magnitudes for compatibility with downstream safe-range handling.
- @param preview_luminance_stats {tuple[float, float, float]|None} Unused compatibility argument retained to minimize call-site changes.
- @param auto_zero_dependencies {tuple[ModuleType, ModuleType]|None} Optional `(cv2_module, numpy_module)` tuple.
- @param base_rgb_float {object|None} Optional precomputed normalized linear RGB float base image.
- @return {float} Resolved EV-zero center.
- @exception ValueError Raised when resolved EV-zero is outside bit-derived safe range.
- @exception RuntimeError Raised when auto-zero dependencies are unavailable.
- @satisfies REQ-008, REQ-018, REQ-032, REQ-037

### fn `def _parse_luminance_text_option(option_name, option_raw)` `priv` (L2179-2199)
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

### fn `def _parse_gamma_option(gamma_raw)` `priv` (L2200-2238)
- @brief Parse and validate one gamma option value pair.
- @details Accepts comma-separated positive float pair in `a,b` format with optional surrounding parentheses, normalizes to `(a, b)` tuple, and rejects malformed, non-numeric, or non-positive values. Parsed values are retained for CLI compatibility diagnostics and do not alter linear HDR bracket extraction.
- @param gamma_raw {str} Raw gamma token extracted from CLI args.
- @return {tuple[float, float]|None} Parsed gamma tuple when valid; `None` otherwise.
- @satisfies REQ-020, REQ-064, REQ-157

### fn `def _parse_positive_float_option(option_name, option_raw)` `priv` (L2239-2262)
- @brief Parse and validate one positive float option value.
- @details Converts option token to `float`, requires value greater than zero, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {float|None} Parsed positive float value when valid; `None` otherwise.
- @satisfies REQ-065

### fn `def _parse_positive_int_option(option_name, option_raw)` `priv` (L2263-2286)
- @brief Parse and validate one positive integer option value.
- @details Converts option token to `int`, requires value greater than zero, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {int|None} Parsed positive integer value when valid; `None` otherwise.
- @satisfies REQ-127, REQ-130

### fn `def _parse_tmo_passthrough_value(option_name, option_raw)` `priv` (L2287-2303)
- @brief Parse and validate one luminance `--tmo*` passthrough value.
- @details Rejects empty values and preserves original payload for transparent forwarding to `luminance-hdr-cli`.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {str|None} Original value when valid; `None` otherwise.
- @satisfies REQ-067

### fn `def _parse_jpg_compression_option(compression_raw)` `priv` (L2304-2326)
- @brief Parse and validate JPEG compression option value.
- @details Converts option token to `int`, requires inclusive range `[0, 100]`, and emits deterministic parse errors on malformed values.
- @param compression_raw {str} Raw compression token value from CLI args.
- @return {int|None} Parsed JPEG compression level when valid; `None` otherwise.
- @satisfies REQ-065

### fn `def _parse_float_exclusive_range_option(option_name, option_raw, min_value, max_value)` `priv` (L2327-2351)
- @brief Parse and validate one float option in an exclusive range.
- @details Converts option token to `float`, validates `min < value < max`, and emits deterministic parse errors on malformed or out-of-range values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @param min_value {float} Exclusive minimum bound.
- @param max_value {float} Exclusive maximum bound.
- @return {float|None} Parsed float value when valid; `None` otherwise.
- @satisfies REQ-065, REQ-089

### fn `def _parse_non_negative_float_option(option_name, option_raw)` `priv` (L2352-2374)
- @brief Parse and validate one non-negative float option value.
- @details Converts option token to `float`, requires value greater than or equal to zero, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {float|None} Parsed non-negative float value when valid; `None` otherwise.
- @satisfies REQ-065, REQ-089

### fn `def _parse_float_in_range_option(option_name, option_raw, min_value, max_value)` `priv` (L2375-2400)
- @brief Parse and validate one float option constrained to inclusive range.
- @details Converts option token to `float`, validates inclusive bounds, and emits deterministic parse errors on malformed or out-of-range values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @param min_value {float} Inclusive minimum bound.
- @param max_value {float} Inclusive maximum bound.
- @return {float|None} Parsed bounded float value when valid; `None` otherwise.
- @satisfies REQ-082, REQ-084

### fn `def _parse_positive_int_pair_option(option_name, option_raw)` `priv` (L2401-2432)
- @brief Parse and validate one positive integer pair option value.
- @details Accepts `rowsxcols`, `rowsXcols`, or `rows,cols`, converts both tokens to `int`, requires each value to be greater than zero, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {tuple[int, int]|None} Parsed positive integer pair when valid; `None` otherwise.
- @satisfies REQ-065, REQ-125

### fn `def _parse_auto_brightness_options(auto_brightness_raw_values)` `priv` (L2433-2529)
- @brief Parse and validate auto-brightness parameters.
- @details Parses optional controls for the original photographic BT.709 float-domain tonemap pipeline and applies deterministic defaults for omitted auto-brightness options.
- @param auto_brightness_raw_values {dict[str, str]} Raw `--ab-*` option values keyed by long option name.
- @return {AutoBrightnessOptions|None} Parsed auto-brightness options or `None` on validation error.
- @satisfies REQ-088, REQ-089, REQ-103, REQ-104, REQ-105, REQ-124, REQ-135

### fn `def _parse_auto_levels_hr_method_option(auto_levels_method_raw)` `priv` (L2530-2561)
- @brief Parse auto-levels highlight reconstruction method option value.
- @details Validates case-insensitive method names and normalizes accepted values to canonical tokens used by runtime dispatch.
- @param auto_levels_method_raw {str} Raw `--al-highlight-reconstruction-method` option token.
- @return {str|None} Canonical method token or `None` on parse failure.
- @satisfies REQ-101, REQ-102, REQ-119

### fn `def _parse_auto_levels_options(auto_levels_raw_values)` `priv` (L2562-2625)
- @brief Parse and validate auto-levels parameters.
- @details Parses histogram clip percentage, explicit gamut clipping toggle, optional highlight reconstruction method, and Inpaint Opposed gain threshold using RawTherapee-aligned defaults.
- @param auto_levels_raw_values {dict[str, str]} Raw `--al-*` option values keyed by long option name.
- @return {AutoLevelsOptions|None} Parsed auto-levels options or `None` on validation error.
- @satisfies REQ-100, REQ-101, REQ-102, REQ-116

### fn `def _parse_auto_adjust_options(auto_adjust_raw_values)` `priv` (L2626-2775)
- @brief Parse and validate auto-adjust knobs.
- @details Applies defaults for omitted knobs, validates scalar/range constraints, validates CLAHE-luma controls, and enforces level percentile ordering contract.
- @param auto_adjust_raw_values {dict[str, str]} Raw `--aa-*` option values keyed by long option name.
- @return {AutoAdjustOptions|None} Parsed shared auto-adjust options or `None` on validation error.
- @satisfies REQ-051, REQ-082, REQ-083, REQ-084, REQ-123, REQ-125

### fn `def _parse_hdrplus_proxy_mode_option(proxy_mode_raw)` `priv` (L2776-2794)
- @brief Parse HDR+ scalar proxy mode selector.
- @details Accepts case-insensitive proxy mode names, normalizes to canonical lowercase spelling, and rejects unsupported values with deterministic diagnostics.
- @param proxy_mode_raw {str} Raw HDR+ proxy mode token from CLI args.
- @return {str|None} Canonical proxy mode token or `None` on parse failure.
- @satisfies REQ-126, REQ-127, REQ-130

### fn `def _parse_hdrplus_options(hdrplus_raw_values)` `priv` (L2795-2871)
- @brief Parse and validate HDR+ merge knob values.
- @details Applies source-matching defaults for omitted knobs, validates the RGB-to-scalar proxy selector, alignment search radius, and temporal weight parameters, and rejects inconsistent temporal threshold combinations.
- @param hdrplus_raw_values {dict[str, str]} Raw `--hdrplus-*` option values keyed by long option name.
- @return {HdrPlusOptions|None} Parsed HDR+ options or `None` on validation error.
- @satisfies REQ-126, REQ-127, REQ-128, REQ-130

### fn `def _parse_auto_adjust_option(auto_adjust_raw)` `priv` (L2872-2895)
- @brief Parse auto-adjust enable selector option value.
- @details Accepts case-insensitive `enable` and `disable` tokens and maps them to the resolved auto-adjust stage state.
- @param auto_adjust_raw {str} Raw auto-adjust enable token.
- @return {bool|None} `True` when auto-adjust is enabled; `False` when disabled; `None` on parse failure.
- @satisfies REQ-065, REQ-073, REQ-075

### fn `def _parse_hdr_merge_option(hdr_merge_raw)` `priv` (L2896-2925)
- @brief Parse HDR backend selector option value.
- @details Accepts case-insensitive backend selector names and normalizes them to canonical runtime mode names.
- @param hdr_merge_raw {str} Raw `--hdr-merge` selector token.
- @return {str|None} Canonical HDR merge mode or `None` on parse failure.
- @satisfies CTN-002, REQ-023, REQ-024, REQ-107, REQ-111

### fn `def _resolve_default_postprocess(` `priv` (L2926-2929)

### fn `def _parse_run_options(args)` `priv` (L3001-3200)
- @brief Resolve backend-specific postprocess defaults.
- @brief Parse CLI args into input, output, and EV parameters.
- @details Selects backend-specific defaults. Uses algorithm-specific OpenCV
defaults keyed by resolved `Debevec|Robertson|Mertens`, luminance-operator-
specific defaults for `Luminace-HDR`, and neutral defaults for `HDR-Plus`
and untuned luminance operators. Complexity: O(1). Side effects: none.
- @details Supports positional file arguments, optional exposure selectors (`--ev=<value>`/`--ev <value>` and `--auto-ev[=<enable|disable>]`) with deterministic precedence where static `--ev` overrides enabled `--auto-ev`, optional `--ev-zero=<value>` or `--ev-zero <value>`, optional `--auto-zero[=<enable|disable>]`, optional `--auto-zero-pct=<0..100>`, optional `--auto-ev-pct=<0..100>`, optional `--gamma=<a,b>` or `--gamma <a,b>` retained for compatibility diagnostics only, optional postprocess controls, optional auto-brightness stage and `--ab-*` knobs, optional auto-levels stage and `--al-*` knobs, optional shared auto-adjust knobs, optional backend selector (`--hdr-merge=<Luminace-HDR|OpenCV|HDR-Plus>` default `OpenCV`), OpenCV backend controls, HDR+ backend controls, and luminance backend controls including explicit `--tmo*` passthrough options and optional auto-adjust enable selector (`--auto-adjust <enable|disable>`), plus optional `--debug` persistent checkpoint emission; rejects unknown options and invalid arity.
- @param hdr_merge_mode {str} Canonical HDR merge mode selector.
- @param luminance_tmo {str} Selected luminance tone-mapping operator.
- @param opencv_merge_algorithm {str} Resolved OpenCV merge algorithm selector.
- @param args {list[str]} Raw command argument vector.
- @return {tuple[float, float, float, float]} Defaults in `(post_gamma, brightness, contrast, saturation)` order.
- @return {tuple[Path, Path, float|None, bool, tuple[float, float], PostprocessOptions, bool, bool, LuminanceOptions, OpenCvMergeOptions, HdrPlusOptions, bool, float, bool, float, float]|None} Parsed `(input, output, ev, auto_ev, gamma, postprocess, enable_luminance, enable_opencv, luminance_options, opencv_merge_options, hdrplus_options, enable_hdr_plus, ev_zero, auto_zero_enabled, auto_zero_pct, auto_ev_pct)` tuple; `None` on parse failure.
- @satisfies DES-006, DES-008, REQ-145
- @satisfies CTN-002, CTN-003, REQ-007, REQ-008, REQ-009, REQ-018, REQ-022, REQ-023, REQ-024, REQ-025, REQ-100, REQ-101, REQ-107, REQ-111, REQ-125, REQ-135, REQ-141, REQ-143, REQ-146

### fn `def _load_image_dependencies()` `priv` (L3822-3859)
- @brief Load optional Python dependencies required by `dng2jpg`.
- @details Imports `rawpy` for RAW decoding and `imageio` for image IO using `imageio.v3` when available with fallback to top-level `imageio` module.
- @return {tuple[ModuleType, ModuleType, ModuleType]|None} `(rawpy_module, imageio_module, pil_image_module)` on success; `None` on missing dependency.
- @satisfies REQ-059, REQ-066, REQ-074

### fn `def _parse_exif_datetime_to_timestamp(datetime_raw)` `priv` (L3860-3890)
- @brief Parse one EXIF datetime token into POSIX timestamp.
- @details Normalizes scalar EXIF datetime input (`str` or `bytes`), trims optional null-terminated EXIF payload suffix, and parses strict EXIF format `YYYY:MM:DD HH:MM:SS` to generate filesystem timestamp.
- @param datetime_raw {str|bytes|object} EXIF datetime scalar.
- @return {float|None} Parsed POSIX timestamp; `None` when value is missing or invalid.
- @satisfies REQ-074, REQ-077

### fn `def _parse_exif_exposure_time_to_seconds(exposure_raw)` `priv` (L3891-3953)
- @brief Parse one EXIF exposure-time token into positive seconds.
- @details Normalizes scalar or rational-like EXIF `ExposureTime` payloads from Pillow metadata into one positive Python `float` measured in seconds. Accepted forms include numeric scalars, two-item `(numerator, denominator)` pairs, and objects exposing `numerator`/`denominator` attributes.
- @param exposure_raw {object} EXIF `ExposureTime` scalar or rational-like payload.
- @return {float|None} Positive exposure time in seconds; `None` when missing or invalid.
- @satisfies REQ-161

### fn `def _extract_dng_exif_payload_and_timestamp(pil_image_module, input_dng)` `priv` (L3954-4048)
- @brief Extract DNG EXIF payload bytes, preferred datetime timestamp, source orientation, and exposure time.
- @details Opens input DNG via Pillow, suppresses known non-actionable `PIL.TiffImagePlugin` metadata warning for malformed TIFF tag `33723`, reads EXIF mapping without orientation mutation, serializes payload for JPEG save while source image handle is still open, resolves source orientation from EXIF tag `274`, resolves datetime/exposure metadata from the top-level EXIF mapping with fallback to the nested EXIF IFD (`34665`) when Pillow omits those tags from the root mapping, parses EXIF `ExposureTime` to positive seconds, and resolves filesystem timestamp priority: `DateTimeOriginal`(36867) > `DateTimeDigitized`(36868) > `DateTime`(306).
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @param input_dng {Path} Source DNG path.
- @return {tuple[bytes|None, float|None, int, float|None]} `(exif_payload, exif_timestamp, source_orientation, exposure_time_seconds)` with orientation defaulting to `1`.
- @satisfies REQ-066, REQ-074, REQ-077, REQ-161

### fn `def _read_exif_value(exif_tag)` `priv` (L3998-4015)
- @brief Extract DNG EXIF payload bytes, preferred datetime timestamp, source orientation, and exposure time.
- @brief Resolve one EXIF value from root EXIF data with nested-IFD fallback.
- @details Opens input DNG via Pillow, suppresses known non-actionable
`PIL.TiffImagePlugin` metadata warning for malformed TIFF tag `33723`, reads
EXIF mapping without orientation mutation, serializes payload for JPEG save
while source image handle is still open, resolves source orientation from
EXIF tag `274`, resolves datetime/exposure metadata from the top-level EXIF
mapping with fallback to the nested EXIF IFD (`34665`) when Pillow omits
those tags from the root mapping, parses EXIF `ExposureTime` to positive
seconds, and resolves filesystem timestamp priority:
`DateTimeOriginal`(36867) > `DateTimeDigitized`(36868) > `DateTime`(306).
- @details Reads the requested EXIF tag from the top-level Pillow EXIF mapping first, then falls back to the nested EXIF IFD payload when available. Complexity: O(1). Side effects: none.
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @param input_dng {Path} Source DNG path.
- @param exif_tag {int} Numeric EXIF tag identifier.
- @return {tuple[bytes|None, float|None, int, float|None]} `(exif_payload, exif_timestamp, source_orientation, exposure_time_seconds)` with orientation defaulting to `1`.
- @return {object|None} Raw EXIF value or `None` when absent in both locations.
- @satisfies REQ-066, REQ-074, REQ-077, REQ-161
- @satisfies REQ-161

### fn `def _resolve_thumbnail_transpose_map(pil_image_module)` `priv` (L4049-4080)
- @brief Build deterministic EXIF-orientation-to-transpose mapping.
- @details Resolves Pillow transpose constants from modern `Image.Transpose` namespace with fallback to legacy module-level constants.
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @return {dict[int, int]} Orientation-to-transpose mapping for values `2..8`.
- @satisfies REQ-077, REQ-078

### fn `def _apply_orientation_transform(pil_image_module, pil_image, source_orientation)` `priv` (L4081-4103)
- @brief Apply EXIF orientation transform to one image copy.
- @details Produces display-oriented pixels from source-oriented input while preserving the original image object and preserving orientation invariants in the main processing pipeline.
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @param pil_image {object} Pillow image-like object.
- @param source_orientation {int} EXIF orientation value in range `1..8`.
- @return {object} Transformed Pillow image object.
- @satisfies REQ-077, REQ-078

### fn `def _build_oriented_thumbnail_jpeg_bytes(` `priv` (L4104-4105)

### fn `def _coerce_exif_int_like_value(raw_value)` `priv` (L4136-4178)
- @brief Build refreshed JPEG thumbnail bytes from final quantized JPG pixels.
- @brief Coerce integer-like EXIF scalar values to Python integers.
- @details Creates a Pillow image from the final RGB uint8 array that is saved
as the output JPG, applies source-orientation-aware transform, scales to the
bounded thumbnail size, and serializes deterministic JPEG thumbnail payload
for EXIF embedding without re-reading the output file.
- @details Converts scalar EXIF values represented as `int`, integer-valued `float`, ASCII-digit `str`, or ASCII-digit `bytes` (including trailing null-terminated variants) into deterministic Python `int`; returns `None` when conversion is not safe.
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @param final_image_rgb_uint8 {numpy.ndarray} Final RGB uint8 array used for JPG save.
- @param source_orientation {int} EXIF orientation value in range `1..8`.
- @param raw_value {object} Candidate EXIF scalar value.
- @return {bytes} Serialized JPEG thumbnail payload.
- @return {int|None} Coerced integer value or `None` when not coercible.
- @satisfies REQ-041, REQ-078
- @satisfies REQ-066, REQ-077, REQ-078

### fn `def _normalize_ifd_integer_like_values_for_piexif_dump(piexif_module, exif_dict)` `priv` (L4179-4312)
- @brief Normalize integer-like IFD values before `piexif.dump`.
- @details Traverses EXIF IFD mappings (`0th`, `Exif`, `GPS`, `Interop`, `1st`) and coerces integer-like values that can trigger `piexif.dump` packing failures when represented as strings or other non-int scalars. Tuple/list values are normalized only when all items are integer-like. For integer sequence tag types, nested two-item pairs are flattened to a single integer sequence for `piexif.dump` compatibility. Scalar conversion is additionally constrained by `piexif.TAGS` integer field types when tag metadata is available.
- @param piexif_module {ModuleType} Imported piexif module.
- @param exif_dict {dict[str, object]} EXIF dictionary loaded via piexif.
- @return {None} Mutates `exif_dict` in place.
- @satisfies REQ-066, REQ-077, REQ-078

### fn `def _refresh_output_jpg_exif_thumbnail_after_save(` `priv` (L4313-4319)

### fn `def _set_output_file_timestamps(output_jpg, exif_timestamp)` `priv` (L4369-4383)
- @brief Refresh output JPG EXIF thumbnail while preserving source orientation.
- @brief Set output JPG atime and mtime from EXIF timestamp.
- @details Loads source EXIF payload, regenerates thumbnail from the final
quantized RGB uint8 image used for JPG save, preserves source orientation in
main EXIF IFD, sets thumbnail orientation to identity, and re-inserts updated
EXIF payload into output JPG before any filesystem timestamp synchronization.
- @details Applies EXIF-derived POSIX timestamp to both access and modification times using `os.utime`.
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @param piexif_module {ModuleType} Imported piexif module.
- @param output_jpg {Path} Final JPG path.
- @param final_image_rgb_uint8 {numpy.ndarray} Final RGB uint8 array used for JPG save.
- @param source_exif_payload {bytes} Serialized EXIF payload from source DNG.
- @param source_orientation {int} Source EXIF orientation value in range `1..8`.
- @param output_jpg {Path} Output JPG path.
- @param exif_timestamp {float} Source EXIF-derived POSIX timestamp.
- @return {None} Side effects only.
- @return {None} Side effects only.
- @exception RuntimeError Raised when EXIF thumbnail refresh fails.
- @exception OSError Raised when filesystem metadata update fails.
- @satisfies REQ-014, REQ-041, REQ-078
- @satisfies REQ-074, REQ-077

### fn `def _sync_output_file_timestamps_from_exif(output_jpg, exif_timestamp)` `priv` (L4384-4401)
- @brief Synchronize output JPG atime/mtime from optional EXIF timestamp.
- @details Provides one dedicated call site for filesystem timestamp sync and applies update only when EXIF datetime parsing produced a valid POSIX value after refreshed EXIF metadata has already been written to the output JPG.
- @param output_jpg {Path} Output JPG path.
- @param exif_timestamp {float|None} Source EXIF-derived POSIX timestamp.
- @return {None} Side effects only.
- @exception OSError Raised when filesystem metadata update fails.
- @satisfies REQ-014, REQ-074, REQ-077

### fn `def _build_exposure_multipliers(ev_value, ev_zero=0.0)` `priv` (L4402-4420)
- @brief Compute bracketing brightness multipliers from EV delta and center.
- @details Produces exactly three multipliers mapped to exposure stops `[ev_zero-ev, ev_zero, ev_zero+ev]` as powers of two for float-domain HDR base-image scaling.
- @param ev_value {float} Exposure bracket EV delta.
- @param ev_zero {float} Central bracket EV value.
- @return {tuple[float, float, float]} Multipliers in order `(under, base, over)`.
- @satisfies REQ-057, REQ-077, REQ-079, REQ-080, REQ-092, REQ-093, REQ-095, REQ-159

### fn `def _build_bracket_images_from_linear_base_float(np_module, base_rgb_float, multipliers)` `priv` (L4421-4449)
- @brief Build normalized HDR brackets from one linear RGB base tensor.
- @details Broadcast-multiplies one normalized linear RGB base tensor by the ordered EV multiplier triplet `(ev_minus, ev_zero, ev_plus)`, clamps each result into `[0,1]`, and returns float32 bracket tensors in canonical downstream order. Complexity: O(3*H*W). Side effects: none.
- @param np_module {ModuleType} Imported numpy module.
- @param base_rgb_float {object} Linear normalized RGB float tensor in `[0,1]`.
- @param multipliers {tuple[float, float, float]} Ordered EV multipliers.
- @return {list[object]} Ordered RGB float32 bracket tensors.
- @satisfies REQ-159, REQ-160

### fn `def _extract_bracket_images_float(` `priv` (L4450-4455)

### fn `def _order_bracket_paths(bracket_paths)` `priv` (L4491-4516)
- @brief Extract three normalized RGB float brackets from one RAW handle.
- @brief Validate and reorder bracket TIFF paths for deterministic backend argv.
- @details Ignores the parsed CLI gamma pair for HDR extraction, reuses an
optional precomputed normalized linear base tensor when available, otherwise
executes one deterministic linear camera-WB-aware RAW postprocess call, and
derives canonical bracket tensors by NumPy EV scaling and `[0,1]` clipping
without exposing TIFF artifacts outside this step. Complexity: O(H*W).
Side effects: at most one RAW postprocess invocation.
- @details Enforces exact exposure order `<ev_minus.tif> <ev_zero.tif> <ev_plus.tif>` required by backend command generation and raises on missing labels.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @param np_module {ModuleType} Imported numpy module.
- @param multipliers {tuple[float, float, float]} Ordered exposure multipliers.
- @param gamma_value {tuple[float, float]} Parsed CLI gamma pair retained for compatibility diagnostics only.
- @param base_rgb_float {object|None} Optional precomputed normalized linear RGB float base tensor.
- @param bracket_paths {list[Path]} Temporary bracket TIFF paths generated from RAW.
- @return {list[object]} Ordered RGB float bracket tensors.
- @return {list[Path]} Reordered bracket path list in deterministic exposure order.
- @exception ValueError Raised when any expected bracket label is missing.
- @satisfies REQ-010, REQ-157, REQ-158, REQ-159, REQ-160
- @satisfies REQ-062, REQ-112

### fn `def _order_hdr_plus_reference_paths(bracket_paths)` `priv` (L4517-4532)
- @brief Reorder bracket TIFF paths into HDR+ reference-first frame order.
- @details Converts canonical bracket order `(ev_minus, ev_zero, ev_plus)` to source-algorithm frame order `(ev_zero, ev_minus, ev_plus)` so the central bracket acts as temporal reference frame `n=0`, matching HDR+ temporal merge semantics while preserving existing bracket export filenames.
- @param bracket_paths {list[Path]} Temporary bracket TIFF paths generated from RAW.
- @return {list[Path]} Ordered bracket paths in HDR+ reference-first order.
- @satisfies REQ-112

### fn `def _run_luminance_hdr_cli(` `priv` (L4533-4540)

### fn `def _build_opencv_radiance_exposure_times(` `priv` (L4604-4607)
- @brief Merge bracket float images into one RGB float image via `luminance-hdr-cli`.
- @details Builds deterministic luminance-hdr-cli argv using EV sequence
centered around zero-reference (`-ev_value,0,+ev_value`) even when extraction
uses non-zero `ev_zero`, serializes float inputs to local 16-bit TIFFs,
forwards deterministic HDR/TMO arguments, isolates sidecar artifacts in a
backend-specific temporary directory, then reloads the produced TIFF as
normalized RGB float `[0,1]`.
- @param bracket_images_float {Sequence[object]} Ordered RGB float bracket tensors.
- @param temp_dir {Path} Temporary workspace root.
- @param imageio_module {ModuleType} Imported imageio module with `imread` and `imwrite`.
- @param np_module {ModuleType} Imported numpy module.
- @param ev_value {float} EV bracket delta used to generate exposure files.
- @param ev_zero {float} Central EV used to generate exposure files.
- @param luminance_options {LuminanceOptions} Luminance backend command controls.
- @return {object} Normalized RGB float merged image.
- @exception subprocess.CalledProcessError Raised when `luminance-hdr-cli` returns non-zero exit status.
- @satisfies REQ-011, REQ-060, REQ-061, REQ-067, REQ-068, REQ-095

### fn `def _build_ev_times_from_ev_zero_and_delta(ev_zero, ev_delta)` `priv` (L4641-4660)
- @brief Build deterministic unit-base exposure times array from EV center and EV delta.
- @details Delegates to the OpenCV radiance exposure-time helper using unit source exposure `1.0` second so tests and compatibility callers can verify deterministic stop-space mapping without EXIF metadata dependency.
- @param ev_zero {float} Central EV used during bracket extraction.
- @param ev_delta {float} EV bracket delta used during bracket extraction.
- @return {object} `numpy.float32` vector with length `3`.
- @exception RuntimeError Raised when numpy dependency is unavailable.
- @satisfies REQ-109, REQ-142

### fn `def _normalize_opencv_hdr_to_unit_range(np_module, hdr_rgb_float32)` `priv` (L4661-4684)
- @brief Normalize OpenCV HDR tensor to unit range with deterministic bounds.
- @details Normalizes arbitrary OpenCV HDR or fusion output to one congruent RGB float contract. Negative and non-finite values are cleared, values above unit range are scaled down by global maximum, and the final tensor is clamped into `[0,1]`.
- @param np_module {ModuleType} Imported numpy module.
- @param hdr_rgb_float32 {object} OpenCV HDR or fusion RGB tensor.
- @return {object} Normalized RGB float tensor clamped to `[0,1]`.
- @satisfies REQ-110, REQ-143, REQ-144

### fn `def _run_opencv_merge_mertens(cv2_module, np_module, exposures_float)` `priv` (L4685-4706)
- @brief Execute OpenCV Mertens exposure fusion path.
- @details Runs `cv2.createMergeMertens().process(...)` on normalized RGB float brackets, rescales the float result by `255` to match OpenCV exposure-fusion brightness semantics observed on `uint8` inputs, and then normalizes the result to the repository RGB float contract.
- @param cv2_module {ModuleType} Imported OpenCV module.
- @param np_module {ModuleType} Imported numpy module.
- @param exposures_float {list[object]} Ordered normalized RGB float bracket tensors.
- @return {object} Normalized RGB float tensor.
- @satisfies REQ-108, REQ-110, REQ-144, REQ-154

### fn `def _estimate_opencv_camera_response(` `priv` (L4707-4711)

### fn `def _run_opencv_merge_radiance(` `priv` (L4740-4747)
- @brief Estimate OpenCV inverse camera response for Debevec or Robertson radiance merge.
- @details Selects the OpenCV calibrator matching the requested radiance merge
algorithm and computes one inverse camera response tensor from backend-local
`uint8` bracket views derived from the shared linear float contract by the
caller. This preserves the repository-wide RGB float `[0,1]` interface
while satisfying the OpenCV radiance path requirement for `CV_8U`
calibrator inputs. Time complexity: `O(n*p)` where `n` is bracket count and
`p` is pixels per bracket. Side effects: none.
- @param cv2_module {ModuleType} Imported OpenCV module.
- @param exposures_radiance_uint8 {list[object]} Ordered backend-local RGB `uint8` bracket tensors.
- @param exposure_times {object} OpenCV exposure-time vector.
- @param merge_algorithm {str} Canonical OpenCV merge algorithm token.
- @return {object} OpenCV response tensor compatible with Debevec/Robertson merge calls.
- @exception RuntimeError Raised when `merge_algorithm` is unsupported.
- @satisfies REQ-153, REQ-162

### fn `def _normalize_debevec_hdr_to_unit_range(np_module, hdr_rgb_float32, white_point_percentile)` `priv` (L4811-4830)
- @brief Execute OpenCV radiance HDR path for Debevec or Robertson.
- @brief Preserve legacy Debevec normalization helper contract.
- @details Follows the OpenCV tutorial flow by estimating inverse camera
response with the matching `CalibrateDebevec` or `CalibrateRobertson`
implementation before `MergeDebevec` or `MergeRobertson`. OpenCV requires
the radiance path to consume backend-local `uint8` bracket payloads when
calibrated `response` is supplied, so this helper quantizes the shared
linear float brackets only inside the backend step, preserving float
repository interfaces at entry and exit. Then it applies simple OpenCV
gamma tone mapping when enabled; otherwise normalizes the radiance map
directly to the repository RGB float contract. Time complexity: `O(n*p)`.
Side effects: none.
- @details Keeps the historical helper name as one compatibility adapter for tests and references while delegating to the unified OpenCV normalization contract used by Debevec, Robertson, and Mertens outputs.
- @param cv2_module {ModuleType} Imported OpenCV module.
- @param np_module {ModuleType} Imported numpy module.
- @param exposures_linear_float {list[object]} Ordered linear RGB float bracket tensors.
- @param exposure_times {object} OpenCV exposure-time vector.
- @param merge_algorithm {str} Canonical OpenCV merge algorithm token.
- @param tonemap_enabled {bool} `True` enables simple OpenCV tone mapping.
- @param tonemap_gamma {float} Positive gamma passed to `createTonemap`.
- @param np_module {ModuleType} Imported numpy module.
- @param hdr_rgb_float32 {object} OpenCV HDR RGB tensor.
- @param white_point_percentile {float} Unused legacy parameter retained for compatibility.
- @return {object} Normalized RGB float tensor.
- @return {object} Normalized RGB float tensor clamped to `[0,1]`.
- @exception RuntimeError Raised when `merge_algorithm` is unsupported.
- @satisfies REQ-108, REQ-109, REQ-110, REQ-143, REQ-144, REQ-152, REQ-153, REQ-162
- @satisfies REQ-144

### fn `def _run_opencv_hdr_merge(` `priv` (L4831-4838)

### fn `def _hdrplus_box_down2_float32(np_module, frames_float32)` `priv` (L4901-4929)
- @brief Merge bracket float images into one RGB float image via OpenCV.
- @brief Downsample HDR+ scalar frames with 2x2 box averaging in float domain.
- @details Accepts three normalized RGB float bracket tensors ordered as
`(ev_minus, ev_zero, ev_plus)`, derives OpenCV radiance exposure times in
seconds from EXIF `ExposureTime` for Debevec/Robertson or dispatches
Mertens directly, and returns one congruent normalized RGB float image.
Debevec and Robertson consume the shared linear HDR bracket contract
directly with calibrated inverse response, while Mertens consumes the same
normalized float brackets and compensates OpenCV float-path scaling.
- @details Ports `box_down2` from `util.cpp` for repository HDR+ execution by reflect-padding odd image sizes to even extents, summing each 2x2 region, and multiplying by `0.25` once. Input and output stay in float domain to preserve the repository-wide HDR+ internal arithmetic contract.
- @param bracket_images_float {Sequence[object]} Ordered RGB float bracket tensors.
- @param ev_value {float} EV bracket delta used to generate exposure files.
- @param ev_zero {float} Central EV used to generate exposure files.
- @param source_exposure_time_seconds {float|None} Positive EXIF `ExposureTime` in seconds for the extracted linear base image.
- @param gamma_value {tuple[float, float]} Parsed CLI gamma pair retained for compatibility with existing call sites.
- @param opencv_merge_options {OpenCvMergeOptions} OpenCV merge backend controls.
- @param auto_adjust_dependencies {tuple[ModuleType, ModuleType]|None} Optional `(cv2, numpy)` dependency tuple.
- @param np_module {ModuleType} Imported numpy module.
- @param frames_float32 {object} Scalar float tensor with shape `(N,H,W)`.
- @return {object} Normalized RGB float merged image.
- @return {object} Downsampled float tensor with shape `(N,ceil(H/2),ceil(W/2))`.
- @exception RuntimeError Raised when OpenCV/numpy dependencies are missing or bracket payloads are invalid.
- @satisfies REQ-107, REQ-108, REQ-109, REQ-110, REQ-142, REQ-143, REQ-144, REQ-152, REQ-153, REQ-154, REQ-160, REQ-161, REQ-162
- @satisfies REQ-112, REQ-113, REQ-129

### fn `def _hdrplus_gauss_down4_float32(np_module, frames_float32)` `priv` (L4930-4976)
- @brief Downsample HDR+ scalar frames by `4` with the source 5x5 Gaussian kernel.
- @details Ports `gauss_down4` from `util.cpp`: applies the integer kernel with coefficients summing to `159`, uses reflect padding to emulate `mirror_interior`, then samples every fourth pixel in both axes. Input and output remain float to keep HDR+ alignment math in floating point.
- @param np_module {ModuleType} Imported numpy module.
- @param frames_float32 {object} Scalar float tensor with shape `(N,H,W)`.
- @return {object} Downsampled float tensor with shape `(N,ceil(H/4),ceil(W/4))`.
- @satisfies REQ-112, REQ-113, REQ-129

### fn `def _hdrplus_build_scalar_proxy_float32(np_module, frames_rgb_float32, hdrplus_options)` `priv` (L4977-5010)
- @brief Convert RGB bracket tensors into the scalar HDR+ source-domain proxy.
- @details Adapts normalized RGB float32 brackets to the original single-channel HDR+ merge domain without any uint16 staging. Mode `rggb` approximates Bayer energy with weights `(0.25, 0.5, 0.25)`; mode `bt709` uses luminance weights `(0.2126, 0.7152, 0.0722)`; mode `mean` uses arithmetic RGB average. Output remains normalized float32 to preserve downstream alignment and merge precision.
- @param np_module {ModuleType} Imported numpy module.
- @param frames_rgb_float32 {object} Normalized RGB float32 frame tensor with shape `(N,H,W,3)`.
- @param hdrplus_options {HdrPlusOptions} HDR+ proxy/alignment/temporal controls.
- @return {object} Normalized scalar float32 tensor with shape `(N,H,W)`.
- @satisfies REQ-112, REQ-126, REQ-128, REQ-129, REQ-140

### fn `def _hdrplus_compute_tile_start_positions(np_module, axis_length, tile_stride, pad_margin)` `priv` (L5011-5031)
- @brief Compute HDR+ tile start coordinates for one image axis.
- @details Reproduces the source overlap geometry used by the Python HDR+ port: tile starts advance by `tile_stride` and include the leading virtual tile at `-tile_stride`, represented by positive indices inside the padded tensor.
- @param np_module {ModuleType} Imported numpy module.
- @param axis_length {int} Source image extent for the selected axis.
- @param tile_stride {int} Tile stride in pixels.
- @param pad_margin {int} Reflect padding added on both sides of the axis.
- @return {object} `int32` axis start-position vector with shape `(T,)`.
- @satisfies REQ-112, REQ-115

### fn `def _hdrplus_trunc_divide_int32(np_module, values_int32, divisor)` `priv` (L5032-5050)
- @brief Divide signed HDR+ offsets with truncation toward zero.
- @details Emulates C++ integer division semantics used by the source code for negative offsets, which differs from Python floor division. This helper is required for the source-consistent `offset / 2` conversion between full and downsampled tile domains.
- @param np_module {ModuleType} Imported numpy module.
- @param values_int32 {object} Signed integer tensor.
- @param divisor {int} Positive divisor.
- @return {object} Signed integer tensor truncated toward zero.
- @satisfies REQ-113, REQ-114

### fn `def _hdrplus_compute_alignment_bounds(search_radius)` `priv` (L5051-5075)
- @brief Derive source-equivalent hierarchical HDR+ alignment bounds.
- @details Reconstructs the source `min_3/min_2/min_1` and `max_3/max_2/max_1` recurrences for the fixed three-level pyramid and search offsets `[-search_radius, search_radius-1]`.
- @param search_radius {int} Per-layer alignment search radius.
- @return {tuple[tuple[int, int], ...]} Bound pairs in coarse-to-fine order.
- @satisfies REQ-113

### fn `def _hdrplus_compute_alignment_margin(search_radius, divisor=1)` `priv` (L5076-5094)
- @brief Compute safe reflect-padding margin for HDR+ alignment offsets.
- @details Converts the fixed three-level search radius into a conservative full-resolution offset bound and optionally scales it down for lower pyramid levels via truncation-toward-zero division.
- @param search_radius {int} Per-layer alignment search radius.
- @param divisor {int} Positive scale divisor applied to the full-resolution bound.
- @return {int} Non-negative padding margin in pixels.
- @satisfies REQ-113

### fn `def _hdrplus_extract_overlapping_tiles(` `priv` (L5095-5100)

### fn `def _hdrplus_extract_aligned_tiles(` `priv` (L5153-5159)

### fn `def _hdrplus_align_layer(` `priv` (L5232-5239)
- @brief Extract HDR+ tiles after applying per-tile alignment offsets.
- @details Builds tile coordinate grids from the padded frame tensor, adds the
per-tile `(x,y)` offsets resolved by hierarchical alignment, and gathers the
aligned scalar or RGB tiles needed by temporal distance evaluation and
temporal accumulation.
- @param np_module {ModuleType} Imported numpy module.
- @param frames_array {object} Frame tensor with shape `(N,H,W)` or `(N,H,W,C)`.
- @param tile_size {int} Square tile edge length.
- @param tile_stride {int} Tile stride between adjacent overlapping tiles.
- @param pad_margin {int} Reflect padding added on each image edge.
- @param alignment_offsets {object} Signed integer offset tensor with shape `(N,Ty,Tx,2)`.
- @return {object} Aligned tile tensor with shape `(N,Ty,Tx,tile_size,tile_size[,C])`.
- @satisfies REQ-113, REQ-114

### fn `def _hdrplus_align_layers(np_module, scalar_frames, hdrplus_options)` `priv` (L5329-5416)
- @brief Resolve one HDR+ alignment layer for one alternate frame.
- @brief Resolve hierarchical HDR+ tile alignment for all alternate frames.
- @details Ports `align_layer` from `align.cpp`: propagates the coarser
alignment estimate via `prev_tile`, scales it by the fixed downsample rate
`4`, evaluates all candidate offsets in `[-search_radius, search_radius-1]`
using per-tile L1 distance over `16x16` tiles, and returns the minimizing
offset for each tile.
- @details Ports `align.cpp` at the algorithm level: builds the source alignment pyramid `box_down2 -> gauss_down4 -> gauss_down4`, computes coarse-to-fine tile alignments for each alternate frame against reference frame `n=0`, and lifts the finest layer offsets back to full-resolution coordinates by factor `2`.
- @param np_module {ModuleType} Imported numpy module.
- @param reference_layer {object} Reference scalar layer with shape `(H,W)`.
- @param alternate_layer {object} Alternate scalar layer with shape `(H,W)`.
- @param prev_alignment {object} Previous-layer alignment tensor with shape `(Ty,Tx,2)`.
- @param prev_min {int} Minimum previous-layer offset bound used before upscaling.
- @param prev_max {int} Maximum previous-layer offset bound used before upscaling.
- @param search_radius {int} Per-layer alignment search radius.
- @param np_module {ModuleType} Imported numpy module.
- @param scalar_frames {object} Normalized scalar float32 tensor with shape `(N,H,W)`.
- @param hdrplus_options {HdrPlusOptions} HDR+ proxy/alignment/temporal controls.
- @return {object} Signed integer alignment tensor with shape `(Ty,Tx,2)`.
- @return {object} Full-resolution `int32` alignment tensor with shape `(N,Ty,Tx,2)`.
- @satisfies REQ-112, REQ-113, REQ-129
- @satisfies REQ-112, REQ-113, REQ-128, REQ-129, REQ-139

### fn `def _hdrplus_resolve_temporal_runtime_options(hdrplus_options)` `priv` (L5417-5441)
- @brief Remap HDR+ temporal CLI knobs for normalized float32 distance inputs.
- @details Converts user-facing temporal controls defined on the historical 16-bit code-domain into runtime controls consumed by normalized float32 `[0,1]` tile distances. The factor and floor are scaled by `1/65535` through pure linear rescaling; the cutoff remains expressed in the post-normalized comparison space so the current inverse-distance weight curve remains numerically equivalent while diagnostics still print the original CLI values.
- @param hdrplus_options {HdrPlusOptions} User-facing HDR+ proxy/alignment/temporal controls.
- @return {HdrPlusTemporalRuntimeOptions} Normalized runtime temporal controls.
- @satisfies REQ-114, REQ-131, REQ-138

### fn `def _hdrplus_compute_temporal_weights(` `priv` (L5442-5446)

### fn `def _hdrplus_merge_temporal_rgb(` `priv` (L5527-5533)
- @brief Compute HDR+ temporal tile weights against the aligned reference frame.
- @details Ports `merge_temporal` from `merge.cpp`: extracts reference tiles
from the downsampled scalar layer, applies resolved per-tile alignment
offsets to alternate frames in the same layer domain, computes average tile
L1 distance on normalized float32 inputs, remaps user-facing temporal knobs
into normalized runtime controls, derives inverse-distance weights without
extra radiometric renormalization, and adds the implicit reference weight
`1.0`.
- @param np_module {ModuleType} Imported numpy module.
- @param downsampled_scalar_frames {object} Downsampled normalized scalar float32 tensor with shape `(N,H,W)`.
- @param alignment_offsets {object} Full-resolution `int32` alignment tensor with shape `(N,Ty,Tx,2)`.
- @param hdrplus_options {HdrPlusOptions} HDR+ proxy/alignment/temporal controls.
- @return {tuple[object, object]} `(weights, total_weight)` where `weights` has shape `(N-1,Ty,Tx)` and `total_weight` has shape `(Ty,Tx)`.
- @satisfies REQ-112, REQ-114, REQ-128, REQ-129, REQ-138

### fn `def _hdrplus_merge_spatial_rgb(np_module, temporal_tiles, width, height)` `priv` (L5582-5654)
- @brief Merge HDR+ full-resolution RGB tiles across the temporal dimension.
- @brief Blend HDR+ temporally merged tiles with raised-cosine overlap.
- @details Ports the temporal accumulation phase of `merge.cpp`: extracts the
reference `32x32` tile stack, applies resolved full-resolution alignment
offsets to alternate RGB frames, normalizes all contributions with the
shared per-tile `total_weight`, and preserves float arithmetic until the
spatial merge stage.
- @details Ports `merge_spatial` from `merge.cpp`: builds source raised-cosine weights over `32` samples, gathers four overlapping tiles for each output pixel using source index formulas derived from `tile_0`, `tile_1`, `idx_0`, and `idx_1`, then computes one weighted RGB sum and returns the continuous normalized float32 result without a final quantized lattice projection.
- @param np_module {ModuleType} Imported numpy module.
- @param frames_rgb_float32 {object} Normalized RGB float32 tensor with shape `(N,H,W,3)`.
- @param alignment_offsets {object} Full-resolution `int32` alignment tensor with shape `(N,Ty,Tx,2)`.
- @param weights {object} Alternate-frame weight tensor with shape `(N-1,Ty,Tx)`.
- @param total_weight {object} Reference-inclusive tile total weights with shape `(Ty,Tx)`.
- @param hdrplus_options {HdrPlusOptions} HDR+ proxy/alignment/temporal controls.
- @param np_module {ModuleType} Imported numpy module.
- @param temporal_tiles {object} Temporally merged normalized RGB float32 tile tensor with shape `(Ty,Tx,32,32,3)`.
- @param width {int} Output image width.
- @param height {int} Output image height.
- @return {object} Temporally merged normalized RGB float32 tile tensor with shape `(Ty,Tx,32,32,3)`.
- @return {object} Normalized RGB float32 merged image tensor with shape `(H,W,3)`.
- @satisfies REQ-112, REQ-114, REQ-129, REQ-140
- @satisfies REQ-112, REQ-115, REQ-129, REQ-140

### fn `def _run_hdr_plus_merge(` `priv` (L5655-5658)

### fn `def _convert_compression_to_quality(jpg_compression)` `priv` (L5735-5745)
- @brief Merge bracket float images into one RGB float image via HDR+.
- @brief Convert JPEG compression level to Pillow quality value.
- @details Ports the source HDR+ merge pipeline from `align.cpp`, `merge.cpp`,
and `util.cpp` onto repository RGB float brackets: reorders inputs into
reference-first frame order `(ev_zero, ev_minus, ev_plus)`, normalizes each
bracket to RGB float32 `[0,1]`, executes scalar proxy generation,
hierarchical alignment, source `box_down2`, temporal weighting, temporal
RGB merge, raised-cosine spatial blending, and returns one normalized RGB
float32 image without any HDR+-local uint16 conversion.
- @details Maps inclusive compression range `[0, 100]` to inclusive quality range `[100, 1]` preserving deterministic inverse relation.
- @param bracket_images_float {Sequence[object]} Ordered RGB float bracket tensors.
- @param np_module {ModuleType} Imported numpy module.
- @param hdrplus_options {HdrPlusOptions} HDR+ proxy/alignment/temporal controls.
- @param jpg_compression {int} JPEG compression level.
- @return {object} Normalized RGB float32 merged image.
- @return {int} Pillow quality value in `[1, 100]`.
- @exception RuntimeError Raised when bracket payloads are invalid.
- @satisfies REQ-111, REQ-112, REQ-113, REQ-114, REQ-115, REQ-126, REQ-129, REQ-138, REQ-139, REQ-140
- @satisfies REQ-065, REQ-066

### fn `def _collect_missing_external_executables(` `priv` (L5746-5748)

### fn `def _resolve_auto_adjust_dependencies()` `priv` (L5767-5792)
- @brief Collect missing external executables required by resolved runtime options.
- @brief Resolve OpenCV and numpy runtime dependencies for image-domain stages.
- @details Evaluates the selected backend to derive the exact external
executable set needed by this invocation, then probes each command on
`PATH` and returns a deterministic missing-command tuple for preflight
failure reporting before processing starts.
- @details Imports `cv2` and `numpy` modules required by the auto-adjust pipeline, the OpenCV HDR backend, and the automatic EV-zero evaluation, and returns `None` with deterministic error output when dependencies are missing.
- @param enable_luminance {bool} `True` when luminance backend is selected.
- @return {tuple[str, ...]} Ordered tuple of missing executable labels.
- @return {tuple[ModuleType, ModuleType]|None} `(cv2_module, numpy_module)` when available; `None` on dependency failure.
- @satisfies CTN-005
- @satisfies REQ-037, REQ-059, REQ-073, REQ-075

### fn `def _resolve_numpy_dependency()` `priv` (L5793-5812)
- @brief Resolve numpy runtime dependency for float-interface image stages.
- @details Imports `numpy` required by bracket float normalization, in-memory merge orchestration, float-domain post-merge stages, and TIFF16 adaptation helpers, and returns `None` with deterministic error output when the dependency is missing.
- @return {ModuleType|None} Imported numpy module; `None` on dependency failure.
- @satisfies REQ-010, REQ-012, REQ-059, REQ-100

### fn `def _to_float32_image_array(np_module, image_data)` `priv` (L5813-5844)
- @brief Convert image tensor to normalized `float32` range `[0,1]`.
- @details Normalizes integer or float image payloads into RGB-stage `float32` tensors. `uint16` uses `/65535`, `uint8` uses `/255`, floating inputs outside `[0,1]` are interpreted on the closest integer image scale (`255` or `65535`) and then clamped.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image tensor.
- @return {object} Normalized `float32` image tensor.
- @satisfies REQ-010, REQ-012, REQ-106

### fn `def _normalize_float_rgb_image(np_module, image_data)` `priv` (L5845-5872)
- @brief Normalize image payload into RGB `float32` tensor.
- @details Converts input image payload to normalized `float32`, expands grayscale to one channel, replicates single-channel input to RGB, drops alpha from RGBA input, and returns exactly three channels for deterministic float-stage processing.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image tensor.
- @return {object} RGB `float32` tensor with shape `(H,W,3)` and range `[0,1]`.
- @exception ValueError Raised when normalized image has unsupported shape.
- @satisfies REQ-010, REQ-012, REQ-106

### fn `def _write_rgb_float_tiff16(imageio_module, np_module, output_path, image_rgb_float)` `priv` (L5873-5896)
- @brief Serialize one RGB float tensor as 16-bit TIFF payload.
- @details Normalizes the source image to RGB float `[0,1]`, converts it to `uint16`, and writes the result through `imageio`. This helper localizes float-to-TIFF16 adaptation inside steps that depend on file-based tools.
- @param imageio_module {ModuleType} Imported imageio module with `imwrite`.
- @param np_module {ModuleType} Imported numpy module.
- @param output_path {Path} Output TIFF path.
- @param image_rgb_float {object} RGB float tensor in `[0,1]`.
- @return {None} Side effects only.
- @satisfies REQ-011, REQ-106

### fn `def _write_debug_rgb_float_tiff(` `priv` (L5897-5902)

### fn `def _build_debug_artifact_context(output_jpg, input_dng, postprocess_options)` `priv` (L5932-5952)
- @brief Persist one debug checkpoint TIFF from normalized RGB float data.
- @brief Build persistent debug output metadata for one command invocation.
- @details Serializes one normalized RGB float `[0,1]` tensor into TIFF16
using the persistent debug output directory and canonical filename pattern
`<input-stem><stage-suffix>.tiff`. The helper keeps checkpoint files outside
the temporary workspace lifecycle so they survive command completion.
- @details Returns `None` when debug mode is disabled. When enabled, the helper derives the output directory from the final JPG destination and uses the source DNG stem as the canonical debug filename prefix.
- @param imageio_module {ModuleType} Imported imageio module with `imwrite`.
- @param np_module {ModuleType} Imported numpy module.
- @param debug_context {DebugArtifactContext|None} Persistent debug output metadata; `None` disables emission.
- @param stage_suffix {str} Progressive stage suffix such as `_2.0_hdr-merge`.
- @param image_rgb_float {object} RGB float tensor on normalized `[0,1]` scale.
- @param output_jpg {Path} Final JPG destination path.
- @param input_dng {Path} Source DNG input path.
- @param postprocess_options {PostprocessOptions} Parsed postprocess controls including debug flag.
- @return {Path|None} Written TIFF path; `None` when debug output is disabled.
- @return {DebugArtifactContext|None} Persistent debug output metadata or `None` when debug mode is disabled.
- @satisfies DES-009, REQ-147, REQ-149
- @satisfies REQ-146, REQ-147, REQ-149

### fn `def _format_debug_ev_suffix_value(ev_value)` `priv` (L5953-5970)
- @brief Format one EV value token for debug checkpoint filenames.
- @details Emits a signed decimal representation that preserves quarter-step EV precision while keeping integer-valued stops on one decimal place for stable filenames such as `+1.0`, `+0.5`, or `-0.25`.
- @param ev_value {float} EV value expressed in stop units.
- @return {str} Signed decimal token for debug filename suffixes.
- @satisfies REQ-147, REQ-148

### fn `def _materialize_bracket_tiffs_from_float(` `priv` (L5971-5975)

### fn `def _to_uint8_image_array(np_module, image_data)` `priv` (L6005-6051)
- @brief Write canonical bracket TIFF files from RGB float images.
- @brief Convert image tensor to `uint8` range `[0,255]`.
- @details Emits `ev_minus.tif`, `ev_zero.tif`, and `ev_plus.tif` into the
provided temporary directory using 16-bit TIFF encoding derived from
normalized RGB float images. The helper is used only by file-oriented merge
backends.
- @details Normalizes integer or float image payloads into `uint8` preserving relative brightness scale: `uint16` uses `/257`, normalized float arrays in `[0,1]` use `*255`, and all paths clamp to inclusive byte range.
- @param imageio_module {ModuleType} Imported imageio module with `imwrite`.
- @param np_module {ModuleType} Imported numpy module.
- @param bracket_images_float {Sequence[object]} Ordered RGB float bracket tensors.
- @param temp_dir {Path} Temporary directory for TIFF artifacts.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image tensor.
- @return {list[Path]} Ordered canonical TIFF paths.
- @return {object} `uint8` image tensor.
- @satisfies REQ-011, REQ-034
- @satisfies REQ-066, REQ-090

### fn `def _to_uint16_image_array(np_module, image_data)` `priv` (L6052-6096)
- @brief Convert image tensor to `uint16` range `[0,65535]`.
- @details Normalizes integer or float image payloads into `uint16` preserving relative brightness scale: `uint8` uses `*257`, normalized float arrays in `[0,1]` use `*65535`, and all paths clamp to inclusive 16-bit range.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image tensor.
- @return {object} `uint16` image tensor.
- @satisfies REQ-066, REQ-090

### fn `def _apply_post_gamma_float(np_module, image_rgb_float, gamma_value)` `priv` (L6097-6122)
- @brief Apply static post-gamma over RGB float tensor.
- @details Executes the legacy static gamma equation on normalized RGB float data (`output = input^(1/gamma)`), preserves the original stage-local clipping semantics, and removes the previous uint16 LUT adaptation layer.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float image tensor.
- @param gamma_value {float} Static post-gamma factor.
- @return {object} RGB float tensor after gamma stage.
- @satisfies REQ-012, REQ-013, REQ-132, REQ-134

### fn `def _apply_brightness_float(np_module, image_rgb_float, brightness_factor)` `priv` (L6123-6145)
- @brief Apply static brightness factor on RGB float tensor.
- @details Executes the legacy brightness equation on normalized RGB float data (`output = factor * input`), preserves per-stage clipping semantics, and removes the prior uint16 round-trip.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float image tensor.
- @param brightness_factor {float} Brightness scale factor.
- @return {object} RGB float tensor after brightness stage.
- @satisfies REQ-012, REQ-013, REQ-132, REQ-134

### fn `def _apply_contrast_float(np_module, image_rgb_float, contrast_factor)` `priv` (L6146-6170)
- @brief Apply static contrast factor on RGB float tensor.
- @details Executes the legacy contrast equation on normalized RGB float data (`output = mean + factor * (input - mean)`), where `mean` remains the per-channel global image average, then applies stage-local clipping.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float image tensor.
- @param contrast_factor {float} Contrast interpolation factor.
- @return {object} RGB float tensor after contrast stage.
- @satisfies REQ-012, REQ-013, REQ-132, REQ-134

### fn `def _apply_saturation_float(np_module, image_rgb_float, saturation_factor)` `priv` (L6171-6200)
- @brief Apply static saturation factor on RGB float tensor.
- @details Executes the legacy saturation equation on normalized RGB float data using BT.709 grayscale (`output = gray + factor * (input - gray)`), then applies stage-local clipping without quantized intermediates.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float image tensor.
- @param saturation_factor {float} Saturation interpolation factor.
- @return {object} RGB float tensor after saturation stage.
- @satisfies REQ-012, REQ-013, REQ-132, REQ-134

### fn `def _apply_static_postprocess_float(` `priv` (L6201-6206)

### fn `def _to_linear_srgb(np_module, image_srgb)` `priv` (L6283-6300)
- @brief Execute static postprocess chain with float-only stage internals.
- @brief Convert sRGB tensor to linear-sRGB tensor.
- @details Accepts one normalized RGB float tensor, preserves the legacy
gamma/brightness/contrast/saturation equations and stage order, executes
all intermediate calculations in float domain, optionally emits persistent
debug TIFF checkpoints after each static substage, and eliminates the prior
float->uint16->float adaptation cycle from this step.
- @details Applies IEC 61966-2-1 piecewise inverse transfer function on normalized channel values in `[0,1]`.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float tensor.
- @param postprocess_options {PostprocessOptions} Parsed postprocess controls.
- @param imageio_module {ModuleType|None} Optional imageio module used for debug TIFF checkpoint emission.
- @param debug_context {DebugArtifactContext|None} Optional persistent debug output metadata.
- @param np_module {ModuleType} Imported numpy module.
- @param image_srgb {object} Float image tensor in sRGB domain `[0,1]`.
- @return {object} RGB float tensor after static postprocess chain.
- @return {object} Float image tensor in linear-sRGB domain `[0,1]`.
- @satisfies REQ-012, REQ-013, REQ-132, REQ-134, REQ-148
- @satisfies REQ-090, REQ-099

### fn `def _from_linear_srgb(np_module, image_linear)` `priv` (L6301-6318)
- @brief Convert linear-sRGB tensor to sRGB tensor.
- @details Applies IEC 61966-2-1 piecewise forward transfer function on normalized linear channel values in `[0,1]`.
- @param np_module {ModuleType} Imported numpy module.
- @param image_linear {object} Float image tensor in linear-sRGB domain `[0,1]`.
- @return {object} Float image tensor in sRGB domain `[0,1]`.
- @satisfies REQ-090, REQ-099

### fn `def _compute_bt709_luminance(np_module, linear_rgb)` `priv` (L6319-6336)
- @brief Compute BT.709 linear luminance from linear RGB tensor.
- @details Computes per-pixel luminance using BT.709 coefficients with RGB channel order: `0.2126*R + 0.7152*G + 0.0722*B`.
- @param np_module {ModuleType} Imported numpy module.
- @param linear_rgb {object} Linear-sRGB float tensor with shape `H,W,3`.
- @return {object} Float luminance tensor with shape `H,W`.
- @satisfies REQ-090, REQ-099

### fn `def _analyze_luminance_key(np_module, luminance, eps)` `priv` (L6337-6376)
- @brief Analyze luminance distribution and classify scene key.
- @details Computes log-average luminance, median, percentile tails, and clip proxies on normalized BT.709 luminance and classifies scene as `low-key`, `normal-key`, or `high-key` using the thresholds from `/tmp/auto-brightness.py`.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance {object} BT.709 luminance float tensor in `[0, 1]`.
- @param eps {float} Positive numerical stability guard.
- @return {dict[str, float|str]} Key analysis dictionary with key type, central statistics, tails, and clipping proxies.
- @satisfies REQ-050, REQ-103, REQ-121

### fn `def _choose_auto_key_value(key_analysis, auto_brightness_options)` `priv` (L6377-6422)
- @brief Select Reinhard key value from key-analysis metrics.
- @details Chooses base key by scene class (`0.09/0.18/0.36`) and applies conservative under/over-exposure adaptation bounded by configured automatic key limits and automatic boost factor.
- @param key_analysis {dict[str, float|str]} Luminance key-analysis dictionary.
- @param auto_brightness_options {AutoBrightnessOptions} Parsed auto-brightness parameters.
- @return {float} Clamped key value `a`.
- @satisfies REQ-050, REQ-103, REQ-122

### fn `def _reinhard_global_tonemap_luminance(` `priv` (L6423-6428)

### fn `def _luminance_preserving_desaturate_to_fit(np_module, rgb_linear, luminance, eps)` `priv` (L6462-6489)
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

### fn `def _apply_mild_local_contrast_bgr_uint16(cv2_module, np_module, image_bgr_uint16, options)` `priv` (L6490-6528)
- @brief Apply legacy uint16 CLAHE micro-contrast on 16-bit Y channel.
- @details Converts BGR16 to YCrCb, runs CLAHE on 16-bit Y with configured clip/tile controls, then blends original and CLAHE outputs using configured local-contrast strength. Retained as quantized reference implementation for float-domain CLAHE-luma equivalence verification.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param image_bgr_uint16 {object} BGR uint16 image tensor.
- @param options {AutoAdjustOptions} Parsed auto-adjust CLAHE options.
- @return {object} BGR uint16 image tensor after optional local contrast.
- @satisfies REQ-125, REQ-137

### fn `def _quantize_clahe_luminance_bins(np_module, luminance_values, histogram_size)` `priv` (L6529-6554)
- @brief Map normalized luminance samples onto CLAHE histogram addresses.
- @details Computes OpenCV-compatible histogram bin addresses from normalized float luminance without materializing an intermediate uint16 image plane. Rounds against the `[0, hist_size-1]` lattice preserved by the historical uint16 reference so tile histograms remain semantically aligned while the active path stays in float-domain image buffers.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_values {object} Normalized luminance tensor in `[0,1]`.
- @param histogram_size {int} Number of CLAHE histogram bins.
- @return {object} `int32` tensor of histogram bin addresses.
- @satisfies REQ-136, REQ-137

### fn `def _build_clahe_float_tile_histogram(np_module, luminance_tile, histogram_size)` `priv` (L6555-6576)
- @brief Build one CLAHE histogram from a float luminance tile.
- @details Converts one normalized luminance tile into one dense histogram using the preserved 16-bit CLAHE lattice and returns per-bin population counts for downstream clipping and CDF generation.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_tile {object} Tile luminance tensor in `[0,1]`.
- @param histogram_size {int} Number of CLAHE histogram bins.
- @return {object} Dense histogram tensor with one count per CLAHE bin.
- @satisfies REQ-136, REQ-137

### fn `def _clip_clahe_histogram(np_module, histogram, clip_limit, tile_population)` `priv` (L6577-6624)
- @brief Clip one CLAHE histogram with OpenCV-compatible redistribution.
- @details Normalizes the user clip limit by tile population and histogram size, applies the same integer clip ceiling used by OpenCV CLAHE, then redistributes clipped mass through uniform batch fill plus residual stride increments. Output preserves the original total tile population.
- @param np_module {ModuleType} Imported numpy module.
- @param histogram {object} Dense tile histogram tensor.
- @param clip_limit {float} User-provided CLAHE clip limit.
- @param tile_population {int} Number of pixels contained in the tile.
- @return {object} Clipped histogram tensor after redistributed excess mass.
- @satisfies REQ-136, REQ-137

### fn `def _build_clahe_float_lut(np_module, histogram, tile_population)` `priv` (L6625-6644)
- @brief Convert one clipped CLAHE histogram into one normalized LUT.
- @details Builds one cumulative distribution from the clipped histogram and normalizes it by tile population so the resulting lookup table maps each histogram address directly into one float luminance output in `[0,1]`. Uses `float32` storage to limit per-tile memory while preserving normalized luminance precision required by the active float pipeline.
- @param np_module {ModuleType} Imported numpy module.
- @param histogram {object} Clipped histogram tensor.
- @param tile_population {int} Number of pixels contained in the tile.
- @return {object} Normalized CLAHE lookup-table tensor in `[0,1]`.
- @satisfies REQ-136, REQ-137

### fn `def _pad_clahe_luminance_float(np_module, luminance_float, tile_grid_size)` `priv` (L6645-6683)
- @brief Pad luminance plane to an even CLAHE tile lattice.
- @details Reproduces OpenCV CLAHE tiling rules by extending only the bottom and right borders to the next multiple of the configured tile grid. Uses reflect-101 semantics when the axis length is greater than one and edge replication for single-pixel axes where reflection is undefined.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Luminance tensor in `[0,1]`.
- @param tile_grid_size {tuple[int, int]} OpenCV-compatible tile-grid tuple.
- @return {tuple[object, int, int]} Padded luminance tensor, tile height, and tile width.
- @satisfies REQ-136, REQ-137

### fn `def _build_clahe_axis_interpolation(np_module, axis_length, tile_size, tile_count)` `priv` (L6684-6711)
- @brief Precompute CLAHE neighbor indices and bilinear weights per axis.
- @details Recreates OpenCV CLAHE interpolation coordinates by locating each sample relative to adjacent tile centers using `coord / tile_size - 0.5`. Returned weights remain unchanged after edge clamping so border pixels map to the closest tile exactly as the historical uint16 reference does.
- @param np_module {ModuleType} Imported numpy module.
- @param axis_length {int} Number of samples on the axis.
- @param tile_size {int} Size of each padded tile on the axis.
- @param tile_count {int} Number of tiles on the axis.
- @return {tuple[object, object, object, object]} Lower indices, upper indices, lower weights, and upper weights.
- @satisfies REQ-136, REQ-137

### fn `def _build_clahe_tile_luts_float(np_module, luminance_float, clip_limit, tile_grid_size, histogram_size)` `priv` (L6712-6763)
- @brief Build per-tile CLAHE lookup tables from float luminance input.
- @details Pads the luminance plane to the CLAHE lattice, then builds one histogram, clipped histogram, and normalized LUT per tile in call order. Stores LUTs in one dense `(tiles_y, tiles_x, hist_size)` tensor used by the bilinear tile interpolation stage.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Luminance tensor in `[0,1]`.
- @param clip_limit {float} User-provided CLAHE clip limit.
- @param tile_grid_size {tuple[int, int]} OpenCV-compatible tile-grid tuple.
- @param histogram_size {int} Number of CLAHE histogram bins.
- @return {tuple[object, int, int]} LUT tensor, tile height, and tile width.
- @satisfies REQ-136, REQ-137

### fn `def _interpolate_clahe_bilinear_float(np_module, luminance_float, tile_luts, tile_height, tile_width)` `priv` (L6764-6816)
- @brief Bilinearly interpolate CLAHE LUT outputs across adjacent tiles.
- @details Samples the four neighboring tile LUTs for each original-image row using OpenCV-compatible tile-center geometry and blends those per-pixel outputs with bilinear weights. Processes one row at a time to avoid one extra full-image histogram-address buffer.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Original luminance tensor in `[0,1]`.
- @param tile_luts {object} Per-tile LUT tensor.
- @param tile_height {int} Padded tile height.
- @param tile_width {int} Padded tile width.
- @return {object} Equalized luminance tensor in `[0,1]`.
- @satisfies REQ-136, REQ-137

### fn `def _apply_clahe_luminance_float(np_module, luminance_float, clip_limit, tile_grid_size)` `priv` (L6817-6848)
- @brief Execute native float-domain CLAHE on one luminance plane.
- @details Builds per-tile histograms and normalized LUTs with OpenCV-like clip-limit normalization, then reconstructs one equalized luminance plane via bilinear interpolation between adjacent tiles. Keeps the luminance plane in normalized float representation throughout the active path.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Luminance tensor in `[0,1]`.
- @param clip_limit {float} User-provided CLAHE clip limit.
- @param tile_grid_size {tuple[int, int]} OpenCV-compatible tile-grid tuple.
- @return {object} Equalized luminance tensor in `[0,1]`.
- @satisfies REQ-136, REQ-137

### fn `def _reconstruct_rgb_from_ycrcb_luma_float(cv2_module, np_module, luminance_float, cr_channel, cb_channel)` `priv` (L6849-6872)
- @brief Reconstruct RGB float output from YCrCb float channels.
- @details Creates one float32 YCrCb tensor from one equalized luminance plane plus preserved Cr/Cb channels, converts it back to RGB with OpenCV color transforms only, and returns one clamped float64 RGB tensor for downstream blending in the auto-adjust pipeline.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Equalized luminance tensor in `[0,1]`.
- @param cr_channel {object} Preserved YCrCb Cr channel.
- @param cb_channel {object} Preserved YCrCb Cb channel.
- @return {object} Reconstructed RGB float tensor in `[0,1]`.
- @satisfies REQ-136, REQ-137

### fn `def _apply_clahe_luma_rgb_float(cv2_module, np_module, image_rgb_float, auto_adjust_options)` `priv` (L6873-6922)
- @brief Apply CLAHE-luma local contrast directly on RGB float buffers.
- @details Converts normalized RGB float input to float YCrCb, runs one native NumPy CLAHE implementation on the luminance plane with OpenCV-compatible tiling, clip-limit normalization, clipping, redistribution, and bilinear tile interpolation, then reconstructs one RGB float CLAHE candidate from preserved chroma plus mapped luminance and blends that candidate with the original float RGB image using configured strength. OpenCV is used only for RGB<->YCrCb color conversion; the active CLAHE path performs no uint16 image-plane round-trip.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float tensor in `[0,1]`.
- @param auto_adjust_options {AutoAdjustOptions} Parsed auto-adjust CLAHE controls.
- @return {object} RGB float tensor after optional CLAHE-luma stage.
- @satisfies REQ-123, REQ-125, REQ-136, REQ-137

### fn `def _rt_gamma2(np_module, values)` `priv` (L6923-6942)
- @brief Apply RawTherapee gamma2 transfer function.
- @details Implements the same piecewise gamma curve used in the attached auto-levels source for histogram-domain bright clipping normalization.
- @param np_module {ModuleType} Imported numpy module.
- @param values {object} Float tensor in linear domain.
- @return {object} Float tensor in gamma2 domain.
- @satisfies REQ-100

### fn `def _rt_igamma2(np_module, values)` `priv` (L6943-6963)
- @brief Apply inverse RawTherapee gamma2 transfer function.
- @details Implements inverse piecewise gamma curve paired with `_rt_gamma2` for whiteclip/black normalization inside auto-levels.
- @param np_module {ModuleType} Imported numpy module.
- @param values {object} Float tensor in gamma2 domain.
- @return {object} Float tensor in linear domain.
- @satisfies REQ-100

### fn `def _auto_levels_index_to_normalized_value(histogram_value, histcompr)` `priv` (L6964-6980)
- @brief Convert one compressed histogram coordinate to normalized scale.
- @details Maps one RawTherapee histogram bin coordinate or derived statistic from the fixed `2^16` histogram family to normalized `[0,1]` intensity units using the exact lower-edge scaling of the original code domain. This helper centralizes pure scale conversion and keeps algorithmic thresholds in `_compute_auto_levels_from_histogram(...)` domain-independent.
- @param histogram_value {int|float} Histogram index or statistic expressed in compressed-bin units.
- @param histcompr {int} Histogram compression shift in `[0, 15]`.
- @return {float} Normalized value in `[0, +inf)`.
- @satisfies REQ-100, REQ-117, REQ-118

### fn `def _auto_levels_normalized_to_legacy_code_value(value)` `priv` (L6981-6996)
- @brief Convert one normalized auto-levels scalar to legacy code scale.
- @details Multiplies one normalized scalar by the legacy `2^16-1` ceiling. Scope is restricted to compatibility mirrors returned by `_compute_auto_levels_from_histogram(...)` and to transitional adapter paths. Production auto-levels math must remain in normalized float units.
- @param value {int|float} Normalized scalar.
- @return {float} Legacy code-domain scalar.
- @note Scope: compatibility-only.
- @satisfies REQ-100, REQ-118

### fn `def _auto_levels_normalized_to_legacy_code(np_module, values)` `priv` (L6997-7013)
- @brief Convert normalized auto-levels tensors to legacy code scale.
- @details Multiplies normalized float tensors by the legacy `2^16-1` ceiling. This helper exists only for compatibility adapters that preserve deterministic legacy unit-test hooks while the production path remains float-native.
- @param np_module {ModuleType} Imported numpy module.
- @param values {object} Normalized scalar or tensor.
- @return {object} Float64 tensor on legacy code scale.
- @note Scope: compatibility-only.
- @satisfies REQ-100

### fn `def _auto_levels_legacy_code_to_normalized(np_module, values)` `priv` (L7014-7029)
- @brief Convert legacy code-domain tensors to normalized float scale.
- @details Divides legacy `2^16-1`-scaled float tensors by the code ceiling. Scope is restricted to transitional compatibility adapters and legacy unit test hooks. Production auto-levels math must not depend on this helper.
- @param np_module {ModuleType} Imported numpy module.
- @param values {object} Legacy code-domain scalar or tensor.
- @return {object} Float64 tensor on normalized scale.
- @note Scope: compatibility-only.
- @satisfies REQ-100

### fn `def _pack_auto_levels_metrics(` `priv` (L7030-7045)

### fn `def _build_autoexp_histogram_rgb_float(np_module, image_rgb_float, histcompr)` `priv` (L7097-7132)
- @brief Assemble normalized and compatibility auto-levels metrics.
- @brief Build RGB auto-levels histogram from normalized float image tensor.
- @details Stores the authoritative normalized-domain metrics under
`*_normalized` keys while mirroring the historical code-domain values under
legacy key names so existing callers and deterministic tests remain stable
during the float-native migration. Algorithmic controls (`expcomp`,
`brightness`, `contrast`, `hlcompr`, `ospread`) remain unscaled because
they are not pure code-domain quantities.
- @details Builds one RawTherapee-compatible luminance histogram from the post-merge RGB float tensor directly in normalized units, applies the RawTherapee BT.709 luminance coefficients, maps luminance to the fixed `2^(16-histcompr)` histogram family without creating an intermediate `*65535` working tensor, and clips indices deterministically.
- @param expcomp {float} Exposure compensation in EV.
- @param gain {float} Exposure gain factor.
- @param black {float} Normalized clipped black point.
- @param brightness {int} RawTherapee brightness control.
- @param contrast {int} RawTherapee contrast control.
- @param hlcompr {int} RawTherapee highlight-compression control.
- @param hlcomprthresh {int} RawTherapee highlight-compression threshold control.
- @param whiteclip {float} Normalized clipped white point.
- @param rawmax {float} Normalized maximum occupied histogram coordinate.
- @param shc {float} Normalized clipped shadow coordinate.
- @param median {float} Normalized histogram median.
- @param average {float} Normalized histogram average.
- @param overex {int} Overexposure classification flag from RawTherapee logic.
- @param ospread {float} Octile spread metric.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float tensor in `[0,1]`.
- @param histcompr {int} Histogram compression shift in `[0, 15]`.
- @return {dict[str, int|float]} Metrics dictionary with normalized and compatibility fields.
- @return {object} Histogram tensor.
- @satisfies REQ-100, REQ-117, REQ-118
- @satisfies REQ-100, REQ-117

### fn `def _build_autoexp_histogram_rgb_uint16(np_module, image_rgb_uint16, histcompr)` `priv` (L7133-7165)
- @brief Build RGB auto-levels histogram from uint16 image tensor.
- @details Builds one RawTherapee-compatible luminance histogram from the post-merge RGB tensor using BT.709 luminance, compressed bins (`hist_size = 65536 >> histcompr`), and deterministic index clipping.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_uint16 {object} RGB uint16 image tensor.
- @param histcompr {int} Histogram compression shift in `[0, 15]`.
- @return {object} Histogram tensor.
- @satisfies REQ-100, REQ-117

### fn `def _compute_auto_levels_from_histogram(np_module, histogram, histcompr, clip_percent)` `priv` (L7166-7365)
- @brief Compute auto-levels gain metrics from histogram.
- @details Ports `get_autoexp_from_histogram` from attached source as-is in numeric behavior for one luminance histogram: octile spread, white/black clip, exposure compensation, brightness/contrast, and highlight compression metrics. All scale-dependent intermediates are derived in normalized units. The returned dictionary exposes normalized-domain metrics under `*_normalized` keys and preserves legacy code-domain mirrors under the historical key names for deterministic compatibility.
- @param np_module {ModuleType} Imported numpy module.
- @param histogram {object} Flattened histogram tensor.
- @param histcompr {int} Histogram compression shift.
- @param clip_percent {float} Clip percentage.
- @return {dict[str, int|float]} Auto-levels metrics dictionary.
- @satisfies REQ-100, REQ-117, REQ-118

### fn `def _call_auto_levels_compat_helper(` `priv` (L7439-7444)

### fn `def _apply_auto_levels_float(np_module, image_rgb_float, auto_levels_options)` `priv` (L7488-7587)
- @brief Invoke float-native helper while honoring patched legacy aliases.
- @brief Apply auto-levels stage on RGB float tensor.
- @details Selects the float-native helper for normal execution. If a legacy
`_uint16` alias has been monkeypatched away from its built-in compatibility
shim, converts designated normalized arguments to legacy code scale,
delegates to the patched callable, and maps the returned tensor back to
normalized scale. This preserves deterministic legacy unit-test hooks
without reintroducing code-domain math into the production auto-levels
pipeline.
- @details Executes the RawTherapee-compatible histogram analysis on a normalized RGB float tensor, applies gain derived from exposure compensation, conditionally runs float-native highlight reconstruction, optionally normalizes overflowing RGB triplets back into gamut, and returns normalized RGB float output without any internal `*65535` or `/65535` staging.
- @param np_module {ModuleType} Imported numpy module.
- @param primary_callable {object} Float-native helper callable.
- @param legacy_name {str} Legacy module attribute name.
- @param scaled_argument_names {set[str]} Keyword names requiring normalized<->legacy scaling in compatibility mode.
- @param kwargs {dict[str, object]} Helper keyword arguments.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float tensor.
- @param auto_levels_options {AutoLevelsOptions} Parsed auto-levels options.
- @return {object} Normalized RGB float tensor returned by the selected helper.
- @return {object} RGB float tensor after auto-levels stage.
- @satisfies REQ-100, REQ-102, REQ-119, REQ-120
- @satisfies REQ-100, REQ-101, REQ-102, REQ-119, REQ-120

### fn `def _clip_auto_levels_out_of_gamut_float(np_module, image_rgb, maxval=1.0)` `priv` (L7588-7606)
- @brief Normalize overflowing RGB triplets back into normalized gamut.
- @details Computes per-pixel maximum channel value, derives one scale factor for overflowing pixels, and preserves RGB ratios while bounding the triplet to `maxval`.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on normalized scale.
- @param maxval {float} Maximum allowed channel value.
- @return {object} RGB float tensor with no channel above `maxval`.
- @satisfies REQ-120

### fn `def _clip_auto_levels_out_of_gamut_uint16(` `priv` (L7607-7608)

### fn `def _hlrecovery_luminance_float(np_module, image_rgb, maxval=1.0)` `priv` (L7638-7684)
- @brief Compatibility adapter for the legacy gamut-clip helper name.
- @brief Apply Luminance highlight reconstruction on normalized RGB tensor.
- @details Converts legacy code-domain float tensors to normalized scale,
delegates to `_clip_auto_levels_out_of_gamut_float(...)`, and rescales the
result back to legacy code units. This shim exists only for transitional
internal references and deterministic legacy unit-test hooks.
- @details Ports luminance method from attached source in RGB domain with clipped-channel chroma ratio scaling and masked reconstruction.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on legacy code scale.
- @param maxval {float} Maximum allowed legacy code-domain value.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on normalized scale.
- @param maxval {float} Maximum channel value.
- @return {object} RGB float tensor on legacy code scale.
- @return {object} Highlight-reconstructed RGB float tensor.
- @deprecated Use `_clip_auto_levels_out_of_gamut_float`.
- @satisfies REQ-120
- @satisfies REQ-102

### fn `def _hlrecovery_luminance_uint16(np_module, image_rgb, maxval=_AUTO_LEVELS_CODE_MAX)` `priv` (L7685-7713)
- @brief Compatibility adapter for legacy luminance recovery helper name.
- @details Converts legacy code-domain float tensors to normalized scale, delegates to `_hlrecovery_luminance_float(...)`, and rescales the result back to legacy code units. This shim exists only for transitional internal references and deterministic legacy unit-test hooks.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on legacy code scale.
- @param maxval {float} Maximum legacy code-domain value.
- @return {object} Highlight-reconstructed RGB float tensor on legacy code scale.
- @deprecated Use `_hlrecovery_luminance_float`.
- @satisfies REQ-102

### fn `def _hlrecovery_cielab_float(` `priv` (L7714-7715)

### fn `def _f_lab(values)` `priv` (L7748-7755)
- @brief Apply CIELab blending highlight reconstruction on RGB tensor.
- @details Ports CIELab blending method from attached source with Lab-space
channel repair under clipped highlights.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on normalized scale.
- @param maxval {float} Maximum channel value.
- @param xyz_cam {object|None} Optional XYZ conversion matrix.
- @param cam_xyz {object|None} Optional inverse matrix.
- @return {object} Highlight-reconstructed RGB float tensor.
- @satisfies REQ-102

### fn `def _f2xyz(values)` `priv` (L7756-7762)

### fn `def _hlrecovery_cielab_uint16(` `priv` (L7798-7799)

### fn `def _hlrecovery_blend_float(np_module, image_rgb, hlmax, maxval=1.0)` `priv` (L7833-7938)
- @brief Compatibility adapter for legacy CIELab helper name.
- @brief Apply Blend highlight reconstruction on RGB tensor.
- @details Converts legacy code-domain float tensors to normalized scale,
delegates to `_hlrecovery_cielab_float(...)`, and rescales the result back
to legacy code units. This shim exists only for transitional internal
references and deterministic legacy unit-test hooks.
- @details Ports blend method from attached source with quadratic channel blend and desaturation phase driven by clipping metrics.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on legacy code scale.
- @param maxval {float} Maximum legacy code-domain value.
- @param xyz_cam {object|None} Optional XYZ conversion matrix.
- @param cam_xyz {object|None} Optional inverse matrix.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on normalized scale.
- @param hlmax {object} Channel maxima vector with shape `(3,)`.
- @param maxval {float} Maximum channel value.
- @return {object} Highlight-reconstructed RGB float tensor on legacy code scale.
- @return {object} Highlight-reconstructed RGB float tensor.
- @deprecated Use `_hlrecovery_cielab_float`.
- @satisfies REQ-102
- @satisfies REQ-102

### fn `def _hlrecovery_blend_uint16(` `priv` (L7939-7940)

### fn `def _dilate_mask_float(np_module, mask)` `priv` (L7975-7997)
- @brief Compatibility adapter for legacy Blend helper name.
- @brief Expand one boolean mask by one Chebyshev pixel.
- @details Converts legacy code-domain float tensors to normalized scale,
delegates to `_hlrecovery_blend_float(...)`, and rescales the result back
to legacy code units. This shim exists only for transitional internal
references and deterministic legacy unit-test hooks.
- @details Pads the mask by one pixel and OR-combines the `3x3` neighborhood so later highlight-reconstruction stages can estimate one border region around clipped pixels without external dependencies.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on legacy code scale.
- @param hlmax {object} Legacy code-domain channel maxima vector.
- @param maxval {float} Maximum legacy code-domain value.
- @param np_module {ModuleType} Imported numpy module.
- @param mask {object} Boolean tensor with shape `H,W`.
- @return {object} Highlight-reconstructed RGB float tensor on legacy code scale.
- @return {object} Boolean tensor with the same shape as `mask`.
- @deprecated Use `_hlrecovery_blend_float`.
- @satisfies REQ-102
- @satisfies REQ-119

### fn `def _box_mean_3x3_float(np_module, image_2d)` `priv` (L7998-8021)
- @brief Compute one deterministic `3x3` box mean over a 2D float tensor.
- @details Uses edge padding and exact neighborhood averaging to approximate RawTherapee local neighborhood probes needed by RGB-space color-propagation and inpaint-opposed highlight reconstruction.
- @param np_module {ModuleType} Imported numpy module.
- @param image_2d {object} Float tensor with shape `H,W`.
- @return {object} Float tensor with shape `H,W`.
- @satisfies REQ-119

### fn `def _hlrecovery_color_propagation_float(np_module, image_rgb, maxval=1.0)` `priv` (L8022-8066)
- @brief Apply Color Propagation highlight reconstruction on RGB tensor.
- @details Approximates RawTherapee `Color` recovery in post-merge RGB space: detect clipped channel regions, estimate one local opposite-channel reference from `3x3` means, derive one border chrominance offset, and fill clipped samples deterministically.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on normalized scale.
- @param maxval {float} Maximum channel value.
- @return {object} Highlight-reconstructed RGB float tensor.
- @satisfies REQ-102, REQ-119

### fn `def _hlrecovery_color_propagation_uint16(` `priv` (L8067-8068)

### fn `def _hlrecovery_inpaint_opposed_float(` `priv` (L8098-8099)
- @brief Compatibility adapter for legacy Color Propagation helper name.
- @details Converts legacy code-domain float tensors to normalized scale,
delegates to `_hlrecovery_color_propagation_float(...)`, and rescales the
result back to legacy code units. This shim exists only for transitional
internal references and deterministic legacy unit-test hooks.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on legacy code scale.
- @param maxval {float} Maximum legacy code-domain value.
- @return {object} Highlight-reconstructed RGB float tensor on legacy code scale.
- @deprecated Use `_hlrecovery_color_propagation_float`.
- @satisfies REQ-102, REQ-119

### fn `def _hlrecovery_inpaint_opposed_uint16(` `priv` (L8152-8153)
- @brief Apply Inpaint Opposed highlight reconstruction on RGB tensor.
- @details Approximates RawTherapee `Coloropp` recovery in post-merge RGB
space: derive the RawTherapee clip threshold from `gain_threshold`,
construct one cubic-root opposite-channel neighborhood predictor, estimate
one border chrominance offset, and inpaint only pixels above the clip
threshold.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on normalized scale.
- @param gain_threshold {float} Positive Inpaint Opposed gain threshold.
- @param maxval {float} Maximum channel value.
- @return {object} Highlight-reconstructed RGB float tensor.
- @satisfies REQ-102, REQ-119

### fn `def _apply_auto_brightness_rgb_float(` `priv` (L8195-8198)
- @brief Compatibility adapter for legacy Inpaint Opposed helper name.
- @details Converts legacy code-domain float tensors to normalized scale,
delegates to `_hlrecovery_inpaint_opposed_float(...)`, and rescales the
result back to legacy code units. This shim exists only for transitional
internal references and deterministic legacy unit-test hooks.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on legacy code scale.
- @param gain_threshold {float} Positive Inpaint Opposed gain threshold.
- @param maxval {float} Maximum legacy code-domain value.
- @return {object} Highlight-reconstructed RGB float tensor on legacy code scale.
- @deprecated Use `_hlrecovery_inpaint_opposed_float`.
- @satisfies REQ-102, REQ-119

### fn `def _clamp01(np_module, values)` `priv` (L8255-8268)
- @brief Apply original photographic auto-brightness flow on RGB float tensor.
- @brief Clamp numeric image tensor values into `[0.0, 1.0]` interval.
- @details Executes `/tmp/auto-brightness.py` step order over normalized RGB
float input: linearize sRGB, derive BT.709 luminance, classify key using
normalized distribution thresholds, choose or override key value `a`,
apply Reinhard global tonemap with robust percentile white-point, preserve
chromaticity by luminance scaling, optionally desaturate only overflowing
linear RGB pixels, then re-encode to sRGB without any CLAHE substep.
- @details Applies vectorized clipping to ensure deterministic bounded values for auto-adjust float-domain operations.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float tensor.
- @param auto_brightness_options {AutoBrightnessOptions} Parsed auto-brightness parameters.
- @param np_module {ModuleType} Imported numpy module.
- @param values {object} Numeric tensor-like payload.
- @return {object} RGB float tensor after BT.709 auto-brightness.
- @return {object} Clipped tensor payload.
- @satisfies REQ-050, REQ-103, REQ-104, REQ-105, REQ-121, REQ-122
- @satisfies REQ-075

### fn `def _gaussian_kernel_2d(np_module, sigma, radius=None)` `priv` (L8269-8291)
- @brief Build normalized 2D Gaussian kernel.
- @details Creates deterministic Gaussian kernel used by selective blur stage; returns identity kernel when `sigma <= 0`.
- @param np_module {ModuleType} Imported numpy module.
- @param sigma {float} Gaussian sigma value.
- @param radius {int|None} Optional kernel radius override.
- @return {object} Normalized 2D kernel tensor.
- @satisfies REQ-075

### fn `def _rgb_to_hsl(np_module, rgb)` `priv` (L8292-8325)
- @brief Convert RGB float tensor to HSL channels.
- @details Implements explicit HSL conversion for auto-adjust saturation-gamma stage without delegating to external color-space helpers.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB tensor in `[0.0, 1.0]`.
- @return {tuple[object, object, object]} `(h, s, l)` channel tensors.
- @satisfies REQ-075

### fn `def _hue_to_rgb(np_module, p_values, q_values, t_values)` `priv` (L8326-8356)
- @brief Convert one hue-shift channel to RGB component.
- @details Evaluates piecewise hue interpolation branch used by HSL-to-RGB conversion in the auto-adjust pipeline.
- @param np_module {ModuleType} Imported numpy module.
- @param p_values {object} Lower chroma interpolation boundary.
- @param q_values {object} Upper chroma interpolation boundary.
- @param t_values {object} Hue-shifted channel tensor.
- @return {object} RGB component tensor.
- @satisfies REQ-075

### fn `def _hsl_to_rgb(np_module, hue, saturation, lightness)` `priv` (L8357-8397)
- @brief Convert HSL channels to RGB float tensor.
- @details Reconstructs RGB tensor with explicit achromatic/chromatic branches for the auto-adjust saturation-gamma stage.
- @param np_module {ModuleType} Imported numpy module.
- @param hue {object} Hue channel tensor.
- @param saturation {object} Saturation channel tensor.
- @param lightness {object} Lightness channel tensor.
- @return {object} RGB tensor in `[0.0, 1.0]`.
- @satisfies REQ-075

### fn `def _selective_blur_contrast_gated_vectorized(` `priv` (L8398-8399)

### fn `def _level_per_channel_adaptive(np_module, rgb, low_pct=0.1, high_pct=99.9)` `priv` (L8448-8470)
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

### fn `def _sigmoidal_contrast(np_module, rgb, contrast=3.0, midpoint=0.5)` `priv` (L8471-8495)
- @brief Execute sigmoidal contrast stage.
- @details Applies logistic remapping with bounded normalization for each RGB channel.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param contrast {float} Logistic slope.
- @param midpoint {float} Logistic midpoint.
- @return {object} Contrast-adjusted RGB float tensor.
- @satisfies REQ-075

### fn `def logistic(z_values)` (L8486-8488)
- @brief Execute sigmoidal contrast stage.
- @details Applies logistic remapping with bounded normalization for each RGB
channel.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param contrast {float} Logistic slope.
- @param midpoint {float} Logistic midpoint.
- @return {object} Contrast-adjusted RGB float tensor.
- @satisfies REQ-075

### fn `def _vibrance_hsl_gamma(np_module, rgb, saturation_gamma=0.8)` `priv` (L8496-8513)
- @brief Execute HSL saturation gamma stage.
- @details Converts RGB to HSL, applies saturation gamma transform, and converts back to RGB.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param saturation_gamma {float} Saturation gamma denominator value.
- @return {object} Saturation-adjusted RGB float tensor.
- @satisfies REQ-075

### fn `def _gaussian_blur_rgb(cv2_module, np_module, rgb, sigma)` `priv` (L8514-8537)
- @brief Execute RGB Gaussian blur with reflected border mode.
- @details Computes odd kernel size from sigma and applies OpenCV Gaussian blur preserving reflected border behavior.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param sigma {float} Gaussian sigma.
- @return {object} Blurred RGB float tensor.
- @satisfies REQ-075

### fn `def _high_pass_math_gray(cv2_module, np_module, rgb, blur_sigma=2.5)` `priv` (L8538-8561)
- @brief Execute high-pass math grayscale stage.
- @details Computes high-pass response as `A - B + 0.5` over RGB channels and converts to luminance grayscale tensor.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param blur_sigma {float} Gaussian blur sigma for high-pass base.
- @return {object} Grayscale float tensor in `[0.0, 1.0]`.
- @satisfies REQ-075

### fn `def _overlay_composite(np_module, base_rgb, overlay_gray)` `priv` (L8562-8583)
- @brief Execute overlay composite stage.
- @details Applies conditional overlay blend equation over RGB base and grayscale overlay tensors.
- @param np_module {ModuleType} Imported numpy module.
- @param base_rgb {object} Base RGB float tensor in `[0.0, 1.0]`.
- @param overlay_gray {object} Overlay grayscale tensor in `[0.0, 1.0]`.
- @return {object} Overlay-composited RGB float tensor.
- @satisfies REQ-075

### fn `def _apply_validated_auto_adjust_pipeline(` `priv` (L8584-8590)

### fn `def _load_piexif_dependency()` `priv` (L8699-8716)
- @brief Execute the validated auto-adjust pipeline.
- @brief Resolve piexif runtime dependency for EXIF thumbnail refresh.
- @details Accepts one normalized RGB float image, executes selective blur,
adaptive levels, float-domain CLAHE-luma, sigmoidal contrast, HSL
saturation gamma, and high-pass/overlay stages entirely in float domain,
optionally persists progressive debug checkpoints, and returns normalized
RGB float output without any file round-trip.
- @details Imports `piexif` module required for EXIF thumbnail regeneration and reinsertion; emits deterministic install guidance when dependency is missing.
- @param image_rgb_float {object} RGB float tensor.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param auto_adjust_options {AutoAdjustOptions} Shared auto-adjust knob values.
- @param imageio_module {ModuleType|None} Optional imageio module used for debug TIFF checkpoint emission.
- @param debug_context {DebugArtifactContext|None} Optional persistent debug output metadata.
- @return {object} RGB float tensor after auto-adjust.
- @return {ModuleType|None} Imported piexif module; `None` on dependency failure.
- @satisfies REQ-051, REQ-075, REQ-106, REQ-123, REQ-136, REQ-137, REQ-148
- @satisfies REQ-059, REQ-078

### fn `def _encode_jpg(` `priv` (L8717-8728)

### fn `def _collect_processing_errors(rawpy_module)` `priv` (L8860-8888)
- @brief Build deterministic tuple of recoverable processing exceptions.
- @details Combines common IO/value/subprocess errors with rawpy-specific decoding error classes when present in runtime module version.
- @param rawpy_module {ModuleType} Imported rawpy module.
- @return {tuple[type[BaseException], ...]} Ordered deduplicated exception class tuple.
- @satisfies REQ-059

### fn `def _is_supported_runtime_os()` `priv` (L8889-8908)
- @brief Validate runtime platform support for `dng2jpg`.
- @details Accepts Linux runtime only; emits explicit non-Linux unsupported message that includes OS label (`Windows` or `MacOS`) for deterministic UX.
- @return {bool} `True` when runtime OS is Linux; `False` otherwise.
- @satisfies REQ-055, REQ-059

### fn `def run(args)` (L8909-9108)
- @brief Execute `dng2jpg` command pipeline.
- @details Parses command options, validates dependencies, detects source DNG bits-per-color from RAW metadata, resolves manual or automatic EV-zero center, resolves static or adaptive EV selector around resolved center using bit-derived EV ceilings, extracts one linear HDR base image and derives three normalized RGB float brackets, executes the selected HDR backend with float input/output interfaces, executes the float-interface post-merge pipeline, optionally emits persistent debug TIFF checkpoints for executed stages, writes the final JPG, and guarantees temporary artifact cleanup through isolated temporary directory lifecycle.
- @param args {list[str]} Command argument vector excluding command token.
- @return {int} `0` on success; `1` on parse/validation/dependency/processing failure.
- @satisfies PRJ-001, CTN-001, CTN-004, CTN-005, REQ-010, REQ-011, REQ-012, REQ-013, REQ-014, REQ-015, REQ-050, REQ-052, REQ-100, REQ-106, REQ-107, REQ-108, REQ-109, REQ-110, REQ-111, REQ-112, REQ-113, REQ-114, REQ-115, REQ-126, REQ-127, REQ-128, REQ-129, REQ-131, REQ-132, REQ-133, REQ-134, REQ-138, REQ-139, REQ-140, REQ-146, REQ-147, REQ-148, REQ-149, REQ-157, REQ-158, REQ-159, REQ-160

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`PROGRAM`|var|pub|35||
|`DESCRIPTION`|var|pub|36||
|`DEFAULT_GAMMA`|var|pub|39||
|`DEFAULT_POST_GAMMA`|var|pub|40||
|`DEFAULT_BRIGHTNESS`|var|pub|41||
|`DEFAULT_CONTRAST`|var|pub|42||
|`DEFAULT_SATURATION`|var|pub|43||
|`DEFAULT_JPG_COMPRESSION`|var|pub|44||
|`DEFAULT_AUTO_ZERO_PCT`|var|pub|45||
|`DEFAULT_AUTO_EV_PCT`|var|pub|46||
|`DEFAULT_AA_BLUR_SIGMA`|var|pub|47||
|`DEFAULT_AA_BLUR_THRESHOLD_PCT`|var|pub|48||
|`DEFAULT_AA_LEVEL_LOW_PCT`|var|pub|49||
|`DEFAULT_AA_LEVEL_HIGH_PCT`|var|pub|50||
|`DEFAULT_AA_ENABLE_LOCAL_CONTRAST`|var|pub|51||
|`DEFAULT_AA_LOCAL_CONTRAST_STRENGTH`|var|pub|52||
|`DEFAULT_AA_CLAHE_CLIP_LIMIT`|var|pub|53||
|`DEFAULT_AA_CLAHE_TILE_GRID_SIZE`|var|pub|54||
|`DEFAULT_AA_SIGMOID_CONTRAST`|var|pub|55||
|`DEFAULT_AA_SIGMOID_MIDPOINT`|var|pub|56||
|`DEFAULT_AA_SATURATION_GAMMA`|var|pub|57||
|`DEFAULT_AA_HIGHPASS_BLUR_SIGMA`|var|pub|58||
|`DEFAULT_AB_KEY_VALUE`|var|pub|59||
|`DEFAULT_AB_WHITE_POINT_PERCENTILE`|var|pub|60||
|`DEFAULT_AB_A_MIN`|var|pub|61||
|`DEFAULT_AB_A_MAX`|var|pub|62||
|`DEFAULT_AB_MAX_AUTO_BOOST_FACTOR`|var|pub|63||
|`DEFAULT_AB_ENABLE_LUMINANCE_PRESERVING_DESAT`|var|pub|64||
|`DEFAULT_AB_EPS`|var|pub|65||
|`DEFAULT_AB_LOW_KEY_VALUE`|var|pub|66||
|`DEFAULT_AB_NORMAL_KEY_VALUE`|var|pub|67||
|`DEFAULT_AB_HIGH_KEY_VALUE`|var|pub|68||
|`DEFAULT_AL_CLIP_PERCENT`|var|pub|69||
|`DEFAULT_AL_CLIP_OUT_OF_GAMUT`|var|pub|70||
|`DEFAULT_AL_GAIN_THRESHOLD`|var|pub|71||
|`DEFAULT_AL_HISTCOMPR`|var|pub|72||
|`DEFAULT_LUMINANCE_HDR_MODEL`|var|pub|94||
|`DEFAULT_LUMINANCE_HDR_WEIGHT`|var|pub|95||
|`DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE`|var|pub|96||
|`DEFAULT_LUMINANCE_TMO`|var|pub|97||
|`DEFAULT_AUTO_ADJUST_ENABLED`|var|pub|98||
|`HDR_MERGE_MODE_LUMINANCE`|var|pub|99||
|`HDR_MERGE_MODE_OPENCV`|var|pub|100||
|`HDR_MERGE_MODE_HDR_PLUS`|var|pub|101||
|`OPENCV_MERGE_ALGORITHM_DEBEVEC`|var|pub|102||
|`OPENCV_MERGE_ALGORITHM_ROBERTSON`|var|pub|103||
|`OPENCV_MERGE_ALGORITHM_MERTENS`|var|pub|104||
|`DEFAULT_REINHARD02_BRIGHTNESS`|var|pub|105||
|`DEFAULT_REINHARD02_CONTRAST`|var|pub|106||
|`DEFAULT_REINHARD02_SATURATION`|var|pub|107||
|`DEFAULT_MANTIUK08_CONTRAST`|var|pub|108||
|`DEFAULT_OPENCV_POST_GAMMA`|var|pub|109||
|`DEFAULT_OPENCV_BRIGHTNESS`|var|pub|110||
|`DEFAULT_OPENCV_CONTRAST`|var|pub|111||
|`DEFAULT_OPENCV_SATURATION`|var|pub|112||
|`DEFAULT_OPENCV_MERGE_ALGORITHM`|var|pub|113||
|`DEFAULT_OPENCV_TONEMAP_ENABLED`|var|pub|114||
|`DEFAULT_OPENCV_TONEMAP_GAMMA`|var|pub|115||
|`DEFAULT_HDRPLUS_PROXY_MODE`|var|pub|116||
|`DEFAULT_HDRPLUS_SEARCH_RADIUS`|var|pub|117||
|`DEFAULT_HDRPLUS_TEMPORAL_FACTOR`|var|pub|118||
|`DEFAULT_HDRPLUS_TEMPORAL_MIN_DIST`|var|pub|119||
|`DEFAULT_HDRPLUS_TEMPORAL_MAX_DIST`|var|pub|120||
|`HDRPLUS_TILE_SIZE`|var|pub|121||
|`HDRPLUS_TILE_STRIDE`|var|pub|122||
|`HDRPLUS_DOWNSAMPLED_TILE_SIZE`|var|pub|123||
|`HDRPLUS_ALIGNMENT_LEVELS`|var|pub|124||
|`HDRPLUS_ALIGNMENT_DOWNSAMPLE_RATE`|var|pub|125||
|`HDRPLUS_TEMPORAL_FACTOR`|var|pub|126||
|`HDRPLUS_TEMPORAL_MIN_DIST`|var|pub|127||
|`HDRPLUS_TEMPORAL_MAX_DIST`|var|pub|128||
|`EV_STEP`|var|pub|130||
|`MIN_SUPPORTED_BITS_PER_COLOR`|var|pub|131||
|`DEFAULT_DNG_BITS_PER_COLOR`|var|pub|132||
|`SUPPORTED_EV_VALUES`|var|pub|133||
|`AUTO_EV_LOW_PERCENTILE`|var|pub|139||
|`AUTO_EV_HIGH_PERCENTILE`|var|pub|140||
|`AUTO_EV_MEDIAN_PERCENTILE`|var|pub|141||
|`AUTO_EV_TARGET_SHADOW`|var|pub|142||
|`AUTO_EV_TARGET_HIGHLIGHT`|var|pub|143||
|`AUTO_EV_MEDIAN_TARGET`|var|pub|144||
|`AUTO_ZERO_SCENE_KEY_LOW_THRESHOLD`|var|pub|145||
|`AUTO_ZERO_SCENE_KEY_HIGH_THRESHOLD`|var|pub|146||
|`AUTO_ZERO_TARGET_LOW_KEY`|var|pub|147||
|`AUTO_ZERO_TARGET_HIGH_KEY`|var|pub|148||
|`AutoAdjustOptions`|class|pub|362-397|class AutoAdjustOptions|
|`AutoBrightnessOptions`|class|pub|399-427|class AutoBrightnessOptions|
|`AutoLevelsOptions`|class|pub|429-452|class AutoLevelsOptions|
|`PostprocessOptions`|class|pub|454-490|class PostprocessOptions|
|`DebugArtifactContext`|class|pub|492-508|class DebugArtifactContext|
|`LuminanceOptions`|class|pub|510-530|class LuminanceOptions|
|`OpenCvMergeOptions`|class|pub|532-552|class OpenCvMergeOptions|
|`HdrPlusOptions`|class|pub|554-577|class HdrPlusOptions|
|`HdrPlusTemporalRuntimeOptions`|class|pub|579-598|class HdrPlusTemporalRuntimeOptions|
|`AutoEvInputs`|class|pub|600-627|class AutoEvInputs|
|`AutoZeroEvaluation`|class|pub|629-647|class AutoZeroEvaluation|
|`_print_box_table`|fn|priv|648-684|def _print_box_table(headers, rows, header_rows=())|
|`_border`|fn|priv|668-670|def _border(left, middle, right)|
|`_line`|fn|priv|671-674|def _line(values)|
|`_build_two_line_operator_rows`|fn|priv|685-701|def _build_two_line_operator_rows(operator_entries)|
|`_print_help_section`|fn|priv|702-716|def _print_help_section(title)|
|`_print_help_option`|fn|priv|717-758|def _print_help_option(option_label, description, detail_...|
|`print_help`|fn|pub|759-958|def print_help(version)|
|`_calculate_max_ev_from_bits`|fn|priv|1129-1147|def _calculate_max_ev_from_bits(bits_per_color)|
|`_calculate_safe_ev_zero_max`|fn|priv|1148-1160|def _calculate_safe_ev_zero_max(base_max_ev)|
|`_derive_supported_ev_zero_values`|fn|priv|1161-1177|def _derive_supported_ev_zero_values(base_max_ev)|
|`_derive_supported_ev_values`|fn|priv|1178-1206|def _derive_supported_ev_values(bits_per_color, ev_zero=0.0)|
|`_detect_dng_bits_per_color`|fn|priv|1207-1252|def _detect_dng_bits_per_color(raw_handle)|
|`_is_ev_value_on_supported_step`|fn|priv|1253-1266|def _is_ev_value_on_supported_step(ev_value)|
|`_parse_ev_option`|fn|priv|1267-1298|def _parse_ev_option(ev_raw)|
|`_parse_ev_zero_option`|fn|priv|1299-1329|def _parse_ev_zero_option(ev_zero_raw)|
|`_parse_auto_ev_option`|fn|priv|1330-1349|def _parse_auto_ev_option(auto_ev_raw)|
|`_parse_auto_zero_option`|fn|priv|1350-1369|def _parse_auto_zero_option(auto_zero_raw)|
|`_parse_percentage_option`|fn|priv|1370-1392|def _parse_percentage_option(option_name, option_raw)|
|`_parse_auto_brightness_option`|fn|priv|1393-1412|def _parse_auto_brightness_option(auto_brightness_raw)|
|`_parse_auto_levels_option`|fn|priv|1413-1432|def _parse_auto_levels_option(auto_levels_raw)|
|`_parse_explicit_boolean_option`|fn|priv|1433-1453|def _parse_explicit_boolean_option(option_name, option_raw)|
|`_parse_opencv_merge_algorithm_option`|fn|priv|1454-1478|def _parse_opencv_merge_algorithm_option(algorithm_raw)|
|`_parse_opencv_options`|fn|priv|1479-1525|def _parse_opencv_options(opencv_raw_values)|
|`_clamp_ev_to_supported`|fn|priv|1526-1539|def _clamp_ev_to_supported(ev_candidate, ev_values)|
|`_quantize_ev_to_supported`|fn|priv|1540-1561|def _quantize_ev_to_supported(ev_value, ev_values)|
|`_quantize_ev_toward_zero_step`|fn|priv|1562-1583|def _quantize_ev_toward_zero_step(ev_value, step=EV_STEP)|
|`_apply_auto_percentage_scaling`|fn|priv|1584-1598|def _apply_auto_percentage_scaling(ev_value, percentage)|
|`_extract_normalized_preview_luminance_stats`|fn|priv|1599-1658|def _extract_normalized_preview_luminance_stats(raw_handle)|
|`_percentile`|fn|priv|1633-1643|def _percentile(percentile_value)|
|`_extract_base_rgb_linear_float`|fn|priv|1659-1687|def _extract_base_rgb_linear_float(raw_handle, np_module)|
|`_coerce_positive_luminance`|fn|priv|1688-1707|def _coerce_positive_luminance(value, fallback)|
|`_calculate_bt709_luminance`|fn|priv|1708-1730|def _calculate_bt709_luminance(np_module, image_rgb_float)|
|`_smoothstep`|fn|priv|1731-1749|def _smoothstep(np_module, values, edge0, edge1)|
|`_calculate_entropy_optimized_ev`|fn|priv|1750-1795|def _calculate_entropy_optimized_ev(cv2_module, np_module...|
|`_calculate_ettr_ev`|fn|priv|1796-1815|def _calculate_ettr_ev(np_module, luminance_float)|
|`_calculate_detail_preservation_ev`|fn|priv|1816-1882|def _calculate_detail_preservation_ev(cv2_module, np_modu...|
|`_calculate_auto_zero_evaluations`|fn|priv|1883-1920|def _calculate_auto_zero_evaluations(cv2_module, np_modul...|
|`_evaluate_auto_zero_exposure`|fn|priv|1921-1954|def _evaluate_auto_zero_exposure(cv2_module, np_module, i...|
|`_optimize_adaptive_ev_delta`|fn|priv|1955-1984|def _optimize_adaptive_ev_delta(auto_ev_inputs)|
|`_compute_auto_ev_value_from_stats`|fn|priv|1985-1990|def _compute_auto_ev_value_from_stats(|
|`_compute_auto_ev_value`|fn|priv|2018-2045|def _compute_auto_ev_value(raw_handle, supported_ev_value...|
|`_resolve_ev_zero`|fn|priv|2046-2055|def _resolve_ev_zero(|
|`_resolve_ev_value`|fn|priv|2119-2126|def _resolve_ev_value(|
|`_parse_luminance_text_option`|fn|priv|2179-2199|def _parse_luminance_text_option(option_name, option_raw)|
|`_parse_gamma_option`|fn|priv|2200-2238|def _parse_gamma_option(gamma_raw)|
|`_parse_positive_float_option`|fn|priv|2239-2262|def _parse_positive_float_option(option_name, option_raw)|
|`_parse_positive_int_option`|fn|priv|2263-2286|def _parse_positive_int_option(option_name, option_raw)|
|`_parse_tmo_passthrough_value`|fn|priv|2287-2303|def _parse_tmo_passthrough_value(option_name, option_raw)|
|`_parse_jpg_compression_option`|fn|priv|2304-2326|def _parse_jpg_compression_option(compression_raw)|
|`_parse_float_exclusive_range_option`|fn|priv|2327-2351|def _parse_float_exclusive_range_option(option_name, opti...|
|`_parse_non_negative_float_option`|fn|priv|2352-2374|def _parse_non_negative_float_option(option_name, option_...|
|`_parse_float_in_range_option`|fn|priv|2375-2400|def _parse_float_in_range_option(option_name, option_raw,...|
|`_parse_positive_int_pair_option`|fn|priv|2401-2432|def _parse_positive_int_pair_option(option_name, option_raw)|
|`_parse_auto_brightness_options`|fn|priv|2433-2529|def _parse_auto_brightness_options(auto_brightness_raw_va...|
|`_parse_auto_levels_hr_method_option`|fn|priv|2530-2561|def _parse_auto_levels_hr_method_option(auto_levels_metho...|
|`_parse_auto_levels_options`|fn|priv|2562-2625|def _parse_auto_levels_options(auto_levels_raw_values)|
|`_parse_auto_adjust_options`|fn|priv|2626-2775|def _parse_auto_adjust_options(auto_adjust_raw_values)|
|`_parse_hdrplus_proxy_mode_option`|fn|priv|2776-2794|def _parse_hdrplus_proxy_mode_option(proxy_mode_raw)|
|`_parse_hdrplus_options`|fn|priv|2795-2871|def _parse_hdrplus_options(hdrplus_raw_values)|
|`_parse_auto_adjust_option`|fn|priv|2872-2895|def _parse_auto_adjust_option(auto_adjust_raw)|
|`_parse_hdr_merge_option`|fn|priv|2896-2925|def _parse_hdr_merge_option(hdr_merge_raw)|
|`_resolve_default_postprocess`|fn|priv|2926-2929|def _resolve_default_postprocess(|
|`_parse_run_options`|fn|priv|3001-3200|def _parse_run_options(args)|
|`_load_image_dependencies`|fn|priv|3822-3859|def _load_image_dependencies()|
|`_parse_exif_datetime_to_timestamp`|fn|priv|3860-3890|def _parse_exif_datetime_to_timestamp(datetime_raw)|
|`_parse_exif_exposure_time_to_seconds`|fn|priv|3891-3953|def _parse_exif_exposure_time_to_seconds(exposure_raw)|
|`_extract_dng_exif_payload_and_timestamp`|fn|priv|3954-4048|def _extract_dng_exif_payload_and_timestamp(pil_image_mod...|
|`_read_exif_value`|fn|priv|3998-4015|def _read_exif_value(exif_tag)|
|`_resolve_thumbnail_transpose_map`|fn|priv|4049-4080|def _resolve_thumbnail_transpose_map(pil_image_module)|
|`_apply_orientation_transform`|fn|priv|4081-4103|def _apply_orientation_transform(pil_image_module, pil_im...|
|`_build_oriented_thumbnail_jpeg_bytes`|fn|priv|4104-4105|def _build_oriented_thumbnail_jpeg_bytes(|
|`_coerce_exif_int_like_value`|fn|priv|4136-4178|def _coerce_exif_int_like_value(raw_value)|
|`_normalize_ifd_integer_like_values_for_piexif_dump`|fn|priv|4179-4312|def _normalize_ifd_integer_like_values_for_piexif_dump(pi...|
|`_refresh_output_jpg_exif_thumbnail_after_save`|fn|priv|4313-4319|def _refresh_output_jpg_exif_thumbnail_after_save(|
|`_set_output_file_timestamps`|fn|priv|4369-4383|def _set_output_file_timestamps(output_jpg, exif_timestamp)|
|`_sync_output_file_timestamps_from_exif`|fn|priv|4384-4401|def _sync_output_file_timestamps_from_exif(output_jpg, ex...|
|`_build_exposure_multipliers`|fn|priv|4402-4420|def _build_exposure_multipliers(ev_value, ev_zero=0.0)|
|`_build_bracket_images_from_linear_base_float`|fn|priv|4421-4449|def _build_bracket_images_from_linear_base_float(np_modul...|
|`_extract_bracket_images_float`|fn|priv|4450-4455|def _extract_bracket_images_float(|
|`_order_bracket_paths`|fn|priv|4491-4516|def _order_bracket_paths(bracket_paths)|
|`_order_hdr_plus_reference_paths`|fn|priv|4517-4532|def _order_hdr_plus_reference_paths(bracket_paths)|
|`_run_luminance_hdr_cli`|fn|priv|4533-4540|def _run_luminance_hdr_cli(|
|`_build_opencv_radiance_exposure_times`|fn|priv|4604-4607|def _build_opencv_radiance_exposure_times(|
|`_build_ev_times_from_ev_zero_and_delta`|fn|priv|4641-4660|def _build_ev_times_from_ev_zero_and_delta(ev_zero, ev_de...|
|`_normalize_opencv_hdr_to_unit_range`|fn|priv|4661-4684|def _normalize_opencv_hdr_to_unit_range(np_module, hdr_rg...|
|`_run_opencv_merge_mertens`|fn|priv|4685-4706|def _run_opencv_merge_mertens(cv2_module, np_module, expo...|
|`_estimate_opencv_camera_response`|fn|priv|4707-4711|def _estimate_opencv_camera_response(|
|`_run_opencv_merge_radiance`|fn|priv|4740-4747|def _run_opencv_merge_radiance(|
|`_normalize_debevec_hdr_to_unit_range`|fn|priv|4811-4830|def _normalize_debevec_hdr_to_unit_range(np_module, hdr_r...|
|`_run_opencv_hdr_merge`|fn|priv|4831-4838|def _run_opencv_hdr_merge(|
|`_hdrplus_box_down2_float32`|fn|priv|4901-4929|def _hdrplus_box_down2_float32(np_module, frames_float32)|
|`_hdrplus_gauss_down4_float32`|fn|priv|4930-4976|def _hdrplus_gauss_down4_float32(np_module, frames_float32)|
|`_hdrplus_build_scalar_proxy_float32`|fn|priv|4977-5010|def _hdrplus_build_scalar_proxy_float32(np_module, frames...|
|`_hdrplus_compute_tile_start_positions`|fn|priv|5011-5031|def _hdrplus_compute_tile_start_positions(np_module, axis...|
|`_hdrplus_trunc_divide_int32`|fn|priv|5032-5050|def _hdrplus_trunc_divide_int32(np_module, values_int32, ...|
|`_hdrplus_compute_alignment_bounds`|fn|priv|5051-5075|def _hdrplus_compute_alignment_bounds(search_radius)|
|`_hdrplus_compute_alignment_margin`|fn|priv|5076-5094|def _hdrplus_compute_alignment_margin(search_radius, divi...|
|`_hdrplus_extract_overlapping_tiles`|fn|priv|5095-5100|def _hdrplus_extract_overlapping_tiles(|
|`_hdrplus_extract_aligned_tiles`|fn|priv|5153-5159|def _hdrplus_extract_aligned_tiles(|
|`_hdrplus_align_layer`|fn|priv|5232-5239|def _hdrplus_align_layer(|
|`_hdrplus_align_layers`|fn|priv|5329-5416|def _hdrplus_align_layers(np_module, scalar_frames, hdrpl...|
|`_hdrplus_resolve_temporal_runtime_options`|fn|priv|5417-5441|def _hdrplus_resolve_temporal_runtime_options(hdrplus_opt...|
|`_hdrplus_compute_temporal_weights`|fn|priv|5442-5446|def _hdrplus_compute_temporal_weights(|
|`_hdrplus_merge_temporal_rgb`|fn|priv|5527-5533|def _hdrplus_merge_temporal_rgb(|
|`_hdrplus_merge_spatial_rgb`|fn|priv|5582-5654|def _hdrplus_merge_spatial_rgb(np_module, temporal_tiles,...|
|`_run_hdr_plus_merge`|fn|priv|5655-5658|def _run_hdr_plus_merge(|
|`_convert_compression_to_quality`|fn|priv|5735-5745|def _convert_compression_to_quality(jpg_compression)|
|`_collect_missing_external_executables`|fn|priv|5746-5748|def _collect_missing_external_executables(|
|`_resolve_auto_adjust_dependencies`|fn|priv|5767-5792|def _resolve_auto_adjust_dependencies()|
|`_resolve_numpy_dependency`|fn|priv|5793-5812|def _resolve_numpy_dependency()|
|`_to_float32_image_array`|fn|priv|5813-5844|def _to_float32_image_array(np_module, image_data)|
|`_normalize_float_rgb_image`|fn|priv|5845-5872|def _normalize_float_rgb_image(np_module, image_data)|
|`_write_rgb_float_tiff16`|fn|priv|5873-5896|def _write_rgb_float_tiff16(imageio_module, np_module, ou...|
|`_write_debug_rgb_float_tiff`|fn|priv|5897-5902|def _write_debug_rgb_float_tiff(|
|`_build_debug_artifact_context`|fn|priv|5932-5952|def _build_debug_artifact_context(output_jpg, input_dng, ...|
|`_format_debug_ev_suffix_value`|fn|priv|5953-5970|def _format_debug_ev_suffix_value(ev_value)|
|`_materialize_bracket_tiffs_from_float`|fn|priv|5971-5975|def _materialize_bracket_tiffs_from_float(|
|`_to_uint8_image_array`|fn|priv|6005-6051|def _to_uint8_image_array(np_module, image_data)|
|`_to_uint16_image_array`|fn|priv|6052-6096|def _to_uint16_image_array(np_module, image_data)|
|`_apply_post_gamma_float`|fn|priv|6097-6122|def _apply_post_gamma_float(np_module, image_rgb_float, g...|
|`_apply_brightness_float`|fn|priv|6123-6145|def _apply_brightness_float(np_module, image_rgb_float, b...|
|`_apply_contrast_float`|fn|priv|6146-6170|def _apply_contrast_float(np_module, image_rgb_float, con...|
|`_apply_saturation_float`|fn|priv|6171-6200|def _apply_saturation_float(np_module, image_rgb_float, s...|
|`_apply_static_postprocess_float`|fn|priv|6201-6206|def _apply_static_postprocess_float(|
|`_to_linear_srgb`|fn|priv|6283-6300|def _to_linear_srgb(np_module, image_srgb)|
|`_from_linear_srgb`|fn|priv|6301-6318|def _from_linear_srgb(np_module, image_linear)|
|`_compute_bt709_luminance`|fn|priv|6319-6336|def _compute_bt709_luminance(np_module, linear_rgb)|
|`_analyze_luminance_key`|fn|priv|6337-6376|def _analyze_luminance_key(np_module, luminance, eps)|
|`_choose_auto_key_value`|fn|priv|6377-6422|def _choose_auto_key_value(key_analysis, auto_brightness_...|
|`_reinhard_global_tonemap_luminance`|fn|priv|6423-6428|def _reinhard_global_tonemap_luminance(|
|`_luminance_preserving_desaturate_to_fit`|fn|priv|6462-6489|def _luminance_preserving_desaturate_to_fit(np_module, rg...|
|`_apply_mild_local_contrast_bgr_uint16`|fn|priv|6490-6528|def _apply_mild_local_contrast_bgr_uint16(cv2_module, np_...|
|`_quantize_clahe_luminance_bins`|fn|priv|6529-6554|def _quantize_clahe_luminance_bins(np_module, luminance_v...|
|`_build_clahe_float_tile_histogram`|fn|priv|6555-6576|def _build_clahe_float_tile_histogram(np_module, luminanc...|
|`_clip_clahe_histogram`|fn|priv|6577-6624|def _clip_clahe_histogram(np_module, histogram, clip_limi...|
|`_build_clahe_float_lut`|fn|priv|6625-6644|def _build_clahe_float_lut(np_module, histogram, tile_pop...|
|`_pad_clahe_luminance_float`|fn|priv|6645-6683|def _pad_clahe_luminance_float(np_module, luminance_float...|
|`_build_clahe_axis_interpolation`|fn|priv|6684-6711|def _build_clahe_axis_interpolation(np_module, axis_lengt...|
|`_build_clahe_tile_luts_float`|fn|priv|6712-6763|def _build_clahe_tile_luts_float(np_module, luminance_flo...|
|`_interpolate_clahe_bilinear_float`|fn|priv|6764-6816|def _interpolate_clahe_bilinear_float(np_module, luminanc...|
|`_apply_clahe_luminance_float`|fn|priv|6817-6848|def _apply_clahe_luminance_float(np_module, luminance_flo...|
|`_reconstruct_rgb_from_ycrcb_luma_float`|fn|priv|6849-6872|def _reconstruct_rgb_from_ycrcb_luma_float(cv2_module, np...|
|`_apply_clahe_luma_rgb_float`|fn|priv|6873-6922|def _apply_clahe_luma_rgb_float(cv2_module, np_module, im...|
|`_rt_gamma2`|fn|priv|6923-6942|def _rt_gamma2(np_module, values)|
|`_rt_igamma2`|fn|priv|6943-6963|def _rt_igamma2(np_module, values)|
|`_auto_levels_index_to_normalized_value`|fn|priv|6964-6980|def _auto_levels_index_to_normalized_value(histogram_valu...|
|`_auto_levels_normalized_to_legacy_code_value`|fn|priv|6981-6996|def _auto_levels_normalized_to_legacy_code_value(value)|
|`_auto_levels_normalized_to_legacy_code`|fn|priv|6997-7013|def _auto_levels_normalized_to_legacy_code(np_module, val...|
|`_auto_levels_legacy_code_to_normalized`|fn|priv|7014-7029|def _auto_levels_legacy_code_to_normalized(np_module, val...|
|`_pack_auto_levels_metrics`|fn|priv|7030-7045|def _pack_auto_levels_metrics(|
|`_build_autoexp_histogram_rgb_float`|fn|priv|7097-7132|def _build_autoexp_histogram_rgb_float(np_module, image_r...|
|`_build_autoexp_histogram_rgb_uint16`|fn|priv|7133-7165|def _build_autoexp_histogram_rgb_uint16(np_module, image_...|
|`_compute_auto_levels_from_histogram`|fn|priv|7166-7365|def _compute_auto_levels_from_histogram(np_module, histog...|
|`_call_auto_levels_compat_helper`|fn|priv|7439-7444|def _call_auto_levels_compat_helper(|
|`_apply_auto_levels_float`|fn|priv|7488-7587|def _apply_auto_levels_float(np_module, image_rgb_float, ...|
|`_clip_auto_levels_out_of_gamut_float`|fn|priv|7588-7606|def _clip_auto_levels_out_of_gamut_float(np_module, image...|
|`_clip_auto_levels_out_of_gamut_uint16`|fn|priv|7607-7608|def _clip_auto_levels_out_of_gamut_uint16(|
|`_hlrecovery_luminance_float`|fn|priv|7638-7684|def _hlrecovery_luminance_float(np_module, image_rgb, max...|
|`_hlrecovery_luminance_uint16`|fn|priv|7685-7713|def _hlrecovery_luminance_uint16(np_module, image_rgb, ma...|
|`_hlrecovery_cielab_float`|fn|priv|7714-7715|def _hlrecovery_cielab_float(|
|`_f_lab`|fn|priv|7748-7755|def _f_lab(values)|
|`_f2xyz`|fn|priv|7756-7762|def _f2xyz(values)|
|`_hlrecovery_cielab_uint16`|fn|priv|7798-7799|def _hlrecovery_cielab_uint16(|
|`_hlrecovery_blend_float`|fn|priv|7833-7938|def _hlrecovery_blend_float(np_module, image_rgb, hlmax, ...|
|`_hlrecovery_blend_uint16`|fn|priv|7939-7940|def _hlrecovery_blend_uint16(|
|`_dilate_mask_float`|fn|priv|7975-7997|def _dilate_mask_float(np_module, mask)|
|`_box_mean_3x3_float`|fn|priv|7998-8021|def _box_mean_3x3_float(np_module, image_2d)|
|`_hlrecovery_color_propagation_float`|fn|priv|8022-8066|def _hlrecovery_color_propagation_float(np_module, image_...|
|`_hlrecovery_color_propagation_uint16`|fn|priv|8067-8068|def _hlrecovery_color_propagation_uint16(|
|`_hlrecovery_inpaint_opposed_float`|fn|priv|8098-8099|def _hlrecovery_inpaint_opposed_float(|
|`_hlrecovery_inpaint_opposed_uint16`|fn|priv|8152-8153|def _hlrecovery_inpaint_opposed_uint16(|
|`_apply_auto_brightness_rgb_float`|fn|priv|8195-8198|def _apply_auto_brightness_rgb_float(|
|`_clamp01`|fn|priv|8255-8268|def _clamp01(np_module, values)|
|`_gaussian_kernel_2d`|fn|priv|8269-8291|def _gaussian_kernel_2d(np_module, sigma, radius=None)|
|`_rgb_to_hsl`|fn|priv|8292-8325|def _rgb_to_hsl(np_module, rgb)|
|`_hue_to_rgb`|fn|priv|8326-8356|def _hue_to_rgb(np_module, p_values, q_values, t_values)|
|`_hsl_to_rgb`|fn|priv|8357-8397|def _hsl_to_rgb(np_module, hue, saturation, lightness)|
|`_selective_blur_contrast_gated_vectorized`|fn|priv|8398-8399|def _selective_blur_contrast_gated_vectorized(|
|`_level_per_channel_adaptive`|fn|priv|8448-8470|def _level_per_channel_adaptive(np_module, rgb, low_pct=0...|
|`_sigmoidal_contrast`|fn|priv|8471-8495|def _sigmoidal_contrast(np_module, rgb, contrast=3.0, mid...|
|`logistic`|fn|pub|8486-8488|def logistic(z_values)|
|`_vibrance_hsl_gamma`|fn|priv|8496-8513|def _vibrance_hsl_gamma(np_module, rgb, saturation_gamma=...|
|`_gaussian_blur_rgb`|fn|priv|8514-8537|def _gaussian_blur_rgb(cv2_module, np_module, rgb, sigma)|
|`_high_pass_math_gray`|fn|priv|8538-8561|def _high_pass_math_gray(cv2_module, np_module, rgb, blur...|
|`_overlay_composite`|fn|priv|8562-8583|def _overlay_composite(np_module, base_rgb, overlay_gray)|
|`_apply_validated_auto_adjust_pipeline`|fn|priv|8584-8590|def _apply_validated_auto_adjust_pipeline(|
|`_load_piexif_dependency`|fn|priv|8699-8716|def _load_piexif_dependency()|
|`_encode_jpg`|fn|priv|8717-8728|def _encode_jpg(|
|`_collect_processing_errors`|fn|priv|8860-8888|def _collect_processing_errors(rawpy_module)|
|`_is_supported_runtime_os`|fn|priv|8889-8908|def _is_supported_runtime_os()|
|`run`|fn|pub|8909-9108|def run(args)|


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

