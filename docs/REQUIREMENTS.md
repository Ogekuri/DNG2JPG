---
title: "DNG2JPG Requirements"
description: Software requirements specification derived from implemented behavior
version: "0.1.0"
date: "2026-03-29"
author: "GitHub Copilot CLI (req-create)"
scope:
  paths:
    - "src/**/*.py"
    - ".github/workflows/*.yml"
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
This SRS captures implemented behavior of the Python CLI conversion pipeline in `src/dng2jpg/` and release automation behavior in `.github/workflows/release-uvx.yml`.

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
- `uv` CLI is used by management/install flows (`src/dng2jpg/core.py`) and release build workflow (`.github/workflows/release-uvx.yml`).
- `enfuse`, `luminance-hdr-cli`, and ImageMagick (`magick` or `convert`) are runtime external executables resolved in `src/dng2jpg/dng2jpg.py`.

### 1.6 Unit Test Coverage Summary
No unit test files were identified under `tests/` during this analysis snapshot; therefore, no unit-test-derived behavioral evidence was available.

### 1.7 Performance Optimization Evidence
Explicit optimization patterns are implemented in the OpenCV pipeline using vectorized NumPy operations (for example `_selective_blur_contrast_gated_vectorized` and related array-domain transforms in `src/dng2jpg/dng2jpg.py`).

## 2. Project Requirements

### 2.1 Project Functions
- **PRJ-001**: MUST convert one input DNG into one output JPG using three synthetic RAW exposure brackets and one selected HDR merge backend.
- **PRJ-002**: MUST expose a CLI with options for exposure mode, EV center mode, postprocess controls, auto-brightness, auto-adjust, and backend selection.
- **PRJ-003**: MUST expose management commands for help, version, upgrade, and uninstall through the package entrypoint dispatcher.
- **PRJ-004**: MUST support release artifact publication through a GitHub Actions workflow triggered by semantic-version tags.

### 2.2 Project Constraints
- **CTN-001**: MUST execute conversion only on Linux runtime and reject unsupported operating systems with explicit error output.
- **CTN-002**: MUST require exactly one backend selector between `--enable-enfuse` and `--enable-luminance`.
- **CTN-003**: MUST require exactly one exposure selector between `--ev` and `--auto-ev`.
- **CTN-004**: MUST require `.dng` input extension, existing input file, and existing output parent directory.
- **CTN-005**: MUST fail when required Python modules or required backend executables for enabled features are unavailable.

## 3. Requirements

### 3.1 Design and Implementation
- **DES-001**: MUST parse CLI arguments by deterministic token scanning supporting both `--option value` and `--option=value` syntaxes.
- **DES-002**: MUST model runtime options with immutable dataclasses `AutoAdjustOptions`, `AutoBrightnessOptions`, `PostprocessOptions`, `LuminanceOptions`, and `AutoEvInputs`.
- **DES-003**: MUST derive supported EV and EV-zero quantized values from detected DNG bit depth using `0.25` EV step constraints.
- **DES-004**: MUST isolate intermediate processing artifacts in temporary directories and cleanup automatically after command completion.
- **DES-005**: MUST preserve source EXIF payload into output JPEG and refresh EXIF thumbnail/orientation metadata when EXIF payload exists.
- **DES-006**: MUST resolve backend-specific default postprocess factors based on selected backend and luminance tone-mapping operator.

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
- **REQ-012**: MUST encode final JPEG with configurable post-gamma, brightness, contrast, saturation, and JPEG compression mapping.
- **REQ-013**: MUST execute optional auto-brightness and optional auto-adjust stage (`ImageMagick` or `OpenCV`) before final JPEG write when configured.
- **REQ-014**: MUST synchronize output file timestamps from EXIF datetime when EXIF datetime metadata is available.
- **REQ-015**: MUST return `1` on parse, validation, dependency, and processing errors, and return `0` on successful processing.
- **REQ-016**: MUST execute GitHub latest-release version checks with an idle-time cache file and print version status or check errors.
- **REQ-017**: MUST render conversion usage prefix from internal constant `PROGRAM="shellscripts"`, which can differ from installed command names.

## 4. Test Requirements

- **TST-001**: MUST verify `_parse_run_options` rejects missing or simultaneous exposure/backend selectors and returns `None` with deterministic error output.
- **TST-002**: MUST verify `run` returns `1` for unsupported runtime OS, missing external executables, and missing Python dependencies.
- **TST-003**: MUST verify successful `run` execution returns `0`, writes output JPG, and emits success message `HDR JPG created: <output>`.

## 5. Evidence Matrix

| Requirement ID | Evidence |
|---|---|
| PRJ-001 | `src/dng2jpg/dng2jpg.py::run`, `_build_exposure_multipliers`, `_write_bracket_images`, `_run_enfuse`, `_run_luminance_hdr_cli`; excerpt: "three synthetic exposures (`ev_zero-ev`, `ev_zero`, `ev_zero+ev`)". |
| PRJ-002 | `src/dng2jpg/dng2jpg.py::print_help`, `_parse_run_options`; excerpt: usage includes `--ev`, `--auto-ev`, `--auto-zero`, `--auto-adjust`, backend selectors. |
| PRJ-003 | `src/dng2jpg/core.py::main`; excerpt: handles `--help`, `--ver/--version`, `--upgrade`, `--uninstall`. |
| PRJ-004 | `.github/workflows/release-uvx.yml`; excerpt: trigger on `push tags vX.Y.Z`, build `dist/*`, create GitHub Release with uploaded assets. |
| CTN-001 | `src/dng2jpg/dng2jpg.py::_is_supported_runtime_os`; excerpt: "if runtime_os == 'linux': return True", otherwise prints Linux-only error. |
| CTN-002 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: "Exactly one backend selector is required". |
| CTN-003 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: "Exactly one exposure selector is required". |
| CTN-004 | `src/dng2jpg/dng2jpg.py::run`; excerpt: validates `.dng`, input existence, and output directory existence. |
| CTN-005 | `src/dng2jpg/dng2jpg.py::run`, `_load_image_dependencies`, `_resolve_auto_adjust_opencv_dependencies`, `_resolve_imagemagick_command`; excerpts: missing dependency errors and early return `1`. |
| DES-001 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: iterative `while idx < len(args)` parser with branch-per-token handling. |
| DES-002 | `src/dng2jpg/dng2jpg.py` dataclasses: `AutoAdjustOptions`, `AutoBrightnessOptions`, `PostprocessOptions`, `LuminanceOptions`, `AutoEvInputs`. |
| DES-003 | `src/dng2jpg/dng2jpg.py::_detect_dng_bits_per_color`, `_derive_supported_ev_values`, `_derive_supported_ev_zero_values`; excerpt: `EV_STEP = 0.25`. |
| DES-004 | `src/dng2jpg/dng2jpg.py::run`, `_encode_jpg`; excerpt: `with tempfile.TemporaryDirectory(...)` for main and auto-adjust paths. |
| DES-005 | `src/dng2jpg/dng2jpg.py::_extract_dng_exif_payload_and_timestamp`, `_encode_jpg`, `_refresh_output_jpg_exif_thumbnail_after_save`. |
| DES-006 | `src/dng2jpg/dng2jpg.py::_resolve_default_postprocess`; excerpt: defaults vary for enfuse, `reinhard02`, and `mantiuk08`. |
| REQ-001 | `src/dng2jpg/core.py::main`; excerpt: if no args, `ported.print_help(__version__)` and return `0`. |
| REQ-002 | `src/dng2jpg/core.py::main`; excerpt: top-level `--help` prints management help then conversion help. |
| REQ-003 | `src/dng2jpg/core.py::main`; excerpt: top-level `--ver`/`--version` prints `__version__` and returns `0`. |
| REQ-004 | `src/dng2jpg/core.py::main`, `_run_management`; excerpt: `uv tool install ... --force --from git+https://github.com/...` and `uv tool uninstall`. |
| REQ-005 | `src/dng2jpg/core.py::_run_management`; excerpt: non-Linux prints "Run it manually" plus command and returns `0`. |
| REQ-006 | `src/dng2jpg/dng2jpg.py::_parse_run_options` and parse helpers; excerpts: "Unknown option", "Missing value", and option-specific validation errors. |
| REQ-007 | `src/dng2jpg/dng2jpg.py::_parse_run_options`; excerpt: knob gating errors for `--aa-*` and `--ab-*` without enabling flags. |
| REQ-008 | `src/dng2jpg/dng2jpg.py::_resolve_ev_zero`; excerpt: auto mode uses preview stats and validates safe range. |
| REQ-009 | `src/dng2jpg/dng2jpg.py::_resolve_ev_value`, `_compute_auto_ev_value_from_stats`; excerpt: adaptive EV from preview percentiles with clamping. |
| REQ-010 | `src/dng2jpg/dng2jpg.py::_write_bracket_images`; excerpt: writes `ev_minus.tif`, `ev_zero.tif`, `ev_plus.tif` with `output_bps=16`. |
| REQ-011 | `src/dng2jpg/dng2jpg.py::_run_enfuse`, `_run_luminance_hdr_cli`; excerpts: `--compression=lzw`, `luminance-hdr-cli ... --ldrTiff 16b`. |
| REQ-012 | `src/dng2jpg/dng2jpg.py::_encode_jpg`; excerpt: applies gamma LUT, brightness/contrast/saturation, then JPEG save with mapped quality. |
| REQ-013 | `src/dng2jpg/dng2jpg.py::_encode_jpg`; excerpt: conditional auto-adjust `ImageMagick` or `OpenCV` pre-final-encode flow. |
| REQ-014 | `src/dng2jpg/dng2jpg.py::_sync_output_file_timestamps_from_exif`; excerpt: calls `os.utime` when EXIF timestamp exists. |
| REQ-015 | `src/dng2jpg/dng2jpg.py::run`; excerpt: parse/dependency/processing failures return `1`; success prints and returns `0`. |
| REQ-016 | `src/dng2jpg/core.py::_check_online_version`, `_should_skip_version_check`, `_write_version_cache`; excerpt: GitHub releases API with cache file. |
| REQ-017 | `src/dng2jpg/dng2jpg.py`; excerpt: `PROGRAM = "shellscripts"` and usage line `Usage: {PROGRAM} dng2jpg ...`. |
| TST-001 | Directly testable via `src/dng2jpg/dng2jpg.py::_parse_run_options` branch constraints and deterministic parse error messages. |
| TST-002 | Directly testable via `src/dng2jpg/dng2jpg.py::_is_supported_runtime_os`, dependency resolvers, and guarded branches in `run`. |
| TST-003 | Directly testable via `src/dng2jpg/dng2jpg.py::run` success path and `print_success(f"HDR JPG created: {output_jpg}")`. |

