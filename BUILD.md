
# 🛠️ How to Build `voe-dl.exe`

## Requirements
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed

---

## 🧱 Build Instructions

```bash
# Install dependencies (including pyinstaller)
uv sync
uv add --dev pyinstaller

# Build the executable
uv run pyinstaller --onefile --name=voe-dl voe_dl/__main__.py
```

This will create:
```
dist/voe-dl.exe
```

---

## 🏷️ Rename and Create SHA256

```bash
# Generate checksum
sha256sum dist/voe-dl.exe > dist/voe-dl.sha256.txt
```

Or on Windows PowerShell:
```powershell
Get-FileHash dist\voe-dl.exe -Algorithm SHA256 | Out-File dist\voe-dl.sha256.txt
```

---

## 📦 Ready to Release

- Upload `voe-dl-v1.5.1.exe` and `voe-dl-v1.5.1.sha256.txt` to GitHub Releases.
