#!/usr/bin/env bash
#
# Validate that all Protocol Buffer schemas compile correctly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROTO_DIR="${PROJECT_ROOT}/schemas/proto"

echo "Validating Protocol Buffer schemas ..."
echo

if ! command -v protoc >/dev/null 2>&1; then
    echo "⚠️  protoc is not installed. Skipping protobuf compilation."
    echo "Install with:"
    echo "  macOS:  brew install protobuf"
    echo "  Ubuntu: sudo apt-get install -y protobuf-compiler"
    echo "Or run: make install-tools"
    exit 0
fi

PROTO_FILES=()
while IFS= read -r -d '' f; do
    PROTO_FILES+=("$f")
done < <(find "${PROTO_DIR}" -type f -name '*.proto' -print0 | sort -z)

if [ ${#PROTO_FILES[@]} -eq 0 ]; then
    echo "No .proto files found under ${PROTO_DIR}"
    exit 1
fi

protoc --proto_path="${PROTO_DIR}" --descriptor_set_out=/dev/null "${PROTO_FILES[@]}"

echo "✓ All canonical protos compile successfully"
echo
echo "─────────────────────────────────────"
echo "✓ All Protocol Buffer schemas are syntactically valid"
