## Execution Units Index

## Behavioral Notes (2026-04-13)

- Main-flow color-space contracts are now explicit: pre-merge stages operate on
  camera-linear RGB, while shared postprocess and final-save preparation
  operate on display-referred standard RGB after backend-local merge-gamma or
  equivalent tone-mapped handoff.
- Main-flow boundary operators are now centralized through dedicated helpers for
  bracket clipping, OpenCV radiance high-precision input adaptation,
  high-precision support probing with deterministic fail-fast rejection,
  Mertens `*255.0` rescale, auto-levels entry clip, repeated auto-adjust
  clamps, postprocess exit clip, and final JPEG quantization.
- OpenCV radiance backend now executes one direct float32 Debevec/Robertson
  merge path, rejects unsupported runtimes before any pre-merge `uint8`
  quantization, and emits one explicit `opencv-radiance-path` runtime
  diagnostic.
- Numeric static post-gamma now applies sign-preserving power on finite
  display-referred RGB float payloads, preventing `NaN`/`Inf` on signed
  OpenCV-Tonemap outputs while preserving non-negative backend behavior and
  float-domain boundary separation.
- Standard CLI auto-brightness and auto-white-balance now execute only on the
  pre-bracket linear-base image; `_postprocess(...)` now starts from
  merge-backend output and executes only static postprocess, auto-levels, and
  auto-adjust.
- Auto-white-balance runtime selectors now exclude the dormant
  `white_balance_analysis_source` concept so the option model matches the
  CLI-accepted selector set.
- Float-domain highlight-reconstruction helpers now sanitize non-finite RGB
  inputs locally before method-specific recovery arithmetic.

## Behavioral Notes (2026-04-12)

- EV-dependent multiplier generation is now centralized through
  `_safe_pow2_ev(...)` so all `2**EV` scaling paths reject non-finite
  exponents, overflowed powers, and non-positive/non-finite multipliers with
  deterministic `ValueError` diagnostics.
- Preview luminance normalization now filters non-finite samples before
  percentile extraction and raises deterministic errors when normalized
  statistics become non-finite or no valid samples remain.
- Automatic EV evaluators (`_calculate_ettr_ev(...)`,
  `_calculate_detail_preservation_ev(...)`) now sanitize non-finite inputs
  locally and fall back deterministically to `0.0` when finite scoring is not
  possible.
- Recoverable processing-error aggregation now includes `OverflowError` for
  EV-scaling failure propagation in runtime error handling.

## Behavioral Notes (2026-04-11)

- Float-stage ingress sanitization is now centralized through
  `_sanitize_finite_float_array(...)` and applied by
  `_to_float32_image_array(...)` and
  `_ensure_three_channel_float_array_no_range_adjust(...)` before downstream
  numeric stages.
- Automatic EV planning (`_resolve_auto_ev_delta(...)`) now validates finite
  inputs, rejects all-non-finite base tensors, treats non-finite clipping
  metrics as clipped pixels, and enforces deterministic iteration/span guards to
  prevent non-terminating loops.
- Exposure selector semantics now distinguish omitted `--bracketing`
  (implicit automatic delta solving) from explicit `--bracketing=auto`
  (automatic delta solving that also permits manual `--exposure=<value>`);
  OpenCV-Tonemap still resolves any automatic delta request to fixed `0.1 EV`,
  and static `--bracketing`/`--exposure` values remain quantized to one
  decimal place.
- Auto-brightness now routes low-variance/low-sample luminance through a
  fallback simple Reinhard safeguard while preserving finite-only luminance
  statistics; auto-gamma still falls back deterministically to identity gamma
  when resolved gamma becomes non-finite.
- Auto-levels and validated auto-adjust stages now sanitize non-finite
  luminance/RGB intermediates before histogram indexing, percentiles, HSL,
  sigmoidal mapping, CLAHE, and final stage outputs.

- id: PROC:pipeline-test-runner
  - type: process
  - parent_process: null
  - role: Shell matrix runner invoking `scripts/d2j.sh` across pipeline profiles and deterministic default-stage variants including all auto-white-balance modes.
  - entrypoint_symbols:
    - main(...)
  - defining_files:
    - scripts/test_all_pipeline.sh
- id: THR:PROC:pipeline-test-runner#main-thread
  - type: thread
  - parent_process: PROC:pipeline-test-runner
  - role: Single shell execution thread for input validation, help handling, and case dispatch.
  - entrypoint_symbols:
    - main(...)
    - run_pipeline_case(...)
  - defining_files:
    - scripts/test_all_pipeline.sh
- id: PROC:launcher
  - type: process
  - parent_process: null
  - role: Shell launcher resolving project root and delegating to uv.
  - entrypoint_symbols:
    - script_body(...)
  - defining_files:
    - scripts/d2j.sh
- id: THR:PROC:launcher#main-thread
  - type: thread
  - parent_process: PROC:launcher
  - role: Single shell execution thread for launcher control flow.
  - entrypoint_symbols:
    - script_body(...)
  - defining_files:
    - scripts/d2j.sh
- id: PROC:main
  - type: process
  - parent_process: null
  - role: Python CLI process executing dng2jpg management and conversion flows.
  - entrypoint_symbols:
    - __main__(...)
    - main(...)
  - defining_files:
    - src/dng2jpg/__main__.py
    - src/dng2jpg/core.py
    - src/dng2jpg/dng2jpg.py
    - src/shell_scripts/utils.py
- id: THR:PROC:main#main-thread
  - type: thread
  - parent_process: PROC:main
  - role: Single Python interpreter thread driving CLI parse, merge, and encode pipeline.
  - entrypoint_symbols:
    - __main__(...)
    - main(...)
    - run(...)
  - defining_files:
    - src/dng2jpg/__main__.py
    - src/dng2jpg/core.py
    - src/dng2jpg/dng2jpg.py
    - src/shell_scripts/utils.py
- id: PROC:gha-check-branch
  - type: process
  - parent_process: null
  - role: GitHub Actions job evaluating whether tagged commit belongs to master.
  - entrypoint_symbols:
    - check_branch_job(...)
  - defining_files:
    - .github/workflows/release-uvx.yml
- id: THR:PROC:gha-check-branch#main-thread
  - type: thread
  - parent_process: PROC:gha-check-branch
  - role: Runner shell thread executing checkout and branch containment script.
  - entrypoint_symbols:
    - check_branch_job(...)
  - defining_files:
    - .github/workflows/release-uvx.yml
- id: PROC:gha-build-release
  - type: process
  - parent_process: null
  - role: GitHub Actions job building distributions and publishing release artifacts.
  - entrypoint_symbols:
    - build_release_job(...)
  - defining_files:
    - .github/workflows/release-uvx.yml
- id: THR:PROC:gha-build-release#main-thread
  - type: thread
  - parent_process: PROC:gha-build-release
  - role: Runner shell thread executing build, attestation, changelog, and release steps.
  - entrypoint_symbols:
    - build_release_job(...)
  - defining_files:
    - .github/workflows/release-uvx.yml

## Execution Units

### PROC:pipeline-test-runner
- Entrypoint(s):
  - main(...): parse help-only options, validate DNG input, and dispatch backend plus deterministic default-stage cases including all auto-white-balance modes [scripts/test_all_pipeline.sh]
- Lifecycle/trigger:
  - Triggered when `scripts/test_all_pipeline.sh` is executed.
  - Executes one deterministic pipeline matrix for one input DNG.
  - No explicit threads detected beyond main thread.
- Internal Call-Trace Tree:
  - main(...): parse help-only CLI options, validate paths, and dispatch matrix [scripts/test_all_pipeline.sh]
    - run_pipeline_case(...): execute one profile invocation with deterministic output suffix [scripts/test_all_pipeline.sh]
- External Boundaries:
  - readlink/dirname/basename/tr shell utilities.
  - `scripts/d2j.sh` process invocation.

### THR:PROC:pipeline-test-runner#main-thread
- Entrypoint(s):
  - main(...): shell command sequence for matrix orchestration [scripts/test_all_pipeline.sh]
- Lifecycle/trigger:
  - Starts with pipeline-test-runner process start.
  - Ends after the final matrix invocation exits.
  - Blocking points are per-profile `scripts/d2j.sh` process executions.
- Internal Call-Trace Tree:
  - main(...): validate input and schedule matrix cases [scripts/test_all_pipeline.sh]
    - run_pipeline_case(...): dispatch one backend profile [scripts/test_all_pipeline.sh]
- External Boundaries:
  - filesystem validation and path normalization shell commands.
  - repeated launcher process invocations.

### PROC:launcher
- Entrypoint(s):
  - script_body(...): top-level shell execution from launcher file [scripts/d2j.sh]
- Lifecycle/trigger:
  - Triggered when `scripts/d2j.sh` is executed.
  - Terminates by `exec` handoff to uv runtime command.
  - No explicit threads detected beyond main thread.
- Internal Call-Trace Tree:
  - script_body(...): resolve launcher path, validate git root, then delegate runtime [scripts/d2j.sh]
- External Boundaries:
  - readlink/dirname/basename/date shell utilities.
  - `git -C <base> rev-parse --show-toplevel`.
  - `exec uv run --project <base> python -m dng2jpg`.

### THR:PROC:launcher#main-thread
- Entrypoint(s):
  - script_body(...): shell command sequence for launcher bootstrap [scripts/d2j.sh]
- Lifecycle/trigger:
  - Starts with launcher process start.
  - Ends when `exec` replaces process image.
  - Blocking points are shell command executions.
- Internal Call-Trace Tree:
  - script_body(...): launcher state derivation and delegation [scripts/d2j.sh]
- External Boundaries:
  - filesystem path resolution and git command invocation.
  - uv runtime process replacement.

### PROC:main
- Entrypoint(s):
  - __main__(...): module execution gateway [src/dng2jpg/__main__.py]
  - main(argv): CLI dispatcher and management-command router [src/dng2jpg/core.py]
- Lifecycle/trigger:
  - Triggered by `python -m dng2jpg` (directly or via launcher/uv).
  - Executes one CLI invocation and exits with status code.
  - No explicit threads detected in repository code.
- Internal Call-Trace Tree:
  - main(argv): parse top-level management commands and dispatch conversion [src/dng2jpg/core.py]
    - _check_online_version(force): latest-release check with cache gating and silent same-version outcome [src/dng2jpg/core.py]
      - _should_skip_version_check(force): idle-time cache gate [src/dng2jpg/core.py]
      - _write_version_cache(idle_delay_seconds): persist cache metadata [src/dng2jpg/core.py]
    - _run_management(command): execute upgrade/uninstall subprocess on Linux [src/dng2jpg/core.py]
    - print_help(version): render full help page for CLI options, including the current backend-specific static default summary [src/dng2jpg/dng2jpg.py]
      - _print_help_section(title): section heading emission [src/dng2jpg/dng2jpg.py]
      - _print_help_option(option_label, description, detail_lines): option row emission [src/dng2jpg/dng2jpg.py]
      - _build_two_line_operator_rows(operator_entries): help-table row composition [src/dng2jpg/dng2jpg.py]
      - _print_box_table(headers, rows, header_rows): bordered table rendering [src/dng2jpg/dng2jpg.py]
        - _border(...): border line generation [src/dng2jpg/dng2jpg.py]
        - _line(...): row line generation [src/dng2jpg/dng2jpg.py]
    - run(args): HDR conversion pipeline orchestration [src/dng2jpg/dng2jpg.py]
      - _is_supported_runtime_os(): Linux-only runtime guard [src/dng2jpg/dng2jpg.py]
      - _parse_run_options(args): parse and validate conversion options, defaulting omitted `--bracketing` and `--exposure` to automatic exposure solving, treating explicit `--bracketing=auto` as automatic backend-specific `ev_delta`, rounding static `--bracketing`/`--exposure` values to one decimal place, and allowing `--exposure=<value>` only when bracketing resolves to static mode or explicit auto-delta mode; rejects legacy removed options `--auto-ev`, `--auto-zero`, `--auto-zero-pct` with explicit "Removed option:" diagnostics; defaults omitted `--hdr-merge` to `OpenCV-Tonemap`, defaults omitted xphoto estimation domain to `linear`, and maps `--auto-white-balance=disable` to explicit stage bypass [src/dng2jpg/dng2jpg.py]
        - _parse_opencv_merge_backend_options(...): OpenCV backend option parsing [src/dng2jpg/dng2jpg.py]
        - _parse_post_gamma_auto_options(...): auto post-gamma option parsing [src/dng2jpg/dng2jpg.py]
        - _parse_auto_brightness_options(...): auto-brightness option parsing [src/dng2jpg/dng2jpg.py]
        - _parse_auto_levels_options(...): auto-levels option parsing [src/dng2jpg/dng2jpg.py]
        - _parse_auto_adjust_options(...): auto-adjust option parsing [src/dng2jpg/dng2jpg.py]
        - _parse_hdrplus_options(...): HDR+ option parsing [src/dng2jpg/dng2jpg.py]
        - _parse_opencv_tonemap_backend_options(...): OpenCV tonemap selector/knob parsing for `--opencv-tonemap-*` CLI options [src/dng2jpg/dng2jpg.py]
        - _parse_hdr_merge_option(...): backend selector parsing [src/dng2jpg/dng2jpg.py]
        - _parse_ev_option(...): EV delta parsing [src/dng2jpg/dng2jpg.py]
        - _parse_ev_center_option(...): EV center parsing for `--exposure=<value>` (numeric only; auto sentinel handled inline) [src/dng2jpg/dng2jpg.py]
        - _is_explicit_auto_bracketing_selected(...): explicit `--bracketing=auto` selector detection for reachable auto-delta-only mode [src/dng2jpg/dng2jpg.py]
        - _parse_gamma_option(...): post-gamma numeric parsing [src/dng2jpg/dng2jpg.py]
        - _parse_jpg_compression_option(...): JPG compression parsing [src/dng2jpg/dng2jpg.py]
        - _resolve_default_postprocess(...): backend default postprocess profile resolution keyed by backend variant (`Luminace-HDR`, `OpenCV-Merge`, `OpenCV-Tonemap`, `HDR-Plus`), with `OpenCV-Tonemap drago=(1.0,1.0,1.4,1.0)` and `mantiuk=(0.9,1.0,1.3,1.0)` [src/dng2jpg/dng2jpg.py]
      - _derive_opencv_tonemap_enabled(postprocess_options): backend gate derivation [src/dng2jpg/dng2jpg.py]
      - _print_validated_run_parameters(...): emit structured validated parameter summary grouped by `Input/Output`, `Exposure`, `White Balance`, `HDR Backend`, `Merge Gamma`, `Postprocess`, `Auto-Brightness (AB)`, `Auto-White-Balance (AWB)`, `Auto-Levels`, `Auto-Adjust`, and `Debug`, always printing auto-stage status lines [src/dng2jpg/dng2jpg.py]
      - _build_debug_artifact_context(output_jpg, input_dng, postprocess_options): debug path setup [src/dng2jpg/dng2jpg.py]
      - _collect_missing_external_executables(enable_luminance): external binary checks [src/dng2jpg/dng2jpg.py]
      - _resolve_numpy_dependency(): import NumPy dependency [src/dng2jpg/dng2jpg.py]
      - _resolve_auto_adjust_dependencies(): import OpenCV optional dependency bundle [src/dng2jpg/dng2jpg.py]
      - _load_image_dependencies(): import rawpy/imageio/Pillow modules [src/dng2jpg/dng2jpg.py]
      - _extract_dng_exif_payload_and_timestamp(pil_image_module, input_dng): EXIF payload and timestamps [src/dng2jpg/dng2jpg.py]
        - _read_exif_value(...): read typed EXIF value [src/dng2jpg/dng2jpg.py]
        - _parse_exif_datetime_to_timestamp(datetime_raw): normalize datetime to epoch [src/dng2jpg/dng2jpg.py]
        - _parse_exif_exposure_time_to_seconds(exposure_raw): parse rational exposure duration [src/dng2jpg/dng2jpg.py]
      - _collect_processing_errors(rawpy_module): dynamic recoverable-exception tuple [src/dng2jpg/dng2jpg.py]
      - _extract_source_gamma_info(raw_handle): source gamma evidence extraction [src/dng2jpg/dng2jpg.py]
        - _classify_explicit_source_gamma(raw_handle): metadata gamma classification [src/dng2jpg/dng2jpg.py]
        - _classify_tone_curve_gamma(raw_handle): tone-curve gamma classification [src/dng2jpg/dng2jpg.py]
        - _classify_matrix_hint_gamma(raw_handle): matrix-hint gamma classification [src/dng2jpg/dng2jpg.py]
      - _detect_dng_bits_per_color(raw_handle): sensor bit-depth detection [src/dng2jpg/dng2jpg.py]
      - _validate_supported_bits_per_color(bits_per_color): bit-depth support enforcement [src/dng2jpg/dng2jpg.py]
      - _extract_exif_gamma_tags(input_dng): gamma-tag extraction with fallback [src/dng2jpg/dng2jpg.py]
        - _exiftool_color_space_fallback(input_dng): exiftool fallback query [src/dng2jpg/dng2jpg.py]
      - _resolve_auto_merge_gamma(exif_gamma_tags, source_gamma_info): merge transfer model selection [src/dng2jpg/dng2jpg.py]
      - _extract_base_rgb_linear_float(raw_handle, np_module, raw_white_balance_mode): single RAW linear base extraction [src/dng2jpg/dng2jpg.py]
        - _build_rawpy_neutral_postprocess_kwargs(raw_handle): neutral postprocess kwargs [src/dng2jpg/dng2jpg.py]
        - _extract_sensor_dynamic_range_max(raw_handle, np_module): sensor dynamic-range scaling [src/dng2jpg/dng2jpg.py]
        - _extract_camera_whitebalance_rgb_triplet(raw_handle): camera white-balance extraction [src/dng2jpg/dng2jpg.py]
        - _normalize_white_balance_gains_rgb(...): gain normalization [src/dng2jpg/dng2jpg.py]
        - _apply_normalized_white_balance_to_rgb_float(...): gain application [src/dng2jpg/dng2jpg.py]
      - _apply_auto_brightness_rgb_float(...): optional auto-brightness stage [src/dng2jpg/dng2jpg.py]
        - _compute_bt709_luminance(...): BT.709 linear luminance derivation [src/dng2jpg/dng2jpg.py]
        - _analyze_luminance_key(...): key-distribution statistics and scene-class classification [src/dng2jpg/dng2jpg.py]
        - _choose_auto_key_value(...): automatic key-value resolution with conservative boost/attenuation [src/dng2jpg/dng2jpg.py]
        - _reinhard_global_tonemap_luminance(...): safeguarded Reinhard luminance operator dispatch [src/dng2jpg/dng2jpg.py]
          - _sanitize_finite_float_array(...): finite-safe luminance tensor sanitization [src/dng2jpg/dng2jpg.py]
          - _extract_finite_luminance_samples(...): finite luminance sampling for robust statistics [src/dng2jpg/dng2jpg.py]
          - _should_use_low_variance_auto_brightness_fallback(...): low-variance/low-sample fallback gate [src/dng2jpg/dng2jpg.py]
        - _luminance_preserving_desaturate_to_fit(...): overflow-only luminance-preserving desaturation [src/dng2jpg/dng2jpg.py]
      - _apply_auto_white_balance_stage_float(...): mandatory auto-white-balance stage entry with internal enable-state validation and disabled pass-through path [src/dng2jpg/dng2jpg.py]
        - _estimate_xphoto_white_balance_gains_rgb(...): xphoto mode dispatch with per-algorithm uint16 capability probe [src/dng2jpg/dng2jpg.py]
          - _probe_xphoto_uint16_payload_support(...): runtime uint16 payload probe for selected xphoto algorithm [src/dng2jpg/dng2jpg.py]
          - _resolve_white_balance_xphoto_estimation_domain(...): effective estimation-domain resolution (`linear|srgb|source-auto`) [src/dng2jpg/dng2jpg.py]
          - _prepare_xphoto_estimation_image_rgb_float(...): estimation-domain payload preparation [src/dng2jpg/dng2jpg.py]
          - _extract_white_balance_channel_gains_from_xphoto(...): xphoto estimation payload adaptation and gain extraction [src/dng2jpg/dng2jpg.py]
            - _build_xphoto_analysis_image_rgb_float(...): deterministic real-image payload build with anti-aliased pyramid downsampling [src/dng2jpg/dng2jpg.py]
            - _rescale_xphoto_estimation_payload_rgb_float(...): robust percentile payload rescaling [src/dng2jpg/dng2jpg.py]
              - _resolve_xphoto_estimation_payload_scale(...): robust rescale-factor derivation [src/dng2jpg/dng2jpg.py]
            - _compress_xphoto_estimation_payload_highlights_soft_knee(...): monotonic highlight shoulder compression [src/dng2jpg/dng2jpg.py]
            - _quantize_xphoto_estimation_payload_rgb(...): backend-local quantization (`uint8|uint16`) [src/dng2jpg/dng2jpg.py]
      - _resolve_joint_auto_ev_solution(...): joint auto EV center+delta resolution when automatic `ev_zero` and automatic `ev_delta` are both active for non-OpenCV-Tonemap backends [src/dng2jpg/dng2jpg.py]
        - _calculate_auto_zero_evaluations(...): EV quality measurements with finite-safe heuristics [src/dng2jpg/dng2jpg.py]
          - _calculate_ettr_ev(...): ETTR heuristic with finite-sample filtering and deterministic `0.0` fallback [src/dng2jpg/dng2jpg.py]
          - _calculate_detail_preservation_ev(...): detail heuristic with non-finite sanitization and deterministic `0.0` fallback [src/dng2jpg/dng2jpg.py]
        - _select_ev_zero_candidate(evaluations): EV center selection as signed numeric minimum across `ev_best`, `ev_ettr`, `ev_detail` [src/dng2jpg/dng2jpg.py]
        - _resolve_auto_ev_delta(...): iterative bracket half-span expansion algorithm [src/dng2jpg/dng2jpg.py]
      - _resolve_auto_ev_delta(...): standalone auto EV delta resolution when only automatic `ev_delta` is active and backend is not OpenCV-Tonemap [src/dng2jpg/dng2jpg.py]
      - _resolve_opencv_tonemap_auto_ev_delta(): OpenCV-Tonemap automatic-delta fixed half-span resolver with skip diagnostics [src/dng2jpg/dng2jpg.py]
      - _build_exposure_multipliers(ev_value, ev_zero): EV triplet multipliers with finite-safe exponentiation guard [src/dng2jpg/dng2jpg.py]
        - _safe_pow2_ev(exponent, context): deterministic `2**EV` finite/overflow validator [src/dng2jpg/dng2jpg.py]
      - _extract_bracket_images_float(...): bracket extraction with optional side-bracket bypass for OpenCV-Tonemap [src/dng2jpg/dng2jpg.py]
        - _build_bracket_images_from_linear_base_float(...): synthetic bracket synthesis [src/dng2jpg/dng2jpg.py]
          - _clip_bracket_rgb_unit_interval(...): explicit bracket-contract clipping boundary [src/dng2jpg/dng2jpg.py]
      - _run_luminance_hdr_cli(...): luminance-hdr-cli merge backend [src/dng2jpg/dng2jpg.py]
        - _materialize_bracket_tiffs_from_float(...): temporary TIFF materialization [src/dng2jpg/dng2jpg.py]
        - _order_bracket_paths(bracket_paths): deterministic path ordering [src/dng2jpg/dng2jpg.py]
        - _format_external_command_for_log(command): command log formatting [src/dng2jpg/dng2jpg.py]
      - _run_opencv_merge_backend(...): OpenCV merge backend [src/dng2jpg/dng2jpg.py]
        - _run_opencv_merge_radiance(...): Debevec/Robertson merge path with high-precision-only success contract [src/dng2jpg/dng2jpg.py]
          - _select_opencv_radiance_path_adapters(...): confirm supported high-precision adapter bundle or reject runtime [src/dng2jpg/dng2jpg.py]
            - _probe_opencv_high_precision_radiance_support(...): probe direct float32 radiance merge support [src/dng2jpg/dng2jpg.py]
              - _merge_opencv_radiance_high_precision(...): execute probe-compatible float32 Debevec/Robertson merge [src/dng2jpg/dng2jpg.py]
            - Deterministic invariant: emit `opencv-radiance-path: fail-fast` and raise `RuntimeError` when the probe fails.
          - _print_opencv_radiance_path_diagnostic(...): emit supported radiance-path runtime line [src/dng2jpg/dng2jpg.py]
          - _adapt_opencv_radiance_input_high_precision(...): adapt float32 radiance inputs for merge entry [src/dng2jpg/dng2jpg.py]
          - _estimate_opencv_camera_response(...): dispatch selected response-estimator adapter [src/dng2jpg/dng2jpg.py]
            - _estimate_opencv_camera_response_high_precision(...): return no response for direct float32 merge [src/dng2jpg/dng2jpg.py]
          - _merge_opencv_radiance_high_precision(...): execute direct float32 Debevec/Robertson merge [src/dng2jpg/dng2jpg.py]
          - _normalize_opencv_hdr_to_unit_range(...): backend normalization to shared float contract [src/dng2jpg/dng2jpg.py]
        - _run_opencv_merge_mertens(...): Mertens merge path [src/dng2jpg/dng2jpg.py]
          - _rescale_mertens_fusion_to_display_range(...): explicit `*255.0` exposure-fusion rescale bridge [src/dng2jpg/dng2jpg.py]
          - _normalize_opencv_hdr_to_unit_range(...): backend normalization to shared float contract [src/dng2jpg/dng2jpg.py]
        - _apply_merge_gamma_float(...): backend display-boundary transfer conversion [src/dng2jpg/dng2jpg.py]
      - _run_opencv_tonemap_backend(...): OpenCV tonemap backend [src/dng2jpg/dng2jpg.py]
        - _resolve_opencv_tonemap_gamma_inverse(...): OpenCV tonemap gamma inverse resolution from merge transfer [src/dng2jpg/dng2jpg.py]
        - _apply_merge_gamma_float_no_clip(...): backend display-boundary transfer conversion without clipping [src/dng2jpg/dng2jpg.py]
      - _run_hdr_plus_merge(...): HDR+ merge backend [src/dng2jpg/dng2jpg.py]
        - _hdrplus_build_scalar_proxy_float32(...): scalar proxy generation [src/dng2jpg/dng2jpg.py]
        - _hdrplus_align_layers(...): multilevel tile alignment [src/dng2jpg/dng2jpg.py]
        - _hdrplus_compute_temporal_weights(...): temporal weight computation [src/dng2jpg/dng2jpg.py]
        - _hdrplus_merge_temporal_rgb(...): temporal merge [src/dng2jpg/dng2jpg.py]
        - _hdrplus_merge_spatial_rgb(...): spatial merge [src/dng2jpg/dng2jpg.py]
      - _write_hdr_merge_debug_checkpoints(...): optional stage checkpoint writer [src/dng2jpg/dng2jpg.py]
      - _postprocess(...): post-merge static postprocess, auto-levels, and auto-adjust dispatch without auto-brightness or auto-white-balance re-entry [src/dng2jpg/dng2jpg.py]
        - _prepare_postprocess_entry_rgb_float(...): postprocess entry payload adaptation [src/dng2jpg/dng2jpg.py]
        - _apply_static_postprocess_float(...): gamma/brightness/contrast/saturation stage with sign-preserving numeric post-gamma for signed float backend payloads [src/dng2jpg/dng2jpg.py]
        - _apply_auto_levels_float(...): optional auto-levels stage [src/dng2jpg/dng2jpg.py]
          - _clip_auto_levels_entry_rgb(...): explicit auto-levels entry clip [src/dng2jpg/dng2jpg.py]
        - _apply_auto_adjust_stage_float(...): mandatory auto-adjust stage entry with internal enable-state validation and disabled pass-through path [src/dng2jpg/dng2jpg.py]
          - _apply_validated_auto_adjust_pipeline(...): validated auto-adjust stage implementation for enabled mode [src/dng2jpg/dng2jpg.py]
            - _clip_auto_adjust_stage_rgb(...): repeated auto-adjust clamp boundary [src/dng2jpg/dng2jpg.py]
        - _clip_postprocess_exit_rgb(...): explicit postprocess exit clip [src/dng2jpg/dng2jpg.py]
      - _encode_jpg(...): JPEG encoding [src/dng2jpg/dng2jpg.py]
        - _quantize_final_rgb_uint8(...): final JPEG quantization boundary [src/dng2jpg/dng2jpg.py]
          - _clip_postprocess_exit_rgb(...): final-save float clip before byte quantization [src/dng2jpg/dng2jpg.py]
          - _to_uint8_image_array(...): uint8 conversion [src/dng2jpg/dng2jpg.py]
        - _convert_compression_to_quality(jpg_compression): JPEG quality mapping [src/dng2jpg/dng2jpg.py]
        - _refresh_output_jpg_exif_thumbnail_after_save(...): EXIF thumbnail regeneration [src/dng2jpg/dng2jpg.py]
      - _sync_output_file_timestamps_from_exif(output_jpg, exif_timestamp): timestamp propagation [src/dng2jpg/dng2jpg.py]
        - _set_output_file_timestamps(output_jpg, exif_timestamp): filesystem timestamp write [src/dng2jpg/dng2jpg.py]
- External Boundaries:
  - HTTPS call to GitHub Releases API for version check.
  - Filesystem reads/writes for cache, source DNG, temp artifacts, and output JPG.
  - Dynamic imports of `numpy`, `cv2`, `rawpy`, `imageio`, `PIL`, and optional `piexif`.
  - Subprocess execution for `uv tool`, `exiftool`, and `luminance-hdr-cli`.

### THR:PROC:main#main-thread
- Entrypoint(s):
  - __main__(...): module entrypoint invoking core dispatcher [src/dng2jpg/__main__.py]
- Lifecycle/trigger:
  - Starts when Python process starts.
  - Runs one CLI transaction and exits.
  - No additional internal thread creation detected.
- Internal Call-Trace Tree:
  - __main__(...): module-to-core bridge [src/dng2jpg/__main__.py]
    - main(argv): command dispatcher [src/dng2jpg/core.py]
      - _check_online_version(force): optional release check with silent same-version outcome [src/dng2jpg/core.py]
      - _run_management(command): optional management command [src/dng2jpg/core.py]
      - run(args): conversion pipeline [src/dng2jpg/dng2jpg.py]
        - _parse_run_options(args): CLI option parser defaulting omitted `--hdr-merge` to `OpenCV-Tonemap`, defaulting xphoto estimation domain to `linear`, treating explicit `--bracketing=auto` as automatic backend-specific `ev_delta`, rounding static EV selectors to one decimal place, including explicit `--auto-white-balance=disable` stage bypass mapping, rejecting removed options (`--auto-ev`, `--auto-zero`, `--auto-zero-pct`) with explicit diagnostics, and enforcing that omitted `--bracketing` keeps manual `--exposure=<value>` unreachable [src/dng2jpg/dng2jpg.py]
        - _print_validated_run_parameters(...): structured validated parameter summary after file-path preconditions [src/dng2jpg/dng2jpg.py]
        - _extract_base_rgb_linear_float(...): RAW extraction and WB normalization [src/dng2jpg/dng2jpg.py]
        - _extract_bracket_images_float(...): bracket synthesis with OpenCV-Tonemap side-bracket skip path [src/dng2jpg/dng2jpg.py]
        - _run_luminance_hdr_cli(...) / _run_opencv_merge_backend(...) / _run_opencv_tonemap_backend(...) / _run_hdr_plus_merge(...): backend merge dispatch [src/dng2jpg/dng2jpg.py]
        - _postprocess(...): post-merge postprocess stage dispatch without auto-brightness or auto-white-balance branches [src/dng2jpg/dng2jpg.py]
        - _encode_jpg(...): final JPEG encode stage [src/dng2jpg/dng2jpg.py]
        - _sync_output_file_timestamps_from_exif(...): output timestamp synchronization [src/dng2jpg/dng2jpg.py]
- External Boundaries:
  - Same external boundaries as PROC:main.

### PROC:gha-check-branch
- Entrypoint(s):
  - check_branch_job(...): workflow job execution entry [.github/workflows/release-uvx.yml]
- Lifecycle/trigger:
  - Triggered by release workflow `push tags` or manual `workflow_dispatch`.
  - Executes checkout and git branch-containment script.
  - Emits job output `is_master` and exits.
  - No explicit threads detected beyond main runner thread.
- Internal Call-Trace Tree:
  - check_branch_job(...): GitHub Actions declarative job [.github/workflows/release-uvx.yml]
- External Boundaries:
  - `actions/checkout@v4` action execution.
  - `git fetch` and `git branch -r --contains` shell commands.
  - GitHub-hosted runner environment variables/output channel.

### THR:PROC:gha-check-branch#main-thread
- Entrypoint(s):
  - check_branch_job(...): runner script execution thread [.github/workflows/release-uvx.yml]
- Lifecycle/trigger:
  - Starts with job startup.
  - Ends after writing `is_master` output.
  - No additional internal thread creation detected.
- Internal Call-Trace Tree:
  - check_branch_job(...): sequential action/command execution [.github/workflows/release-uvx.yml]
- External Boundaries:
  - GitHub Actions runtime and git remote communication.

### PROC:gha-build-release
- Entrypoint(s):
  - build_release_job(...): workflow release-build job entry [.github/workflows/release-uvx.yml]
- Lifecycle/trigger:
  - Triggered only when `needs.check-branch.outputs.is_master == 'true'`.
  - Runs checkout, Python+uv setup, distribution build, attestation, changelog generation, and release publish.
  - Exits after release upload completion.
  - No explicit threads detected beyond main runner thread.
- Internal Call-Trace Tree:
  - build_release_job(...): GitHub Actions declarative job [.github/workflows/release-uvx.yml]
- External Boundaries:
  - `actions/checkout@v4`, `actions/setup-python@v5`, `astral-sh/setup-uv@v3`.
  - `uv run --frozen --with build python -m build`.
  - `actions/attest-build-provenance@v1`.
  - `mikepenz/release-changelog-builder-action@v6`.
  - `softprops/action-gh-release@v2`.

### THR:PROC:gha-build-release#main-thread
- Entrypoint(s):
  - build_release_job(...): runner script execution thread [.github/workflows/release-uvx.yml]
- Lifecycle/trigger:
  - Starts with build-release job startup.
  - Ends after release publication step.
  - No additional internal thread creation detected.
- Internal Call-Trace Tree:
  - build_release_job(...): sequential action/command execution [.github/workflows/release-uvx.yml]
- External Boundaries:
  - GitHub Actions runtime, package build backend, and GitHub Release API.

## Communication Edges

- id: EDGE:pipeline-test-runner-to-launcher
  - source: PROC:pipeline-test-runner
  - destination: PROC:launcher
  - mechanism: repeated shell process invocation of `scripts/d2j.sh` per pipeline profile.
  - endpoint_channel: launcher argv handoff (`input.dng`, `output.jpg`, and per-case profile options).
  - payload_data_shape: deterministic per-case CLI vector containing one output-suffix profile identifier and optional stage selector token (including `--auto-white-balance=<mode>` for each supported mode).
  - declaration_files:
    - scripts/test_all_pipeline.sh
    - scripts/d2j.sh
- id: EDGE:launcher-to-main
  - source: PROC:launcher
  - destination: PROC:main
  - mechanism: process replacement + delegated process start (`exec uv run --project ... python -m dng2jpg`).
  - endpoint_channel: CLI argv/environment handoff to Python module entry.
  - payload_data_shape: shell argument vector (`$@`) and inherited process environment.
  - declaration_files:
    - scripts/d2j.sh
    - src/dng2jpg/__main__.py
    - src/dng2jpg/core.py
- id: EDGE:gha-check-branch-to-gha-build-release
  - source: PROC:gha-check-branch
  - destination: PROC:gha-build-release
  - mechanism: GitHub Actions job dependency output propagation.
  - endpoint_channel: `needs.check-branch.outputs.is_master`.
  - payload_data_shape: string boolean (`"true"` or `"false"`) controlling downstream job execution.
  - declaration_files:
    - .github/workflows/release-uvx.yml
