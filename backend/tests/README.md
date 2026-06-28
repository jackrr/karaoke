# Karaoke Backend Tests

## Setup

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx aioresponses

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific category
pytest tests/integration  pytest tests/unit  pytest tests/unit