#!/bin/bash
# -*- coding: utf-8 -*-
# VERSION: 0.1.0
# AUTHORS: Ogekuri

set -euo pipefail

###############################################################################
## @brief Emit usage contract for pipeline-matrix execution.
## @details Prints one deterministic usage block including required input DNG
##          argument and optional stage toggles. Output is consumed for
##          validation diagnostics and explicit help requests.
## @return {None} Writes usage lines to stdout.
## @satisfies REQ-230
###############################################################################
print_usage() {
    cat <<'EOF'
Usage:
  scripts/test_all_pipeline.sh <input.dng> [options]

Options:
  --auto-brightness             Append --auto-brightness=enable.
  --auto-white-balance          Append --auto-white-balance=Simple.
  --auto-white-balance=<mode>   Append --auto-white-balance=<mode>.
  --auto-levels                 Append --auto-levels=enable.
  --auto-adjust                 Append --auto-adjust=enable.
  -h, --help                    Show this message.
EOF
}

###############################################################################
## @brief Normalize arbitrary token text for filename suffix usage.
## @details Converts uppercase characters to lowercase and replaces every
##          non `[a-z0-9._-]` character with `-` to maintain deterministic
##          cross-platform-safe suffix composition.
## @param raw_token {string} Raw token candidate.
## @return {string} Normalized token constrained to filename-safe characters.
## @satisfies REQ-233
###############################################################################
sanitize_suffix_token() {
    local raw_token="$1"
    local lower_token
    lower_token=$(printf '%s' "${raw_token}" | tr '[:upper:]' '[:lower:]')
    printf '%s' "${lower_token}" | tr -c 'a-z0-9._-' '-'
}

###############################################################################
## @brief Append enabled stage options and stage suffix tokens.
## @details Reads global toggle state and appends the corresponding enabling
##          CLI flags to the provided options array reference, while appending
##          deterministic short tokens to the provided suffix array reference.
## @param options_ref {name-reference} Mutable array receiving CLI options.
## @param suffix_ref {name-reference} Mutable array receiving suffix fragments.
## @return {None} Mutates referenced arrays in place.
## @satisfies REQ-232, REQ-233
###############################################################################
append_common_stage_options() {
    local -n options_ref="$1"
    local -n suffix_ref="$2"
    local normalized_wb_mode

    if [ "${AUTO_BRIGHTNESS_ENABLED}" = "true" ]; then
        options_ref+=("--auto-brightness=enable")
        suffix_ref+=("ab")
    fi

    if [ "${AUTO_WHITE_BALANCE_ENABLED}" = "true" ]; then
        options_ref+=("--auto-white-balance=${AUTO_WHITE_BALANCE_MODE}")
        normalized_wb_mode=$(sanitize_suffix_token "${AUTO_WHITE_BALANCE_MODE}")
        suffix_ref+=("awb-${normalized_wb_mode}")
    fi

    if [ "${AUTO_LEVELS_ENABLED}" = "true" ]; then
        options_ref+=("--auto-levels=enable")
        suffix_ref+=("al")
    fi

    if [ "${AUTO_ADJUST_ENABLED}" = "true" ]; then
        options_ref+=("--auto-adjust=enable")
        suffix_ref+=("aa")
    fi
}

###############################################################################
## @brief Execute one pipeline-profile conversion case.
## @details Builds one deterministic output JPG path using the input DNG stem,
##          pipeline suffix, and optional stage suffix tokens; then executes
##          `scripts/d2j.sh` with profile-specific options and optional stage
##          toggles. Any non-zero child exit terminates script execution.
## @param pipeline_suffix {string} Unique profile suffix identifier.
## @param profile_options {array<string>} Optional profile-specific CLI options.
## @return {None} Executes one conversion command.
## @satisfies REQ-231, REQ-232, REQ-233
###############################################################################
run_pipeline_case() {
    local pipeline_suffix="$1"
    shift

    local -a profile_options=("$@")
    local -a stage_options=()
    local -a stage_suffix_tokens=()
    local stage_suffix_joined
    local effective_suffix
    local output_jpg

    append_common_stage_options stage_options stage_suffix_tokens

    effective_suffix="${pipeline_suffix}"
    if [ "${#stage_suffix_tokens[@]}" -gt 0 ]; then
        stage_suffix_joined=$(IFS='-'; printf '%s' "${stage_suffix_tokens[*]}")
        effective_suffix="${pipeline_suffix}--${stage_suffix_joined}"
    fi

    output_jpg="${INPUT_DNG_DIR}/${INPUT_DNG_STEM}__${effective_suffix}.jpg"

    echo "INFO: running pipeline '${effective_suffix}'"
    "${D2J_SCRIPT_PATH}" "${INPUT_DNG_PATH}" "${output_jpg}" \
        "${profile_options[@]}" "${stage_options[@]}"
}

###############################################################################
## @brief Parse input arguments and execute full pipeline matrix.
## @details Validates one existing `.dng` input path, parses optional stage
##          toggles, resolves canonical runtime paths, and dispatches all
##          required profile invocations plus one default invocation.
## @return {int} Returns `0` on full matrix success; returns `1` on validation
##               or parsing failures.
## @satisfies REQ-230, REQ-231, REQ-232, REQ-233
###############################################################################
main() {
    local input_dng_argument
    local input_extension

    if [ "$#" -lt 1 ]; then
        echo "ERROR: Missing <input.dng> argument."
        print_usage
        return 1
    fi

    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        print_usage
        return 0
    fi

    input_dng_argument="$1"
    shift

    AUTO_BRIGHTNESS_ENABLED="false"
    AUTO_WHITE_BALANCE_ENABLED="false"
    AUTO_WHITE_BALANCE_MODE="Simple"
    AUTO_LEVELS_ENABLED="false"
    AUTO_ADJUST_ENABLED="false"

    while [ "$#" -gt 0 ]; do
        case "$1" in
            --auto-brightness)
                AUTO_BRIGHTNESS_ENABLED="true"
                ;;
            --auto-white-balance)
                AUTO_WHITE_BALANCE_ENABLED="true"
                AUTO_WHITE_BALANCE_MODE="Simple"
                ;;
            --auto-white-balance=*)
                AUTO_WHITE_BALANCE_ENABLED="true"
                AUTO_WHITE_BALANCE_MODE="${1#*=}"
                if [ -z "${AUTO_WHITE_BALANCE_MODE}" ]; then
                    echo "ERROR: --auto-white-balance requires a non-empty mode."
                    return 1
                fi
                ;;
            --auto-levels)
                AUTO_LEVELS_ENABLED="true"
                ;;
            --auto-adjust)
                AUTO_ADJUST_ENABLED="true"
                ;;
            -h|--help)
                print_usage
                return 0
                ;;
            *)
                echo "ERROR: Unknown option: $1"
                print_usage
                return 1
                ;;
        esac
        shift
    done

    INPUT_DNG_PATH=$(readlink -f -- "${input_dng_argument}")
    if [ ! -f "${INPUT_DNG_PATH}" ]; then
        echo "ERROR: Input DNG file not found: ${input_dng_argument}"
        return 1
    fi

    input_extension="${INPUT_DNG_PATH##*.}"
    input_extension=$(printf '%s' "${input_extension}" | tr '[:upper:]' '[:lower:]')
    if [ "${input_extension}" != "dng" ]; then
        echo "ERROR: Input path must end with .dng: ${INPUT_DNG_PATH}"
        return 1
    fi

    INPUT_DNG_DIR=$(dirname "${INPUT_DNG_PATH}")
    INPUT_DNG_FILENAME=$(basename "${INPUT_DNG_PATH}")
    INPUT_DNG_STEM="${INPUT_DNG_FILENAME%.*}"

    SCRIPT_FULL_PATH=$(readlink -f -- "$0")
    SCRIPT_DIR_PATH=$(dirname "${SCRIPT_FULL_PATH}")
    REPOSITORY_ROOT_PATH=$(dirname "${SCRIPT_DIR_PATH}")
    D2J_SCRIPT_PATH="${REPOSITORY_ROOT_PATH}/scripts/d2j.sh"

    if [ ! -x "${D2J_SCRIPT_PATH}" ]; then
        echo "ERROR: d2j launcher not found or not executable: ${D2J_SCRIPT_PATH}"
        return 1
    fi

    run_pipeline_case \
        "luminace-hdr-reinhard02" \
        "--hdr-merge=Luminace-HDR" \
        "--luminance-tmo=reinhard02"

    run_pipeline_case \
        "luminace-hdr-mantiuk08" \
        "--hdr-merge=Luminace-HDR" \
        "--luminance-tmo=mantiuk08"

    run_pipeline_case \
        "opencv-merge-debevec" \
        "--hdr-merge=OpenCV-Merge" \
        "--opencv-merge-algorithm=Debevec"

    run_pipeline_case \
        "opencv-merge-robertson" \
        "--hdr-merge=OpenCV-Merge" \
        "--opencv-merge-algorithm=Robertson"

    run_pipeline_case \
        "opencv-merge-mertens" \
        "--hdr-merge=OpenCV-Merge" \
        "--opencv-merge-algorithm=Mertens"

    run_pipeline_case \
        "opencv-tonemap-drago" \
        "--hdr-merge=OpenCV-Tonemap" \
        "--opencv-tonemap-algorithm=drago"

    run_pipeline_case \
        "opencv-tonemap-reinhard" \
        "--hdr-merge=OpenCV-Tonemap" \
        "--opencv-tonemap-algorithm=reinhard"

    run_pipeline_case \
        "opencv-tonemap-mantiuk" \
        "--hdr-merge=OpenCV-Tonemap" \
        "--opencv-tonemap-algorithm=mantiuk"

    run_pipeline_case "hdr-plus" "--hdr-merge=HDR-Plus"

    run_pipeline_case "default-opencv-tonemap-reinhard"

    return 0
}

main "$@"
