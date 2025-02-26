# Variables
PACKAGE_NAME=pylumagen
PYTHON=python3
PIP=pip
INIT_FILE=lumagen/__init__.py
PROJECT_FILE=pyproject.toml
BUILD_DIR=dist
SOURCE_FILES=$(wildcard lumagen/**/*.py tests/**/*.py scripts/**/*)

# Default target
all: install

# Extract and bump version
bump-version:
	@echo "Bumping version in $(INIT_FILE)..."
	@version=$$(grep -E '^__version__ = ' $(INIT_FILE) | sed -E 's/__version__ = "(.*)"/\1/') && \
	major=$$(echo $$version | cut -d. -f1) && \
	minor=$$(echo $$version | cut -d. -f2) && \
	patch=$$(echo $$version | cut -d. -f3) && \
	new_version="$$major.$$minor.$$((patch + 1))" && \
	awk -v new_version="$$new_version" '/__version__/ {gsub(/"[0-9]+\.[0-9]+\.[0-9]+"/, "\"" new_version "\"")}1' $(INIT_FILE) > $(INIT_FILE).tmp && \
	mv $(INIT_FILE).tmp $(INIT_FILE) && \
	echo "New version: $$new_version"


# Build the package using `python -m build` only if sources have changed
$(BUILD_DIR): $(SOURCE_FILES) $(INIT_FILE)
	@echo "Source files or scripts changed, cleaning and rebuilding..."
	$(MAKE) clean
	$(MAKE) build

build: bump-version
	$(PYTHON) -m build

# Clean up build artifacts
clean:
	rm -rf build dist *.egg-info

# Install dependencies and package
install: $(BUILD_DIR)
	rm -rf ~/pypi-server/packages/pylumagen*
	cp dist/* ~/pypi-server/packages/

# Run tests using pytest
test:
	$(PYTHON) -m pytest tests

coverage:
	@echo "Running coverage tests..."
	@coverage run -m pytest tests/ && coverage report -m

# Help
help:
	@echo "Available targets:"
	@echo "  install        Default target. Installs package after checking for changes."
	@echo "  build          Bump version and build the package (using python -m build)"
	@echo "  clean          Remove build artifacts"
	@echo "  test           Run tests with pytest"
	@echo "  coverage       Run tests with coverage and show report only if tests pass"
	@echo "  install-local  Install the package locally"
	@echo "  publish        Upload the package to PyPI"
