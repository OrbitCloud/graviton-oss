#!/bin/bash

search_and_execute() {
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
        search_and_execute "$dir"
    done
else
    search_and_execute .
fi


printf "\nDone\n"
