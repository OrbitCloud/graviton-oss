#!/bin/bash

# Recursively searches for Pulumi projects and stacks
#
# Runs:
# pulumi pre --expect-no-changes
#
# Reports back whether there are any errors or pending changes in stacks.
#
# Usage
# chmod +x drift_detect.sh
# ./drift_detect.sh <target directory> (defaults to current directory)

pulumi_recursive_drift_detect() {
    while IFS= read -r line; do
        directories+=("$line")
    done < <(find "$1" -type f -name "Pulumi.*.yaml" -exec dirname {} \; | sort -u)

    if [ ${#directories[@]} -eq 0 ]; then
        echo "No directories found with Pulumi stack configs."
    else
        echo "Checking unexpected changes in stacks"
        for dir in "${directories[@]}"; do
            stacks=()
            while IFS= read -r file; do
                stack=$(echo "$file" | sed -n 's/.*Pulumi\.\(.*\)\.yaml/\1/p')
                stacks+=("$stack")
            done < <(find "$dir" -type f -name "Pulumi.*.yaml")

            printf '\nPulumi project \e[4m%s\e[24m' "${dir#./}"

            for stack in "${stacks[@]}"; do
                printf '\n   Stack: \e[3;4;33m%s\e[0m' "${stack}"
                pulumi_pre_command=("pulumi" "pre" "--cwd" "$dir" "--expect-no-changes" "-s" "${stack}")
                output=$("${pulumi_pre_command[@]}" 2>&1 >/dev/null)
                exit_code=$?
                if [ $exit_code -ne 0 ]; then
                    printf '      ❌ %s' "${output/error:/}"
                else
                    printf '      ✅ No changes detected'
                fi
            done
            printf '\n'
        done
    fi
}

# If arguments are passed, use them as directories to search
if [ $# -gt 0 ]; then
    for dir in "$@"; do
        pulumi_recursive_drift_detect "$dir"
    done
else
    pulumi_recursive_drift_detect .
fi


printf "\nDone\n"
