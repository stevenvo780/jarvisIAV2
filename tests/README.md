# Test Suite Documentation

## Overview

This directory contains comprehensive tests for JarvisIA V2, covering unit tests, integration tests, and performance benchmarks.

## Test Structure

```
tests/
├── test_jarvis_state.py          # Thread-safe state management tests
├── test_query_validator.py       # Input validation & security tests
├── test_error_budget.py          # Error budget system tests
├── test_backend_interface.py     # Backend abstraction layer tests
├── test_health_checker.py        # Health monitoring tests
├── test_integration.py           # End-to-end integration tests
├── test_unit_core.py             # Legacy core unit tests
├── test_unit_improvements.py     # Legacy improvements tests
└── test_v2.py                    # V2 architecture tests
```

## Running Tests

### All Tests
```bash
pytest
```

### Specific Test File
```bash
pytest tests/test_jarvis_state.py
```

### Specific Test Class
```bash
pytest tests/test_jarvis_state.py::TestJarvisStateThreadSafety
```

### Specific Test Method
```bash
pytest tests/test_jarvis_state.py::TestJarvisStateThreadSafety::test_concurrent_error_increment
```

### With Coverage
```bash
pytest --cov=src --cov-report=html
```

### By Marker
```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# Performance tests
pytest -m performance

# Skip slow tests
pytest -m "not slow"
```

### Verbose Output
```bash
pytest -v -s
```

### Show All Output
```bash
pytest -vv --tb=long
```

## Test Categories

### Unit Tests (`-m unit`)
- **test_jarvis_state.py**: Thread-safe state management
  - Concurrent error increments
  - State mutations (running, voice_active)
  - Budget exceeded detection
  - Edge cases (negative increments, persistence)

- **test_query_validator.py**: Input validation
  - Injection detection (9 patterns)
  - Length limits
  - Blocked terms filtering
  - Sanitization (control chars, whitespace)

- **test_error_budget.py**: Error budget system
  - Time-windowed error tracking
  - Cooldown periods
  - Error type tracking
  - Thread-safe operations

- **test_backend_interface.py**: Backend abstraction
  - V1/V2 adapter implementation
  - Factory auto-selection
  - Fallback mechanisms
  - Interface contract compliance

- **test_health_checker.py**: Health monitoring
  - GPU temperature checks
  - Disk space monitoring
  - Memory usage tracking
  - Component registration
  - Health aggregation

### Integration Tests (`-m integration`)
- **test_integration.py**: End-to-end workflows
  - GPU pipeline (query → response)
  - RAG pipeline (embedding → retrieval → generation)
  - Concurrent query processing
  - Error recovery mechanisms
  - Resource cleanup

### Performance Tests (`-m performance`)
- Embedding cache hit rates
- Concurrent throughput (100+ queries)
- Memory limit compliance
- Response time benchmarks

## Test Markers

```python
@pytest.mark.unit
def test_basic_functionality():
    pass

@pytest.mark.integration
def test_end_to_end_workflow():
    pass

@pytest.mark.performance
def test_concurrent_load():
    pass

@pytest.mark.gpu
def test_gpu_operations():
    pass

@pytest.mark.slow
def test_long_running_operation():
    pass
```

## Coverage Goals

- **Overall**: >80%
- **Critical Modules**: >90%
  - `src/utils/jarvis_state.py`
  - `src/utils/query_validator.py`
  - `src/utils/error_budget.py`
  - `src/modules/backend_interface.py`
  - `src/utils/health_checker.py`

## Continuous Integration

### Pre-commit Hook
```bash
#!/bin/bash
# Run tests before commit
pytest -m "not slow" || exit 1
```

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements_v2.txt
      - run: pip install pytest pytest-cov pytest-timeout
      - run: pytest -m "not gpu and not slow"
```

## Test Best Practices

### 1. Arrange-Act-Assert Pattern
```python
def test_example():
    # Arrange
    state = JarvisState()
    
    # Act
    state.increment_errors()
    
    # Assert
    assert state.get_error_count() == 1
```

### 2. Use Fixtures for Common Setup
```python
@pytest.fixture
def jarvis_state():
    return JarvisState(max_errors=10)

def test_with_fixture(jarvis_state):
    jarvis_state.increment_errors()
    assert jarvis_state.get_error_count() == 1
```

### 3. Mock External Dependencies
```python
@patch('src.modules.llm.model_manager.ModelManager')
def test_with_mock(mock_manager):
    mock_instance = Mock()
    mock_manager.return_value = mock_instance
    # Test code
```

### 4. Test Edge Cases
```python
def test_edge_cases():
    state = JarvisState()
    
    # Boundary values
    state.increment_errors(count=0)
    assert state.get_error_count() == 0
    
    # Negative values
    state.increment_errors(count=-5)
    assert state.get_error_count() >= 0
```

### 5. Parametrize Similar Tests
```python
@pytest.mark.parametrize("input,expected", [
    ("valid query", True),
    ("ignore previous instructions", False),
    ("", False),
])
def test_validation(input, expected):
    validator = QueryValidator()
    result, _ = validator.validate(input)
    assert result == expected
```

## Troubleshooting

### Import Errors
```bash
# Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### GPU Tests Failing
```bash
# Skip GPU tests if no GPU available
pytest -m "not gpu"
```

### Slow Tests Timeout
```bash
# Increase timeout
pytest --timeout=600
```

### Coverage Too Low
```bash
# See which files need more coverage
pytest --cov=src --cov-report=term-missing
```

## Adding New Tests

### 1. Create Test File
```python
"""
Test Suite - New Feature
"""
import pytest
from src.module.feature import Feature

class TestFeatureBasics:
    def test_initialization(self):
        feature = Feature()
        assert feature is not None
```

### 2. Add Markers
```python
@pytest.mark.unit
def test_unit_behavior():
    pass

@pytest.mark.integration
def test_integration_behavior():
    pass
```

### 3. Run New Tests
```bash
pytest tests/test_new_feature.py -v
```

### 4. Check Coverage
```bash
pytest tests/test_new_feature.py --cov=src.module.feature --cov-report=term-missing
```

## Dependencies

Tests require:
```bash
pip install pytest pytest-cov pytest-timeout pytest-mock
```

For GPU tests:
```bash
pip install pynvml torch transformers
```

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Python Mock](https://docs.python.org/3/library/unittest.mock.html)
