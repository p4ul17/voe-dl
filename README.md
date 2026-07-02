
# voe-dl

A Python-based downloader for videos hosted on [voe.sx](https://voe.sx).

### 🔄 Release Status

| Source               | Version                                                                  |
|----------------------|--------------------------------------------------------------------------|
| **Upstream**         | [![Upstream Release](https://img.shields.io/github/v/release/p4ul17/voe-dl)](https://github.com/p4ul17/voe-dl/releases) |
| **MPZ-00's Fork**    | [![MPZ-00's Release](https://img.shields.io/github/v/release/MPZ-00/voe-dl)](https://github.com/MPZ-00/voe-dl/releases/latest) |


---

## ⚠️ Always Use the Latest Version

> Voe frequently updates their website to break download scripts.  
> **Make sure you are using the latest version** of `voe-dl` to ensure compatibility.

---

## 📥 How to Use `voe-dl`

### Method 1: Using `voe-dl.exe`

1. **Open Command Prompt**  
   Press `Win + R`, type `cmd`, and press Enter.

2. **Navigate to the folder with `voe-dl.exe`**  
   Example:
   ```cmd
   cd "C:\Users\YourName\Downloads"
   ```

3. **Download a video**
   ```cmd
   voe-dl.exe -u https://voe.sx/yourvideo
   ```

> 📝 You don’t need to add `voe-dl.exe` to your system PATH. Just navigate to the folder in CMD.

---

### Method 2: Running from Python Source Code

1. **Install [uv](https://docs.astral.sh/uv/getting-started/installation/)**  
   A fast Python package/project manager. It installs its own Python if needed, so a separate Python install isn't required.

2. **Clone or download the repository**

3. **Install dependencies**  
   In the project folder:
   ```cmd
   uv sync
   ```

4. **Run the script**
   ```cmd
   uv run voe-dl -u https://voe.sx/yourvideo
   ```
   or equivalently: `uv run python -m voe_dl -u https://voe.sx/yourvideo`

5. **See all options**
   ```cmd
   uv run voe-dl -h
   ```

> Prefer plain `pip`? `pip install .` also works, since dependencies are declared in `pyproject.toml`.

---

## 📄 Command Line Usage

### Download Single Video
```bash
voe-dl -u https://voe.sx/yourvideo
```

### Download from a list (batch)
Create a `links.txt` file:
```
https://voe.sx/xxxxxxx
https://voe.sx/yyyyyyy
```

Run:
```bash
voe-dl -l links.txt
```

### Setting Title in List File
You can specify a custom title for all files by adding a special comment at the start of your list file:
```
#: My Series Title
https://voe.sx/xxxxxxx
https://voe.sx/yyyyyyy
```
This title will be used when combined with `--numbering` instead of the `--name` argument.

### Custom File Naming
Set a custom name for downloaded files:
```bash
voe-dl -u https://voe.sx/yourvideo --name "MyVideo"
```

With episode numbering (extracts S##E## from URL or numbers sequentially):
```bash
voe-dl -l links.txt --name "ShowName" --numbering
```
This creates files like: `ShowName_S01E01.mp4`, `ShowName_S01E02.mp4`, etc.

If you use `--numbering` without `--name`, it defaults to "Episode":
```bash
voe-dl -l links.txt --numbering
```
Creates: `Episode_S01E01.mp4`, `Episode_S01E02.mp4`, etc.

### Parallel Downloads
Set the number of parallel workers (default is 4):
```bash
voe-dl -l links.txt -w 8
```

### Dry Run Mode
Test the download process without actually downloading:
```bash
voe-dl -l links.txt --dry-run
```

### Aborting Downloads
Press `Ctrl+C` to gracefully abort downloads. You'll be prompted to either:
- **Keep** `.part` files to resume later
- **Delete** `.part` files to start fresh next time

### Piped Output
When stdout is piped, `voe-dl` resolves the video and prints only the direct download link instead of downloading it:
```bash
voe-dl -u https://voe.sx/yourvideo | xargs -I{} wget {}
```

---

## 📂 Output

Downloaded videos will be saved in the same folder where you run the command.
But this can be changed using the `-d` option to specify a target directory.
```bash
voe-dl -d downloads
```
Attention: The target directory must be existent when running the script

---

## 🛠 Common Errors & Fixes

### ❌ SyntaxError when pasting into Python
Make sure you run commands in **CMD/Terminal**, not in the Python shell (`>>>` prompt).

### ❌ CMD window closes instantly
Open CMD manually and run the tool from there to see error output.

### ❌ `requests.exceptions.InvalidSchema`
Make sure the URL is valid and doesn't contain brackets or formatting issues.

✅ Correct:
```
https://voe.sx/fi3fqtyh7932
```

### ❌ No connection adapter found
Ensure the URL starts with `http://` or `https://` and doesn't contain strange characters.

---

## 🆘 Help
Run:
```bash
voe-dl -h
```
This will print all available options:

```
-h, --help              Show help message and exit
-u, --url               Download single video from URL
-l, --list              Download videos from a text file (one URL per line)
-w, --workers           Number of parallel download threads (default: 4)
--name                  Custom filename for downloaded videos
--numbering             Enable episode numbering (S##E## format)
--dry-run               Test download process without actually downloading
```

---

## 💡 Contributing

Pull requests are welcome! If you fix a bug or add a feature, please update the README accordingly.

