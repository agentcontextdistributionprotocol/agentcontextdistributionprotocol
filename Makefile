.PHONY: help validate validate-all proto-lint proto-compile proto-gen-all \
	json-validate json-schema-validate clean install-tools \
	gen-go gen-python gen-java gen-csharp gen-js docs

PROTO_SRC := schemas/proto
PROTO_FILES := acdp/v1/common.proto acdp/v1/context.proto acdp/v1/publish.proto acdp/v1/discovery.proto acdp/v1/capabilities.proto acdp/v1/error.proto

# ── Default ───────────────────────────────────────────────────────────────────

help:
	@echo "ACDP Development Commands"
	@echo
	@echo "Validation:"
	@echo "  make validate              Run all validations"
	@echo "  make json-schema-validate  Validate JSON Schema itself"
	@echo "  make json-validate         Validate JSON examples / fixtures against schemas"
	@echo "  make proto-lint            Lint Protocol Buffer schemas"
	@echo "  make proto-compile         Compile Protocol Buffer schemas (validation)"
	@echo
	@echo "Code generation (per-language into packages/):"
	@echo "  make gen-go                Generate Go into packages/proto-go/"
	@echo "  make gen-python            Generate Python into packages/proto-python/"
	@echo "  make gen-java              Generate Java into packages/proto-java/"
	@echo "  make gen-csharp            Generate C# into packages/proto-csharp/"
	@echo "  make gen-js                Generate JavaScript into packages/proto-npm/"
	@echo "  make proto-gen-all         Generate all languages into packages/"
	@echo
	@echo "Docs:"
	@echo "  make docs                  Print the docs reading order"
	@echo
	@echo "Utilities:"
	@echo "  make clean                 Remove generated files"
	@echo "  make install-tools         Install required development tools"

# ── Validation ────────────────────────────────────────────────────────────────

validate: json-schema-validate json-validate proto-lint proto-compile
	@echo "✓ All validations passed"

validate-all: validate proto-gen-all
	@echo "✓ All validations and code generation completed"

json-schema-validate:
	@echo "Validating JSON Schemas (meta-validation)..."
	@./scripts/validate-json-schema.sh

json-validate:
	@echo "Validating JSON examples and conformance fixtures..."
	@./scripts/validate-json.sh

proto-lint:
	@echo "Linting Protocol Buffers..."
	@if command -v buf >/dev/null 2>&1; then \
		buf lint; \
	else \
		echo "⚠️  buf not installed. Skipping protobuf linting."; \
		echo "   Install buf with 'make install-tools' or see https://buf.build/docs/installation"; \
	fi

proto-compile:
	@echo "Compiling Protocol Buffers..."
	@./scripts/validate-proto.sh

# ── Code generation ───────────────────────────────────────────────────────────

gen-go:
	@echo "Generating Go..."
	@buf generate --template buf/buf.gen.go.yaml
	@echo "✓ Go code in packages/proto-go/"

gen-python:
	@echo "Generating Python (via grpc_tools.protoc)..."
	@mkdir -p packages/proto-python/src
	@python -m grpc_tools.protoc \
		-I$(PROTO_SRC) \
		--python_out=packages/proto-python/src \
		--grpc_python_out=packages/proto-python/src \
		$(PROTO_FILES)
	@echo "✓ Python code in packages/proto-python/src/"

gen-java:
	@echo "Generating Java..."
	@buf generate --template buf/buf.gen.java.yaml
	@echo "✓ Java code in packages/proto-java/src/"

gen-csharp:
	@echo "Generating C#..."
	@buf generate --template buf/buf.gen.csharp.yaml
	@echo "✓ C# code in packages/proto-csharp/"

gen-js:
	@echo "Generating JavaScript..."
	@buf generate --template buf/buf.gen.js.yaml
	@echo "✓ JS code in packages/proto-npm/generated/"

proto-gen-all: gen-go gen-python gen-java gen-csharp gen-js
	@echo "✓ All languages generated into packages/"

# ── Docs ─────────────────────────────────────────────────────────────────────

docs:
	@echo "ACDP reading order:"
	@echo "  1. README.md"
	@echo "  2. manifesto/manifesto.md"
	@echo "  3. rfcs/RFC-ACDP-0001-core.md"
	@echo "  4. rfcs/RFC-ACDP-0002-context-body.md"
	@echo "  5. rfcs/RFC-ACDP-0003-publish.md"
	@echo "  6. rfcs/RFC-ACDP-0004-retrieval.md"
	@echo "  7. rfcs/RFC-ACDP-0005-discovery.md"
	@echo "  8. rfcs/RFC-ACDP-0006-cross-registry.md"
	@echo "  9. rfcs/RFC-ACDP-0007-capabilities.md"
	@echo " 10. rfcs/RFC-ACDP-0008-security.md"
	@echo " 11. rfcs/RFC-ACDP-0009-extensions.md (Reserved)"
	@echo " 12. docs/overview.md"
	@echo " 13. docs/integration-guide.md"

# ── Clean ────────────────────────────────────────────────────────────────────

clean:
	@echo "Cleaning generated files..."
	@rm -rf packages/proto-go/acdp/
	@rm -f  packages/proto-csharp/*.cs
	@rm -rf packages/proto-java/src/main/java/io/
	@rm -rf packages/proto-npm/generated/
	@rm -rf packages/proto-python/src/acdp/
	@echo "✓ Cleaned"

# ── Tooling install ──────────────────────────────────────────────────────────

install-tools:
	@echo "Installing development tools..."
	@echo
	@echo "1. Installing buf (protobuf tooling)..."
	@if command -v brew >/dev/null 2>&1; then \
		brew install bufbuild/buf/buf; \
	else \
		echo "Please install buf manually: https://buf.build/docs/installation"; \
	fi
	@echo
	@echo "2. Installing ajv-cli and ajv-formats..."
	@if command -v npm >/dev/null 2>&1; then \
		npm install -g ajv-cli ajv-formats; \
	else \
		echo "Please install Node.js and npm, then run: npm install -g ajv-cli ajv-formats"; \
	fi
	@echo
	@echo "3. Installing protoc..."
	@if command -v brew >/dev/null 2>&1; then \
		brew install protobuf; \
	elif command -v apt-get >/dev/null 2>&1; then \
		sudo apt-get update && sudo apt-get install -y protobuf-compiler; \
	else \
		echo "Please install protoc manually: https://protobuf.dev/downloads/"; \
	fi
	@echo
	@echo "✓ Tool installation complete"
