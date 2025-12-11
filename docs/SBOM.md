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
| **Version** | 4.6.2 |
| **License** | MIT |
| **Local Path** | `src/web/static/js/vendor/socket.io-4.6.2.min.js` |
| **Download URL** | [https://registry.npmjs.org/socket.io-client/-/socket.io-client-4.6.2.tgz](https://registry.npmjs.org/socket.io-client/-/socket.io-client-4.6.2.tgz) |
| **NPM Registry** | [https://www.npmjs.com/package/socket.io-client/v/4.6.2](https://www.npmjs.com/package/socket.io-client/v/4.6.2) |
| **GitHub** | [https://github.com/socketio/socket.io-client](https://github.com/socketio/socket.io-client) |
| **SHA-256** | `39d4925fad0da1c8405fb91ce0e4628c892a6fef94147a0923fafd2e6a0a25a1` |
| **NPM Integrity** | `sha512-OwWrMbbA8wSqhBAR0yoPK6EdQLERQAYjXb3A0zLpgxfM1ZGLKoxHx8gVmCHA6pcclRX5oA/zvQf7bghAS11jRA==` |
| **Security Note** | Version 4.6.2 fixes CVE-2024-38355 (CVSS 7.3) |

**Extraction Command:**
```bash
curl -sL "https://registry.npmjs.org/socket.io-client/-/socket.io-client-4.6.2.tgz" -o socket.io-client.tgz
tar -xzf socket.io-client.tgz package/dist/socket.io.min.js
cp package/dist/socket.io.min.js src/web/static/js/vendor/socket.io-4.6.2.min.js
```

**Verification Command:**
```bash
echo "39d4925fad0da1c8405fb91ce0e4628c892a6fef94147a0923fafd2e6a0a25a1  src/web/static/js/vendor/socket.io-4.6.2.min.js" | sha256sum -c
```

---

## Python Dependencies

Python dependencies are managed via `requirements.txt` and installed from PyPI.
PyPI packages are verified via pip's built-in hash checking.

### Core Dependencies

| Package | Version | License | PyPI URL |
|---------|---------|---------|----------|
| numpy | >=1.26.0 | BSD-3-Clause | https://pypi.org/project/numpy/ |
| opencv-python | >=4.9.0 | MIT | https://pypi.org/project/opencv-python/ |
| opencv-contrib-python | >=4.9.0 | MIT | https://pypi.org/project/opencv-contrib-python/ |

### Web Framework

| Package | Version | License | PyPI URL |
|---------|---------|---------|----------|
| Flask | >=3.0.0 | BSD-3-Clause | https://pypi.org/project/Flask/ |
| Flask-SocketIO | >=5.3.0 | MIT | https://pypi.org/project/Flask-SocketIO/ |
| python-socketio | >=5.10.0 | MIT | https://pypi.org/project/python-socketio/ |

### Hardware Interface

| Package | Version | License | PyPI URL |
|---------|---------|---------|----------|
| smbus2 | >=0.4.3 | MIT | https://pypi.org/project/smbus2/ |

### Camera Support (Raspberry Pi)

| Package | Version | License | PyPI URL |
|---------|---------|---------|----------|
| picamera | >=1.13 | BSD | https://pypi.org/project/picamera/ |
| picamera2 | >=0.3.16 | BSD | https://pypi.org/project/picamera2/ |

### Image Processing

| Package | Version | License | PyPI URL |
|---------|---------|---------|----------|
| Pillow | >=10.3.0 | HPND | https://pypi.org/project/Pillow/ |
| scipy | >=1.12.0 | BSD-3-Clause | https://pypi.org/project/scipy/ |

### Optional: IMU Support

| Package | Version | License | PyPI URL |
|---------|---------|---------|----------|
| adafruit-circuitpython-mpu6050 | >=1.2.0 | MIT | https://pypi.org/project/adafruit-circuitpython-mpu6050/ |
| adafruit-circuitpython-bno055 | >=1.6.0 | MIT | https://pypi.org/project/adafruit-circuitpython-bno055/ |

### Optional: Machine Learning

| Package | Version | License | PyPI URL |
|---------|---------|---------|----------|
| tflite-runtime | >=2.14.0 | Apache-2.0 | https://pypi.org/project/tflite-runtime/ |
| tensorflow | >=2.15.0 | Apache-2.0 | https://pypi.org/project/tensorflow/ |
| onnxruntime | >=1.16.0 | MIT | https://pypi.org/project/onnxruntime/ |

### Development Dependencies

| Package | Version | License | PyPI URL |
|---------|---------|---------|----------|
| pytest | >=8.0.0 | MIT | https://pypi.org/project/pytest/ |
| pytest-asyncio | >=0.23.0 | Apache-2.0 | https://pypi.org/project/pytest-asyncio/ |
| black | >=24.0.0 | MIT | https://pypi.org/project/black/ |
| flake8 | >=7.0.0 | MIT | https://pypi.org/project/flake8/ |
| mypy | >=1.8.0 | MIT | https://pypi.org/project/mypy/ |
| pre-commit | >=3.6.0 | MIT | https://pypi.org/project/pre-commit/ |

---

## Verification Script

A script is provided to verify all vendored dependencies:

```bash
#!/bin/bash
# verify-dependencies.sh
# Verifies all vendored dependencies against known checksums

set -e

echo "Verifying vendored JavaScript dependencies..."

# Socket.IO client 4.6.2 (fixes CVE-2024-38355)
EXPECTED_SHA256="39d4925fad0da1c8405fb91ce0e4628c892a6fef94147a0923fafd2e6a0a25a1"
ACTUAL_SHA256=$(sha256sum src/web/static/js/vendor/socket.io-4.6.2.min.js | cut -d' ' -f1)

if [ "$EXPECTED_SHA256" = "$ACTUAL_SHA256" ]; then
    echo "✓ socket.io-4.6.2.min.js: OK"
else
    echo "✗ socket.io-4.6.2.min.js: CHECKSUM MISMATCH"
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
