
# 🛠️ How to Build `voe-dl.exe`

## Requirements
- Python 3.8+ installed
- `pip install pyinstaller`

---

## 🧱 Build Instructions

```bash
# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build the executable
pyinstaller --onefile --name=voe-dl dl.py
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
