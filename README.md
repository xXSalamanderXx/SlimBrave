<div align="center">

# SlimBrave - Revived

  <img src="https://i.postimg.cc/QCyWVFGN/SlimBrave.png" alt="SlimBrave Lion Logo" width="200"/>

A lightweight utility designed to give you ultimate control over your Brave Browser. Lock down telemetry, enforce strict privacy standards, and strip away built-in browser bloatware—all from a single, clean interface.

Supported on Windows, Linux & MacOS!
</div>

<br>

[![Release](https://img.shields.io/github/v/release/xXSalamanderXx/SlimBrave?style=for-the-badge)](https://github.com/xXSalamanderXx/SlimBrave/releases)
![](https://img.shields.io/badge/PowerShell-5391FE?style=for-the-badge&labelColor=ffffff&logoColor=5391FE&logo=powershell)
![](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&labelColor=FFD43B&logoColor=3776AB&logo=python)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue?style=for-the-badge)](./LICENSE)

[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://buymeacoffee.com/SinZZzz)

## SlimBrave Revived - Windows
[![Slimbrave-Windows.png](https://i.postimg.cc/5yNPg6pc/Slimbrave-Windows.png)](https://postimg.cc/Pp9zrfBK)

## SlimBrave Revived - macOS & Linux
[![Slimbrave-mac-OS.png](https://i.postimg.cc/cChH34Lq/Slimbrave-mac-OS.png)](https://postimg.cc/xNknDQmg)

<details>
<summary> Requirements </summary>


## Windows Requirements:

- Windows 10/11
- PowerShell
- Administrator privileges

<details>
<summary> Powershell Error "Running Scripts is Disabled on this System"</summary>

### Run this command in PowerShell:

```ps1
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned
```

</details>

## MacOS Requiremens:

- Homebrew
- Python (python via Homebrew)
- Python Tkinter

(Homebrew and Python/Tk will be automatically installed if you agree to the auto-installation upon running Slimbrave and if they're not already installed)

## Linux Requiremens:

- Python (usually installed by default)
- Python Tkinter (sometimes installed by default)

(Python/Tk will be automatically installed if you agree to the auto-installation upon running Slimbrave and if they're not already installed)

</details>


## 🚀 How to Use

## (Windows)

## Run the command below in PowerShell:

> [!TIP]
> Better if you run Powershell as Administrator
```ps1
iwr "https://raw.githubusercontent.com/xXSalamanderXx/SlimBrave/main/SlimBrave-Windows.ps1" -OutFile "SlimBrave-Windows.ps1"; .\SlimBrave-Windows.ps1
```
## or

1. Download the `SlimBrave.ps1` script from the [Releases](https://github.com/xXSalamanderXx/SlimBrave/releases) page.
2. Right-click the file and select **Run with PowerShell**.
3. Accept the UAC prompt (Administrator privileges are required to modify registry policies).
4. Check the boxes for the features you wish to disable/enable.
5. Click **Apply Settings** and restart your Brave Browser.


## (MacOS)

## Run the command below in Terminal:
```
curl -sO https://raw.githubusercontent.com/xXSalamanderXx/SlimBrave/main/SlimBrave-MacOS.py && python3 SlimBrave-MacOS.py
```

> [!IMPORTANT]
> If dependencies fail to auto-install via the script, please refer to this.
> 1. Install Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
> 2. Install Python: `brew install python`
> 3. Install Tkinter support: `brew install python-tk`


## (Linux)

## Run the command below in Terminal:
```
curl -sO https://raw.githubusercontent.com/xXSalamanderXx/SlimBrave/main/SlimBrave-Linux.py && python3 SlimBrave-Linux.py
```

> [!IMPORTANT]
> If dependencies fail to auto-install via the script, please refer to this.
> 
> **Debian / Ubuntu / Linux Mint:**
> `sudo apt update && sudo apt install python3 python3-tk`
> 
> **Arch Linux / Manjaro:**
> `sudo pacman -S python tk`
> 
> **Fedora / RedHat / CentOS:**
> `sudo dnf install python3 python3-tkinter`

##
  
### Why SlimBrave Matters

In an era of increasingly bloated browsers, SlimBrave puts **you** back in control:

🚀 **Faster browsing** by removing unnecessary features.

🛡️ **Enhanced privacy and security** through granular controls.

⚙️ **Transparent customization** without hidden settings.

---

<p align="center">
  <b>⭐ Star the repo • ☕ Support development • 🚀 Explore more projects</b>
</p>

## ⭐ Show Your Support

If this repo has helped you, please consider giving it a **star** on GitHub!  
It really helps show support, motivates future updates, and encourages continued development. 🚀

Every ⭐ makes a difference and means a lot. Thanks for helping this project grow! 🙌

## ☕ Support Development

If you'd like to support my work even more, you can **buy me a coffee** here:  
[☕ buymeacoffee.com/SinZZzz](https://buymeacoffee.com/SinZZzz)

Your support helps keep development active and appreciated. 💙

## 🔍 Check Out My Other Repos

You might also like these projects:

[🔎 RLSBB-Search-Plus](https://github.com/xXSalamanderXx/RLSBB-Search-Plus)

[🎬 HDEncode-Search-Plus](https://github.com/xXSalamanderXx/HDEncode-Search-Plus)

[🦎 salamander-trackers](https://github.com/xXSalamanderXx/salamander-trackers)

[📷️ Caesium Image Compressor - Linux](https://github.com/xXSalamanderXx/caesium-image-compressor-linux)

---

## 🙌 Credit

Acknowledgment and thanks goes to the original creator:

[ltx0101/SlimBrave](https://github.com/ltx0101/SlimBrave)

---

## Disclaimer

This project is provided as-is, with no guarantees or warranties of any kind.

You are responsible for how you use the contents of this repository and for making sure your usage complies with any applicable laws, rules, or policies.

The author and contributors are not liable for any claims, damages, or other issues arising from the use of this project.

## License 📄

Licensed under the **GPL-3.0** license.  
See the full license here: [GPL-3.0 License](https://github.com/xXSalamanderXx/SlimBrave/blob/main/LICENSE)
