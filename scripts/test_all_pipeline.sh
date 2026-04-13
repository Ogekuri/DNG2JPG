#!/bin/bash
# -*- coding: utf-8 -*-
# VERSION: 0.3.0
# AUTHORS: Ogekuri

set -euo pipefail

###############################################################################
## @brief Emit usage contract for pipeline-matrix execution.
## @details Prints one deterministic usage block including required input DNG
##          argument and help selectors only. Output is consumed for
##          validation diagnostics and explicit help requests.
## @return {None} Writes usage lines to stdout.
## @satisfies REQ-230, REQ-232
###############################################################################
print_usage() {
    cat <<'EOF'
Usage:
  scripts/test_all_pipeline.sh <input.dng> [options]

Options:
  -h, --help                    Show this message.
EOF
}

###############################################################################
## @brief Execute one pipeline-profile conversion case.
## @details Builds one deterministic output JPG path using the input DNG stem
##          and pipeline suffix, then executes `scripts/d2j.sh` with the
##          provided profile options. Any non-zero child exit terminates script
##          execution.
## @param pipeline_suffix {string} Unique profile suffix identifier.
## @param profile_options {array<string>} Optional profile-specific CLI options.
## @return {None} Executes one conversion command.
## @satisfies REQ-231, REQ-233
###############################################################################
run_pipeline_case() {
    local pipeline_suffix="$1"
    shift

    local -a profile_options=("$@")
    local output_jpg

    output_jpg="${INPUT_DNG_DIR}/${INPUT_DNG_STEM}__${pipeline_suffix}.jpg"

    echo "INFO: running pipeline '${pipeline_suffix}'"
    "${D2J_SCRIPT_PATH}" "${INPUT_DNG_PATH}" "${output_jpg}" \
        "${profile_options[@]}"
}

###############################################################################
## @brief Parse input arguments and execute full pipeline matrix.
## @details Validates one existing `.dng` input path, parses only help options,
##          resolves canonical runtime paths, and dispatches all required
##          profile invocations plus deterministic default-pipeline option
##          variants, including one invocation per supported auto-white-balance
##          mode.
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

    while [ "$#" -gt 0 ]; do
        case "$1" in
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

    run_pipeline_case "auto-brightness" "--auto-brightness=enable"

    run_pipeline_case \
        "auto-white-balance-Simple" \
        "--auto-white-balance=Simple"

    run_pipeline_case \
        "auto-white-balance-GrayworldWB" \
        "--auto-white-balance=GrayworldWB"

    run_pipeline_case \
        "auto-white-balance-IA" \
        "--auto-white-balance=IA"

    run_pipeline_case \
        "auto-white-balance-ColorConstancy" \
        "--auto-white-balance=ColorConstancy"

    run_pipeline_case \
        "auto-white-balance-TTL" \
        "--auto-white-balance=TTL"

    run_pipeline_case "auto-levels" "--auto-levels=enable"

    run_pipeline_case "auto-adjust" "--auto-adjust=enable"

    return 0
}

main "$@"
