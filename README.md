<div align="center">

# SlimBrave - Revived!
<img src="https://github.com/user-attachments/assets/3e90a996-a74a-4ca1-bea6-0869275bab58" width="200" height="300">
</div>

[![Release](https://img.shields.io/github/v/release/xXSalamanderXx/SlimBrave?style=for-the-badge)](https://github.com/xXSalamanderXx/SlimBrave/releases) [![Top language](https://img.shields.io/github/languages/top/xXSalamanderXx/SlimBrave?style=for-the-badge)](https://github.com/xXSalamanderXx/SlimBrave) [![License](https://img.shields.io/github/license/xXSalamanderXx/SlimBrave?style=for-the-badge)](./LICENSE)

---

## Brave Browser Fast Debloater

SlimBrave is a powerful PowerShell script designed for Windows users to streamline their Brave Browser experience by toggling and configuring unwanted features. With SlimBrave, you can easily disable or enable various Brave functionalities, customize settings, and improve privacy.

### Features:

<details>
<summary> Click here to view </summary>

- **Disable Brave Rewards**  
   Brave's reward system.

- **Disable Brave Wallet**  
   Brave's Wallet feature for managing cryptocurrencies.

- **Disable Brave VPN**  
   Brave's VPN feature for "enhanced" privacy.

- **Disable Brave AI Chat**  
   Brave's integrated AI Chat feature.

- **Disable Password Manager**  
   Brave's built-in password manager for website login credentials.

- **Disable Tor**  
   Tor functionality for "anonymous" browsing.

- **Set DNS Over HTTPS Mode**  
   Set the DNS Over HTTPS mode (options include automatic or off) to ensure private browsing with secure DNS queries.

- **Disable Sync**  
   Sync functionality that synchronizes your data across devices.

- **Telemetry & Reporting Controls**  
   Disable metrics reporting, safe browsing reporting, and data collection.

- **Privacy & Security Options**  
   Manage autofill, WebRTC, QUIC protocol, and more.

- **Performance Optimization**  
   Disable background processes and unnecessary features.

- **Enable Do Not Track**  
   Forces Do Not Track header for all browsing.

- **Force Google SafeSearch**  
   Enforces SafeSearch across Google searches.

- **Disable IPFS**  
   Disables InterPlanetary File System support.

- **Disable Spellcheck**  
   Disables browser spellcheck functionality.

- **Disable Browser Sign-in**  
   Prevents browser account sign-in.

- **Disable Printing**  
   Disables web page printing capability.

- **Disable Incognito Mode**  
   Blocks private browsing/incognito mode.

- **Disable Default Browser Prompt**  
   Stops Brave from asking to be default browser.

- **Disable Developer Tools**  
   Blocks access to developer tools.

- **Always Open PDF Externally**  
   Forces PDFs to open in external applications.

- **Disable Brave Shields**  
   Turns off Brave's built-in Shields protection.
</details>

---

# How to Run

### Run the command below in PowerShell:

```ps1
iwr "https://raw.githubusercontent.com/xXSalamanderXx/SlimBrave/main/SlimBrave.ps1" -OutFile "SlimBrave.ps1"; .\SlimBrave.ps1
```

---

## Extras:

<details>
<summary> Presets </summary>


- **Maximum Privacy Preset**  
   - Telemetry: Blocks all reporting (metrics, safe browsing, URL collection, feedback).
   - Privacy: Disables autofill, password manager, sign-in, WebRTC leaks, QUIC, and forces Do Not Track.
   - Brave Features: Kills Rewards, Wallet, VPN, AI Chat, Tor, and Sync.
   - Performance: Disables background processes, recommendations, and bloat.
   - DNS: Uses plain DNS (no HTTPS) to prevent potential logging by DoH providers.
   - Best for: Paranoid users, journalists, activists, or anyone who wants Brave as private as possible.

- **Balanced Privacy Preset**  
   - Telemetry: Blocks all tracking but keeps basic safe browsing.
   - Privacy: Blocks third-party cookies, enables Do Not Track, but allows password manager and autofill for addresses.
   - Brave Features: Disables Rewards, Wallet, VPN, and AI features.
   - Performance: Turns off background services and ads.
   - DNS: Uses automatic DoH (lets Brave choose the fastest secure DNS).
   - Best for: Most users who want privacy but still need convenience features.

- **Performance Focused Preset**  
   - Telemetry: Only blocks metrics and feedback surveys (keeps some safe browsing).
   - Brave Features: Disables Rewards, Wallet, VPN, and AI to declutter the browser.
   - Performance: Kills background processes, shopping features, and promotions.
   - DNS: Automatic DoH for a balance of speed and security.
   - Best for: Users who want a faster, cleaner Brave without extreme privacy tweaks.

- **Developer Preset**  
   - Telemetry: Blocks all reporting.
   - Brave Features: Disables Rewards, Wallet, and VPN but keeps developer tools.
   - Performance: Turns off background services and ads.
   - DNS: Automatic DoH (default secure DNS).
   - Best for: Developers who need dev tools but still want telemetry and ads disabled.

- **Strict Parental Controls Preset**  
   - Privacy: Blocks incognito mode, forces Google SafeSearch, and disables sign-in.
   - Brave Features: Disables Rewards, Wallet, VPN, Tor, and dev tools.
   - DNS: Uses custom DoH (can be set to a family-friendly DNS like Cloudflare for Families).
   - Best for: Parents, schools, or workplaces that need restricted browsing.


</details>



<details>
<summary> Requirements </summary>

- Windows 10/11
- PowerShell
- Administrator privileges
</details>

<details>
<summary>Error "Running Scripts is Disabled on this System"</summary>

### Run this command in PowerShell:

```ps1
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned
```
</details>
<div align="center">
  
---

### Why SlimBrave Matters

In an era of increasingly bloated browsers, SlimBrave puts **you** back in control:

🚀 **Faster browsing** by removing unnecessary features

🛡️ **Enhanced privacy** through granular controls

⚙️ **Transparent customization** without hidden settings

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



