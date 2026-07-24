# Test environment matching the Volumio OS 4 target (Python 3.11.2, Debian bookworm).
# Only requirements-dev.txt is installed: the Adafruit hardware packages in
# requirements.txt are ARM/Pi-only and are stubbed by tests/conftest.py.
FROM python:3.11-slim-bookworm

WORKDIR /app

# Copy the dependency manifest first so `pip install` is cached across code changes.
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy the rest of the project (the compose file also bind-mounts it for iteration).
COPY . .

# pytest.ini provides testpaths/addopts.
CMD ["python", "-m", "pytest", "-v"]
