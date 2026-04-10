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

# core.py | Python | 226L | 9 symbols | 14 imports | 8 comments
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

### fn `def _check_online_version(force: bool) -> None` `priv` (L101-174)
- @brief Execute the latest-release check and refresh cache idle-time policy.
- @details Skips the network request when `_should_skip_version_check(...)` returns true. Otherwise performs one GitHub latest-release API request, normalizes the returned tag name, assigns idle-delay `3600` seconds after a successful attempt, assigns idle-delay `86400` seconds after any handled request/parsing error, rewrites the cache JSON after every attempted API call, emits version status only when latest and installed versions differ, and emits error messages for request/parsing failures. Complexity: O(1). Side effects: network I/O, cache-file rewrite, stdout/stderr output.
- @param force {bool} Bypass flag that forces a network request even when the cache idle-time is still active.
- @return {None} No return value.
- @throws {OSError} Cache-file rewrite failure after a completed API attempt.
- @see _should_skip_version_check
- @see _write_version_cache
- @satisfies REQ-016, REQ-150, REQ-151

### fn `def _run_management(command: list[str]) -> int` `priv` (L175-188)

### fn `def main(argv: Sequence[str] | None = None) -> int` (L189-226)

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`PROGRAM`|var|pub|14||
|`OWNER`|var|pub|15||
|`REPOSITORY`|var|pub|16||
|`_management_help`|fn|priv|27-40|def _management_help() -> str|
|`_write_version_cache`|fn|priv|41-72|def _write_version_cache(idle_delay_seconds: int) -> None|
|`_should_skip_version_check`|fn|priv|73-100|def _should_skip_version_check(force: bool) -> bool|
|`_check_online_version`|fn|priv|101-174|def _check_online_version(force: bool) -> None|
|`_run_management`|fn|priv|175-188|def _run_management(command: list[str]) -> int|
|`main`|fn|pub|189-226|def main(argv: Sequence[str] | None = None) -> int|


---

# dng2jpg.py | Python | 12974L | 408 symbols | 32 imports | 271 comments
> Path: `src/dng2jpg/dng2jpg.py`

## Imports
```
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
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from shell_scripts.utils import (
import json
import subprocess  # noqa: S404
import exifread  # type: ignore
import rawpy  # type: ignore
import imageio.v3 as imageio  # type: ignore
import imageio  # type: ignore
from PIL import Image as pil_image  # type: ignore
from skimage import color as skimage_color_module  # type: ignore
from skimage import color as skimage_color_module  # type: ignore
import numpy as np_module  # type: ignore
from numpy.lib.stride_tricks import sliding_window_view  # type: ignore
from numpy.lib.stride_tricks import sliding_window_view  # type: ignore
import cv2  # type: ignore
import numpy as numpy_module  # type: ignore
import numpy as numpy_module  # type: ignore
import piexif  # type: ignore
import numpy as np_module  # type: ignore
import numpy as np_module  # type: ignore
```

## Definitions

- var `PROGRAM = "dng2jpg"` (L39)
- var `DESCRIPTION = (` (L40)
- var `DEFAULT_POST_GAMMA = 1.0` (L43)
- var `DEFAULT_POST_GAMMA_MODE = "numeric"` (L44)
- var `DEFAULT_POST_GAMMA_AUTO_TARGET_GRAY = 0.5` (L45)
- var `DEFAULT_POST_GAMMA_AUTO_LUMA_MIN = 0.01` (L46)
- var `DEFAULT_POST_GAMMA_AUTO_LUMA_MAX = 0.99` (L47)
- var `DEFAULT_POST_GAMMA_AUTO_LUT_SIZE = 256` (L48)
- var `DEFAULT_BRIGHTNESS = 1.0` (L49)
- var `DEFAULT_CONTRAST = 1.0` (L50)
- var `DEFAULT_SATURATION = 1.0` (L51)
- var `DEFAULT_JPG_COMPRESSION = 15` (L52)
- var `DEFAULT_AUTO_EV_SHADOW_CLIPPING = 20.0` (L53)
- var `DEFAULT_AUTO_EV_HIGHLIGHT_CLIPPING = 20.0` (L54)
- var `DEFAULT_AUTO_EV_STEP = 0.1` (L55)
- var `DEFAULT_AA_BLUR_SIGMA = 0.9` (L56)
- var `DEFAULT_AA_BLUR_THRESHOLD_PCT = 5.0` (L57)
- var `DEFAULT_AA_LEVEL_LOW_PCT = 0.1` (L58)
- var `DEFAULT_AA_LEVEL_HIGH_PCT = 99.9` (L59)
- var `DEFAULT_AA_ENABLE_LOCAL_CONTRAST = True` (L60)
- var `DEFAULT_AA_LOCAL_CONTRAST_STRENGTH = 0.20` (L61)
- var `DEFAULT_AA_CLAHE_CLIP_LIMIT = 1.6` (L62)
- var `DEFAULT_AA_CLAHE_TILE_GRID_SIZE = (8, 8)` (L63)
- var `DEFAULT_AA_SIGMOID_CONTRAST = 1.8` (L64)
- var `DEFAULT_AA_SIGMOID_MIDPOINT = 0.5` (L65)
- var `DEFAULT_AA_SATURATION_GAMMA = 0.8` (L66)
- var `DEFAULT_AA_HIGHPASS_BLUR_SIGMA = 2.0` (L67)
- var `DEFAULT_AB_KEY_VALUE = None` (L68)
- var `DEFAULT_AB_WHITE_POINT_PERCENTILE = 99.8` (L69)
- var `DEFAULT_AB_A_MIN = 0.045` (L70)
- var `DEFAULT_AB_A_MAX = 0.72` (L71)
- var `DEFAULT_AB_MAX_AUTO_BOOST_FACTOR = 1.25` (L72)
- var `DEFAULT_AB_ENABLE_LUMINANCE_PRESERVING_DESAT = True` (L73)
- var `DEFAULT_AB_EPS = 1e-6` (L74)
- var `DEFAULT_AB_LOW_KEY_VALUE = 0.09` (L75)
- var `DEFAULT_AB_NORMAL_KEY_VALUE = 0.18` (L76)
- var `DEFAULT_AB_HIGH_KEY_VALUE = 0.36` (L77)
- var `DEFAULT_AL_CLIP_PERCENT = 0.02` (L78)
- var `DEFAULT_AL_CLIP_OUT_OF_GAMUT = True` (L79)
- var `DEFAULT_AL_GAIN_THRESHOLD = 1.0` (L80)
- var `DEFAULT_AL_HISTCOMPR = 3` (L81)
- var `DEFAULT_LUMINANCE_HDR_MODEL = "debevec"` (L109)
- var `DEFAULT_LUMINANCE_HDR_WEIGHT = "flat"` (L110)
- var `DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE = "linear"` (L111)
- var `DEFAULT_LUMINANCE_TMO = "mantiuk08"` (L112)
- var `DEFAULT_AUTO_ADJUST_ENABLED = True` (L113)
- var `HDR_MERGE_MODE_LUMINANCE = "Luminace-HDR"` (L114)
- var `HDR_MERGE_MODE_OPENCV_MERGE = "OpenCV-Merge"` (L115)
- var `HDR_MERGE_MODE_OPENCV_TONEMAP = "OpenCV-Tonemap"` (L116)
- var `HDR_MERGE_MODE_HDR_PLUS = "HDR-Plus"` (L117)
- var `WHITE_BALANCE_MODE_SIMPLE = "Simple"` (L118)
- var `WHITE_BALANCE_MODE_GRAYWORLD = "GrayworldWB"` (L119)
- var `WHITE_BALANCE_MODE_IA = "IA"` (L120)
- var `WHITE_BALANCE_MODE_COLOR_CONSTANCY = "ColorConstancy"` (L121)
- var `WHITE_BALANCE_MODE_TTL = "TTL"` (L122)
- var `AUTO_WHITE_BALANCE_MODE_DISABLE = "disable"` (L123)
- var `WHITE_BALANCE_XPHOTO_DOMAIN_LINEAR = "linear"` (L124)
- var `WHITE_BALANCE_XPHOTO_DOMAIN_SRGB = "srgb"` (L125)
- var `WHITE_BALANCE_XPHOTO_DOMAIN_SOURCE_AUTO = "source-auto"` (L126)
- var `RAW_WHITE_BALANCE_MODE_GREEN = "GREEN"` (L127)
- var `RAW_WHITE_BALANCE_MODE_MAX = "MAX"` (L128)
- var `RAW_WHITE_BALANCE_MODE_MIN = "MIN"` (L129)
- var `RAW_WHITE_BALANCE_MODE_MEAN = "MEAN"` (L130)
- var `DEFAULT_RAW_WHITE_BALANCE_MODE = RAW_WHITE_BALANCE_MODE_MAX` (L131)
- var `DEFAULT_WHITE_BALANCE_XPHOTO_DOMAIN = WHITE_BALANCE_XPHOTO_DOMAIN_SOURCE_AUTO` (L132)
- var `WHITE_BALANCE_ANALYSIS_SOURCE_EV_ZERO = "ev-zero"` (L133)
- var `WHITE_BALANCE_ANALYSIS_SOURCE_LINEAR_BASE = "linear-base"` (L134)
- var `OPENCV_TONEMAP_MAP_DRAGO = "drago"` (L135)
- var `OPENCV_TONEMAP_MAP_REINHARD = "reinhard"` (L136)
- var `OPENCV_TONEMAP_MAP_MANTIUK = "mantiuk"` (L137)
- var `OPENCV_MERGE_ALGORITHM_DEBEVEC = "Debevec"` (L138)
- var `OPENCV_MERGE_ALGORITHM_ROBERTSON = "Robertson"` (L139)
- var `OPENCV_MERGE_ALGORITHM_MERTENS = "Mertens"` (L140)
- var `DEFAULT_REINHARD02_POST_GAMMA = 0.9` (L141)
- var `DEFAULT_REINHARD02_BRIGHTNESS = 1.3` (L142)
- var `DEFAULT_REINHARD02_CONTRAST = 0.75` (L143)
- var `DEFAULT_REINHARD02_SATURATION = 0.7` (L144)
- var `DEFAULT_MANTIUK08_POST_GAMMA = 0.8` (L145)
- var `DEFAULT_MANTIUK08_BRIGHTNESS = 0.8` (L146)
- var `DEFAULT_MANTIUK08_CONTRAST = 1.1` (L147)
- var `DEFAULT_MANTIUK08_SATURATION = 1.05` (L148)
- var `DEFAULT_HDRPLUS_POST_GAMMA = 0.8` (L149)
- var `DEFAULT_HDRPLUS_BRIGHTNESS = 0.9` (L150)
- var `DEFAULT_HDRPLUS_CONTRAST = 1.0` (L151)
- var `DEFAULT_HDRPLUS_SATURATION = 1.0` (L152)
- var `DEFAULT_OPENCV_DEBEVEC_POST_GAMMA = 1.0` (L153)
- var `DEFAULT_OPENCV_DEBEVEC_BRIGHTNESS = 1.0` (L154)
- var `DEFAULT_OPENCV_DEBEVEC_CONTRAST = 1.5` (L155)
- var `DEFAULT_OPENCV_DEBEVEC_SATURATION = 1.05` (L156)
- var `DEFAULT_OPENCV_DEBEVEC_TONEMAP_GAMMA = 1.0` (L157)
- var `DEFAULT_OPENCV_ROBERTSON_POST_GAMMA = 1.0` (L158)
- var `DEFAULT_OPENCV_ROBERTSON_BRIGHTNESS = 1.0` (L159)
- var `DEFAULT_OPENCV_ROBERTSON_CONTRAST = 1.4` (L160)
- var `DEFAULT_OPENCV_ROBERTSON_SATURATION = 1.05` (L161)
- var `DEFAULT_OPENCV_ROBERTSON_TONEMAP_GAMMA = 0.9` (L162)
- var `DEFAULT_OPENCV_MERTENS_POST_GAMMA = 1.0` (L163)
- var `DEFAULT_OPENCV_MERTENS_BRIGHTNESS = 0.9` (L164)
- var `DEFAULT_OPENCV_MERTENS_CONTRAST = 1.3` (L165)
- var `DEFAULT_OPENCV_MERTENS_SATURATION = 1.1` (L166)
- var `DEFAULT_OPENCV_MERTENS_TONEMAP_GAMMA = 0.8` (L167)
- var `DEFAULT_OPENCV_POST_GAMMA = DEFAULT_OPENCV_ROBERTSON_POST_GAMMA` (L168)
- var `DEFAULT_OPENCV_BRIGHTNESS = DEFAULT_OPENCV_ROBERTSON_BRIGHTNESS` (L169)
- var `DEFAULT_OPENCV_CONTRAST = DEFAULT_OPENCV_ROBERTSON_CONTRAST` (L170)
- var `DEFAULT_OPENCV_SATURATION = DEFAULT_OPENCV_ROBERTSON_SATURATION` (L171)
- var `DEFAULT_OPENCV_MERGE_ALGORITHM = OPENCV_MERGE_ALGORITHM_ROBERTSON` (L172)
- var `DEFAULT_OPENCV_TONEMAP_ENABLED = True` (L173)
- var `DEFAULT_OPENCV_TONEMAP_GAMMA = DEFAULT_OPENCV_ROBERTSON_TONEMAP_GAMMA` (L174)
- var `DEFAULT_OPENCV_TONEMAP_DRAGO_SATURATION = 1.0` (L175)
- var `DEFAULT_OPENCV_TONEMAP_DRAGO_BIAS = 0.85` (L176)
- var `DEFAULT_OPENCV_TONEMAP_REINHARD_INTENSITY = 0.0` (L177)
- var `DEFAULT_OPENCV_TONEMAP_REINHARD_LIGHT_ADAPT = 0.0` (L178)
- var `DEFAULT_OPENCV_TONEMAP_REINHARD_COLOR_ADAPT = 0.0` (L179)
- var `DEFAULT_OPENCV_TONEMAP_MANTIUK_SCALE = 0.7` (L180)
- var `DEFAULT_OPENCV_TONEMAP_MANTIUK_SATURATION = 1.0` (L181)
- var `DEFAULT_HDRPLUS_PROXY_MODE = "rggb"` (L182)
- var `DEFAULT_HDRPLUS_SEARCH_RADIUS = 4` (L183)
- var `DEFAULT_HDRPLUS_TEMPORAL_FACTOR = 8.0` (L184)
- var `DEFAULT_HDRPLUS_TEMPORAL_MIN_DIST = 10.0` (L185)
- var `DEFAULT_HDRPLUS_TEMPORAL_MAX_DIST = 300.0` (L186)
- var `HDRPLUS_TILE_SIZE = 32` (L187)
- var `HDRPLUS_TILE_STRIDE = HDRPLUS_TILE_SIZE // 2` (L188)
- var `HDRPLUS_DOWNSAMPLED_TILE_SIZE = HDRPLUS_TILE_STRIDE` (L189)
- var `HDRPLUS_ALIGNMENT_LEVELS = 3` (L190)
- var `HDRPLUS_ALIGNMENT_DOWNSAMPLE_RATE = 4` (L191)
- var `HDRPLUS_TEMPORAL_FACTOR = DEFAULT_HDRPLUS_TEMPORAL_FACTOR` (L192)
- var `HDRPLUS_TEMPORAL_MIN_DIST = DEFAULT_HDRPLUS_TEMPORAL_MIN_DIST` (L193)
- var `HDRPLUS_TEMPORAL_MAX_DIST = DEFAULT_HDRPLUS_TEMPORAL_MAX_DIST` (L194)
- var `MIN_SUPPORTED_BITS_PER_COLOR = 9` (L196)
### class `class AutoAdjustOptions` `@dataclass(frozen=True)` (L461-496)
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

### class `class AutoBrightnessOptions` `@dataclass(frozen=True)` (L498-526)
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

### class `class AutoLevelsOptions` `@dataclass(frozen=True)` (L528-551)
- @brief Hold `--auto-levels` knob values.
- @details Encapsulates validated histogram-based auto-levels controls ported from the attached RawTherapee-oriented source and adapted for normalized RGB float stage execution in the current post-merge pipeline.
- @param clip_percent {float} Histogram clipping percentage in `[0, +inf)`.
- @param clip_out_of_gamut {bool} `True` to normalize overflowing RGB triplets back into normalized gamut after tonal transform/reconstruction.
- @param histcompr {int} Histogram compression shift in `[0, 15]`.
- @param highlight_reconstruction_enabled {bool} `True` when highlight reconstruction is explicitly enabled.
- @param highlight_reconstruction_method {str} Highlight reconstruction method selector.
- @param gain_threshold {float} Inpaint Opposed gain threshold in `(0, +inf)`.
- @return {None} Immutable dataclass container.
- @satisfies REQ-100, REQ-101, REQ-102, REQ-116, REQ-120, REQ-165

### class `class PostGammaAutoOptions` `@dataclass(frozen=True)` (L553-571)
- @brief Hold `--post-gamma=auto` knob values.
- @details Encapsulates mean-luminance anchoring controls for the dedicated auto-gamma replacement stage in static postprocess execution.
- @param target_gray {float} Mid-gray anchor target in `(0,1)`.
- @param luma_min {float} Lower luminance guard in `(0,1)` for gamma solving.
- @param luma_max {float} Upper luminance guard in `(0,1)` for gamma solving.
- @param lut_size {int} Floating-point LUT size (`>=2`) for gamma mapping.
- @return {None} Immutable dataclass container.
- @satisfies REQ-177, REQ-179

### class `class MergeGammaOption` `@dataclass(frozen=True)` (L573-591)
- @brief Hold requested merge-gamma CLI selector state.
- @details Encodes the user-facing `--gamma` request independently from the backend-resolved transfer so parsing stays deterministic and runtime can emit exact request diagnostics. `mode="auto"` selects EXIF/source-driven resolution. `mode="custom"` requires both custom parameters.
- @param mode {str} Canonical selector in `{"auto","custom"}`.
- @param linear_coeff {float|None} Custom linear-segment coefficient for Rec.709-style transfer.
- @param exponent {float|None} Custom exponent for Rec.709-style transfer.
- @return {None} Immutable dataclass container.
- @satisfies REQ-020

### class `class ResolvedMergeGamma` `@dataclass(frozen=True)` (L593-618)
- @brief Hold one resolved merge-output transfer function payload.
- @details Captures the backend-local transfer applied after OpenCV/HDR+ merge normalization. `transfer` selects one implementation family: `linear`, `srgb`, `power`, or `rec709`. `param_a` and `param_b` carry transfer-specific numeric parameters for deterministic diagnostics and backend execution.
- @param request {MergeGammaOption} Original parsed user selector.
- @param transfer {str} Resolved transfer family identifier.
- @param label {str} Deterministic human-readable transfer label.
- @param param_a {float|None} First resolved transfer parameter when required.
- @param param_b {float|None} Second resolved transfer parameter when required.
- @param evidence {str} Resolution evidence token.
- @return {None} Immutable dataclass container.
- @satisfies REQ-169, REQ-170, REQ-171

### class `class ExifGammaTags` `@dataclass(frozen=True)` (L620-641)
- @brief Hold EXIF tags relevant to auto merge-gamma resolution.
- @details Encapsulates normalized EXIF color-space, interoperability, image-model, and image-make tokens extracted from the source RAW/DNG container via `exifread` binary stream processing. The payload is consumed only by merge-gamma resolution and diagnostics and never mutates bracket extraction.
- @param color_space {str|None} Normalized EXIF `ColorSpace` token.
- @param interoperability_index {str|None} Normalized EXIF interoperability token.
- @param image_model {str|None} Normalized EXIF `Image Model` token.
- @param image_make {str|None} Normalized EXIF `Image Make` token.
- @return {None} Immutable dataclass container.
- @satisfies REQ-169, REQ-172, REQ-173

### class `class OpenCvTonemapOptions` `@dataclass(frozen=True)` (L643-672)
- @brief Hold deterministic OpenCV-Tonemap backend option values.
- @details Encapsulates one mandatory OpenCV tone-map algorithm selector and optional algorithm-specific parameters for the `--hdr-merge=OpenCV-Tonemap` backend. The backend executes one selected algorithm only, resolves OpenCV tone-map gamma as the inverse of the resolved merge-gamma curve parameter, and applies merge gamma only as the backend-final step.
- @param tonemap_map {str} Selected OpenCV tone-map algorithm in `{"drago","reinhard","mantiuk"}`.
- @param drago_saturation {float} Drago saturation parameter.
- @param drago_bias {float} Drago bias parameter.
- @param reinhard_intensity {float} Reinhard intensity parameter.
- @param reinhard_light_adapt {float} Reinhard light adaptation parameter in `[0,1]`.
- @param reinhard_color_adapt {float} Reinhard color adaptation parameter in `[0,1]`.
- @param mantiuk_scale {float} Mantiuk scale parameter.
- @param mantiuk_saturation {float} Mantiuk saturation parameter.
- @return {None} Immutable dataclass container.
- @satisfies REQ-190, REQ-193, REQ-194, REQ-195, REQ-196, REQ-198

### class `class PostprocessOptions` `@dataclass(frozen=True)` (L674-772)
- @brief Hold deterministic postprocessing option values.
- @details Encapsulates correction factors and JPEG compression level used by shared TIFF-to-JPG postprocessing for both HDR backends, including `--post-gamma=auto` replacement-stage controls.
- @param post_gamma {float} Numeric gamma correction factor for static numeric mode.
- @param post_gamma_mode {str} Static gamma selector in `{"numeric","auto"}`.
- @param post_gamma_auto_options {PostGammaAutoOptions} Auto-gamma replacement stage knobs.
- @param brightness {float} Brightness enhancement factor.
- @param contrast {float} Contrast enhancement factor.
- @param saturation {float} Saturation enhancement factor.
- @param jpg_compression {int} JPEG compression level in range `[0, 100]`.
- @param auto_brightness_enabled {bool} `True` when the pre-bracketing auto-brightness stage is enabled.
- @param auto_brightness_pre_applied {bool} `True` when auto-brightness already executed before `_postprocess(...)` and must be skipped inside post-merge processing.
- @param auto_brightness_options {AutoBrightnessOptions} Auto-brightness stage knobs.
- @param auto_levels_enabled {bool} `True` when auto-levels stage is enabled.
- @param auto_levels_options {AutoLevelsOptions} Auto-levels stage knobs.
- @param auto_adjust_enabled {bool} `True` when the auto-adjust stage is enabled.
- @param auto_adjust_options {AutoAdjustOptions} Knobs for the sole auto-adjust implementation.
- @param debug_enabled {bool} `True` when persistent debug TIFF checkpoints are enabled.
- @param merge_gamma_option {MergeGammaOption} Parsed merge-gamma request applied only by OpenCV and HDR+ backends.
- @param raw_white_balance_mode {str} RAW camera WB normalization mode in `{"GREEN","MAX","MIN","MEAN"}`.
- @param white_balance_mode {str|None} Optional `--auto-white-balance` mode applied to the linear base image after auto-brightness and before auto-zero evaluation.
- @param auto_white_balance_pre_applied {bool} `True` when auto-white-balance already executed before `_postprocess(...)` and must be skipped inside post-merge processing.
- @param white_balance_analysis_source {str} `--white-balance-analysis-source` selector for auto-white-balance analysis payload in `{"ev-zero","linear-base"}`.
- @param white_balance_xphoto_domain {str} Xphoto estimation-domain selector in `{"linear","srgb","source-auto"}` applied only to xphoto gain estimation.
- @param opencv_tonemap_options {OpenCvTonemapOptions|None} Optional OpenCV-Tonemap backend selector and knob payload.
- @return {None} Immutable dataclass container.
- @satisfies REQ-020, REQ-050, REQ-065, REQ-066, REQ-069, REQ-071, REQ-072, REQ-073, REQ-075, REQ-082, REQ-083, REQ-084, REQ-086, REQ-087, REQ-088, REQ-089, REQ-090, REQ-100, REQ-101, REQ-102, REQ-103, REQ-104, REQ-105, REQ-146, REQ-176, REQ-179, REQ-181, REQ-182, REQ-190, REQ-194, REQ-195, REQ-196, REQ-199, REQ-203, REQ-210
- fn `def auto_white_balance_mode(self) -> str | None` (L734-745)
  - @brief Expose optional `--auto-white-balance` mode with explicit naming.
  - @details Provides a semantically explicit alias for `white_balance_mode` to distinguish auto-white-balance stage control from RAW camera white-balance normalization (`--white-balance`).
  - @return {str|None} Canonical auto-white-balance mode or `None` when omitted.
  - @satisfies REQ-181, REQ-182
- fn `def auto_white_balance_analysis_source(self) -> str` (L747-758)
  - @brief Expose `--white-balance-analysis-source` with explicit auto-stage naming.
  - @details Provides a semantically explicit alias for `white_balance_analysis_source` to make auto-white-balance stage payload selection unambiguous in runtime orchestration code.
  - @return {str} Canonical auto-white-balance analysis-source selector.
  - @satisfies REQ-199, REQ-200
- fn `def auto_white_balance_xphoto_domain(self) -> str` (L760-772)
  - @brief Expose xphoto estimation-domain selector with explicit auto-stage naming.
  - @details Provides a semantically explicit alias for `white_balance_xphoto_domain` so runtime orchestration can pass the selector only to xphoto gain estimation.
  - @return {str} Canonical auto-white-balance xphoto estimation-domain selector.
  - @satisfies REQ-210, REQ-212

### class `class DebugArtifactContext` `@dataclass(frozen=True)` (L774-790)
- @brief Hold persistent debug-checkpoint output metadata.
- @details Stores the source input stem and destination directory used to emit debug TIFF checkpoints outside the temporary workspace. The suffix counter remains external so orchestration can map checkpoints to exact pipeline stages in execution order.
- @param output_dir {Path} Destination directory for persistent debug TIFF files.
- @param input_stem {str} Source DNG stem used as the filename prefix.
- @return {None} Immutable debug output metadata container.
- @satisfies DES-009, REQ-146, REQ-147, REQ-149

### class `class SourceGammaInfo` `@dataclass(frozen=True)` (L792-810)
- @brief Hold one source-gamma diagnostic payload derived from RAW metadata.
- @details Encapsulates one deterministic runtime diagnostic resolved from RAW metadata only. The payload is observational and MUST NOT participate in HDR bracket extraction, HDR merge dispatch, or static postprocess state resolution.
- @param label {str} Deterministic source-gamma classification label.
- @param gamma_value {float|None} Numeric gamma value when derivable; `None` when metadata cannot resolve one.
- @param evidence {str} Metadata field or hint bundle used to classify the label.
- @return {None} Immutable dataclass container.
- @satisfies REQ-157, REQ-163, REQ-164

### class `class LuminanceOptions` `@dataclass(frozen=True)` (L812-833)
- @brief Hold deterministic luminance-hdr-cli option values.
- @details Encapsulates luminance backend model and tone-mapping parameters forwarded to `luminance-hdr-cli` command generation. The response-curve payload is constrained to the repository linear HDR bracket contract.
- @param hdr_model {str} Luminance HDR model (`--hdrModel`).
- @param hdr_weight {str} Luminance weighting function (`--hdrWeight`).
- @param hdr_response_curve {str} Luminance response curve (`--hdrResponseCurve`).
- @param tmo {str} Tone-mapping operator (`--tmo`).
- @param tmo_extra_args {tuple[str, ...]} Explicit passthrough `--tmo*` option pairs in CLI order.
- @return {None} Immutable dataclass container.
- @satisfies REQ-061, REQ-067, REQ-068

### class `class OpenCvMergeOptions` `@dataclass(frozen=True)` (L835-855)
- @brief Hold deterministic OpenCV HDR merge option values.
- @details Encapsulates OpenCV merge controls used by the `--hdr-merge=OpenCV-Merge` backend. Debevec and Robertson linearize the extracted float brackets and execute `Merge* -> Tonemap` on backend-local radiance payloads, Mertens executes exposure fusion on float brackets with OpenCV-equivalent output rescaling plus optional simple tonemap, and all external interfaces stay RGB float `[0,1]`.
- @param merge_algorithm {str} Canonical OpenCV merge algorithm in `{"Debevec","Robertson","Mertens"}`.
- @param tonemap_enabled {bool} `True` enables simple OpenCV gamma tone mapping for Debevec/Robertson/Mertens outputs.
- @param tonemap_gamma {float} Positive gamma value passed to `cv2.createTonemap`; parser defaults are algorithm-specific (`Debevec=1.0`, `Robertson=0.9`, `Mertens=0.8`).
- @return {None} Immutable dataclass container.
- @satisfies REQ-108, REQ-109, REQ-110, REQ-141, REQ-142, REQ-143, REQ-144, REQ-152, REQ-153, REQ-154

### class `class HdrPlusOptions` `@dataclass(frozen=True)` (L857-880)
- @brief Hold deterministic HDR+ merge option values.
- @details Encapsulates the user-facing RGB-to-scalar proxy selection, hierarchical alignment search radius, and temporal weight controls used by the HDR+ backend port. Temporal values remain expressed in the historical 16-bit code-domain units so CLI defaults, parsing, and runtime diagnostics stay unchanged while normalized float32 runtime controls are derived later.
- @param proxy_mode {str} Scalar proxy mode selector in `{"rggb","bt709","mean"}`.
- @param search_radius {int} Per-layer alignment search radius in pixels; candidate offsets span `[-search_radius, search_radius-1]`.
- @param temporal_factor {float} User-facing denominator stretch factor defined on historical 16-bit code-domain tile L1 distance.
- @param temporal_min_dist {float} User-facing distance floor defined on historical 16-bit code-domain tile L1 distance.
- @param temporal_max_dist {float} User-facing distance ceiling defined on historical 16-bit code-domain tile L1 distance.
- @return {None} Immutable dataclass container.
- @satisfies REQ-126, REQ-127, REQ-128, REQ-130, REQ-131, REQ-138

### class `class HdrPlusTemporalRuntimeOptions` `@dataclass(frozen=True)` (L882-901)
- @brief Hold HDR+ temporal controls remapped for normalized distance inputs.
- @details Converts user-facing temporal CLI values into runtime controls consumed by normalized float32 `[0,1]` tile L1 distances. The denominator stretch factor and distance floor are scaled from the historical 16-bit code-domain units, while the cutoff remains stored in the post-normalized comparison space so the existing weight curve stays numerically equivalent.
- @param distance_factor {float} Normalized-distance denominator stretch factor.
- @param min_distance {float} Normalized-distance floor before inverse-distance attenuation starts.
- @param max_weight_distance {float} Dimensionless cutoff threshold applied after normalization.
- @return {None} Immutable dataclass container.
- @satisfies REQ-114, REQ-131, REQ-138

### class `class JointAutoEvSolution` `@dataclass(frozen=True)` (L903-923)
- @brief Hold one resolved automatic exposure plan.
- @details Stores the selected `ev_zero`, the selected symmetric bracket half-span `ev_delta`, the heuristic name that supplied `ev_zero`, and the full ordered iteration trace used to stop bracket expansion. Side effects: none.
- @param ev_zero {float} Selected central EV value.
- @param ev_delta {float} Selected symmetric bracket half-span.
- @param selected_source {str} Heuristic label chosen for `ev_zero`.
- @param iteration_steps {tuple[AutoEvIterationStep, ...]} Ordered clipping-evaluation steps from iterative bracket expansion.
- @return {None} Immutable automatic exposure plan container.
- @satisfies REQ-008, REQ-009, REQ-032, REQ-052, REQ-167, REQ-168

### class `class AutoEvIterationStep` `@dataclass(frozen=True)` (L925-942)
- @brief Hold one iterative bracket-evaluation step.
- @details Stores one tested `ev_delta` together with the measured shadow and highlight clipping percentages derived from unclipped bracket images at `ev_zero-ev_delta` and `ev_zero+ev_delta`. Side effects: none.
- @param ev_delta {float} Tested symmetric bracket half-span.
- @param shadow_clipping_pct {float} Percentage of minus-image pixels with any channel `<=0`.
- @param highlight_clipping_pct {float} Percentage of plus-image pixels with any channel `>=1`.
- @return {None} Immutable bracket-step container.
- @satisfies REQ-167, REQ-168

### class `class AutoEvOptions` `@dataclass(frozen=True)` (L944-961)
- @brief Hold automatic exposure bracket-search controls.
- @details Encapsulates the iterative bracket-search thresholds and step size used by automatic exposure planning. Thresholds are expressed as percentages in `0..100`; step is a positive EV increment. Side effects: none.
- @param shadow_clipping_pct {float} Shadow clipping stop threshold in percent.
- @param highlight_clipping_pct {float} Highlight clipping stop threshold in percent.
- @param step {float} Positive EV increment used by iterative bracket expansion.
- @return {None} Immutable automatic exposure option container.
- @satisfies REQ-019, REQ-166, REQ-167

### class `class AutoZeroEvaluation` `@dataclass(frozen=True)` (L963-981)
- @brief Hold the three exposure-measure EV evaluations.
- @details Stores the entropy-optimized candidate (`ev_best`), the ETTR candidate (`ev_ettr`), and the detail-preservation candidate (`ev_detail`) computed from one normalized linear RGB float image. Values are rounded to one decimal place before downstream selection.
- @param ev_best {float} Entropy-optimized EV candidate.
- @param ev_ettr {float} ETTR EV candidate.
- @param ev_detail {float} Detail-preservation EV candidate.
- @return {None} Immutable center-heuristic evaluation container.
- @satisfies REQ-008, REQ-032, REQ-052

### fn `def _print_box_table(headers, rows, header_rows=())` `priv` (L982-1018)
- @brief Print one Unicode box-drawing table.
- @details Computes deterministic column widths from headers and rows, then prints aligned borders and cells using Unicode line-drawing glyphs.
- @param headers {tuple[str, ...]} Table header labels in fixed output order.
- @param header_rows {tuple[tuple[str, ...], ...]} Additional physical header rows rendered before header/body separator.
- @param rows {tuple[tuple[str, ...], ...]} Table body rows with one value per column.
- @return {None} Writes formatted table to stdout.
- @satisfies REQ-070

### fn `def _border(left, middle, right)` `priv` (L1002-1004)
- @brief Print one Unicode box-drawing table.
- @details Computes deterministic column widths from headers and rows, then
prints aligned borders and cells using Unicode line-drawing glyphs.
- @param headers {tuple[str, ...]} Table header labels in fixed output order.
- @param header_rows {tuple[tuple[str, ...], ...]} Additional physical header rows rendered before header/body separator.
- @param rows {tuple[tuple[str, ...], ...]} Table body rows with one value per column.
- @return {None} Writes formatted table to stdout.
- @satisfies REQ-070

### fn `def _line(values)` `priv` (L1005-1008)

### fn `def _build_two_line_operator_rows(operator_entries)` `priv` (L1019-1035)
- @brief Build two-line physical rows for luminance operator table.
- @details Expands each logical operator entry into two physical rows while preserving the bordered three-column layout used by help rendering.
- @param operator_entries {tuple[tuple[str, str, str, str, str], ...]} Logical operator rows in `(operator, family, character, neutrality, when_to_use)` format.
- @return {tuple[tuple[str, str, str], ...]} Expanded physical rows for `_print_box_table`.
- @satisfies REQ-070

### fn `def _print_help_section(title)` `priv` (L1036-1050)
- @brief Print one numbered help section title.
- @details Emits one blank separator line followed by one deterministic section title so conversion help stays ordered by pipeline execution step. Complexity: O(1). Side effects: stdout writes only.
- @param title {str} Section title text already normalized for display order.
- @return {None} Writes formatted section title to stdout.
- @satisfies REQ-017, REQ-155

### fn `def _print_help_option(option_label, description, detail_lines=())` `priv` (L1051-1092)
- @brief Print one aligned conversion-help option block.
- @details Renders one option label and wrapped description using a fixed indentation grid, then renders any continuation detail lines under the same description column. Complexity: O(n) in total output characters. Side effects: stdout writes only.
- @param option_label {str} Left-column option label or positional argument label.
- @param description {str} Primary description line for the option block.
- @param detail_lines {tuple[str, ...]|list[str]} Additional wrapped lines aligned under the description column.
- @return {None} Writes formatted option block to stdout.
- @satisfies REQ-017, REQ-155, REQ-156

### fn `def print_help(version)` (L1093-1292)
- @brief Print help text for the `dng2jpg` command.
- @details Renders conversion help in pipeline execution order. Groups each processing stage with the selectors and knobs that configure that stage, documents allowed values and activation conditions for every accepted conversion option, and prints effective omitted-value defaults using aligned indentation and stable table formatting. Complexity: O(n) in emitted characters. Side effects: stdout writes only.
- @param version {str} CLI version label to append in usage output.
- @return {None} Writes help text to stdout.
- @satisfies DES-008, REQ-017, REQ-018, REQ-019, REQ-020, REQ-021, REQ-022, REQ-023, REQ-024, REQ-025, REQ-033, REQ-100, REQ-101, REQ-102, REQ-107, REQ-111, REQ-124, REQ-125, REQ-127, REQ-128, REQ-135, REQ-141, REQ-143, REQ-146, REQ-155, REQ-156, REQ-176, REQ-179, REQ-181, REQ-182, REQ-189, REQ-190, REQ-194, REQ-195, REQ-196, REQ-203

### fn `def _validate_supported_bits_per_color(bits_per_color)` `priv` (L1547-1564)
- @brief Validate supported minimum DNG bits-per-color contract.
- @details Enforces repository minimum bit-depth support independently from exposure range planning and raises deterministic failure when source DNG metadata exposes a lower precision container.
- @param bits_per_color {int} Detected source DNG bits per color.
- @return {None} Validation completion without payload.
- @exception ValueError Raised when bit depth is below supported minimum.
- @satisfies REQ-027

### fn `def _detect_dng_bits_per_color(raw_handle)` `priv` (L1565-1610)
- @brief Detect source DNG bits-per-color from RAW metadata.
- @details Prefers RAW sample container bit depth from `raw_handle.raw_image_visible.dtype.itemsize * 8` because the DNG white level can represent effective sensor range (for example `4000`) while RAW samples are still stored in a wider container (for example `uint16`). Falls back to `raw_handle.white_level` `bit_length` when container metadata is unavailable.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {int} Detected source DNG bits per color.
- @exception ValueError Raised when metadata is missing, non-numeric, or non-positive.
- @satisfies REQ-026, REQ-027

### fn `def _is_ev_value_on_supported_step(ev_value)` `priv` (L1611-1623)
- @brief Validate EV value is a finite numeric scalar.
- @details Performs finite-number validation only. Step-based validation was removed from manual exposure planning.
- @param ev_value {float} Parsed EV numeric value.
- @return {bool} `True` when EV value is finite.
- @satisfies REQ-030

### fn `def _parse_ev_option(ev_raw)` `priv` (L1624-1650)
- @brief Parse and validate one `--bracketing` static value.
- @details Converts token to `float`, enforces finiteness and non-negativity, and preserves the parsed static bracket half-span without applying any bit-depth-derived upper-bound contract. Does not handle the `auto` sentinel; callers MUST check for `auto` before invoking this function.
- @param ev_raw {str} EV token extracted from command arguments.
- @return {float|None} Parsed EV value when valid; `None` otherwise.
- @satisfies REQ-030, CTN-003

### fn `def _parse_ev_center_option(ev_center_raw)` `priv` (L1651-1677)
- @brief Parse and validate one `--exposure` center option value.
- @details Converts token to `float`, enforces finiteness, and preserves static center EV value without applying bit-depth-derived upper bounds. Does not handle the `auto` sentinel; callers MUST check for `auto` before invoking this function.
- @param ev_center_raw {str} EV-center token extracted from command arguments.
- @return {float|None} Parsed EV-center value when valid; `None` otherwise.
- @satisfies REQ-030, CTN-007

### fn `def _parse_percentage_option(option_name, option_raw)` `priv` (L1678-1700)
- @brief Parse and validate one percentage option value.
- @details Converts option token to `float`, requires inclusive range `[0, 100]`, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {float|None} Parsed percentage value when valid; `None` otherwise.
- @satisfies REQ-019, REQ-030

### fn `def _parse_auto_brightness_option(auto_brightness_raw)` `priv` (L1701-1720)
- @brief Parse and validate one `--auto-brightness` option value.
- @details Accepts only explicit enable/disable tokens to keep deterministic toggle behavior for stage activation.
- @param auto_brightness_raw {str} Raw `--auto-brightness` value token from CLI args.
- @return {bool|None} Parsed enable-state value; `None` on parse failure.
- @satisfies REQ-065, REQ-089

### fn `def _parse_auto_levels_option(auto_levels_raw)` `priv` (L1721-1740)
- @brief Parse and validate one `--auto-levels` option value.
- @details Accepts only explicit enable/disable tokens to keep deterministic toggle behavior for stage activation.
- @param auto_levels_raw {str} Raw `--auto-levels` value token from CLI args.
- @return {bool|None} Parsed enable-state value; `None` on parse failure.
- @satisfies REQ-100, REQ-101

### fn `def _parse_explicit_boolean_option(option_name, option_raw)` `priv` (L1741-1761)
- @brief Parse one explicit boolean option value.
- @details Accepts canonical true/false token families to keep deterministic toggle parsing for CLI knobs that support both enabling and disabling.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {bool|None} Parsed boolean value; `None` on parse failure.
- @satisfies REQ-101

### fn `def _parse_opencv_merge_algorithm_option(algorithm_raw)` `priv` (L1762-1786)
- @brief Parse OpenCV merge algorithm selector.
- @details Accepts case-insensitive OpenCV algorithm names, normalizes them to canonical runtime tokens, and rejects unsupported values with deterministic diagnostics.
- @param algorithm_raw {str} Raw `--opencv-merge-algorithm` selector token.
- @return {str|None} Canonical OpenCV merge algorithm token or `None` on parse failure.
- @satisfies REQ-108, REQ-141

### fn `def _resolve_default_opencv_tonemap_gamma(merge_algorithm)` `priv` (L1787-1808)
- @brief Resolve OpenCV tone-map gamma default from merge algorithm.
- @details Maps `Debevec`, `Robertson`, and `Mertens` to deterministic default gamma values used when `--opencv-merge-tonemap-gamma` is omitted. Unknown values fall back to the repository default merge algorithm profile.
- @param merge_algorithm {str} Resolved OpenCV merge algorithm selector.
- @return {float} Default OpenCV tone-map gamma for the selected algorithm.
- @satisfies REQ-141, REQ-143

### fn `def _parse_opencv_merge_backend_options(opencv_raw_values)` `priv` (L1809-1861)
- @brief Parse and validate OpenCV HDR merge knob values.
- @details Applies OpenCV defaults for algorithm selector, tone-map toggle, and tone-map gamma, validates allowed values, and returns one immutable backend option container for downstream merge dispatch.
- @param opencv_raw_values {dict[str, str]} Raw `--opencv-*` option values keyed by long option name.
- @return {OpenCvMergeOptions|None} Parsed OpenCV merge options or `None` on validation error.
- @satisfies REQ-141, REQ-143

### fn `def _parse_opencv_tonemap_backend_options(` `priv` (L1862-1864)

### fn `def _extract_normalized_preview_luminance_stats(raw_handle)` `priv` (L2035-2094)
- @brief Parse and validate OpenCV-Tonemap backend selector and knobs.
- @brief Extract normalized preview luminance percentiles from RAW handle.
- @details Requires exactly one selector in
`--opencv-tonemap-algorithm=<drago|reinhard|mantiuk>`, applies
deterministic defaults
for optional algorithm-specific knobs, and rejects knobs that do not belong
to the selected algorithm.
- @details Generates one deterministic linear preview (`bright=1.0`, `output_bps=16`, camera white balance, no auto-bright, linear gamma, `user_flip=0`), computes luminance for each pixel, then returns normalized low/median/high percentiles by dividing with preview maximum luminance.
- @param tonemap_selector_options {list[str]} Ordered list of selected OpenCV-Tonemap selector tokens.
- @param tonemap_knob_raw_values {dict[str, str]} Raw `--opencv-tonemap-*` knob payloads keyed by option name.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {OpenCvTonemapOptions|None} Parsed OpenCV-Tonemap options or `None` on validation failure.
- @return {tuple[float, float, float]} Normalized `(p_low, p_median, p_high)` in `(0,1)`.
- @exception ValueError Raised when preview extraction cannot produce valid luminance values.
- @satisfies REQ-190, REQ-194, REQ-195, REQ-196
- @satisfies REQ-009

### fn `def _percentile(percentile_value)` `priv` (L2069-2079)
- @brief Extract normalized preview luminance percentiles from RAW handle.
- @details Generates one deterministic linear preview (`bright=1.0`,
`output_bps=16`, camera white balance, no auto-bright, linear gamma,
`user_flip=0`), computes luminance for each pixel, then returns normalized
low/median/high percentiles by dividing with preview maximum luminance.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {tuple[float, float, float]} Normalized `(p_low, p_median, p_high)` in `(0,1)`.
- @exception ValueError Raised when preview extraction cannot produce valid luminance values.
- @satisfies REQ-009

### fn `def _extract_camera_whitebalance_rgb_triplet(raw_handle)` `priv` (L2095-2127)
- @brief Extract one `(R,G,B)` camera white-balance triplet from RAW metadata.
- @details Reads `rawpy` camera white-balance payload, validates finite positive coefficients, and returns the first three channels as one RGB triplet used for float-domain gain normalization. Falls back to unit triplet when metadata is missing or invalid. Complexity: O(1). Side effects: none.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {tuple[float, float, float]} Positive finite `(r, g, b)` coefficients.
- @satisfies REQ-031, REQ-158, REQ-183

### fn `def _format_rgb_triplet_fixed4(rgb_values)` `priv` (L2128-2157)
- @brief Format one RGB triplet for deterministic RAW WB diagnostics.
- @details Converts one iterable payload to exactly three finite float values and renders deterministic `R/G/B` fixed-point tokens with four fractional digits. Invalid or missing entries are replaced by `1.0000`. Complexity: O(1). Side effects: none.
- @param rgb_values {object} Iterable-like payload containing at least three channel coefficients.
- @return {str} Formatted token string `R=<value>, G=<value>, B=<value>`.
- @satisfies REQ-208, REQ-209

### fn `def _normalize_white_balance_gains_rgb(` `priv` (L2158-2161)

### fn `def _apply_normalized_white_balance_to_rgb_float(np_module, image_rgb_float, normalized_gains_rgb)` `priv` (L2208-2231)
- @brief Normalize one RAW camera WB gain triplet by selected mode.
- @brief Apply normalized RGB white-balance gains to one RGB float tensor.
- @details Converts one camera white-balance RGB triplet to float64 and
normalizes coefficients by one mode-specific divisor: `GREEN` uses the
green coefficient, `MAX` uses the triplet maximum,
`MIN` uses the triplet minimum, and `MEAN` uses the arithmetic mean.
Invalid vectors resolve to unit gains. Complexity: O(1). Side effects:
none.
- @details Broadcast-multiplies normalized RGB gains over one RGB float image in float64 precision and returns float32 without explicit clipping or range normalization, preserving headroom for downstream EV scaling and clipping stages. Complexity: O(H*W). Side effects: none.
- @param np_module {ModuleType} Imported numpy module.
- @param camera_wb_rgb {tuple[float, float, float]} Positive finite camera WB RGB triplet.
- @param raw_white_balance_mode {str} RAW WB normalization mode selector.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float tensor.
- @param normalized_gains_rgb {object} RGB normalized gain vector with shape `(3,)`.
- @return {object} Float64 RGB gain vector normalized by selected mode divisor.
- @return {object} White-balanced RGB float32 tensor without stage-local clipping.
- @exception ValueError Raised when the mode selector is unsupported.
- @satisfies REQ-031, REQ-158, REQ-183, REQ-203, REQ-204, REQ-205, REQ-206, REQ-207
- @satisfies REQ-031, REQ-158, REQ-183

### fn `def _build_rawpy_neutral_postprocess_kwargs(raw_handle)` `priv` (L2232-2272)
- @brief Build deterministic neutral `rawpy.postprocess` keyword arguments.
- @details Produces one neutral linear extraction payload with fixed fields (`gamma`, `no_auto_bright`, `output_bps`, `use_camera_wb`, `user_wb`, `output_color=rawpy.ColorSpace.raw`, `no_auto_scale`, `user_flip`) for deterministic RAW extraction without camera-WB application in postprocess. Complexity: O(1). Side effects: imports `rawpy` when module discovery from the handle does not expose `ColorSpace`.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {dict[str, object]} Keyword argument mapping for neutral RAW extraction.
- @exception RuntimeError Raised when `rawpy.ColorSpace.raw` cannot be resolved.
- @satisfies REQ-010

### fn `def _extract_sensor_dynamic_range_max(raw_handle, np_module)` `priv` (L2273-2330)
- @brief Compute one sensor dynamic-range normalization denominator.
- @details Reads RAW metadata `white_level` and `black_level_per_channel`, computes `dynamic_range_max = white_level - mean(black_level_per_channel)`, and validates a finite positive result for neutral RAW-base normalization. Falls back to `white_level` when black-level payload is unavailable or invalid. Complexity: O(C) where C is black-level channel count. Side effects: none.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @param np_module {ModuleType} Imported numpy module.
- @return {float} Positive finite dynamic-range denominator.
- @exception ValueError Raised when `white_level` metadata is missing or non-positive.
- @satisfies REQ-158

### fn `def _extract_base_rgb_linear_float(` `priv` (L2331-2334)

### fn `def _normalize_source_gamma_label(label_raw)` `priv` (L2381-2399)
- @brief Extract one linear normalized RGB base image from one RAW handle.
- @brief Normalize one source-gamma label token.
- @details Executes exactly one neutral linear `rawpy.postprocess` call with
deterministic no-auto/no-camera-WB parameters, converts output to float,
normalizes by sensor dynamic range `white_level - mean(black_level_per_channel)`,
extracts camera WB metadata gains, normalizes gains by one selected mode
(`GREEN`, `MAX`, `MIN`, `MEAN`), and applies those gains in float domain
without explicit clipping. Complexity: O(H*W). Side effects: one RAW
postprocess invocation.
- @details Trims surrounding whitespace, collapses empty values to `unknown`, and preserves the remaining token verbatim for deterministic runtime diagnostics.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @param np_module {ModuleType} Imported numpy module.
- @param raw_white_balance_mode {str} RAW WB normalization mode selector.
- @param label_raw {object} Candidate label payload derived from RAW metadata.
- @return {object} White-balanced RGB float tensor derived from neutral extraction.
- @return {str} Normalized diagnostic label.
- @see _extract_normalized_preview_luminance_stats
- @satisfies REQ-010, REQ-031, REQ-158, REQ-203, REQ-204, REQ-205, REQ-206, REQ-207, REQ-208, REQ-209
- @satisfies REQ-163, REQ-164

### fn `def _decode_raw_metadata_text(metadata_raw)` `priv` (L2400-2431)
- @brief Decode one RAW metadata token to deterministic text.
- @details Accepts `bytes`, `bytearray`, `str`, and sequence-like metadata payloads, strips null terminators, joins sequence entries with `/`, and returns `None` when no stable textual representation exists.
- @param metadata_raw {object} Candidate RAW metadata payload.
- @return {str|None} Normalized text token or `None`.
- @satisfies REQ-163

### fn `def _classify_explicit_source_gamma(raw_handle)` `priv` (L2432-2481)
- @brief Classify source gamma from explicit profile or color-space metadata.
- @details Inspects common RAW metadata attributes that can already carry an explicit transfer-function declaration, maps recognized tokens to deterministic label/gamma pairs, and returns `None` when no explicit classification is available.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {SourceGammaInfo|None} Classified explicit profile diagnostic or `None`.
- @satisfies REQ-157, REQ-163

### fn `def _classify_tone_curve_gamma(raw_handle)` `priv` (L2482-2530)
- @brief Classify source gamma from `rawpy.tone_curve` metadata.
- @details Reads the optional tone-curve payload, estimates one effective power-law gamma from valid interior samples, and suppresses the result when the curve is absent, too short, degenerate, or non-finite.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {SourceGammaInfo|None} Tone-curve diagnostic or `None`.
- @satisfies REQ-157, REQ-163

### fn `def _has_nonzero_matrix(matrix_raw)` `priv` (L2531-2551)
- @brief Determine whether one RAW metadata matrix carries non-zero values.
- @details Iterates nested list/tuple/numpy-like matrix payloads and returns `True` when any element coerces to a finite non-zero scalar.
- @param matrix_raw {object} Candidate RAW metadata matrix.
- @return {bool} `True` when matrix evidence is non-zero.
- @satisfies REQ-163

### fn `def _classify_matrix_hint_gamma(raw_handle)` `priv` (L2552-2582)
- @brief Classify source gamma from matrix and color-description hints.
- @details Uses `rgb_xyz_matrix`, `color_matrix`, and `color_desc` as weaker evidence than explicit profiles or tone curves. Numeric gamma remains undetermined for this class of evidence.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {SourceGammaInfo|None} Matrix-hint diagnostic or `None`.
- @satisfies REQ-157, REQ-163

### fn `def _extract_source_gamma_info(raw_handle)` `priv` (L2583-2610)
- @brief Derive source-gamma diagnostics from RAW metadata only.
- @details Applies deterministic evidence priority: explicit profile or color-space metadata first, then `rawpy.tone_curve`, then weaker camera color-matrix hints (`rgb_xyz_matrix`, `color_matrix`, `color_desc`), and finally emits `unknown` when no metadata source can support classification.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @return {SourceGammaInfo} Deterministic source-gamma diagnostic payload.
- @satisfies REQ-157, REQ-163

### fn `def _describe_source_gamma_info(source_gamma_info)` `priv` (L2611-2632)
- @brief Format one deterministic source-gamma runtime diagnostic line.
- @details Renders one stable `print_info` payload that always includes both a source-gamma label and a numeric gamma value or the literal `undetermined`.
- @param source_gamma_info {SourceGammaInfo} Derived source-gamma metadata payload.
- @return {str} Deterministic runtime diagnostic line.
- @satisfies REQ-164

### fn `def _coerce_positive_luminance(value, fallback)` `priv` (L2633-2652)
- @brief Coerce luminance scalar to positive range for logarithmic math.
- @details Converts input to float and enforces a strictly positive minimum. Returns fallback when conversion fails or result is non-positive.
- @param value {object} Candidate luminance scalar.
- @param fallback {float} Fallback positive luminance scalar.
- @return {float} Positive luminance value suitable for `log2`.
- @satisfies REQ-031

### fn `def _calculate_bt709_luminance(np_module, image_rgb_float)` `priv` (L2653-2675)
- @brief Convert one normalized RGB float image to BT.709 luminance.
- @details Normalizes the input image to the repository RGB float contract and computes luminance in the linear gamma=`1` domain using BT.709 coefficients `(0.2126, 0.7152, 0.0722)`. Complexity: O(H*W). Side effects: none.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} Input image payload convertible to normalized RGB float `[0,1]`.
- @return {object} Linear luminance tensor with shape `(H,W)` and dtype `float32`.
- @satisfies REQ-008, REQ-032

### fn `def _smoothstep(np_module, values, edge0, edge1)` `priv` (L2676-2694)
- @brief Evaluate one smoothstep ramp with clamped normalized input.
- @details Computes the cubic Hermite interpolation `t*t*(3-2*t)` over input values normalized into `[0,1]` using denominator `max(edge1-edge0, 1e-6)`. Complexity: O(N). Side effects: none.
- @param np_module {ModuleType} Imported numpy module.
- @param values {object} Numeric tensor evaluated element-wise.
- @param edge0 {float} Lower transition edge.
- @param edge1 {float} Upper transition edge.
- @return {object} Float tensor with values in `[0,1]`.
- @satisfies REQ-032

### fn `def _calculate_entropy_optimized_ev(_cv2_module, np_module, luminance_float)` `priv` (L2695-2740)
- @brief Compute the entropy-optimized EV candidate on linear luminance.
- @details Sweeps EV values in range `[-3.0,+3.0]` with step `0.1`, scales the normalized linear luminance by `2**EV`, clips into `[0,1]`, converts the clipped image directly to 8-bit linear code values, evaluates histogram entropy with clipping penalties, and returns the highest-score EV rounded to one decimal place. Complexity: O(K*H*W)` where `K=61`. Side effects: none.
- @param cv2_module {ModuleType|None} Optional OpenCV module retained for call compatibility.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Linear luminance tensor normalized to `[0,1]`.
- @return {float} Entropy-optimized EV candidate rounded to one decimal place.
- @satisfies REQ-032

### fn `def _calculate_ettr_ev(np_module, luminance_float)` `priv` (L2741-2760)
- @brief Compute the ETTR EV candidate on linear luminance.
- @details Evaluates the `99`th percentile of normalized linear luminance, targets that percentile to `0.90`, computes `log2(target/L99)`, and returns the result rounded to one decimal place. Fully black inputs return `0.0`. Complexity: O(H*W log(H*W)) due to percentile extraction. Side effects: none.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Linear luminance tensor normalized to `[0,1]`.
- @return {float} ETTR EV candidate rounded to one decimal place.
- @satisfies REQ-032

### fn `def _calculate_detail_preservation_ev(_cv2_module, np_module, luminance_float)` `priv` (L2761-2828)
- @brief Compute the detail-preservation EV candidate on linear luminance.
- @details Builds local-detail weights from Sobel gradients on `log(luminance+eps)`, suppresses flat regions below the `40`th percentile, estimates a heuristic noise floor from the `1`st percentile, sweeps EV in `[-3.0,+3.0]` with step `0.1`, and maximizes preserved weighted detail while penalizing highlight clipping and shadow crushing. Returns the best EV rounded to one decimal place. Complexity: O(K*H*W)` where `K=61`. Side effects: none.
- @param cv2_module {ModuleType} Imported OpenCV module.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Linear luminance tensor normalized to `[0,1]`.
- @return {float} Detail-preservation EV candidate rounded to one decimal place.
- @satisfies REQ-032

### fn `def _calculate_auto_zero_evaluations(cv2_module, np_module, image_rgb_float)` `priv` (L2829-2866)
- @brief Compute the three automatic EV-zero candidate evaluations.
- @details Migrates `calcola_correzioni_ev(immagine_float)` from the external prototype into the current pipeline, adapts it to the repository linear gamma=`1` RGB float contract, computes BT.709 luminance, evaluates `ev_best`, `ev_ettr`, and `ev_detail`, and returns all three rounded candidates without applying selector quantization. Complexity: dominated by the EV sweeps in entropy/detail evaluation. Side effects: none.
- @param cv2_module {ModuleType} Imported OpenCV module.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} Input image payload convertible to normalized RGB float `[0,1]`.
- @return {AutoZeroEvaluation} Candidate EV evaluations on the normalized linear image.
- @satisfies REQ-008, REQ-032, CTN-007

### fn `def _select_ev_zero_candidate(evaluations)` `priv` (L2867-2895)
- @brief Select `ev_zero` from the exposure-measure EV triplet.
- @details Selects the numeric minimum EV candidate preserving sign using deterministic tie-break order `value -> declaration order` without applying bit-depth-derived clamping. Invoked only when `--exposure=auto` is active.
- @param evaluations {AutoZeroEvaluation} Exposure-measure EV values.
- @return {tuple[float, str]} Selected `(ev_zero, source_label)` pair.
- @satisfies REQ-032, CTN-007

### fn `def _build_unclipped_bracket_images_from_linear_base_float(` `priv` (L2896-2900)

### fn `def _measure_any_channel_highlight_clipping_pct(np_module, image_rgb_float)` `priv` (L2930-2947)
- @brief Build unclipped bracket tensors from the shared linear base image.
- @brief Measure highlight clipping percentage for one RGB image.
- @details Applies exposure multipliers for `ev_zero-ev_delta`, `ev_zero`, and
`ev_zero+ev_delta` without clipping to `[0,1]`.
- @details Counts pixels where any RGB channel is greater than or equal to `1` and returns the result in percent.
- @param np_module {ModuleType} Imported numpy module.
- @param base_rgb_float {object} Normalized linear base RGB tensor.
- @param ev_delta {float} Symmetric bracket half-span.
- @param ev_zero {float} Bracket center EV.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB image tensor.
- @return {tuple[object, object, object]} Unclipped `(ev_minus, ev_zero, ev_plus)` tensors.
- @return {float} Highlight clipping percentage in `0..100`.
- @satisfies REQ-167
- @satisfies REQ-168

### fn `def _measure_any_channel_shadow_clipping_pct(np_module, image_rgb_float)` `priv` (L2948-2965)
- @brief Measure shadow clipping percentage for one RGB image.
- @details Counts pixels where any RGB channel is less than or equal to `0` and returns the result in percent.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB image tensor.
- @return {float} Shadow clipping percentage in `0..100`.
- @satisfies REQ-168

### fn `def _resolve_auto_ev_delta(` `priv` (L2966-2970)

### fn `def _resolve_joint_auto_ev_solution(` `priv` (L3024-3027)
- @brief Resolve automatic bracket half-span by iterative clipping-threshold expansion.
- @details Starts at `auto_ev_options.step`, evaluates unclipped bracket images
at `ev_zero-ev_delta` and `ev_zero+ev_delta`, and stops at the first step where
shadow clipping exceeds `shadow_clipping_pct` or highlight clipping reaches
`highlight_clipping_pct`. Prints per-step diagnostics and final selection.
- @param np_module {ModuleType} Imported numpy module.
- @param base_rgb_float {object} Normalized linear base RGB image.
- @param ev_zero {float} Fixed bracket center EV used during iteration.
- @param auto_ev_options {AutoEvOptions} Automatic clipping thresholds and EV increment.
- @return {tuple[float, tuple[AutoEvIterationStep, ...]]} `(ev_delta, iteration_steps)` pair.
- @satisfies REQ-009, REQ-052, REQ-167, REQ-168

### fn `def _parse_luminance_text_option(option_name, option_raw)` `priv` (L3084-3104)
- @brief Resolve the joint automatic symmetric exposure plan.
- @brief Parse and validate non-empty luminance string option value.
- @details Loads numeric dependencies, computes the exposure-measure EV
triplet from one normalized linear base image, selects `ev_zero` as numeric
minimum preserving sign, then delegates iterative bracket half-span expansion to
`_resolve_auto_ev_delta`.
- @details Normalizes surrounding spaces, lowercases token, rejects empty values, and rejects ambiguous values that start with option prefix marker.
- @param auto_ev_options {AutoEvOptions} Automatic clipping thresholds and EV increment.
- @param auto_adjust_dependencies {tuple[ModuleType, ModuleType]|None} Optional `(cv2_module, numpy_module)` tuple.
- @param base_rgb_float {object|None} Optional precomputed normalized linear base RGB image.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {JointAutoEvSolution} Selected joint automatic exposure solution.
- @return {str|None} Parsed normalized option token when valid; `None` otherwise.
- @exception RuntimeError Raised when required `cv2` or `numpy` dependencies are unavailable.
- @satisfies REQ-008, REQ-009, REQ-031, REQ-032, REQ-037, REQ-052, REQ-167, REQ-168
- @satisfies REQ-061

### fn `def _parse_luminance_response_curve_option(option_raw)` `priv` (L3105-3131)
- @brief Parse one luminance response-curve selector under the linear backend contract.
- @details Normalizes one raw `--luminance-hdr-response-curve` token through the shared luminance text parser, then enforces the repository luminance backend contract requiring deterministic `linear` response-curve forwarding. Complexity: `O(n)` in token length. Side effects: emits deterministic parse diagnostics on invalid values.
- @param option_raw {str} Raw CLI payload for `--luminance-hdr-response-curve`.
- @return {str|None} Canonical `linear` token when valid; `None` otherwise.
- @satisfies REQ-011

### fn `def _parse_positive_float_option(option_name, option_raw)` `priv` (L3132-3155)
- @brief Parse and validate one positive float option value.
- @details Converts option token to `float`, requires value greater than zero, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {float|None} Parsed positive float value when valid; `None` otherwise.
- @satisfies REQ-065

### fn `def _parse_post_gamma_selector_option(option_raw)` `priv` (L3156-3177)
- @brief Parse `--post-gamma` selector as numeric factor or `auto`.
- @details Accepts one positive float token for numeric static gamma mode or literal `auto` for auto-gamma replacement mode.
- @param option_raw {str} Raw `--post-gamma` value token from CLI args.
- @return {tuple[float, str]|None} `(post_gamma_value, mode)` where `mode` is `numeric` or `auto`; `None` on parse failure.
- @satisfies REQ-176

### fn `def _parse_positive_int_option(option_name, option_raw)` `priv` (L3178-3201)
- @brief Parse and validate one positive integer option value.
- @details Converts option token to `int`, requires value greater than zero, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {int|None} Parsed positive integer value when valid; `None` otherwise.
- @satisfies REQ-127, REQ-130

### fn `def _parse_post_gamma_auto_options(post_gamma_auto_raw_values)` `priv` (L3202-3277)
- @brief Parse and validate post-gamma auto replacement knobs.
- @details Applies deterministic defaults for omitted knobs, validates target-gray and luminance guards as exclusive `(0,1)` bounds, validates LUT size as integer `>=2`, and enforces `luma_min < luma_max`.
- @param post_gamma_auto_raw_values {dict[str, str]} Raw `--post-gamma-auto-*` option values keyed by long option name.
- @return {PostGammaAutoOptions|None} Parsed auto-gamma options or `None` on validation error.
- @satisfies REQ-177, REQ-179

### fn `def _parse_tmo_passthrough_value(option_name, option_raw)` `priv` (L3278-3294)
- @brief Parse and validate one luminance `--tmo*` passthrough value.
- @details Rejects empty values and preserves original payload for transparent forwarding to `luminance-hdr-cli`.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {str|None} Original value when valid; `None` otherwise.
- @satisfies REQ-067

### fn `def _parse_jpg_compression_option(compression_raw)` `priv` (L3295-3317)
- @brief Parse and validate JPEG compression option value.
- @details Converts option token to `int`, requires inclusive range `[0, 100]`, and emits deterministic parse errors on malformed values.
- @param compression_raw {str} Raw compression token value from CLI args.
- @return {int|None} Parsed JPEG compression level when valid; `None` otherwise.
- @satisfies REQ-065

### fn `def _parse_float_exclusive_range_option(option_name, option_raw, min_value, max_value)` `priv` (L3318-3342)
- @brief Parse and validate one float option in an exclusive range.
- @details Converts option token to `float`, validates `min < value < max`, and emits deterministic parse errors on malformed or out-of-range values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @param min_value {float} Exclusive minimum bound.
- @param max_value {float} Exclusive maximum bound.
- @return {float|None} Parsed float value when valid; `None` otherwise.
- @satisfies REQ-065, REQ-089

### fn `def _parse_non_negative_float_option(option_name, option_raw)` `priv` (L3343-3365)
- @brief Parse and validate one non-negative float option value.
- @details Converts option token to `float`, requires value greater than or equal to zero, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {float|None} Parsed non-negative float value when valid; `None` otherwise.
- @satisfies REQ-065, REQ-089

### fn `def _parse_float_in_range_option(option_name, option_raw, min_value, max_value)` `priv` (L3366-3391)
- @brief Parse and validate one float option constrained to inclusive range.
- @details Converts option token to `float`, validates inclusive bounds, and emits deterministic parse errors on malformed or out-of-range values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @param min_value {float} Inclusive minimum bound.
- @param max_value {float} Inclusive maximum bound.
- @return {float|None} Parsed bounded float value when valid; `None` otherwise.
- @satisfies REQ-082, REQ-084

### fn `def _parse_positive_int_pair_option(option_name, option_raw)` `priv` (L3392-3423)
- @brief Parse and validate one positive integer pair option value.
- @details Accepts `rowsxcols`, `rowsXcols`, or `rows,cols`, converts both tokens to `int`, requires each value to be greater than zero, and emits deterministic parse errors on malformed values.
- @param option_name {str} Long-option identifier used in error messages.
- @param option_raw {str} Raw option token value from CLI args.
- @return {tuple[int, int]|None} Parsed positive integer pair when valid; `None` otherwise.
- @satisfies REQ-065, REQ-125

### fn `def _parse_auto_brightness_options(auto_brightness_raw_values)` `priv` (L3424-3520)
- @brief Parse and validate auto-brightness parameters.
- @details Parses optional controls for the original photographic BT.709 float-domain tonemap pipeline and applies deterministic defaults for omitted auto-brightness options.
- @param auto_brightness_raw_values {dict[str, str]} Raw `--ab-*` option values keyed by long option name.
- @return {AutoBrightnessOptions|None} Parsed auto-brightness options or `None` on validation error.
- @satisfies REQ-088, REQ-089, REQ-103, REQ-104, REQ-105, REQ-124, REQ-135

### fn `def _parse_auto_levels_hr_method_option(auto_levels_method_raw)` `priv` (L3521-3552)
- @brief Parse auto-levels highlight reconstruction method option value.
- @details Validates case-insensitive method names and normalizes accepted values to canonical tokens used by runtime dispatch.
- @param auto_levels_method_raw {str} Raw `--al-highlight-reconstruction-method` option token.
- @return {str|None} Canonical method token or `None` on parse failure.
- @satisfies REQ-101, REQ-102, REQ-119

### fn `def _parse_auto_levels_options(auto_levels_raw_values)` `priv` (L3553-3625)
- @brief Parse and validate auto-levels parameters.
- @details Parses histogram clip percentage, explicit gamut clipping toggle, explicit highlight reconstruction toggle, optional highlight reconstruction method, and Inpaint Opposed gain threshold using RawTherapee-aligned defaults.
- @param auto_levels_raw_values {dict[str, str]} Raw `--al-*` option values keyed by long option name.
- @return {AutoLevelsOptions|None} Parsed auto-levels options or `None` on validation error.
- @satisfies REQ-100, REQ-101, REQ-102, REQ-116, REQ-120

### fn `def _parse_auto_adjust_options(auto_adjust_raw_values)` `priv` (L3626-3775)
- @brief Parse and validate auto-adjust knobs.
- @details Applies defaults for omitted knobs, validates scalar/range constraints, validates CLAHE-luma controls, and enforces level percentile ordering contract.
- @param auto_adjust_raw_values {dict[str, str]} Raw `--aa-*` option values keyed by long option name.
- @return {AutoAdjustOptions|None} Parsed shared auto-adjust options or `None` on validation error.
- @satisfies REQ-051, REQ-082, REQ-083, REQ-084, REQ-123, REQ-125

### fn `def _parse_hdrplus_proxy_mode_option(proxy_mode_raw)` `priv` (L3776-3794)
- @brief Parse HDR+ scalar proxy mode selector.
- @details Accepts case-insensitive proxy mode names, normalizes to canonical lowercase spelling, and rejects unsupported values with deterministic diagnostics.
- @param proxy_mode_raw {str} Raw HDR+ proxy mode token from CLI args.
- @return {str|None} Canonical proxy mode token or `None` on parse failure.
- @satisfies REQ-126, REQ-127, REQ-130

### fn `def _parse_hdrplus_options(hdrplus_raw_values)` `priv` (L3795-3871)
- @brief Parse and validate HDR+ merge knob values.
- @details Applies source-matching defaults for omitted knobs, validates the RGB-to-scalar proxy selector, alignment search radius, and temporal weight parameters, and rejects inconsistent temporal threshold combinations.
- @param hdrplus_raw_values {dict[str, str]} Raw `--hdrplus-*` option values keyed by long option name.
- @return {HdrPlusOptions|None} Parsed HDR+ options or `None` on validation error.
- @satisfies REQ-126, REQ-127, REQ-128, REQ-130

### fn `def _apply_merge_gamma_float_no_clip(np_module, image_rgb_float, resolved_merge_gamma)` `priv` (L3872-3925)
- @brief Apply resolved merge-gamma transfer without any input/output clipping.
- @details Executes the same transfer families as `_apply_merge_gamma_float` but intentionally avoids lower-bound clipping to preserve unbounded positive and negative float dynamic range for OpenCV-Tonemap backend execution.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} Backend RGB float tensor.
- @param resolved_merge_gamma {ResolvedMergeGamma} Resolved merge-gamma payload.
- @return {object} RGB float32 tensor after transfer evaluation.
- @satisfies REQ-197, REQ-198

### fn `def _resolve_opencv_tonemap_gamma_inverse(resolved_merge_gamma)` `priv` (L3926-3959)
- @brief Resolve OpenCV-Tonemap gamma inverse from merge-gamma payload.
- @details Maps resolved merge-gamma transfer families to one OpenCV tone-mapping gamma value that inverts the merge-gamma curve parameter: `sRGB -> 1/2.4`, `power -> 1/param_a`, `rec709 -> 1/param_b`, and `linear -> 1.0`.
- @param resolved_merge_gamma {ResolvedMergeGamma} Resolved merge-gamma payload.
- @return {float} Positive OpenCV tone-map gamma value.
- @exception ValueError Raised when required merge-gamma parameters are missing or non-positive.
- @satisfies REQ-193

### fn `def _parse_auto_adjust_option(auto_adjust_raw)` `priv` (L3960-3983)
- @brief Parse auto-adjust enable selector option value.
- @details Accepts case-insensitive `enable` and `disable` tokens and maps them to the resolved auto-adjust stage state.
- @param auto_adjust_raw {str} Raw auto-adjust enable token.
- @return {bool|None} `True` when auto-adjust is enabled; `False` when disabled; `None` on parse failure.
- @satisfies REQ-065, REQ-073, REQ-075

### fn `def _parse_raw_white_balance_mode_option(raw_white_balance_mode_raw)` `priv` (L3984-4011)
- @brief Parse RAW white-balance normalization mode selector option value.
- @details Accepts case-insensitive RAW white-balance normalization mode selectors and normalizes them to canonical runtime names.
- @param raw_white_balance_mode_raw {str} Raw `--white-balance` selector token.
- @return {str|None} Canonical RAW white-balance normalization mode or `None` on parse failure.
- @satisfies REQ-203

### fn `def _parse_auto_white_balance_mode_option(auto_white_balance_raw)` `priv` (L4012-4043)
- @brief Parse `--auto-white-balance` mode selector option value.
- @details Accepts case-insensitive auto-white-balance selector names and normalizes them to canonical runtime mode names, including explicit `disable` alias token.
- @param auto_white_balance_raw {str} Raw `--auto-white-balance` selector token.
- @return {str|None} Canonical selector token including `disable` alias or `None` on parse failure.
- @satisfies REQ-181, REQ-183

### fn `def _parse_white_balance_mode_option(white_balance_raw)` `priv` (L4044-4056)
- @brief Parse compatibility alias for `--auto-white-balance` selector.
- @details Preserves compatibility for existing internal/test references while delegating parsing logic to `_parse_auto_white_balance_mode_option`.
- @param white_balance_raw {str} Raw `--auto-white-balance` selector token.
- @return {str|None} Canonical auto-white-balance mode or `None` on parse failure.
- @satisfies REQ-181, REQ-183

### fn `def _parse_white_balance_analysis_source_option(analysis_source_raw)` `priv` (L4057-4086)
- @brief Parse white-balance analysis source selector option value.
- @details Accepts case-insensitive white-balance analysis-source selector names and normalizes them to canonical runtime selector names.
- @param analysis_source_raw {str} Raw `--white-balance-analysis-source` selector token.
- @return {str|None} Canonical analysis-source selector or `None` on parse failure.
- @satisfies REQ-199

### fn `def _parse_white_balance_xphoto_domain_option(xphoto_domain_raw)` `priv` (L4087-4113)
- @brief Parse white-balance xphoto estimation-domain selector option value.
- @details Accepts case-insensitive xphoto estimation-domain selector names and normalizes them to canonical runtime selector names.
- @param xphoto_domain_raw {str} Raw `--white-balance-xphoto-domain` selector token.
- @return {str|None} Canonical xphoto estimation-domain selector or `None` on parse failure.
- @satisfies REQ-210

### fn `def _parse_hdr_merge_option(hdr_merge_raw)` `priv` (L4114-4144)
- @brief Parse HDR backend selector option value.
- @details Accepts case-insensitive backend selector names and normalizes them to canonical runtime mode names.
- @param hdr_merge_raw {str} Raw `--hdr-merge` selector token.
- @return {str|None} Canonical HDR merge mode or `None` on parse failure.
- @satisfies CTN-002, REQ-023, REQ-024, REQ-107, REQ-111, REQ-189

### fn `def _resolve_default_postprocess(` `priv` (L4145-4148)

### fn `def _parse_gamma_option(option_value)` `priv` (L4229-4267)
- @brief Resolve backend-specific postprocess defaults.
- @brief Parse one `--gamma` selector into normalized request state.
- @details Selects backend-specific defaults. Uses algorithm-specific OpenCV
defaults keyed by resolved `Debevec|Robertson|Mertens`, luminance-operator-
specific defaults for `Luminace-HDR` (`mantiuk08`, `reinhard02`),
configured defaults for `HDR-Plus`, and generic fallback defaults for
untuned luminance operators. Complexity: O(1). Side effects: none.
- @details Accepts literal `auto` or one comma-separated pair `<linear_coeff,exponent>`. Both numeric values must be finite and strictly positive. Returns `None` after deterministic diagnostics on invalid payload.
- @param hdr_merge_mode {str} Canonical HDR merge mode selector.
- @param luminance_tmo {str} Selected luminance tone-mapping operator.
- @param opencv_merge_algorithm {str} Resolved OpenCV merge algorithm selector.
- @param option_value {str} Raw `--gamma` value.
- @return {tuple[float, float, float, float]} Defaults in `(post_gamma, brightness, contrast, saturation)` order.
- @return {MergeGammaOption|None} Parsed request dataclass on success; `None` on validation failure.
- @satisfies DES-006, DES-008, REQ-145
- @satisfies REQ-020

### fn `def _decode_exif_text_value(exif_value)` `priv` (L4268-4287)
- @brief Normalize one EXIF scalar payload to deterministic stripped text.
- @details Accepts bytes, rationals, enums, or generic scalar-like values and returns one normalized text token for merge-gamma auto resolution. Complexity: O(len(value_text)). Side effects: none.
- @param exif_value {object} Raw EXIF payload.
- @return {str|None} Normalized text token or `None` when payload is absent/empty.
- @satisfies REQ-169

### fn `def _exiftool_color_space_fallback(input_dng)` `priv` (L4288-4339)
- @brief Extract color-space evidence via exiftool subprocess fallback.
- @details Invokes `exiftool -j -ColorSpace` as a subprocess to recover color-space metadata from MakerNotes or vendor-specific IFDs that `exifread` cannot parse (e.g., Canon MakerNotes embedded in DNG). Maps exiftool text labels to EXIF-compatible numeric tokens: `Adobe RGB` -> `"2"`, `sRGB` -> `"1"`. Returns `None` when exiftool is unavailable, times out, or yields no color-space evidence. Complexity: O(1) subprocess invocation. Side effects: read-only.
- @param input_dng {Path} Source RAW/DNG file path.
- @return {str|None} EXIF-compatible numeric `ColorSpace` token or `None`.
- @satisfies REQ-169

### fn `def _extract_exif_gamma_tags(input_dng)` `priv` (L4340-4408)
- @brief Extract EXIF color-space metadata relevant to auto merge gamma.
- @details Opens the source RAW/DNG file as a binary stream via `exifread.process_file` and normalizes `EXIF ColorSpace`, `Interop InteroperabilityIndex`, `Image Model`, and `Image Make` tags for deterministic auto transfer resolution. When `exifread` yields no `ColorSpace` evidence, falls back to `exiftool` subprocess extraction to recover vendor-specific MakerNotes color-space data (e.g., Canon DNG). Does not use Pillow for this extraction. Complexity: O(file_size). Side effects: none (read-only file access).
- @param input_dng {Path} Source RAW/DNG file path.
- @return {ExifGammaTags} Normalized EXIF merge-gamma evidence payload.
- @satisfies REQ-169, REQ-172, REQ-173

### fn `def _resolve_auto_merge_gamma(exif_gamma_tags, source_gamma_info)` `priv` (L4409-4455)
- @brief Resolve auto merge-output transfer from EXIF-first metadata evidence.
- @details Applies deterministic priority: EXIF `ColorSpace==1` selects sRGB, EXIF `ColorSpace==2` or interoperability token containing `R03` selects Adobe RGB power gamma `2.19921875`, and unresolved cases default to sRGB transfer as fallback.
- @param exif_gamma_tags {ExifGammaTags} Normalized EXIF color-space evidence.
- @param source_gamma_info {SourceGammaInfo} Derived source-gamma diagnostic payload (retained for backward compatibility; not used for resolution).
- @return {ResolvedMergeGamma} Resolved auto transfer payload.
- @satisfies REQ-169

### fn `def _describe_resolved_merge_gamma(resolved_merge_gamma)` `priv` (L4456-4515)
- @brief Format one deterministic merge-gamma runtime diagnostic line.
- @details Renders one stable diagnostic payload including request mode, resolved transfer family, label, explicit linear-segment parameters, explicit curve-segment parameters, and evidence token.
- @param resolved_merge_gamma {ResolvedMergeGamma} Resolved merge-gamma payload.
- @return {str} Deterministic runtime diagnostic line.
- @satisfies REQ-171

### fn `def _format_gamma_number(value)` `priv` (L4467-4480)
- @brief Format one deterministic merge-gamma runtime diagnostic line.
- @brief Format one finite gamma parameter for deterministic diagnostics.
- @details Renders one stable diagnostic payload including request mode,
resolved transfer family, label, explicit linear-segment parameters,
explicit curve-segment parameters, and evidence token.
- @details Serializes one numeric gamma parameter with stable decimal precision, preserving exact repository-relevant constants such as `2.19921875` while avoiding scientific notation and insignificant trailing zeroes.
- @param resolved_merge_gamma {ResolvedMergeGamma} Resolved merge-gamma payload.
- @param value {float} Numeric gamma parameter to serialize.
- @return {str} Deterministic runtime diagnostic line.
- @return {str} Stable decimal representation for runtime diagnostics.
- @satisfies REQ-171
- @satisfies REQ-171

### fn `def _describe_exif_gamma_tags(exif_gamma_tags)` `priv` (L4516-4558)
- @brief Format one deterministic EXIF merge-gamma input diagnostic line.
- @details Renders one stable runtime payload exposing the normalized EXIF `ColorSpace`, `InteroperabilityIndex`, `ImageModel`, `ImageMake`, and a human-readable `ColorProfile` label derived from `ColorSpace` and `InteroperabilityIndex`. Mapping: `ColorSpace==1` -> `sRGB`, `ColorSpace==2` or `InteroperabilityIndex` containing `R03` -> `Adobe RGB`, `ColorSpace==65535` -> `Uncalibrated`, otherwise `Unknown`. Missing values are rendered as `missing`.
- @param exif_gamma_tags {ExifGammaTags} Normalized EXIF merge-gamma evidence payload.
- @return {str} Deterministic runtime diagnostic line.
- @satisfies REQ-172

### fn `def _ensure_three_channel_float_array_no_clip(np_module, image_data)` `priv` (L4559-4590)
- @brief Normalize one image payload to three-channel float tensor without upper clipping.
- @details Converts arbitrary numeric image payloads into RGB `float64`, preserving finite positive values above `1.0`, clearing non-finite and negative values only, expanding grayscale/single-channel inputs to RGB, and dropping alpha channels. Used exclusively by backend-final merge-gamma application to avoid unnecessary clipping around transfer evaluation.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image payload.
- @return {object} RGB `float64` tensor with shape `(H,W,3)` and lower bound `0`.
- @exception ValueError Raised when the input shape cannot be normalized to RGB.
- @satisfies REQ-170

### fn `def _ensure_three_channel_float_array_no_bounds(np_module, image_data)` `priv` (L4591-4620)
- @brief Normalize one image payload to RGB float tensor without clipping bounds.
- @details Converts numeric image payloads into RGB `float64`, preserves finite values on the full float range without lower/upper clipping, replaces non-finite payload samples with `0.0`, expands grayscale/single- channel data to RGB, and drops alpha.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image payload.
- @return {object} RGB `float64` tensor with shape `(H,W,3)` and unbounded finite range.
- @exception ValueError Raised when image shape is unsupported.
- @satisfies REQ-198

### fn `def _apply_merge_gamma_float(np_module, image_rgb_float, resolved_merge_gamma)` `priv` (L4621-4673)
- @brief Apply one resolved merge-output transfer without extra clipping.
- @details Executes backend-final transfer encoding on positive float-domain RGB values after backend normalization. The helper intentionally avoids upper clipping before and after transfer evaluation so highlight headroom is preserved until the shared downstream pipeline chooses its own bounds.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} Backend-normalized RGB float tensor.
- @param resolved_merge_gamma {ResolvedMergeGamma} Resolved merge-gamma payload.
- @return {object} RGB float32 tensor after merge-gamma transfer.
- @satisfies REQ-170

### fn `def _parse_run_options(args)` `priv` (L4674-4873)
- @brief Parse CLI args into input, output, and EV parameters.
- @details Supports positional file arguments, bracket delta selector (`--bracketing=<auto|value>`, default `1.0` static), bracket center selector (`--exposure=<auto|value>`, default `0.0` static), optional automatic exposure clipping and step controls, optional RAW white-balance normalization selector (`--white-balance=<GREEN|MAX|MIN|MEAN>`), optional auto-white-balance selector (`--auto-white-balance=<mode>`) applied to the linear base image after auto-brightness and before auto-zero evaluation, optional xphoto estimation-domain selector (`--white-balance-xphoto-domain=<linear|srgb|source-auto>`), optional postprocess controls including `--post-gamma=<value|auto>` and optional `--post-gamma-auto-*` knobs, optional auto-brightness stage and `--ab-*` knobs, optional auto-levels stage and `--al-*` knobs, optional shared auto-adjust knobs, optional backend selector (`--hdr-merge=<Luminace-HDR|OpenCV-Merge|OpenCV-Tonemap|HDR-Plus>` default `OpenCV-Merge`), OpenCV backend controls, OpenCV-Tonemap backend controls, HDR+ backend controls, and luminance backend controls including explicit `--tmo*` passthrough options and optional auto-adjust enable selector (`--auto-adjust <enable|disable>`), plus optional `--debug` persistent checkpoint emission; parses `--gamma=<auto|linear_coeff,exponent>` merge-output transfer selector defaulting to `auto` when omitted, rejects unknown options, and rejects invalid arity.
- @param args {list[str]} Raw command argument vector.
- @return {tuple[Path, Path, float|None, bool, PostprocessOptions, bool, bool, LuminanceOptions, OpenCvMergeOptions, HdrPlusOptions, bool, float, bool, AutoEvOptions]|None} Parsed `(input, output, ev, auto_ev_delta_enabled, postprocess, enable_luminance, enable_opencv, luminance_options, opencv_merge_options, hdrplus_options, enable_hdr_plus, ev_zero, auto_ev_zero_enabled, auto_ev_options)` tuple; `None` on parse failure.
- @satisfies CTN-002, CTN-003, CTN-007, REQ-007, REQ-008, REQ-009, REQ-018, REQ-020, REQ-022, REQ-023, REQ-024, REQ-025, REQ-030, REQ-100, REQ-101, REQ-107, REQ-111, REQ-125, REQ-135, REQ-141, REQ-143, REQ-146, REQ-176, REQ-179, REQ-180, REQ-181, REQ-183, REQ-189, REQ-190, REQ-191, REQ-194, REQ-195, REQ-196, REQ-199, REQ-203, REQ-210

### fn `def _load_image_dependencies()` `priv` (L5307-5344)
- @brief Load optional Python dependencies required by `dng2jpg`.
- @details Imports `rawpy` for RAW decoding and `imageio` for image IO using `imageio.v3` when available with fallback to top-level `imageio` module.
- @return {tuple[ModuleType, ModuleType, ModuleType]|None} `(rawpy_module, imageio_module, pil_image_module)` on success; `None` on missing dependency.
- @satisfies REQ-059, REQ-066, REQ-074

### fn `def _parse_exif_datetime_to_timestamp(datetime_raw)` `priv` (L5345-5375)
- @brief Parse one EXIF datetime token into POSIX timestamp.
- @details Normalizes scalar EXIF datetime input (`str` or `bytes`), trims optional null-terminated EXIF payload suffix, and parses strict EXIF format `YYYY:MM:DD HH:MM:SS` to generate filesystem timestamp.
- @param datetime_raw {str|bytes|object} EXIF datetime scalar.
- @return {float|None} Parsed POSIX timestamp; `None` when value is missing or invalid.
- @satisfies REQ-074, REQ-077

### fn `def _parse_exif_exposure_time_to_seconds(exposure_raw)` `priv` (L5376-5438)
- @brief Parse one EXIF exposure-time token into positive seconds.
- @details Normalizes scalar or rational-like EXIF `ExposureTime` payloads from Pillow metadata into one positive Python `float` measured in seconds. Accepted forms include numeric scalars, two-item `(numerator, denominator)` pairs, and objects exposing `numerator`/`denominator` attributes.
- @param exposure_raw {object} EXIF `ExposureTime` scalar or rational-like payload.
- @return {float|None} Positive exposure time in seconds; `None` when missing or invalid.
- @satisfies REQ-161

### fn `def _extract_dng_exif_payload_and_timestamp(pil_image_module, input_dng)` `priv` (L5439-5533)
- @brief Extract DNG EXIF payload bytes, preferred datetime timestamp, source orientation, and exposure time.
- @details Opens input DNG via Pillow, suppresses known non-actionable `PIL.TiffImagePlugin` metadata warning for malformed TIFF tag `33723`, reads EXIF mapping without orientation mutation, serializes payload for JPEG save while source image handle is still open, resolves source orientation from EXIF tag `274`, resolves datetime/exposure metadata from the top-level EXIF mapping with fallback to the nested EXIF IFD (`34665`) when Pillow omits those tags from the root mapping, parses EXIF `ExposureTime` to positive seconds, and resolves filesystem timestamp priority: `DateTimeOriginal`(36867) > `DateTimeDigitized`(36868) > `DateTime`(306).
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @param input_dng {Path} Source DNG path.
- @return {tuple[bytes|None, float|None, int, float|None]} `(exif_payload, exif_timestamp, source_orientation, exposure_time_seconds)` with orientation defaulting to `1`.
- @satisfies REQ-066, REQ-074, REQ-077, REQ-161

### fn `def _read_exif_value(exif_tag)` `priv` (L5483-5500)
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

### fn `def _resolve_thumbnail_transpose_map(pil_image_module)` `priv` (L5534-5565)
- @brief Build deterministic EXIF-orientation-to-transpose mapping.
- @details Resolves Pillow transpose constants from modern `Image.Transpose` namespace with fallback to legacy module-level constants.
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @return {dict[int, int]} Orientation-to-transpose mapping for values `2..8`.
- @satisfies REQ-077, REQ-078

### fn `def _apply_orientation_transform(pil_image_module, pil_image, source_orientation)` `priv` (L5566-5588)
- @brief Apply EXIF orientation transform to one image copy.
- @details Produces display-oriented pixels from source-oriented input while preserving the original image object and preserving orientation invariants in the main processing pipeline.
- @param pil_image_module {ModuleType} Imported Pillow Image module.
- @param pil_image {object} Pillow image-like object.
- @param source_orientation {int} EXIF orientation value in range `1..8`.
- @return {object} Transformed Pillow image object.
- @satisfies REQ-077, REQ-078

### fn `def _build_oriented_thumbnail_jpeg_bytes(` `priv` (L5589-5590)

### fn `def _coerce_exif_int_like_value(raw_value)` `priv` (L5621-5663)
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

### fn `def _normalize_ifd_integer_like_values_for_piexif_dump(piexif_module, exif_dict)` `priv` (L5664-5797)
- @brief Normalize integer-like IFD values before `piexif.dump`.
- @details Traverses EXIF IFD mappings (`0th`, `Exif`, `GPS`, `Interop`, `1st`) and coerces integer-like values that can trigger `piexif.dump` packing failures when represented as strings or other non-int scalars. Tuple/list values are normalized only when all items are integer-like. For integer sequence tag types, nested two-item pairs are flattened to a single integer sequence for `piexif.dump` compatibility. Scalar conversion is additionally constrained by `piexif.TAGS` integer field types when tag metadata is available.
- @param piexif_module {ModuleType} Imported piexif module.
- @param exif_dict {dict[str, object]} EXIF dictionary loaded via piexif.
- @return {None} Mutates `exif_dict` in place.
- @satisfies REQ-066, REQ-077, REQ-078

### fn `def _refresh_output_jpg_exif_thumbnail_after_save(` `priv` (L5798-5804)

### fn `def _set_output_file_timestamps(output_jpg, exif_timestamp)` `priv` (L5854-5868)
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

### fn `def _sync_output_file_timestamps_from_exif(output_jpg, exif_timestamp)` `priv` (L5869-5886)
- @brief Synchronize output JPG atime/mtime from optional EXIF timestamp.
- @details Provides one dedicated call site for filesystem timestamp sync and applies update only when EXIF datetime parsing produced a valid POSIX value after refreshed EXIF metadata has already been written to the output JPG.
- @param output_jpg {Path} Output JPG path.
- @param exif_timestamp {float|None} Source EXIF-derived POSIX timestamp.
- @return {None} Side effects only.
- @exception OSError Raised when filesystem metadata update fails.
- @satisfies REQ-014, REQ-074, REQ-077

### fn `def _build_exposure_multipliers(ev_value, ev_zero=0.0)` `priv` (L5887-5905)
- @brief Compute bracketing brightness multipliers from EV delta and center.
- @details Produces exactly three multipliers mapped to exposure stops `[ev_zero-ev, ev_zero, ev_zero+ev]` as powers of two for float-domain HDR base-image scaling.
- @param ev_value {float} Exposure bracket EV delta.
- @param ev_zero {float} Central bracket EV value.
- @return {tuple[float, float, float]} Multipliers in order `(under, base, over)`.
- @satisfies REQ-009, REQ-159, REQ-160

### fn `def _build_bracket_images_from_linear_base_float(np_module, base_rgb_float, multipliers)` `priv` (L5906-5935)
- @brief Build normalized HDR brackets from one linear RGB base tensor.
- @details Broadcast-multiplies one linear RGB base tensor by the ordered EV multiplier triplet `(ev_minus, ev_zero, ev_plus)`, clamps each result into `[0,1]`, and returns float32 bracket tensors in canonical downstream order. The input base tensor range is preserved before EV scaling to avoid stage-local pre-clipping. Complexity: O(3*H*W). Side effects: none.
- @param np_module {ModuleType} Imported numpy module.
- @param base_rgb_float {object} Linear RGB float tensor.
- @param multipliers {tuple[float, float, float]} Ordered EV multipliers.
- @return {list[object]} Ordered RGB float32 bracket tensors.
- @satisfies REQ-159, REQ-160

### fn `def _build_white_balance_analysis_image_from_linear_base_float(` `priv` (L5936-5939)

### fn `def _validate_white_balance_triplet_shape(np_module, bracket_images_float)` `priv` (L5961-5990)
- @brief Build unclipped white-balance analysis image from linear base and EV center.
- @brief Validate white-balance bracket triplet shape contract.
- @details Converts the shared linear base tensor to RGB float without range
clipping and multiplies it by `2^ev_zero` to produce one unclipped analysis
payload independent from bracket clipping side effects.
- @details Normalizes each bracket to RGB float32 and verifies that all three bracket tensors share identical shape so one EV0-derived correction payload can be applied deterministically to every bracket.
- @param np_module {ModuleType} Imported numpy module.
- @param base_rgb_float {object} Shared linear base RGB tensor.
- @param ev_zero {float} Resolved center EV.
- @param np_module {ModuleType} Imported numpy module.
- @param bracket_images_float {Sequence[object]} Candidate bracket tensors.
- @return {object} RGB float32 analysis image without stage-local clipping.
- @return {tuple[object, object, object]} Normalized `(ev_minus, ev_zero, ev_plus)` RGB float32 tensors.
- @exception ValueError Raised when bracket count is not three or shapes differ.
- @satisfies REQ-183, REQ-200
- @satisfies REQ-183

### fn `def _downsample_xphoto_analysis_image_half(np_module, analysis_rgb, cv2_module)` `priv` (L5991-6037)
- @brief Downsample one RGB analysis payload by factor `2` with anti-aliasing.
- @details Uses OpenCV `resize(..., INTER_AREA)` when available; otherwise applies deterministic `2x2` area averaging with edge padding for odd image dimensions. The output keeps RGB channel order and finite non-negative values.
- @param np_module {ModuleType} Imported numpy module.
- @param analysis_rgb {object} RGB float tensor.
- @param cv2_module {ModuleType|None} Optional OpenCV module.
- @return {object} Anti-aliased half-resolution RGB float tensor.
- @satisfies REQ-184, REQ-185, REQ-186

### fn `def _build_xphoto_analysis_image_rgb_float(` `priv` (L6038-6041)

### fn `def _build_white_balance_robust_analysis_mask(np_module, analysis_rgb_float)` `priv` (L6073-6112)
- @brief Build deterministic real-image xphoto analysis payload.
- @brief Build robust white-balance mask excluding near-black and near-saturated pixels.
- @details Converts one analysis image to RGB float, preserves values above
`1.0`, replaces non-finite values with `0`, removes negatives, and applies
deterministic anti-aliased pyramid downsampling (`INTER_AREA` when
available) until maximum side is `<=1024`. This removes fixed proxy-size
assumptions while reducing chromatic aliasing bias in estimation.
- @details Builds a deterministic per-pixel mask using finite and non-negative RGB values, derives near-black and near-saturation cutoffs from channel-max percentile thresholds, and applies fallback tiers to guarantee at least one valid pixel for downstream statistics.
- @param np_module {ModuleType} Imported numpy module.
- @param analysis_image_rgb_float {object} Analysis RGB float tensor.
- @param cv2_module {ModuleType|None} Optional OpenCV module used for `INTER_AREA` resizing.
- @param np_module {ModuleType} Imported numpy module.
- @param analysis_rgb_float {object} Analysis RGB float tensor.
- @return {object} Downsampled RGB float32 analysis payload.
- @return {object} Boolean mask with shape `(H,W)`.
- @satisfies REQ-183, REQ-184, REQ-185, REQ-186
- @satisfies REQ-187, REQ-188

### fn `def _extract_white_balance_channel_gains_from_xphoto(` `priv` (L6113-6119)

### fn `def _resolve_white_balance_xphoto_estimation_domain(` `priv` (L6199-6201)
- @brief Derive per-channel white-balance gains from one OpenCV xphoto algorithm.
- @details Builds one real-image analysis payload with deterministic pyramid
downsampling, performs one backend-local normalization to `[0,1]` for xphoto
quantization only, executes xphoto `balanceWhite(...)`, and derives one gain
vector from channel means `balanced/original`. Gains are finite positive
float64 values.
- @param cv2_module {ModuleType} Imported OpenCV module.
- @param np_module {ModuleType} Imported numpy module.
- @param wb_algorithm {object} OpenCV xphoto white-balance instance.
- @param analysis_image_rgb_float {object} EV0 RGB float tensor.
- @param bits_per_color {int} Source DNG bit depth used for range-aware quantization.
- @param prefer_uint16_payload {bool} `True` requests uint16 xphoto payload generation when backend support exists.
- @return {object} Channel gains vector with shape `(3,)`.
- @exception RuntimeError Raised when xphoto result shape is invalid.
- @satisfies REQ-183, REQ-184, REQ-185, REQ-186, REQ-201, REQ-211

### fn `def _prepare_xphoto_estimation_image_rgb_float(` `priv` (L6244-6247)
- @brief Resolve effective xphoto estimation domain from selector and source diagnostics.
- @details Returns explicit selector values unchanged for `linear` and `srgb`.
For `source-auto`, derives one deterministic domain from source-gamma
diagnostics, preferring numeric gamma (`>1.2 => srgb`, else `linear`) and
falling back to label-token classification.
- @param white_balance_xphoto_domain {str} Requested xphoto estimation-domain selector.
- @param source_gamma_info {SourceGammaInfo|None} Source-gamma diagnostic payload.
- @return {str} Effective xphoto estimation-domain selector in `{"linear","srgb"}`.
- @satisfies REQ-212

### fn `def _resolve_learning_based_wb_hist_bin_num(bits_per_color)` `priv` (L6282-6297)
- @brief Build xphoto estimation payload in selected estimation domain.
- @brief Resolve IA histogram-bin count from source bit depth.
- @details Normalizes one analysis image to finite non-negative RGB float.
When the selected estimation domain is `srgb`, clamps values to `[0,1]`,
applies linear-to-sRGB transfer, and returns gamma-encoded analysis payload.
The conversion is local to xphoto estimation and does not mutate triplet
processing domains.
- @details Maps source bit depth to a bounded power-of-two histogram count to keep LearningBasedWB histogram granularity coherent with source precision while avoiding excessive bin counts. Mapping: `2^clamp(bits-4, 8, 12)`.
- @param np_module {ModuleType} Imported numpy module.
- @param analysis_image_rgb_float {object} Analysis RGB float tensor.
- @param xphoto_estimation_domain {str} Effective estimation-domain selector in `{"linear","srgb"}`.
- @param bits_per_color {int} Source DNG bit depth.
- @return {object} Domain-resolved RGB float32 analysis payload.
- @return {int} LearningBasedWB histogram-bin count.
- @satisfies REQ-212
- @satisfies REQ-211

### fn `def _estimate_xphoto_white_balance_gains_rgb(` `priv` (L6298-6305)

### fn `def _estimate_color_constancy_white_balance_gains_rgb(` `priv` (L6380-6383)
- @brief Estimate EV0-derived white-balance gains using OpenCV xphoto modes.
- @details Creates one OpenCV xphoto white-balance instance for `Simple`,
`GrayworldWB`, or `IA`, applies optional mode-specific setup, and derives
one channel-gain vector from EV0 analysis only.
- @param cv2_module {ModuleType} Imported OpenCV module.
- @param np_module {ModuleType} Imported numpy module.
- @param white_balance_mode {str} Canonical white-balance mode selector.
- @param analysis_image_rgb_float {object} EV0 RGB float tensor.
- @param bits_per_color {int} Source DNG bit depth used for IA quantization settings.
- @param white_balance_xphoto_domain {str} Requested xphoto estimation-domain selector.
- @param source_gamma_info {SourceGammaInfo|None} Source-gamma diagnostic payload used by `source-auto`.
- @return {object} Channel gains vector with shape `(3,)`.
- @exception RuntimeError Raised when required xphoto API is unavailable.
- @exception ValueError Raised when mode is unsupported for xphoto estimation.
- @satisfies REQ-183, REQ-184, REQ-185, REQ-186, REQ-211, REQ-212

### fn `def _estimate_ttl_white_balance_gains_rgb(np_module, analysis_image_rgb_float)` `priv` (L6418-6449)
- @brief Estimate EV0-derived white-balance gains using scikit-image color constancy.
- @brief Estimate EV0-derived TTL white-balance gains using channel averages.
- @details Normalizes the analysis image to RGB float, builds one robust mask
excluding near-black and near-saturated pixels, converts masked RGB data to
one scalar luminance map via `skimage.color.rgb2gray(...)`, computes masked
channel and luminance means, and derives one Von-Kries-like gain vector
`luma_mean/channel_mean`.
- @details Normalizes the analysis image to RGB float, builds one robust mask excluding near-black and near-saturated pixels, computes masked channel means `(R,G,B)`, computes global gray average as `(R+G+B)/3`, and derives channel gains as `gray/channel_mean` without clipping for downstream float-domain application.
- @param np_module {ModuleType} Imported numpy module.
- @param skimage_color_module {ModuleType} Imported scikit-image color module.
- @param analysis_image_rgb_float {object} EV0 RGB float tensor.
- @param np_module {ModuleType} Imported numpy module.
- @param analysis_image_rgb_float {object} EV0 RGB float tensor.
- @return {object} Channel gains vector with shape `(3,)`.
- @return {object} Channel gains vector with shape `(3,)`.
- @satisfies REQ-183, REQ-187
- @satisfies REQ-183, REQ-188

### fn `def _apply_channel_gains_to_white_balance_triplet(` `priv` (L6450-6453)

### fn `def _apply_channel_gains_to_white_balance_image(` `priv` (L6479-6482)
- @brief Apply one shared channel-gain vector to all three bracket images.
- @details Broadcast-multiplies RGB channels of each bracket with the same
gain vector to enforce identical white-balance transform across
`(ev_minus, ev_zero, ev_plus)` without stage-local clipping.
- @param np_module {ModuleType} Imported numpy module.
- @param bracket_triplet_rgb_float {tuple[object, object, object]} Normalized RGB bracket tensors.
- @param channel_gains {object} Channel gains vector `(r_gain, g_gain, b_gain)`.
- @return {list[object]} White-balanced bracket tensors in canonical order.
- @satisfies REQ-183, REQ-184, REQ-185, REQ-186, REQ-187, REQ-188

### fn `def _apply_auto_white_balance_stage_float(` `priv` (L6504-6512)
- @brief Apply one channel-gain vector to one RGB image.
- @details Broadcast-multiplies one normalized RGB float image by one
channel-gain vector `(r_gain,g_gain,b_gain)` without stage-local clipping.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float image tensor.
- @param channel_gains {object} Channel gains vector `(r_gain, g_gain, b_gain)`.
- @return {object} White-balanced RGB float image.
- @satisfies REQ-200

### fn `def _apply_white_balance_to_bracket_triplet(` `priv` (L6605-6612)

### fn `def _extract_bracket_images_float(` `priv` (L6698-6703)

### fn `def _order_bracket_paths(bracket_paths)` `priv` (L6739-6764)
- @brief Extract three normalized RGB float brackets from one RAW handle.
- @brief Validate and reorder bracket TIFF paths for deterministic backend argv.
- @details Reuses an optional precomputed normalized linear base tensor when
available, otherwise executes one deterministic linear camera-WB-aware RAW
postprocess call, and derives canonical bracket tensors by NumPy EV
scaling and `[0,1]` clipping without exposing TIFF artifacts outside this
step. Complexity: O(H*W). Side effects: at most one RAW postprocess
invocation.
- @details Enforces exact exposure order `<ev_minus.tif> <ev_zero.tif> <ev_plus.tif>` required by backend command generation and raises on missing labels.
- @param raw_handle {Any} Opened RAW handle from `rawpy.imread`.
- @param np_module {ModuleType} Imported numpy module.
- @param multipliers {tuple[float, float, float]} Ordered exposure multipliers.
- @param base_rgb_float {object|None} Optional precomputed normalized linear RGB float base tensor.
- @param raw_white_balance_mode {str} RAW WB normalization mode selector used when base extraction executes in this function.
- @param bracket_paths {list[Path]} Temporary bracket TIFF paths generated from RAW.
- @return {list[object]} Ordered RGB float bracket tensors.
- @return {list[Path]} Reordered bracket path list in deterministic exposure order.
- @exception ValueError Raised when any expected bracket label is missing.
- @satisfies REQ-010, REQ-157, REQ-158, REQ-159, REQ-160, REQ-203, REQ-204, REQ-205, REQ-206, REQ-207
- @satisfies REQ-062, REQ-112

### fn `def _order_hdr_plus_reference_paths(bracket_paths)` `priv` (L6765-6780)
- @brief Reorder bracket TIFF paths into HDR+ reference-first frame order.
- @details Converts canonical bracket order `(ev_minus, ev_zero, ev_plus)` to source-algorithm frame order `(ev_zero, ev_minus, ev_plus)` so the central bracket acts as temporal reference frame `n=0`, matching HDR+ temporal merge semantics while preserving existing bracket export filenames.
- @param bracket_paths {list[Path]} Temporary bracket TIFF paths generated from RAW.
- @return {list[Path]} Ordered bracket paths in HDR+ reference-first order.
- @satisfies REQ-112

### fn `def _format_external_command_for_log(command)` `priv` (L6781-6796)
- @brief Format one external command argv into deterministic shell-like text.
- @details Converts one sequence of raw argv tokens into one reproducible shell-style command string using POSIX quoting rules so runtime diagnostics can report the exact external command syntax and parameters without relying on shell execution. Complexity: `O(n)` in total token length. Side effects: none.
- @param command {Sequence[str]} External command argv tokens in execution order.
- @return {str} One shell-quoted command string suitable for runtime logging.
- @satisfies REQ-011

### fn `def _run_luminance_hdr_cli(` `priv` (L6797-6804)

### fn `def _build_opencv_radiance_exposure_times(` `priv` (L6880-6883)
- @brief Merge bracket float images into one RGB float image via `luminance-hdr-cli`.
- @details Builds deterministic luminance-hdr-cli argv using EV sequence
centered around zero-reference (`-ev_value,0,+ev_value`) even when extraction
uses non-zero `ev_zero`, serializes float inputs to local float32 TIFFs,
forwards deterministic HDR/TMO arguments including `--ldrTiff 32b` to force
float32 output, emits one runtime log line with the full executed command
syntax and parameters, isolates sidecar artifacts in a backend-specific
temporary directory, then reloads the produced float32 TIFF and normalizes
it back to DNG2JPG RGB float `[0,1]` working format.
- @param bracket_images_float {Sequence[object]} Ordered RGB float bracket tensors.
- @param temp_dir {Path} Temporary workspace root.
- @param imageio_module {ModuleType} Imported imageio module with `imread` and `imwrite`.
- @param np_module {ModuleType} Imported numpy module.
- @param ev_value {float} EV bracket delta used to generate exposure files.
- @param ev_zero {float} Central EV used to generate exposure files.
- @param luminance_options {LuminanceOptions} Luminance backend command controls.
- @return {object} Normalized RGB float merged image.
- @exception subprocess.CalledProcessError Raised when `luminance-hdr-cli` returns non-zero exit status.
- @satisfies REQ-011, REQ-033, REQ-034, REQ-035, REQ-174, REQ-175

### fn `def _build_ev_times_from_ev_zero_and_delta(ev_zero, ev_delta)` `priv` (L6917-6936)
- @brief Build deterministic unit-base exposure times array from EV center and EV delta.
- @details Delegates to the OpenCV radiance exposure-time helper using unit source exposure `1.0` second so tests and compatibility callers can verify deterministic stop-space mapping without EXIF metadata dependency.
- @param ev_zero {float} Central EV used during bracket extraction.
- @param ev_delta {float} EV bracket delta used during bracket extraction.
- @return {object} `numpy.float32` vector with length `3`.
- @exception RuntimeError Raised when numpy dependency is unavailable.
- @satisfies REQ-109, REQ-142

### fn `def _normalize_opencv_hdr_to_unit_range(np_module, hdr_rgb_float32)` `priv` (L6937-6962)
- @brief Normalize OpenCV HDR tensor to unit range with deterministic bounds.
- @details Normalizes arbitrary OpenCV HDR or fusion output to one congruent RGB float contract. Negative and non-finite values are cleared via `np.maximum(0.0)` floor, and values above unit range are scaled down by global maximum; no final `[0,1]` clipping is applied because the floor-and-scale sequence guarantees the output is bounded within `[0,1]` deterministically.
- @param np_module {ModuleType} Imported numpy module.
- @param hdr_rgb_float32 {object} OpenCV HDR or fusion RGB tensor.
- @return {object} Normalized RGB float tensor bounded within `[0,1]` by floor-and-scale normalization.
- @satisfies REQ-110, REQ-143, REQ-144

### fn `def _run_opencv_merge_mertens(` `priv` (L6963-6968)

### fn `def _estimate_opencv_camera_response(` `priv` (L6998-7002)
- @brief Execute OpenCV Mertens exposure fusion path.
- @details Runs `cv2.createMergeMertens().process(...)` on RGB float
brackets that already share one identical merge-gamma transfer curve,
rescales the float result by `255` to match OpenCV exposure-fusion
brightness semantics observed on `uint8` inputs, optionally applies OpenCV
simple gamma tonemap with user-configured gamma, and then normalizes the
result to the repository RGB float contract.
- @param cv2_module {ModuleType} Imported OpenCV module.
- @param np_module {ModuleType} Imported numpy module.
- @param exposures_float {list[object]} Ordered RGB float bracket tensors preconditioned with one identical merge-gamma transfer.
- @param tonemap_enabled {bool} `True` enables simple OpenCV tone mapping.
- @param tonemap_gamma {float} Positive gamma passed to `createTonemap`.
- @return {object} Normalized RGB float tensor.
- @satisfies REQ-108, REQ-110, REQ-143, REQ-144, REQ-154

### fn `def _run_opencv_merge_radiance(` `priv` (L7031-7038)
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

### fn `def _normalize_debevec_hdr_to_unit_range(np_module, hdr_rgb_float32, white_point_percentile)` `priv` (L7102-7121)
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

### fn `def _run_opencv_tonemap_backend(` `priv` (L7122-7127)

### fn `def _derive_opencv_tonemap_enabled(postprocess_options)` `priv` (L7206-7219)
- @brief Execute OpenCV-Tonemap backend on ev-zero only.
- @brief Resolve OpenCV-Tonemap backend enable state from parsed options.
- @details Selects bracket index `1` (`ev_zero`) as the only tone-map input,
dispatches exactly one OpenCV tone-map implementation (`Drago`, `Reinhard`,
or `Mantiuk`) with `gamma_inv` resolved as the inverse merge-gamma curve
parameter, preserves float-domain dynamic range without backend-local
clipping, and applies merge gamma strictly as backend-final step.
- @details Returns `True` only when one OpenCV-Tonemap selector payload is present in postprocess options. This helper centralizes backend-enable derivation for parse output compatibility and run-time dispatch.
- @param bracket_images_float {Sequence[object]} Ordered RGB float bracket tensors `(ev_minus, ev_zero, ev_plus)`.
- @param opencv_tonemap_options {OpenCvTonemapOptions} OpenCV-Tonemap selector and knob payload.
- @param auto_adjust_dependencies {tuple[ModuleType, ModuleType]|None} Optional `(cv2, numpy)` dependency tuple.
- @param resolved_merge_gamma {ResolvedMergeGamma} Backend-final merge-output transfer payload.
- @param merge_debug_snapshots {dict|None} Optional mutable mapping populated with merge-stage debug images.
- @param postprocess_options {PostprocessOptions} Parsed postprocess payload.
- @return {object} OpenCV-Tonemap RGB float tensor after backend-final merge gamma.
- @return {bool} `True` when OpenCV-Tonemap backend is selected.
- @exception RuntimeError Raised when OpenCV/numpy dependencies are missing.
- @exception ValueError Raised when bracket payload or selector is invalid.
- @satisfies REQ-148, REQ-192, REQ-193, REQ-194, REQ-195, REQ-196, REQ-197, REQ-198
- @satisfies REQ-189, REQ-190

### fn `def _run_opencv_merge_backend(` `priv` (L7220-7228)

### fn `def _hdrplus_box_down2_float32(np_module, frames_float32)` `priv` (L7325-7353)
- @brief Merge bracket float images into one RGB float image via OpenCV.
- @brief Downsample HDR+ scalar frames with 2x2 box averaging in float domain.
- @details Accepts three RGB float bracket tensors ordered as `(ev_minus,
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
- @details Ports `box_down2` from `util.cpp` for repository HDR+ execution by reflect-padding odd image sizes to even extents, summing each 2x2 region, and multiplying by `0.25` once. Input and output stay in float domain to preserve the repository-wide HDR+ internal arithmetic contract.
- @param bracket_images_float {Sequence[object]} Ordered RGB float bracket tensors.
- @param ev_value {float} EV bracket delta used to generate exposure files.
- @param ev_zero {float} Central EV used to generate exposure files.
- @param source_exposure_time_seconds {float|None} Positive EXIF `ExposureTime` in seconds for the extracted linear base image.
- @param opencv_merge_options {OpenCvMergeOptions} OpenCV merge backend controls.
- @param auto_adjust_dependencies {tuple[ModuleType, ModuleType]|None} Optional `(cv2, numpy)` dependency tuple.
- @param resolved_merge_gamma {ResolvedMergeGamma} Backend-final merge-output transfer payload.
- @param merge_debug_snapshots {dict|None} Optional mutable mapping populated with merge-stage debug images.
- @param np_module {ModuleType} Imported numpy module.
- @param frames_float32 {object} Scalar float tensor with shape `(N,H,W)`.
- @return {object} Normalized RGB float merged image.
- @return {object} Downsampled float tensor with shape `(N,ceil(H/2),ceil(W/2))`.
- @exception RuntimeError Raised when OpenCV/numpy dependencies are missing or bracket payloads are invalid.
- @satisfies REQ-107, REQ-108, REQ-109, REQ-110, REQ-142, REQ-143, REQ-144, REQ-148, REQ-152, REQ-153, REQ-154, REQ-160, REQ-161, REQ-162, REQ-170
- @satisfies REQ-112, REQ-113, REQ-129

### fn `def _hdrplus_gauss_down4_float32(np_module, frames_float32)` `priv` (L7354-7400)
- @brief Downsample HDR+ scalar frames by `4` with the source 5x5 Gaussian kernel.
- @details Ports `gauss_down4` from `util.cpp`: applies the integer kernel with coefficients summing to `159`, uses reflect padding to emulate `mirror_interior`, then samples every fourth pixel in both axes. Input and output remain float to keep HDR+ alignment math in floating point.
- @param np_module {ModuleType} Imported numpy module.
- @param frames_float32 {object} Scalar float tensor with shape `(N,H,W)`.
- @return {object} Downsampled float tensor with shape `(N,ceil(H/4),ceil(W/4))`.
- @satisfies REQ-112, REQ-113, REQ-129

### fn `def _hdrplus_build_scalar_proxy_float32(np_module, frames_rgb_float32, hdrplus_options)` `priv` (L7401-7434)
- @brief Convert RGB bracket tensors into the scalar HDR+ source-domain proxy.
- @details Adapts normalized RGB float32 brackets to the original single-channel HDR+ merge domain without any uint16 staging. Mode `rggb` approximates Bayer energy with weights `(0.25, 0.5, 0.25)`; mode `bt709` uses luminance weights `(0.2126, 0.7152, 0.0722)`; mode `mean` uses arithmetic RGB average. Output remains normalized float32 to preserve downstream alignment and merge precision.
- @param np_module {ModuleType} Imported numpy module.
- @param frames_rgb_float32 {object} Normalized RGB float32 frame tensor with shape `(N,H,W,3)`.
- @param hdrplus_options {HdrPlusOptions} HDR+ proxy/alignment/temporal controls.
- @return {object} Normalized scalar float32 tensor with shape `(N,H,W)`.
- @satisfies REQ-112, REQ-126, REQ-128, REQ-129, REQ-140

### fn `def _hdrplus_compute_tile_start_positions(np_module, axis_length, tile_stride, pad_margin)` `priv` (L7435-7455)
- @brief Compute HDR+ tile start coordinates for one image axis.
- @details Reproduces the source overlap geometry used by the Python HDR+ port: tile starts advance by `tile_stride` and include the leading virtual tile at `-tile_stride`, represented by positive indices inside the padded tensor.
- @param np_module {ModuleType} Imported numpy module.
- @param axis_length {int} Source image extent for the selected axis.
- @param tile_stride {int} Tile stride in pixels.
- @param pad_margin {int} Reflect padding added on both sides of the axis.
- @return {object} `int32` axis start-position vector with shape `(T,)`.
- @satisfies REQ-112, REQ-115

### fn `def _hdrplus_trunc_divide_int32(np_module, values_int32, divisor)` `priv` (L7456-7474)
- @brief Divide signed HDR+ offsets with truncation toward zero.
- @details Emulates C++ integer division semantics used by the source code for negative offsets, which differs from Python floor division. This helper is required for the source-consistent `offset / 2` conversion between full and downsampled tile domains.
- @param np_module {ModuleType} Imported numpy module.
- @param values_int32 {object} Signed integer tensor.
- @param divisor {int} Positive divisor.
- @return {object} Signed integer tensor truncated toward zero.
- @satisfies REQ-113, REQ-114

### fn `def _hdrplus_compute_alignment_bounds(search_radius)` `priv` (L7475-7499)
- @brief Derive source-equivalent hierarchical HDR+ alignment bounds.
- @details Reconstructs the source `min_3/min_2/min_1` and `max_3/max_2/max_1` recurrences for the fixed three-level pyramid and search offsets `[-search_radius, search_radius-1]`.
- @param search_radius {int} Per-layer alignment search radius.
- @return {tuple[tuple[int, int], ...]} Bound pairs in coarse-to-fine order.
- @satisfies REQ-113

### fn `def _hdrplus_compute_alignment_margin(search_radius, divisor=1)` `priv` (L7500-7518)
- @brief Compute safe reflect-padding margin for HDR+ alignment offsets.
- @details Converts the fixed three-level search radius into a conservative full-resolution offset bound and optionally scales it down for lower pyramid levels via truncation-toward-zero division.
- @param search_radius {int} Per-layer alignment search radius.
- @param divisor {int} Positive scale divisor applied to the full-resolution bound.
- @return {int} Non-negative padding margin in pixels.
- @satisfies REQ-113

### fn `def _hdrplus_extract_overlapping_tiles(` `priv` (L7519-7524)

### fn `def _hdrplus_extract_aligned_tiles(` `priv` (L7577-7583)

### fn `def _hdrplus_align_layer(` `priv` (L7656-7663)
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

### fn `def _hdrplus_align_layers(np_module, scalar_frames, hdrplus_options)` `priv` (L7753-7840)
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

### fn `def _hdrplus_resolve_temporal_runtime_options(hdrplus_options)` `priv` (L7841-7865)
- @brief Remap HDR+ temporal CLI knobs for normalized float32 distance inputs.
- @details Converts user-facing temporal controls defined on the historical 16-bit code-domain into runtime controls consumed by normalized float32 `[0,1]` tile distances. The factor and floor are scaled by `1/65535` through pure linear rescaling; the cutoff remains expressed in the post-normalized comparison space so the current inverse-distance weight curve remains numerically equivalent while diagnostics still print the original CLI values.
- @param hdrplus_options {HdrPlusOptions} User-facing HDR+ proxy/alignment/temporal controls.
- @return {HdrPlusTemporalRuntimeOptions} Normalized runtime temporal controls.
- @satisfies REQ-114, REQ-131, REQ-138

### fn `def _hdrplus_compute_temporal_weights(` `priv` (L7866-7870)

### fn `def _hdrplus_merge_temporal_rgb(` `priv` (L7951-7957)
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

### fn `def _hdrplus_merge_spatial_rgb(np_module, temporal_tiles, width, height)` `priv` (L8006-8078)
- @brief Merge HDR+ full-resolution RGB tiles across the temporal dimension.
- @brief Blend HDR+ temporally merged tiles with raised-cosine overlap.
- @details Ports the temporal accumulation phase of `merge.cpp`: extracts the
reference `32x32` tile stack, applies resolved full-resolution alignment
offsets to alternate RGB frames, normalizes all contributions with the
shared per-tile `total_weight`, and preserves float arithmetic until the
spatial merge stage.
- @details Ports `merge_spatial` from `merge.cpp`: builds source raised-cosine weights over `32` samples, gathers four overlapping tiles for each output pixel using source index formulas derived from `tile_0`, `tile_1`, `idx_0`, and `idx_1`, then computes one weighted RGB sum and returns the continuous normalized float32 result without stage-local `[0,1]` clipping or quantized lattice projection.
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

### fn `def _run_hdr_plus_merge(` `priv` (L8079-8084)

### fn `def _convert_compression_to_quality(jpg_compression)` `priv` (L8180-8190)
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
- @param resolved_merge_gamma {ResolvedMergeGamma} Backend-final merge-output transfer payload.
- @param merge_debug_snapshots {dict|None} Optional mutable mapping populated with merge-stage debug images.
- @param jpg_compression {int} JPEG compression level.
- @return {object} Normalized RGB float32 merged image.
- @return {int} Pillow quality value in `[1, 100]`.
- @exception RuntimeError Raised when bracket payloads are invalid.
- @satisfies REQ-111, REQ-112, REQ-113, REQ-114, REQ-115, REQ-126, REQ-129, REQ-138, REQ-139, REQ-140, REQ-148, REQ-170
- @satisfies REQ-065, REQ-066

### fn `def _collect_missing_external_executables(` `priv` (L8191-8193)

### fn `def _resolve_auto_adjust_dependencies()` `priv` (L8212-8241)
- @brief Collect missing external executables required by resolved runtime options.
- @brief Resolve OpenCV and numpy runtime dependencies for image-domain stages.
- @details Evaluates the selected backend to derive the exact external
executable set needed by this invocation, then probes each command on
`PATH` and returns a deterministic missing-command tuple for preflight
failure reporting before processing starts.
- @details Imports `cv2` and `numpy` modules required by the auto-adjust pipeline, the OpenCV HDR backend, auto-white-balance stage execution, and the automatic EV-zero evaluation, and returns `None` with deterministic error output when dependencies are missing.
- @param enable_luminance {bool} `True` when luminance backend is selected.
- @return {tuple[str, ...]} Ordered tuple of missing executable labels.
- @return {tuple[ModuleType, ModuleType]|None} `(cv2_module, numpy_module)` when available; `None` on dependency failure.
- @satisfies CTN-005
- @satisfies REQ-037, REQ-059, REQ-073, REQ-075, REQ-184, REQ-185, REQ-186

### fn `def _resolve_numpy_dependency()` `priv` (L8242-8261)
- @brief Resolve numpy runtime dependency for float-interface image stages.
- @details Imports `numpy` required by bracket float normalization, in-memory merge orchestration, float-domain post-merge stages, and TIFF16 adaptation helpers, and returns `None` with deterministic error output when the dependency is missing.
- @return {ModuleType|None} Imported numpy module; `None` on dependency failure.
- @satisfies REQ-010, REQ-012, REQ-059, REQ-100

### fn `def _to_float32_image_array(np_module, image_data)` `priv` (L8262-8293)
- @brief Convert image tensor to normalized `float32` range `[0,1]`.
- @details Normalizes integer or float image payloads into RGB-stage `float32` tensors. `uint16` uses `/65535`, `uint8` uses `/255`, floating inputs outside `[0,1]` are interpreted on the closest integer image scale (`255` or `65535`) and then clamped.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image tensor.
- @return {object} Normalized `float32` image tensor.
- @satisfies REQ-010, REQ-012, REQ-106

### fn `def _normalize_float_rgb_image(np_module, image_data)` `priv` (L8294-8321)
- @brief Normalize image payload into RGB `float32` tensor.
- @details Converts input image payload to normalized `float32`, expands grayscale to one channel, replicates single-channel input to RGB, drops alpha from RGBA input, and returns exactly three channels for deterministic float-stage processing.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image tensor.
- @return {object} RGB `float32` tensor with shape `(H,W,3)` and range `[0,1]`.
- @exception ValueError Raised when normalized image has unsupported shape.
- @satisfies REQ-010, REQ-012, REQ-106

### fn `def _prepare_postprocess_entry_rgb_float(np_module, image_data)` `priv` (L8322-8349)
- @brief Adapt postprocess entry payload to RGB float32 without unconditional clipping.
- @details Preserves merge-backend float payload dynamic range by bypassing normalization/clipping for float-typed inputs and normalizes only non-float image encodings (`uint8`, `uint16`, or integer-like payloads) into the repository RGB float working domain before postprocess stages execute.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Postprocess entry image payload.
- @return {object} RGB `float32` tensor with shape `(H,W,3)`.
- @exception ValueError Raised when input shape is unsupported.
- @satisfies REQ-012, REQ-134, REQ-214

### fn `def _write_rgb_float_tiff16(imageio_module, np_module, output_path, image_rgb_float)` `priv` (L8350-8376)
- @brief Serialize one RGB float tensor as 16-bit TIFF payload.
- @details Normalizes the source image to RGB float, clamps to `[0,1]` before quantization to ensure correct uint16 scaling when upstream pipeline stages emit unbounded float values, converts to `uint16`, and writes the result through `imageio`. This helper localizes float-to-TIFF16 adaptation inside steps that depend on file-based tools.
- @param imageio_module {ModuleType} Imported imageio module with `imwrite`.
- @param np_module {ModuleType} Imported numpy module.
- @param output_path {Path} Output TIFF path.
- @param image_rgb_float {object} RGB float tensor, potentially unbounded.
- @return {None} Side effects only.
- @satisfies REQ-106

### fn `def _write_rgb_float_tiff32(imageio_module, np_module, output_path, image_rgb_float)` `priv` (L8377-8401)
- @brief Serialize one RGB float tensor as float32 TIFF payload.
- @details Normalizes the source image to RGB float32 `[0,1]` and writes it directly as a float32 TIFF through `imageio`, preserving full floating-point precision without quantization. Used by the luminance backend to provide float32 bracket inputs to `luminance-hdr-cli`.
- @param imageio_module {ModuleType} Imported imageio module with `imwrite`.
- @param np_module {ModuleType} Imported numpy module.
- @param output_path {Path} Output TIFF path.
- @param image_rgb_float {object} RGB float tensor in `[0,1]`.
- @return {None} Side effects only.
- @satisfies REQ-011, REQ-174

### fn `def _write_debug_rgb_float_tiff(` `priv` (L8402-8407)

### fn `def _build_debug_artifact_context(output_jpg, input_dng, postprocess_options)` `priv` (L8437-8457)
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

### fn `def _write_hdr_merge_debug_checkpoints(` `priv` (L8458-8463)

### fn `def _format_debug_ev_suffix_value(ev_value)` `priv` (L8522-8539)
- @brief Persist HDR merge boundary checkpoints when debug mode is enabled.
- @brief Format one EV value token for debug checkpoint filenames.
- @details Emits merge-stage checkpoints in execution order. When backend code
provides explicit merge-gamma boundaries, this helper writes pre-gamma,
post-gamma, and final-HDR outputs. Otherwise it writes only final-HDR output.
- @details Emits a signed decimal representation that preserves quarter-step EV precision while keeping integer-valued stops on one decimal place for stable filenames such as `+1.0`, `+0.5`, or `-0.25`.
- @param imageio_module {ModuleType} Imported imageio module with `imwrite`.
- @param np_module {ModuleType} Imported numpy module.
- @param debug_context {DebugArtifactContext|None} Persistent debug output metadata; `None` disables emission.
- @param merged_image_float {object} Final HDR merge output forwarded to post-merge processing.
- @param merge_debug_snapshots {dict|None} Optional mutable mapping with backend-provided merge checkpoint tensors.
- @param ev_value {float} EV value expressed in stop units.
- @return {None} Side effects only.
- @return {str} Signed decimal token for debug filename suffixes.
- @satisfies REQ-148
- @satisfies REQ-147, REQ-148

### fn `def _materialize_bracket_tiffs_from_float(` `priv` (L8540-8544)

### fn `def _to_uint8_image_array(np_module, image_data)` `priv` (L8574-8624)
- @brief Write canonical bracket TIFF files from RGB float images.
- @brief Convert image tensor to `uint8` range `[0,255]`.
- @details Emits `ev_minus.tif`, `ev_zero.tif`, and `ev_plus.tif` into the
provided temporary directory using float32 TIFF encoding derived from
normalized RGB float images. The helper is used only by file-oriented merge
backends requiring float32 TIFF inputs.
- @details Normalizes integer or float image payloads into `uint8` preserving relative brightness scale: `uint16` uses `/257`, normalized float arrays in `[0,1]` use `*255`, non-finite float samples are replaced with `0.0`, and all paths clamp to inclusive byte range.
- @param imageio_module {ModuleType} Imported imageio module with `imwrite`.
- @param np_module {ModuleType} Imported numpy module.
- @param bracket_images_float {Sequence[object]} Ordered RGB float bracket tensors.
- @param temp_dir {Path} Temporary directory for TIFF artifacts.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image tensor.
- @return {list[Path]} Ordered canonical TIFF paths.
- @return {object} `uint8` image tensor.
- @satisfies REQ-011, REQ-034, REQ-174
- @satisfies REQ-066, REQ-090

### fn `def _to_uint16_image_array(np_module, image_data)` `priv` (L8625-8673)
- @brief Convert image tensor to `uint16` range `[0,65535]`.
- @details Normalizes integer or float image payloads into `uint16` preserving relative brightness scale: `uint8` uses `*257`, normalized float arrays in `[0,1]` use `*65535`, non-finite float samples are replaced with `0.0`, and all paths clamp to inclusive 16-bit range.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image tensor.
- @return {object} `uint16` image tensor.
- @satisfies REQ-066, REQ-090

### fn `def _apply_post_gamma_float(np_module, image_rgb_float, gamma_value)` `priv` (L8674-8699)
- @brief Apply static post-gamma over RGB float tensor.
- @details Executes the legacy static gamma equation on RGB float data (`output = input^(1/gamma)`) without intermediate stage-local `[0,1]` clipping, preserving float headroom for downstream pipeline stages.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float image tensor.
- @param gamma_value {float} Static post-gamma factor.
- @return {object} RGB float tensor after gamma stage without stage-local clipping.
- @satisfies REQ-012, REQ-013, REQ-132, REQ-134

### fn `def _build_auto_post_gamma_lut_float(np_module, gamma_value, lut_size)` `priv` (L8700-8716)
- @brief Build one floating-point LUT for auto-gamma mapping.
- @details Generates one evenly sampled domain in `[0,1]` and evaluates `output = input^gamma` over that domain using float precision only.
- @param np_module {ModuleType} Imported numpy module.
- @param gamma_value {float} Resolved auto-gamma exponent.
- @param lut_size {int} LUT sample count (`>=2`).
- @return {tuple[object, object]} LUT domain and mapped values as float arrays.
- @satisfies REQ-178

### fn `def _ensure_three_channel_float_array_no_range_adjust(np_module, image_data)` `priv` (L8717-8743)
- @brief Normalize one image payload to three-channel float tensor without range clipping.
- @details Converts numeric image payloads into RGB `float64` while preserving original numeric range, expands grayscale and single-channel input to RGB, and drops alpha channels.
- @param np_module {ModuleType} Imported numpy module.
- @param image_data {object} Numeric image payload.
- @return {object} RGB `float64` tensor with shape `(H,W,3)`.
- @exception ValueError Raised when the input shape cannot be normalized to RGB.
- @satisfies REQ-178

### fn `def _apply_auto_post_gamma_float(np_module, image_rgb_float, post_gamma_auto_options)` `priv` (L8744-8788)
- @brief Apply mean-luminance anchored auto-gamma over RGB float tensor.
- @details Computes grayscale mean luminance from normalized RGB float input, solves `gamma=log(target_gray)/log(mean_luminance)` when mean luminance is strictly within configured guards, otherwise returns input unchanged with resolved gamma `1.0`, then applies one floating-point LUT-domain mapping `output=input^gamma` without quantized intermediates or stage-local clipping.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float image tensor.
- @param post_gamma_auto_options {PostGammaAutoOptions} Auto-gamma replacement stage knobs.
- @return {tuple[object, float]} RGB float tensor and resolved gamma value.
- @satisfies REQ-177, REQ-178

### fn `def _apply_brightness_float(np_module, image_rgb_float, brightness_factor)` `priv` (L8789-8811)
- @brief Apply static brightness factor on RGB float tensor.
- @details Executes the legacy brightness equation on RGB float data (`output = factor * input`) without intermediate stage-local `[0,1]` clipping, preserving float headroom for downstream pipeline stages.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float image tensor.
- @param brightness_factor {float} Brightness scale factor.
- @return {object} RGB float tensor after brightness stage without stage-local clipping.
- @satisfies REQ-012, REQ-013, REQ-132, REQ-134

### fn `def _apply_contrast_float(np_module, image_rgb_float, contrast_factor)` `priv` (L8812-8836)
- @brief Apply static contrast factor on RGB float tensor.
- @details Executes the legacy contrast equation on RGB float data (`output = mean + factor * (input - mean)`), where `mean` remains the per-channel global image average, without stage-local clipping.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float image tensor.
- @param contrast_factor {float} Contrast interpolation factor.
- @return {object} RGB float tensor after contrast stage without stage-local clipping.
- @satisfies REQ-012, REQ-013, REQ-132, REQ-134

### fn `def _apply_saturation_float(np_module, image_rgb_float, saturation_factor)` `priv` (L8837-8867)
- @brief Apply static saturation factor on RGB float tensor.
- @details Executes the legacy saturation equation on RGB float data using BT.709 grayscale (`output = gray + factor * (input - gray)`) without intermediate stage-local `[0,1]` clipping, preserving float headroom for downstream pipeline stages.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float image tensor.
- @param saturation_factor {float} Saturation interpolation factor.
- @return {object} RGB float tensor after saturation stage without stage-local clipping.
- @satisfies REQ-012, REQ-013, REQ-132, REQ-134

### fn `def _apply_static_postprocess_float(` `priv` (L8868-8873)

### fn `def _to_linear_srgb(np_module, image_srgb)` `priv` (L8990-9007)
- @brief Execute static postprocess chain with float-only stage internals.
- @brief Convert sRGB tensor to linear-sRGB tensor.
- @details Accepts one normalized RGB float tensor and executes static
postprocess in strict order `gamma->brightness->contrast->saturation`,
where gamma is either numeric static gamma or auto-gamma replacement when
`--post-gamma=auto` is selected. Bypasses numeric static stage when all
numeric factors are neutral (`1.0`), executes only non-neutral numeric
substages in order, runs all intermediate calculations in float domain
without stage-local `[0,1]` clipping on gamma/brightness/saturation
stages, optionally emits persistent debug TIFF checkpoints after each
executed static substage, and eliminates the prior float->uint16->float
adaptation cycle from this step.
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
- @satisfies REQ-012, REQ-013, REQ-132, REQ-134, REQ-148, REQ-176, REQ-177, REQ-178
- @satisfies REQ-090, REQ-099

### fn `def _from_linear_srgb(np_module, image_linear)` `priv` (L9008-9025)
- @brief Convert linear-sRGB tensor to sRGB tensor.
- @details Applies IEC 61966-2-1 piecewise forward transfer function on normalized linear channel values in `[0,1]`.
- @param np_module {ModuleType} Imported numpy module.
- @param image_linear {object} Float image tensor in linear-sRGB domain `[0,1]`.
- @return {object} Float image tensor in sRGB domain `[0,1]`.
- @satisfies REQ-090, REQ-099

### fn `def _compute_bt709_luminance(np_module, linear_rgb)` `priv` (L9026-9043)
- @brief Compute BT.709 linear luminance from linear RGB tensor.
- @details Computes per-pixel luminance using BT.709 coefficients with RGB channel order: `0.2126*R + 0.7152*G + 0.0722*B`.
- @param np_module {ModuleType} Imported numpy module.
- @param linear_rgb {object} Linear-sRGB float tensor with shape `H,W,3`.
- @return {object} Float luminance tensor with shape `H,W`.
- @satisfies REQ-090, REQ-099

### fn `def _analyze_luminance_key(np_module, luminance, eps)` `priv` (L9044-9083)
- @brief Analyze luminance distribution and classify scene key.
- @details Computes log-average luminance, median, percentile tails, and clip proxies on normalized BT.709 luminance and classifies scene as `low-key`, `normal-key`, or `high-key` using the thresholds from `/tmp/auto-brightness.py`.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance {object} BT.709 luminance float tensor in `[0, 1]`.
- @param eps {float} Positive numerical stability guard.
- @return {dict[str, float|str]} Key analysis dictionary with key type, central statistics, tails, and clipping proxies.
- @satisfies REQ-050, REQ-103, REQ-121

### fn `def _choose_auto_key_value(key_analysis, auto_brightness_options)` `priv` (L9084-9129)
- @brief Select Reinhard key value from key-analysis metrics.
- @details Chooses base key by scene class (`0.09/0.18/0.36`) and applies conservative under/over-exposure adaptation bounded by configured automatic key limits and automatic boost factor.
- @param key_analysis {dict[str, float|str]} Luminance key-analysis dictionary.
- @param auto_brightness_options {AutoBrightnessOptions} Parsed auto-brightness parameters.
- @return {float} Clamped key value `a`.
- @satisfies REQ-050, REQ-103, REQ-122

### fn `def _reinhard_global_tonemap_luminance(` `priv` (L9130-9135)

### fn `def _luminance_preserving_desaturate_to_fit(np_module, rgb_linear, luminance, eps)` `priv` (L9169-9196)
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

### fn `def _apply_mild_local_contrast_bgr_uint16(cv2_module, np_module, image_bgr_uint16, options)` `priv` (L9197-9235)
- @brief Apply legacy uint16 CLAHE micro-contrast on 16-bit Y channel.
- @details Converts BGR16 to YCrCb, runs CLAHE on 16-bit Y with configured clip/tile controls, then blends original and CLAHE outputs using configured local-contrast strength. Retained as quantized reference implementation for float-domain CLAHE-luma equivalence verification.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param image_bgr_uint16 {object} BGR uint16 image tensor.
- @param options {AutoAdjustOptions} Parsed auto-adjust CLAHE options.
- @return {object} BGR uint16 image tensor after optional local contrast.
- @satisfies REQ-125, REQ-137

### fn `def _quantize_clahe_luminance_bins(np_module, luminance_values, histogram_size)` `priv` (L9236-9261)
- @brief Map normalized luminance samples onto CLAHE histogram addresses.
- @details Computes OpenCV-compatible histogram bin addresses from normalized float luminance without materializing an intermediate uint16 image plane. Rounds against the `[0, hist_size-1]` lattice preserved by the historical uint16 reference so tile histograms remain semantically aligned while the active path stays in float-domain image buffers.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_values {object} Normalized luminance tensor in `[0,1]`.
- @param histogram_size {int} Number of CLAHE histogram bins.
- @return {object} `int32` tensor of histogram bin addresses.
- @satisfies REQ-136, REQ-137

### fn `def _build_clahe_float_tile_histogram(np_module, luminance_tile, histogram_size)` `priv` (L9262-9283)
- @brief Build one CLAHE histogram from a float luminance tile.
- @details Converts one normalized luminance tile into one dense histogram using the preserved 16-bit CLAHE lattice and returns per-bin population counts for downstream clipping and CDF generation.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_tile {object} Tile luminance tensor in `[0,1]`.
- @param histogram_size {int} Number of CLAHE histogram bins.
- @return {object} Dense histogram tensor with one count per CLAHE bin.
- @satisfies REQ-136, REQ-137

### fn `def _clip_clahe_histogram(np_module, histogram, clip_limit, tile_population)` `priv` (L9284-9331)
- @brief Clip one CLAHE histogram with OpenCV-compatible redistribution.
- @details Normalizes the user clip limit by tile population and histogram size, applies the same integer clip ceiling used by OpenCV CLAHE, then redistributes clipped mass through uniform batch fill plus residual stride increments. Output preserves the original total tile population.
- @param np_module {ModuleType} Imported numpy module.
- @param histogram {object} Dense tile histogram tensor.
- @param clip_limit {float} User-provided CLAHE clip limit.
- @param tile_population {int} Number of pixels contained in the tile.
- @return {object} Clipped histogram tensor after redistributed excess mass.
- @satisfies REQ-136, REQ-137

### fn `def _build_clahe_float_lut(np_module, histogram, tile_population)` `priv` (L9332-9351)
- @brief Convert one clipped CLAHE histogram into one normalized LUT.
- @details Builds one cumulative distribution from the clipped histogram and normalizes it by tile population so the resulting lookup table maps each histogram address directly into one float luminance output in `[0,1]`. Uses `float32` storage to limit per-tile memory while preserving normalized luminance precision required by the active float pipeline.
- @param np_module {ModuleType} Imported numpy module.
- @param histogram {object} Clipped histogram tensor.
- @param tile_population {int} Number of pixels contained in the tile.
- @return {object} Normalized CLAHE lookup-table tensor in `[0,1]`.
- @satisfies REQ-136, REQ-137

### fn `def _pad_clahe_luminance_float(np_module, luminance_float, tile_grid_size)` `priv` (L9352-9390)
- @brief Pad luminance plane to an even CLAHE tile lattice.
- @details Reproduces OpenCV CLAHE tiling rules by extending only the bottom and right borders to the next multiple of the configured tile grid. Uses reflect-101 semantics when the axis length is greater than one and edge replication for single-pixel axes where reflection is undefined.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Luminance tensor in `[0,1]`.
- @param tile_grid_size {tuple[int, int]} OpenCV-compatible tile-grid tuple.
- @return {tuple[object, int, int]} Padded luminance tensor, tile height, and tile width.
- @satisfies REQ-136, REQ-137

### fn `def _build_clahe_axis_interpolation(np_module, axis_length, tile_size, tile_count)` `priv` (L9391-9418)
- @brief Precompute CLAHE neighbor indices and bilinear weights per axis.
- @details Recreates OpenCV CLAHE interpolation coordinates by locating each sample relative to adjacent tile centers using `coord / tile_size - 0.5`. Returned weights remain unchanged after edge clamping so border pixels map to the closest tile exactly as the historical uint16 reference does.
- @param np_module {ModuleType} Imported numpy module.
- @param axis_length {int} Number of samples on the axis.
- @param tile_size {int} Size of each padded tile on the axis.
- @param tile_count {int} Number of tiles on the axis.
- @return {tuple[object, object, object, object]} Lower indices, upper indices, lower weights, and upper weights.
- @satisfies REQ-136, REQ-137

### fn `def _build_clahe_tile_luts_float(np_module, luminance_float, clip_limit, tile_grid_size, histogram_size)` `priv` (L9419-9470)
- @brief Build per-tile CLAHE lookup tables from float luminance input.
- @details Pads the luminance plane to the CLAHE lattice, then builds one histogram, clipped histogram, and normalized LUT per tile in call order. Stores LUTs in one dense `(tiles_y, tiles_x, hist_size)` tensor used by the bilinear tile interpolation stage.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Luminance tensor in `[0,1]`.
- @param clip_limit {float} User-provided CLAHE clip limit.
- @param tile_grid_size {tuple[int, int]} OpenCV-compatible tile-grid tuple.
- @param histogram_size {int} Number of CLAHE histogram bins.
- @return {tuple[object, int, int]} LUT tensor, tile height, and tile width.
- @satisfies REQ-136, REQ-137

### fn `def _interpolate_clahe_bilinear_float(np_module, luminance_float, tile_luts, tile_height, tile_width)` `priv` (L9471-9523)
- @brief Bilinearly interpolate CLAHE LUT outputs across adjacent tiles.
- @details Samples the four neighboring tile LUTs for each original-image row using OpenCV-compatible tile-center geometry and blends those per-pixel outputs with bilinear weights. Processes one row at a time to avoid one extra full-image histogram-address buffer.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Original luminance tensor in `[0,1]`.
- @param tile_luts {object} Per-tile LUT tensor.
- @param tile_height {int} Padded tile height.
- @param tile_width {int} Padded tile width.
- @return {object} Equalized luminance tensor in `[0,1]`.
- @satisfies REQ-136, REQ-137

### fn `def _apply_clahe_luminance_float(np_module, luminance_float, clip_limit, tile_grid_size)` `priv` (L9524-9555)
- @brief Execute native float-domain CLAHE on one luminance plane.
- @details Builds per-tile histograms and normalized LUTs with OpenCV-like clip-limit normalization, then reconstructs one equalized luminance plane via bilinear interpolation between adjacent tiles. Keeps the luminance plane in normalized float representation throughout the active path.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Luminance tensor in `[0,1]`.
- @param clip_limit {float} User-provided CLAHE clip limit.
- @param tile_grid_size {tuple[int, int]} OpenCV-compatible tile-grid tuple.
- @return {object} Equalized luminance tensor in `[0,1]`.
- @satisfies REQ-136, REQ-137

### fn `def _reconstruct_rgb_from_ycrcb_luma_float(cv2_module, np_module, luminance_float, cr_channel, cb_channel)` `priv` (L9556-9579)
- @brief Reconstruct RGB float output from YCrCb float channels.
- @details Creates one float32 YCrCb tensor from one equalized luminance plane plus preserved Cr/Cb channels, converts it back to RGB with OpenCV color transforms only, and returns one clamped float64 RGB tensor for downstream blending in the auto-adjust pipeline.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param luminance_float {object} Equalized luminance tensor in `[0,1]`.
- @param cr_channel {object} Preserved YCrCb Cr channel.
- @param cb_channel {object} Preserved YCrCb Cb channel.
- @return {object} Reconstructed RGB float tensor in `[0,1]`.
- @satisfies REQ-136, REQ-137

### fn `def _apply_clahe_luma_rgb_float(cv2_module, np_module, image_rgb_float, auto_adjust_options)` `priv` (L9580-9629)
- @brief Apply CLAHE-luma local contrast directly on RGB float buffers.
- @details Converts normalized RGB float input to float YCrCb, runs one native NumPy CLAHE implementation on the luminance plane with OpenCV-compatible tiling, clip-limit normalization, clipping, redistribution, and bilinear tile interpolation, then reconstructs one RGB float CLAHE candidate from preserved chroma plus mapped luminance and blends that candidate with the original float RGB image using configured strength. OpenCV is used only for RGB<->YCrCb color conversion; the active CLAHE path performs no uint16 image-plane round-trip.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float tensor in `[0,1]`.
- @param auto_adjust_options {AutoAdjustOptions} Parsed auto-adjust CLAHE controls.
- @return {object} RGB float tensor after optional CLAHE-luma stage.
- @satisfies REQ-123, REQ-125, REQ-136, REQ-137

### fn `def _rt_gamma2(np_module, values)` `priv` (L9630-9649)
- @brief Apply RawTherapee gamma2 transfer function.
- @details Implements the same piecewise gamma curve used in the attached auto-levels source for histogram-domain bright clipping normalization.
- @param np_module {ModuleType} Imported numpy module.
- @param values {object} Float tensor in linear domain.
- @return {object} Float tensor in gamma2 domain.
- @satisfies REQ-100

### fn `def _rt_igamma2(np_module, values)` `priv` (L9650-9670)
- @brief Apply inverse RawTherapee gamma2 transfer function.
- @details Implements inverse piecewise gamma curve paired with `_rt_gamma2` for whiteclip/black normalization inside auto-levels.
- @param np_module {ModuleType} Imported numpy module.
- @param values {object} Float tensor in gamma2 domain.
- @return {object} Float tensor in linear domain.
- @satisfies REQ-100

### fn `def _auto_levels_index_to_normalized_value(histogram_value, histcompr)` `priv` (L9671-9687)
- @brief Convert one compressed histogram coordinate to normalized scale.
- @details Maps one RawTherapee histogram bin coordinate or derived statistic from the fixed `2^16` histogram family to normalized `[0,1]` intensity units using the exact lower-edge scaling of the original code domain. This helper centralizes pure scale conversion and keeps algorithmic thresholds in `_compute_auto_levels_from_histogram(...)` domain-independent.
- @param histogram_value {int|float} Histogram index or statistic expressed in compressed-bin units.
- @param histcompr {int} Histogram compression shift in `[0, 15]`.
- @return {float} Normalized value in `[0, +inf)`.
- @satisfies REQ-100, REQ-117, REQ-118

### fn `def _auto_levels_normalized_to_legacy_code_value(value)` `priv` (L9688-9703)
- @brief Convert one normalized auto-levels scalar to legacy code scale.
- @details Multiplies one normalized scalar by the legacy `2^16-1` ceiling. Scope is restricted to compatibility mirrors returned by `_compute_auto_levels_from_histogram(...)` and to transitional adapter paths. Production auto-levels math must remain in normalized float units.
- @param value {int|float} Normalized scalar.
- @return {float} Legacy code-domain scalar.
- @note Scope: compatibility-only.
- @satisfies REQ-100, REQ-118

### fn `def _auto_levels_normalized_to_legacy_code(np_module, values)` `priv` (L9704-9720)
- @brief Convert normalized auto-levels tensors to legacy code scale.
- @details Multiplies normalized float tensors by the legacy `2^16-1` ceiling. This helper exists only for compatibility adapters that preserve deterministic legacy unit-test hooks while the production path remains float-native.
- @param np_module {ModuleType} Imported numpy module.
- @param values {object} Normalized scalar or tensor.
- @return {object} Float64 tensor on legacy code scale.
- @note Scope: compatibility-only.
- @satisfies REQ-100

### fn `def _auto_levels_legacy_code_to_normalized(np_module, values)` `priv` (L9721-9736)
- @brief Convert legacy code-domain tensors to normalized float scale.
- @details Divides legacy `2^16-1`-scaled float tensors by the code ceiling. Scope is restricted to transitional compatibility adapters and legacy unit test hooks. Production auto-levels math must not depend on this helper.
- @param np_module {ModuleType} Imported numpy module.
- @param values {object} Legacy code-domain scalar or tensor.
- @return {object} Float64 tensor on normalized scale.
- @note Scope: compatibility-only.
- @satisfies REQ-100

### fn `def _pack_auto_levels_metrics(` `priv` (L9737-9752)

### fn `def _build_autoexp_histogram_rgb_float(np_module, image_rgb_float, histcompr)` `priv` (L9804-9839)
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

### fn `def _build_autoexp_histogram_rgb_uint16(np_module, image_rgb_uint16, histcompr)` `priv` (L9840-9872)
- @brief Build RGB auto-levels histogram from uint16 image tensor.
- @details Builds one RawTherapee-compatible luminance histogram from the post-merge RGB tensor using BT.709 luminance, compressed bins (`hist_size = 65536 >> histcompr`), and deterministic index clipping.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_uint16 {object} RGB uint16 image tensor.
- @param histcompr {int} Histogram compression shift in `[0, 15]`.
- @return {object} Histogram tensor.
- @satisfies REQ-100, REQ-117

### fn `def _compute_auto_levels_from_histogram(np_module, histogram, histcompr, clip_percent)` `priv` (L9873-10072)
- @brief Compute auto-levels gain metrics from histogram.
- @details Ports `get_autoexp_from_histogram` from attached source as-is in numeric behavior for one luminance histogram: octile spread, white/black clip, exposure compensation, brightness/contrast, and highlight compression metrics. All scale-dependent intermediates are derived in normalized units. The returned dictionary exposes normalized-domain metrics under `*_normalized` keys and preserves legacy code-domain mirrors under the historical key names for deterministic compatibility.
- @param np_module {ModuleType} Imported numpy module.
- @param histogram {object} Flattened histogram tensor.
- @param histcompr {int} Histogram compression shift.
- @param clip_percent {float} Clip percentage.
- @return {dict[str, int|float]} Auto-levels metrics dictionary.
- @satisfies REQ-100, REQ-117, REQ-118

### fn `def _rt_simplebasecurve_scalar(x_value, black, shadow_recovery)` `priv` (L10146-10238)
- @brief Evaluate RawTherapee `simplebasecurve` for one normalized sample.
- @details Ports the `CurveFactory::simplebasecurve(...)` path used by RawTherapee to derive the shadow tone factor curve. Input and output stay in normalized float space; no uint16 buffer staging is introduced.
- @param x_value {float} Normalized sample coordinate.
- @param black {float} Normalized clipped black point.
- @param shadow_recovery {float} Shadow recovery strength.
- @return {float} Normalized curve output for the sample.
- @satisfies REQ-100, REQ-119

### fn `def _basel(x_input, slope_start, slope_end)` `priv` (L10159-10175)
- @brief Evaluate RawTherapee `simplebasecurve` for one normalized sample.
- @details Ports the `CurveFactory::simplebasecurve(...)` path used by
RawTherapee to derive the shadow tone factor curve. Input and output stay in
normalized float space; no uint16 buffer staging is introduced.
- @param x_value {float} Normalized sample coordinate.
- @param black {float} Normalized clipped black point.
- @param shadow_recovery {float} Shadow recovery strength.
- @return {float} Normalized curve output for the sample.
- @satisfies REQ-100, REQ-119

### fn `def _baseu(x_input, slope_start, slope_end)` `priv` (L10176-10178)

### fn `def _cupper(x_input, slope_value, highlight_recovery)` `priv` (L10179-10198)

### fn `def _clower(x_input, slope_value, shadow_value)` `priv` (L10199-10201)

### fn `def _clower2(x_input, slope_value, shadow_value)` `priv` (L10202-10213)

### fn `def _build_rt_nurbs_curve_lut(np_module, x_points, y_points, sample_count)` `priv` (L10239-10372)
- @brief Build one RawTherapee-style NURBS diagonal-curve LUT.
- @details Ports the `DiagonalCurve` NURBS polygonization path used by RawTherapee for the brightness and contrast curves inside `CurveFactory::complexCurve(...)`, then resamples the resulting polyline on one dense normalized LUT.
- @param np_module {ModuleType} Imported numpy module.
- @param x_points {tuple[float, ...]|list[float]} Ordered control-point x coordinates.
- @param y_points {tuple[float, ...]|list[float]} Ordered control-point y coordinates.
- @param sample_count {int} Output LUT length.
- @return {object} Dense normalized float64 LUT.
- @exception ValueError Raised when control-point arrays are invalid.
- @satisfies REQ-100, REQ-119

### fn `def _sample_auto_levels_lut_float(` `priv` (L10373-10379)

### fn `def _build_auto_levels_full_histogram_rgb_float(np_module, image_rgb_float)` `priv` (L10411-10442)
- @brief Sample one dense float LUT with RawTherapee-style interpolation.
- @brief Build the full 16-bit luminance histogram for auto-levels curves.
- @details Replicates `LUT<float>::operator[](float)` semantics for scalar or
tensor indices, including optional clipping or edge extrapolation, while
keeping the surrounding pipeline in normalized float arrays.
- @details Builds the uncompressed `0..65535` luminance histogram required by the RawTherapee `complexCurve(...)` contrast-centering step while preserving float-only image buffers.
- @param np_module {ModuleType} Imported numpy module.
- @param lut_values {object} One-dimensional float LUT.
- @param indices {object} Scalar or tensor of float lookup coordinates.
- @param clip_below {bool} `True` to clip values below the lower bound.
- @param clip_above {bool} `True` to clip values above the upper bound.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} Normalized RGB float tensor.
- @return {object} LUT-sampled float tensor.
- @return {object} Full-resolution uint64 histogram.
- @satisfies REQ-100, REQ-119
- @satisfies REQ-100, REQ-119

### fn `def _rt_hlcurve_float(np_module, exp_scale, comp, hlrange, levels_code)` `priv` (L10443-10473)
- @brief Evaluate RawTherapee highlight-curve overflow branch.
- @details Ports `CurveFactory::hlcurve(...)` for channel samples above the dense LUT range while staying in float arithmetic and code-value units only for the local formula evaluation.
- @param np_module {ModuleType} Imported numpy module.
- @param exp_scale {float} Exposure scaling factor `2^expcomp`.
- @param comp {float} Highlight-compression coefficient.
- @param hlrange {float} Highlight range in RawTherapee code units.
- @param levels_code {object} Code-domain sample tensor.
- @return {object} Tone factors for the overflow samples.
- @satisfies REQ-100, REQ-119

### fn `def _build_auto_levels_tone_curve_state(np_module, image_rgb_float, auto_levels_metrics)` `priv` (L10474-10663)
- @brief Build RawTherapee-equivalent auto-levels curve state.
- @details Ports the curve-building path of `CurveFactory::complexCurve(...)` into normalized float execution: full-resolution histogram, highlight curve, shadow curve, brightness curve, contrast curve, and inverse-gamma output tonecurve. Shadow compression remains fixed to RawTherapee default `0`.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} Normalized RGB float tensor.
- @param auto_levels_metrics {dict[str, int|float]} Metrics from `_compute_auto_levels_from_histogram(...)`.
- @return {dict[str, object]} Tone-curve state dictionary.
- @satisfies REQ-100, REQ-118, REQ-119

### fn `def _apply_auto_levels_tonal_transform_float(` `priv` (L10664-10667)

### fn `def _auto_levels_has_full_tone_metrics(auto_levels_metrics)` `priv` (L10751-10774)
- @brief Apply RawTherapee-equivalent auto-levels tonal transformation.
- @brief Check whether auto-levels metrics support full tone processing.
- @details Executes the float-domain port of RawTherapee auto-levels tone
processing in the same stage order as `rgbProc(...)`: highlight curve,
shadow curve, then output tonecurve. Exposure scaling is carried by the
highlight curve baseline instead of a separate gain-only multiply. Mixed
overflow pixels remain on the RawTherapee per-channel path; the function
does not bypass tone mapping for partially out-of-gamut triplets.
- @details Verifies the presence of the full RawTherapee-compatible metric set consumed by `_apply_auto_levels_tonal_transform_float(...)`. Legacy tests may monkeypatch `_compute_auto_levels_from_histogram(...)` with partial dictionaries containing only `gain`; such patched metrics must keep the historical gain-only fallback path.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} Normalized RGB float tensor.
- @param auto_levels_metrics {dict[str, int|float]} Metrics from `_compute_auto_levels_from_histogram(...)`.
- @param auto_levels_metrics {dict[str, int|float]} Histogram-derived metrics dictionary.
- @return {object} Tonally transformed RGB float tensor.
- @return {bool} `True` when all full tone-transform metrics are present.
- @satisfies REQ-100, REQ-119
- @satisfies REQ-100, REQ-119

### fn `def _call_auto_levels_compat_helper(` `priv` (L10775-10780)

### fn `def _apply_auto_levels_float(np_module, image_rgb_float, auto_levels_options)` `priv` (L10824-10927)
- @brief Invoke float-native helper while honoring patched legacy aliases.
- @brief Apply auto-levels stage on RGB float tensor.
- @details Selects the float-native helper for normal execution. If a legacy
`_uint16` alias has been monkeypatched away from its built-in compatibility
shim, converts designated normalized arguments to legacy code scale,
delegates to the patched callable, and maps the returned tensor back to
normalized scale. This preserves deterministic legacy unit-test hooks
without reintroducing code-domain math into the production auto-levels
pipeline.
- @details Executes RawTherapee-compatible histogram analysis on a normalized RGB float tensor, applies the full float-domain tonal transformation driven by exposure, black, brightness, contrast, and highlight-compression metrics, conditionally runs float-native highlight reconstruction, and optionally clips overflowing RGB triplets with RawTherapee film-like gamut logic without any production uint16 staging buffers; no final stage-local `[0,1]` clipping is applied beyond the optional gamut clip.
- @param np_module {ModuleType} Imported numpy module.
- @param primary_callable {object} Float-native helper callable.
- @param legacy_name {str} Legacy module attribute name.
- @param scaled_argument_names {set[str]} Keyword names requiring normalized<->legacy scaling in compatibility mode.
- @param kwargs {dict[str, object]} Helper keyword arguments.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float tensor.
- @param auto_levels_options {AutoLevelsOptions} Parsed auto-levels options.
- @return {object} Normalized RGB float tensor returned by the selected helper.
- @return {object} RGB float tensor after auto-levels stage without final stage-local clipping.
- @satisfies REQ-100, REQ-102, REQ-119, REQ-120
- @satisfies REQ-100, REQ-101, REQ-102, REQ-119, REQ-120, REQ-165

### fn `def _clip_auto_levels_out_of_gamut_float(np_module, image_rgb, maxval=1.0)` `priv` (L10928-11088)
- @brief Clip overflowing RGB triplets with RawTherapee film-like gamut logic.
- @details Ports RawTherapee `filmlike_clip(...)` to normalized float space. Negative channels are clamped to `0` first. Overflowing triplets then use the Adobe-style hue-stable diagonal clipping family instead of isotropic normalization so dominant-channel ordering and cross-channel interpolation follow RawTherapee semantics.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on normalized scale.
- @param maxval {float} Maximum allowed channel value.
- @return {object} RGB float tensor with no channel above `maxval`.
- @satisfies REQ-165

### fn `def _filmlike_clip_rgb_tone(primary, middle, lower)` `priv` (L10958-10991)
- @brief Clip overflowing RGB triplets with RawTherapee film-like gamut logic.
- @brief Apply one ordered RawTherapee diagonal gamut clip branch.
- @details Ports RawTherapee `filmlike_clip(...)` to normalized float space.
Negative channels are clamped to `0` first. Overflowing triplets then use
the Adobe-style hue-stable diagonal clipping family instead of isotropic
normalization so dominant-channel ordering and cross-channel interpolation
follow RawTherapee semantics.
- @details Clamps the dominant and lower channels to `maxval`, then reconstructs the middle channel by linearly interpolating across the unclipped diagonal exactly like RawTherapee `filmlike_clip_rgb_tone`. Division-by-zero only occurs on degenerate equal-channel cases that are dispatched away by the branch predicates, but one safe fallback is kept for deterministic vectorized execution.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on normalized scale.
- @param maxval {float} Maximum allowed channel value.
- @param primary {object} Dominant-channel tensor for one branch.
- @param middle {object} Middle-ranked channel tensor for one branch.
- @param lower {object} Lowest-ranked channel tensor for one branch.
- @return {object} RGB float tensor with no channel above `maxval`.
- @return {tuple[object, object, object]} Branch-clipped `(primary, middle, lower)` tensors.
- @satisfies REQ-165
- @satisfies REQ-165

### fn `def _clip_auto_levels_out_of_gamut_uint16(` `priv` (L11089-11090)

### fn `def _hlrecovery_luminance_float(np_module, image_rgb, maxval=1.0)` `priv` (L11120-11166)
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
- @satisfies REQ-165
- @satisfies REQ-102

### fn `def _hlrecovery_luminance_uint16(np_module, image_rgb, maxval=_AUTO_LEVELS_CODE_MAX)` `priv` (L11167-11195)
- @brief Compatibility adapter for legacy luminance recovery helper name.
- @details Converts legacy code-domain float tensors to normalized scale, delegates to `_hlrecovery_luminance_float(...)`, and rescales the result back to legacy code units. This shim exists only for transitional internal references and deterministic legacy unit-test hooks.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on legacy code scale.
- @param maxval {float} Maximum legacy code-domain value.
- @return {object} Highlight-reconstructed RGB float tensor on legacy code scale.
- @deprecated Use `_hlrecovery_luminance_float`.
- @satisfies REQ-102

### fn `def _hlrecovery_cielab_float(` `priv` (L11196-11197)

### fn `def _f_lab(values)` `priv` (L11230-11237)
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

### fn `def _f2xyz(values)` `priv` (L11238-11244)

### fn `def _hlrecovery_cielab_uint16(` `priv` (L11280-11281)

### fn `def _hlrecovery_blend_float(np_module, image_rgb, hlmax, maxval=1.0)` `priv` (L11315-11420)
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

### fn `def _hlrecovery_blend_uint16(` `priv` (L11421-11422)

### fn `def _dilate_mask_float(np_module, mask)` `priv` (L11457-11479)
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

### fn `def _box_mean_3x3_float(np_module, image_2d)` `priv` (L11480-11503)
- @brief Compute one deterministic `3x3` box mean over a 2D float tensor.
- @details Uses edge padding and exact neighborhood averaging to approximate RawTherapee local neighborhood probes needed by RGB-space color-propagation and inpaint-opposed highlight reconstruction.
- @param np_module {ModuleType} Imported numpy module.
- @param image_2d {object} Float tensor with shape `H,W`.
- @return {object} Float tensor with shape `H,W`.
- @satisfies REQ-119

### fn `def _hlrecovery_color_propagation_float(np_module, image_rgb, maxval=1.0)` `priv` (L11504-11548)
- @brief Apply Color Propagation highlight reconstruction on RGB tensor.
- @details Approximates RawTherapee `Color` recovery in post-merge RGB space: detect clipped channel regions, estimate one local opposite-channel reference from `3x3` means, derive one border chrominance offset, and fill clipped samples deterministically.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb {object} RGB float tensor on normalized scale.
- @param maxval {float} Maximum channel value.
- @return {object} Highlight-reconstructed RGB float tensor.
- @satisfies REQ-102, REQ-119

### fn `def _hlrecovery_color_propagation_uint16(` `priv` (L11549-11550)

### fn `def _hlrecovery_inpaint_opposed_float(` `priv` (L11580-11581)
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

### fn `def _hlrecovery_inpaint_opposed_uint16(` `priv` (L11634-11635)
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

### fn `def _apply_auto_brightness_rgb_float(` `priv` (L11677-11680)
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

### fn `def _clamp01(np_module, values)` `priv` (L11736-11749)
- @brief Apply original photographic auto-brightness flow on RGB float tensor.
- @brief Clamp numeric image tensor values into `[0.0, 1.0]` interval.
- @details Executes `/tmp/auto-brightness.py` step order directly on linear
gamma `1.0` RGB float input: derive BT.709 luminance, classify key using
normalized distribution thresholds, choose or override key value `a`,
apply Reinhard global tonemap with robust percentile white-point, preserve
chromaticity by luminance scaling, optionally desaturate only overflowing
RGB pixels, and preserve linear gamma `1.0` output without any CLAHE
substep or stage-local `[0,1]` output clipping.
- @details Applies vectorized clipping to ensure deterministic bounded values for auto-adjust float-domain operations.
- @param np_module {ModuleType} Imported numpy module.
- @param image_rgb_float {object} RGB float tensor.
- @param auto_brightness_options {AutoBrightnessOptions} Parsed auto-brightness parameters.
- @param np_module {ModuleType} Imported numpy module.
- @param values {object} Numeric tensor-like payload.
- @return {object} RGB float tensor after BT.709 auto-brightness without stage-local clipping.
- @return {object} Clipped tensor payload.
- @satisfies REQ-050, REQ-103, REQ-104, REQ-105, REQ-121, REQ-122
- @satisfies REQ-075

### fn `def _gaussian_kernel_2d(np_module, sigma, radius=None)` `priv` (L11750-11772)
- @brief Build normalized 2D Gaussian kernel.
- @details Creates deterministic Gaussian kernel used by selective blur stage; returns identity kernel when `sigma <= 0`.
- @param np_module {ModuleType} Imported numpy module.
- @param sigma {float} Gaussian sigma value.
- @param radius {int|None} Optional kernel radius override.
- @return {object} Normalized 2D kernel tensor.
- @satisfies REQ-075

### fn `def _rgb_to_hsl(np_module, rgb)` `priv` (L11773-11806)
- @brief Convert RGB float tensor to HSL channels.
- @details Implements explicit HSL conversion for auto-adjust saturation-gamma stage without delegating to external color-space helpers.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB tensor in `[0.0, 1.0]`.
- @return {tuple[object, object, object]} `(h, s, l)` channel tensors.
- @satisfies REQ-075

### fn `def _hue_to_rgb(np_module, p_values, q_values, t_values)` `priv` (L11807-11837)
- @brief Convert one hue-shift channel to RGB component.
- @details Evaluates piecewise hue interpolation branch used by HSL-to-RGB conversion in the auto-adjust pipeline.
- @param np_module {ModuleType} Imported numpy module.
- @param p_values {object} Lower chroma interpolation boundary.
- @param q_values {object} Upper chroma interpolation boundary.
- @param t_values {object} Hue-shifted channel tensor.
- @return {object} RGB component tensor.
- @satisfies REQ-075

### fn `def _hsl_to_rgb(np_module, hue, saturation, lightness)` `priv` (L11838-11878)
- @brief Convert HSL channels to RGB float tensor.
- @details Reconstructs RGB tensor with explicit achromatic/chromatic branches for the auto-adjust saturation-gamma stage.
- @param np_module {ModuleType} Imported numpy module.
- @param hue {object} Hue channel tensor.
- @param saturation {object} Saturation channel tensor.
- @param lightness {object} Lightness channel tensor.
- @return {object} RGB tensor in `[0.0, 1.0]`.
- @satisfies REQ-075

### fn `def _selective_blur_contrast_gated_vectorized(` `priv` (L11879-11880)

### fn `def _level_per_channel_adaptive(np_module, rgb, low_pct=0.1, high_pct=99.9)` `priv` (L11929-11951)
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

### fn `def _sigmoidal_contrast(np_module, rgb, contrast=3.0, midpoint=0.5)` `priv` (L11952-11976)
- @brief Execute sigmoidal contrast stage.
- @details Applies logistic remapping with bounded normalization for each RGB channel.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param contrast {float} Logistic slope.
- @param midpoint {float} Logistic midpoint.
- @return {object} Contrast-adjusted RGB float tensor.
- @satisfies REQ-075

### fn `def logistic(z_values)` (L11967-11969)
- @brief Execute sigmoidal contrast stage.
- @details Applies logistic remapping with bounded normalization for each RGB
channel.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param contrast {float} Logistic slope.
- @param midpoint {float} Logistic midpoint.
- @return {object} Contrast-adjusted RGB float tensor.
- @satisfies REQ-075

### fn `def _vibrance_hsl_gamma(np_module, rgb, saturation_gamma=0.8)` `priv` (L11977-11994)
- @brief Execute HSL saturation gamma stage.
- @details Converts RGB to HSL, applies saturation gamma transform, and converts back to RGB.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param saturation_gamma {float} Saturation gamma denominator value.
- @return {object} Saturation-adjusted RGB float tensor.
- @satisfies REQ-075

### fn `def _gaussian_blur_rgb(cv2_module, np_module, rgb, sigma)` `priv` (L11995-12018)
- @brief Execute RGB Gaussian blur with reflected border mode.
- @details Computes odd kernel size from sigma and applies OpenCV Gaussian blur preserving reflected border behavior.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param sigma {float} Gaussian sigma.
- @return {object} Blurred RGB float tensor.
- @satisfies REQ-075

### fn `def _high_pass_math_gray(cv2_module, np_module, rgb, blur_sigma=2.5)` `priv` (L12019-12042)
- @brief Execute high-pass math grayscale stage.
- @details Computes high-pass response as `A - B + 0.5` over RGB channels and converts to luminance grayscale tensor.
- @param cv2_module {ModuleType} Imported cv2 module.
- @param np_module {ModuleType} Imported numpy module.
- @param rgb {object} RGB float tensor in `[0.0, 1.0]`.
- @param blur_sigma {float} Gaussian blur sigma for high-pass base.
- @return {object} Grayscale float tensor in `[0.0, 1.0]`.
- @satisfies REQ-075

### fn `def _overlay_composite(np_module, base_rgb, overlay_gray)` `priv` (L12043-12064)
- @brief Execute overlay composite stage.
- @details Applies conditional overlay blend equation over RGB base and grayscale overlay tensors.
- @param np_module {ModuleType} Imported numpy module.
- @param base_rgb {object} Base RGB float tensor in `[0.0, 1.0]`.
- @param overlay_gray {object} Overlay grayscale tensor in `[0.0, 1.0]`.
- @return {object} Overlay-composited RGB float tensor.
- @satisfies REQ-075

### fn `def _apply_validated_auto_adjust_pipeline(` `priv` (L12065-12071)

### fn `def _load_piexif_dependency()` `priv` (L12180-12197)
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

### fn `def _postprocess(` `priv` (L12198-12206)

### fn `def _encode_jpg(` `priv` (L12336-12344)

### fn `def _collect_processing_errors(rawpy_module)` `priv` (L12404-12432)
- @brief Build deterministic tuple of recoverable processing exceptions.
- @details Combines common IO/value/subprocess errors with rawpy-specific decoding error classes when present in runtime module version.
- @param rawpy_module {ModuleType} Imported rawpy module.
- @return {tuple[type[BaseException], ...]} Ordered deduplicated exception class tuple.
- @satisfies REQ-059

### fn `def _is_supported_runtime_os()` `priv` (L12433-12452)
- @brief Validate runtime platform support for `dng2jpg`.
- @details Accepts Linux runtime only; emits explicit non-Linux unsupported message that includes OS label (`Windows` or `MacOS`) for deterministic UX.
- @return {bool} `True` when runtime OS is Linux; `False` otherwise.
- @satisfies REQ-055, REQ-059

### fn `def run(args)` (L12453-12652)
- @brief Execute `dng2jpg` command pipeline.
- @details Parses command options, validates dependencies, detects source DNG bits-per-color from RAW metadata, resolves `ev_zero` (static `0.0` default, static `--exposure=<value>`, or auto via `--exposure=auto`) and `ev_delta` (static `1.0` default, static `--bracketing=<value>`, or auto via `--bracketing=auto`), extracts one linear HDR base image using selected RAW WB normalization mode and derives three normalized RGB float brackets, executes the selected HDR backend with float input/output interfaces, executes the float-interface post-merge pipeline, optionally emits persistent debug TIFF checkpoints for executed stages, writes the final JPG, and guarantees temporary artifact cleanup through isolated temporary directory lifecycle.
- @param args {list[str]} Command argument vector excluding command token.
- @return {int} `0` on success; `1` on parse/validation/dependency/processing failure.
- @satisfies PRJ-001, CTN-001, CTN-004, CTN-005, CTN-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012, REQ-013, REQ-014, REQ-015, REQ-032, REQ-037, REQ-050, REQ-052, REQ-100, REQ-106, REQ-107, REQ-108, REQ-109, REQ-110, REQ-111, REQ-112, REQ-113, REQ-114, REQ-115, REQ-126, REQ-127, REQ-128, REQ-129, REQ-131, REQ-132, REQ-133, REQ-134, REQ-138, REQ-139, REQ-140, REQ-146, REQ-147, REQ-148, REQ-149, REQ-157, REQ-158, REQ-159, REQ-160, REQ-181, REQ-182, REQ-183, REQ-184, REQ-185, REQ-186, REQ-187, REQ-188, REQ-189, REQ-190, REQ-191, REQ-192, REQ-193, REQ-194, REQ-195, REQ-196, REQ-197, REQ-198, REQ-203, REQ-204, REQ-205, REQ-206, REQ-207

## Symbol Index
|Symbol|Kind|Vis|Lines|Sig|
|---|---|---|---|---|
|`PROGRAM`|var|pub|39||
|`DESCRIPTION`|var|pub|40||
|`DEFAULT_POST_GAMMA`|var|pub|43||
|`DEFAULT_POST_GAMMA_MODE`|var|pub|44||
|`DEFAULT_POST_GAMMA_AUTO_TARGET_GRAY`|var|pub|45||
|`DEFAULT_POST_GAMMA_AUTO_LUMA_MIN`|var|pub|46||
|`DEFAULT_POST_GAMMA_AUTO_LUMA_MAX`|var|pub|47||
|`DEFAULT_POST_GAMMA_AUTO_LUT_SIZE`|var|pub|48||
|`DEFAULT_BRIGHTNESS`|var|pub|49||
|`DEFAULT_CONTRAST`|var|pub|50||
|`DEFAULT_SATURATION`|var|pub|51||
|`DEFAULT_JPG_COMPRESSION`|var|pub|52||
|`DEFAULT_AUTO_EV_SHADOW_CLIPPING`|var|pub|53||
|`DEFAULT_AUTO_EV_HIGHLIGHT_CLIPPING`|var|pub|54||
|`DEFAULT_AUTO_EV_STEP`|var|pub|55||
|`DEFAULT_AA_BLUR_SIGMA`|var|pub|56||
|`DEFAULT_AA_BLUR_THRESHOLD_PCT`|var|pub|57||
|`DEFAULT_AA_LEVEL_LOW_PCT`|var|pub|58||
|`DEFAULT_AA_LEVEL_HIGH_PCT`|var|pub|59||
|`DEFAULT_AA_ENABLE_LOCAL_CONTRAST`|var|pub|60||
|`DEFAULT_AA_LOCAL_CONTRAST_STRENGTH`|var|pub|61||
|`DEFAULT_AA_CLAHE_CLIP_LIMIT`|var|pub|62||
|`DEFAULT_AA_CLAHE_TILE_GRID_SIZE`|var|pub|63||
|`DEFAULT_AA_SIGMOID_CONTRAST`|var|pub|64||
|`DEFAULT_AA_SIGMOID_MIDPOINT`|var|pub|65||
|`DEFAULT_AA_SATURATION_GAMMA`|var|pub|66||
|`DEFAULT_AA_HIGHPASS_BLUR_SIGMA`|var|pub|67||
|`DEFAULT_AB_KEY_VALUE`|var|pub|68||
|`DEFAULT_AB_WHITE_POINT_PERCENTILE`|var|pub|69||
|`DEFAULT_AB_A_MIN`|var|pub|70||
|`DEFAULT_AB_A_MAX`|var|pub|71||
|`DEFAULT_AB_MAX_AUTO_BOOST_FACTOR`|var|pub|72||
|`DEFAULT_AB_ENABLE_LUMINANCE_PRESERVING_DESAT`|var|pub|73||
|`DEFAULT_AB_EPS`|var|pub|74||
|`DEFAULT_AB_LOW_KEY_VALUE`|var|pub|75||
|`DEFAULT_AB_NORMAL_KEY_VALUE`|var|pub|76||
|`DEFAULT_AB_HIGH_KEY_VALUE`|var|pub|77||
|`DEFAULT_AL_CLIP_PERCENT`|var|pub|78||
|`DEFAULT_AL_CLIP_OUT_OF_GAMUT`|var|pub|79||
|`DEFAULT_AL_GAIN_THRESHOLD`|var|pub|80||
|`DEFAULT_AL_HISTCOMPR`|var|pub|81||
|`DEFAULT_LUMINANCE_HDR_MODEL`|var|pub|109||
|`DEFAULT_LUMINANCE_HDR_WEIGHT`|var|pub|110||
|`DEFAULT_LUMINANCE_HDR_RESPONSE_CURVE`|var|pub|111||
|`DEFAULT_LUMINANCE_TMO`|var|pub|112||
|`DEFAULT_AUTO_ADJUST_ENABLED`|var|pub|113||
|`HDR_MERGE_MODE_LUMINANCE`|var|pub|114||
|`HDR_MERGE_MODE_OPENCV_MERGE`|var|pub|115||
|`HDR_MERGE_MODE_OPENCV_TONEMAP`|var|pub|116||
|`HDR_MERGE_MODE_HDR_PLUS`|var|pub|117||
|`WHITE_BALANCE_MODE_SIMPLE`|var|pub|118||
|`WHITE_BALANCE_MODE_GRAYWORLD`|var|pub|119||
|`WHITE_BALANCE_MODE_IA`|var|pub|120||
|`WHITE_BALANCE_MODE_COLOR_CONSTANCY`|var|pub|121||
|`WHITE_BALANCE_MODE_TTL`|var|pub|122||
|`AUTO_WHITE_BALANCE_MODE_DISABLE`|var|pub|123||
|`WHITE_BALANCE_XPHOTO_DOMAIN_LINEAR`|var|pub|124||
|`WHITE_BALANCE_XPHOTO_DOMAIN_SRGB`|var|pub|125||
|`WHITE_BALANCE_XPHOTO_DOMAIN_SOURCE_AUTO`|var|pub|126||
|`RAW_WHITE_BALANCE_MODE_GREEN`|var|pub|127||
|`RAW_WHITE_BALANCE_MODE_MAX`|var|pub|128||
|`RAW_WHITE_BALANCE_MODE_MIN`|var|pub|129||
|`RAW_WHITE_BALANCE_MODE_MEAN`|var|pub|130||
|`DEFAULT_RAW_WHITE_BALANCE_MODE`|var|pub|131||
|`DEFAULT_WHITE_BALANCE_XPHOTO_DOMAIN`|var|pub|132||
|`WHITE_BALANCE_ANALYSIS_SOURCE_EV_ZERO`|var|pub|133||
|`WHITE_BALANCE_ANALYSIS_SOURCE_LINEAR_BASE`|var|pub|134||
|`OPENCV_TONEMAP_MAP_DRAGO`|var|pub|135||
|`OPENCV_TONEMAP_MAP_REINHARD`|var|pub|136||
|`OPENCV_TONEMAP_MAP_MANTIUK`|var|pub|137||
|`OPENCV_MERGE_ALGORITHM_DEBEVEC`|var|pub|138||
|`OPENCV_MERGE_ALGORITHM_ROBERTSON`|var|pub|139||
|`OPENCV_MERGE_ALGORITHM_MERTENS`|var|pub|140||
|`DEFAULT_REINHARD02_POST_GAMMA`|var|pub|141||
|`DEFAULT_REINHARD02_BRIGHTNESS`|var|pub|142||
|`DEFAULT_REINHARD02_CONTRAST`|var|pub|143||
|`DEFAULT_REINHARD02_SATURATION`|var|pub|144||
|`DEFAULT_MANTIUK08_POST_GAMMA`|var|pub|145||
|`DEFAULT_MANTIUK08_BRIGHTNESS`|var|pub|146||
|`DEFAULT_MANTIUK08_CONTRAST`|var|pub|147||
|`DEFAULT_MANTIUK08_SATURATION`|var|pub|148||
|`DEFAULT_HDRPLUS_POST_GAMMA`|var|pub|149||
|`DEFAULT_HDRPLUS_BRIGHTNESS`|var|pub|150||
|`DEFAULT_HDRPLUS_CONTRAST`|var|pub|151||
|`DEFAULT_HDRPLUS_SATURATION`|var|pub|152||
|`DEFAULT_OPENCV_DEBEVEC_POST_GAMMA`|var|pub|153||
|`DEFAULT_OPENCV_DEBEVEC_BRIGHTNESS`|var|pub|154||
|`DEFAULT_OPENCV_DEBEVEC_CONTRAST`|var|pub|155||
|`DEFAULT_OPENCV_DEBEVEC_SATURATION`|var|pub|156||
|`DEFAULT_OPENCV_DEBEVEC_TONEMAP_GAMMA`|var|pub|157||
|`DEFAULT_OPENCV_ROBERTSON_POST_GAMMA`|var|pub|158||
|`DEFAULT_OPENCV_ROBERTSON_BRIGHTNESS`|var|pub|159||
|`DEFAULT_OPENCV_ROBERTSON_CONTRAST`|var|pub|160||
|`DEFAULT_OPENCV_ROBERTSON_SATURATION`|var|pub|161||
|`DEFAULT_OPENCV_ROBERTSON_TONEMAP_GAMMA`|var|pub|162||
|`DEFAULT_OPENCV_MERTENS_POST_GAMMA`|var|pub|163||
|`DEFAULT_OPENCV_MERTENS_BRIGHTNESS`|var|pub|164||
|`DEFAULT_OPENCV_MERTENS_CONTRAST`|var|pub|165||
|`DEFAULT_OPENCV_MERTENS_SATURATION`|var|pub|166||
|`DEFAULT_OPENCV_MERTENS_TONEMAP_GAMMA`|var|pub|167||
|`DEFAULT_OPENCV_POST_GAMMA`|var|pub|168||
|`DEFAULT_OPENCV_BRIGHTNESS`|var|pub|169||
|`DEFAULT_OPENCV_CONTRAST`|var|pub|170||
|`DEFAULT_OPENCV_SATURATION`|var|pub|171||
|`DEFAULT_OPENCV_MERGE_ALGORITHM`|var|pub|172||
|`DEFAULT_OPENCV_TONEMAP_ENABLED`|var|pub|173||
|`DEFAULT_OPENCV_TONEMAP_GAMMA`|var|pub|174||
|`DEFAULT_OPENCV_TONEMAP_DRAGO_SATURATION`|var|pub|175||
|`DEFAULT_OPENCV_TONEMAP_DRAGO_BIAS`|var|pub|176||
|`DEFAULT_OPENCV_TONEMAP_REINHARD_INTENSITY`|var|pub|177||
|`DEFAULT_OPENCV_TONEMAP_REINHARD_LIGHT_ADAPT`|var|pub|178||
|`DEFAULT_OPENCV_TONEMAP_REINHARD_COLOR_ADAPT`|var|pub|179||
|`DEFAULT_OPENCV_TONEMAP_MANTIUK_SCALE`|var|pub|180||
|`DEFAULT_OPENCV_TONEMAP_MANTIUK_SATURATION`|var|pub|181||
|`DEFAULT_HDRPLUS_PROXY_MODE`|var|pub|182||
|`DEFAULT_HDRPLUS_SEARCH_RADIUS`|var|pub|183||
|`DEFAULT_HDRPLUS_TEMPORAL_FACTOR`|var|pub|184||
|`DEFAULT_HDRPLUS_TEMPORAL_MIN_DIST`|var|pub|185||
|`DEFAULT_HDRPLUS_TEMPORAL_MAX_DIST`|var|pub|186||
|`HDRPLUS_TILE_SIZE`|var|pub|187||
|`HDRPLUS_TILE_STRIDE`|var|pub|188||
|`HDRPLUS_DOWNSAMPLED_TILE_SIZE`|var|pub|189||
|`HDRPLUS_ALIGNMENT_LEVELS`|var|pub|190||
|`HDRPLUS_ALIGNMENT_DOWNSAMPLE_RATE`|var|pub|191||
|`HDRPLUS_TEMPORAL_FACTOR`|var|pub|192||
|`HDRPLUS_TEMPORAL_MIN_DIST`|var|pub|193||
|`HDRPLUS_TEMPORAL_MAX_DIST`|var|pub|194||
|`MIN_SUPPORTED_BITS_PER_COLOR`|var|pub|196||
|`AutoAdjustOptions`|class|pub|461-496|class AutoAdjustOptions|
|`AutoBrightnessOptions`|class|pub|498-526|class AutoBrightnessOptions|
|`AutoLevelsOptions`|class|pub|528-551|class AutoLevelsOptions|
|`PostGammaAutoOptions`|class|pub|553-571|class PostGammaAutoOptions|
|`MergeGammaOption`|class|pub|573-591|class MergeGammaOption|
|`ResolvedMergeGamma`|class|pub|593-618|class ResolvedMergeGamma|
|`ExifGammaTags`|class|pub|620-641|class ExifGammaTags|
|`OpenCvTonemapOptions`|class|pub|643-672|class OpenCvTonemapOptions|
|`PostprocessOptions`|class|pub|674-772|class PostprocessOptions|
|`PostprocessOptions.auto_white_balance_mode`|fn|pub|734-745|def auto_white_balance_mode(self) -> str | None|
|`PostprocessOptions.auto_white_balance_analysis_source`|fn|pub|747-758|def auto_white_balance_analysis_source(self) -> str|
|`PostprocessOptions.auto_white_balance_xphoto_domain`|fn|pub|760-772|def auto_white_balance_xphoto_domain(self) -> str|
|`DebugArtifactContext`|class|pub|774-790|class DebugArtifactContext|
|`SourceGammaInfo`|class|pub|792-810|class SourceGammaInfo|
|`LuminanceOptions`|class|pub|812-833|class LuminanceOptions|
|`OpenCvMergeOptions`|class|pub|835-855|class OpenCvMergeOptions|
|`HdrPlusOptions`|class|pub|857-880|class HdrPlusOptions|
|`HdrPlusTemporalRuntimeOptions`|class|pub|882-901|class HdrPlusTemporalRuntimeOptions|
|`JointAutoEvSolution`|class|pub|903-923|class JointAutoEvSolution|
|`AutoEvIterationStep`|class|pub|925-942|class AutoEvIterationStep|
|`AutoEvOptions`|class|pub|944-961|class AutoEvOptions|
|`AutoZeroEvaluation`|class|pub|963-981|class AutoZeroEvaluation|
|`_print_box_table`|fn|priv|982-1018|def _print_box_table(headers, rows, header_rows=())|
|`_border`|fn|priv|1002-1004|def _border(left, middle, right)|
|`_line`|fn|priv|1005-1008|def _line(values)|
|`_build_two_line_operator_rows`|fn|priv|1019-1035|def _build_two_line_operator_rows(operator_entries)|
|`_print_help_section`|fn|priv|1036-1050|def _print_help_section(title)|
|`_print_help_option`|fn|priv|1051-1092|def _print_help_option(option_label, description, detail_...|
|`print_help`|fn|pub|1093-1292|def print_help(version)|
|`_validate_supported_bits_per_color`|fn|priv|1547-1564|def _validate_supported_bits_per_color(bits_per_color)|
|`_detect_dng_bits_per_color`|fn|priv|1565-1610|def _detect_dng_bits_per_color(raw_handle)|
|`_is_ev_value_on_supported_step`|fn|priv|1611-1623|def _is_ev_value_on_supported_step(ev_value)|
|`_parse_ev_option`|fn|priv|1624-1650|def _parse_ev_option(ev_raw)|
|`_parse_ev_center_option`|fn|priv|1651-1677|def _parse_ev_center_option(ev_center_raw)|
|`_parse_percentage_option`|fn|priv|1678-1700|def _parse_percentage_option(option_name, option_raw)|
|`_parse_auto_brightness_option`|fn|priv|1701-1720|def _parse_auto_brightness_option(auto_brightness_raw)|
|`_parse_auto_levels_option`|fn|priv|1721-1740|def _parse_auto_levels_option(auto_levels_raw)|
|`_parse_explicit_boolean_option`|fn|priv|1741-1761|def _parse_explicit_boolean_option(option_name, option_raw)|
|`_parse_opencv_merge_algorithm_option`|fn|priv|1762-1786|def _parse_opencv_merge_algorithm_option(algorithm_raw)|
|`_resolve_default_opencv_tonemap_gamma`|fn|priv|1787-1808|def _resolve_default_opencv_tonemap_gamma(merge_algorithm)|
|`_parse_opencv_merge_backend_options`|fn|priv|1809-1861|def _parse_opencv_merge_backend_options(opencv_raw_values)|
|`_parse_opencv_tonemap_backend_options`|fn|priv|1862-1864|def _parse_opencv_tonemap_backend_options(|
|`_extract_normalized_preview_luminance_stats`|fn|priv|2035-2094|def _extract_normalized_preview_luminance_stats(raw_handle)|
|`_percentile`|fn|priv|2069-2079|def _percentile(percentile_value)|
|`_extract_camera_whitebalance_rgb_triplet`|fn|priv|2095-2127|def _extract_camera_whitebalance_rgb_triplet(raw_handle)|
|`_format_rgb_triplet_fixed4`|fn|priv|2128-2157|def _format_rgb_triplet_fixed4(rgb_values)|
|`_normalize_white_balance_gains_rgb`|fn|priv|2158-2161|def _normalize_white_balance_gains_rgb(|
|`_apply_normalized_white_balance_to_rgb_float`|fn|priv|2208-2231|def _apply_normalized_white_balance_to_rgb_float(np_modul...|
|`_build_rawpy_neutral_postprocess_kwargs`|fn|priv|2232-2272|def _build_rawpy_neutral_postprocess_kwargs(raw_handle)|
|`_extract_sensor_dynamic_range_max`|fn|priv|2273-2330|def _extract_sensor_dynamic_range_max(raw_handle, np_module)|
|`_extract_base_rgb_linear_float`|fn|priv|2331-2334|def _extract_base_rgb_linear_float(|
|`_normalize_source_gamma_label`|fn|priv|2381-2399|def _normalize_source_gamma_label(label_raw)|
|`_decode_raw_metadata_text`|fn|priv|2400-2431|def _decode_raw_metadata_text(metadata_raw)|
|`_classify_explicit_source_gamma`|fn|priv|2432-2481|def _classify_explicit_source_gamma(raw_handle)|
|`_classify_tone_curve_gamma`|fn|priv|2482-2530|def _classify_tone_curve_gamma(raw_handle)|
|`_has_nonzero_matrix`|fn|priv|2531-2551|def _has_nonzero_matrix(matrix_raw)|
|`_classify_matrix_hint_gamma`|fn|priv|2552-2582|def _classify_matrix_hint_gamma(raw_handle)|
|`_extract_source_gamma_info`|fn|priv|2583-2610|def _extract_source_gamma_info(raw_handle)|
|`_describe_source_gamma_info`|fn|priv|2611-2632|def _describe_source_gamma_info(source_gamma_info)|
|`_coerce_positive_luminance`|fn|priv|2633-2652|def _coerce_positive_luminance(value, fallback)|
|`_calculate_bt709_luminance`|fn|priv|2653-2675|def _calculate_bt709_luminance(np_module, image_rgb_float)|
|`_smoothstep`|fn|priv|2676-2694|def _smoothstep(np_module, values, edge0, edge1)|
|`_calculate_entropy_optimized_ev`|fn|priv|2695-2740|def _calculate_entropy_optimized_ev(_cv2_module, np_modul...|
|`_calculate_ettr_ev`|fn|priv|2741-2760|def _calculate_ettr_ev(np_module, luminance_float)|
|`_calculate_detail_preservation_ev`|fn|priv|2761-2828|def _calculate_detail_preservation_ev(_cv2_module, np_mod...|
|`_calculate_auto_zero_evaluations`|fn|priv|2829-2866|def _calculate_auto_zero_evaluations(cv2_module, np_modul...|
|`_select_ev_zero_candidate`|fn|priv|2867-2895|def _select_ev_zero_candidate(evaluations)|
|`_build_unclipped_bracket_images_from_linear_base_float`|fn|priv|2896-2900|def _build_unclipped_bracket_images_from_linear_base_float(|
|`_measure_any_channel_highlight_clipping_pct`|fn|priv|2930-2947|def _measure_any_channel_highlight_clipping_pct(np_module...|
|`_measure_any_channel_shadow_clipping_pct`|fn|priv|2948-2965|def _measure_any_channel_shadow_clipping_pct(np_module, i...|
|`_resolve_auto_ev_delta`|fn|priv|2966-2970|def _resolve_auto_ev_delta(|
|`_resolve_joint_auto_ev_solution`|fn|priv|3024-3027|def _resolve_joint_auto_ev_solution(|
|`_parse_luminance_text_option`|fn|priv|3084-3104|def _parse_luminance_text_option(option_name, option_raw)|
|`_parse_luminance_response_curve_option`|fn|priv|3105-3131|def _parse_luminance_response_curve_option(option_raw)|
|`_parse_positive_float_option`|fn|priv|3132-3155|def _parse_positive_float_option(option_name, option_raw)|
|`_parse_post_gamma_selector_option`|fn|priv|3156-3177|def _parse_post_gamma_selector_option(option_raw)|
|`_parse_positive_int_option`|fn|priv|3178-3201|def _parse_positive_int_option(option_name, option_raw)|
|`_parse_post_gamma_auto_options`|fn|priv|3202-3277|def _parse_post_gamma_auto_options(post_gamma_auto_raw_va...|
|`_parse_tmo_passthrough_value`|fn|priv|3278-3294|def _parse_tmo_passthrough_value(option_name, option_raw)|
|`_parse_jpg_compression_option`|fn|priv|3295-3317|def _parse_jpg_compression_option(compression_raw)|
|`_parse_float_exclusive_range_option`|fn|priv|3318-3342|def _parse_float_exclusive_range_option(option_name, opti...|
|`_parse_non_negative_float_option`|fn|priv|3343-3365|def _parse_non_negative_float_option(option_name, option_...|
|`_parse_float_in_range_option`|fn|priv|3366-3391|def _parse_float_in_range_option(option_name, option_raw,...|
|`_parse_positive_int_pair_option`|fn|priv|3392-3423|def _parse_positive_int_pair_option(option_name, option_raw)|
|`_parse_auto_brightness_options`|fn|priv|3424-3520|def _parse_auto_brightness_options(auto_brightness_raw_va...|
|`_parse_auto_levels_hr_method_option`|fn|priv|3521-3552|def _parse_auto_levels_hr_method_option(auto_levels_metho...|
|`_parse_auto_levels_options`|fn|priv|3553-3625|def _parse_auto_levels_options(auto_levels_raw_values)|
|`_parse_auto_adjust_options`|fn|priv|3626-3775|def _parse_auto_adjust_options(auto_adjust_raw_values)|
|`_parse_hdrplus_proxy_mode_option`|fn|priv|3776-3794|def _parse_hdrplus_proxy_mode_option(proxy_mode_raw)|
|`_parse_hdrplus_options`|fn|priv|3795-3871|def _parse_hdrplus_options(hdrplus_raw_values)|
|`_apply_merge_gamma_float_no_clip`|fn|priv|3872-3925|def _apply_merge_gamma_float_no_clip(np_module, image_rgb...|
|`_resolve_opencv_tonemap_gamma_inverse`|fn|priv|3926-3959|def _resolve_opencv_tonemap_gamma_inverse(resolved_merge_...|
|`_parse_auto_adjust_option`|fn|priv|3960-3983|def _parse_auto_adjust_option(auto_adjust_raw)|
|`_parse_raw_white_balance_mode_option`|fn|priv|3984-4011|def _parse_raw_white_balance_mode_option(raw_white_balanc...|
|`_parse_auto_white_balance_mode_option`|fn|priv|4012-4043|def _parse_auto_white_balance_mode_option(auto_white_bala...|
|`_parse_white_balance_mode_option`|fn|priv|4044-4056|def _parse_white_balance_mode_option(white_balance_raw)|
|`_parse_white_balance_analysis_source_option`|fn|priv|4057-4086|def _parse_white_balance_analysis_source_option(analysis_...|
|`_parse_white_balance_xphoto_domain_option`|fn|priv|4087-4113|def _parse_white_balance_xphoto_domain_option(xphoto_doma...|
|`_parse_hdr_merge_option`|fn|priv|4114-4144|def _parse_hdr_merge_option(hdr_merge_raw)|
|`_resolve_default_postprocess`|fn|priv|4145-4148|def _resolve_default_postprocess(|
|`_parse_gamma_option`|fn|priv|4229-4267|def _parse_gamma_option(option_value)|
|`_decode_exif_text_value`|fn|priv|4268-4287|def _decode_exif_text_value(exif_value)|
|`_exiftool_color_space_fallback`|fn|priv|4288-4339|def _exiftool_color_space_fallback(input_dng)|
|`_extract_exif_gamma_tags`|fn|priv|4340-4408|def _extract_exif_gamma_tags(input_dng)|
|`_resolve_auto_merge_gamma`|fn|priv|4409-4455|def _resolve_auto_merge_gamma(exif_gamma_tags, source_gam...|
|`_describe_resolved_merge_gamma`|fn|priv|4456-4515|def _describe_resolved_merge_gamma(resolved_merge_gamma)|
|`_format_gamma_number`|fn|priv|4467-4480|def _format_gamma_number(value)|
|`_describe_exif_gamma_tags`|fn|priv|4516-4558|def _describe_exif_gamma_tags(exif_gamma_tags)|
|`_ensure_three_channel_float_array_no_clip`|fn|priv|4559-4590|def _ensure_three_channel_float_array_no_clip(np_module, ...|
|`_ensure_three_channel_float_array_no_bounds`|fn|priv|4591-4620|def _ensure_three_channel_float_array_no_bounds(np_module...|
|`_apply_merge_gamma_float`|fn|priv|4621-4673|def _apply_merge_gamma_float(np_module, image_rgb_float, ...|
|`_parse_run_options`|fn|priv|4674-4873|def _parse_run_options(args)|
|`_load_image_dependencies`|fn|priv|5307-5344|def _load_image_dependencies()|
|`_parse_exif_datetime_to_timestamp`|fn|priv|5345-5375|def _parse_exif_datetime_to_timestamp(datetime_raw)|
|`_parse_exif_exposure_time_to_seconds`|fn|priv|5376-5438|def _parse_exif_exposure_time_to_seconds(exposure_raw)|
|`_extract_dng_exif_payload_and_timestamp`|fn|priv|5439-5533|def _extract_dng_exif_payload_and_timestamp(pil_image_mod...|
|`_read_exif_value`|fn|priv|5483-5500|def _read_exif_value(exif_tag)|
|`_resolve_thumbnail_transpose_map`|fn|priv|5534-5565|def _resolve_thumbnail_transpose_map(pil_image_module)|
|`_apply_orientation_transform`|fn|priv|5566-5588|def _apply_orientation_transform(pil_image_module, pil_im...|
|`_build_oriented_thumbnail_jpeg_bytes`|fn|priv|5589-5590|def _build_oriented_thumbnail_jpeg_bytes(|
|`_coerce_exif_int_like_value`|fn|priv|5621-5663|def _coerce_exif_int_like_value(raw_value)|
|`_normalize_ifd_integer_like_values_for_piexif_dump`|fn|priv|5664-5797|def _normalize_ifd_integer_like_values_for_piexif_dump(pi...|
|`_refresh_output_jpg_exif_thumbnail_after_save`|fn|priv|5798-5804|def _refresh_output_jpg_exif_thumbnail_after_save(|
|`_set_output_file_timestamps`|fn|priv|5854-5868|def _set_output_file_timestamps(output_jpg, exif_timestamp)|
|`_sync_output_file_timestamps_from_exif`|fn|priv|5869-5886|def _sync_output_file_timestamps_from_exif(output_jpg, ex...|
|`_build_exposure_multipliers`|fn|priv|5887-5905|def _build_exposure_multipliers(ev_value, ev_zero=0.0)|
|`_build_bracket_images_from_linear_base_float`|fn|priv|5906-5935|def _build_bracket_images_from_linear_base_float(np_modul...|
|`_build_white_balance_analysis_image_from_linear_base_float`|fn|priv|5936-5939|def _build_white_balance_analysis_image_from_linear_base_...|
|`_validate_white_balance_triplet_shape`|fn|priv|5961-5990|def _validate_white_balance_triplet_shape(np_module, brac...|
|`_downsample_xphoto_analysis_image_half`|fn|priv|5991-6037|def _downsample_xphoto_analysis_image_half(np_module, ana...|
|`_build_xphoto_analysis_image_rgb_float`|fn|priv|6038-6041|def _build_xphoto_analysis_image_rgb_float(|
|`_build_white_balance_robust_analysis_mask`|fn|priv|6073-6112|def _build_white_balance_robust_analysis_mask(np_module, ...|
|`_extract_white_balance_channel_gains_from_xphoto`|fn|priv|6113-6119|def _extract_white_balance_channel_gains_from_xphoto(|
|`_resolve_white_balance_xphoto_estimation_domain`|fn|priv|6199-6201|def _resolve_white_balance_xphoto_estimation_domain(|
|`_prepare_xphoto_estimation_image_rgb_float`|fn|priv|6244-6247|def _prepare_xphoto_estimation_image_rgb_float(|
|`_resolve_learning_based_wb_hist_bin_num`|fn|priv|6282-6297|def _resolve_learning_based_wb_hist_bin_num(bits_per_color)|
|`_estimate_xphoto_white_balance_gains_rgb`|fn|priv|6298-6305|def _estimate_xphoto_white_balance_gains_rgb(|
|`_estimate_color_constancy_white_balance_gains_rgb`|fn|priv|6380-6383|def _estimate_color_constancy_white_balance_gains_rgb(|
|`_estimate_ttl_white_balance_gains_rgb`|fn|priv|6418-6449|def _estimate_ttl_white_balance_gains_rgb(np_module, anal...|
|`_apply_channel_gains_to_white_balance_triplet`|fn|priv|6450-6453|def _apply_channel_gains_to_white_balance_triplet(|
|`_apply_channel_gains_to_white_balance_image`|fn|priv|6479-6482|def _apply_channel_gains_to_white_balance_image(|
|`_apply_auto_white_balance_stage_float`|fn|priv|6504-6512|def _apply_auto_white_balance_stage_float(|
|`_apply_white_balance_to_bracket_triplet`|fn|priv|6605-6612|def _apply_white_balance_to_bracket_triplet(|
|`_extract_bracket_images_float`|fn|priv|6698-6703|def _extract_bracket_images_float(|
|`_order_bracket_paths`|fn|priv|6739-6764|def _order_bracket_paths(bracket_paths)|
|`_order_hdr_plus_reference_paths`|fn|priv|6765-6780|def _order_hdr_plus_reference_paths(bracket_paths)|
|`_format_external_command_for_log`|fn|priv|6781-6796|def _format_external_command_for_log(command)|
|`_run_luminance_hdr_cli`|fn|priv|6797-6804|def _run_luminance_hdr_cli(|
|`_build_opencv_radiance_exposure_times`|fn|priv|6880-6883|def _build_opencv_radiance_exposure_times(|
|`_build_ev_times_from_ev_zero_and_delta`|fn|priv|6917-6936|def _build_ev_times_from_ev_zero_and_delta(ev_zero, ev_de...|
|`_normalize_opencv_hdr_to_unit_range`|fn|priv|6937-6962|def _normalize_opencv_hdr_to_unit_range(np_module, hdr_rg...|
|`_run_opencv_merge_mertens`|fn|priv|6963-6968|def _run_opencv_merge_mertens(|
|`_estimate_opencv_camera_response`|fn|priv|6998-7002|def _estimate_opencv_camera_response(|
|`_run_opencv_merge_radiance`|fn|priv|7031-7038|def _run_opencv_merge_radiance(|
|`_normalize_debevec_hdr_to_unit_range`|fn|priv|7102-7121|def _normalize_debevec_hdr_to_unit_range(np_module, hdr_r...|
|`_run_opencv_tonemap_backend`|fn|priv|7122-7127|def _run_opencv_tonemap_backend(|
|`_derive_opencv_tonemap_enabled`|fn|priv|7206-7219|def _derive_opencv_tonemap_enabled(postprocess_options)|
|`_run_opencv_merge_backend`|fn|priv|7220-7228|def _run_opencv_merge_backend(|
|`_hdrplus_box_down2_float32`|fn|priv|7325-7353|def _hdrplus_box_down2_float32(np_module, frames_float32)|
|`_hdrplus_gauss_down4_float32`|fn|priv|7354-7400|def _hdrplus_gauss_down4_float32(np_module, frames_float32)|
|`_hdrplus_build_scalar_proxy_float32`|fn|priv|7401-7434|def _hdrplus_build_scalar_proxy_float32(np_module, frames...|
|`_hdrplus_compute_tile_start_positions`|fn|priv|7435-7455|def _hdrplus_compute_tile_start_positions(np_module, axis...|
|`_hdrplus_trunc_divide_int32`|fn|priv|7456-7474|def _hdrplus_trunc_divide_int32(np_module, values_int32, ...|
|`_hdrplus_compute_alignment_bounds`|fn|priv|7475-7499|def _hdrplus_compute_alignment_bounds(search_radius)|
|`_hdrplus_compute_alignment_margin`|fn|priv|7500-7518|def _hdrplus_compute_alignment_margin(search_radius, divi...|
|`_hdrplus_extract_overlapping_tiles`|fn|priv|7519-7524|def _hdrplus_extract_overlapping_tiles(|
|`_hdrplus_extract_aligned_tiles`|fn|priv|7577-7583|def _hdrplus_extract_aligned_tiles(|
|`_hdrplus_align_layer`|fn|priv|7656-7663|def _hdrplus_align_layer(|
|`_hdrplus_align_layers`|fn|priv|7753-7840|def _hdrplus_align_layers(np_module, scalar_frames, hdrpl...|
|`_hdrplus_resolve_temporal_runtime_options`|fn|priv|7841-7865|def _hdrplus_resolve_temporal_runtime_options(hdrplus_opt...|
|`_hdrplus_compute_temporal_weights`|fn|priv|7866-7870|def _hdrplus_compute_temporal_weights(|
|`_hdrplus_merge_temporal_rgb`|fn|priv|7951-7957|def _hdrplus_merge_temporal_rgb(|
|`_hdrplus_merge_spatial_rgb`|fn|priv|8006-8078|def _hdrplus_merge_spatial_rgb(np_module, temporal_tiles,...|
|`_run_hdr_plus_merge`|fn|priv|8079-8084|def _run_hdr_plus_merge(|
|`_convert_compression_to_quality`|fn|priv|8180-8190|def _convert_compression_to_quality(jpg_compression)|
|`_collect_missing_external_executables`|fn|priv|8191-8193|def _collect_missing_external_executables(|
|`_resolve_auto_adjust_dependencies`|fn|priv|8212-8241|def _resolve_auto_adjust_dependencies()|
|`_resolve_numpy_dependency`|fn|priv|8242-8261|def _resolve_numpy_dependency()|
|`_to_float32_image_array`|fn|priv|8262-8293|def _to_float32_image_array(np_module, image_data)|
|`_normalize_float_rgb_image`|fn|priv|8294-8321|def _normalize_float_rgb_image(np_module, image_data)|
|`_prepare_postprocess_entry_rgb_float`|fn|priv|8322-8349|def _prepare_postprocess_entry_rgb_float(np_module, image...|
|`_write_rgb_float_tiff16`|fn|priv|8350-8376|def _write_rgb_float_tiff16(imageio_module, np_module, ou...|
|`_write_rgb_float_tiff32`|fn|priv|8377-8401|def _write_rgb_float_tiff32(imageio_module, np_module, ou...|
|`_write_debug_rgb_float_tiff`|fn|priv|8402-8407|def _write_debug_rgb_float_tiff(|
|`_build_debug_artifact_context`|fn|priv|8437-8457|def _build_debug_artifact_context(output_jpg, input_dng, ...|
|`_write_hdr_merge_debug_checkpoints`|fn|priv|8458-8463|def _write_hdr_merge_debug_checkpoints(|
|`_format_debug_ev_suffix_value`|fn|priv|8522-8539|def _format_debug_ev_suffix_value(ev_value)|
|`_materialize_bracket_tiffs_from_float`|fn|priv|8540-8544|def _materialize_bracket_tiffs_from_float(|
|`_to_uint8_image_array`|fn|priv|8574-8624|def _to_uint8_image_array(np_module, image_data)|
|`_to_uint16_image_array`|fn|priv|8625-8673|def _to_uint16_image_array(np_module, image_data)|
|`_apply_post_gamma_float`|fn|priv|8674-8699|def _apply_post_gamma_float(np_module, image_rgb_float, g...|
|`_build_auto_post_gamma_lut_float`|fn|priv|8700-8716|def _build_auto_post_gamma_lut_float(np_module, gamma_val...|
|`_ensure_three_channel_float_array_no_range_adjust`|fn|priv|8717-8743|def _ensure_three_channel_float_array_no_range_adjust(np_...|
|`_apply_auto_post_gamma_float`|fn|priv|8744-8788|def _apply_auto_post_gamma_float(np_module, image_rgb_flo...|
|`_apply_brightness_float`|fn|priv|8789-8811|def _apply_brightness_float(np_module, image_rgb_float, b...|
|`_apply_contrast_float`|fn|priv|8812-8836|def _apply_contrast_float(np_module, image_rgb_float, con...|
|`_apply_saturation_float`|fn|priv|8837-8867|def _apply_saturation_float(np_module, image_rgb_float, s...|
|`_apply_static_postprocess_float`|fn|priv|8868-8873|def _apply_static_postprocess_float(|
|`_to_linear_srgb`|fn|priv|8990-9007|def _to_linear_srgb(np_module, image_srgb)|
|`_from_linear_srgb`|fn|priv|9008-9025|def _from_linear_srgb(np_module, image_linear)|
|`_compute_bt709_luminance`|fn|priv|9026-9043|def _compute_bt709_luminance(np_module, linear_rgb)|
|`_analyze_luminance_key`|fn|priv|9044-9083|def _analyze_luminance_key(np_module, luminance, eps)|
|`_choose_auto_key_value`|fn|priv|9084-9129|def _choose_auto_key_value(key_analysis, auto_brightness_...|
|`_reinhard_global_tonemap_luminance`|fn|priv|9130-9135|def _reinhard_global_tonemap_luminance(|
|`_luminance_preserving_desaturate_to_fit`|fn|priv|9169-9196|def _luminance_preserving_desaturate_to_fit(np_module, rg...|
|`_apply_mild_local_contrast_bgr_uint16`|fn|priv|9197-9235|def _apply_mild_local_contrast_bgr_uint16(cv2_module, np_...|
|`_quantize_clahe_luminance_bins`|fn|priv|9236-9261|def _quantize_clahe_luminance_bins(np_module, luminance_v...|
|`_build_clahe_float_tile_histogram`|fn|priv|9262-9283|def _build_clahe_float_tile_histogram(np_module, luminanc...|
|`_clip_clahe_histogram`|fn|priv|9284-9331|def _clip_clahe_histogram(np_module, histogram, clip_limi...|
|`_build_clahe_float_lut`|fn|priv|9332-9351|def _build_clahe_float_lut(np_module, histogram, tile_pop...|
|`_pad_clahe_luminance_float`|fn|priv|9352-9390|def _pad_clahe_luminance_float(np_module, luminance_float...|
|`_build_clahe_axis_interpolation`|fn|priv|9391-9418|def _build_clahe_axis_interpolation(np_module, axis_lengt...|
|`_build_clahe_tile_luts_float`|fn|priv|9419-9470|def _build_clahe_tile_luts_float(np_module, luminance_flo...|
|`_interpolate_clahe_bilinear_float`|fn|priv|9471-9523|def _interpolate_clahe_bilinear_float(np_module, luminanc...|
|`_apply_clahe_luminance_float`|fn|priv|9524-9555|def _apply_clahe_luminance_float(np_module, luminance_flo...|
|`_reconstruct_rgb_from_ycrcb_luma_float`|fn|priv|9556-9579|def _reconstruct_rgb_from_ycrcb_luma_float(cv2_module, np...|
|`_apply_clahe_luma_rgb_float`|fn|priv|9580-9629|def _apply_clahe_luma_rgb_float(cv2_module, np_module, im...|
|`_rt_gamma2`|fn|priv|9630-9649|def _rt_gamma2(np_module, values)|
|`_rt_igamma2`|fn|priv|9650-9670|def _rt_igamma2(np_module, values)|
|`_auto_levels_index_to_normalized_value`|fn|priv|9671-9687|def _auto_levels_index_to_normalized_value(histogram_valu...|
|`_auto_levels_normalized_to_legacy_code_value`|fn|priv|9688-9703|def _auto_levels_normalized_to_legacy_code_value(value)|
|`_auto_levels_normalized_to_legacy_code`|fn|priv|9704-9720|def _auto_levels_normalized_to_legacy_code(np_module, val...|
|`_auto_levels_legacy_code_to_normalized`|fn|priv|9721-9736|def _auto_levels_legacy_code_to_normalized(np_module, val...|
|`_pack_auto_levels_metrics`|fn|priv|9737-9752|def _pack_auto_levels_metrics(|
|`_build_autoexp_histogram_rgb_float`|fn|priv|9804-9839|def _build_autoexp_histogram_rgb_float(np_module, image_r...|
|`_build_autoexp_histogram_rgb_uint16`|fn|priv|9840-9872|def _build_autoexp_histogram_rgb_uint16(np_module, image_...|
|`_compute_auto_levels_from_histogram`|fn|priv|9873-10072|def _compute_auto_levels_from_histogram(np_module, histog...|
|`_rt_simplebasecurve_scalar`|fn|priv|10146-10238|def _rt_simplebasecurve_scalar(x_value, black, shadow_rec...|
|`_basel`|fn|priv|10159-10175|def _basel(x_input, slope_start, slope_end)|
|`_baseu`|fn|priv|10176-10178|def _baseu(x_input, slope_start, slope_end)|
|`_cupper`|fn|priv|10179-10198|def _cupper(x_input, slope_value, highlight_recovery)|
|`_clower`|fn|priv|10199-10201|def _clower(x_input, slope_value, shadow_value)|
|`_clower2`|fn|priv|10202-10213|def _clower2(x_input, slope_value, shadow_value)|
|`_build_rt_nurbs_curve_lut`|fn|priv|10239-10372|def _build_rt_nurbs_curve_lut(np_module, x_points, y_poin...|
|`_sample_auto_levels_lut_float`|fn|priv|10373-10379|def _sample_auto_levels_lut_float(|
|`_build_auto_levels_full_histogram_rgb_float`|fn|priv|10411-10442|def _build_auto_levels_full_histogram_rgb_float(np_module...|
|`_rt_hlcurve_float`|fn|priv|10443-10473|def _rt_hlcurve_float(np_module, exp_scale, comp, hlrange...|
|`_build_auto_levels_tone_curve_state`|fn|priv|10474-10663|def _build_auto_levels_tone_curve_state(np_module, image_...|
|`_apply_auto_levels_tonal_transform_float`|fn|priv|10664-10667|def _apply_auto_levels_tonal_transform_float(|
|`_auto_levels_has_full_tone_metrics`|fn|priv|10751-10774|def _auto_levels_has_full_tone_metrics(auto_levels_metrics)|
|`_call_auto_levels_compat_helper`|fn|priv|10775-10780|def _call_auto_levels_compat_helper(|
|`_apply_auto_levels_float`|fn|priv|10824-10927|def _apply_auto_levels_float(np_module, image_rgb_float, ...|
|`_clip_auto_levels_out_of_gamut_float`|fn|priv|10928-11088|def _clip_auto_levels_out_of_gamut_float(np_module, image...|
|`_filmlike_clip_rgb_tone`|fn|priv|10958-10991|def _filmlike_clip_rgb_tone(primary, middle, lower)|
|`_clip_auto_levels_out_of_gamut_uint16`|fn|priv|11089-11090|def _clip_auto_levels_out_of_gamut_uint16(|
|`_hlrecovery_luminance_float`|fn|priv|11120-11166|def _hlrecovery_luminance_float(np_module, image_rgb, max...|
|`_hlrecovery_luminance_uint16`|fn|priv|11167-11195|def _hlrecovery_luminance_uint16(np_module, image_rgb, ma...|
|`_hlrecovery_cielab_float`|fn|priv|11196-11197|def _hlrecovery_cielab_float(|
|`_f_lab`|fn|priv|11230-11237|def _f_lab(values)|
|`_f2xyz`|fn|priv|11238-11244|def _f2xyz(values)|
|`_hlrecovery_cielab_uint16`|fn|priv|11280-11281|def _hlrecovery_cielab_uint16(|
|`_hlrecovery_blend_float`|fn|priv|11315-11420|def _hlrecovery_blend_float(np_module, image_rgb, hlmax, ...|
|`_hlrecovery_blend_uint16`|fn|priv|11421-11422|def _hlrecovery_blend_uint16(|
|`_dilate_mask_float`|fn|priv|11457-11479|def _dilate_mask_float(np_module, mask)|
|`_box_mean_3x3_float`|fn|priv|11480-11503|def _box_mean_3x3_float(np_module, image_2d)|
|`_hlrecovery_color_propagation_float`|fn|priv|11504-11548|def _hlrecovery_color_propagation_float(np_module, image_...|
|`_hlrecovery_color_propagation_uint16`|fn|priv|11549-11550|def _hlrecovery_color_propagation_uint16(|
|`_hlrecovery_inpaint_opposed_float`|fn|priv|11580-11581|def _hlrecovery_inpaint_opposed_float(|
|`_hlrecovery_inpaint_opposed_uint16`|fn|priv|11634-11635|def _hlrecovery_inpaint_opposed_uint16(|
|`_apply_auto_brightness_rgb_float`|fn|priv|11677-11680|def _apply_auto_brightness_rgb_float(|
|`_clamp01`|fn|priv|11736-11749|def _clamp01(np_module, values)|
|`_gaussian_kernel_2d`|fn|priv|11750-11772|def _gaussian_kernel_2d(np_module, sigma, radius=None)|
|`_rgb_to_hsl`|fn|priv|11773-11806|def _rgb_to_hsl(np_module, rgb)|
|`_hue_to_rgb`|fn|priv|11807-11837|def _hue_to_rgb(np_module, p_values, q_values, t_values)|
|`_hsl_to_rgb`|fn|priv|11838-11878|def _hsl_to_rgb(np_module, hue, saturation, lightness)|
|`_selective_blur_contrast_gated_vectorized`|fn|priv|11879-11880|def _selective_blur_contrast_gated_vectorized(|
|`_level_per_channel_adaptive`|fn|priv|11929-11951|def _level_per_channel_adaptive(np_module, rgb, low_pct=0...|
|`_sigmoidal_contrast`|fn|priv|11952-11976|def _sigmoidal_contrast(np_module, rgb, contrast=3.0, mid...|
|`logistic`|fn|pub|11967-11969|def logistic(z_values)|
|`_vibrance_hsl_gamma`|fn|priv|11977-11994|def _vibrance_hsl_gamma(np_module, rgb, saturation_gamma=...|
|`_gaussian_blur_rgb`|fn|priv|11995-12018|def _gaussian_blur_rgb(cv2_module, np_module, rgb, sigma)|
|`_high_pass_math_gray`|fn|priv|12019-12042|def _high_pass_math_gray(cv2_module, np_module, rgb, blur...|
|`_overlay_composite`|fn|priv|12043-12064|def _overlay_composite(np_module, base_rgb, overlay_gray)|
|`_apply_validated_auto_adjust_pipeline`|fn|priv|12065-12071|def _apply_validated_auto_adjust_pipeline(|
|`_load_piexif_dependency`|fn|priv|12180-12197|def _load_piexif_dependency()|
|`_postprocess`|fn|priv|12198-12206|def _postprocess(|
|`_encode_jpg`|fn|priv|12336-12344|def _encode_jpg(|
|`_collect_processing_errors`|fn|priv|12404-12432|def _collect_processing_errors(rawpy_module)|
|`_is_supported_runtime_os`|fn|priv|12433-12452|def _is_supported_runtime_os()|
|`run`|fn|pub|12453-12652|def run(args)|


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

