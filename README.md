
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

1. **Install Python**  
   [Download Python](https://www.python.org/downloads) and make sure to check the box:
   - ✅ "Add Python to PATH"

2. **Clone or download the repository**

3. **Install requirements**  
   In the project folder:
   ```cmd
   pip install -r requirements.txt
   ```

4. **Run the script**
   ```cmd
   python dl.py -u https://voe.sx/yourvideo
   ```

5. **See all options**
   ```cmd
   python dl.py -h
   ```

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

### Optional: Parallel Downloads
You can add the `-w` option to set number of parallel workers:
```bash
voe-dl -l links.txt -w 8
```
(Default is 4)

---

## 📂 Output

Downloaded videos will be saved in the same folder where you run the command.

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
This will print all available options, arguments, and descriptions.

---

## 💡 Contributing

Pull requests are welcome! If you fix a bug or add a feature, please update the README accordingly.
