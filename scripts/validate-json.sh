#!/usr/bin/env bash
#
# Validate ACDP JSON examples and conformance fixtures against the published schemas.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SCHEMA_DIR="${PROJECT_ROOT}/schemas/json"
COMMON_SCHEMA="${SCHEMA_DIR}/acdp-common.schema.json"
DATA_REF_SCHEMA="${SCHEMA_DIR}/acdp-data-ref.schema.json"
CONTEXT_BODY_SCHEMA="${SCHEMA_DIR}/acdp-context-body.schema.json"
REGISTRY_STATE_SCHEMA="${SCHEMA_DIR}/acdp-registry-state.schema.json"
REGISTRY_RECEIPT_SCHEMA="${SCHEMA_DIR}/acdp-registry-receipt.schema.json"
LINEAGE_HEAD_RECEIPT_SCHEMA="${SCHEMA_DIR}/acdp-lineage-head-receipt.schema.json"
CONTEXT_SCHEMA="${SCHEMA_DIR}/acdp-context.schema.json"
PUBLISH_REQUEST_SCHEMA="${SCHEMA_DIR}/acdp-publish-request.schema.json"
PUBLISH_RESPONSE_SCHEMA="${SCHEMA_DIR}/acdp-publish-response.schema.json"
SEARCH_RESPONSE_SCHEMA="${SCHEMA_DIR}/acdp-search-response.schema.json"
CAPABILITIES_SCHEMA="${SCHEMA_DIR}/acdp-capabilities.schema.json"
ERROR_SCHEMA="${SCHEMA_DIR}/acdp-error.schema.json"

REFS=(
    -r "${COMMON_SCHEMA}"
    -r "${DATA_REF_SCHEMA}"
    -r "${CONTEXT_BODY_SCHEMA}"
    -r "${REGISTRY_STATE_SCHEMA}"
    -r "${REGISTRY_RECEIPT_SCHEMA}"
    -r "${LINEAGE_HEAD_RECEIPT_SCHEMA}"
)

CONFORMANCE_DIR="${PROJECT_ROOT}/schemas/conformance"
EXAMPLES_DIR="${PROJECT_ROOT}/examples"

echo "Validating ACDP JSON artifacts..."
echo

if ! command -v ajv >/dev/null 2>&1; then
    echo "Error: ajv-cli is not installed"
    echo "Install with: npm install -g ajv-cli ajv-formats"
    echo "Or run: make install-tools"
    exit 1
fi

TOTAL=0
VALIDATED=0

# Plain JSON syntax check fallback for files that aren't single payloads.
syntax_check() {
    local file="$1"
    if command -v python3 >/dev/null 2>&1; then
        python3 -c "import json,sys;json.load(open(sys.argv[1]))" "$file"
    elif command -v node >/dev/null 2>&1; then
        node -e "JSON.parse(require('fs').readFileSync(process.argv[1],'utf8'))" "$file"
    else
        return 0
    fi
}

# ── Conformance fixtures: syntax-only ────────────────────────────────────────
if [ -d "$CONFORMANCE_DIR" ]; then
    echo "── Conformance fixtures (${CONFORMANCE_DIR}) ──"
    for f in "${CONFORMANCE_DIR}"/*.json; do
        [ -f "$f" ] || continue
        TOTAL=$((TOTAL + 1))
        echo "  $(basename "$f")"
        if syntax_check "$f"; then
            VALIDATED=$((VALIDATED + 1))
            echo "    ✓ Valid JSON"
        else
            echo "    ✗ Invalid JSON"
            exit 1
        fi
    done
    echo
fi

# ── Examples: validate by directory against the matching schema ─────────────
validate_dir_against() {
    local dir="$1"
    local schema="$2"
    local label="$3"
    [ -d "$dir" ] || return 0
    echo "── ${label} examples (${dir}) ──"
    for f in "${dir}"/*.json; do
        [ -f "$f" ] || continue
        TOTAL=$((TOTAL + 1))
        echo "  $(basename "$f")"
        if ajv validate -s "${schema}" "${REFS[@]}" -d "${f}" --spec=draft2020 --strict=false >/dev/null 2>&1; then
            VALIDATED=$((VALIDATED + 1))
            echo "    ✓ Valid"
        else
            echo "    ✗ Invalid against ${label} schema"
            ajv validate -s "${schema}" "${REFS[@]}" -d "${f}" --spec=draft2020 --strict=false || true
            exit 1
        fi
    done
    echo
}

validate_dir_against "${EXAMPLES_DIR}/publish"          "${PUBLISH_REQUEST_SCHEMA}"      "publish-request"
validate_dir_against "${EXAMPLES_DIR}/retrieval"        "${CONTEXT_SCHEMA}"              "context"
validate_dir_against "${EXAMPLES_DIR}/supersession"     "${CONTEXT_SCHEMA}"              "context (supersession)"
validate_dir_against "${EXAMPLES_DIR}/mixed-data-refs"  "${CONTEXT_SCHEMA}"              "context (mixed data refs)"
validate_dir_against "${EXAMPLES_DIR}/visibility"       "${CONTEXT_SCHEMA}"              "context (visibility)"
validate_dir_against "${EXAMPLES_DIR}/capabilities"     "${CAPABILITIES_SCHEMA}"         "capabilities"
validate_dir_against "${EXAMPLES_DIR}/error"            "${ERROR_SCHEMA}"                "error"

# Meta-shape illustrative examples — JSON syntax check only (not single payloads)
syntax_check_dir() {
    local dir="$1"
    local label="$2"
    [ -d "$dir" ] || return 0
    echo "── ${label} examples (${dir}) — syntax check only ──"
    for f in "${dir}"/*.json; do
        [ -f "$f" ] || continue
        TOTAL=$((TOTAL + 1))
        echo "  $(basename "$f")"
        if syntax_check "$f"; then
            VALIDATED=$((VALIDATED + 1))
            echo "    ✓ Valid JSON"
        else
            echo "    ✗ Invalid JSON"
            exit 1
        fi
    done
    echo
}

# multi-step-derivation.json (in examples/lineage) is a tutorial/narrative
# document illustrating a derived_from chain walk. It is NOT a wire-shape
# and does not validate against acdp-context.schema.json. See the file's
# top-level "_note", "description" and "chain" fields.
syntax_check_dir "${EXAMPLES_DIR}/lineage"        "lineage"
syntax_check_dir "${EXAMPLES_DIR}/idempotency"    "idempotency"
syntax_check_dir "${EXAMPLES_DIR}/key-resolution" "key-resolution (DID documents)"

validate_dir_against "${EXAMPLES_DIR}/search"           "${SEARCH_RESPONSE_SCHEMA}"      "search-response"

if [ $TOTAL -eq 0 ]; then
    echo "Warning: No JSON example or fixture files found"
    exit 1
fi

echo "─────────────────────────────────────"
echo "✓ All ${VALIDATED}/${TOTAL} JSON files validated"
