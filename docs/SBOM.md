# Software Bill of Materials (SBOM)

This document lists all software dependencies used by the MonsterBorg Self-Drive
project, including download sources, versions, and verification checksums.

**Last Updated:** 2025-12-11
**SBOM Format:** Custom Markdown (compatible with CycloneDX/SPDX concepts)

## Security Policy

All external resources MUST be:

1. Downloaded and stored locally in the repository
2. Verified using checksums before deployment
3. Documented in this SBOM with source URL
4. Never loaded from external CDNs at runtime

## Frontend JavaScript Dependencies

### Socket.IO Client

| Property | Value |
|----------|-------|
| **Name** | socket.io-client |
| **Version** | 4.8.1 |
| **License** | MIT |
| **Local Path** | `src/web/static/js/vendor/socket.io-4.8.1.min.js` |
| **Download URL** | [https://registry.npmjs.org/socket.io-client/-/socket.io-client-4.8.1.tgz](https://registry.npmjs.org/socket.io-client/-/socket.io-client-4.8.1.tgz) |
| **NPM Registry** | [https://www.npmjs.com/package/socket.io-client/v/4.8.1](https://www.npmjs.com/package/socket.io-client/v/4.8.1) |
| **GitHub** | [https://github.com/socketio/socket.io-client](https://github.com/socketio/socket.io-client) |
| **SHA-256** | `b0e735814f8dcfecd6cdb8a7ce95a297a7e1e5f2727a29e6f5901801d52fa0c5` |
| **NPM Shasum** | `1941eca135a5490b94281d0323fe2a35f6f291cb` |
| **Security Note** | Latest stable release; includes fix for CVE-2024-38355 (since 4.6.2) |

**Extraction Command:**

```bash
curl -sL "https://registry.npmjs.org/socket.io-client/-/socket.io-client-4.8.1.tgz" -o socket.io-client.tgz
tar -xzf socket.io-client.tgz package/dist/socket.io.min.js
cp package/dist/socket.io.min.js src/web/static/js/vendor/socket.io-4.8.1.min.js
```

**Verification Command:**

```bash
echo "b0e735814f8dcfecd6cdb8a7ce95a297a7e1e5f2727a29e6f5901801d52fa0c5  src/web/static/js/vendor/socket.io-4.8.1.min.js" | sha256sum -c
```

---

## Python Dependencies

Python dependencies are managed via `requirements.txt` and installed from PyPI.
PyPI packages are verified via pip's built-in hash checking.

### Core Dependencies

| Package | Version | License | PyPI URL |
|---------|---------|---------|----------|
| numpy | >=2.0.0,<2.3 | BSD-3-Clause | [https://pypi.org/project/numpy/](https://pypi.org/project/numpy/) |
| opencv-python | >=4.10.0.84 | MIT | [https://pypi.org/project/opencv-python/](https://pypi.org/project/opencv-python/) |
| opencv-contrib-python | >=4.10.0.84 | MIT | [https://pypi.org/project/opencv-contrib-python/](https://pypi.org/project/opencv-contrib-python/) |

**Compatibility Notes:**

- NumPy 2.x compatible - codebase uses only basic APIs
- opencv-python >=4.10.0.84 required (4.10.0.82 incompatible with NumPy 2.x)
- If encountering NumPy errors, clear pip cache: `pip cache purge`

### Web Framework

| Package | Version | License | PyPI URL |
|---------|---------|---------|----------|
| Flask | >=3.1.0 | BSD-3-Clause | [https://pypi.org/project/Flask/](https://pypi.org/project/Flask/) |
| Flask-SocketIO | >=5.5.0 | MIT | [https://pypi.org/project/Flask-SocketIO/](https://pypi.org/project/Flask-SocketIO/) |
| python-socketio | >=5.15.0 | MIT | [https://pypi.org/project/python-socketio/](https://pypi.org/project/python-socketio/) |

### Hardware Interface

| Package | Version | License | PyPI URL |
|---------|---------|---------|----------|
| smbus2 | >=0.4.3 | MIT | [https://pypi.org/project/smbus2/](https://pypi.org/project/smbus2/) |

### Camera Support (Raspberry Pi - install separately)

| Package | Version | License | PyPI URL |
|---------|---------|---------|----------|
| picamera | >=1.13 | BSD | [https://pypi.org/project/picamera/](https://pypi.org/project/picamera/) |
| picamera2 | >=0.3.16 | BSD | [https://pypi.org/project/picamera2/](https://pypi.org/project/picamera2/) |

**Note:** These packages require system dependencies. On Raspberry Pi:

```bash
sudo apt install libcap-dev python3-picamera2 python3-libcamera
pip install picamera2
```

### Image Processing

| Package | Version | License | PyPI URL |
|---------|---------|---------|----------|
| Pillow | >=11.0.0 | HPND | [https://pypi.org/project/Pillow/](https://pypi.org/project/Pillow/) |
| scipy | >=1.14.0 | BSD-3-Clause | [https://pypi.org/project/scipy/](https://pypi.org/project/scipy/) |

### Optional: IMU Support

| Package | Version | License | PyPI URL |
|---------|---------|---------|----------|
| adafruit-circuitpython-mpu6050 | >=1.2.0 | MIT | [https://pypi.org/project/adafruit-circuitpython-mpu6050/](https://pypi.org/project/adafruit-circuitpython-mpu6050/) |
| adafruit-circuitpython-bno055 | >=1.6.0 | MIT | [https://pypi.org/project/adafruit-circuitpython-bno055/](https://pypi.org/project/adafruit-circuitpython-bno055/) |

### Optional: Machine Learning (Future)

**Status:** No ML inference code implemented yet. Dependencies will be added when
on-device object detection is implemented.

**Planned packages when inference is added:**

| Package | Platform | License | Notes |
|---------|----------|---------|-------|
| ai-edge-litert | aarch64 | Apache-2.0 | LiteRT (formerly TensorFlow Lite) |
| tensorflow | x86_64 | Apache-2.0 | Development/training only |
| keras | x86_64 | Apache-2.0 | Requires >=3.12.0 for CVE fixes |
| onnxruntime | All | MIT | Alternative inference runtime |

**References:**

- [LiteRT Migration Guide](https://ai.google.dev/edge/litert/migration)
  (`tflite-runtime` is deprecated)
- [ai-edge-litert on PyPI](https://pypi.org/project/ai-edge-litert/)

**Security considerations for keras (when added):**

- CVE-2025-12060: Path traversal in tar archive extraction
- CVE-2025-9906: Arbitrary code execution via model loading
- CVE-2025-9905: Unsafe deserialization in legacy formats
- CVE-2025-12058: Arbitrary file read and SSRF

### Development Dependencies

| Package | Version | License | PyPI URL |
|---------|---------|---------|----------|
| pytest | >=9.0.0 | MIT | [https://pypi.org/project/pytest/](https://pypi.org/project/pytest/) |
| pytest-asyncio | >=0.24.0 | Apache-2.0 | [https://pypi.org/project/pytest-asyncio/](https://pypi.org/project/pytest-asyncio/) |
| black | >=24.0.0 | MIT | [https://pypi.org/project/black/](https://pypi.org/project/black/) |
| flake8 | >=7.0.0 | MIT | [https://pypi.org/project/flake8/](https://pypi.org/project/flake8/) |
| mypy | >=1.8.0 | MIT | [https://pypi.org/project/mypy/](https://pypi.org/project/mypy/) |
| pre-commit | >=3.6.0 | MIT | [https://pypi.org/project/pre-commit/](https://pypi.org/project/pre-commit/) |
| filelock | >=3.20.1 | Unlicense | [https://pypi.org/project/filelock/](https://pypi.org/project/filelock/) |

**Notes:**
- pytest >=9.0.0 requires Python 3.10+ (Debian Trixie has 3.13.5)
- filelock >=3.20.1 required to fix CVE-2025-68146 (TOCTOU symlink vulnerability)

---

## Verification Script

A script is provided to verify all vendored dependencies:

```bash
#!/bin/bash
# verify-dependencies.sh
# Verifies all vendored dependencies against known checksums

set -e

echo "Verifying vendored JavaScript dependencies..."

# Socket.IO client 4.8.1 (latest stable, includes CVE-2024-38355 fix)
EXPECTED_SHA256="b0e735814f8dcfecd6cdb8a7ce95a297a7e1e5f2727a29e6f5901801d52fa0c5"
ACTUAL_SHA256=$(sha256sum src/web/static/js/vendor/socket.io-4.8.1.min.js | cut -d' ' -f1)

if [ "$EXPECTED_SHA256" = "$ACTUAL_SHA256" ]; then
    echo "✓ socket.io-4.8.1.min.js: OK"
else
    echo "✗ socket.io-4.8.1.min.js: CHECKSUM MISMATCH"
    echo "  Expected: $EXPECTED_SHA256"
    echo "  Actual:   $ACTUAL_SHA256"
    exit 1
fi

echo ""
echo "All dependencies verified successfully."
```

---

## Deployment Checklist

Before deploying to production:

1. [ ] Run `verify-dependencies.sh` to confirm checksums
2. [ ] Check for security advisories on all dependencies
3. [ ] Verify no external URLs are loaded at runtime (grep for `http://` and `https://`)
4. [ ] Update this SBOM if any dependencies change

---

## Adding New Dependencies

When adding a new dependency:

1. Download from official source (PyPI, npm registry, GitHub releases)
2. Verify package signature/checksum if available
3. Store locally in appropriate directory:
   - Python: Add to `requirements.txt`
   - JavaScript: Store in `src/web/static/js/vendor/`
4. Document in this SBOM with:
   - Name, version, license
   - Download URL
   - SHA-256 checksum
   - Verification command
5. Never reference external CDNs in HTML/JS

---

## License Compliance

All dependencies use permissive open-source licenses compatible with this project:

- MIT License
- BSD-3-Clause License
- Apache-2.0 License
- HPND (Pillow)

See individual package documentation for full license text.
