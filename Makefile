.PHONY: help bootstrap validate validate-all json-validate json-schema-validate conformance consistency clean install-tools install-python-deps docs

# ── Default ───────────────────────────────────────────────────────────────────

help:
	@echo "ACDP Development Commands"
	@echo
	@echo "Setup (one-time):"
	@echo "  make bootstrap             Install all dev dependencies (ajv-cli + Python)"
	@echo
	@echo "Validation:"
	@echo "  make validate              Run all validations"
	@echo "  make json-schema-validate  Validate JSON Schema itself"
	@echo "  make json-validate         Validate JSON examples / fixtures against schemas"
	@echo "  make conformance           Run executable conformance vectors"
	@echo "  make consistency           Check fixtures <-> profiles <-> README <-> registries wiring"
	@echo
	@echo "Docs:"
	@echo "  make docs                  Print the docs reading order"
	@echo
	@echo "Utilities:"
	@echo "  make clean                 Remove generated files"
	@echo "  make install-tools         Install ajv-cli only"
	@echo "  make install-python-deps   Install Python conformance-runner deps only"

# ── Validation ────────────────────────────────────────────────────────────────

validate: json-schema-validate json-validate conformance consistency
	@echo "✓ All validations passed"

conformance:
	@echo "Running executable conformance vectors..."
	@python3 scripts/conformance-runner.py

consistency:
	@echo "Checking cross-artifact consistency..."
	@python3 scripts/check-consistency.py

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
	@echo " 12. rfcs/RFC-ACDP-0010-registry-receipts.md (0.2.0)"
	@echo " 13. rfcs/RFC-ACDP-0011-lineage-head-receipts.md (0.3.0)"
	@echo " 14. rfcs/RFC-ACDP-0012-transparency-log.md (0.3.0)"
	@echo " 15. rfcs/RFC-ACDP-0013-lifecycle-events.md (0.3.0)"
	@echo " 16. rfcs/RFC-ACDP-0014-key-revocation.md (0.3.0)"
	@echo " 17. rfcs/RFC-ACDP-0015-witness-cosigning.md (0.4.0)"
	@echo " 18. rfcs/RFC-ACDP-0016-external-anchors.md (0.5.0, Draft)"
	@echo " 19. rfcs/RFC-ACDP-0017-chain-verification.md (0.5.0, Final; §10-§11 Draft)"
	@echo " 20. rfcs/RFC-ACDP-0018-retraction-recall.md (0.5.0, Draft)"
	@echo " 21. rfcs/RFC-ACDP-0019-mcp-tool-result-provenance.md (0.5.0, Final; §5, §7, §10 Draft)"
	@echo " 22. rfcs/RFC-ACDP-0020-registry-trust-lists.md (0.5.0, Final)"
	@echo " 23. rfcs/RFC-ACDP-0021-keyless-signing.md (0.5.0, Draft)"
	@echo " 24. docs/overview.md"
	@echo " 25. docs/integration-guide.md"

# ── Clean ────────────────────────────────────────────────────────────────────

clean:
	@echo "Cleaning generated files..."
	@echo "✓ Cleaned"

# ── Tooling install ──────────────────────────────────────────────────────────

bootstrap: install-tools install-python-deps
	@echo
	@echo "✓ All dev dependencies installed."
	@echo "  Run: make validate"

install-tools:
	@echo "Installing ajv-cli and ajv-formats (pinned to the CI majors)..."
	@if command -v npm >/dev/null 2>&1; then \
		npm install -g ajv-cli@5 ajv-formats@3; \
	else \
		echo "ERROR: npm required (see https://nodejs.org)"; exit 1; \
	fi

install-python-deps:
	@echo "Installing Python conformance-runner dependencies..."
	@if command -v pip3 >/dev/null 2>&1; then \
		pip3 install --quiet -r requirements-dev.txt || { \
			echo; \
			echo "pip3 install failed. On a PEP 668 externally-managed Python"; \
			echo "(e.g. Homebrew on macOS), use a virtualenv, or run:"; \
			echo "  pip3 install --user --break-system-packages -r requirements-dev.txt"; \
			exit 1; \
		}; \
	else \
		echo "ERROR: pip3 required"; exit 1; \
	fi
