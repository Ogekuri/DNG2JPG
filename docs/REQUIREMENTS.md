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
- **CTN-002**: MUST parse `--hdr-merge <Luminace-HDR|OpenCV-Merge|HDR-Plus>` and MUST default to `OpenCV-Merge` when omitted.
- **CTN-003**: MUST resolve exposure mode from `--ev`, `--ev-zero`, and `--auto-ev <enable|disable>`, and MUST reject any invocation that combines `--ev` with `--auto-ev`.
- **CTN-004**: MUST require `.dng` input extension, existing input file, and existing output parent directory.
- **CTN-005**: MUST preflight-check each external executable selected by resolved options (`luminance-hdr-cli`) and MUST fail before processing with explicit diagnostics naming every missing executable.
- **CTN-006**: MUST reject launcher execution when resolved launcher base directory differs from repository git root.

## 3. Requirements

### 3.1 Design and Implementation
- **DES-001**: MUST parse CLI arguments by deterministic token scanning supporting both `--option value` and `--option=value` syntaxes.
- **DES-002**: MUST model runtime options with immutable dataclasses `AutoAdjustOptions`, `AutoBrightnessOptions`, `PostprocessOptions`, `LuminanceOptions`, and `AutoEvInputs`.
- **DES-003**: MUST derive supported EV and EV-zero quantized values from detected DNG bit depth using `0.25` EV step constraints.
- **DES-004**: MUST isolate intermediate processing artifacts in temporary directories and cleanup automatically after command completion.
- **DES-005**: MUST preserve source EXIF payload into output JPEG, rebuild EXIF thumbnail from the exact final quantized RGB uint8 save buffer, preserve JPEG-display-equivalent thumbnail orientation, and write refreshed EXIF metadata before timestamp synchronization.
- **DES-006**: MUST resolve backend-specific default postprocess factors from selected `--hdr-merge` mode, from resolved `Luminace-HDR` tone-mapping operator, and from resolved OpenCV merge algorithm.
- **DES-008**: MUST resolve OpenCV backend static postprocess defaults per `Debevec`, `Robertson`, and `Mertens`, assigning each algorithm `post_gamma=1.0`, `brightness=1.0`, `contrast=1.0`, and `saturation=1.0`.
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
- **REQ-007**: MUST reject `--aa-*` options when `--auto-adjust` resolves to `disable` and MUST reject `--ab-*` options when `--auto-brightness` resolves to `disable`.
- **REQ-008**: MUST compute `ev_best`, `ev_ettr`, and `ev_detail` from the normalized linear HDR base image whenever exposure planning executes, independent of whether `--ev` or `--auto-ev` selected the mode.
- **REQ-009**: MUST compute one symmetric triplet centered on `ev_zero` and use one bracketing half-span `ev_delta` derived only from the iterative clipping-threshold process.
- **REQ-010**: MUST extract one maximum-resolution demosaiced RGB base image using linear `rawpy.postprocess` with camera white balance before HDR bracket generation.
- **REQ-158**: MUST normalize the extracted HDR base image to RGB float `[0,1]` before any bracket arithmetic.
- **REQ-159**: MUST derive `ev_minus`, `ev_zero`, and `ev_plus` only by EV scaling and `[0,1]` clipping of the normalized HDR base image.
- **REQ-160**: MUST preserve the ordered float triplet `(ev_minus, ev_zero, ev_plus)` as the only cross-stage HDR bracket contract.
- **REQ-011**: MUST run `luminance-hdr-cli` with deterministic HDR/TMO arguments including `--ldrTiff 32b` for luminance backend, MUST print the full executed command syntax with parameters to runtime output, confine any required float32 TIFF intermediates to the backend step, and return normalized RGB float output.
- **REQ-174**: MUST serialize luminance backend input bracket images from DNG2JPG RGB float `[0,1]` working format into TIFF float32 files before `luminance-hdr-cli` execution.
- **REQ-175**: MUST import `luminance-hdr-cli` output TIFF float32 data and normalize it back to DNG2JPG RGB float `[0,1]` working format.
- **REQ-012**: MUST exchange normalized OpenCV-compatible RGB float tensors `[0,1]` between merge, auto-brightness, auto-levels, static postprocess, auto-adjust, and final-save preparation stages.
- **REQ-013**: MUST execute static postprocess in order `gamma->brightness->contrast->saturation`, where `gamma` is numeric `--post-gamma=<value>` or auto `--post-gamma=auto`, before optional auto-brightness and optional auto-levels.
- **REQ-106**: MUST execute optional auto-adjust stage after static postprocess and before final JPEG quantization/write, preserve RGB float input/output interfaces, and confine any required float-to-uint16 or TIFF16 conversions to the auto-adjust step itself.
- **REQ-014**: MUST synchronize output file timestamps from EXIF datetime only after refreshed EXIF metadata has been written when EXIF datetime metadata is available.
- **REQ-015**: MUST return `1` on parse, validation, dependency, and processing errors, and return `0` on successful processing.
- **REQ-016**: MUST execute GitHub latest-release version checks with an idle-time cache JSON file and print version status or check errors.
- **REQ-150**: MUST use idle-delay `3600` seconds after successful latest-release checks and idle-delay `86400` seconds after any latest-release check error.
- **REQ-151**: MUST recalculate idle-time and rewrite the version-check cache JSON after every latest-release API attempt, regardless of success or error outcome.
- **REQ-017**: MUST render conversion usage/help with canonical executable name `dng2jpg`, stable aligned indentation, and MUST NOT prepend alternative launcher labels.
- **REQ-018**: MUST reject `--ev-zero` unless `--ev` is specified and MUST reject `--auto-zero`, `--auto-zero-pct`, `--auto-ev-shadow-target`, `--auto-ev-highlight-target`, and `--auto-ev-pct` as removed options.
- **REQ-019**: MUST accept `--auto-ev-shadow-clipping` and `--auto-ev-highlight-clipping` as percentage thresholds in inclusive range `0..100`, defaulting both to `20`.
- **REQ-020**: MUST parse `--gamma=auto` as the default HDR merge-output transfer selector and MUST accept `--gamma=<linear_coeff,exponent>` as one explicit custom transfer selector.
- **REQ-169**: MUST resolve `--gamma=auto` from original RAW/DNG EXIF color-space evidence extracted via `exifread` binary stream processing, mapping sRGB to IEC 61966-2-1 transfer, Adobe RGB to power gamma `2.19921875`, and unresolved evidence to sRGB transfer as default fallback.
- **REQ-170**: MUST apply resolved merge gamma only as the last backend-local step of OpenCV `Debevec`/`Robertson` and `HDR-Plus` HDR merge pipelines, after backend normalization and before shared static postprocess, without additional clipping above backend normalization.
- **REQ-171**: MUST print deterministic merge-gamma runtime diagnostics containing the user request, resolved transfer label, parameter payload, and evidence source.
- **REQ-172**: MUST print normalized EXIF merge-gamma inputs containing `ColorSpace`, `InteroperabilityIndex`, `ImageModel`, `ImageMake`, and a human-readable `ColorProfile` label derived from `ColorSpace` and `InteroperabilityIndex` values whenever `--gamma=auto` is resolved from RAW/DNG metadata.
- **REQ-173**: MUST extract merge-gamma EXIF evidence by opening the original RAW/DNG file as a binary stream via `exifread.process_file` and MUST normalize `EXIF ColorSpace`, `Interop InteroperabilityIndex`, and `Image Model` tags for deterministic auto transfer resolution.
- **REQ-157**: MUST derive source gamma diagnostics from original RAW/DNG EXIF color-profile metadata via `exifread` and MAY supplement with `rawpy` metadata without modifying HDR bracket extraction, which remains linear and camera-WB-aware.
- **REQ-163**: MUST classify source gamma diagnostics by preferring DNG EXIF `ColorSpace` and `InteroperabilityIndex` fields, mapping `ColorSpace=1` to sRGB, `ColorSpace=2` or `R03` interop to Adobe RGB, and MUST report `unknown` when EXIF evidence is insufficient.
- **REQ-164**: MUST print source gamma diagnostics as one deterministic runtime line containing both a source-gamma label and either a numeric gamma value or `undetermined`.
- **REQ-021**: MUST enforce `--jpg-compression` in inclusive range `0..100`.
- **REQ-022**: MUST reject luminance-specific options when `--hdr-merge` is not `Luminace-HDR`.
- **REQ-023**: MUST reject unknown `--hdr-merge` values and accept only `Luminace-HDR`, `OpenCV-Merge`, or `HDR-Plus`.
- **REQ-024**: MUST route backend execution from resolved `--hdr-merge` mode and MUST preserve the existing processing behavior of `Luminace-HDR`, `OpenCV-Merge`, and `HDR-Plus`.
- **REQ-025**: MUST reject unsupported `--auto-adjust` values, accept only `enable` or `disable`, and default omitted `--auto-adjust` to `enable`.
- **REQ-026**: MUST resolve DNG bit depth from `raw_image_visible.dtype.itemsize * 8` with fallback to `white_level.bit_length()`.
- **REQ-027**: MUST enforce minimum supported bit depth as `9` bits per color.
- **REQ-028**: MUST compute bracket EV ceiling only from bit-depth headroom `MAX_BRACKET=((bits_per_color-8)/2)-abs(ev_zero)`.
- **REQ-029**: MUST compute EV-zero safe ceiling with `SAFE_ZERO_MAX=((bits_per_color-8)/2)-1`.
- **REQ-030**: MUST accept any numeric `--ev` and `--ev-zero` values within the bit-depth-derived valid range without enforcing `0.25` EV step granularity.
- **REQ-031**: MUST derive exposure-planning inputs from the shared normalized linear HDR base image used for bracket export.
- **REQ-032**: MUST evaluate `ev_best`, `ev_ettr`, and `ev_detail` on the normalized linear gamma=`1` RGB image and MUST select default `ev_zero` as the minimum absolute-value candidate among those three values when `--ev-zero` is not specified.
- **REQ-166**: MUST expose `--auto-ev-step` as a positive configurable EV increment for iterative bracket expansion, defaulting to `0.1`.
- **REQ-167**: MUST derive `ev_delta` by iterating from `auto_ev_step`, evaluating unclipped bracket images at `ev_zero-ev_delta` and `ev_zero+ev_delta`, and stopping at the first step where shadow clipping exceeds `--auto-ev-shadow-clipping` or highlight clipping reaches `--auto-ev-highlight-clipping`.
- **REQ-168**: MUST measure highlight clipping as the percentage of pixels in the plus image with any channel `>=1` and shadow clipping as the percentage of pixels in the minus image with any channel `<=0`.
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
- **REQ-050**: MUST implement `/tmp/auto-brightness.py` auto-brightness step order on normalized RGB float input/output: normalize sRGB, linearize, compute BT.709 luminance, tonemap luminance, rescale RGB, optionally desaturate, then re-encode sRGB.
- **REQ-051**: MUST support exactly one auto-adjust pipeline with one validated knob model containing shared controls and CLAHE-luma controls.
- **REQ-052**: MUST print deterministic runtime diagnostics for input path, gamma, postprocess factors, backend, exposure mode, `Exposure Misure EV` values, selected `ev_zero`, iterative bracket-step clipping metrics, final `ev_delta`, EV triplet, and OpenCV radiance exposure calculations/results.
- **REQ-103**: MUST classify normalized BT.709 luminance as `low-key` when `median<0.35 && p95<0.85`, `high-key` when `median>0.65 && p05>0.15`, else `normal-key`.
- **REQ-104**: MUST map luminance with `L=(a/Lw_bar)*Y`, percentile-derived robust `Lwhite`, and burn-out compression `Ld=(L*(1+L/Lwhite^2))/(1+L)` before linear-domain chromaticity-preserving RGB scaling.
- **REQ-105**: MUST desaturate only overflowing linear RGB pixels by blending toward `(Ld,Ld,Ld)` with the minimal factor that restores `max(R,G,B)<=1` while preserving luminance.
- **REQ-100**: MUST execute auto-levels after static postprocess and optional auto-brightness when `--auto-levels` resolves to `enable`, preserving RGB float input/output buffers and float internal calculations across histogram analysis and tonal transformation.
- **REQ-101**: MUST parse `--auto-levels <enable|disable>`, `--al-clip-pct`, `--al-clip-out-of-gamut`, `--al-highlight-reconstruction`, `--al-highlight-reconstruction-method`, and `--al-gain-threshold`, requiring resolved auto-levels state `enable` before any `--al-*` option.
- **REQ-102**: MUST accept highlight reconstruction methods `Luminance Recovery`, `CIELab Blending`, `Blend`, `Color Propagation`, and `Inpaint Opposed`.
- **REQ-116**: MUST default auto-levels knobs to `clip_pct=0.02`, `clip_out_of_gamut=true`, `highlight_reconstruction=disabled`, `highlight_reconstruction_method=Inpaint Opposed`, and `gain_threshold=1.0`.
- **REQ-117**: MUST derive auto-levels calibration from a RawTherapee-compatible luminance histogram using `sum`, `average`, `median`, octiles, `ospread`, `rawmax`, clipped white point, and clipped black point.
- **REQ-118**: MUST derive `expcomp`, `black`, `brightness`, `contrast`, `hlcompr`, and `hlcomprthresh` using RawTherapee `ImProcFunctions::getAutoExp` formula families, including gamma-domain whiteclip correction and normalized float-domain metric emission.
- **REQ-119**: MUST apply a RawTherapee-equivalent float-domain tonal transformation that consumes `expcomp`, `black`, `brightness`, `contrast`, `hlcompr`, and `hlcomprthresh`, including per-channel overflow handling, exposure scaling, highlight curve, brightness curve, contrast curve, inverse-gamma output mapping, and default shadow compression `0`.
- **REQ-120**: MUST execute optional highlight reconstruction after the auto-levels tonal transformation, using `--al-highlight-reconstruction` as the explicit enable toggle, mapping `Color Propagation` to RawTherapee `Color` and `Inpaint Opposed` to RawTherapee `Coloropp`.
- **REQ-165**: MUST apply `Clip out-of-gamut colors` after the complete auto-levels tonal transformation and optional highlight reconstruction using the RawTherapee `filmlike_clip` hue-stable clipping family instead of isotropic ratio-preserving normalization.
- **REQ-121**: MUST compute `log_avg_lum`, `median_lum`, `p05`, `p95`, `shadow_clip_in<=1/255`, and `highlight_clip_in>=254/255` from normalized luminance before key-value selection.
- **REQ-122**: MUST auto-select base Reinhard `a` as `0.09`, `0.18`, or `0.36`, boost when `p95<0.60 && median<0.35`, attenuate when `p05>0.40 && median>0.65`, then clamp to `[a_min,a_max]`.
- **REQ-123**: MUST execute auto-adjust stages in this exact order on RGB float buffers: selective blur, adaptive level, CLAHE-luma, sigmoidal contrast, HSL vibrance, and high-pass overlay.
- **REQ-124**: MUST expose auto-brightness CLI knobs for `key_value`, `white_point_percentile`, `a_min`, `a_max`, `max_auto_boost_factor`, and `eps`.
- **REQ-125**: MUST expose `--aa-enable-local-contrast`, `--aa-local-contrast-strength`, `--aa-clahe-clip-limit`, and `--aa-clahe-tile-grid-size` as auto-adjust CLAHE-luma controls.
- **REQ-135**: MUST expose `--ab-enable-luminance-preserving-desat` as the auto-brightness desaturation toggle.
- **REQ-136**: MUST implement CLAHE-luma directly on RGB float `[0,1]` by adjusting luminance only, reconstructing RGB with preserved chroma, and blending with the original image via configurable strength.
- **REQ-137**: MUST keep auto-adjust CLAHE-luma functionally equivalent to the former auto-brightness CLAHE-luma stage except for differences attributable only to removed float-uint16 quantization.
- **REQ-107**: MUST accept `--hdr-merge OpenCV-Merge` as HDR backend selector and execute OpenCV backend behavior when selected or by default.
- **REQ-108**: MUST execute OpenCV backend from three in-memory RGB float brackets ordered as `ev_minus`, `ev_zero`, `ev_plus` using selectable algorithm `Debevec`, `Robertson`, or `Mertens`, defaulting to `Robertson`, and MUST pass brackets without entry re-normalization or clipping.
- **REQ-109**: MUST derive OpenCV Debevec/Robertson exposure times in seconds from source EXIF `ExposureTime`, preserve bracket order, and map the sequence to extracted `(ev_zero-ev_delta, ev_zero, ev_zero+ev_delta)`.
- **REQ-110**: MUST preserve RGB float input/output interfaces for OpenCV merge and MUST keep the full OpenCV HDR path in RGB float `[0,1]` without backend-local `uint8` or `uint16` conversions.
- **REQ-141**: MUST expose OpenCV controls `--opencv-merge-algorithm`, `--opencv-tonemap`, and `--opencv-tonemap-gamma`, defaulting to `Robertson`, `enable`, and `2.2`.
- **REQ-142**: MUST treat EXIF `ExposureTime` as the linear RAW exposure time of the extracted base image and MUST compute OpenCV radiance times as `t_raw*2^(ev_zero-ev_delta)`, `t_raw*2^ev_zero`, and `t_raw*2^(ev_zero+ev_delta)`.
- **REQ-143**: MUST execute optional OpenCV simple gamma tone mapping for `Debevec`, `Robertson`, and `Mertens` outputs before downstream postprocess, default enabled with gamma `2.2`, and MUST skip contrast-enhancing tone operators.
- **REQ-144**: MUST deliver one congruent normalized RGB float output contract across OpenCV `Debevec`, `Robertson`, and `Mertens`, preserving exposure semantics without backend-specific contrast compensation.
- **REQ-152**: MUST feed Debevec and Robertson OpenCV input brackets directly from the linear HDR bracket contract without any gamma-inversion preprocessing step.
- **REQ-153**: MUST estimate inverse camera response with OpenCV `CalibrateDebevec` or `CalibrateRobertson` before OpenCV `MergeDebevec` or `MergeRobertson` and MUST pass both `times` and calibrated `response` into the merge call.
- **REQ-161**: MUST extract EXIF `ExposureTime` from the source DNG metadata and reject OpenCV `Debevec` or `Robertson` execution when that value is missing, non-positive, or not coercible to seconds.
- **REQ-162**: MUST keep OpenCV Debevec and Robertson processing on RGB float `[0,1]` interfaces while allowing backend-local response estimation inputs/outputs required by OpenCV calibrators.
- **REQ-154**: MUST execute OpenCV `MergeMertens` on RGB float `[0,1]` brackets with one identical resolved merge-gamma transfer pre-applied to all three inputs, then rescale fusion output and apply optional OpenCV tonemap before final normalization.
- **REQ-145**: MUST resolve OpenCV backend downstream postprocess defaults per `Debevec`, `Robertson`, and `Mertens`, assigning each algorithm neutral factors `post_gamma=1.0`, `brightness=1.0`, `contrast=1.0`, and `saturation=1.0`.
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
- **REQ-133**: MUST perform exactly one float-to-uint8 quantization immediately before final JPEG save.
- **REQ-134**: MUST preserve legacy numeric static equations in float domain, execute `gamma->brightness->contrast->saturation`, and MUST NOT apply stage-local `[0,1]` clipping in static substage input adaptation or substage equations.
- **REQ-176**: MUST parse `--post-gamma=auto` as an alternative to numeric `--post-gamma=<value>` and replace only the static gamma substage, preserving downstream static `brightness->contrast->saturation` execution unchanged.
- **REQ-177**: MUST compute auto-gamma from grayscale mean luminance `L` using `gamma=log(target_gray)/log(L)` when `luma_min < L < luma_max`, and MUST return input unchanged with resolved gamma `1.0` otherwise.
- **REQ-178**: MUST apply auto-gamma by LUT-domain mapping in RGB float space using `output=input^gamma` with configurable LUT size, without stage-local clipping or quantized intermediates.
- **REQ-179**: MUST expose auto-gamma knobs `--post-gamma-auto-target-gray`, `--post-gamma-auto-luma-min`, `--post-gamma-auto-luma-max`, and `--post-gamma-auto-lut-size` with defaults `0.5`, `0.01`, `0.99`, and `256`.
- **REQ-180**: MUST reject `--post-gamma-auto-*` options unless `--post-gamma=auto` is selected.
- **REQ-146**: MUST accept `--debug` as a flag that enables persistent TIFF checkpoint emission for executed pipeline stages without changing the final JPG destination.
- **REQ-147**: MUST write each debug TIFF from normalized RGB float `[0,1]` data using filename `<input-dng-stem><stage-suffix>.tiff` in the resolved output JPG directory.
- **REQ-148**: MUST use monotonically increasing numeric stage suffixes with phase labels covering bracket extraction (`ev_min`, `ev_zero`, `ev_max`), HDR merge, static postprocess, auto-brightness, auto-levels, and auto-adjust checkpoints when those stages execute.
- **REQ-149**: MUST preserve debug TIFF files after command completion while keeping temporary workspace cleanup behavior unchanged for non-debug intermediates.
- **REQ-181**: MUST parse optional `--white-balance <Simple|GrayworldWB|IA|ColorConstancy|TTL>`, defaulting to disabled when omitted and rejecting unknown values.
- **REQ-182**: MUST execute white-balance only when `--white-balance` is specified, after bracket triplet extraction and before HDR backend merge; omitted option MUST skip the stage without altering existing merge behavior.
- **REQ-183**: MUST estimate white-balance correction parameters exclusively from `ev_zero`, apply identical parameters to all three brackets, and preserve normalized float RGB tensors as canonical input, internal representation, and output.
- **REQ-184**: MUST implement `--white-balance Simple` via OpenCV xphoto `createSimpleWB` for tangential parameter or curve evaluation only, while keeping bracket processing in normalized float RGB without stage-local image discretization.
- **REQ-185**: MUST implement `--white-balance GrayworldWB` via OpenCV xphoto `createGrayworldWB` for tangential parameter or curve evaluation only, while keeping bracket processing in normalized float RGB without stage-local image discretization.
- **REQ-186**: MUST implement `--white-balance IA` via OpenCV xphoto `createLearningBasedWB` with `setHistBinNum(256)` for tangential parameter or curve evaluation only, while keeping bracket processing in normalized float RGB without stage-local image discretization.
- **REQ-187**: MUST implement `--white-balance ColorConstancy` using scikit-image-derived color-constancy analysis on `ev_zero` and apply identical float-domain channel correction to all three brackets without non-mandatory clipping or rescaling.
- **REQ-188**: MUST implement `--white-balance TTL` with Von Kries-style per-channel gains computed from `ev_zero` channel means and apply those gains identically to all three brackets without stage-local clipping.

## 4. Test Requirements

- **TST-001**: MUST verify `_parse_run_options` rejects `--ev` with `--auto-ev`, parses `--hdr-merge`, and rejects unknown `--hdr-merge` values with deterministic error output.
- **TST-002**: MUST verify `run` returns `1` for unsupported runtime OS and for missing `luminance-hdr-cli` dependency with deterministic diagnostics naming each missing executable.
- **TST-003**: MUST verify successful `run` execution returns `0`, writes output JPG, and emits success message `HDR JPG created: <output>`.
- **TST-004**: MUST verify default `ev_zero` selection chooses the minimum absolute-value candidate among `ev_best`, `ev_ettr`, and `ev_detail`, independent of whether static `--ev` or `--auto-ev` selected the mode.
- **TST-005**: MUST verify static exposure resolution preserves any in-range manual `--ev` and `--ev-zero` values, rejects out-of-range values for the detected bit depth, and no longer requires `0.25` EV increments.
- **TST-006**: MUST verify `_run_luminance_hdr_cli` builds deterministic argument order and includes any `--tmo*` passthrough pairs unchanged.
- **TST-007**: MUST verify `_extract_dng_exif_payload_and_timestamp` applies datetime priority `36867` then `36868` then `306` and extracts EXIF `ExposureTime` as positive seconds.
- **TST-008**: MUST verify `_refresh_output_jpg_exif_thumbnail_after_save` preserves source orientation fields, rebuilds EXIF thumbnail bytes from the exact final quantized RGB uint8 save buffer, and emits display-oriented thumbnail pixels with thumbnail orientation `1`.
- **TST-009**: MUST verify release workflow gates `build-release` execution on `needs.check-branch.outputs.is_master == "true"`.
- **TST-010**: MUST verify `_parse_run_options` enforces `--auto-levels <enable|disable>` with `--al-*` coupling and validates `Clip out-of-gamut colors`, `Clip %`, highlight-reconstruction toggle, method, and gain-threshold knobs.
- **TST-011**: MUST verify `_apply_auto_brightness_rgb_float` preserves float I/O and executes the original step order, key-analysis thresholds, Reinhard mapping, and optional desaturation.
- **TST-012**: MUST verify `_encode_jpg` keeps float stage buffers and applies a single float-to-uint8 conversion immediately before JPEG save.
- **TST-013**: MUST verify `_parse_run_options` accepts `--hdr-merge OpenCV-Merge`, defaults `--hdr-merge` to `OpenCV-Merge`, and rejects values outside `Luminace-HDR`, `OpenCV-Merge`, and `HDR-Plus`.
- **TST-014**: MUST verify OpenCV radiance exposure derivation preserves bracket order, uses EXIF exposure seconds, maps the sequence to `(ev_zero-ev_delta, ev_zero, ev_zero+ev_delta)`, and remains deterministic for variable bracket spans.
- **TST-015**: MUST verify OpenCV merge outputs for `Debevec`, `Robertson`, and `Mertens` remain normalized RGB float images bounded to `[0,1]` after float-only backend execution.
- **TST-047**: MUST verify `_parse_run_options` rejects removed `--auto-ev-shadow-target`, `--auto-ev-highlight-target`, and `--auto-ev-pct`, and accepts `--auto-ev-shadow-clipping`, `--auto-ev-highlight-clipping`, and `--auto-ev-step` with deterministic defaults and validation.
- **TST-048**: MUST verify iterative bracket expansion stops on the first step where plus-image highlight clipping reaches threshold or minus-image shadow clipping exceeds threshold and returns that step as `ev_delta`.
- **TST-049**: MUST verify runtime diagnostics rename `Auto-EV heuristic` to `Exposure Misure EV`, print per-step clipping percentages for the iterative bracket search, and print the final `ev_zero` and `ev_delta` selection.
- **TST-016**: MUST verify auto-levels parser defaults `clip_pct=0.02`, `clip_out_of_gamut=true`, `highlight_reconstruction=false`, `highlight_reconstruction_method=Inpaint Opposed`, and `gain_threshold=1.0`.
- **TST-017**: MUST verify auto-levels histogram calibration reproduces RawTherapee-compatible `expcomp`, `black`, `brightness`, `contrast`, `hlcompr`, and `hlcomprthresh` for deterministic synthetic histograms.
- **TST-018**: MUST verify auto-levels tonal transformation consumes the RawTherapee-compatible metric set in normalized float space, preserves float-only internal math, and matches RawTherapee mixed-overflow channel handling.
- **TST-046**: MUST verify `Clip out-of-gamut colors` executes the RawTherapee `filmlike_clip` hue-stable clipping family instead of isotropic ratio-preserving normalization.
- **TST-045**: MUST verify `Color Propagation` and `Inpaint Opposed` selectors execute only when `--al-highlight-reconstruction` resolves to enabled and preserve deterministic RGB float outputs.
- **TST-019**: MUST verify auto-brightness CLI parsing exposes key-value, white-point, boost, epsilon, and desaturation controls with deterministic defaults and validation.
- **TST-020**: MUST verify auto-brightness clipping proxies use normalized thresholds `1/255` and `254/255` and key auto-selection uses the original base values and boost rules.
- **TST-021**: MUST verify `_parse_run_options` accepts HDR+ knob overrides and rejects invalid HDR+ knob combinations with deterministic parse errors.
- **TST-022**: MUST verify HDR+ scalar proxy mode `rggb` produces deterministic green-weighted scalar conversion from RGB float input.
- **TST-023**: MUST verify HDR+ hierarchical alignment resolves non-zero alternate-frame tile offsets for translated inputs and keeps reference offsets at zero.
- **TST-024**: MUST verify HDR+ temporal weighting applies resolved alignment offsets and internally normalized temporal parameters before distance evaluation and RGB accumulation.
- **TST-025**: MUST verify HDR+ merge preserves normalized float32 arithmetic and float input/output boundaries without any HDR+ `uint16` conversion path.
- **TST-026**: MUST verify `_apply_static_postprocess_float` preserves float I/O and does not call uint16 adaptation helpers or legacy uint16 static-stage helpers.
- **TST-027**: MUST verify `_apply_static_postprocess_float` bypasses when all static factors are neutral and otherwise executes only non-neutral substages in strict `gamma->brightness->contrast->saturation` order.
- **TST-028**: MUST verify auto-adjust CLI parsing accepts `enable|disable`, defaults to `enable`, and exposes CLAHE-luma enable, strength, clip-limit, and tile-grid controls with deterministic defaults and validation.
- **TST-029**: MUST verify `_apply_validated_auto_adjust_pipeline` preserves float I/O and executes `blur -> level -> CLAHE-luma -> sigmoid -> vibrance -> high-pass`.
- **TST-030**: MUST verify float-domain auto-adjust CLAHE-luma preserves blend semantics and remains within quantization-only deviation from the former uint16 implementation on deterministic fixtures.
- **TST-031**: MUST verify `_resolve_default_postprocess` resolves `Debevec`, `Robertson`, and `Mertens` OpenCV defaults independently and returns neutral factors `post_gamma=1.0`, `brightness=1.0`, `contrast=1.0`, and `saturation=1.0` for each algorithm.
- **TST-041**: MUST verify `print_help` renders conversion help in pipeline execution order, colocates per-stage configuration options with the described stage, and keeps canonical `dng2jpg` usage formatting.
- **TST-042**: MUST verify `print_help` documents every accepted conversion CLI option with allowed values or activation conditions and prints effective defaults for omitted options.
- **TST-032**: MUST verify `_parse_run_options` accepts `--opencv-merge-algorithm`, `--opencv-tonemap`, and `--opencv-tonemap-gamma`, applies defaults, and rejects invalid OpenCV HDR values.
- **TST-033**: MUST verify OpenCV backend dispatch selects `MergeDebevec`, `MergeRobertson`, or `MergeMertens` and runs `CalibrateDebevec` or `CalibrateRobertson` before Debevec/Robertson merge dispatch.
- **TST-034**: MUST verify optional OpenCV tone mapping defaults to enabled with gamma `2.2` and can be disabled for `Debevec`, `Robertson`, and `Mertens` without changing pre-tonemap merge outputs.
- **TST-035**: MUST verify OpenCV radiance exposure derivation uses EXIF exposure seconds with non-zero extracted `ev_zero` and propagates calibrated response into Debevec/Robertson merge calls.
- **TST-036**: MUST verify OpenCV backend preserves RGB float input/output boundaries and avoids backend-local `uint8` or `uint16` conversions.
- **TST-037**: MUST verify `_parse_run_options` accepts `--debug` and enables persistent debug checkpoint configuration without changing existing positional or backend parsing.
- **TST-038**: MUST verify debug checkpoint writers emit progressive TIFF filenames for extraction, merge, static postprocess, auto-brightness, auto-levels, and auto-adjust outputs in the output directory.
- **TST-039**: MUST verify Debevec and Robertson OpenCV inputs are consumed directly from the linear HDR bracket contract without gamma-inversion preprocessing.
- **TST-043**: MUST verify `_extract_bracket_images_float` executes exactly one RAW postprocess call for a linear camera-WB-aware base image and derives `ev_minus`, `ev_zero`, `ev_plus` only through NumPy EV scaling and `[0,1]` clipping.
- **TST-044**: MUST verify CLI help documents `--gamma`, parser defaults to `--gamma=auto`, parser accepts `--gamma=<a,b>`, parser rejects invalid gamma payloads, and HDR bracket extraction remains linear.
- **TST-050**: MUST verify `--gamma=auto` resolves transfer selection from EXIF color-space evidence with deterministic fallback ordering.
- **TST-051**: MUST verify OpenCV backend applies resolved merge gamma as the final backend-local float step without extra clipping around the gamma transfer.
- **TST-052**: MUST verify HDR+ backend applies resolved merge gamma as the final backend-local float step without extra clipping around the gamma transfer.
- **TST-053**: MUST verify runtime diagnostics print deterministic merge-gamma request and resolved-transfer lines.
- **TST-054**: MUST verify automatic merge-gamma diagnostics print normalized EXIF `ColorSpace`, `InteroperabilityIndex`, and `ImageModel` inputs used during resolution.
- **TST-055**: MUST verify `_parse_run_options` accepts `--post-gamma=auto`, applies auto-gamma defaults, and parses `--post-gamma-auto-*` overrides.
- **TST-056**: MUST verify `_parse_run_options` rejects `--post-gamma-auto-*` options when `--post-gamma=auto` is not selected.
- **TST-057**: MUST verify `_apply_static_postprocess_float` executes `auto-gamma->brightness->contrast->saturation` when `--post-gamma=auto`, preserving numeric static behavior for `brightness->contrast->saturation`.
- **TST-058**: MUST verify auto-gamma luminance anchoring computes `gamma=log(target_gray)/log(mean_luminance)` and returns unchanged image when mean luminance is outside configured guard bounds.
- **TST-059**: MUST verify auto-gamma LUT-domain mapping runs in float space without quantized intermediates and without stage-local clipping.
- **TST-040**: MUST verify float-only OpenCV Mertens output applies OpenCV-equivalent `255x` exposure-fusion scaling before final `[0,1]` normalization.
- **TST-060**: MUST verify `_parse_run_options` defaults white-balance to disabled when omitted and accepts `Simple`, `GrayworldWB`, `IA`, `ColorConstancy`, and `TTL`.
- **TST-061**: MUST verify `_parse_run_options` rejects missing or unsupported `--white-balance` values with deterministic parse diagnostics.
- **TST-062**: MUST verify `run` skips white-balance stage when `--white-balance` is omitted and forwards extracted bracket tensors unchanged to selected HDR backend.
- **TST-063**: MUST verify `_apply_white_balance_to_bracket_triplet` computes correction parameters from bracket index `1` (`ev_zero`) only and applies identical parameters to all three brackets.
- **TST-064**: MUST verify `Simple` white-balance path invokes OpenCV xphoto `createSimpleWB`, confines quantized image evaluation to tangential parameter extraction, and applies EV0-derived float-domain gains identically to all brackets.
- **TST-065**: MUST verify `GrayworldWB` white-balance path invokes OpenCV xphoto `createGrayworldWB`, confines quantized image evaluation to tangential parameter extraction, and applies EV0-derived float-domain gains identically to all brackets.
- **TST-066**: MUST verify `IA` white-balance path invokes OpenCV xphoto `createLearningBasedWB`, applies `setHistBinNum(256)` when supported, confines quantized image evaluation to tangential parameter extraction, and applies EV0-derived float-domain gains identically to all brackets.
- **TST-067**: MUST verify `ColorConstancy` white-balance path uses scikit-image luminance analysis to derive EV0-only gains and applies them identically to all brackets.
- **TST-068**: MUST verify `TTL` white-balance path computes gains as `avg_gray/avg_channel` from `ev_zero` and applies un-clipped float-domain gains identically to all brackets.

## 5. Evidence Matrix

| Requirement ID | Evidence |
|---|---|
| PRJ-001 | `src/dng2jpg/dng2jpg.py::run`, `_build_exposure_multipliers`, and `_extract_bracket_images_float`; excerpt: derives `ev_minus`, `ev_zero`, `ev_plus` multipliers, extracts three normalized RGB float brackets with `output_bps=16`, then merges via selected backend. |
| PRJ-002 | `src/dng2jpg/dng2jpg.py::print_help`, `_parse_run_options`; excerpt: documents and parses exposure, EV-center, backend, postprocess, auto-adjust, and auto-brightness controls. |
| PRJ-003 | `src/dng2jpg/core.py::main`; excerpt: handles `--help`, `--ver`, `--version`, `--upgrade`, `--uninstall`, and conversion dispatch. |
| PRJ-004 | `.github/workflows/release-uvx.yml`; excerpt: semantic tag trigger, build job, attestation, and GitHub release upload flow. |
| PRJ-005 | `scripts/d2j.sh`; excerpt: `exec "${UV_TOOL}" run --project "${BASE_DIR}" python -m dng2jpg "$@"`. |
| CTN-001 | `src/dng2jpg/dng2jpg.py::_is_supported_runtime_os`; excerpt: returns true only on Linux and prints Linux-only error otherwise. |
| CTN-002 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: parses `--hdr-merge` from the remaining backend set and defaults to `OpenCV-Merge` when omitted. |
| CTN-003 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: resolves static versus automatic exposure mode and rejects invalid `--ev`/`--auto-ev` combinations. |
| CTN-004 | `src/dng2jpg/dng2jpg.py::run`; excerpt: validates `.dng` suffix, input existence, and output parent directory existence. |
| CTN-005 | `src/dng2jpg/dng2jpg.py::_collect_missing_external_executables`, `run`; excerpt: explicit preflight for selected external commands and deterministic missing-dependency diagnostics. |
| CTN-006 | `scripts/d2j.sh`; excerpt: compares `${PROJECT_ROOT}` and `${BASE_DIR}` and exits `1` on mismatch. |
| DES-001 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: deterministic token scan loop over args with explicit branch handling. |
| DES-002 | `src/dng2jpg/dng2jpg.py` dataclasses; evidence: `AutoAdjustOptions`, `AutoBrightnessOptions`, `PostprocessOptions`, `LuminanceOptions`, `AutoEvInputs`. |
| DES-003 | `src/dng2jpg/dng2jpg.py::_derive_supported_ev_values`, `_derive_supported_ev_zero_values`; excerpt: uses `EV_STEP = 0.25`. |
| DES-004 | `src/dng2jpg/dng2jpg.py::run`, `_run_luminance_hdr_cli`; excerpt: isolates intermediate artifacts under the command temporary workspace and backend-local subdirectories. |
| DES-005 | `src/dng2jpg/dng2jpg.py::_extract_dng_exif_payload_and_timestamp`, `_refresh_output_jpg_exif_thumbnail_after_save`, `_build_oriented_thumbnail_jpeg_bytes`, `_encode_jpg`, `_sync_output_file_timestamps_from_exif`. |
| DES-006 | `src/dng2jpg/dng2jpg.py::_resolve_default_postprocess`; excerpt: backend and TMO-specific defaults. |
| DES-008 | `src/dng2jpg/dng2jpg.py::_resolve_default_postprocess`; excerpt: OpenCV backend defaults `post_gamma=1.0`, `brightness=1.0`, `contrast=1.0`, `saturation=1.0`. |
| DES-007 | `docs/WORKFLOW.md`; excerpt: execution-unit model shows process-based flows and "no explicit threads detected". |
| REQ-001 | `src/dng2jpg/core.py::main`; excerpt: no args -> `ported.print_help(__version__)` and `return 0`. |
| REQ-002 | `src/dng2jpg/core.py::main`; excerpt: `--help` prints management help and conversion help. |
| REQ-003 | `src/dng2jpg/core.py::main`; excerpt: `--ver` and `--version` print version and return `0`. |
| REQ-004 | `src/dng2jpg/core.py::_run_management`, `main`; excerpt: executes `uv tool install ...` and `uv tool uninstall` on Linux. |
| REQ-005 | `src/dng2jpg/core.py::_run_management`; excerpt: non-Linux path prints manual command and returns `0`. |
| REQ-006 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: explicit errors for unknown option and missing values. |
| REQ-007 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: rejects `--aa-*` when auto-adjust resolves to `disable` and rejects `--ab-*` when auto-brightness resolves to `disable`. |
| REQ-008 | `src/dng2jpg/dng2jpg.py::_resolve_joint_auto_ev_solution`, `_optimize_joint_ev_zero_and_delta`; excerpt: solves `ev_zero` and `ev_delta` jointly from linear-image heuristics and preview statistics. |
| REQ-009 | `src/dng2jpg/dng2jpg.py::_resolve_joint_auto_ev_solution`; excerpt: treats `--auto-ev` as the only automatic exposure path and emits the symmetric EV triplet. |
| REQ-010 | `src/dng2jpg/dng2jpg.py::_extract_base_rgb_linear_float`, `_extract_bracket_images_float`; excerpt: executes one linear camera-WB-aware `rawpy.postprocess(...)` call before bracket derivation. |
| REQ-011 | `src/dng2jpg/dng2jpg.py::_run_luminance_hdr_cli`, `_format_external_command_for_log`; excerpt: deterministic luminance args including `--ldrTiff 32b`, emitted full command syntax with parameters, and backend-local float32 TIFF artifact handling. |
| REQ-174 | `src/dng2jpg/dng2jpg.py::_materialize_bracket_tiffs_from_float`, `_write_rgb_float_tiff32`; excerpt: serializes DNG2JPG RGB float `[0,1]` brackets as TIFF float32 files. |
| REQ-175 | `src/dng2jpg/dng2jpg.py::_run_luminance_hdr_cli`; excerpt: imports `luminance-hdr-cli` output TIFF float32 and normalizes to RGB float `[0,1]`. |
| REQ-012 | `src/dng2jpg/dng2jpg.py::_encode_jpg`, `_apply_static_postprocess_float`; excerpt: keeps merge/postprocess/auto-adjust/final-save buffers on normalized RGB float interfaces. |
| REQ-013 | `src/dng2jpg/dng2jpg.py::_encode_jpg`, `_apply_static_postprocess_float`; excerpt: executes static order `gamma->brightness->contrast->saturation` where gamma is numeric or auto-gamma, before optional auto-brightness/auto-levels. |
| REQ-014 | `src/dng2jpg/dng2jpg.py::_encode_jpg`, `_sync_output_file_timestamps_from_exif`; excerpt: writes refreshed EXIF metadata before applying `os.utime` from EXIF timestamp. |
| REQ-015 | `src/dng2jpg/dng2jpg.py::run`; excerpt: parse/dependency/processing failures return `1`, success returns `0`. |
| REQ-016 | `src/dng2jpg/core.py::_check_online_version`, `_write_version_cache`; excerpt: GitHub latest-release check uses idle-time cache JSON and prints status or error output. |
| REQ-150 | `src/dng2jpg/core.py::_check_online_version`; excerpt: success path uses `3600` seconds and error paths use `86400` seconds when calculating idle-delay. |
| REQ-151 | `src/dng2jpg/core.py::_check_online_version`, `_write_version_cache`; excerpt: cache JSON is rewritten after every latest-release API attempt on both success and error outcomes. |
| REQ-017 | `src/dng2jpg/dng2jpg.py`; excerpt: `PROGRAM = "dng2jpg"` and help usage renders canonical command label without duplicated command token. |
| REQ-018 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: rejects removed `--auto-zero*` options and rejects `--ev-zero` outside static `--ev` mode. |
| REQ-019 | `src/dng2jpg/dng2jpg.py::_parse_percentage_option`; excerpt: enforces inclusive `0..100` bounds for `--auto-ev-pct`. |
| REQ-020 | `src/dng2jpg/dng2jpg.py::_parse_gamma_option`, `_parse_run_options`, `print_help`; excerpt: restores `--gamma`, defaults omitted gamma to `auto`, and accepts custom `<linear_coeff,exponent>` payloads. |
| REQ-021 | `src/dng2jpg/dng2jpg.py::_parse_jpg_compression_option`; excerpt: enforces inclusive `0..100`. |
| REQ-022 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: rejects luminance options unless `--hdr-merge Luminace-HDR` is selected. |
| REQ-023 | `src/dng2jpg/dng2jpg.py::_parse_hdr_merge_option`, `_parse_run_options`; excerpt: validates `--hdr-merge` against the remaining allowed modes. |
| REQ-024 | `src/dng2jpg/dng2jpg.py::run`; excerpt: routes backend execution from resolved `--hdr-merge` mode. |
| REQ-025 | `src/dng2jpg/dng2jpg.py::_parse_auto_adjust_option`, `_parse_run_options`; excerpt: validates `enable|disable` values and defaults omitted auto-adjust to `enable`. |
| REQ-026 | `src/dng2jpg/dng2jpg.py::_detect_dng_bits_per_color`; excerpt: container bit depth primary path with white-level fallback. |
| REQ-027 | `src/dng2jpg/dng2jpg.py::_calculate_max_ev_from_bits`; excerpt: raises on bit depth below `MIN_SUPPORTED_BITS_PER_COLOR=9`. |
| REQ-028 | `src/dng2jpg/dng2jpg.py::_derive_supported_ev_values`; excerpt: uses `MAX_BRACKET=((bits_per_color-8)/2)-abs(ev_zero)`. |
| REQ-029 | `src/dng2jpg/dng2jpg.py::_calculate_safe_ev_zero_max`; excerpt: `SAFE_ZERO_MAX = BASE_MAX - 1`. |
| REQ-030 | `src/dng2jpg/dng2jpg.py::_is_ev_value_on_supported_step`; excerpt: quarter-step quantization validation. |
| REQ-031 | `src/dng2jpg/dng2jpg.py::_extract_normalized_preview_luminance_stats`; excerpt: percentiles `0.1`, `50.0`, `99.9`. |
| REQ-032 | `src/dng2jpg/dng2jpg.py::_build_joint_auto_ev_regularization_anchors`, `_optimize_joint_ev_zero_and_delta`; excerpt: converts the three automatic heuristics into soft center regularization for the joint solver. |
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
| REQ-050 | `src/dng2jpg/dng2jpg.py::_apply_auto_brightness_rgb_float`; excerpt: executes the original auto-brightness step order on normalized RGB float I/O with optional luminance-preserving desaturation before final sRGB re-encoding. |
| REQ-051 | `src/dng2jpg/dng2jpg.py::AutoAdjustOptions`, `_apply_validated_auto_adjust_pipeline`; excerpt: supports one float-domain auto-adjust implementation with one validated knob container including CLAHE-luma controls. |
| REQ-052 | `src/dng2jpg/dng2jpg.py::run`; excerpt: deterministic `print_info` diagnostic lines for exposure mode, automatic anchors, selected joint solution, EV triplet, and OpenCV radiance timing calculations/results. |
| REQ-103 | `src/dng2jpg/dng2jpg.py::_analyze_luminance_key`; excerpt: classifies `low-key`/`normal-key`/`high-key` with the original median and percentile thresholds. |
| REQ-104 | `src/dng2jpg/dng2jpg.py::_reinhard_global_tonemap_luminance`, `_apply_auto_brightness_rgb_float`; excerpt: percentile robust `Lwhite` and burn-out compression before RGB scaling. |
| REQ-105 | `src/dng2jpg/dng2jpg.py::_luminance_preserving_desaturate_to_fit`; excerpt: overflow-only luminance-preserving grayscale blending with minimal factor selection. |
| REQ-100 | `src/dng2jpg/dng2jpg.py::_encode_jpg`, `_apply_auto_levels_float`, `_apply_static_postprocess_float`, `_apply_auto_brightness_rgb_float`; excerpt: executes auto-levels only when resolved state is `enable`, after static postprocess and optional auto-brightness. |
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
| REQ-107 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `print_help`; excerpt: parses `--hdr-merge OpenCV-Merge` and defaults to `OpenCV-Merge` when omitted. |
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
| REQ-141 | `src/dng2jpg/dng2jpg.py::OpenCvMergeOptions`, `_parse_opencv_merge_backend_options`, `_parse_run_options`, `print_help`; excerpt: exposes OpenCV algorithm, tone-map enable, and tone-map gamma controls with defaults `Robertson`, `enable`, and `2.2`. |
| REQ-142 | `src/dng2jpg/dng2jpg.py::_build_opencv_radiance_exposure_times`, `run`; excerpt: treats EXIF `ExposureTime` as linear RAW exposure and computes radiance times as `t_raw*2^(ev_zero±ev_delta)` around extracted `ev_zero`. |
| REQ-165 | `src/dng2jpg/dng2jpg.py::_clip_auto_levels_out_of_gamut_float`, `_apply_auto_levels_float`; excerpt: normalizes overflowing RGB triplets after tonal transform and optional highlight reconstruction while preserving channel ratios. |
| REQ-143 | `src/dng2jpg/dng2jpg.py::_run_opencv_merge_radiance`, `_run_opencv_merge_mertens`, `_normalize_opencv_hdr_to_unit_range`; excerpt: applies optional simple gamma tone mapping for Debevec/Robertson/Mertens, defaults it to enabled with gamma `2.2`, and avoids contrast-enhancing OpenCV tone operators. |
| REQ-144 | `src/dng2jpg/dng2jpg.py::_normalize_opencv_hdr_to_unit_range`, `_run_opencv_merge_radiance`, `_run_opencv_merge_mertens`; excerpt: normalizes Debevec, Robertson, and Mertens outputs to one congruent RGB float `[0,1]` contract without backend-specific contrast compensation. |
| REQ-145 | `src/dng2jpg/dng2jpg.py::_resolve_default_postprocess`; excerpt: assigns neutral downstream postprocess defaults for the OpenCV backend. |
| REQ-152 | `src/dng2jpg/dng2jpg.py::_run_opencv_merge_backend`; excerpt: routes Debevec and Robertson directly from the shared linear HDR bracket contract without gamma-inversion preprocessing. |
| REQ-157 | `src/dng2jpg/dng2jpg.py::_describe_source_gamma_info`, `_extract_source_gamma_info`, `run`; excerpt: derives source gamma diagnostics from RAW metadata while leaving linear HDR extraction unchanged. |
| REQ-163 | `src/dng2jpg/dng2jpg.py::_extract_source_gamma_info`, `_classify_tone_curve_gamma`; excerpt: applies metadata-priority ordering and returns `unknown` when metadata evidence is insufficient. |
| REQ-164 | `src/dng2jpg/dng2jpg.py::_describe_source_gamma_info`, `run`; excerpt: prints deterministic source gamma label and numeric-or-undetermined value. |
| REQ-169 | `src/dng2jpg/dng2jpg.py::_extract_exif_gamma_tags`, `_resolve_auto_merge_gamma`, `run`; excerpt: derives auto merge transfer from EXIF color-space evidence via `exifread` binary stream processing with source-gamma fallback. |
| REQ-170 | `src/dng2jpg/dng2jpg.py::_apply_merge_gamma_float`, `_run_opencv_merge_backend`, `_run_hdr_plus_merge`; excerpt: applies merge gamma only as the last backend-local float step without post-gamma clipping. |
| REQ-171 | `src/dng2jpg/dng2jpg.py::_describe_resolved_merge_gamma`, `run`; excerpt: prints deterministic merge-gamma request and resolved-transfer diagnostics. |
| REQ-158 | `src/dng2jpg/dng2jpg.py::_extract_base_rgb_linear_float`; excerpt: normalizes the extracted HDR base image to RGB float `[0,1]` before bracket arithmetic. |
| REQ-159 | `src/dng2jpg/dng2jpg.py::_build_exposure_multipliers`, `_build_bracket_images_from_linear_base_float`; excerpt: derives brackets exclusively by EV multipliers and `[0,1]` clipping of the normalized base tensor. |
| REQ-160 | `src/dng2jpg/dng2jpg.py::_build_bracket_images_from_linear_base_float`, `_extract_bracket_images_float`, `_run_opencv_merge_backend`, `_run_luminance_hdr_cli`, `_run_hdr_plus_merge`; excerpt: preserves ordered float triplet `(ev_minus, ev_zero, ev_plus)` as the shared downstream contract. |
| REQ-153 | `src/dng2jpg/dng2jpg.py::_estimate_opencv_camera_response`, `_run_opencv_merge_radiance`; excerpt: calibrates inverse camera response before Debevec/Robertson merge and passes both `times` and `response` into the merge call. |
| REQ-161 | `src/dng2jpg/dng2jpg.py::_parse_exif_exposure_time_to_seconds`, `_extract_dng_exif_payload_and_timestamp`, `_build_opencv_radiance_exposure_times`, `run`; excerpt: extracts EXIF `ExposureTime`, coerces it to positive seconds, and rejects radiance merge when invalid. |
| REQ-162 | `src/dng2jpg/dng2jpg.py::_estimate_opencv_camera_response`, `_run_opencv_merge_radiance`, `_run_opencv_merge_backend`; excerpt: preserves RGB float `[0,1]` interfaces while allowing OpenCV-local response estimation artifacts. |
| REQ-154 | `src/dng2jpg/dng2jpg.py::_run_opencv_merge_mertens`, `_run_opencv_merge_backend`; excerpt: keeps Mertens on RGB float `[0,1]` brackets and applies `255x` output rescaling plus optional OpenCV tonemap before final normalization. |
| REQ-132 | `src/dng2jpg/dng2jpg.py::_apply_static_postprocess_float`, `_apply_post_gamma_float`, `_apply_brightness_float`, `_apply_contrast_float`, `_apply_saturation_float`; excerpt: bypasses numeric static postprocess when all numeric static factors are neutral and otherwise executes only non-neutral static factors directly on RGB float tensors without quantized intermediates. |
| REQ-133 | `src/dng2jpg/dng2jpg.py::_encode_jpg`; excerpt: performs the only float-to-uint8 quantization immediately before Pillow JPEG save. |
| REQ-134 | `src/dng2jpg/dng2jpg.py::_apply_static_postprocess_float`, `_apply_post_gamma_float`, `_apply_brightness_float`, `_apply_contrast_float`, `_apply_saturation_float`; excerpt: preserves numeric static transfer equations in float domain and enforces static substage order `gamma->brightness->contrast->saturation` for executed factors. |
| REQ-176 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `_apply_static_postprocess_float`; excerpt: parses `--post-gamma=auto` and replaces only the gamma substage while preserving downstream static brightness/contrast/saturation execution. |
| REQ-177 | `src/dng2jpg/dng2jpg.py::_apply_auto_post_gamma_float`; excerpt: computes grayscale mean-luminance anchored gamma and returns unchanged input with gamma `1.0` outside configured guard bounds. |
| REQ-178 | `src/dng2jpg/dng2jpg.py::_build_auto_post_gamma_lut_float`, `_apply_auto_post_gamma_float`; excerpt: applies float LUT-domain mapping `output=input^gamma` without quantized intermediates or stage-local clipping. |
| REQ-179 | `src/dng2jpg/dng2jpg.py::PostGammaAutoOptions`, `_parse_post_gamma_auto_options`, `_parse_run_options`, `print_help`; excerpt: exposes auto-gamma knobs and defaults. |
| REQ-180 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: rejects `--post-gamma-auto-*` options unless `--post-gamma=auto` is selected. |
| DES-009 | `src/dng2jpg/dng2jpg.py::DebugArtifactContext`, `_write_debug_rgb_float_tiff`; excerpt: serializes float checkpoints as persistent TIFF16 outputs outside the temporary workspace. |
| REQ-146 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `print_help`, `run`; excerpt: parses `--debug`, documents the flag, and enables persistent checkpoint orchestration. |
| REQ-147 | `src/dng2jpg/dng2jpg.py::_write_debug_rgb_float_tiff`, `run`; excerpt: writes `<input-dng-stem><stage-suffix>.tiff` into the output JPG directory from normalized RGB float payloads. |
| REQ-148 | `src/dng2jpg/dng2jpg.py::run`, `_apply_static_postprocess_float`, `_encode_jpg`, `_apply_validated_auto_adjust_pipeline`; excerpt: emits progressive numeric stage suffixes across extraction, merge, postprocess, and optional stage checkpoints. |
| REQ-149 | `src/dng2jpg/dng2jpg.py::run`; excerpt: keeps debug TIFF outputs outside `TemporaryDirectory(...)` while still cleaning the temporary workspace after execution. |
| TST-001 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; branches for exposure-mode exclusivity, hdr-merge parsing, and deterministic parse failures. |
| TST-002 | `src/dng2jpg/dng2jpg.py::run`; branches for unsupported OS and dependency failures returning `1`. |
| TST-003 | `src/dng2jpg/dng2jpg.py::run`; success branch prints `HDR JPG created: ...` and returns `0`. |
| TST-004 | `tests/test_uint16_postprocess_pipeline.py::test_optimize_joint_ev_zero_and_delta_reduces_span_against_legacy_baseline`, `test_optimize_joint_ev_zero_and_delta_uses_deterministic_tie_break`; verifies span reduction and deterministic ordering. |
| TST-005 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_defaults_ev_zero_to_zero_for_static_ev`, `test_parse_run_options_preserves_manual_ev_zero_with_static_ev`, `test_parse_run_options_rejects_ev_zero_without_static_ev`; verifies static-mode EV-center rules. |
| TST-006 | `src/dng2jpg/dng2jpg.py::_run_luminance_hdr_cli`; deterministic argv generation including passthrough. |
| TST-007 | `tests/test_uint16_postprocess_pipeline.py::test_extract_dng_exif_payload_and_timestamp_reads_datetime_priority_and_exposure_time`; verifies EXIF datetime priority and positive-second `ExposureTime` parsing. |
| TST-008 | `tests/test_uint16_postprocess_pipeline.py::test_encode_jpg_refreshes_exif_thumbnail_from_final_quantized_rgb_uint8`; verifies EXIF orientation fields and thumbnail bytes derive from final quantized RGB uint8 save image. |
| TST-009 | `.github/workflows/release-uvx.yml`; release job condition depends on `is_master` gate output. |
| TST-010 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; branch checks for `--auto-levels <enable|disable>` coupling and `--al-*` knob validations. |
| TST-011 | `tests/test_uint16_postprocess_pipeline.py::test_apply_auto_brightness_rgb_float_executes_original_stage_order`; verifies float-interface auto-brightness stage order and optional desaturation without CLAHE local contrast. |
| TST-012 | `tests/test_uint16_postprocess_pipeline.py::test_encode_jpg_quantizes_once_at_final_boundary`; verifies one final float-to-uint8 conversion at the JPEG boundary. |
| TST-013 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_hdr_merge_opencv_backend`, `test_parse_run_options_rejects_unknown_hdr_merge_backend`, `test_parse_run_options_defaults_hdr_merge_to_opencv`; validates remaining hdr-merge selection, default, and invalid-value rejection. |
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
| TST-031 | `tests/test_uint16_postprocess_pipeline.py::test_resolve_default_postprocess_opencv_uses_updated_static_defaults`; verifies OpenCV default static postprocess factors resolve to neutral `1.0`, `1.0`, `1.0`, and `1.0`. |
| TST-032 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_opencv_controls_and_defaults`, `test_parse_run_options_rejects_invalid_opencv_controls`; verifies `--opencv-*` parsing, defaults, validation, and backend coupling. |
| TST-033 | `tests/test_uint16_postprocess_pipeline.py::test_run_opencv_merge_backend_dispatches_debevec_uint8_radiance_path_with_tonemap`, `test_run_opencv_merge_backend_dispatches_robertson_uint8_radiance_path`, `test_run_opencv_merge_backend_applies_tonemap_for_mertens_when_enabled`; verifies OpenCV algorithm dispatch across Debevec, Robertson, and Mertens with calibrate-before-merge behavior for radiance modes. |
| TST-034 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_opencv_controls_and_defaults`, `test_run_opencv_merge_backend_dispatches_debevec_uint8_radiance_path_with_tonemap`, `test_run_opencv_merge_backend_applies_tonemap_for_mertens_when_enabled`, `test_run_opencv_merge_backend_skips_tonemap_for_mertens_when_disabled`; verifies tone-map default gamma `2.2`, enabled paths, and explicit disable paths across OpenCV algorithms. |
| TST-035 | `tests/test_uint16_postprocess_pipeline.py::test_run_opencv_merge_backend_dispatches_debevec_direct_float_path_with_tonemap`, `test_run_opencv_merge_backend_dispatches_robertson_direct_float_path`, `test_run_opencv_merge_backend_requires_exif_exposure_time_for_radiance_modes`; verifies EXIF-second radiance timing, calibrated response propagation, and invalid-exposure rejection. |
| TST-045 | `tests/test_uint16_postprocess_pipeline.py::test_apply_auto_levels_color_methods_require_explicit_enable`; verifies highlight reconstruction methods execute only when explicitly enabled. |
| TST-036 | `tests/test_uint16_postprocess_pipeline.py::test_run_opencv_merge_backend_keeps_mertens_inputs_as_float32`, `test_run_opencv_merge_backend_dispatches_debevec_direct_float_path_with_tonemap`, `test_run_opencv_merge_backend_dispatches_robertson_direct_float_path`; verifies OpenCV backend preserves RGB float input/output boundaries and avoids backend-local `uint8` or `uint16` conversions. |
| TST-037 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_enables_debug_flag`; verifies `--debug` parsing preserves existing positional and backend parsing. |
| TST-038 | `tests/test_uint16_postprocess_pipeline.py::test_encode_jpg_writes_debug_checkpoints_with_progressive_suffixes`; verifies persistent TIFF checkpoint filenames and output-directory placement. |
| TST-039 | `tests/test_uint16_postprocess_pipeline.py::test_run_opencv_merge_backend_dispatches_debevec_uint8_radiance_path_with_tonemap`, `test_run_opencv_merge_backend_dispatches_robertson_uint8_radiance_path`; verifies Debevec and Robertson consume the shared linear bracket contract without gamma inversion. |
| TST-043 | `tests/test_uint16_postprocess_pipeline.py::test_extract_bracket_images_float_uses_single_linear_base_pass`; verifies one RAW postprocess call plus NumPy EV scaling/clipping for bracket derivation. |
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
| REQ-181 | `src/dng2jpg/dng2jpg.py::_parse_white_balance_mode_option`, `_parse_run_options`, `print_help`; excerpt: parses optional `--white-balance`, validates mode set, and leaves stage disabled when omitted. |
| REQ-182 | `src/dng2jpg/dng2jpg.py::run`; excerpt: executes white-balance stage only when mode is configured and positions it strictly between bracket extraction and HDR merge dispatch. |
| REQ-183 | `src/dng2jpg/dng2jpg.py::_apply_white_balance_to_bracket_triplet`, `_validate_white_balance_triplet_shape`; excerpt: EV0-only parameter estimation with identical gain payload applied to all brackets while preserving normalized float RGB stage contracts. |
| REQ-184 | `src/dng2jpg/dng2jpg.py::_extract_white_balance_channel_gains_from_xphoto`; excerpt: `Simple` mode confines xphoto quantized evaluation to a parameter-estimation boundary and applies resulting gains to float-domain triplet data. |
| REQ-185 | `src/dng2jpg/dng2jpg.py::_extract_white_balance_channel_gains_from_xphoto`; excerpt: `GrayworldWB` mode confines xphoto quantized evaluation to a parameter-estimation boundary and applies resulting gains to float-domain triplet data. |
| REQ-186 | `src/dng2jpg/dng2jpg.py::_extract_white_balance_channel_gains_from_xphoto`, `_estimate_xphoto_white_balance_gains_rgb`; excerpt: `IA` mode configures `setHistBinNum(256)` and confines xphoto quantized evaluation to parameter-estimation boundary with float-domain triplet application. |
| REQ-187 | `src/dng2jpg/dng2jpg.py::_estimate_color_constancy_white_balance_gains_rgb`; excerpt: uses scikit-image luminance conversion on EV0 to derive one channel-gain payload applied identically to triplet in float domain. |
| REQ-188 | `src/dng2jpg/dng2jpg.py::_estimate_ttl_white_balance_gains_rgb`; excerpt: computes Von Kries-style gains from EV0 channel means and applies un-clipped float-domain gains identically to triplet. |
| TST-060 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_white_balance_modes_and_defaults_disabled`; verifies accepted mode set and default disabled state. |
| TST-061 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_rejects_invalid_white_balance_mode`; verifies deterministic parse rejection for unsupported mode. |
| TST-062 | `tests/test_uint16_postprocess_pipeline.py::test_run_skips_white_balance_when_mode_not_specified`; verifies no white-balance call when option omitted. |
| TST-063 | `tests/test_uint16_postprocess_pipeline.py::test_apply_white_balance_to_bracket_triplet_uses_ev_zero_analysis_only`; verifies center-only analysis with identical triplet application. |
| TST-064 | `tests/test_uint16_postprocess_pipeline.py::test_apply_white_balance_to_bracket_triplet_simple_mode_uses_xphoto_factory`; verifies `Simple` mode xphoto factory path. |
| TST-065 | `tests/test_uint16_postprocess_pipeline.py::test_apply_white_balance_to_bracket_triplet_grayworld_mode_uses_xphoto_factory`; verifies `GrayworldWB` mode xphoto factory path. |
| TST-066 | `tests/test_uint16_postprocess_pipeline.py::test_apply_white_balance_to_bracket_triplet_ia_mode_sets_hist_bins`; verifies `IA` mode learning-based xphoto path and histogram-bin configuration. |
| TST-067 | `tests/test_uint16_postprocess_pipeline.py::test_apply_white_balance_to_bracket_triplet_color_constancy_mode_uses_skimage_luminance`; verifies scikit-image-driven color-constancy path. |
| TST-068 | `tests/test_uint16_postprocess_pipeline.py::test_apply_white_balance_to_bracket_triplet_ttl_mode_applies_unclipped_gains`; verifies TTL gain formula and unclipped float application. |
