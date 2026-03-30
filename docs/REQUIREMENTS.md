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
- **CTN-002**: MUST parse `--hdr-merge <enfuse|Luminace-HDR|OpenCV|HDR-Plus>` and MUST default to `OpenCV` when omitted.
- **CTN-003**: MUST resolve exposure mode from `--ev` and `--auto-ev <enable|disable>`, and MUST let `--ev` override enabled auto exposure when both are specified.
- **CTN-004**: MUST require `.dng` input extension, existing input file, and existing output parent directory.
- **CTN-005**: MUST preflight-check each external executable selected by resolved options (`enfuse`, `luminance-hdr-cli`, and ImageMagick `magick|convert`) and MUST fail before processing with explicit diagnostics naming every missing executable.
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
- **REQ-007**: MUST require `--auto-adjust` before accepting any `--aa-*` option and MUST reject `--ab-*` options when `--auto-brightness` resolves to `disable`.
- **REQ-008**: MUST compute automatic EV center from preview luminance when `--auto-zero` resolves to `enable` and clamp it to safe bit-derived bounds.
- **REQ-009**: MUST compute adaptive EV from preview luminance statistics when `--auto-ev` resolves to `enable` and `--ev` is not specified, then clamp it to supported selectors.
- **REQ-010**: MUST extract brackets `ev_minus`, `ev_zero`, and `ev_plus` with `rawpy.postprocess output_bps=16`, convert each bracket to normalized OpenCV-compatible RGB float `[0,1]`, and expose only that float triplet to downstream merge stages.
- **REQ-011**: MUST run `enfuse` with LZW compression for enfuse backend and `luminance-hdr-cli` with deterministic HDR/TMO arguments for luminance backend, confining any required 16-bit TIFF intermediates to the backend step and returning normalized RGB float output.
- **REQ-012**: MUST exchange normalized OpenCV-compatible RGB float tensors `[0,1]` between merge, auto-brightness, auto-levels, static postprocess, auto-adjust, and final-save preparation stages.
- **REQ-013**: MUST execute optional auto-brightness, optional auto-levels, post-gamma, brightness, contrast, and saturation in this exact order on RGB float stage interfaces before any optional auto-adjust stage.
- **REQ-106**: MUST execute optional auto-adjust stage after static postprocess and before final JPEG quantization/write, preserve RGB float input/output interfaces, and confine any required float-to-uint16 or TIFF16 conversions to the auto-adjust step itself.
- **REQ-014**: MUST synchronize output file timestamps from EXIF datetime when EXIF datetime metadata is available.
- **REQ-015**: MUST return `1` on parse, validation, dependency, and processing errors, and return `0` on successful processing.
- **REQ-016**: MUST execute GitHub latest-release version checks with an idle-time cache file and print version status or check errors.
- **REQ-017**: MUST render conversion usage with canonical executable name `dng2jpg` and MUST NOT prepend alternative launcher labels.
- **REQ-018**: MUST parse `--auto-zero <enable|disable>`, default it to `enable` without `--ev-zero` and `disable` with `--ev-zero`, and MUST let `--ev-zero` override enabled auto-zero with an explicit ignored-parameter output.
- **REQ-019**: MUST enforce `--auto-zero-pct` and `--auto-ev-pct` values in inclusive range `0..100`.
- **REQ-020**: MUST parse `--gamma` as two positive numeric values and reject malformed pairs.
- **REQ-021**: MUST enforce `--jpg-compression` in inclusive range `0..100`.
- **REQ-022**: MUST reject luminance-specific options when `--hdr-merge` is not `Luminace-HDR`.
- **REQ-023**: MUST reject unknown `--hdr-merge` values and accept only `enfuse`, `Luminace-HDR`, `OpenCV`, or `HDR-Plus`.
- **REQ-024**: MUST route backend execution from resolved `--hdr-merge` mode and MUST preserve backend-specific processing behavior.
- **REQ-025**: MUST reject unsupported `--auto-adjust` mode values, accept only `ImageMagick` or `OpenCV`, and default `--auto-adjust` to `OpenCV` when omitted.
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
- **REQ-050**: MUST implement `/tmp/auto-brightness.py` auto-brightness step order on normalized RGB float input/output: normalize sRGB, linearize, compute BT.709 luminance, tonemap luminance, rescale RGB, optionally desaturate, then re-encode sRGB.
- **REQ-051**: MUST support `ImageMagick` and `OpenCV` auto-adjust pipelines with one validated knob model containing shared controls and OpenCV-only CLAHE-luma controls.
- **REQ-052**: MUST print deterministic runtime diagnostics for input path, gamma, postprocess factors, backend, EV selections, and EV triplet.
- **REQ-103**: MUST classify normalized BT.709 luminance as `low-key` when `median<0.35 && p95<0.85`, `high-key` when `median>0.65 && p05>0.15`, else `normal-key`.
- **REQ-104**: MUST map luminance with `L=(a/Lw_bar)*Y`, percentile-derived robust `Lwhite`, and burn-out compression `Ld=(L*(1+L/Lwhite^2))/(1+L)` before linear-domain chromaticity-preserving RGB scaling.
- **REQ-105**: MUST desaturate only overflowing linear RGB pixels by blending toward `(Ld,Ld,Ld)` with the minimal factor that restores `max(R,G,B)<=1` while preserving luminance.
- **REQ-100**: MUST execute auto-levels after optional auto-brightness and before static postprocess when `--auto-levels` resolves to `enable`, while preserving RGB float input/output buffers and float internal calculations.
- **REQ-101**: MUST parse `--auto-levels <enable|disable>`, `--al-clip-pct`, `--al-clip-out-of-gamut`, `--al-highlight-reconstruction-method`, and `--al-gain-threshold`, requiring resolved auto-levels state `enable` before any `--al-*` option.
- **REQ-102**: MUST accept highlight reconstruction methods `Luminance Recovery`, `CIELab Blending`, `Blend`, `Color Propagation`, and `Inpaint Opposed`.
- **REQ-116**: MUST default auto-levels knobs to `clip_pct=0.02`, `clip_out_of_gamut=true`, `highlight_reconstruction=disabled`, `highlight_reconstruction_method=Inpaint Opposed`, and `gain_threshold=1.0`.
- **REQ-117**: MUST derive auto-levels calibration from a RawTherapee-compatible luminance histogram using `sum`, `average`, `median`, octiles, `ospread`, `rawmax`, clipped white point, and clipped black point.
- **REQ-118**: MUST derive `expcomp`, `black`, `brightness`, `contrast`, `hlcompr`, and `hlcomprthresh` using RawTherapee `ImProcFunctions::getAutoExp` formula families, including gamma-domain whiteclip correction.
- **REQ-119**: MUST map `Color Propagation` to RawTherapee `Color` and `Inpaint Opposed` to RawTherapee `Coloropp`, and SHOULD approximate these raw-domain methods deterministically in RGB post-merge processing.
- **REQ-120**: MUST apply `Clip out-of-gamut colors` after auto-levels gain using per-pixel normalization that bounds each overflowing RGB triplet to the uint16 ceiling while preserving channel ratios.
- **REQ-121**: MUST compute `log_avg_lum`, `median_lum`, `p05`, `p95`, `shadow_clip_in<=1/255`, and `highlight_clip_in>=254/255` from normalized luminance before key-value selection.
- **REQ-122**: MUST auto-select base Reinhard `a` as `0.09`, `0.18`, or `0.36`, boost when `p95<0.60 && median<0.35`, attenuate when `p05>0.40 && median>0.65`, then clamp to `[a_min,a_max]`.
- **REQ-123**: MUST execute OpenCV auto-adjust stages in this exact order on RGB float buffers: selective blur, adaptive level, CLAHE-luma, sigmoidal contrast, HSL vibrance, and high-pass overlay.
- **REQ-124**: MUST expose auto-brightness CLI knobs for `key_value`, `white_point_percentile`, `a_min`, `a_max`, `max_auto_boost_factor`, and `eps`.
- **REQ-125**: MUST expose `--aa-enable-local-contrast`, `--aa-local-contrast-strength`, `--aa-clahe-clip-limit`, and `--aa-clahe-tile-grid-size` as OpenCV auto-adjust CLAHE-luma controls.
- **REQ-135**: MUST expose `--ab-enable-luminance-preserving-desat` as the auto-brightness desaturation toggle.
- **REQ-136**: MUST implement CLAHE-luma directly on RGB float `[0,1]` by adjusting luminance only, reconstructing RGB with preserved chroma, and blending with the original image via configurable strength.
- **REQ-137**: MUST keep OpenCV auto-adjust CLAHE-luma functionally equivalent to the former auto-brightness CLAHE-luma stage except for differences attributable only to removed float-uint16 quantization.
- **REQ-107**: MUST accept `--hdr-merge OpenCV` as HDR backend selector and execute OpenCV backend behavior when selected or by default.
- **REQ-108**: MUST execute OpenCV backend merge from three in-memory RGB float brackets ordered as `ev_minus`, `ev_zero`, `ev_plus`, using `MergeMertens`, `MergeDebevec`, and EV-derived exposure times.
- **REQ-109**: MUST normalize Debevec HDR radiance in float domain using robust luminance white-point percentile, blend it with Mertens fusion in float domain, and return one normalized RGB float image.
- **REQ-110**: MUST confine any OpenCV-backend float-to-uint16 adaptation required by `MergeDebevec` to the merge step itself and MUST preserve RGB float input/output interfaces for the merge step.
- **REQ-111**: MUST accept `--hdr-merge HDR-Plus` as HDR backend selector and execute HDR+ backend behavior when selected.
- **REQ-112**: MUST execute HDR+ backend in source step order `scalar proxy -> hierarchical alignment -> box_down2 -> temporal merge -> spatial merge`, using `ev_zero` as reference frame.
- **REQ-113**: MUST compute three-level HDR+ alignment on the scalar proxy with `box_down2`, two `gauss_down4` levels, per-tile L1 minimization over offsets `[-4,+3]`, and final full-resolution offset lift by `2`.
- **REQ-114**: MUST compute HDR+ temporal alternate-frame weights from aligned 16x16 downsampled tiles with `factor=8`, `min_dist=10`, `max_dist=300`, hard cutoff, and reference-inclusive normalization.
- **REQ-115**: MUST execute HDR+ spatial blending over aligned half-overlapped 32x32 tiles using raised-cosine weights and return one normalized RGB float image without intermediate `uint8` quantization.
- **REQ-126**: MUST adapt RGB float bracket images to the single-channel HDR+ source domain by deriving one deterministic scalar proxy with default mode `rggb`.
- **REQ-127**: MUST expose HDR+ CLI knobs `--hdrplus-proxy-mode`, `--hdrplus-search-radius`, `--hdrplus-temporal-factor`, `--hdrplus-temporal-min-dist`, and `--hdrplus-temporal-max-dist`.
- **REQ-128**: MUST default HDR+ CLI knobs to `proxy_mode=rggb`, `search_radius=4`, `temporal_factor=8`, `temporal_min_dist=10`, and `temporal_max_dist=300`.
- **REQ-129**: MUST execute HDR+ alignment and merge arithmetic in float domain and confine any required uint16 adaptation to the HDR+ step while preserving RGB float input/output interfaces.
- **REQ-130**: MUST reject HDR+ knob values when `search_radius<1`, `temporal_factor<=0`, `temporal_min_dist<0`, or `temporal_max_dist<=temporal_min_dist`.
- **REQ-131**: MUST print resolved HDR+ proxy, alignment, and temporal knob values in deterministic runtime diagnostics.
- **REQ-132**: MUST execute static postprocess gamma, brightness, contrast, and saturation directly on RGB float tensors without uint16 or other quantized intermediates.
- **REQ-133**: MUST perform exactly one float-to-uint8 quantization immediately before final JPEG save.
- **REQ-134**: MUST preserve legacy post-gamma, brightness, contrast, and saturation equations and parameter semantics in the float-domain port; output differences MUST derive only from removed quantization.

## 4. Test Requirements

- **TST-001**: MUST verify `_parse_run_options` applies `--ev`/`--auto-ev` precedence, parses `--hdr-merge`, and rejects unknown `--hdr-merge` values with deterministic error output.
- **TST-002**: MUST verify `run` returns `1` for unsupported runtime OS and for missing `enfuse`, `luminance-hdr-cli`, or ImageMagick (`magick|convert`) dependencies with deterministic diagnostics naming each missing executable.
- **TST-003**: MUST verify successful `run` execution returns `0`, writes output JPG, and emits success message `HDR JPG created: <output>`.
- **TST-004**: MUST verify `_resolve_ev_zero` enforces `SAFE_ZERO_MAX=((bits_per_color-8)/2)-1` and rejects out-of-range values.
- **TST-005**: MUST verify `_resolve_ev_value` clamps adaptive EV to bit-derived selector bounds and rejects unsupported static EV for the detected bit depth.
- **TST-006**: MUST verify `_run_luminance_hdr_cli` builds deterministic argument order and includes any `--tmo*` passthrough pairs unchanged.
- **TST-007**: MUST verify `_extract_dng_exif_payload_and_timestamp` applies datetime priority `36867` then `36868` then `306`.
- **TST-008**: MUST verify `_refresh_output_jpg_exif_thumbnail_after_save` preserves source orientation in `0th` IFD and sets `1st` IFD orientation to `1`.
- **TST-009**: MUST verify release workflow gates `build-release` execution on `needs.check-branch.outputs.is_master == "true"`.
- **TST-010**: MUST verify `_parse_run_options` enforces `--auto-levels <enable|disable>` with `--al-*` coupling and validates `Clip out-of-gamut colors`, `Clip %`, method, and gain-threshold knobs.
- **TST-011**: MUST verify `_apply_auto_brightness_rgb_float` preserves float I/O and executes the original step order, key-analysis thresholds, Reinhard mapping, and optional desaturation.
- **TST-012**: MUST verify `_encode_jpg` keeps float stage buffers and applies a single float-to-uint8 conversion immediately before JPEG save.
- **TST-013**: MUST verify `_parse_run_options` accepts `--hdr-merge OpenCV`, defaults `--hdr-merge` to `OpenCV`, and rejects unknown `--hdr-merge` values.
- **TST-014**: MUST verify OpenCV EV-time derivation returns deterministic three-element stop-space sequence mapped to bracket order.
- **TST-015**: MUST verify Debevec normalization clamps blended radiance contribution to `[0,1]` float range before merge-step float return.
- **TST-016**: MUST verify auto-levels parser defaults `clip_pct=0.02`, `clip_out_of_gamut=true`, `highlight_reconstruction_method=Inpaint Opposed`, and `gain_threshold=1.0`.
- **TST-017**: MUST verify auto-levels histogram calibration reproduces RawTherapee-compatible `expcomp`, `black`, `brightness`, `contrast`, `hlcompr`, and `hlcomprthresh` for deterministic synthetic histograms.
- **TST-018**: MUST verify `Color Propagation` and `Inpaint Opposed` selectors produce deterministic RGB float outputs and preserve float-only internal math within the auto-levels stage.
- **TST-019**: MUST verify auto-brightness CLI parsing exposes key-value, white-point, boost, epsilon, and desaturation controls with deterministic defaults and validation.
- **TST-020**: MUST verify auto-brightness clipping proxies use normalized thresholds `1/255` and `254/255` and key auto-selection uses the original base values and boost rules.
- **TST-021**: MUST verify `_parse_run_options` accepts HDR+ knob overrides and rejects invalid HDR+ knob combinations with deterministic parse errors.
- **TST-022**: MUST verify HDR+ scalar proxy mode `rggb` produces deterministic green-weighted scalar conversion from RGB float input.
- **TST-023**: MUST verify HDR+ hierarchical alignment resolves non-zero alternate-frame tile offsets for translated inputs and keeps reference offsets at zero.
- **TST-024**: MUST verify HDR+ temporal weighting and RGB accumulation apply resolved alignment offsets before distance evaluation and tile merge.
- **TST-025**: MUST verify HDR+ merge preserves float internal arithmetic and float input/output boundaries.
- **TST-026**: MUST verify `_apply_static_postprocess_float` preserves float I/O and does not call uint16 adaptation helpers or legacy uint16 static-stage helpers.
- **TST-027**: MUST verify float-domain static postprocess matches legacy gamma, brightness, contrast, and saturation outputs within quantization-only tolerance on deterministic fixtures.
- **TST-028**: MUST verify OpenCV auto-adjust CLI parsing exposes CLAHE-luma enable, strength, clip-limit, and tile-grid controls with deterministic defaults and validation.
- **TST-029**: MUST verify `_apply_validated_auto_adjust_pipeline_opencv` preserves float I/O and executes `blur -> level -> CLAHE-luma -> sigmoid -> vibrance -> high-pass`.
- **TST-030**: MUST verify float-domain OpenCV CLAHE-luma preserves blend semantics and remains within quantization-only deviation from the former uint16 implementation on deterministic fixtures.

## 5. Evidence Matrix

| Requirement ID | Evidence |
|---|---|
| PRJ-001 | `src/dng2jpg/dng2jpg.py::run`, `_build_exposure_multipliers`, and `_extract_bracket_images_float`; excerpt: derives `ev_minus`, `ev_zero`, `ev_plus` multipliers, extracts three normalized RGB float brackets with `output_bps=16`, then merges via selected backend. |
| PRJ-002 | `src/dng2jpg/dng2jpg.py::print_help`, `_parse_run_options`; excerpt: documents and parses exposure, EV-center, backend, postprocess, auto-adjust, and auto-brightness controls. |
| PRJ-003 | `src/dng2jpg/core.py::main`; excerpt: handles `--help`, `--ver`, `--version`, `--upgrade`, `--uninstall`, and conversion dispatch. |
| PRJ-004 | `.github/workflows/release-uvx.yml`; excerpt: semantic tag trigger, build job, attestation, and GitHub release upload flow. |
| PRJ-005 | `scripts/d2j.sh`; excerpt: `exec "${UV_TOOL}" run --project "${BASE_DIR}" python -m dng2jpg "$@"`. |
| CTN-001 | `src/dng2jpg/dng2jpg.py::_is_supported_runtime_os`; excerpt: returns true only on Linux and prints Linux-only error otherwise. |
| CTN-002 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: parses `--hdr-merge` and defaults to `OpenCV` when omitted. |
| CTN-003 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: resolves `--ev` and `--auto-ev <enable|disable>` with deterministic precedence. |
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
| REQ-010 | `src/dng2jpg/dng2jpg.py::_extract_bracket_images_float`; excerpt: calls `rawpy.postprocess(..., output_bps=16)`, normalizes to RGB float `[0,1]`, and returns ordered `ev_minus`, `ev_zero`, `ev_plus` bracket tensors. |
| REQ-011 | `src/dng2jpg/dng2jpg.py::_run_enfuse`, `_run_luminance_hdr_cli`; excerpt: `--compression=lzw`, deterministic luminance args, and `--ldrTiff 16b`. |
| REQ-012 | `src/dng2jpg/dng2jpg.py::_encode_jpg`, `_apply_static_postprocess_float`; excerpt: keeps merge/postprocess/auto-adjust/final-save buffers on normalized RGB float interfaces. |
| REQ-013 | `src/dng2jpg/dng2jpg.py::_encode_jpg`; excerpt: auto-brightness executes before auto-levels and postprocess factors; optional auto-adjust executes before final JPEG save. |
| REQ-014 | `src/dng2jpg/dng2jpg.py::_sync_output_file_timestamps_from_exif`; excerpt: applies `os.utime` when EXIF timestamp exists. |
| REQ-015 | `src/dng2jpg/dng2jpg.py::run`; excerpt: parse/dependency/processing failures return `1`, success returns `0`. |
| REQ-016 | `src/dng2jpg/core.py::_check_online_version`; excerpt: GitHub API check with idle-time cache policy and error/status outputs. |
| REQ-017 | `src/dng2jpg/dng2jpg.py`; excerpt: `PROGRAM = "dng2jpg"` and help usage renders canonical command label without duplicated command token. |
| REQ-018 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: resolves `--ev-zero` and `--auto-zero <enable|disable>` defaults with explicit ignored-parameter output on override. |
| REQ-019 | `src/dng2jpg/dng2jpg.py::_parse_percentage_option`; excerpt: enforces inclusive `0..100` bounds. |
| REQ-020 | `src/dng2jpg/dng2jpg.py::_parse_gamma_option`; excerpt: requires two positive numeric values. |
| REQ-021 | `src/dng2jpg/dng2jpg.py::_parse_jpg_compression_option`; excerpt: enforces inclusive `0..100`. |
| REQ-022 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: rejects luminance options unless `--hdr-merge Luminace-HDR` is selected. |
| REQ-023 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: validates `--hdr-merge` against allowed modes. |
| REQ-024 | `src/dng2jpg/dng2jpg.py::run`; excerpt: routes backend execution from resolved `--hdr-merge` mode. |
| REQ-025 | `src/dng2jpg/dng2jpg.py::_parse_auto_adjust_mode_option`, `_parse_run_options`; excerpt: validates mode values and defaults auto-adjust mode to `OpenCV`. |
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
| REQ-050 | `src/dng2jpg/dng2jpg.py::_apply_auto_brightness_rgb_float`; excerpt: executes the original auto-brightness step order on normalized RGB float I/O with optional luminance-preserving desaturation before final sRGB re-encoding. |
| REQ-051 | `src/dng2jpg/dng2jpg.py::AutoAdjustOptions`, `_apply_validated_auto_adjust_pipeline`, `_apply_validated_auto_adjust_pipeline_opencv`; excerpt: supports both auto-adjust implementations with one validated knob container including OpenCV-only CLAHE-luma controls. |
| REQ-052 | `src/dng2jpg/dng2jpg.py::run`; excerpt: deterministic `print_info` diagnostic lines for runtime selections and computed EV values. |
| REQ-103 | `src/dng2jpg/dng2jpg.py::_analyze_luminance_key`; excerpt: classifies `low-key`/`normal-key`/`high-key` with the original median and percentile thresholds. |
| REQ-104 | `src/dng2jpg/dng2jpg.py::_reinhard_global_tonemap_luminance`, `_apply_auto_brightness_rgb_float`; excerpt: percentile robust `Lwhite` and burn-out compression before RGB scaling. |
| REQ-105 | `src/dng2jpg/dng2jpg.py::_luminance_preserving_desaturate_to_fit`; excerpt: overflow-only luminance-preserving grayscale blending with minimal factor selection. |
| REQ-100 | `src/dng2jpg/dng2jpg.py::_encode_jpg`, `_apply_auto_levels_float`, `_apply_static_postprocess_float`; excerpt: executes auto-levels only when resolved state is `enable`, between auto-brightness and static postprocess. |
| REQ-101 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `_parse_auto_levels_options`; excerpt: parses `--auto-levels <enable|disable>` and validates `--al-*` coupling. |
| REQ-102 | `src/dng2jpg/dng2jpg.py::_parse_auto_levels_hr_method_option`, `_apply_auto_levels_float`; excerpt: validates and executes the full RawTherapee-aligned highlight reconstruction method set. |
| REQ-116 | `src/dng2jpg/dng2jpg.py::AutoLevelsOptions`, `_parse_auto_levels_options`; excerpt: sets parser defaults for clip percentage, gamut clipping, highlight method, and gain threshold. |
| REQ-117 | `src/dng2jpg/dng2jpg.py::_build_autoexp_histogram_rgb_uint16`, `_compute_auto_levels_from_histogram`; excerpt: derives RawTherapee-compatible histogram statistics and clipping points. |
| REQ-118 | `src/dng2jpg/dng2jpg.py::_compute_auto_levels_from_histogram`; excerpt: implements RawTherapee-compatible formulas for `expcomp`, `black`, `brightness`, `contrast`, and highlight-compression outputs. |
| REQ-119 | `src/dng2jpg/dng2jpg.py::_apply_auto_levels_float`; excerpt: maps CLI method names to RawTherapee `Color`/`Coloropp` semantics and applies deterministic RGB-space approximations. |
| REQ-120 | `src/dng2jpg/dng2jpg.py::_clip_auto_levels_out_of_gamut_uint16`, `_apply_auto_levels_float`; excerpt: normalizes overflowing RGB triplets to the uint16 ceiling while preserving channel ratios. |
| REQ-121 | `src/dng2jpg/dng2jpg.py::_analyze_luminance_key`; excerpt: computes `log_avg_lum`, `median_lum`, `p05`, `p95`, `shadow_clip_in`, and `highlight_clip_in` using normalized `1/255` and `254/255` thresholds. |
| REQ-122 | `src/dng2jpg/dng2jpg.py::_choose_auto_key_value`; excerpt: selects `0.09/0.18/0.36`, applies under/over hints, and clamps to `[a_min,a_max]`. |
| REQ-123 | `src/dng2jpg/dng2jpg.py::_apply_validated_auto_adjust_pipeline_opencv`; excerpt: executes OpenCV auto-adjust in the exact order `blur -> level -> CLAHE-luma -> sigmoid -> vibrance -> high-pass`. |
| REQ-124 | `src/dng2jpg/dng2jpg.py::AutoBrightnessOptions`, `_parse_auto_brightness_options`, `print_help`; excerpt: exposes `key_value`, `white_point_percentile`, `a_min`, `a_max`, `max_auto_boost_factor`, and `eps` as CLI-configurable controls. |
| REQ-125 | `src/dng2jpg/dng2jpg.py::AutoAdjustOptions`, `_parse_auto_adjust_options`, `print_help`; excerpt: exposes CLAHE-luma enable, blend strength, clip limit, and tile grid size as OpenCV auto-adjust CLI controls. |
| REQ-135 | `src/dng2jpg/dng2jpg.py::AutoBrightnessOptions`, `_parse_auto_brightness_options`, `print_help`; excerpt: exposes auto-brightness luminance-preserving desaturation toggle without local-contrast controls. |
| REQ-136 | `src/dng2jpg/dng2jpg.py::_apply_clahe_luma_rgb_float`; excerpt: applies CLAHE on float-domain luminance, reconstructs RGB with preserved chroma, and blends with original via configured strength. |
| REQ-137 | `src/dng2jpg/dng2jpg.py::_apply_clahe_luma_rgb_float`; excerpt: keeps OpenCV auto-adjust CLAHE-luma behavior aligned with the former uint16-based local-contrast stage except for quantization removal. |
| REQ-107 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `print_help`; excerpt: parses `--hdr-merge OpenCV` and defaults to `OpenCV` when omitted. |
| REQ-108 | `src/dng2jpg/dng2jpg.py::_run_opencv_hdr_merge`, `_build_ev_times_from_ev_zero_and_delta`; excerpt: executes OpenCV Mertens+Debevec using ordered bracket inputs and EV-derived exposure times. |
| REQ-109 | `src/dng2jpg/dng2jpg.py::_normalize_debevec_hdr_to_unit_range`, `_run_opencv_hdr_merge`; excerpt: applies robust luminance white-point percentile normalization and blends Debevec with Mertens in float domain. |
| REQ-110 | `src/dng2jpg/dng2jpg.py::_run_opencv_hdr_merge`; excerpt: maintains float-domain processing and performs one float-to-uint16 conversion for merged TIFF write. |
| REQ-111 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `print_help`, `run`; excerpt: accepts `--hdr-merge HDR-Plus`, documents backend, and routes execution to HDR+ merge path. |
| REQ-112 | `src/dng2jpg/dng2jpg.py::_order_hdr_plus_reference_paths`, `_hdrplus_build_scalar_proxy_float32`, `_hdrplus_align_layers`, `_hdrplus_box_down2_float32`, `_hdrplus_compute_temporal_weights`, `_hdrplus_merge_temporal_rgb`, `_hdrplus_merge_spatial_rgb`, `_run_hdr_plus_merge`; excerpt: executes source order `scalar proxy -> hierarchical alignment -> box_down2 -> temporal merge -> spatial merge` with `ev_zero` reference. |
| REQ-113 | `src/dng2jpg/dng2jpg.py::_hdrplus_align_layer`, `_hdrplus_align_layers`; excerpt: applies three-level hierarchical tile alignment with `box_down2`, two `gauss_down4` levels, search offsets `[-4,+3]`, and final full-resolution offset lift. |
| REQ-114 | `src/dng2jpg/dng2jpg.py::_hdrplus_compute_temporal_weights`, `_hdrplus_merge_temporal_rgb`; excerpt: applies aligned 16x16 tile L1 weights with `factor=8`, `min_dist=10`, `max_dist=300`, cutoff, and reference-inclusive normalization. |
| REQ-115 | `src/dng2jpg/dng2jpg.py::_hdrplus_merge_spatial_rgb`, `_run_hdr_plus_merge`; excerpt: blends aligned half-overlapped 32x32 tiles with raised-cosine weights and writes RGB `uint16` merged TIFF. |
| REQ-126 | `src/dng2jpg/dng2jpg.py::HdrPlusOptions`, `_parse_hdrplus_options`, `_hdrplus_build_scalar_proxy_float32`; excerpt: adapts RGB bracket TIFFs into deterministic scalar proxy with default `rggb` mode. |
| REQ-127 | `src/dng2jpg/dng2jpg.py::_parse_run_options`, `print_help`, `HdrPlusOptions`; excerpt: exposes HDR+ CLI knobs for proxy, search radius, and temporal weighting. |
| REQ-128 | `src/dng2jpg/dng2jpg.py::HdrPlusOptions`; excerpt: stores source-matching default values for HDR+ proxy, alignment, and temporal weights. |
| REQ-129 | `src/dng2jpg/dng2jpg.py::_run_hdr_plus_merge`, `_hdrplus_align_layers`, `_hdrplus_compute_temporal_weights`, `_hdrplus_merge_temporal_rgb`; excerpt: preserves float internals with `uint16` input/output boundaries. |
| REQ-130 | `src/dng2jpg/dng2jpg.py::_parse_hdrplus_options`, `_parse_run_options`; excerpt: rejects invalid HDR+ knob ranges and inconsistent temporal thresholds. |
| REQ-131 | `src/dng2jpg/dng2jpg.py::run`; excerpt: prints resolved HDR+ proxy, alignment, and temporal knob diagnostics. |
| REQ-132 | `src/dng2jpg/dng2jpg.py::_apply_static_postprocess_float`, `_apply_post_gamma_float`, `_apply_brightness_float`, `_apply_contrast_float`, `_apply_saturation_float`; excerpt: executes static postprocess directly on RGB float tensors without quantized intermediates. |
| REQ-133 | `src/dng2jpg/dng2jpg.py::_encode_jpg`; excerpt: performs the only float-to-uint8 quantization immediately before Pillow JPEG save. |
| REQ-134 | `src/dng2jpg/dng2jpg.py::_apply_post_gamma_float`, `_apply_brightness_float`, `_apply_contrast_float`, `_apply_saturation_float`; excerpt: preserves the legacy transfer equations and parameter semantics in float domain. |
| TST-001 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; branches for exposure precedence, hdr-merge parsing, and deterministic parse failures. |
| TST-002 | `src/dng2jpg/dng2jpg.py::run`; branches for unsupported OS and dependency failures returning `1`. |
| TST-003 | `src/dng2jpg/dng2jpg.py::run`; success branch prints `HDR JPG created: ...` and returns `0`. |
| TST-004 | `src/dng2jpg/dng2jpg.py::_resolve_ev_zero`; safe-range enforcement branch raises on out-of-range EV-zero. |
| TST-005 | `src/dng2jpg/dng2jpg.py::_resolve_ev_value`; adaptive clamp and static EV validity checks. |
| TST-006 | `src/dng2jpg/dng2jpg.py::_run_luminance_hdr_cli`; deterministic argv generation including passthrough. |
| TST-007 | `src/dng2jpg/dng2jpg.py::_extract_dng_exif_payload_and_timestamp`; explicit EXIF datetime tag priority loop. |
| TST-008 | `src/dng2jpg/dng2jpg.py::_refresh_output_jpg_exif_thumbnail_after_save`; orientation handling in `0th` and `1st` IFDs. |
| TST-009 | `.github/workflows/release-uvx.yml`; release job condition depends on `is_master` gate output. |
| TST-010 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; branch checks for `--auto-levels <enable|disable>` coupling and `--al-*` knob validations. |
| TST-011 | `tests/test_uint16_postprocess_pipeline.py::test_apply_auto_brightness_rgb_float_executes_original_stage_order`; verifies float-interface auto-brightness stage order and optional desaturation without CLAHE local contrast. |
| TST-012 | `tests/test_uint16_postprocess_pipeline.py::test_encode_jpg_quantizes_once_at_final_boundary`; verifies one final float-to-uint8 conversion at the JPEG boundary. |
| TST-013 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_hdr_merge_opencv_backend`, `test_parse_run_options_rejects_unknown_hdr_merge_backend`, `test_parse_run_options_defaults_hdr_merge_to_opencv`; validates hdr-merge selection, default, and invalid-value rejection. |
| TST-014 | `tests/test_uint16_postprocess_pipeline.py::test_build_ev_times_from_ev_zero_and_delta_matches_bracket_sequence`; verifies deterministic stop-space EV-time sequence generation. |
| TST-015 | `tests/test_uint16_postprocess_pipeline.py::test_normalize_debevec_hdr_to_unit_range_clamps_to_valid_interval`; verifies Debevec normalization clamps float output to `[0,1]`. |
| TST-016 | `tests/test_uint16_postprocess_pipeline.py::test_parse_auto_levels_options_defaults_match_rawtherapee`; verifies parser default values for clip percentage, gamut clipping, method, and gain threshold. |
| TST-017 | `tests/test_uint16_postprocess_pipeline.py::test_compute_auto_levels_from_histogram_matches_rawtherapee_reference`; verifies RawTherapee-compatible auto-levels numeric outputs for deterministic histograms. |
| TST-018 | `tests/test_uint16_postprocess_pipeline.py::test_apply_auto_levels_color_methods_preserve_uint16_pipeline`; verifies deterministic `Color Propagation` and `Inpaint Opposed` RGB uint16 execution. |
| TST-019 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_remaining_auto_brightness_controls`; verifies auto-brightness parser coverage for surviving key-value, white-point, boost, epsilon, and desaturation controls. |
| TST-020 | `tests/test_uint16_postprocess_pipeline.py::test_analyze_luminance_key_uses_original_thresholds_and_auto_boost_rules`; verifies normalized clipping proxies and key auto-selection rules. |
| TST-021 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_hdrplus_controls`, `test_parse_run_options_rejects_invalid_hdrplus_controls`; verifies HDR+ CLI control parsing and validation. |
| TST-022 | `tests/test_uint16_postprocess_pipeline.py::test_hdrplus_proxy_rggb_matches_green_weighted_scalar`; verifies deterministic `rggb` scalar proxy conversion. |
| TST-023 | `tests/test_uint16_postprocess_pipeline.py::test_hdrplus_align_layers_detects_translated_alternate_frame`; verifies non-zero alternate-frame alignment and zero reference offsets. |
| TST-024 | `tests/test_uint16_postprocess_pipeline.py::test_hdrplus_temporal_merge_uses_alignment_offsets`; verifies resolved alignment offsets affect temporal weighting and RGB accumulation. |
| TST-025 | `tests/test_uint16_postprocess_pipeline.py::test_run_hdr_plus_merge_preserves_float_internal_and_uint16_io`; verifies HDR+ float internals with `uint16` image boundaries. |
| TST-026 | `tests/test_uint16_postprocess_pipeline.py::test_apply_static_postprocess_float_does_not_call_uint16_conversion`; verifies static postprocess avoids uint16 adaptation helpers. |
| TST-027 | `tests/test_uint16_postprocess_pipeline.py::test_apply_static_postprocess_float_matches_legacy_within_quantization_tolerance`; verifies float-domain static postprocess remains within quantization-only deviation from legacy output. |
| TST-028 | `tests/test_uint16_postprocess_pipeline.py::test_parse_run_options_accepts_auto_adjust_clahe_controls`; verifies OpenCV auto-adjust parser coverage for CLAHE-luma controls. |
| TST-029 | `tests/test_uint16_postprocess_pipeline.py::test_apply_validated_auto_adjust_pipeline_opencv_executes_clahe_stage_order`; verifies float-interface OpenCV auto-adjust stage order with inserted CLAHE-luma stage. |
| TST-030 | `tests/test_uint16_postprocess_pipeline.py::test_apply_clahe_luma_rgb_float_matches_uint16_reference_within_quantization_tolerance`; verifies float-domain CLAHE-luma stays within quantization-only deviation from the former uint16 implementation. |
