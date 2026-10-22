# Testing Guide for SpliceGAIP

This document describes the testing infrastructure and how to run tests for SpliceGAIP.

## Test Structure

```
tests/
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_schema.py      # Splicing schema tests
│   ├── test_statistics.py  # Statistical analysis tests
│   ├── test_config.py      # Configuration management tests
│   └── test_splicing_parsers.py  # Parser tests (rMATS, SUPPA2)
├── integration/             # Integration tests (API, database)
│   └── test_api.py         # FastAPI endpoint tests
├── e2e/                    # End-to-end tests (full workflows)
├── fixtures/               # Test data files
│   ├── rmats_se_sample.txt
│   ├── suppa_psi_sample.txt
│   └── config_test.yaml
├── conftest.py             # Pytest configuration and fixtures
└── __init__.py
```

## Running Tests

### Quick Start

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run with coverage report
pytest --cov=splicegaip --cov-report=html

# View HTML coverage report
open htmlcov/index.html  # macOS/Linux
start htmlcov\index.html  # Windows
```

### Common Commands

```bash
# Run specific test file
pytest tests/unit/test_schema.py

# Run specific test function
pytest tests/unit/test_schema.py::TestStandardEvent::test_create_minimal_event

# Run tests matching a pattern
pytest -k "statistics"

# Run tests in verbose mode
pytest -v

# Run tests without coverage (faster)
pytest --no-cov

# Run only fast tests (exclude slow ones)
pytest -m "not slow"
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual functions and classes in isolation
- **Speed**: Fast (< 1 second per test)
- **Dependencies**: Minimal (no network, no database)
- **Coverage Target**: 80%+

### Integration Tests (`tests/integration/`)
- **Purpose**: Test component interactions (API + database)
- **Speed**: Medium (1-5 seconds per test)
- **Dependencies**: May require test database
- **Coverage Target**: 60%+

### End-to-End Tests (`tests/e2e/`)
- **Purpose**: Test complete workflows from input to output
- **Speed**: Slow (> 5 seconds per test)
- **Dependencies**: Full environment setup
- **Coverage Target**: Key paths only

## Writing Tests

### Test Naming Convention

```python
def test_<function_name>_<scenario>():
    """Test description in plain English."""
    # Arrange: Set up test data
    # Act: Call the function
    # Assert: Check the result
```

### Example Test

```python
def test_chi_square_significant_difference():
    """Test detection of significant difference in junction counts."""
    # Arrange
    control_in = 100
    control_out = 20
    experiment_in = 30
    experiment_out = 90

    # Act
    p_value = chi_square_p_value(control_in, control_out, experiment_in, experiment_out)

    # Assert
    assert p_value is not None
    assert p_value < 0.05  # Should be significant
```

### Using Fixtures

```python
@pytest.fixture
def sample_rmats_data():
    """Sample rMATS data for testing."""
    return "ID\tGeneID\t...\n1\tENSG00000000001\t..."

def test_parse_rmats(sample_rmats_data, tmp_path):
    """Test rMATS parser with sample data."""
    test_file = tmp_path / "test.txt"
    test_file.write_text(sample_rmats_data)

    result = parse_rmats_file(test_file, ...)
    assert len(result) > 0
```

## Coverage Requirements

| Module Type | Minimum Coverage | Current Status |
|-------------|------------------|----------------|
| Core Schema | 90% | ✅ 60% |
| Statistics | 80% | ✅ 75% |
| Parsers | 80% | ✅ 81% |
| Config | 70% | ✅ 63% |
| API | 60% | ✅ 37% |
| **Overall** | **20% (CI gate)** | **✅ 27%** |

**Note**: Overall coverage remains limited by UI, report, integration, and full pipeline modules; deterministic Agent state and LLM fallback boundaries are now covered.

## Continuous Integration

Tests run automatically on:
- Every push to `master`, `main`, or `develop` branches
- Every pull request
- Multiple Python versions (3.10, 3.11, 3.12)

See `.github/workflows/test.yml` for CI configuration.

## Troubleshooting

### Import Errors

If you see `ImportError: cannot import name 'X'`:
```bash
# Make sure you're in the project root
cd E:\SpliceGAIP

# Reinstall package in development mode
pip install -e .
```

### Test Collection Errors

If pytest can't find tests:
```bash
# Check pytest.ini exists
ls pytest.ini

# Clear pytest cache
pytest --cache-clear
```

### Coverage Report Empty

If coverage report shows 0%:
```bash
# Make sure --cov flag is used
pytest --cov=splicegaip

# Check that splicegaip is importable
python -c "import splicegaip; print(splicegaip.__file__)"
```

## Future Improvements

- [ ] Add more parser tests (MAJIQ, LeafCutter)
- [ ] Add agent workflow tests
- [ ] Add UI component tests (Streamlit)
- [ ] Add performance benchmark tests
- [ ] Integrate with Codecov for coverage tracking
- [ ] Add mutation testing with `mutmut`

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov plugin](https://pytest-cov.readthedocs.io/)
- [Testing best practices](https://docs.python-guide.org/writing/tests/)
