.PHONY: help validate validate-all json-validate json-schema-validate clean install-tools docs

# ── Default ───────────────────────────────────────────────────────────────────

help:
	@echo "ACDP Development Commands"
	@echo
	@echo "Validation:"
	@echo "  make validate              Run all validations"
	@echo "  make json-schema-validate  Validate JSON Schema itself"
	@echo "  make json-validate         Validate JSON examples / fixtures against schemas"
	@echo
	@echo "Docs:"
	@echo "  make docs                  Print the docs reading order"
	@echo
	@echo "Utilities:"
	@echo "  make clean                 Remove generated files"
	@echo "  make install-tools         Install required development tools"

# ── Validation ────────────────────────────────────────────────────────────────

validate: json-schema-validate json-validate
	@echo "✓ All validations passed"

validate-all: validate
	@echo "✓ All validations completed"

json-schema-validate:
	@echo "Validating JSON Schemas (meta-validation)..."
	@./scripts/validate-json-schema.sh

json-validate:
	@echo "Validating JSON examples and conformance fixtures..."
	@./scripts/validate-json.sh

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
	@echo "✓ Cleaned"

# ── Tooling install ──────────────────────────────────────────────────────────

install-tools:
	@echo "Installing development tools..."
	@echo
	@echo "Installing ajv-cli and ajv-formats..."
	@if command -v npm >/dev/null 2>&1; then \
		npm install -g ajv-cli ajv-formats; \
	else \
		echo "Please install Node.js and npm, then run: npm install -g ajv-cli ajv-formats"; \
	fi
	@echo
	@echo "✓ Tool installation complete"
