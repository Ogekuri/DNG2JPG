---
title: "DNG2JPG Requirements"
description: Software requirements specification derived from implemented behavior
version: "0.3.0"
date: "2026-03-30"
author: "GitHub Copilot CLI (req-recreate)"
scope:
  paths:
    - "src/**/*.py"
    - "scripts/d2j.sh"
    - ".github/workflows/release-uvx.yml"
  excludes:
    - ".*/**"
    - "dist/**"
    - "build/**"
    - "temp/**"
    - ".venv/**"
visibility: "draft"
tags: ["requirements", "srs", "python", "cli"]
---

# DNG2JPG Requirements

## 1. Introduction

### 1.1 Document Rules
This document MUST be written and maintained in English.
- Use RFC 2119 keywords exclusively (MUST, MUST NOT, SHOULD, SHOULD NOT, MAY).
- Every requirement bullet MUST use this format: `- **<ID>**: <RFC2119 keyword> <single-sentence requirement>.`
- Requirement IDs MUST be unique and stable.
- Requirements MUST be atomic, single-sentence, and testable.

### 1.2 Project Scope
This SRS captures implemented behavior of the Python CLI conversion pipeline in `src/dng2jpg/`, launcher behavior in `scripts/d2j.sh`, and release automation behavior in `.github/workflows/release-uvx.yml`.

### 1.3 User Interface Surfaces
- Text-based UI: Implemented (CLI help, status, error, and success output).
- GUI: Not implemented.

### 1.4 Repository Structure (Evidence Snapshot)
```text
DNG2JPG/
├── .github/
│   └── workflows/
│       └── release-uvx.yml
├── docs/
│   ├── REFERENCES.md
│   └── REQUIREMENTS.md
├── scripts/
│   └── d2j.sh
├── src/
│   ├── dng2jpg/
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── core.py
│   │   └── dng2jpg.py
│   └── shell_scripts/
│       ├── __init__.py
│       └── utils.py
└── pyproject.toml
```

### 1.5 Components and Libraries (Evidenced)
- `rawpy`, `imageio`, `pillow`, `numpy`, `opencv-python-headless`, `piexif` (declared in `pyproject.toml` and imported in `src/dng2jpg/dng2jpg.py`).
- `uv` CLI is used by launcher/runtime management flows (`scripts/d2j.sh`, `src/dng2jpg/core.py`) and release build workflow (`.github/workflows/release-uvx.yml`).
- `enfuse`, `luminance-hdr-cli`, and ImageMagick (`magick` or `convert`) are runtime external executables resolved in `src/dng2jpg/dng2jpg.py`; HDR+ backend uses in-process Python/Numpy execution only.

### 1.6 Unit Test Coverage Summary
One unit test file was identified under `tests/`: `tests/test_uint16_postprocess_pipeline.py`.

### 1.7 Performance Optimization Evidence
Explicit optimization patterns are implemented in the OpenCV pipeline using vectorized NumPy operations (for example `_selective_blur_contrast_gated_vectorized`, `_level_per_channel_adaptive`, and tensor-domain clamp/overlay functions in `src/dng2jpg/dng2jpg.py`).

## 2. Project Requirements

### 2.1 Project Functions
- **PRJ-001**: MUST convert one input DNG into one output JPG using three synthetic RAW exposure brackets and one selected HDR merge backend.
- **PRJ-002**: MUST expose a CLI with options for exposure mode, EV center mode, postprocess controls, auto-brightness, auto-adjust, and backend selection.
- **PRJ-003**: MUST expose management commands for help, version, upgrade, and uninstall through the package entrypoint dispatcher.
- **PRJ-004**: MUST support release artifact publication through a GitHub Actions workflow triggered by semantic-version tags.
- **PRJ-005**: MUST expose a shell launcher that delegates argument-preserving execution to `uv run --project <repo-root> python -m dng2jpg`.

### 2.2 Project Constraints
- **CTN-001**: MUST execute conversion only on Linux runtime and reject unsupported operating systems with explicit error output.
- **CTN-002**: MUST require exactly one backend selector between `--enable-enfuse`, `--enable-luminance`, `--enable-opencv`, and `--enable-hdr-plus`.
- **CTN-003**: MUST require exactly one exposure selector between `--ev` and `--auto-ev`.
- **CTN-004**: MUST require `.dng` input extension, existing input file, and existing output parent directory.
- **CTN-005**: MUST fail when required Python modules or required backend executables for enabled features are unavailable.
- **CTN-006**: MUST reject launcher execution when resolved launcher base directory differs from repository git root.

## 3. Requirements

### 3.1 Design and Implementation
- **DES-001**: MUST parse CLI arguments by deterministic token scanning supporting both `--option value` and `--option=value` syntaxes.
- **DES-002**: MUST model runtime options with immutable dataclasses `AutoAdjustOptions`, `AutoBrightnessOptions`, `PostprocessOptions`, `LuminanceOptions`, and `AutoEvInputs`.
- **DES-003**: MUST derive supported EV and EV-zero quantized values from detected DNG bit depth using `0.25` EV step constraints.
- **DES-004**: MUST isolate intermediate processing artifacts in temporary directories and cleanup automatically after command completion.
- **DES-005**: MUST preserve source EXIF payload into output JPEG and refresh EXIF thumbnail/orientation metadata when EXIF payload exists.
- **DES-006**: MUST resolve backend-specific default postprocess factors based on selected backend and luminance tone-mapping operator.
- **DES-007**: MUST process conversion as a one-shot process model without spawning explicit application-managed threads.

### 3.2 Functions
- **REQ-001**: MUST print conversion help and exit successfully when conversion command receives no arguments.
- **REQ-002**: MUST print management help followed by conversion help when top-level `--help` is requested.
- **REQ-003**: MUST print package version and exit successfully for top-level `--ver` and `--version`.
- **REQ-004**: MUST execute `uv tool install` and `uv tool uninstall` automatically on Linux for management upgrade and uninstall commands.
- **REQ-005**: MUST print manual management commands instead of auto-executing them on non-Linux systems.
- **REQ-006**: MUST reject unknown options, missing option values, and invalid option values with explicit parse errors.
- **REQ-007**: MUST require `--auto-adjust` before accepting any `--aa-*` option and require `--auto-brightness` before accepting any `--ab-*` option.
- **REQ-008**: MUST compute automatic EV center from preview luminance when `--auto-zero` is enabled and clamp it to safe bit-derived bounds.
- **REQ-009**: MUST compute adaptive EV from preview luminance statistics when `--auto-ev` is enabled and clamp it to supported selectors.
- **REQ-010**: MUST write bracket TIFFs named `ev_minus.tif`, `ev_zero.tif`, and `ev_plus.tif` using `rawpy.postprocess` at `output_bps=16`.
- **REQ-011**: MUST run `enfuse` with LZW compression for enfuse backend and `luminance-hdr-cli` with deterministic HDR/TMO arguments for luminance backend.
- **REQ-012**: MUST execute post-gamma, brightness, contrast, and saturation in RGB uint16 precision and perform exactly one uint16-to-uint8 quantization immediately before final JPEG save.
- **REQ-013**: MUST execute optional auto-brightness, optional auto-levels, post-gamma, brightness, contrast, and saturation in this exact order before any optional auto-adjust stage.
- **REQ-106**: MUST execute optional auto-adjust stage after static postprocess and before final JPEG quantization/write while preserving uint16 processing buffers.
- **REQ-014**: MUST synchronize output file timestamps from EXIF datetime when EXIF datetime metadata is available.
- **REQ-015**: MUST return `1` on parse, validation, dependency, and processing errors, and return `0` on successful processing.
- **REQ-016**: MUST execute GitHub latest-release version checks with an idle-time cache file and print version status or check errors.
- **REQ-017**: MUST render conversion usage with canonical executable name `dng2jpg` and MUST NOT prepend alternative launcher labels.
- **REQ-018**: MUST support exactly one EV-zero selector between `--ev-zero` and `--auto-zero`.
- **REQ-019**: MUST enforce `--auto-zero-pct` and `--auto-ev-pct` values in inclusive range `0..100`.
- **REQ-020**: MUST parse `--gamma` as two positive numeric values and reject malformed pairs.
- **REQ-021**: MUST enforce `--jpg-compression` in inclusive range `0..100`.
- **REQ-022**: MUST reject luminance-specific options when `--enable-luminance` is not selected.
- **REQ-023**: MUST reject missing backend selector when both backend flags are false.
- **REQ-024**: MUST reject backend selection when both backend flags are true.
- **REQ-025**: MUST reject unsupported `--auto-adjust` mode values and accept only `ImageMagick` or `OpenCV`.
- **REQ-026**: MUST resolve DNG bit depth from `raw_image_visible.dtype.itemsize * 8` with fallback to `white_level.bit_length()`.
- **REQ-027**: MUST enforce minimum supported bit depth as `9` bits per color.
- **REQ-028**: MUST compute bracket EV ceiling with `MAX_BRACKET=((bits_per_color-8)/2)-abs(ev_zero)`.
- **REQ-029**: MUST compute EV-zero safe ceiling with `SAFE_ZERO_MAX=((bits_per_color-8)/2)-1`.
- **REQ-030**: MUST quantize EV and EV-zero computations on `0.25` EV step granularity.
- **REQ-031**: MUST derive adaptive EV from normalized preview luminance percentiles `0.1`, `50.0`, and `99.9`.
- **REQ-032**: MUST derive automatic EV-zero from scene-key-preserving median targets with low-key and high-key thresholds.
- **REQ-033**: MUST parse and preserve `--tmo*` passthrough option payloads for luminance command forwarding.
- **REQ-034**: MUST order luminance backend bracket inputs as `ev_minus`, `ev_zero`, `ev_plus`.
- **REQ-035**: MUST execute `luminance-hdr-cli` from output TIFF parent directory to isolate sidecar artifacts in temporary workspace.
- **REQ-036**: MUST resolve ImageMagick executable by probing `magick` first and `convert` second.
- **REQ-037**: MUST fail auto-adjust OpenCV mode when `cv2` or `numpy` dependencies are unavailable.
- **REQ-038**: MUST fail EXIF-preserving encode path when source EXIF payload exists and `piexif` is unavailable.
- **REQ-039**: MUST extract source EXIF timestamp with priority `DateTimeOriginal` then `DateTimeDigitized` then `DateTime`.
- **REQ-040**: MUST preserve source EXIF orientation in output `0th` IFD and set thumbnail orientation to `1`.
- **REQ-041**: MUST regenerate EXIF thumbnail from output JPEG pixels when source EXIF payload exists.
- **REQ-042**: MUST normalize integer-like EXIF values before `piexif.dump` and drop out-of-range integers for constrained integer tag types.
- **REQ-043**: MUST gate release build-and-publish job on `check-branch` output `is_master == "true"`.
- **REQ-044**: MUST trigger release workflow on `workflow_dispatch` and push tags matching `v[0-9]+.[0-9]+.[0-9]+`.
- **REQ-045**: MUST build release distributions using `uv run --frozen --with build python -m build`.
- **REQ-046**: MUST attest release artifacts with `actions/attest-build-provenance@v1` using `subject-path: dist/*`.
- **REQ-047**: MUST publish release assets from `dist/**/*` using `softprops/action-gh-release@v2` with `fail_on_unmatched_files: true`.
- **REQ-048**: MUST include project script entrypoints `dng2jpg` and `d2j` mapped to `dng2jpg.core:main`.
- **REQ-049**: SHOULD provide both `dng2jpg` and `d2j` as equivalent user-invokable CLI aliases.
- **REQ-050**: MUST implement auto-brightness on RGB uint16 input/output with internal float processing using sRGB linearization, BT.709 luminance computation, and key-adaptive photographic Reinhard mapping.
- **REQ-051**: MUST support both ImageMagick and OpenCV auto-adjust pipelines with shared validated knob parameters.
- **REQ-052**: MUST print deterministic runtime diagnostics for input path, gamma, postprocess factors, backend, EV selections, and EV triplet.
- **REQ-103**: MUST classify scene key from log-average luminance, median, and 5th/95th percentiles, then auto-select key value from `0.09`, `0.18`, `0.36` with configurable clamp and auto-boost limits.
- **REQ-104**: MUST map luminance with `L=(a/Lw_bar)*Y`, percentile-derived robust `Lwhite`, and burn-out compression `Ld=(L*(1+L/Lwhite^2))/(1+L)` before linear-domain chromaticity-preserving RGB scaling.
- **REQ-105**: MUST prevent out-of-gamut clipping by luminance-preserving desaturation only for overflowing pixels and MAY apply mild CLAHE local contrast on luminance with configurable strength and clip limit.
- **REQ-100**: MUST execute `--auto-levels` after optional `--auto-brightness` and before static postprocess while preserving RGB `uint16` input/output buffers and float internal calculations.
- **REQ-101**: MUST parse `--auto-levels`, `--al-clip-pct`, `--al-clip-out-of-gamut`, `--al-highlight-reconstruction-method`, and `--al-gain-threshold`, requiring `--auto-levels` before any `--al-*` option.
- **REQ-102**: MUST accept highlight reconstruction methods `Luminance Recovery`, `CIELab Blending`, `Blend`, `Color Propagation`, and `Inpaint Opposed`.
- **REQ-116**: MUST default auto-levels knobs to `clip_pct=0.02`, `clip_out_of_gamut=true`, `highlight_reconstruction=disabled`, `highlight_reconstruction_method=Inpaint Opposed`, and `gain_threshold=1.0`.
- **REQ-117**: MUST derive auto-levels calibration from a RawTherapee-compatible luminance histogram using `sum`, `average`, `median`, octiles, `ospread`, `rawmax`, clipped white point, and clipped black point.
- **REQ-118**: MUST derive `expcomp`, `black`, `brightness`, `contrast`, `hlcompr`, and `hlcomprthresh` using RawTherapee `ImProcFunctions::getAutoExp` formula families, including gamma-domain whiteclip correction.
- **REQ-119**: MUST map `Color Propagation` to RawTherapee `Color` and `Inpaint Opposed` to RawTherapee `Coloropp`, and SHOULD approximate these raw-domain methods deterministically in RGB post-merge processing.
- **REQ-120**: MUST apply `Clip out-of-gamut colors` after auto-levels gain using per-pixel normalization that bounds each overflowing RGB triplet to the uint16 ceiling while preserving channel ratios.
- **REQ-107**: MUST accept `--enable-opencv` as HDR backend selector and enforce backend exclusivity across `--enable-enfuse`, `--enable-luminance`, `--enable-opencv`, and `--enable-hdr-plus`.
- **REQ-108**: MUST execute OpenCV backend merge using `MergeMertens` and `MergeDebevec` over bracket TIFFs ordered as `ev_minus`, `ev_zero`, `ev_plus` with EV-derived exposure times.
- **REQ-109**: MUST normalize Debevec HDR radiance in float domain using robust luminance white-point percentile and blend it with Mertens fusion before writing merged TIFF.
- **REQ-110**: MUST preserve 16-bit-per-channel processing in OpenCV backend by executing merge/blend in float domain and converting to `uint16` once when writing merged TIFF.
- **REQ-111**: MUST accept `--enable-hdr-plus` as HDR backend selector and enforce backend exclusivity across `--enable-enfuse`, `--enable-luminance`, `--enable-opencv`, and `--enable-hdr-plus`.
- **REQ-112**: MUST execute HDR+ backend in source step order `box_down2 -> temporal merge -> spatial merge`, using `ev_zero` as reference frame and zero alignment offsets for all tiles.
- **REQ-113**: MUST compute HDR+ temporal alternate-frame weights from per-tile L1 distance over 16x16 downsampled tiles with `factor=8`, `min_dist=10`, `max_dist=300`, and reference-inclusive normalization.
- **REQ-114**: MUST execute HDR+ spatial blending over half-overlapped 32x32 tiles using raised-cosine weights and write one RGB `uint16` merged TIFF without intermediate `uint8` quantization.
- **REQ-115**: MUST adapt single-channel HDR+ merge input to aligned RGB bracket TIFFs by deriving one deterministic scalar merge proxy from each RGB pixel before `box_down2` and temporal weighting.

## 4. Test Requirements

- **TST-001**: MUST verify `_parse_run_options` rejects missing or simultaneous exposure/backend selectors and returns `None` with deterministic error output.
- **TST-002**: MUST verify `run` returns `1` for unsupported runtime OS, missing external executables, and missing Python dependencies.
- **TST-003**: MUST verify successful `run` execution returns `0`, writes output JPG, and emits success message `HDR JPG created: <output>`.
- **TST-004**: MUST verify `_resolve_ev_zero` enforces `SAFE_ZERO_MAX=((bits_per_color-8)/2)-1` and rejects out-of-range values.
- **TST-005**: MUST verify `_resolve_ev_value` clamps adaptive EV to bit-derived selector bounds and rejects unsupported static EV for the detected bit depth.
- **TST-006**: MUST verify `_run_luminance_hdr_cli` builds deterministic argument order and includes any `--tmo*` passthrough pairs unchanged.
- **TST-007**: MUST verify `_extract_dng_exif_payload_and_timestamp` applies datetime priority `36867` then `36868` then `306`.
- **TST-008**: MUST verify `_refresh_output_jpg_exif_thumbnail_after_save` preserves source orientation in `0th` IFD and sets `1st` IFD orientation to `1`.
- **TST-009**: MUST verify release workflow gates `build-release` execution on `needs.check-branch.outputs.is_master == "true"`.
- **TST-010**: MUST verify `_parse_run_options` enforces `--auto-levels`/`--al-*` coupling and validates `Clip out-of-gamut colors`, `Clip %`, method, and gain-threshold knobs.
- **TST-011**: MUST verify `_apply_auto_brightness_rgb_uint8` preserves uint16 I/O and executes key-adaptive Reinhard luminance mapping with luminance-preserving anti-clipping desaturation and optional CLAHE local-contrast blending.
- **TST-012**: MUST verify `_encode_jpg` keeps uint16 static postprocess buffers and applies a single uint16-to-uint8 conversion immediately before JPEG save.
- **TST-013**: MUST verify `_parse_run_options` accepts `--enable-opencv` and rejects simultaneous backend selectors.
- **TST-014**: MUST verify OpenCV EV-time derivation returns deterministic three-element stop-space sequence mapped to bracket order.
- **TST-015**: MUST verify Debevec normalization clamps blended radiance contribution to `[0,1]` float range before uint16 conversion.
- **TST-016**: MUST verify auto-levels parser defaults `clip_pct=0.02`, `clip_out_of_gamut=true`, `highlight_reconstruction_method=Inpaint Opposed`, and `gain_threshold=1.0`.
- **TST-017**: MUST verify auto-levels histogram calibration reproduces RawTherapee-compatible `expcomp`, `black`, `brightness`, `contrast`, `hlcompr`, and `hlcomprthresh` for deterministic synthetic histograms.
- **TST-018**: MUST verify `Color Propagation` and `Inpaint Opposed` selectors produce deterministic RGB `uint16` outputs and preserve float-only internal math within the auto-levels stage.

## 5. Evidence Matrix

| Requirement ID | Evidence |
|---|---|
| PRJ-001 | `src/dng2jpg/dng2jpg.py::run` and `_write_bracket_images`; excerpt: writes `ev_minus.tif`, `ev_zero.tif`, `ev_plus.tif` then merges via selected backend. |
| PRJ-002 | `src/dng2jpg/dng2jpg.py::print_help`, `_parse_run_options`; excerpt: documents and parses exposure, EV-center, backend, postprocess, auto-adjust, and auto-brightness controls. |
| PRJ-003 | `src/dng2jpg/core.py::main`; excerpt: handles `--help`, `--ver`, `--version`, `--upgrade`, `--uninstall`, and conversion dispatch. |
| PRJ-004 | `.github/workflows/release-uvx.yml`; excerpt: semantic tag trigger, build job, attestation, and GitHub release upload flow. |
| PRJ-005 | `scripts/d2j.sh`; excerpt: `exec "${UV_TOOL}" run --project "${BASE_DIR}" python -m dng2jpg "$@"`. |
| CTN-001 | `src/dng2jpg/dng2jpg.py::_is_supported_runtime_os`; excerpt: returns true only on Linux and prints Linux-only error otherwise. |
| CTN-002 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: counts four backend selectors and emits "Exactly one backend selector is required: --enable-enfuse, --enable-luminance, --enable-opencv, or --enable-hdr-plus". |
| CTN-003 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: emits "Exactly one exposure selector is required". |
| CTN-004 | `src/dng2jpg/dng2jpg.py::run`; excerpt: validates `.dng` suffix, input existence, and output parent directory existence. |
| CTN-005 | `src/dng2jpg/dng2jpg.py::_load_image_dependencies`, dependency checks in `run`; excerpt: explicit missing dependency diagnostics and return `1`. |
| CTN-006 | `scripts/d2j.sh`; excerpt: compares `${PROJECT_ROOT}` and `${BASE_DIR}` and exits `1` on mismatch. |
| DES-001 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: deterministic token scan loop over args with explicit branch handling. |
| DES-002 | `src/dng2jpg/dng2jpg.py` dataclasses; evidence: `AutoAdjustOptions`, `AutoBrightnessOptions`, `PostprocessOptions`, `LuminanceOptions`, `AutoEvInputs`. |
| DES-003 | `src/dng2jpg/dng2jpg.py::_derive_supported_ev_values`, `_derive_supported_ev_zero_values`; excerpt: uses `EV_STEP = 0.25`. |
| DES-004 | `src/dng2jpg/dng2jpg.py::run`, `_encode_jpg`; excerpt: `TemporaryDirectory(prefix="dng2jpg-")` and nested auto-adjust temp directory. |
| DES-005 | `src/dng2jpg/dng2jpg.py::_extract_dng_exif_payload_and_timestamp`, `_refresh_output_jpg_exif_thumbnail_after_save`, `_encode_jpg`. |
| DES-006 | `src/dng2jpg/dng2jpg.py::_resolve_default_postprocess`; excerpt: backend and TMO-specific defaults. |
| DES-007 | `docs/WORKFLOW.md`; excerpt: execution-unit model shows process-based flows and "no explicit threads detected". |
| REQ-001 | `src/dng2jpg/core.py::main`; excerpt: no args -> `ported.print_help(__version__)` and `return 0`. |
| REQ-002 | `src/dng2jpg/core.py::main`; excerpt: `--help` prints management help and conversion help. |
| REQ-003 | `src/dng2jpg/core.py::main`; excerpt: `--ver` and `--version` print version and return `0`. |
| REQ-004 | `src/dng2jpg/core.py::_run_management`, `main`; excerpt: executes `uv tool install ...` and `uv tool uninstall` on Linux. |
| REQ-005 | `src/dng2jpg/core.py::_run_management`; excerpt: non-Linux path prints manual command and returns `0`. |
| REQ-006 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: explicit errors for unknown option and missing values. |
| REQ-007 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: rejects `--aa-*` without `--auto-adjust` and `--ab-*` without `--auto-brightness`. |
| REQ-008 | `src/dng2jpg/dng2jpg.py::_resolve_ev_zero`; excerpt: auto-zero path and safe-range check with `SAFE_ZERO_MAX`. |
| REQ-009 | `src/dng2jpg/dng2jpg.py::_resolve_ev_value`, `_compute_auto_ev_value_from_stats`; excerpt: adaptive EV from preview stats with clamp. |
| REQ-010 | `src/dng2jpg/dng2jpg.py::_write_bracket_images`; excerpt: writes `ev_minus.tif`, `ev_zero.tif`, `ev_plus.tif` at `output_bps=16`. |
| REQ-011 | `src/dng2jpg/dng2jpg.py::_run_enfuse`, `_run_luminance_hdr_cli`; excerpt: `--compression=lzw`, deterministic luminance args, and `--ldrTiff 16b`. |
| REQ-012 | `src/dng2jpg/dng2jpg.py::_encode_jpg`; excerpt: gamma LUT + brightness/contrast/saturation + quality mapping save flow. |
| REQ-013 | `src/dng2jpg/dng2jpg.py::_encode_jpg`; excerpt: auto-brightness executes before auto-levels and postprocess factors; optional auto-adjust executes before final JPEG save. |
| REQ-014 | `src/dng2jpg/dng2jpg.py::_sync_output_file_timestamps_from_exif`; excerpt: applies `os.utime` when EXIF timestamp exists. |
| REQ-015 | `src/dng2jpg/dng2jpg.py::run`; excerpt: parse/dependency/processing failures return `1`, success returns `0`. |
| REQ-016 | `src/dng2jpg/core.py::_check_online_version`; excerpt: GitHub API check with idle-time cache policy and error/status outputs. |
| REQ-017 | `src/dng2jpg/dng2jpg.py`; excerpt: `PROGRAM = "dng2jpg"` and help usage renders canonical command label without duplicated command token. |
| REQ-018 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: rejects simultaneous `--ev-zero` and `--auto-zero`. |
| REQ-019 | `src/dng2jpg/dng2jpg.py::_parse_percentage_option`; excerpt: enforces inclusive `0..100` bounds. |
| REQ-020 | `src/dng2jpg/dng2jpg.py::_parse_gamma_option`; excerpt: requires two positive numeric values. |
| REQ-021 | `src/dng2jpg/dng2jpg.py::_parse_jpg_compression_option`; excerpt: enforces inclusive `0..100`. |
| REQ-022 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: rejects luminance options without `--enable-luminance`. |
| REQ-023 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: rejects missing backend selection. |
| REQ-024 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: rejects both backends enabled simultaneously. |
| REQ-025 | `src/dng2jpg/dng2jpg.py::_parse_auto_adjust_mode_option`; excerpt: allowed values restricted to `ImageMagick` and `OpenCV`. |
| REQ-026 | `src/dng2jpg/dng2jpg.py::_detect_dng_bits_per_color`; excerpt: container bit depth primary path with white-level fallback. |
| REQ-027 | `src/dng2jpg/dng2jpg.py::_calculate_max_ev_from_bits`; excerpt: raises on bit depth below `MIN_SUPPORTED_BITS_PER_COLOR=9`. |
| REQ-028 | `src/dng2jpg/dng2jpg.py::_derive_supported_ev_values`; excerpt: uses `MAX_BRACKET=((bits_per_color-8)/2)-abs(ev_zero)`. |
| REQ-029 | `src/dng2jpg/dng2jpg.py::_calculate_safe_ev_zero_max`; excerpt: `SAFE_ZERO_MAX = BASE_MAX - 1`. |
| REQ-030 | `src/dng2jpg/dng2jpg.py::_is_ev_value_on_supported_step`; excerpt: quarter-step quantization validation. |
| REQ-031 | `src/dng2jpg/dng2jpg.py::_extract_normalized_preview_luminance_stats`; excerpt: percentiles `0.1`, `50.0`, `99.9`. |
| REQ-032 | `src/dng2jpg/dng2jpg.py::_derive_scene_key_preserving_median_target`; excerpt: low/high thresholds and key-preserving median targets. |
| REQ-033 | `src/dng2jpg/dng2jpg.py::_parse_tmo_passthrough_value`, `_run_luminance_hdr_cli`; excerpt: parses and forwards `--tmo*` args unchanged. |
| REQ-034 | `src/dng2jpg/dng2jpg.py::_order_bracket_paths`; excerpt: deterministic `ev_minus`, `ev_zero`, `ev_plus` order. |
| REQ-035 | `src/dng2jpg/dng2jpg.py::_run_luminance_hdr_cli`; excerpt: changes cwd to output parent before subprocess execution. |
| REQ-036 | `src/dng2jpg/dng2jpg.py::_resolve_imagemagick_command`; excerpt: probes `magick` then `convert`. |
| REQ-037 | `src/dng2jpg/dng2jpg.py::_resolve_auto_adjust_opencv_dependencies`; excerpt: explicit failure when cv2/numpy missing. |
| REQ-038 | `src/dng2jpg/dng2jpg.py::run`, `_load_piexif_dependency`; excerpt: fails when source EXIF exists and piexif is missing. |
| REQ-039 | `src/dng2jpg/dng2jpg.py::_extract_dng_exif_payload_and_timestamp`; excerpt: datetime tag precedence `36867` > `36868` > `306`. |
| REQ-040 | `src/dng2jpg/dng2jpg.py::_refresh_output_jpg_exif_thumbnail_after_save`; excerpt: source orientation in `0th`, thumbnail orientation `1` in `1st`. |
| REQ-041 | `src/dng2jpg/dng2jpg.py::_build_oriented_thumbnail_jpeg_bytes`; excerpt: regenerated thumbnail from output JPG. |
| REQ-042 | `src/dng2jpg/dng2jpg.py::_normalize_ifd_integer_like_values_for_piexif_dump`; excerpt: normalize/drop unsupported integer-like values. |
| REQ-043 | `.github/workflows/release-uvx.yml`; excerpt: `if: needs.check-branch.outputs.is_master == 'true'`. |
| REQ-044 | `.github/workflows/release-uvx.yml`; excerpt: triggers on `workflow_dispatch` and semantic tag pattern. |
| REQ-045 | `.github/workflows/release-uvx.yml`; excerpt: `uv run --frozen --with build python -m build`. |
| REQ-046 | `.github/workflows/release-uvx.yml`; excerpt: `actions/attest-build-provenance@v1` with `subject-path: dist/*`. |
| REQ-047 | `.github/workflows/release-uvx.yml`; excerpt: `softprops/action-gh-release@v2` uploads `dist/**/*` with unmatched-file failure enabled. |
| REQ-048 | `pyproject.toml`; excerpt: `[project.scripts] dng2jpg = "dng2jpg.core:main"` and `d2j = "dng2jpg.core:main"`. |
| REQ-049 | `pyproject.toml`; excerpt: both `dng2jpg` and `d2j` map to identical entrypoint. |
| REQ-050 | `src/dng2jpg/dng2jpg.py::_apply_auto_brightness_rgb_uint8`; excerpt: uint16 I/O, float linearization, BT.709 luminance, and Reinhard photographic tonemap pipeline. |
| REQ-051 | `src/dng2jpg/dng2jpg.py::_apply_validated_auto_adjust_pipeline`, `_apply_validated_auto_adjust_pipeline_opencv`; excerpt: two implementations using shared knob dataclass. |
| REQ-052 | `src/dng2jpg/dng2jpg.py::run`; excerpt: deterministic `print_info` diagnostic lines for runtime selections and computed EV values. |
| REQ-103 | `src/dng2jpg/dng2jpg.py::_analyze_luminance_key`, `_choose_auto_key_value`; excerpt: log-average/percentile scene classification and key auto-selection from low/normal/high presets. |
| REQ-104 | `src/dng2jpg/dng2jpg.py::_reinhard_global_tonemap_luminance`, `_apply_auto_brightness_rgb_uint8`; excerpt: percentile robust `Lwhite` and burn-out compression before RGB scaling. |
| REQ-105 | `src/dng2jpg/dng2jpg.py::_luminance_preserving_desaturate_to_fit`, `_apply_mild_local_contrast_bgr_uint16`; excerpt: overflow-only luminance-preserving desaturation and optional CLAHE luminance blend. |
| REQ-100 | `src/dng2jpg/dng2jpg.py::_apply_static_postprocess_uint16`, `_apply_auto_levels_uint16`; excerpt: executes auto-levels in the static postprocess chain without leaving uint16/float domains. |
| REQ-101 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `_parse_auto_levels_options`; excerpt: parses `--auto-levels` plus all `--al-*` knobs with explicit coupling and validation. |
| REQ-102 | `src/dng2jpg/dng2jpg.py::_parse_auto_levels_hr_method_option`, `_apply_auto_levels_uint16`; excerpt: validates the full RawTherapee-aligned highlight reconstruction method set. |
| REQ-116 | `src/dng2jpg/dng2jpg.py::AutoLevelsOptions`, `_parse_auto_levels_options`; excerpt: sets parser defaults for clip percentage, gamut clipping, highlight method, and gain threshold. |
| REQ-117 | `src/dng2jpg/dng2jpg.py::_build_autoexp_histogram_rgb_uint16`, `_compute_auto_levels_from_histogram`; excerpt: derives RawTherapee-compatible histogram statistics and clipping points. |
| REQ-118 | `src/dng2jpg/dng2jpg.py::_compute_auto_levels_from_histogram`; excerpt: implements RawTherapee-compatible formulas for `expcomp`, `black`, `brightness`, `contrast`, and highlight-compression outputs. |
| REQ-119 | `src/dng2jpg/dng2jpg.py::_apply_auto_levels_uint16`; excerpt: maps CLI method names to RawTherapee `Color`/`Coloropp` semantics and applies deterministic RGB-space approximations. |
| REQ-120 | `src/dng2jpg/dng2jpg.py::_clip_auto_levels_out_of_gamut_uint16`, `_apply_auto_levels_uint16`; excerpt: normalizes overflowing RGB triplets to the uint16 ceiling while preserving channel ratios. |
| REQ-107 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `print_help`; excerpt: parses `--enable-opencv`, enforces single backend selector, and documents exclusivity across four backend flags. |
| REQ-108 | `src/dng2jpg/dng2jpg.py::_run_opencv_hdr_merge`, `_build_ev_times_from_ev_zero_and_delta`; excerpt: executes OpenCV Mertens+Debevec using ordered bracket inputs and EV-derived exposure times. |
| REQ-109 | `src/dng2jpg/dng2jpg.py::_normalize_debevec_hdr_to_unit_range`, `_run_opencv_hdr_merge`; excerpt: applies robust luminance white-point percentile normalization and blends Debevec with Mertens in float domain. |
| REQ-110 | `src/dng2jpg/dng2jpg.py::_run_opencv_hdr_merge`; excerpt: maintains float-domain processing and performs one float-to-uint16 conversion for merged TIFF write. |
| REQ-111 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `print_help`, `run`; excerpt: accepts `--enable-hdr-plus`, documents backend, and routes execution to HDR+ merge path. |
| REQ-112 | `src/dng2jpg/dng2jpg.py::_order_hdr_plus_reference_paths`, `_hdrplus_box_down2_uint16`, `_hdrplus_merge_temporal_rgb`, `_hdrplus_merge_spatial_rgb`, `_run_hdr_plus_merge`; excerpt: executes source order `box_down2 -> temporal merge -> spatial merge` with `ev_zero` reference and no alignment offsets. |
| REQ-113 | `src/dng2jpg/dng2jpg.py::_hdrplus_compute_temporal_weights`; excerpt: applies 16x16 tile L1 distance with `factor=8`, `min_dist=10`, `max_dist=300`, and reference-inclusive normalization. |
| REQ-114 | `src/dng2jpg/dng2jpg.py::_hdrplus_merge_spatial_rgb`, `_run_hdr_plus_merge`; excerpt: blends half-overlapped 32x32 tiles with raised-cosine weights and writes RGB `uint16` merged TIFF. |
| REQ-115 | `src/dng2jpg/dng2jpg.py::_hdrplus_luminance_proxy_uint16`, `_run_hdr_plus_merge`; excerpt: derives deterministic scalar merge proxy from aligned RGB bracket TIFFs before downsampling and weighting. |
| TST-001 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; branches for selector exclusivity and deterministic parse failures. |
| TST-002 | `src/dng2jpg/dng2jpg.py::run`; branches for unsupported OS and dependency failures returning `1`. |
| TST-003 | `src/dng2jpg/dng2jpg.py::run`; success branch prints `HDR JPG created: ...` and returns `0`. |
| TST-004 | `src/dng2jpg/dng2jpg.py::_resolve_ev_zero`; safe-range enforcement branch raises on out-of-range EV-zero. |
| TST-005 | `src/dng2jpg/dng2jpg.py::_resolve_ev_value`; adaptive clamp and static EV validity checks. |
| TST-006 | `src/dng2jpg/dng2jpg.py::_run_luminance_hdr_cli`; deterministic argv generation including passthrough. |
| TST-007 | `src/dng2jpg/dng2jpg.py::_extract_dng_exif_payload_and_timestamp`; explicit EXIF datetime tag priority loop. |
| TST-008 | `src/dng2jpg/dng2jpg.py::_refresh_output_jpg_exif_thumbnail_after_save`; orientation handling in `0th` and `1st` IFDs. |
| TST-009 | `.github/workflows/release-uvx.yml`; release job condition depends on `is_master` gate output. |
| TST-010 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; branch checks for `--auto-levels` coupling and all `--al-*` knob validations. |
| TST-011 | `src/dng2jpg/dng2jpg.py::_apply_auto_brightness_rgb_uint8`, `_apply_mild_local_contrast_bgr_uint16`; stage preserves uint16 domain with key-adaptive tonemap, anti-clipping desaturation, and optional CLAHE blend. |
| TST-013 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_enable_opencv_backend`, `test_parse_run_options_rejects_multiple_backends_with_opencv`; validates acceptance and exclusivity for `--enable-opencv`. |
| TST-014 | `tests/test_uint16_postprocess_pipeline.py::test_build_ev_times_from_ev_zero_and_delta_matches_bracket_sequence`; verifies deterministic stop-space EV-time sequence generation. |
| TST-015 | `tests/test_uint16_postprocess_pipeline.py::test_normalize_debevec_hdr_to_unit_range_clamps_to_valid_interval`; verifies Debevec normalization clamps float output to `[0,1]`. |
| TST-016 | `tests/test_uint16_postprocess_pipeline.py::test_parse_auto_levels_options_defaults_match_rawtherapee`; verifies parser default values for clip percentage, gamut clipping, method, and gain threshold. |
| TST-017 | `tests/test_uint16_postprocess_pipeline.py::test_compute_auto_levels_from_histogram_matches_rawtherapee_reference`; verifies RawTherapee-compatible auto-levels numeric outputs for deterministic histograms. |
| TST-018 | `tests/test_uint16_postprocess_pipeline.py::test_apply_auto_levels_color_methods_preserve_uint16_pipeline`; verifies deterministic `Color Propagation` and `Inpaint Opposed` RGB uint16 execution. |
