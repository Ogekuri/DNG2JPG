---
title: "DNG2JPG Requirements"
description: Software requirements specification derived from implemented behavior
version: "0.5.0"
date: "2026-04-03"
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
- `rawpy`, `imageio`, `pillow`, `numpy`, `opencv-python-headless`, `piexif`, `exifread` (declared in `pyproject.toml` and imported in `src/dng2jpg/dng2jpg.py`).
- `uv` CLI is used by launcher/runtime management flows (`scripts/d2j.sh`, `src/dng2jpg/core.py`) and release build workflow (`.github/workflows/release-uvx.yml`).
- `luminance-hdr-cli` is the only runtime external executable resolved in `src/dng2jpg/dng2jpg.py`; OpenCV and HDR+ backends use in-process Python/Numpy execution only.

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
- **CTN-002**: MUST parse `--hdr-merge <Luminace-HDR|OpenCV-Merge|OpenCV-Tonemap|HDR-Plus>` and MUST default to `OpenCV-Tonemap` when omitted.
- **CTN-003**: MUST resolve `ev_delta` from `--bracketing`: absent → automatic iterative algorithm; `--bracketing=<value>` → `ev_delta=<value>` (static); `--bracketing=auto` → `ev_delta` from iterative automatic algorithm.
- **CTN-007**: MUST resolve `ev_zero` from `--exposure`: absent → `ev_zero=min(ev_best, ev_ettr, ev_detail)` preserving candidate signs; `--exposure=<value>` → `ev_zero=<value>` (static); `--exposure=auto` → `ev_zero=min(ev_best, ev_ettr, ev_detail)` preserving candidate signs.
- **CTN-004**: MUST require `.dng` input extension, existing input file, and existing output parent directory.
- **CTN-005**: MUST preflight-check each external executable selected by resolved options (`luminance-hdr-cli`) and MUST fail before processing with explicit diagnostics naming every missing executable.
- **CTN-006**: MUST reject launcher execution when resolved launcher base directory differs from repository git root.

## 3. Requirements

### 3.1 Design and Implementation
- **DES-001**: MUST parse CLI arguments by deterministic token scanning accepting exclusively the `--option=value` syntax and rejecting the separated `--option value` form for every value-bearing option.
- **REQ-202**: MUST reject any value-bearing CLI option whose value is not embedded via the `=` separator in the same token, emitting deterministic diagnostics and returning a parse failure.
- **DES-002**: MUST model runtime options with immutable dataclasses `AutoAdjustOptions`, `AutoBrightnessOptions`, `PostprocessOptions`, `LuminanceOptions`, and `AutoEvInputs`.
- **DES-003**: MUST parse static EV selectors as finite numeric values without quantization-step enforcement or bit-depth-derived upper-bound contracts.
- **DES-004**: MUST isolate intermediate processing artifacts in temporary directories and cleanup automatically after command completion.
- **DES-005**: MUST preserve source EXIF payload into output JPEG, rebuild EXIF thumbnail from the exact final quantized RGB uint8 save buffer, preserve JPEG-display-equivalent thumbnail orientation, and write refreshed EXIF metadata before timestamp synchronization.
- **DES-006**: MUST resolve backend-specific default postprocess factors from selected `--hdr-merge` mode, resolved `Luminace-HDR` tone-mapping operator, resolved OpenCV merge algorithm, and resolved OpenCV-Tonemap algorithm selector.
- **DES-008**: MUST resolve static postprocess defaults per backend variant as tuples `(post_gamma,brightness,contrast,saturation)` using deterministic mappings for `HDR-Plus`, `Luminace-HDR`, `OpenCV-Merge`, and `OpenCV-Tonemap`.
- **DES-007**: MUST process conversion as a one-shot process model without spawning explicit application-managed threads.
- **DES-009**: MUST serialize `--debug` checkpoints from normalized RGB float stage buffers into persistent TIFF16 files outside the temporary workspace lifecycle.
- **DES-010**: MUST declare `exifread` as a project runtime dependency for merge-gamma EXIF binary stream extraction.

### 3.2 Functions
- **REQ-001**: MUST print conversion help and exit successfully when conversion command receives no arguments.
- **REQ-002**: MUST print management help followed by conversion help when top-level `--help` is requested.
- **REQ-003**: MUST print package version and exit successfully for top-level `--ver` and `--version`.
- **REQ-004**: MUST execute `uv tool install` and `uv tool uninstall` automatically on Linux for management upgrade and uninstall commands.
- **REQ-005**: MUST print manual management commands instead of auto-executing them on non-Linux systems.
- **REQ-006**: MUST reject unknown options, missing option values, and invalid option values with explicit parse errors.
- **REQ-007**: MUST reject `--aa-*` options when `--auto-adjust` resolves to `disable`, MUST reject `--ab-*` options when `--auto-brightness` resolves to `disable`, and MUST default omitted `--auto-brightness` to `disable`.
- **REQ-008**: MUST compute `ev_best`, `ev_ettr`, and `ev_detail` from the normalized linear HDR base image only when `--exposure=auto` or `--bracketing=auto` is active.
- **REQ-009**: MUST compute one symmetric EV triplet `(ev_zero-ev_delta, ev_zero, ev_zero+ev_delta)`.
- **REQ-010**: MUST extract one maximum-resolution demosaiced RGB base image using one neutral linear `rawpy.postprocess` call with `gamma=(1,1)`, `no_auto_bright=True`, `output_bps=16`, `use_camera_wb=False`, `user_wb=[1,1,1,1]`, `output_color=raw`, and `no_auto_scale=True`.
- **REQ-158**: MUST normalize neutral base extraction using sensor dynamic range `(white_level - mean(black_level_per_channel))`, then apply camera white-balance gains normalized by the resolved RAW white-balance normalization mode before any bracket arithmetic.
- **REQ-159**: MUST derive `ev_zero` only by EV scaling and `[0,1]` clipping of the normalized HDR base image.
- **REQ-160**: MUST preserve the ordered bracket contract `(ev_minus, ev_zero, ev_plus)` and allow backend-specific optional side brackets to be represented as `None`.
- **REQ-215**: MUST derive `ev_minus` and `ev_plus` by EV scaling and `[0,1]` clipping only when the selected backend consumes side brackets.
- **REQ-011**: MUST run `luminance-hdr-cli` with deterministic HDR/TMO arguments including `--ldrTiff 32b` for luminance backend, MUST print the full executed command syntax with parameters to runtime output, confine any required float32 TIFF intermediates to the backend step, and return normalized RGB float output.
- **REQ-174**: MUST serialize luminance backend input bracket images from DNG2JPG RGB float `[0,1]` working format into TIFF float32 files before `luminance-hdr-cli` execution.
- **REQ-175**: MUST import `luminance-hdr-cli` output TIFF float32 data and normalize it back to DNG2JPG RGB float `[0,1]` working format.
- **REQ-012**: MUST exchange RGB float tensors across linear-base extraction, auto-brightness, auto-white-balance, auto-zero evaluation, bracket generation, merge, dedicated postprocess orchestration, auto-adjust, and final-save preparation stages with finite-safe sample handling at stage boundaries.
- **REQ-013**: MUST execute optional auto-brightness after `_extract_base_rgb_linear_float` and before `_calculate_auto_zero_evaluations`; static postprocess MUST keep `gamma->brightness->contrast->saturation`, and its brightness substage MUST apply only static/manual brightness.
- **REQ-106**: MUST execute optional auto-adjust stage after static postprocess and before final JPEG quantization/write, preserve RGB float input/output interfaces, and confine any required float-to-uint16 or TIFF16 conversions to the auto-adjust step itself.
- **REQ-014**: MUST synchronize output file timestamps from EXIF datetime only after refreshed EXIF metadata has been written when EXIF datetime metadata is available.
- **REQ-015**: MUST return `1` on parse, validation, dependency, and processing errors, and return `0` on successful processing.
- **REQ-016**: MUST execute GitHub latest-release version checks with an idle-time cache JSON file and print check errors or version status only when latest and installed versions differ.
- **REQ-150**: MUST use idle-delay `3600` seconds after successful latest-release checks and idle-delay `86400` seconds after any latest-release check error.
- **REQ-151**: MUST recalculate idle-time and rewrite the version-check cache JSON after every latest-release API attempt, regardless of success or error outcome.
- **REQ-017**: MUST render conversion usage/help with canonical executable name `dng2jpg`, stable aligned indentation, and MUST NOT prepend alternative launcher labels.
- **REQ-019**: MUST accept `--auto-ev-shadow-clipping` and `--auto-ev-highlight-clipping` as percentage thresholds in inclusive range `0..100`, defaulting both to `20`.
- **REQ-020**: MUST parse `--gamma=auto` as the default HDR merge-output transfer selector and MUST accept `--gamma=<linear_coeff,exponent>` as one explicit custom transfer selector.
- **REQ-169**: MUST resolve `--gamma=auto` from original RAW/DNG EXIF color-space evidence extracted via `exifread` binary stream processing, mapping sRGB to IEC 61966-2-1 transfer, Adobe RGB to power gamma `2.19921875`, and unresolved evidence to sRGB transfer as default fallback.
- **REQ-170**: MUST apply resolved merge gamma only as the last backend-local step of OpenCV `Debevec`/`Robertson` and `HDR-Plus` HDR merge pipelines, after backend normalization and before shared static postprocess, without additional clipping above backend normalization.
- **REQ-171**: MUST print deterministic merge-gamma runtime diagnostics containing the user request, resolved transfer label, parameter payload, and evidence source.
- **REQ-172**: MUST print normalized EXIF merge-gamma inputs containing `ColorSpace`, `InteroperabilityIndex`, `ImageModel`, `ImageMake`, and a human-readable `ColorProfile` label derived from `ColorSpace` and `InteroperabilityIndex` values whenever `--gamma=auto` is resolved from RAW/DNG metadata.
- **REQ-173**: MUST extract merge-gamma EXIF evidence by opening the original RAW/DNG file as a binary stream via `exifread.process_file` and MUST normalize `EXIF ColorSpace`, `Interop InteroperabilityIndex`, and `Image Model` tags for deterministic auto transfer resolution.
- **REQ-157**: MUST derive source gamma diagnostics from original RAW/DNG EXIF color-profile metadata via `exifread` and MAY supplement with `rawpy` metadata without altering neutral RAW extraction or normalized-gain camera white-balance application.
- **REQ-163**: MUST classify source gamma diagnostics by preferring DNG EXIF `ColorSpace` and `InteroperabilityIndex` fields, mapping `ColorSpace=1` to sRGB, `ColorSpace=2` or `R03` interop to Adobe RGB, and MUST report `unknown` when EXIF evidence is insufficient.
- **REQ-164**: MUST print source gamma diagnostics as one deterministic runtime line containing both a source-gamma label and either a numeric gamma value or `undetermined`.
- **REQ-021**: MUST enforce `--jpg-compression` in inclusive range `0..100`.
- **REQ-022**: MUST reject luminance-specific options when `--hdr-merge` is not `Luminace-HDR`.
- **REQ-023**: MUST reject unknown `--hdr-merge` values and accept only `Luminace-HDR`, `OpenCV-Merge`, `OpenCV-Tonemap`, or `HDR-Plus`.
- **REQ-024**: MUST route backend execution from resolved `--hdr-merge` mode and MUST preserve the existing processing behavior of `Luminace-HDR`, `OpenCV-Merge`, `OpenCV-Tonemap`, and `HDR-Plus`.
- **REQ-025**: MUST reject unsupported `--auto-adjust` values, accept only `enable` or `disable`, and default omitted `--auto-adjust` to `enable`.
- **REQ-026**: MUST resolve DNG bit depth from `raw_image_visible.dtype.itemsize * 8` with fallback to `white_level.bit_length()`.
- **REQ-027**: MUST enforce minimum supported bit depth as `9` bits per color.
- **REQ-030**: MUST accept finite numeric `--bracketing` values `>=0` and finite numeric `--exposure` values without enforcing `0.25` EV step granularity or bit-depth-derived upper bounds.
- **REQ-031**: MUST derive exposure-planning inputs from one shared neutral-linear HDR base image after applying float-domain `rawpy` camera white-balance gains normalized by the resolved RAW white-balance normalization mode.
- **REQ-203**: MUST parse optional `--white-balance=<GREEN|MAX|MIN|MEAN>`, defaulting to `MEAN`, and MUST reject unknown values.
- **REQ-204**: MUST implement `GREEN` normalization by dividing all RAW WB coefficients by the green coefficient so the normalized green gain equals `1.0`.
- **REQ-205**: MUST implement `MAX` normalization by dividing all RAW WB coefficients by the maximum coefficient so the maximum normalized gain equals `1.0`.
- **REQ-206**: MUST implement `MIN` normalization by dividing all RAW WB coefficients by the minimum coefficient so the minimum normalized gain equals `1.0`.
- **REQ-207**: MUST implement `MEAN` normalization by dividing all RAW WB coefficients by their arithmetic mean so the normalized mean gain equals `1.0`.
- **REQ-208**: MUST print one RAW WB normalization diagnostic before exposure planning containing rawpy-extracted RGB coefficients, selected normalization mode (`GREEN|MAX|MIN|MEAN`), and normalized RGB gains used for white-balance application.
- **REQ-209**: MUST format every numeric coefficient in RAW WB normalization diagnostics as fixed-point float with exactly four fractional digits.
- **REQ-032**: MUST evaluate `ev_best`, `ev_ettr`, and `ev_detail` on the normalized linear gamma=`1` RGB image after optional auto-brightness and auto-white-balance only when `--exposure=auto` is active, and MUST select `ev_zero` as `min(ev_best, ev_ettr, ev_detail)` preserving candidate signs.
- **REQ-166**: MUST expose `--auto-ev-step` as a positive configurable EV increment for iterative bracket expansion, defaulting to `0.1`.
- **REQ-167**: MUST derive `ev_delta` by iterating from `auto_ev_step`, evaluating unclipped `ev_zero±ev_delta` images, and stopping at first threshold breach or deterministic iteration safety bound when `--bracketing=auto` and backend is not `OpenCV-Tonemap`.
- **REQ-216**: MUST resolve `ev_delta=0.1` and skip clipping-threshold bracket iteration when `--bracketing=auto` and `--hdr-merge=OpenCV-Tonemap`.
- **REQ-217**: MUST print `Bracket step: skipped` and `Exposure planning selected bracket half-span: 0.100000 EV` when `--bracketing=auto` and `--hdr-merge=OpenCV-Tonemap`.
- **REQ-218**: MUST print iterative bracket-step clipping metrics and final `ev_delta` only when `--bracketing=auto` and backend is not `OpenCV-Tonemap`.
- **REQ-168**: MUST measure highlight clipping as the percentage of pixels in the plus image with any channel `>=1` and shadow clipping as the percentage of pixels in the minus image with any channel `<=0` using finite-safe bracket tensors.
- **REQ-033**: MUST parse and preserve `--tmo*` passthrough option payloads for luminance command forwarding.
- **REQ-034**: MUST order luminance backend bracket inputs as `ev_minus`, `ev_zero`, `ev_plus`.
- **REQ-035**: MUST execute `luminance-hdr-cli` from output TIFF parent directory to isolate sidecar artifacts in temporary workspace.
- **REQ-037**: MUST fail enabled auto-adjust stage and enabled automatic exposure solving when `cv2` or `numpy` dependencies are unavailable.
- **REQ-038**: MUST fail EXIF-preserving encode path when source EXIF payload exists and `piexif` is unavailable.
- **REQ-039**: MUST extract source EXIF timestamp with priority `DateTimeOriginal` then `DateTimeDigitized` then `DateTime`.
- **REQ-040**: MUST preserve source EXIF orientation in output `0th` IFD and MUST set thumbnail orientation to `1` after orienting thumbnail pixels to match the saved JPEG display orientation.
- **REQ-041**: MUST regenerate EXIF thumbnail from the exact final quantized RGB uint8 buffer saved as the output JPEG when source EXIF payload exists.
- **REQ-042**: MUST normalize integer-like EXIF values before `piexif.dump` and drop out-of-range integers for constrained integer tag types.
- **REQ-043**: MUST gate release build-and-publish job on `check-branch` output `is_master == "true"`.
- **REQ-044**: MUST trigger release workflow on `workflow_dispatch` and push tags matching `v[0-9]+.[0-9]+.[0-9]+`.
- **REQ-045**: MUST build release distributions using `uv run --frozen --with build python -m build`.
- **REQ-046**: MUST attest release artifacts with `actions/attest-build-provenance@v1` using `subject-path: dist/*`.
- **REQ-047**: MUST publish release assets from `dist/**/*` using `softprops/action-gh-release@v2` with `fail_on_unmatched_files: true`.
- **REQ-048**: MUST include project script entrypoints `dng2jpg` and `d2j` mapped to `dng2jpg.core:main`.
- **REQ-049**: SHOULD provide both `dng2jpg` and `d2j` as equivalent user-invokable CLI aliases.
- **REQ-050**: MUST implement `/tmp/auto-brightness.py` auto-brightness on normalized RGB float `[0,1]` in linear gamma `1.0`: compute BT.709 luminance, tonemap luminance, rescale RGB, optionally desaturate overflow, and return linear gamma `1.0` output without sRGB encode/decode using finite-safe luminance statistics.
- **REQ-051**: MUST support exactly one auto-adjust pipeline with one validated knob model containing shared controls and CLAHE-luma controls.
- **REQ-052**: MUST print deterministic runtime diagnostics for EV triplet and OpenCV radiance exposure calculations/results; MUST print `Exposure Misure EV` values and selected `ev_zero` only when `--exposure=auto` is active.
- **REQ-220**: After `_parse_run_options` returns non-`None` and CTN-004 file-path preconditions pass, MUST invoke `_print_validated_run_parameters` before any dependency resolution or image processing step.
- **REQ-221**: `_print_validated_run_parameters` MUST emit one resolved parameter per line with two-space indentation under unlabeled group headers in fixed order: `Input/Output`, `Exposure`, `White Balance`, `HDR Backend`, `Merge Gamma`, `Postprocess`, `Auto-Brightness (AB)`, `Auto-White-Balance (AWB)`, `Auto-Levels`, `Auto-Adjust`, `Debug`, and MUST print `auto-brightness`, `auto-white-balance`, `auto-levels`, and `auto-adjust` status lines in their groups.
- **REQ-103**: MUST classify normalized BT.709 luminance as `low-key` when `median<0.35 && p95<0.85`, `high-key` when `median>0.65 && p05>0.15`, else `normal-key`.
- **REQ-104**: MUST map luminance with `L=(a/Lw_bar)*Y`, percentile-derived robust `Lwhite`, and burn-out compression `Ld=(L*(1+L/Lwhite^2))/(1+L)` before linear-domain chromaticity-preserving RGB scaling.
- **REQ-105**: MUST desaturate only overflowing linear RGB pixels by blending toward `(Ld,Ld,Ld)` with the minimal factor that restores `max(R,G,B)<=1` while preserving luminance.
- **REQ-100**: MUST execute auto-levels after static postprocess when `--auto-levels` resolves to `enable`, preserving RGB float input/output buffers and float internal calculations across histogram analysis and tonal transformation with finite-safe histogram and tone-curve metrics.
- **REQ-101**: MUST parse `--auto-levels <enable|disable>`, `--al-clip-pct`, `--al-clip-out-of-gamut`, `--al-highlight-reconstruction`, `--al-highlight-reconstruction-method`, and `--al-gain-threshold`, default omitted `--auto-levels` to `enable`, and require resolved auto-levels state `enable` before any `--al-*` option.
- **REQ-102**: MUST accept highlight reconstruction methods `Luminance Recovery`, `CIELab Blending`, `Blend`, `Color Propagation`, and `Inpaint Opposed`.
- **REQ-116**: MUST default auto-levels knobs to `clip_pct=0.02`, `clip_out_of_gamut=true`, `highlight_reconstruction=disabled`, `highlight_reconstruction_method=Inpaint Opposed`, and `gain_threshold=1.0`.
- **REQ-117**: MUST derive auto-levels calibration from a RawTherapee-compatible luminance histogram using `sum`, `average`, `median`, octiles, `ospread`, `rawmax`, clipped white point, and clipped black point.
- **REQ-118**: MUST derive `expcomp`, `black`, `brightness`, `contrast`, `hlcompr`, and `hlcomprthresh` using RawTherapee `ImProcFunctions::getAutoExp` formula families, including gamma-domain whiteclip correction and normalized float-domain metric emission.
- **REQ-119**: MUST apply a RawTherapee-equivalent float-domain tonal transformation that consumes `expcomp`, `black`, `brightness`, `contrast`, `hlcompr`, and `hlcomprthresh`, including per-channel overflow handling, exposure scaling, highlight curve, brightness curve, contrast curve, inverse-gamma output mapping, and default shadow compression `0`.
- **REQ-120**: MUST execute optional highlight reconstruction after the auto-levels tonal transformation, using `--al-highlight-reconstruction` as the explicit enable toggle, mapping `Color Propagation` to RawTherapee `Color` and `Inpaint Opposed` to RawTherapee `Coloropp`.
- **REQ-165**: MUST apply `Clip out-of-gamut colors` after the complete auto-levels tonal transformation and optional highlight reconstruction using the RawTherapee `filmlike_clip` hue-stable clipping family instead of isotropic ratio-preserving normalization.
- **REQ-121**: MUST compute `log_avg_lum`, `median_lum`, `p05`, `p95`, `shadow_clip_in<=1/255`, and `highlight_clip_in>=254/255` from normalized luminance before key-value selection.
- **REQ-122**: MUST auto-select base Reinhard `a` as `0.09`, `0.18`, or `0.36`, boost when `p95<0.60 && median<0.35`, attenuate when `p05>0.40 && median>0.65`, then clamp to `[a_min,a_max]`.
- **REQ-123**: MUST execute auto-adjust stages in this exact order on RGB float buffers: selective blur, adaptive level, CLAHE-luma, sigmoidal contrast, HSL vibrance, and high-pass overlay, with finite-safe sample handling before stage-local statistics.
- **REQ-124**: MUST expose auto-brightness CLI knobs for `key_value`, `white_point_percentile`, `a_min`, `a_max`, `max_auto_boost_factor`, and `eps`.
- **REQ-125**: MUST expose `--aa-enable-local-contrast`, `--aa-local-contrast-strength`, `--aa-clahe-clip-limit`, and `--aa-clahe-tile-grid-size` as auto-adjust CLAHE-luma controls.
- **REQ-135**: MUST expose `--ab-enable-luminance-preserving-desat` as the auto-brightness desaturation toggle.
- **REQ-136**: MUST implement CLAHE-luma directly on RGB float `[0,1]` by adjusting luminance only, reconstructing RGB with preserved chroma, and blending with the original image via configurable strength.
- **REQ-137**: MUST keep auto-adjust CLAHE-luma functionally equivalent to the former auto-brightness CLAHE-luma stage except for differences attributable only to removed float-uint16 quantization.
- **REQ-107**: MUST accept `--hdr-merge OpenCV-Merge` as HDR backend selector and execute OpenCV backend behavior when selected.
- **REQ-108**: MUST execute OpenCV backend from three in-memory RGB float brackets ordered as `ev_minus`, `ev_zero`, `ev_plus` using selectable algorithm `Debevec`, `Robertson`, or `Mertens`, defaulting to `Debevec`, and MUST pass brackets without entry re-normalization or clipping.
- **REQ-109**: MUST derive OpenCV Debevec/Robertson exposure times in seconds from source EXIF `ExposureTime`, preserve bracket order, and map the sequence to extracted `(ev_zero-ev_delta, ev_zero, ev_zero+ev_delta)`.
- **REQ-110**: MUST preserve RGB float input/output interfaces for OpenCV merge and MUST keep the full OpenCV HDR path in RGB float `[0,1]` without backend-local `uint8` or `uint16` conversions.
- **REQ-141**: MUST expose OpenCV controls `--opencv-merge-algorithm`, `--opencv-merge-tonemap`, and `--opencv-merge-tonemap-gamma`, defaulting to `Debevec`, `enable`, and algorithm-specific gamma `Debevec=1.0`, `Robertson=0.9`, `Mertens=0.8`.
- **REQ-142**: MUST treat EXIF `ExposureTime` as the linear RAW exposure time of the extracted base image and MUST compute OpenCV radiance times as `t_raw*2^(ev_zero-ev_delta)`, `t_raw*2^ev_zero`, and `t_raw*2^(ev_zero+ev_delta)`.
- **REQ-143**: MUST execute optional OpenCV simple gamma tone mapping for `Debevec`, `Robertson`, and `Mertens` outputs before downstream postprocess, default enabled with algorithm-specific gamma `1.0`, `0.9`, and `0.8`, and MUST skip contrast-enhancing tone operators.
- **REQ-144**: MUST deliver one congruent normalized RGB float output contract across OpenCV `Debevec`, `Robertson`, and `Mertens`, preserving exposure semantics without backend-specific contrast compensation.
- **REQ-152**: MUST feed Debevec and Robertson OpenCV input brackets directly from the linear HDR bracket contract without any gamma-inversion preprocessing step.
- **REQ-153**: MUST estimate inverse camera response with OpenCV `CalibrateDebevec` or `CalibrateRobertson` before OpenCV `MergeDebevec` or `MergeRobertson` and MUST pass both `times` and calibrated `response` into the merge call.
- **REQ-161**: MUST extract EXIF `ExposureTime` from the source DNG metadata and reject OpenCV `Debevec` or `Robertson` execution when that value is missing, non-positive, or not coercible to seconds.
- **REQ-162**: MUST keep OpenCV Debevec and Robertson processing on RGB float `[0,1]` interfaces while allowing backend-local response estimation inputs/outputs required by OpenCV calibrators.
- **REQ-154**: MUST execute OpenCV `MergeMertens` on RGB float `[0,1]` brackets with one identical resolved merge-gamma transfer pre-applied to all three inputs, then rescale fusion output and apply optional OpenCV tonemap before final normalization.
- **REQ-145**: MUST resolve downstream defaults as `HDR-Plus=(0.9,0.9,1.2,1.0)`, `Luminace-HDR mantiuk08=(0.9,0.8,1.2,1.05)`, `Luminace-HDR reinhard02=(0.9,1.3,0.9,0.7)`, `OpenCV-Merge Debevec=(1.0,1.2,1.5,1.0)`, `OpenCV-Merge Mertens=(1.0,0.9,1.4,1.1)`, `OpenCV-Merge Robertson=(1.0,1.4,1.4,1.0)`, `OpenCV-Tonemap drago=(1.0,1.0,1.4,0.6)`, `OpenCV-Tonemap mantiuk=(0.9,1.2,1.4,0.5)`, and `OpenCV-Tonemap reinhard=(1.0,1.0,1.0,1.0)`.
- **REQ-155**: MUST group conversion help sections in pipeline execution order and colocate each step selector with the option set that configures that step.
- **REQ-156**: MUST document every accepted conversion CLI option in help output, including accepted values, implicit activation conditions, and effective default value when omitted.
- **REQ-111**: MUST accept `--hdr-merge HDR-Plus` as HDR backend selector and execute HDR+ backend behavior when selected.
- **REQ-112**: MUST execute HDR+ backend in source step order `scalar proxy -> hierarchical alignment -> box_down2 -> temporal merge -> spatial merge`, with internal frame order `(ev_zero, ev_minus, ev_plus)` and `ev_zero` at index `0`.
- **REQ-113**: MUST compute three-level HDR+ alignment on the scalar proxy with `box_down2`, two `gauss_down4` levels, per-tile L1 minimization over offsets `[-4,+3]`, and final full-resolution offset lift by `2`.
- **REQ-114**: MUST compute HDR+ temporal alternate-frame weights from aligned 16x16 downsampled tiles with user-facing `factor`, `min_dist`, and `max_dist`, hard cutoff, and reference-inclusive normalization.
- **REQ-115**: MUST execute HDR+ spatial blending over aligned half-overlapped 32x32 tiles using raised-cosine weights and return one normalized RGB float32 image without `uint8` or `uint16` quantization.
- **REQ-126**: MUST adapt RGB float bracket images to one deterministic normalized float32 scalar proxy on `[0,1]` with default mode `rggb`.
- **REQ-127**: MUST expose HDR+ CLI knobs `--hdrplus-proxy-mode`, `--hdrplus-search-radius`, `--hdrplus-temporal-factor`, `--hdrplus-temporal-min-dist`, and `--hdrplus-temporal-max-dist`.
- **REQ-128**: MUST default HDR+ CLI knobs to `proxy_mode=rggb`, `search_radius=4`, `temporal_factor=8`, `temporal_min_dist=10`, and `temporal_max_dist=300`.
- **REQ-129**: MUST execute HDR+ scalar-proxy, alignment, temporal, and spatial radiometric arithmetic on normalized float32 arrays in domain `[0,1]` without additional stage-local radiometric renormalization.
- **REQ-130**: MUST reject HDR+ knob values when `search_radius<1`, `temporal_factor<=0`, `temporal_min_dist<0`, or `temporal_max_dist<=temporal_min_dist`.
- **REQ-131**: MUST print resolved HDR+ proxy, alignment, and temporal knob values in deterministic runtime diagnostics using user-facing CLI values, not normalized internal parameters.
- **REQ-138**: MUST internally remap HDR+ temporal weighting parameters for normalized float32 `[0,1]` distance inputs so numeric behavior remains equivalent to the historical 16-bit code-domain formulation.
- **REQ-139**: MUST keep HDR+ alignment offsets as `int32` and keep tile indices, stride, margins, bounds, and search geometry discrete integers.
- **REQ-140**: MUST NOT convert HDR+ RGB frames or HDR+ scalar proxy arrays to `uint16` at any point in the HDR+ backend.
- **REQ-132**: MUST bypass numeric static postprocess when `post_gamma=1.0`, `brightness=1.0`, `contrast=1.0`, and `saturation=1.0`, and otherwise execute only non-neutral static factors directly on RGB float tensors without quantized intermediates.
- **REQ-133**: MUST keep `_encode_jpg` scoped to final-save operations: one float-to-uint8 quantization, JPEG write, EXIF thumbnail refresh, and EXIF-timestamp synchronization.
- **REQ-134**: MUST preserve legacy numeric static equations in float domain, execute `gamma->brightness->contrast->saturation`, and MUST NOT apply stage-local `[0,1]` clipping in postprocess entry adaptation or static substage equations.
- **REQ-214**: MUST normalize postprocess entry payloads only when they originate from non-float image encodings; merge-backend outputs already expressed as RGB float32 MUST be forwarded without entry normalization, clamping, or clipping.
- **REQ-176**: MUST parse `--post-gamma=auto` as an alternative to numeric `--post-gamma=<value>` and replace only the static gamma substage, preserving downstream static `brightness->contrast->saturation` execution unchanged.
- **REQ-177**: MUST compute auto-gamma from grayscale mean luminance `L` using `gamma=log(target_gray)/log(L)` when `luma_min < L < luma_max` and all required statistics are finite, and MUST return input unchanged with resolved gamma `1.0` otherwise.
- **REQ-222**: MUST replace `NaN`, `+Inf`, and `-Inf` samples with `0.0` in float-ingress helpers `_to_float32_image_array` and `_ensure_three_channel_float_array_no_range_adjust` before numeric reductions.
- **REQ-223**: MUST fail auto `--bracketing` exposure planning with explicit processing diagnostics when finite-safe inputs are unavailable after sanitization.
- **REQ-224**: MUST build auto-gamma LUTs only from finite resolved gamma values and fallback to identity mapping with deterministic diagnostics when gamma is non-finite.
- **REQ-225**: MUST sanitize non-finite luminance samples before CLAHE, percentile, histogram-index, logarithmic, and exponential computations across auto-levels and auto-adjust pipelines.
- **REQ-178**: MUST apply auto-gamma by LUT-domain mapping in RGB float space using `output=input^gamma` with configurable LUT size, without stage-local clipping or quantized intermediates.
- **REQ-179**: MUST expose auto-gamma knobs `--post-gamma-auto-target-gray`, `--post-gamma-auto-luma-min`, `--post-gamma-auto-luma-max`, and `--post-gamma-auto-lut-size` with defaults `0.5`, `0.01`, `0.99`, and `256`.
- **REQ-180**: MUST reject `--post-gamma-auto-*` options unless `--post-gamma=auto` is selected.
- **REQ-146**: MUST accept `--debug` as a flag that enables persistent TIFF checkpoint emission for executed pipeline stages without changing the final JPG destination.
- **REQ-147**: MUST write each debug TIFF from normalized RGB float `[0,1]` data using filename `<input-dng-stem><stage-suffix>.tiff` in the resolved output JPG directory.
- **REQ-148**: MUST emit one debug checkpoint TIFF for each executed pipeline stage output in strict stage order, including bracket extraction, HDR merge final output, explicit pre/post merge-gamma outputs, and every enabled downstream stage output.
- **REQ-149**: MUST preserve debug TIFF files after command completion while keeping temporary workspace cleanup behavior unchanged for non-debug intermediates.
- **REQ-181**: MUST parse optional `--auto-white-balance=<Simple|GrayworldWB|IA|ColorConstancy|TTL|disable>`, defaulting stage to disabled when omitted, keeping it disabled for `disable`, and rejecting unknown values.
- **REQ-199**: MUST derive white-balance analysis exclusively from the current stage input image and MUST NOT use bracket tensors or `ev_zero` as analysis sources.
- **REQ-182**: MUST execute auto-white-balance only when `--auto-white-balance` resolves to enabled mode, after auto-brightness and before `_calculate_auto_zero_evaluations`; omitted option MUST print `Auto-white-balance stage: disabled` and bypass the stage.
- **REQ-183**: MUST estimate one auto-white-balance gain vector from a transient analysis image built from the stage input after applying shared auto-brightness preprocessing.
- **REQ-200**: MUST apply auto-white-balance gains to the original stage input image and output one corrected RGB float image to downstream auto-zero evaluation, bracket generation, and static/manual postprocess stages.
- **REQ-213**: MUST keep auto-brightness preprocessing used for white-point estimation internal to estimation and MUST NOT output that preprocessed image as stage output.
- **REQ-184**: MUST implement `--auto-white-balance=Simple` via OpenCV xphoto `createSimpleWB` on a real analysis image using full resolution or anti-aliased pyramid downsampling with `INTER_AREA`, without fixed-size synthetic proxy payloads.
- **REQ-185**: MUST implement `--auto-white-balance=GrayworldWB` via OpenCV xphoto `createGrayworldWB` on a real analysis image using full resolution or anti-aliased pyramid downsampling with `INTER_AREA`, without fixed-size synthetic proxy payloads.
- **REQ-186**: MUST implement `--auto-white-balance=IA` via OpenCV xphoto `createLearningBasedWB` on real analysis images using full resolution or anti-aliased pyramid downsampling with `INTER_AREA`.
- **REQ-201**: MUST confine xphoto quantization to backend-local estimation boundaries, preserve float-domain triplet processing and gain application, and replace hard clipping with robust-rescale plus monotonic soft-knee compression for estimation payloads.
- **REQ-187**: MUST implement `--auto-white-balance=ColorConstancy` in linear domain (`gamma=1`) using percentile-based robust masks that exclude near-black and near-saturated analysis pixels before channel and luminance mean computation.
- **REQ-188**: MUST implement `--auto-white-balance=TTL` in linear domain (`gamma=1`) using percentile-based robust masks that exclude near-black and near-saturated analysis pixels before `avg_gray/avg_channel` gain computation.
- **REQ-210**: MUST parse optional `--white-balance-xphoto-domain=<linear|srgb|source-auto>`, default to `linear`, preserve `source-auto` as metadata-compatibility selector, and reject unknown values.
- **REQ-211**: MUST probe xphoto uint16 capability per algorithm, keep IA bit-depth-coherent `range_max` and histogram bins, use uint16 for GrayworldWB when probe-supported, and keep Simple on uint8 unless probe-verified uint16 compatibility succeeds.
- **REQ-212**: MUST apply `--white-balance-xphoto-domain` only to xphoto gain estimation; `linear` MUST use linear analysis data, `srgb` MUST use sRGB-encoded analysis data, and `source-auto` MUST resolve from source gamma diagnostics.
- **REQ-189**: MUST accept `--hdr-merge=OpenCV-Tonemap` as HDR backend selector and execute OpenCV-Tonemap backend behavior when selected or by default.
- **REQ-190**: MUST accept zero or one `--opencv-tonemap-algorithm=<drago|reinhard|mantiuk>` selector when `--hdr-merge=OpenCV-Tonemap` is selected and MUST default omitted selector to `reinhard`.
- **REQ-191**: MUST reject `--opencv-tonemap-algorithm` and any `--opencv-tonemap-<algorithm>-*` knob unless `--hdr-merge=OpenCV-Tonemap` is selected.
- **REQ-192**: MUST execute OpenCV-Tonemap only on `ev_zero`; extraction stage MUST skip `ev_minus` and `ev_plus`, set both images to `None`, and log both skip events.
- **REQ-219**: MUST print `Extracting bracket ev_minus: skipped` and `Extracting bracket ev_plus: skipped` when `--hdr-merge=OpenCV-Tonemap`.
- **REQ-193**: MUST invoke OpenCV `createTonemapDrago`, `createTonemapReinhard`, or `createTonemapMantiuk` with `gamma_inv=1/resolved_merge_gamma` derived from merge-gamma curve resolution and keep the selected algorithm as the only active implementation.
- **REQ-194**: MUST expose OpenCV-Tonemap Drago knobs `--opencv-tonemap-drago-saturation` and `--opencv-tonemap-drago-bias`, defaulting to `1.0` and `0.85`.
- **REQ-195**: MUST expose OpenCV-Tonemap Reinhard knobs `--opencv-tonemap-reinhard-intensity`, `--opencv-tonemap-reinhard-light_adapt`, and `--opencv-tonemap-reinhard-color_adapt`, defaulting to `0.0`, `0.0`, and `0.0`.
- **REQ-196**: MUST expose OpenCV-Tonemap Mantiuk knobs `--opencv-tonemap-mantiuk-scale` and `--opencv-tonemap-mantiuk-saturation`, defaulting to `0.7` and `1.0`.
- **REQ-197**: MUST apply resolved merge gamma as the final backend-local step of OpenCV-Tonemap after tone mapping, analogously to OpenCV Debevec or Robertson, and MUST NOT pre-apply merge gamma before tone mapping.
- **REQ-198**: MUST preserve OpenCV-Tonemap float dynamic range without stage-local clipping at input, during tone mapping, during merge-gamma application, and at backend output.

## 4. Test Requirements

- **TST-001**: MUST verify `_parse_run_options` defaults to automatic `ev_delta` and automatic `ev_zero` when both `--bracketing` and `--exposure` are absent; accepts `--bracketing=auto`, finite numeric `--bracketing`, `--exposure=auto`, and finite numeric `--exposure`; parses and rejects unknown `--hdr-merge` values.
- **TST-002**: MUST verify `run` returns `1` for unsupported runtime OS and for missing `luminance-hdr-cli` dependency with deterministic diagnostics naming each missing executable.
- **TST-003**: MUST verify successful `run` execution returns `0`, writes output JPG, and emits success message `HDR JPG created: <output>`.
- **TST-004**: MUST verify `ev_zero` auto-selection chooses `min(ev_best, ev_ettr, ev_detail)` preserving candidate signs when `--exposure=auto` is active.
- **TST-005**: MUST verify static exposure resolution preserves manual `--bracketing` and `--exposure` values, defaults `ev_delta` and `ev_zero` to automatic solving when absent, rejects negative or non-finite `--bracketing`, and does not enforce `0.25` EV increments or bit-depth-derived upper bounds.
- **TST-006**: MUST verify `_run_luminance_hdr_cli` builds deterministic argument order and includes any `--tmo*` passthrough pairs unchanged.
- **TST-007**: MUST verify `_extract_dng_exif_payload_and_timestamp` applies datetime priority `36867` then `36868` then `306` and extracts EXIF `ExposureTime` as positive seconds.
- **TST-008**: MUST verify `_refresh_output_jpg_exif_thumbnail_after_save` preserves source orientation fields, rebuilds EXIF thumbnail bytes from the exact final quantized RGB uint8 save buffer, and emits display-oriented thumbnail pixels with thumbnail orientation `1`.
- **TST-009**: MUST verify release workflow gates `build-release` execution on `needs.check-branch.outputs.is_master == "true"`.
- **TST-010**: MUST verify `_parse_run_options` defaults `--auto-levels` to `enable`, enforces `--auto-levels <enable|disable>` with `--al-*` coupling, and validates `Clip out-of-gamut colors`, `Clip %`, highlight-reconstruction toggle, method, and gain-threshold knobs.
- **TST-011**: MUST verify `_apply_auto_brightness_rgb_float` preserves float I/O and executes the original step order, key-analysis thresholds, Reinhard mapping, and optional desaturation.
- **TST-012**: MUST verify `_encode_jpg` applies one float-to-uint8 conversion immediately before JPEG save after dedicated `_postprocess` stage completion.
- **TST-013**: MUST verify `_parse_run_options` accepts `--hdr-merge OpenCV-Merge`, defaults `--hdr-merge` to `OpenCV-Tonemap`, and rejects values outside `Luminace-HDR`, `OpenCV-Merge`, `OpenCV-Tonemap`, and `HDR-Plus`.
- **TST-014**: MUST verify OpenCV radiance exposure derivation preserves bracket order, uses EXIF exposure seconds, maps the sequence to `(ev_zero-ev_delta, ev_zero, ev_zero+ev_delta)`, and remains deterministic for variable bracket spans.
- **TST-015**: MUST verify OpenCV merge outputs for `Debevec`, `Robertson`, and `Mertens` remain normalized RGB float images bounded to `[0,1]` after float-only backend execution.
- **TST-047**: MUST verify `_parse_run_options` rejects removed `--auto-ev`, `--auto-ev-shadow-target`, `--auto-ev-highlight-target`, and `--auto-ev-pct`, and accepts `--auto-ev-shadow-clipping`, `--auto-ev-highlight-clipping`, and `--auto-ev-step` with deterministic defaults and validation.
- **TST-048**: MUST verify iterative bracket expansion for non-OpenCV-Tonemap backends stops at first threshold breach or deterministic safety bound and always terminates.
- **TST-049**: MUST verify runtime diagnostics print iterative clipping percentages and final `ev_delta` only for non-OpenCV-Tonemap backends when `--bracketing=auto`.
- **TST-082**: MUST verify `_resolve_auto_ev_delta` handles `NaN`-contaminated base images without non-terminating loops.
- **TST-083**: MUST verify `_resolve_auto_ev_delta` raises deterministic processing errors when sanitized base images do not contain finite samples.
- **TST-016**: MUST verify auto-levels parser defaults `clip_pct=0.02`, `clip_out_of_gamut=true`, `highlight_reconstruction=false`, `highlight_reconstruction_method=Inpaint Opposed`, and `gain_threshold=1.0`.
- **TST-017**: MUST verify auto-levels histogram calibration reproduces RawTherapee-compatible `expcomp`, `black`, `brightness`, `contrast`, `hlcompr`, and `hlcomprthresh` for deterministic synthetic histograms with finite-safe luminance indexing.
- **TST-018**: MUST verify auto-levels tonal transformation consumes the RawTherapee-compatible metric set in normalized float space, preserves float-only internal math, and rejects or sanitizes non-finite tone-curve inputs deterministically.
- **TST-046**: MUST verify `Clip out-of-gamut colors` executes the RawTherapee `filmlike_clip` hue-stable clipping family instead of isotropic ratio-preserving normalization.
- **TST-045**: MUST verify `Color Propagation` and `Inpaint Opposed` selectors execute only when `--al-highlight-reconstruction` resolves to enabled and preserve deterministic RGB float outputs.
- **TST-019**: MUST verify auto-brightness CLI parsing defaults omitted `--auto-brightness` to `disable` and exposes key-value, white-point, boost, epsilon, and desaturation controls with deterministic defaults and validation.
- **TST-020**: MUST verify auto-brightness clipping proxies use normalized thresholds `1/255` and `254/255` and key auto-selection uses the original base values and boost rules.
- **TST-021**: MUST verify `_parse_run_options` accepts HDR+ knob overrides and rejects invalid HDR+ knob combinations with deterministic parse errors.
- **TST-022**: MUST verify HDR+ scalar proxy mode `rggb` produces deterministic green-weighted scalar conversion from RGB float input.
- **TST-023**: MUST verify HDR+ hierarchical alignment resolves non-zero alternate-frame tile offsets for translated inputs and keeps reference offsets at zero.
- **TST-024**: MUST verify HDR+ temporal weighting applies resolved alignment offsets and internally normalized temporal parameters before distance evaluation and RGB accumulation.
- **TST-025**: MUST verify HDR+ merge preserves normalized float32 arithmetic and float input/output boundaries without any HDR+ `uint16` conversion path.
- **TST-026**: MUST verify `_apply_static_postprocess_float` preserves float I/O and does not call uint16 adaptation helpers or legacy uint16 static-stage helpers.
- **TST-027**: MUST verify `_apply_static_postprocess_float` bypasses when all static factors are neutral and otherwise executes only non-neutral substages in strict `gamma->brightness->contrast->saturation` order.
- **TST-028**: MUST verify auto-adjust CLI parsing accepts `enable|disable`, defaults to `enable`, and exposes CLAHE-luma enable, strength, clip-limit, and tile-grid controls with deterministic defaults and validation.
- **TST-029**: MUST verify `_apply_validated_auto_adjust_pipeline` preserves float I/O, executes `blur -> level -> CLAHE-luma -> sigmoid -> vibrance -> high-pass`, and sanitizes non-finite intermediates deterministically.
- **TST-030**: MUST verify float-domain auto-adjust CLAHE-luma preserves blend semantics and remains within quantization-only deviation from the former uint16 implementation on deterministic finite fixtures.
- **TST-084**: MUST verify CLAHE luminance processing receives finite-safe luminance tensors when input contains `NaN` or `Inf`.
- **TST-085**: MUST verify HSL vibrance and sigmoidal contrast processing returns finite outputs for inputs containing non-finite channel samples.
- **TST-031**: MUST verify `_resolve_default_postprocess` returns the exact per-variant tuples required by REQ-145 for `HDR-Plus`, `Luminace-HDR` (`mantiuk08`,`reinhard02`), `OpenCV-Merge` (`Debevec`,`Mertens`,`Robertson`), and `OpenCV-Tonemap` (`drago`,`mantiuk`,`reinhard`).
- **TST-041**: MUST verify `print_help` renders conversion help in pipeline execution order, colocates per-stage configuration options with the described stage, and keeps canonical `dng2jpg` usage formatting.
- **TST-042**: MUST verify `print_help` documents every accepted conversion CLI option with allowed values or activation conditions and prints effective defaults for omitted options.
- **TST-032**: MUST verify `_parse_run_options` accepts `--opencv-merge-algorithm`, `--opencv-merge-tonemap`, and `--opencv-merge-tonemap-gamma`, applies defaults, and rejects invalid OpenCV HDR values.
- **TST-033**: MUST verify OpenCV backend dispatch selects `MergeDebevec`, `MergeRobertson`, or `MergeMertens` and runs `CalibrateDebevec` or `CalibrateRobertson` before Debevec/Robertson merge dispatch.
- **TST-034**: MUST verify optional OpenCV tone mapping defaults to enabled with algorithm-specific gamma `Debevec=1.0`, `Robertson=0.9`, `Mertens=0.8` and can be disabled for all algorithms without changing pre-tonemap merge outputs.
- **TST-035**: MUST verify OpenCV radiance exposure derivation uses EXIF exposure seconds with non-zero extracted `ev_zero` and propagates calibrated response into Debevec/Robertson merge calls.
- **TST-036**: MUST verify OpenCV backend preserves RGB float input/output boundaries and avoids backend-local `uint8` or `uint16` conversions.
- **TST-037**: MUST verify `_parse_run_options` accepts `--debug` and enables persistent debug checkpoint configuration without changing existing positional or backend parsing.
- **TST-038**: MUST verify debug checkpoint writers emit progressive TIFF filenames for every executed stage output, including HDR merge output plus pre-merge-gamma and post-merge-gamma outputs, in the output directory.
- **TST-039**: MUST verify Debevec and Robertson OpenCV inputs are consumed directly from the linear HDR bracket contract without gamma-inversion preprocessing.
- **TST-043**: MUST verify `_extract_bracket_images_float` executes exactly one neutral RAW postprocess call, normalizes base RGB using `(white_level - mean(black_level_per_channel))`, applies normalized camera white-balance gains without explicit clipping, and derives clipped EV brackets.
- **TST-044**: MUST verify CLI help documents `--gamma`, parser defaults to `--gamma=auto`, parser accepts `--gamma=<a,b>`, parser rejects invalid gamma payloads, and HDR bracket extraction remains linear.
- **TST-050**: MUST verify `--gamma=auto` resolves transfer selection from EXIF color-space evidence with deterministic fallback ordering.
- **TST-051**: MUST verify OpenCV backend applies resolved merge gamma as the final backend-local float step without extra clipping around the gamma transfer.
- **TST-052**: MUST verify HDR+ backend applies resolved merge gamma as the final backend-local float step without extra clipping around the gamma transfer.
- **TST-053**: MUST verify runtime diagnostics print deterministic merge-gamma request and resolved-transfer lines.
- **TST-054**: MUST verify automatic merge-gamma diagnostics print normalized EXIF `ColorSpace`, `InteroperabilityIndex`, and `ImageModel` inputs used during resolution.
- **TST-055**: MUST verify `_parse_run_options` accepts `--post-gamma=auto`, applies auto-gamma defaults, and parses `--post-gamma-auto-*` overrides.
- **TST-056**: MUST verify `_parse_run_options` rejects `--post-gamma-auto-*` options when `--post-gamma=auto` is not selected.
- **TST-057**: MUST verify `_apply_static_postprocess_float` executes `auto-gamma->brightness->contrast->saturation` when `--post-gamma=auto`, preserving numeric static behavior for `brightness->contrast->saturation`.
- **TST-058**: MUST verify auto-gamma luminance anchoring computes `gamma=log(target_gray)/log(mean_luminance)` only for finite luminance statistics and returns unchanged image when statistics are outside guard bounds.
- **TST-059**: MUST verify auto-gamma LUT-domain mapping runs in float space without quantized intermediates, without stage-local clipping, and with identity fallback when resolved gamma is non-finite.
- **TST-086**: MUST verify auto-brightness returns finite outputs for luminance inputs containing `NaN` and `Inf`.
- **TST-087**: MUST verify `_to_float32_image_array` replaces non-finite grayscale, RGB, and alpha-channel samples with `0.0` while preserving shape semantics.
- **TST-088**: MUST verify `_ensure_three_channel_float_array_no_range_adjust` replaces non-finite samples with `0.0` for grayscale, RGB, and RGBA inputs while preserving channel adaptation behavior.
- **TST-089**: MUST verify `_build_autoexp_histogram_rgb_float` rejects or sanitizes non-finite luminance samples before histogram-index casting.
- **TST-040**: MUST verify float-only OpenCV Mertens output applies OpenCV-equivalent `255x` exposure-fusion scaling before final `[0,1]` normalization.
- **TST-060**: MUST verify `_parse_run_options` defaults auto-white-balance to disabled, defaults xphoto domain to `linear`, defaults RAW white-balance normalization mode to `MEAN`, and accepts all supported auto-white-balance selectors.
- **TST-061**: MUST verify `_parse_run_options` rejects missing or unsupported `--auto-white-balance` and `--white-balance-xphoto-domain` values with deterministic diagnostics.
- **TST-062**: MUST verify `run` prints `Auto-white-balance stage: disabled`, skips auto-white-balance when `--auto-white-balance` is omitted, executes auto-brightness after `_extract_base_rgb_linear_float` and before `_calculate_auto_zero_evaluations`, and keeps static-postprocess brightness manual-only.
- **TST-063**: MUST verify `_apply_auto_white_balance_stage_float` applies one identical gain vector to one stage input image using transient estimation-only preprocessing.
- **TST-064**: MUST verify `Simple` white-balance path invokes OpenCV xphoto `createSimpleWB` and uses real-image analysis payloads without fixed `(1,9,3)` proxy assumptions.
- **TST-065**: MUST verify `GrayworldWB` white-balance path invokes OpenCV xphoto `createGrayworldWB` and uses real-image analysis payloads without fixed `(1,9,3)` proxy assumptions.
- **TST-066**: MUST verify xphoto uint16 capability policy: IA configures bit-depth-coherent `range_max`/histogram settings, GrayworldWB uses uint16 when probe-supported, and Simple falls back to uint8 when probe support is not confirmed.
- **TST-067**: MUST verify `ColorConstancy` white-balance path applies percentile-based robust masks in linear domain before luminance/channel mean computation and does not call xphoto quantization helpers.
- **TST-068**: MUST verify `TTL` white-balance path applies percentile-based robust masks in linear domain before `avg_gray/avg_channel` gain computation and does not call xphoto quantization helpers.
- **TST-075**: MUST verify auto-white-balance estimation uses transient auto-brightness preprocessing and does not leak that preprocessed brightness-adjusted image into stage output.
- **TST-076**: MUST verify xphoto gain extraction accepts real-image analysis payloads with non-fixed shape, remains deterministic with anti-aliased pyramid downsampling, and applies soft-knee highlight compression that reduces hard-clip saturation.
- **TST-077**: MUST verify xphoto estimation-domain selector applies only to estimation (`linear|srgb|source-auto`) and `source-auto` metadata resolution does not alter stage-working float output contracts.
- **TST-069**: MUST verify `_parse_run_options` accepts `--hdr-merge=OpenCV-Tonemap`, defaults omitted `--opencv-tonemap-algorithm` to `reinhard`, accepts one explicit selector, and rejects unknown selector values.
- **TST-070**: MUST verify `_parse_run_options` rejects `--opencv-tonemap-algorithm` and `--opencv-tonemap-<algorithm>-*` options unless `--hdr-merge=OpenCV-Tonemap` is selected and rejects algorithm-specific knob misuse outside the selected map.
- **TST-071**: MUST verify OpenCV-Tonemap backend consumes only `ev_zero`, sets `ev_minus` and `ev_plus` to `None`, and prints both extraction skip diagnostics.
- **TST-072**: MUST verify OpenCV-Tonemap backend dispatches Drago, Reinhard, and Mantiuk implementations with `gamma_inv=1/resolved_merge_gamma` and algorithm-specific optional knobs.
- **TST-073**: MUST verify OpenCV-Tonemap backend applies resolved merge gamma only after selected tone mapping execution.
- **TST-074**: MUST verify OpenCV-Tonemap backend does not clip float values at backend input, tone-map output, merge-gamma output, or backend return boundary.
- **TST-078**: MUST verify `_postprocess` forwards merge-backend float outputs without entry clipping and normalizes only external non-float payloads before stage execution.
- **TST-079**: MUST verify `--bracketing=auto` with `--hdr-merge=OpenCV-Tonemap` sets `ev_delta=0.1`, prints `Bracket step: skipped`, and prints `Exposure planning selected bracket half-span: 0.100000 EV`.
- **TST-080**: MUST verify `_print_validated_run_parameters` emits all group headers in the defined order with two-space-indented parameter lines for a standard resolved option set.
- **TST-081**: MUST verify `_print_validated_run_parameters` always emits `Auto-Brightness (AB)`, `Auto-White-Balance (AWB)`, `Auto-Levels`, and `Auto-Adjust` headers in fixed order and always prints their `auto-*` stage status as `enable` or `disabled`.

## 5. Evidence Matrix

| Requirement ID | Evidence |
|---|---|
| PRJ-001 | `src/dng2jpg/dng2jpg.py::run`, `_build_exposure_multipliers`, and `_extract_bracket_images_float`; excerpt: derives `ev_minus`, `ev_zero`, `ev_plus` multipliers, extracts three normalized RGB float brackets with `output_bps=16`, then merges via selected backend. |
| PRJ-002 | `src/dng2jpg/dng2jpg.py::print_help`, `_parse_run_options`; excerpt: documents and parses exposure, EV-center, backend, postprocess, auto-adjust, and auto-brightness controls. |
| PRJ-003 | `src/dng2jpg/core.py::main`; excerpt: handles `--help`, `--ver`, `--version`, `--upgrade`, `--uninstall`, and conversion dispatch. |
| PRJ-004 | `.github/workflows/release-uvx.yml`; excerpt: semantic tag trigger, build job, attestation, and GitHub release upload flow. |
| PRJ-005 | `scripts/d2j.sh`; excerpt: `exec "${UV_TOOL}" run --project "${BASE_DIR}" python -m dng2jpg "$@"`. |
| CTN-001 | `src/dng2jpg/dng2jpg.py::_is_supported_runtime_os`; excerpt: returns true only on Linux and prints Linux-only error otherwise. |
| CTN-002 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: parses `--hdr-merge` from the remaining backend set and defaults to `OpenCV-Tonemap` when omitted. |
| CTN-003 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: resolves `ev_delta` from `--bracketing` (absent→automatic iterative algorithm, numeric→static, auto→auto algorithm). |
| CTN-007 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: resolves `ev_zero` from `--exposure` (absent→signed numeric minimum of `ev_best`, `ev_ettr`, `ev_detail`, numeric→static, auto→signed numeric minimum of `ev_best`, `ev_ettr`, `ev_detail`). |
| CTN-004 | `src/dng2jpg/dng2jpg.py::run`; excerpt: validates `.dng` suffix, input existence, and output parent directory existence. |
| CTN-005 | `src/dng2jpg/dng2jpg.py::_collect_missing_external_executables`, `run`; excerpt: explicit preflight for selected external commands and deterministic missing-dependency diagnostics. |
| CTN-006 | `scripts/d2j.sh`; excerpt: compares `${PROJECT_ROOT}` and `${BASE_DIR}` and exits `1` on mismatch. |
| DES-001 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: deterministic token scan loop over args with explicit branch handling. |
| DES-002 | `src/dng2jpg/dng2jpg.py` dataclasses; evidence: `AutoAdjustOptions`, `AutoBrightnessOptions`, `PostprocessOptions`, `LuminanceOptions`, `AutoEvInputs`. |
| DES-003 | `src/dng2jpg/dng2jpg.py::_parse_ev_option`, `_parse_ev_center_option`; excerpt: finite-number static EV parsing without quantization or bit-depth upper-bound contracts. |
| DES-004 | `src/dng2jpg/dng2jpg.py::run`, `_run_luminance_hdr_cli`; excerpt: isolates intermediate artifacts under the command temporary workspace and backend-local subdirectories. |
| DES-005 | `src/dng2jpg/dng2jpg.py::_extract_dng_exif_payload_and_timestamp`, `_refresh_output_jpg_exif_thumbnail_after_save`, `_build_oriented_thumbnail_jpeg_bytes`, `_encode_jpg`, `_sync_output_file_timestamps_from_exif`. |
| DES-006 | `src/dng2jpg/dng2jpg.py::_resolve_default_postprocess`, `_parse_run_options`; excerpt: default tuple resolution depends on backend mode plus luminance/OpenCV-merge/OpenCV-tonemap selectors. |
| DES-008 | `src/dng2jpg/dng2jpg.py::_resolve_default_postprocess`; excerpt: deterministic static-default mapping covers HDR-Plus, Luminace-HDR operators, OpenCV-Merge algorithms, and OpenCV-Tonemap algorithms. |
| DES-007 | `docs/WORKFLOW.md`; excerpt: execution-unit model shows process-based flows and "no explicit threads detected". |
| REQ-001 | `src/dng2jpg/core.py::main`; excerpt: no args -> `ported.print_help(__version__)` and `return 0`. |
| REQ-002 | `src/dng2jpg/core.py::main`; excerpt: `--help` prints management help and conversion help. |
| REQ-003 | `src/dng2jpg/core.py::main`; excerpt: `--ver` and `--version` print version and return `0`. |
| REQ-004 | `src/dng2jpg/core.py::_run_management`, `main`; excerpt: executes `uv tool install ...` and `uv tool uninstall` on Linux. |
| REQ-005 | `src/dng2jpg/core.py::_run_management`; excerpt: non-Linux path prints manual command and returns `0`. |
| REQ-006 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: explicit errors for unknown option and missing values. |
| REQ-007 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: rejects `--aa-*` when auto-adjust resolves to `disable` and rejects `--ab-*` when auto-brightness resolves to `disable`. |
| REQ-008 | `src/dng2jpg/dng2jpg.py::_resolve_joint_auto_ev_solution`, `_resolve_auto_ev_delta`, `run`; excerpt: computes `ev_best`, `ev_ettr`, `ev_detail` only when `--exposure=auto` or `--bracketing=auto` is active. |
| REQ-009 | `src/dng2jpg/dng2jpg.py::_resolve_auto_ev_delta`, `_resolve_joint_auto_ev_solution`, `run`; excerpt: symmetric triplet `(ev_zero-ev_delta, ev_zero, ev_zero+ev_delta)` with iterative `ev_delta` only when `--bracketing=auto`. |
| REQ-010 | `src/dng2jpg/dng2jpg.py::_extract_base_rgb_linear_float`, `_extract_bracket_images_float`; excerpt: executes one neutral linear `rawpy.postprocess(...)` call with explicit no-auto and no-camera-WB parameters before bracket derivation. |
| REQ-011 | `src/dng2jpg/dng2jpg.py::_run_luminance_hdr_cli`, `_format_external_command_for_log`; excerpt: deterministic luminance args including `--ldrTiff 32b`, emitted full command syntax with parameters, and backend-local float32 TIFF artifact handling. |
| REQ-174 | `src/dng2jpg/dng2jpg.py::_materialize_bracket_tiffs_from_float`, `_write_rgb_float_tiff32`; excerpt: serializes DNG2JPG RGB float `[0,1]` brackets as TIFF float32 files. |
| REQ-175 | `src/dng2jpg/dng2jpg.py::_run_luminance_hdr_cli`; excerpt: imports `luminance-hdr-cli` output TIFF float32 and normalizes to RGB float `[0,1]`. |
| REQ-012 | `src/dng2jpg/dng2jpg.py::_extract_base_rgb_linear_float`, `_extract_bracket_images_float`, `_run_opencv_merge_backend`, `_run_opencv_tonemap_backend`, `_run_hdr_plus_merge`, `_postprocess`, `_encode_jpg`; excerpt: exchanges RGB float tensors across extraction, merge, postprocess, and final-save preparation boundaries. |
| REQ-013 | `src/dng2jpg/dng2jpg.py::_postprocess`, `_apply_static_postprocess_float`; excerpt: executes optional auto-brightness before static order `gamma->brightness->contrast->saturation`, then optional auto-levels. |
| REQ-014 | `src/dng2jpg/dng2jpg.py::_encode_jpg`, `_sync_output_file_timestamps_from_exif`; excerpt: writes refreshed EXIF metadata before applying `os.utime` from EXIF timestamp. |
| REQ-015 | `src/dng2jpg/dng2jpg.py::run`; excerpt: parse/dependency/processing failures return `1`, success returns `0`. |
| REQ-016 | `src/dng2jpg/core.py::_check_online_version`, `_write_version_cache`; excerpt: GitHub latest-release check uses idle-time cache JSON and prints status or error output. |
| REQ-150 | `src/dng2jpg/core.py::_check_online_version`; excerpt: success path uses `3600` seconds and error paths use `86400` seconds when calculating idle-delay. |
| REQ-151 | `src/dng2jpg/core.py::_check_online_version`, `_write_version_cache`; excerpt: cache JSON is rewritten after every latest-release API attempt on both success and error outcomes. |
| REQ-017 | `src/dng2jpg/dng2jpg.py`; excerpt: `PROGRAM = "dng2jpg"` and help usage renders canonical command label without duplicated command token. |
| REQ-019 | `src/dng2jpg/dng2jpg.py::_parse_percentage_option`; excerpt: enforces inclusive `0..100` bounds for `--auto-ev-shadow-clipping` and `--auto-ev-highlight-clipping`. |
| REQ-020 | `src/dng2jpg/dng2jpg.py::_parse_gamma_option`, `_parse_run_options`, `print_help`; excerpt: restores `--gamma`, defaults omitted gamma to `auto`, and accepts custom `<linear_coeff,exponent>` payloads. |
| REQ-021 | `src/dng2jpg/dng2jpg.py::_parse_jpg_compression_option`; excerpt: enforces inclusive `0..100`. |
| REQ-022 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: rejects luminance options unless `--hdr-merge Luminace-HDR` is selected. |
| REQ-023 | `src/dng2jpg/dng2jpg.py::_parse_hdr_merge_option`, `_parse_run_options`; excerpt: validates `--hdr-merge` against the remaining allowed modes. |
| REQ-024 | `src/dng2jpg/dng2jpg.py::run`; excerpt: routes backend execution from resolved `--hdr-merge` mode. |
| REQ-025 | `src/dng2jpg/dng2jpg.py::_parse_auto_adjust_option`, `_parse_run_options`; excerpt: validates `enable|disable` values and defaults omitted auto-adjust to `enable`. |
| REQ-026 | `src/dng2jpg/dng2jpg.py::_detect_dng_bits_per_color`; excerpt: container bit depth primary path with white-level fallback. |
| REQ-027 | `src/dng2jpg/dng2jpg.py::_validate_supported_bits_per_color`; excerpt: raises on bit depth below `MIN_SUPPORTED_BITS_PER_COLOR=9`. |
| REQ-030 | `src/dng2jpg/dng2jpg.py::_parse_ev_option`, `_parse_ev_center_option`; excerpt: finite static EV parsing enforces non-negative `--bracketing` only and omits bit-depth-derived upper-bound checks. |
| REQ-031 | `src/dng2jpg/dng2jpg.py::_extract_base_rgb_linear_float`; excerpt: applies camera white-balance gains normalized relative to the green coefficient from `rawpy.camera_whitebalance` to the shared neutral base image before exposure planning. |
| REQ-032 | `src/dng2jpg/dng2jpg.py::_calculate_auto_zero_evaluations`, `_select_ev_zero_candidate`, `run`; excerpt: evaluates candidates and selects `ev_zero` as signed numeric minimum among `ev_best`, `ev_ettr`, and `ev_detail` when `--exposure=auto` is active. |
| REQ-033 | `src/dng2jpg/dng2jpg.py::_parse_tmo_passthrough_value`, `_run_luminance_hdr_cli`; excerpt: parses and forwards `--tmo*` args unchanged. |
| REQ-034 | `src/dng2jpg/dng2jpg.py::_order_bracket_paths`; excerpt: deterministic `ev_minus`, `ev_zero`, `ev_plus` order. |
| REQ-035 | `src/dng2jpg/dng2jpg.py::_run_luminance_hdr_cli`; excerpt: changes cwd to output parent before subprocess execution. |
| REQ-037 | `src/dng2jpg/dng2jpg.py::_resolve_auto_adjust_dependencies`; excerpt: explicit failure when enabled auto-adjust dependencies `cv2`/`numpy` are unavailable. |
| REQ-038 | `src/dng2jpg/dng2jpg.py::run`, `_load_piexif_dependency`; excerpt: fails when source EXIF exists and piexif is missing. |
| REQ-039 | `src/dng2jpg/dng2jpg.py::_extract_dng_exif_payload_and_timestamp`; excerpt: datetime tag precedence `36867` > `36868` > `306`. |
| REQ-040 | `src/dng2jpg/dng2jpg.py::_refresh_output_jpg_exif_thumbnail_after_save`; excerpt: source orientation in `0th`, thumbnail orientation `1` in `1st`. |
| REQ-041 | `src/dng2jpg/dng2jpg.py::_build_oriented_thumbnail_jpeg_bytes`, `_encode_jpg`; excerpt: regenerates thumbnail from the final quantized RGB uint8 image that is saved as the output JPG. |
| REQ-042 | `src/dng2jpg/dng2jpg.py::_normalize_ifd_integer_like_values_for_piexif_dump`; excerpt: normalize/drop unsupported integer-like values. |
| REQ-043 | `.github/workflows/release-uvx.yml`; excerpt: `if: needs.check-branch.outputs.is_master == 'true'`. |
| REQ-044 | `.github/workflows/release-uvx.yml`; excerpt: triggers on `workflow_dispatch` and semantic tag pattern. |
| REQ-045 | `.github/workflows/release-uvx.yml`; excerpt: `uv run --frozen --with build python -m build`. |
| REQ-046 | `.github/workflows/release-uvx.yml`; excerpt: `actions/attest-build-provenance@v1` with `subject-path: dist/*`. |
| REQ-047 | `.github/workflows/release-uvx.yml`; excerpt: `softprops/action-gh-release@v2` uploads `dist/**/*` with unmatched-file failure enabled. |
| REQ-048 | `pyproject.toml`; excerpt: `[project.scripts] dng2jpg = "dng2jpg.core:main"` and `d2j = "dng2jpg.core:main"`. |
| REQ-049 | `pyproject.toml`; excerpt: both `dng2jpg` and `d2j` map to identical entrypoint. |
| REQ-050 | `src/dng2jpg/dng2jpg.py::_apply_auto_brightness_rgb_float`; excerpt: executes linear-domain auto-brightness on normalized RGB float I/O and preserves gamma `1.0` output without sRGB re-encoding. |
| REQ-051 | `src/dng2jpg/dng2jpg.py::AutoAdjustOptions`, `_apply_validated_auto_adjust_pipeline`; excerpt: supports one float-domain auto-adjust implementation with one validated knob container including CLAHE-luma controls. |
| REQ-052 | `src/dng2jpg/dng2jpg.py::run`; excerpt: deterministic `print_info` diagnostic lines for exposure mode, automatic anchors, selected joint solution, EV triplet, and OpenCV radiance timing calculations/results. |
| REQ-103 | `src/dng2jpg/dng2jpg.py::_analyze_luminance_key`; excerpt: classifies `low-key`/`normal-key`/`high-key` with the original median and percentile thresholds. |
| REQ-104 | `src/dng2jpg/dng2jpg.py::_reinhard_global_tonemap_luminance`, `_apply_auto_brightness_rgb_float`; excerpt: percentile robust `Lwhite` and burn-out compression before RGB scaling. |
| REQ-105 | `src/dng2jpg/dng2jpg.py::_luminance_preserving_desaturate_to_fit`; excerpt: overflow-only luminance-preserving grayscale blending with minimal factor selection. |
| REQ-100 | `src/dng2jpg/dng2jpg.py::_postprocess`, `_apply_auto_levels_float`, `_apply_static_postprocess_float`, `_apply_auto_brightness_rgb_float`; excerpt: executes auto-levels only when resolved state is `enable`, after static postprocess. |
| REQ-101 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `_parse_auto_levels_options`; excerpt: parses `--auto-levels <enable|disable>` and validates `--al-*` coupling. |
| REQ-102 | `src/dng2jpg/dng2jpg.py::_parse_auto_levels_hr_method_option`, `_apply_auto_levels_float`; excerpt: validates and executes the full RawTherapee-aligned highlight reconstruction method set. |
| REQ-116 | `src/dng2jpg/dng2jpg.py::AutoLevelsOptions`, `_parse_auto_levels_options`; excerpt: sets parser defaults for clip percentage, gamut clipping, highlight method, and gain threshold. |
| REQ-117 | `src/dng2jpg/dng2jpg.py::_build_autoexp_histogram_rgb_uint16`, `_compute_auto_levels_from_histogram`; excerpt: derives RawTherapee-compatible histogram statistics and clipping points. |
| REQ-118 | `src/dng2jpg/dng2jpg.py::_compute_auto_levels_from_histogram`; excerpt: implements RawTherapee-compatible formulas for `expcomp`, `black`, `brightness`, `contrast`, and highlight-compression outputs. |
| REQ-119 | `src/dng2jpg/dng2jpg.py::_apply_auto_levels_tonal_transform_float`, `_build_auto_levels_tone_curve_state`, `_build_rt_nurbs_curve_lut`; excerpt: ports RawTherapee `complexCurve` semantics into float-domain per-channel overflow-aware highlight, shadow, brightness, contrast, and inverse-gamma tone processing. |
| REQ-120 | `src/dng2jpg/dng2jpg.py::_parse_auto_levels_options`, `_apply_auto_levels_float`; excerpt: requires explicit `--al-highlight-reconstruction` enablement before dispatching RawTherapee-aligned highlight reconstruction methods. |
| REQ-121 | `src/dng2jpg/dng2jpg.py::_analyze_luminance_key`; excerpt: computes `log_avg_lum`, `median_lum`, `p05`, `p95`, `shadow_clip_in`, and `highlight_clip_in` using normalized `1/255` and `254/255` thresholds. |
| REQ-122 | `src/dng2jpg/dng2jpg.py::_choose_auto_key_value`; excerpt: selects `0.09/0.18/0.36`, applies under/over hints, and clamps to `[a_min,a_max]`. |
| REQ-123 | `src/dng2jpg/dng2jpg.py::_apply_validated_auto_adjust_pipeline`; excerpt: executes auto-adjust in the exact order `blur -> level -> CLAHE-luma -> sigmoid -> vibrance -> high-pass`. |
| REQ-124 | `src/dng2jpg/dng2jpg.py::AutoBrightnessOptions`, `_parse_auto_brightness_options`, `print_help`; excerpt: exposes `key_value`, `white_point_percentile`, `a_min`, `a_max`, `max_auto_boost_factor`, and `eps` as CLI-configurable controls. |
| REQ-125 | `src/dng2jpg/dng2jpg.py::AutoAdjustOptions`, `_parse_auto_adjust_options`, `print_help`; excerpt: exposes CLAHE-luma enable, blend strength, clip limit, and tile grid size as auto-adjust CLI controls. |
| REQ-135 | `src/dng2jpg/dng2jpg.py::AutoBrightnessOptions`, `_parse_auto_brightness_options`, `print_help`; excerpt: exposes auto-brightness luminance-preserving desaturation toggle without local-contrast controls. |
| REQ-136 | `src/dng2jpg/dng2jpg.py::_apply_clahe_luma_rgb_float`; excerpt: applies CLAHE on float-domain luminance, reconstructs RGB with preserved chroma, and blends with original via configured strength. |
| REQ-137 | `src/dng2jpg/dng2jpg.py::_apply_clahe_luma_rgb_float`; excerpt: keeps auto-adjust CLAHE-luma behavior aligned with the former uint16-based local-contrast stage except for quantization removal. |
| REQ-107 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `print_help`; excerpt: parses `--hdr-merge OpenCV-Merge` and defaults to `OpenCV-Tonemap` when omitted. |
| REQ-108 | `src/dng2jpg/dng2jpg.py::OpenCvMergeOptions`, `_parse_opencv_merge_algorithm_option`, `_parse_opencv_merge_backend_options`, `_run_opencv_merge_backend`, `_run_opencv_merge_radiance`, `_run_opencv_merge_mertens`; excerpt: selects OpenCV `Debevec`, `Robertson`, or `Mertens` and dispatches the matching merge path. |
| REQ-109 | `src/dng2jpg/dng2jpg.py::_build_opencv_radiance_exposure_times`; excerpt: derives deterministic OpenCV radiance exposure times in seconds from EXIF `ExposureTime` and extracted EV triplet. |
| REQ-110 | `src/dng2jpg/dng2jpg.py::_run_opencv_merge_backend`, `_to_uint8_image_array`; excerpt: preserves RGB float input/output while confining OpenCV-local quantization to backend merge adaptation boundaries. |
| REQ-111 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `print_help`, `run`; excerpt: accepts `--hdr-merge HDR-Plus`, documents backend, and routes execution to HDR+ merge path. |
| REQ-112 | `src/dng2jpg/dng2jpg.py::_order_hdr_plus_reference_paths`, `_hdrplus_build_scalar_proxy_float32`, `_hdrplus_align_layers`, `_hdrplus_box_down2_float32`, `_hdrplus_compute_temporal_weights`, `_hdrplus_merge_temporal_rgb`, `_hdrplus_merge_spatial_rgb`, `_run_hdr_plus_merge`; excerpt: executes source order `scalar proxy -> hierarchical alignment -> box_down2 -> temporal merge -> spatial merge` with internal frame order `(ev_zero, ev_minus, ev_plus)` and `ev_zero` reference index `0`. |
| REQ-113 | `src/dng2jpg/dng2jpg.py::_hdrplus_align_layer`, `_hdrplus_align_layers`; excerpt: applies three-level hierarchical tile alignment with `box_down2`, two `gauss_down4` levels, search offsets `[-4,+3]`, and final full-resolution offset lift. |
| REQ-114 | `src/dng2jpg/dng2jpg.py::_hdrplus_resolve_temporal_runtime_options`, `_hdrplus_compute_temporal_weights`, `_hdrplus_merge_temporal_rgb`; excerpt: applies aligned 16x16 tile L1 weights with user-facing temporal knobs, remapped runtime controls, hard cutoff, and reference-inclusive normalization. |
| REQ-115 | `src/dng2jpg/dng2jpg.py::_hdrplus_merge_spatial_rgb`, `_run_hdr_plus_merge`; excerpt: blends aligned half-overlapped 32x32 tiles with raised-cosine weights and returns normalized RGB float32 output without `uint8` or `uint16` quantization. |
| REQ-126 | `src/dng2jpg/dng2jpg.py::HdrPlusOptions`, `_parse_hdrplus_options`, `_hdrplus_build_scalar_proxy_float32`; excerpt: adapts normalized RGB float brackets into deterministic normalized scalar proxy with default `rggb` mode. |
| REQ-127 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `print_help`, `HdrPlusOptions`; excerpt: exposes HDR+ CLI knobs for proxy, search radius, and temporal weighting. |
| REQ-128 | `src/dng2jpg/dng2jpg.py::HdrPlusOptions`; excerpt: stores source-matching default values for HDR+ proxy, alignment, and temporal weights. |
| REQ-129 | `src/dng2jpg/dng2jpg.py::_run_hdr_plus_merge`, `_hdrplus_build_scalar_proxy_float32`, `_hdrplus_align_layers`, `_hdrplus_compute_temporal_weights`, `_hdrplus_merge_temporal_rgb`, `_hdrplus_merge_spatial_rgb`; excerpt: preserves normalized float32 HDR+ radiometric arithmetic without stage-local renormalization. |
| REQ-130 | `src/dng2jpg/dng2jpg.py::_parse_hdrplus_options`, `_parse_run_options`; excerpt: rejects invalid HDR+ knob ranges and inconsistent temporal thresholds. |
| REQ-131 | `src/dng2jpg/dng2jpg.py::HdrPlusOptions`, `_hdrplus_resolve_temporal_runtime_options`, `run`; excerpt: preserves user-facing HDR+ temporal diagnostics while runtime remapping stays internal. |
| REQ-138 | `src/dng2jpg/dng2jpg.py::HdrPlusOptions`, `HdrPlusTemporalRuntimeOptions`, `_hdrplus_resolve_temporal_runtime_options`, `_hdrplus_compute_temporal_weights`; excerpt: remaps temporal weighting controls for normalized `[0,1]` distances while preserving historical 16-bit code-domain behavior. |
| REQ-139 | `src/dng2jpg/dng2jpg.py::_hdrplus_compute_tile_start_positions`, `_hdrplus_trunc_divide_int32`, `_hdrplus_align_layers`; excerpt: keeps alignment offsets, tile geometry, and search-domain indexing in integer form. |
| REQ-140 | `src/dng2jpg/dng2jpg.py::_hdrplus_build_scalar_proxy_float32`, `_hdrplus_merge_temporal_rgb`, `_hdrplus_merge_spatial_rgb`, `_run_hdr_plus_merge`; excerpt: keeps HDR+ RGB frames and scalar proxy on float32 path with no `uint16` adaptation. |
| REQ-141 | `src/dng2jpg/dng2jpg.py::OpenCvMergeOptions`, `_parse_opencv_merge_backend_options`, `_resolve_default_opencv_tonemap_gamma`, `_parse_run_options`, `print_help`; excerpt: exposes OpenCV algorithm, tone-map enable, and algorithm-specific tone-map gamma defaults. |
| REQ-142 | `src/dng2jpg/dng2jpg.py::_build_opencv_radiance_exposure_times`, `run`; excerpt: treats EXIF `ExposureTime` as linear RAW exposure and computes radiance times as `t_raw*2^(ev_zero±ev_delta)` around extracted `ev_zero`. |
| REQ-165 | `src/dng2jpg/dng2jpg.py::_clip_auto_levels_out_of_gamut_float`, `_apply_auto_levels_float`; excerpt: normalizes overflowing RGB triplets after tonal transform and optional highlight reconstruction while preserving channel ratios. |
| REQ-143 | `src/dng2jpg/dng2jpg.py::_run_opencv_merge_radiance`, `_run_opencv_merge_mertens`, `_normalize_opencv_hdr_to_unit_range`, `_resolve_default_opencv_tonemap_gamma`; excerpt: applies optional simple gamma tone mapping for Debevec/Robertson/Mertens with algorithm-specific default gamma and avoids contrast-enhancing operators. |
| REQ-144 | `src/dng2jpg/dng2jpg.py::_normalize_opencv_hdr_to_unit_range`, `_run_opencv_merge_radiance`, `_run_opencv_merge_mertens`; excerpt: normalizes Debevec, Robertson, and Mertens outputs to one congruent RGB float `[0,1]` contract without backend-specific contrast compensation. |
| REQ-145 | `src/dng2jpg/dng2jpg.py::_resolve_default_postprocess`; excerpt: assigns algorithm-specific OpenCV downstream postprocess defaults for Debevec/Robertson/Mertens. |
| REQ-152 | `src/dng2jpg/dng2jpg.py::_run_opencv_merge_backend`; excerpt: routes Debevec and Robertson directly from the shared linear HDR bracket contract without gamma-inversion preprocessing. |
| REQ-157 | `src/dng2jpg/dng2jpg.py::_describe_source_gamma_info`, `_extract_source_gamma_info`, `run`; excerpt: derives source gamma diagnostics independently from neutral extraction and normalized camera white-balance application. |
| REQ-163 | `src/dng2jpg/dng2jpg.py::_extract_source_gamma_info`, `_classify_tone_curve_gamma`; excerpt: applies metadata-priority ordering and returns `unknown` when metadata evidence is insufficient. |
| REQ-164 | `src/dng2jpg/dng2jpg.py::_describe_source_gamma_info`, `run`; excerpt: prints deterministic source gamma label and numeric-or-undetermined value. |
| REQ-169 | `src/dng2jpg/dng2jpg.py::_extract_exif_gamma_tags`, `_resolve_auto_merge_gamma`, `run`; excerpt: derives auto merge transfer from EXIF color-space evidence via `exifread` binary stream processing with source-gamma fallback. |
| REQ-170 | `src/dng2jpg/dng2jpg.py::_apply_merge_gamma_float`, `_run_opencv_merge_backend`, `_run_hdr_plus_merge`; excerpt: applies merge gamma only as the last backend-local float step without post-gamma clipping. |
| REQ-171 | `src/dng2jpg/dng2jpg.py::_describe_resolved_merge_gamma`, `run`; excerpt: prints deterministic merge-gamma request and resolved-transfer diagnostics. |
| REQ-158 | `src/dng2jpg/dng2jpg.py::_extract_sensor_dynamic_range_max`, `_extract_base_rgb_linear_float`; excerpt: computes sensor dynamic range from white/black metadata, scales neutral RAW base by that range, then applies green-referenced camera white-balance gains before bracket arithmetic. |
| REQ-159 | `src/dng2jpg/dng2jpg.py::_build_exposure_multipliers`, `_build_bracket_images_from_linear_base_float`; excerpt: derives brackets exclusively by EV multipliers and `[0,1]` clipping of the normalized base tensor. |
| REQ-160 | `src/dng2jpg/dng2jpg.py::_build_bracket_images_from_linear_base_float`, `_extract_bracket_images_float`, `_run_opencv_merge_backend`, `_run_luminance_hdr_cli`, `_run_hdr_plus_merge`; excerpt: preserves ordered float triplet `(ev_minus, ev_zero, ev_plus)` as the shared downstream contract. |
| REQ-153 | `src/dng2jpg/dng2jpg.py::_estimate_opencv_camera_response`, `_run_opencv_merge_radiance`; excerpt: calibrates inverse camera response before Debevec/Robertson merge and passes both `times` and `response` into the merge call. |
| REQ-161 | `src/dng2jpg/dng2jpg.py::_parse_exif_exposure_time_to_seconds`, `_extract_dng_exif_payload_and_timestamp`, `_build_opencv_radiance_exposure_times`, `run`; excerpt: extracts EXIF `ExposureTime`, coerces it to positive seconds, and rejects radiance merge when invalid. |
| REQ-162 | `src/dng2jpg/dng2jpg.py::_estimate_opencv_camera_response`, `_run_opencv_merge_radiance`, `_run_opencv_merge_backend`; excerpt: preserves RGB float `[0,1]` interfaces while allowing OpenCV-local response estimation artifacts. |
| REQ-154 | `src/dng2jpg/dng2jpg.py::_run_opencv_merge_mertens`, `_run_opencv_merge_backend`; excerpt: keeps Mertens on RGB float `[0,1]` brackets and applies `255x` output rescaling plus optional OpenCV tonemap before final normalization. |
| REQ-132 | `src/dng2jpg/dng2jpg.py::_apply_static_postprocess_float`, `_apply_post_gamma_float`, `_apply_brightness_float`, `_apply_contrast_float`, `_apply_saturation_float`; excerpt: bypasses numeric static postprocess when all numeric static factors are neutral and otherwise executes only non-neutral static factors directly on RGB float tensors without quantized intermediates. |
| REQ-133 | `src/dng2jpg/dng2jpg.py::_encode_jpg`; excerpt: performs the only float-to-uint8 quantization immediately before Pillow JPEG save. |
| REQ-134 | `src/dng2jpg/dng2jpg.py::_postprocess`, `_apply_static_postprocess_float`, `_apply_post_gamma_float`, `_apply_brightness_float`, `_apply_contrast_float`, `_apply_saturation_float`; excerpt: preserves float-domain static equations, keeps substage order, and forbids stage-local clipping in postprocess entry adaptation and static substages. |
| REQ-214 | `src/dng2jpg/dng2jpg.py::_postprocess`; excerpt: normalizes postprocess entry payloads only for non-float encodings and forwards merge-backend RGB float32 outputs without entry normalization/clamping/clipping. |
| REQ-176 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `_apply_static_postprocess_float`; excerpt: parses `--post-gamma=auto` and replaces only the gamma substage while preserving downstream static brightness/contrast/saturation execution. |
| REQ-177 | `src/dng2jpg/dng2jpg.py::_apply_auto_post_gamma_float`; excerpt: computes grayscale mean-luminance anchored gamma and returns unchanged input with gamma `1.0` outside configured guard bounds. |
| REQ-178 | `src/dng2jpg/dng2jpg.py::_build_auto_post_gamma_lut_float`, `_apply_auto_post_gamma_float`; excerpt: applies float LUT-domain mapping `output=input^gamma` without quantized intermediates or stage-local clipping. |
| REQ-179 | `src/dng2jpg/dng2jpg.py::PostGammaAutoOptions`, `_parse_post_gamma_auto_options`, `_parse_run_options`, `print_help`; excerpt: exposes auto-gamma knobs and defaults. |
| REQ-180 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: rejects `--post-gamma-auto-*` options unless `--post-gamma=auto` is selected. |
| DES-009 | `src/dng2jpg/dng2jpg.py::DebugArtifactContext`, `_write_debug_rgb_float_tiff`; excerpt: serializes float checkpoints as persistent TIFF16 outputs outside the temporary workspace. |
| REQ-146 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `print_help`, `run`; excerpt: parses `--debug`, documents the flag, and enables persistent checkpoint orchestration. |
| REQ-147 | `src/dng2jpg/dng2jpg.py::_write_debug_rgb_float_tiff`, `run`; excerpt: writes `<input-dng-stem><stage-suffix>.tiff` into the output JPG directory from normalized RGB float payloads. |
| REQ-148 | `src/dng2jpg/dng2jpg.py::run`, `_write_hdr_merge_debug_checkpoints`, `_postprocess`, `_encode_jpg`; excerpt: emits one progressive checkpoint per executed stage output, including HDR merge final and explicit pre/post merge-gamma boundaries when available. |
| REQ-149 | `src/dng2jpg/dng2jpg.py::run`; excerpt: keeps debug TIFF outputs outside `TemporaryDirectory(...)` while still cleaning the temporary workspace after execution. |
| TST-001 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_ev_defaults_and_auto_selectors`; verifies default automatic `ev_delta`/`ev_zero`, `--bracketing=auto`, `--exposure=auto`, finite selectors, and `--hdr-merge` parsing. |
| TST-002 | `src/dng2jpg/dng2jpg.py::run`; branches for unsupported OS and dependency failures returning `1`. |
| TST-003 | `src/dng2jpg/dng2jpg.py::run`; success branch prints `HDR JPG created: ...` and returns `0`. |
| TST-004 | `tests/test_uint16_postprocess_pipeline.py::test_select_ev_zero_candidate_chooses_numeric_minimum`, `test_select_ev_zero_candidate_uses_unclamped_values`; verifies `ev_zero=min(ev_best, ev_ettr, ev_detail)` with preserved signs when `--exposure=auto`. |
| TST-005 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_static_ev_defaults`, `test_parse_run_options_static_ev_preserves_manual_ev_center`, `test_parse_run_options_rejects_negative_ev_bracketing`; verifies static defaults, manual `--exposure` preservation, and invalid rejection. |
| TST-006 | `src/dng2jpg/dng2jpg.py::_run_luminance_hdr_cli`; deterministic argv generation including passthrough. |
| TST-007 | `tests/test_uint16_postprocess_pipeline.py::test_extract_dng_exif_payload_and_timestamp_reads_datetime_priority_and_exposure_time`; verifies EXIF datetime priority and positive-second `ExposureTime` parsing. |
| TST-008 | `tests/test_uint16_postprocess_pipeline.py::test_encode_jpg_refreshes_exif_thumbnail_from_final_quantized_rgb_uint8`; verifies EXIF orientation fields and thumbnail bytes derive from final quantized RGB uint8 save image. |
| TST-009 | `.github/workflows/release-uvx.yml`; release job condition depends on `is_master` gate output. |
| TST-010 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; branch checks for `--auto-levels <enable|disable>` coupling and `--al-*` knob validations. |
| TST-011 | `tests/test_uint16_postprocess_pipeline.py::test_apply_auto_brightness_rgb_float_executes_original_stage_order`; verifies float-interface auto-brightness stage order and optional desaturation without CLAHE local contrast. |
| TST-012 | `tests/test_uint16_postprocess_pipeline.py::test_encode_jpg_quantizes_once_at_final_boundary`; verifies one final float-to-uint8 conversion at the JPEG boundary after dedicated `_postprocess` stage completion. |
| TST-013 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_hdr_merge_opencv_backend`, `test_parse_run_options_rejects_unknown_hdr_merge_backend`, `test_parse_run_options_defaults_hdr_merge_to_opencv_tonemap`; validates remaining hdr-merge selection, default, and invalid-value rejection. |
| TST-014 | `tests/test_uint16_postprocess_pipeline.py::test_build_ev_times_from_ev_zero_and_delta_matches_bracket_sequence`; verifies deterministic unit-base EV-time sequence generation delegated from the EXIF-based radiance timing helper. |
| TST-015 | `tests/test_uint16_postprocess_pipeline.py::test_normalize_debevec_hdr_to_unit_range_clamps_to_valid_interval`, `test_run_opencv_merge_backend_keeps_mertens_inputs_as_float32`, `test_run_opencv_merge_backend_dispatches_debevec_direct_float_path_with_tonemap`, `test_run_opencv_merge_backend_dispatches_robertson_direct_float_path`; verifies OpenCV merge outputs remain normalized RGB float images bounded to `[0,1]`. |
| TST-016 | `tests/test_uint16_postprocess_pipeline.py::test_parse_auto_levels_options_defaults_match_rawtherapee`; verifies parser default values for clip percentage, gamut clipping, method, and gain threshold. |
| TST-017 | `tests/test_uint16_postprocess_pipeline.py::test_compute_auto_levels_from_histogram_matches_rawtherapee_reference`; verifies RawTherapee-compatible auto-levels numeric outputs for deterministic histograms. |
| TST-018 | `tests/test_uint16_postprocess_pipeline.py::test_apply_auto_levels_tonal_transform_uses_metric_driven_float_curves`; verifies metric-driven float-domain auto-levels tone processing. |
| TST-019 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_remaining_auto_brightness_controls`; verifies auto-brightness parser coverage for surviving key-value, white-point, boost, epsilon, and desaturation controls. |
| TST-020 | `tests/test_uint16_postprocess_pipeline.py::test_analyze_luminance_key_uses_original_thresholds_and_auto_boost_rules`; verifies normalized clipping proxies and key auto-selection rules. |
| TST-021 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_hdrplus_controls`, `test_parse_run_options_rejects_invalid_hdrplus_controls`; verifies HDR+ CLI control parsing and validation. |
| TST-022 | `tests/test_uint16_postprocess_pipeline.py::test_hdrplus_proxy_rggb_matches_green_weighted_scalar`; verifies deterministic `rggb` scalar proxy conversion. |
| TST-023 | `tests/test_uint16_postprocess_pipeline.py::test_hdrplus_align_layers_detects_translated_alternate_frame`; verifies non-zero alternate-frame alignment and zero reference offsets. |
| TST-024 | `tests/test_uint16_postprocess_pipeline.py::test_hdrplus_temporal_merge_uses_alignment_offsets`, `test_hdrplus_temporal_runtime_options_preserve_code_domain_weights`; verifies resolved alignment offsets and normalized temporal runtime remap affect weighting and RGB accumulation. |
| TST-025 | `tests/test_uint16_postprocess_pipeline.py::test_run_hdr_plus_merge_preserves_float_internal_and_float_io`; verifies HDR+ normalized float32 internals and float image boundaries without `uint16` conversion. |
| TST-026 | `tests/test_uint16_postprocess_pipeline.py::test_apply_static_postprocess_float_does_not_call_uint16_conversion`; verifies static postprocess avoids uint16 adaptation helpers. |
| TST-027 | `tests/test_uint16_postprocess_pipeline.py::test_apply_static_postprocess_float_skips_stage_when_all_factors_are_neutral`, `test_apply_static_postprocess_float_executes_only_non_neutral_substages_in_order`; verifies neutral-factor bypass and strict ordered execution of non-neutral static substages. |
| TST-028 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_auto_adjust_clahe_controls`; verifies auto-adjust parser defaults, enable/disable handling, and CLAHE-luma controls. |
| TST-029 | `tests/test_uint16_postprocess_pipeline.py::test_apply_validated_auto_adjust_pipeline_executes_clahe_stage_order`; verifies float-interface auto-adjust stage order with inserted CLAHE-luma stage. |
| TST-030 | `tests/test_uint16_postprocess_pipeline.py::test_apply_clahe_luma_rgb_float_matches_uint16_reference_within_quantization_tolerance`; verifies float-domain CLAHE-luma stays within quantization-only deviation from the former uint16 implementation. |
| TST-031 | `tests/test_uint16_postprocess_pipeline.py::test_resolve_default_postprocess_opencv_uses_updated_static_defaults`, `test_resolve_default_postprocess_hdrplus_uses_updated_static_defaults`, `test_resolve_default_postprocess_luminance_uses_updated_tmo_defaults`, `test_resolve_default_postprocess_opencv_tonemap_uses_algorithm_defaults`; verifies exact REQ-145 tuples for every configured backend variant. |
| TST-032 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_opencv_controls_and_defaults`, `test_parse_run_options_rejects_invalid_opencv_controls`; verifies `--opencv-*` parsing, defaults, validation, and backend coupling. |
| TST-033 | `tests/test_uint16_postprocess_pipeline.py::test_run_opencv_merge_backend_dispatches_debevec_uint8_radiance_path_with_tonemap`, `test_run_opencv_merge_backend_dispatches_robertson_uint8_radiance_path`, `test_run_opencv_merge_backend_applies_tonemap_for_mertens_when_enabled`; verifies OpenCV algorithm dispatch across Debevec, Robertson, and Mertens with calibrate-before-merge behavior for radiance modes. |
| TST-034 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_opencv_controls_and_defaults`, `test_run_opencv_merge_backend_dispatches_debevec_uint8_radiance_path_with_tonemap`, `test_run_opencv_merge_backend_applies_tonemap_for_mertens_when_enabled`, `test_run_opencv_merge_backend_skips_tonemap_for_mertens_when_disabled`; verifies algorithm-specific tone-map defaults, enabled paths, and explicit disable paths across OpenCV algorithms. |
| TST-035 | `tests/test_uint16_postprocess_pipeline.py::test_run_opencv_merge_backend_dispatches_debevec_direct_float_path_with_tonemap`, `test_run_opencv_merge_backend_dispatches_robertson_direct_float_path`, `test_run_opencv_merge_backend_requires_exif_exposure_time_for_radiance_modes`; verifies EXIF-second radiance timing, calibrated response propagation, and invalid-exposure rejection. |
| TST-045 | `tests/test_uint16_postprocess_pipeline.py::test_apply_auto_levels_color_methods_require_explicit_enable`; verifies highlight reconstruction methods execute only when explicitly enabled. |
| TST-036 | `tests/test_uint16_postprocess_pipeline.py::test_run_opencv_merge_backend_keeps_mertens_inputs_as_float32`, `test_run_opencv_merge_backend_dispatches_debevec_direct_float_path_with_tonemap`, `test_run_opencv_merge_backend_dispatches_robertson_direct_float_path`; verifies OpenCV backend preserves RGB float input/output boundaries and avoids backend-local `uint8` or `uint16` conversions. |
| TST-037 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_enables_debug_flag`; verifies `--debug` parsing preserves existing positional and backend parsing. |
| TST-038 | `tests/test_uint16_postprocess_pipeline.py::test_write_hdr_merge_debug_checkpoints_writes_merge_gamma_boundaries`, `test_write_hdr_merge_debug_checkpoints_writes_final_only_without_boundaries`, `test_run_debug_writes_extraction_and_merge_checkpoints`, `test_encode_jpg_writes_debug_checkpoints_with_progressive_suffixes`; verifies progressive checkpoint filenames for extraction, HDR merge final, explicit pre/post merge-gamma boundaries, and downstream executed stages. |
| TST-039 | `tests/test_uint16_postprocess_pipeline.py::test_run_opencv_merge_backend_dispatches_debevec_uint8_radiance_path_with_tonemap`, `test_run_opencv_merge_backend_dispatches_robertson_uint8_radiance_path`; verifies Debevec and Robertson consume the shared linear bracket contract without gamma inversion. |
| TST-043 | `tests/test_uint16_postprocess_pipeline.py::test_extract_bracket_images_float_uses_single_linear_base_pass`; verifies one neutral RAW postprocess call, sensor-dynamic-range base normalization, normalized camera white-balance gain application, and EV scaling/clipping for bracket derivation. |
| TST-044 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_defaults_gamma_to_auto`, `test_parse_run_options_accepts_custom_gamma`, `test_parse_run_options_rejects_invalid_gamma_payload`, `test_print_help_documents_all_conversion_options_with_defaults`; verifies `--gamma` help, default/custom parsing, invalid-payload rejection, and preserved linear extraction. |
| TST-040 | `tests/test_uint16_postprocess_pipeline.py::test_run_opencv_merge_mertens_applies_float_path_brightness_rescaling`, `test_run_opencv_merge_backend_keeps_mertens_inputs_as_float32`; verifies float-only Mertens output applies `255x` exposure-fusion scaling before final normalization. |
| TST-050 | `tests/test_uint16_postprocess_pipeline.py::test_resolve_auto_merge_gamma_prefers_exif_colorspace`; verifies EXIF-first auto merge-gamma resolution ordering. |
| TST-051 | `tests/test_uint16_postprocess_pipeline.py::test_run_opencv_merge_backend_applies_resolved_merge_gamma_last`; verifies final OpenCV backend-local merge gamma application. |
| TST-052 | `tests/test_uint16_postprocess_pipeline.py::test_run_hdr_plus_merge_applies_resolved_merge_gamma_last`; verifies final HDR+ backend-local merge gamma application. |
| TST-053 | `tests/test_uint16_postprocess_pipeline.py::test_run_prints_merge_gamma_diagnostics`; verifies deterministic merge-gamma request and resolved diagnostics. |
| TST-055 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_post_gamma_auto_and_knobs`; verifies parser acceptance of `--post-gamma=auto`, defaults, and knob overrides. |
| TST-056 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_rejects_post_gamma_auto_knobs_without_auto`; verifies parser rejects `--post-gamma-auto-*` without `--post-gamma=auto`. |
| TST-057 | `tests/test_uint16_postprocess_pipeline.py::test_apply_static_postprocess_float_executes_auto_gamma_then_static_substages`; verifies auto-gamma plus downstream static brightness/contrast/saturation order under `--post-gamma=auto`. |
| TST-058 | `tests/test_uint16_postprocess_pipeline.py::test_apply_auto_post_gamma_float_uses_mean_luminance_anchor_and_guards`; verifies luminance-anchor gamma formula and guard-path unchanged output behavior. |
| TST-059 | `tests/test_uint16_postprocess_pipeline.py::test_apply_auto_post_gamma_float_uses_float_lut_mapping_without_quantized_helpers`; verifies float LUT-domain mapping without quantized intermediates or stage-local clipping. |
| REQ-181 | `src/dng2jpg/dng2jpg.py::_parse_white_balance_mode_option`, `_parse_run_options`, `print_help`; excerpt: parses optional `--auto-white-balance`, validates mode set including explicit `disable`, and keeps the stage disabled when omitted or `disable`. |
| REQ-199 | `src/dng2jpg/dng2jpg.py::_apply_auto_white_balance_stage_float`, `_postprocess`; excerpt: derives white-balance estimation payload exclusively from current post-merge stage input and does not consume bracket tensors or `ev_zero` selectors. |
| REQ-210 | `src/dng2jpg/dng2jpg.py::_parse_white_balance_xphoto_domain_option`, `_parse_run_options`, `print_help`; excerpt: parses optional `--white-balance-xphoto-domain`, validates selector set, defaults to `linear`, and preserves `source-auto` compatibility selection. |
| REQ-182 | `src/dng2jpg/dng2jpg.py::_postprocess`, `run`; excerpt: executes auto-white-balance only when mode is configured, after auto-brightness and before static postprocess, and prints disabled diagnostic when omitted. |
| REQ-183 | `src/dng2jpg/dng2jpg.py::_apply_auto_white_balance_stage_float`; excerpt: builds one transient estimation image via shared auto-brightness preprocessing and estimates one correction gain vector from that payload. |
| REQ-200 | `src/dng2jpg/dng2jpg.py::_apply_auto_white_balance_stage_float`, `_apply_channel_gains_to_white_balance_image`; excerpt: applies estimated gains to original stage input and emits one corrected RGB float image for downstream static/manual postprocess stages. |
| REQ-213 | `src/dng2jpg/dng2jpg.py::_apply_auto_white_balance_stage_float`; excerpt: keeps auto-brightness-preprocessed estimation image transient and never emits it as stage output. |
| REQ-184 | `src/dng2jpg/dng2jpg.py::_extract_white_balance_channel_gains_from_xphoto`, `_build_xphoto_analysis_image_rgb_float`; excerpt: `Simple` mode uses real-image payloads with anti-aliased `INTER_AREA` pyramid downsampling and no fixed-size proxy strip. |
| REQ-185 | `src/dng2jpg/dng2jpg.py::_extract_white_balance_channel_gains_from_xphoto`, `_build_xphoto_analysis_image_rgb_float`; excerpt: `GrayworldWB` mode uses real-image payloads with anti-aliased `INTER_AREA` pyramid downsampling and no fixed-size proxy strip. |
| REQ-186 | `src/dng2jpg/dng2jpg.py::_extract_white_balance_channel_gains_from_xphoto`, `_estimate_xphoto_white_balance_gains_rgb`; excerpt: `IA` mode uses real-image payloads with anti-aliased pyramid downsampling before xphoto parameter estimation. |
| REQ-201 | `src/dng2jpg/dng2jpg.py::_rescale_xphoto_estimation_payload_rgb_float`, `_compress_xphoto_estimation_payload_highlights_soft_knee`, `_extract_white_balance_channel_gains_from_xphoto`; excerpt: confines xphoto quantization to estimation boundaries and replaces hard clipping with robust-rescale plus monotonic soft-knee compression. |
| REQ-211 | `src/dng2jpg/dng2jpg.py::_probe_xphoto_uint16_payload_support`, `_estimate_xphoto_white_balance_gains_rgb`, `_quantize_xphoto_estimation_payload_rgb`; excerpt: probes per-algorithm uint16 support, configures IA range/histogram settings, enables Grayworld uint16 when supported, and keeps Simple fallback behavior when probe fails. |
| REQ-212 | `src/dng2jpg/dng2jpg.py::_resolve_white_balance_xphoto_estimation_domain`, `_prepare_xphoto_estimation_image_rgb_float`, `_estimate_xphoto_white_balance_gains_rgb`; excerpt: applies `linear|srgb|source-auto` selector only to xphoto estimation-domain preparation. |
| REQ-187 | `src/dng2jpg/dng2jpg.py::_build_white_balance_robust_analysis_mask`, `_estimate_color_constancy_white_balance_gains_rgb`; excerpt: computes luminance/channel statistics from percentile-based robust masks in linear (`gamma=1`) domain. |
| REQ-188 | `src/dng2jpg/dng2jpg.py::_build_white_balance_robust_analysis_mask`, `_estimate_ttl_white_balance_gains_rgb`; excerpt: computes `avg_gray/avg_channel` gains from percentile-based robust masks in linear (`gamma=1`) domain. |
| TST-060 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_white_balance_modes_and_selector_defaults`; verifies accepted white-balance selectors, default `linear`, and auto-white-balance disabled default. |
| TST-061 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_rejects_invalid_white_balance_mode_or_selectors`; verifies deterministic parse rejection for unsupported white-balance mode, removed analysis-source option, and invalid xphoto domain. |
| TST-062 | `tests/test_uint16_postprocess_pipeline.py::test_run_skips_white_balance_when_mode_not_specified`; verifies diagnostic `Auto-white-balance stage: disabled` and no auto-white-balance call when option omitted. |
| TST-063 | `tests/test_uint16_postprocess_pipeline.py::test_apply_auto_white_balance_stage_float_uses_transient_auto_brightness_preprocessing`; verifies transient estimation preprocessing and single-image gain application on original stage input. |
| TST-064 | `tests/test_uint16_postprocess_pipeline.py::test_apply_white_balance_to_bracket_triplet_simple_mode_uses_xphoto_factory`; verifies `Simple` mode xphoto factory path. |
| TST-065 | `tests/test_uint16_postprocess_pipeline.py::test_apply_white_balance_to_bracket_triplet_grayworld_mode_uses_xphoto_factory`; verifies `GrayworldWB` mode xphoto factory path. |
| TST-066 | `tests/test_uint16_postprocess_pipeline.py::test_apply_white_balance_to_bracket_triplet_ia_mode_sets_hist_bins`, `test_extract_white_balance_channel_gains_from_xphoto_supports_uint16_payload_for_ia`, `test_estimate_xphoto_white_balance_gains_grayworld_uses_uint16_when_probe_succeeds`, `test_estimate_xphoto_white_balance_gains_simple_falls_back_to_uint8_without_probe_support`; verifies xphoto uint16 capability policy for IA, GrayworldWB, and Simple. |
| TST-067 | `tests/test_uint16_postprocess_pipeline.py::test_apply_white_balance_to_bracket_triplet_color_constancy_mode_uses_robust_masked_statistics`, `test_build_white_balance_robust_analysis_mask_uses_percentile_thresholds`, `test_apply_auto_white_balance_stage_float_color_constancy_path_avoids_quantized_helpers`; verifies linear-domain robust masking and no xphoto quantization-helper usage for ColorConstancy. |
| TST-068 | `tests/test_uint16_postprocess_pipeline.py::test_apply_white_balance_to_bracket_triplet_ttl_mode_uses_robust_masked_statistics`, `test_build_white_balance_robust_analysis_mask_uses_percentile_thresholds`, `test_apply_auto_white_balance_stage_float_ttl_path_avoids_quantized_helpers`; verifies linear-domain robust masking and no xphoto quantization-helper usage for TTL. |
| TST-075 | `tests/test_uint16_postprocess_pipeline.py::test_apply_auto_white_balance_stage_float_uses_transient_auto_brightness_preprocessing`; verifies transient auto-brightness estimation does not replace stage output with preprocessed pixels. |
| TST-076 | `tests/test_uint16_postprocess_pipeline.py::test_extract_white_balance_channel_gains_from_xphoto_accepts_real_image_payload_shape`, `test_extract_white_balance_channel_gains_from_xphoto_uses_inter_area_pyramid_downsampling`, `test_compress_xphoto_estimation_payload_highlights_soft_knee_reduces_hard_clip`; verifies non-fixed payload shape, anti-aliased downsampling, and soft-knee highlight compression for xphoto estimation payloads. |
| TST-077 | `tests/test_uint16_postprocess_pipeline.py::test_estimate_xphoto_white_balance_gains_source_auto_resolves_srgb_domain`, `test_apply_auto_white_balance_stage_float_uses_transient_auto_brightness_preprocessing`, `test_run_routes_auto_white_balance_to_post_merge_stage`; verifies estimation-domain selection remains estimation-only and stage output contracts remain float-domain and pre-merge unaffected. |
| REQ-189 | `src/dng2jpg/dng2jpg.py::_parse_hdr_merge_option`, `_parse_run_options`, `run`; excerpt: accepts `OpenCV-Tonemap` selector and routes backend execution when selected or by default. |
| REQ-190 | `src/dng2jpg/dng2jpg.py::_parse_opencv_tonemap_backend_options`, `_parse_run_options`; excerpt: accepts zero or one `--opencv-tonemap-algorithm=<drago|reinhard|mantiuk>` selector in OpenCV-Tonemap mode with default `reinhard`. |
| REQ-191 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: rejects `--opencv-tonemap-algorithm` and `--opencv-tonemap-<algorithm>-*` options unless OpenCV-Tonemap backend is selected. |
| REQ-192 | `src/dng2jpg/dng2jpg.py::_run_opencv_tonemap_backend`; excerpt: processes only bracket index `1` (`ev_zero`) and ignores minus/plus brackets. |
| REQ-193 | `src/dng2jpg/dng2jpg.py::_run_opencv_tonemap_backend`; excerpt: dispatches selected Drago/Reinhard/Mantiuk implementation with `gamma_inv=1/resolved_merge_gamma` from merge-gamma curve resolution. |
| REQ-194 | `src/dng2jpg/dng2jpg.py::OpenCvTonemapOptions`, `_parse_opencv_tonemap_backend_options`, `print_help`; excerpt: exposes and defaults Drago optional knobs. |
| REQ-195 | `src/dng2jpg/dng2jpg.py::OpenCvTonemapOptions`, `_parse_opencv_tonemap_backend_options`, `print_help`; excerpt: exposes and defaults Reinhard optional knobs. |
| REQ-196 | `src/dng2jpg/dng2jpg.py::OpenCvTonemapOptions`, `_parse_opencv_tonemap_backend_options`, `print_help`; excerpt: exposes and defaults Mantiuk optional knobs. |
| REQ-197 | `src/dng2jpg/dng2jpg.py::_run_opencv_tonemap_backend`; excerpt: applies resolved merge gamma only as backend-final step after tone mapping. |
| REQ-198 | `src/dng2jpg/dng2jpg.py::_run_opencv_tonemap_backend`, `_apply_merge_gamma_float_no_clip`; excerpt: preserves float dynamic range without stage-local clipping in OpenCV-Tonemap backend. |
| TST-069 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_opencv_tonemap_backend_and_default_selector`; verifies OpenCV-Tonemap `--opencv-tonemap-algorithm=<drago|reinhard|mantiuk>` parsing with omitted-selector default `reinhard`. |
| TST-070 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_rejects_tonemap_options_without_opencv_tonemap_backend`; verifies `--opencv-tonemap-algorithm` and `--opencv-tonemap-<algorithm>-*` backend coupling plus selector/knob misuse rejections. |
| TST-071 | `tests/test_uint16_postprocess_pipeline.py::test_run_opencv_tonemap_backend_uses_ev_zero_only`; verifies ev-zero-only consumption and minus/plus exclusion. |
| TST-072 | `tests/test_uint16_postprocess_pipeline.py::test_run_opencv_tonemap_backend_dispatches_algorithms_with_fixed_gamma`; verifies Drago/Reinhard/Mantiuk dispatch and `gamma_inv=1/resolved_merge_gamma`. |
| TST-073 | `tests/test_uint16_postprocess_pipeline.py::test_run_opencv_tonemap_backend_applies_merge_gamma_last`; verifies merge gamma is applied after tone mapping. |
| TST-074 | `tests/test_uint16_postprocess_pipeline.py::test_run_opencv_tonemap_backend_preserves_dynamic_range_without_clipping`; verifies no backend-local clipping across OpenCV-Tonemap boundaries. |
| TST-078 | `tests/test_uint16_postprocess_pipeline.py::test_postprocess_skips_entry_normalization_for_float_merge_output`, `test_postprocess_normalizes_non_float_entry_payload`; verifies postprocess entry handling preserves merge float outputs and normalizes external non-float payloads only. |
