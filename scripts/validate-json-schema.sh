#!/usr/bin/env bash
#
# Validate that all ACDP JSON Schemas are themselves valid (meta-validation).
# Resolves cross-file $refs by registering every other schema in the directory
# as a reference (-r) before compiling each one.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCHEMA_DIR="${PROJECT_ROOT}/schemas/json"

echo "Meta-validating JSON Schemas under ${SCHEMA_DIR} ..."
echo

if ! command -v ajv >/dev/null 2>&1; then
    echo "Error: ajv-cli is not installed"
    echo "Install with: npm install -g ajv-cli ajv-formats"
    echo "Or run: make install-tools"
    exit 1
fi

# Collect every schema; we'll pass all-others as -r when compiling each one.
ALL_SCHEMAS=()
for f in "${SCHEMA_DIR}"/*.schema.json; do
    [ -f "$f" ] || continue
    ALL_SCHEMAS+=("$f")
done

if [ ${#ALL_SCHEMAS[@]} -eq 0 ]; then
    echo "Warning: No JSON Schema files found in ${SCHEMA_DIR}"
    exit 1
fi

TOTAL=0
VALIDATED=0

for target in "${ALL_SCHEMAS[@]}"; do
    TOTAL=$((TOTAL + 1))
    echo "Validating: $(basename "$target")"

    # Build -r flags for every OTHER schema.
    REFS=()
    for ref in "${ALL_SCHEMAS[@]}"; do
        if [ "$ref" != "$target" ]; then
            REFS+=( -r "$ref" )
        fi
    done

    if ajv compile -s "$target" "${REFS[@]}" --spec=draft2020 --strict=false; then
        VALIDATED=$((VALIDATED + 1))
        echo "  ✓ Valid"
    else
        echo "  ✗ Invalid"
        exit 1
    fi
    echo
done

echo "─────────────────────────────────────"
echo "✓ All ${VALIDATED}/${TOTAL} JSON Schemas are valid"
