> [!CAUTION]
> This branch is purely for development and experimental use. Do not attempt to run any scripts from this branch.

<div align="center">

# SlimBrave - Revived

  <img src="https://i.postimg.cc/QCyWVFGN/SlimBrave.png" alt="SlimBrave Lion Logo" width="200"/>

A lightweight utility designed to give you ultimate control over your Brave Browser. Lock down telemetry, enforce strict privacy standards, and strip away built-in browser bloatware—all from a single, clean interface.

Supported on Windows and MacOS!
</div>

<br>

[![Release](https://img.shields.io/github/v/release/xXSalamanderXx/SlimBrave?style=for-the-badge)](https://github.com/xXSalamanderXx/SlimBrave/releases)
![](https://img.shields.io/badge/PowerShell-5391FE?style=for-the-badge&labelColor=ffffff&logoColor=5391FE&logo=powershell)
![](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&labelColor=FFD43B&logoColor=3776AB&logo=python)
[![License](https://img.shields.io/badge/License-GPL--3.0-blue?style=for-the-badge)](./LICENSE)

[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://buymeacoffee.com/SinZZzz)

> [!WARNING]
> This tool is currently not built for Linux.
> On Linux, it is recommended to use Brave Origin. Brave Origin is free to use on Linux and debloats Brave out of the box.

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

(Homebrew and Python will be automatically installed if you agree to the auto-installation upon running Slimbrave)

</details>


## 🚀 How to Use

## (Windows)

## Run the command below in PowerShell:
*Tip: Better if you run Powershell as Administrator*
> [!CAUTION]
> This branch is purely for development and experimental use. Do not attempt to run any scripts from this branch.
```ps1
iwr "https://raw.githubusercontent.com/xXSalamanderXx/SlimBrave/prerelease/SlimBrave.ps1" -OutFile "SlimBrave.ps1"; .\SlimBrave.ps1
```
## or

1. Download the `SlimBrave.ps1` script from the [Releases](https://github.com/xXSalamanderXx/SlimBrave/releases) page.
2. Right-click the file and select **Run with PowerShell**.
3. Accept the UAC prompt (Administrator privileges are required to modify registry policies).
4. Check the boxes for the features you wish to disable/enable.
5. Click **Apply Settings** and restart your Brave Browser.


## (MacOS)

## Run the command below in Terminal:
> [!CAUTION]
> This branch is purely for development and experimental use. Do not attempt to run any scripts from this branch.
```
curl -sO https://raw.githubusercontent.com/xXSalamanderXx/SlimBrave/prerelease/SlimBrave.py && python3 SlimBrave.py
```

##

> [!IMPORTANT]
> Presets are now built in, so using the presets below is no longer recommended.
> They still work, but they are deprecated and not updated for the new options available in 2026+.
## 📂 How to Use Presets
Instead of manually checking boxes, you can instantly load a pre-configured setup:
1. Download your desired preset `.json` file from the `Presets` folder in this repository.
2. Run `SlimBrave.ps1`.
3. Click the **Import Settings** button at the bottom of the window.
4. Select the downloaded `.json` file. The script will automatically check the correct boxes for that specific setup.
5. Click **Apply Settings**.

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
