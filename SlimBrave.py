#!/usr/bin/env python3
# SlimBrave - Revived - v1.1.0 (macOS Edition)
# Fixes:
# - Safe full-domain snapshot/restore for Reset All
# - Managed-key-only apply path
# - Robust plist restore using plistlib (binary/XML/backup.plist supported)
# - Cache cleanup during reset/restore
# - No in-place mutation of the user's plist during import

import subprocess
import sys
import os
import shutil
import time
import base64


BREW_INSTALLED_SOMETHING = False


def print_step(msg):
    print(f"\n[SlimBrave] {msg}")


def prompt_yes_no(question):
    while True:
        ans = input(f"{question} [y/n]: ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Please answer 'y' or 'n'.")


def get_brew_prefix():
    if os.path.exists("/opt/homebrew/bin/brew"):
        return "/opt/homebrew"
    if os.path.exists("/usr/local/bin/brew"):
        return "/usr/local"
    return None


def check_homebrew():
    global BREW_INSTALLED_SOMETHING
    if shutil.which("brew"):
        print_step("Homebrew found.")
        return True

    print_step("Homebrew not found.")
    print("Homebrew is required if you want SlimBrave to bootstrap a modern")
    print("Python/Tk environment automatically on macOS.")
    if not prompt_yes_no("Install Homebrew now?"):
        print_step("Cannot continue without Homebrew. Exiting.")
        sys.exit(1)

    print_step("Installing Homebrew – this may take a few minutes…")
    install_cmd = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    try:
        subprocess.run(install_cmd, shell=True, check=True)
    except subprocess.CalledProcessError:
        print_step("Homebrew installation failed. Please install it manually from https://brew.sh")
        sys.exit(1)

    brew_prefix = get_brew_prefix()
    if brew_prefix:
        os.environ["PATH"] = f"{brew_prefix}/bin:{os.environ['PATH']}"

    if shutil.which("brew"):
        BREW_INSTALLED_SOMETHING = True
        print_step("Homebrew installed successfully.")
        return True

    print_step("Homebrew still not available. Exiting.")
    sys.exit(1)


def is_homebrew_python():
    brew_prefix = get_brew_prefix()
    if not brew_prefix:
        return False
    return os.path.abspath(sys.executable).startswith(brew_prefix)


def get_tk_version():
    try:
        import tkinter
        return tkinter.TkVersion
    except Exception:
        return 0


def check_python_and_tk():
    global BREW_INSTALLED_SOMETHING
    brew_prefix = get_brew_prefix()
    if not brew_prefix:
        return

    print_step(f"Current Python: {sys.executable}")

    if not is_homebrew_python():
        print_step("You are using the system Python, which often ships with an old/deprecated Tcl/Tk.")
        if prompt_yes_no("Install Homebrew Python with Tkinter now?"):
            print_step("Installing Homebrew Python + Tk…")
            subprocess.run(["brew", "install", "python-tk"], check=True)
            BREW_INSTALLED_SOMETHING = True
            new_python = f"{brew_prefix}/bin/python3"
            if not os.path.exists(new_python):
                print_step("Installation succeeded but could not find the new Python binary. Exiting.")
                sys.exit(1)
            print_step(f"Relaunching with {new_python} …")
            os.execv(new_python, [new_python] + sys.argv)
        else:
            print_step("A modern Python/Tk is required. Exiting.")
            sys.exit(1)

    tk_ver = get_tk_version()
    print_step(f"Tk version: {tk_ver}")
    if tk_ver < 8.6:
        print_step("Your Tkinter is outdated.")
        if prompt_yes_no("Install/upgrade python-tk via Homebrew?"):
            print_step("Installing python-tk…")
            subprocess.run(["brew", "install", "python-tk"], check=True)
            BREW_INSTALLED_SOMETHING = True
            print_step("Relaunching to use the updated Tk…")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print_step("Cannot run without a working Tk. Exiting.")
            sys.exit(1)


def run_cleanup():
    if shutil.which("brew") and BREW_INSTALLED_SOMETHING:
        print_step("Running brew cleanup…")
        subprocess.run(["brew", "cleanup"], check=False)


def dependency_setup():
    print("=" * 60)
    print(" SlimBrave – Dependency Check")
    print("=" * 60)

    check_homebrew()
    check_python_and_tk()
    run_cleanup()

    print_step("All required dependencies OK. Launching SlimBrave interface…")
    time.sleep(1)


def main():
    import json
    import plistlib
    import tempfile
    import datetime
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog

    DOMAIN = "com.brave.Browser"
    CONFIG_DIR = os.path.expanduser("~/.config/slimbrave")
    STATE_FILE = os.path.join(CONFIG_DIR, "SlimBraveState.json")
    LOG_FILE = os.path.join(CONFIG_DIR, "SlimBrave.log")
    SNAPSHOT_FILE = os.path.join(CONFIG_DIR, "BraveFullDomainBeforeSlimBrave.plist")
    LAST_EXPORT_FILE = os.path.join(CONFIG_DIR, "LastBraveDomainBackup.plist")

    BRAVE_SUPPORT_DIR = os.path.expanduser("~/Library/Application Support/BraveSoftware/Brave-Browser")
    BRAVE_CACHE_DIR = os.path.expanduser("~/Library/Caches/BraveSoftware/Brave-Browser")
    USER_MANAGED_PREFS = os.path.expanduser(f"~/Library/Managed Preferences/{DOMAIN}.plist")
    SYSTEM_MANAGED_PREFS = f"/Library/Managed Preferences/{DOMAIN}.plist"

    os.makedirs(CONFIG_DIR, exist_ok=True)

    def write_log(message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} - {message}\n")

    write_log("SlimBrave macOS UI Initializing...")

    telemetry_features = [
        {"Name": "Disable Metrics Reporting", "Key": "MetricsReportingEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Stops Brave from sending anonymous usage and crash reports.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Safe Browsing Reporting", "Key": "SafeBrowsingExtendedReportingEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Stops Brave from sending extended Safe Browsing data back to servers.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable URL Data Collection", "Key": "UrlKeyedAnonymizedDataCollectionEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Stops sending anonymized URLs to help improve the browser.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Feedback Surveys", "Key": "FeedbackSurveysEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Disables proactive feedback survey prompts.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable P3A Telemetry", "Key": "BraveP3AEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Disables Privacy-Preserving Product Analytics completely.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Daily Stats Ping", "Key": "BraveStatsPingEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Stops the daily active user ping.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Web Discovery", "Key": "BraveWebDiscoveryEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Prevents anonymous search/browsing data from being sent to Brave Search.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
    ]

    privacy_features = [
        {"Name": "Disable Autofill (Addresses)", "Key": "AutofillAddressEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Disables saving and autofilling addresses.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Autofill (Credit Cards)", "Key": "AutofillCreditCardEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Disables saving and autofilling credit cards.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Password Manager", "Key": "PasswordManagerEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Disables the built-in password manager.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Browser Sign-in", "Key": "BrowserSignin", "Value": 0, "Type": "int",
         "ToolTip": "Prevents syncing your data to cloud accounts.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable WebRTC IP Leak", "Key": "WebRtcIPHandling", "Value": "disable_non_proxied_udp", "Type": "string",
         "ToolTip": "Prevents your real IP address from leaking when using a VPN.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable QUIC Protocol", "Key": "QuicAllowed", "Value": False, "Type": "bool",
         "ToolTip": "Forces standard TCP, stopping UDP firewall bypasses and tracking.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Block Third Party Cookies", "Key": "BlockThirdPartyCookies", "Value": True, "Type": "bool",
         "ToolTip": "Blocks all third-party tracking cookies.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Enable Do Not Track", "Key": "EnableDoNotTrack", "Value": True, "Type": "bool",
         "ToolTip": "Sends a Do Not Track request with your browsing traffic.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Force Google SafeSearch", "Key": "ForceGoogleSafeSearch", "Value": True, "Type": "bool",
         "ToolTip": "Filters explicit search results.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Disable IPFS", "Key": "IPFSEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Stops peer-to-peer background connections to unknown nodes.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Force Incognito Mode", "Key": "IncognitoModeAvailability", "Value": 2, "Type": "int",
         "ToolTip": "Forces the browser to always open in Incognito Mode.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Force Download Prompts", "Key": "PromptForDownloadLocation", "Value": True, "Type": "bool",
         "ToolTip": "Forces Brave to ask where to save a file before downloading, preventing drive-by downloads.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Clear Data on Exit", "Key": "ClearBrowsingDataOnExitList", "Value": [
            "browsing_history",
            "download_history",
            "cookies_and_other_site_data",
            "cached_images_and_files",
            "password_signin",
            "autofill",
            "site_settings",
            "hosted_app_data"
        ], "Type": "array",
         "ToolTip": "Wipes all cookies, cache, and browsing history the moment the browser closes.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Force HTTPS-Only Mode", "Key": "HttpsOnlyMode", "Value": "force_enabled", "Type": "string",
         "ToolTip": "Strictly upgrades all connections to HTTPS and blocks unencrypted HTTP traffic.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
    ]

    brave_features = [
        {"Name": "Disable Brave Rewards and Sponsored Elements", "Key": "BraveRewardsDisabled", "Value": True, "Type": "bool",
         "ToolTip": "Completely disables the Brave Crypto Rewards system and disables sponsored backgrounds on the New Tab page.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave Wallet", "Key": "BraveWalletDisabled", "Value": True, "Type": "bool",
         "ToolTip": "Disables the built-in Brave Crypto Wallet.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave VPN", "Key": "BraveVPNDisabled", "Value": True, "Type": "bool",
         "ToolTip": "Removes the Brave VPN integration and prompts.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave AI Chat", "Key": "BraveAIChatEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Disables Brave Leo (AI Chat) integration.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Tor", "Key": "TorDisabled", "Value": True, "Type": "bool",
         "ToolTip": "Disables built-in Tor window support.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Sync", "Key": "SyncDisabled", "Value": True, "Type": "bool",
         "ToolTip": "Disables Brave Sync functionality across devices.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Disable Brave News", "Key": "BraveNewsDisabled", "Value": True, "Type": "bool",
         "ToolTip": "Removes the Brave News feed bloat from the New Tab page.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave Talk", "Key": "BraveTalkDisabled", "Value": True, "Type": "bool",
         "ToolTip": "Removes the built-in video calling integration.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Speedreader", "Key": "BraveSpeedreaderEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Completely disables the Speedreader feature, reader mode, and automatic prompts.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Wayback Machine Prompts", "Key": "BraveWaybackMachineEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Stops Brave from asking to search the Internet Archive when you hit a 404 error.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
    ]

    perf_features = [
        {"Name": "Disable Background Mode", "Key": "BackgroundModeEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Prevents extensions/apps from running after the browser is closed.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Media Recommendations", "Key": "MediaRecommendationsEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Disables media recommendations to save memory.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Shopping List", "Key": "ShoppingListEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Disables the shopping list feature.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Always Open PDF Externally", "Key": "AlwaysOpenPdfExternally", "Value": True, "Type": "bool",
         "ToolTip": "Forces PDFs to download and open in your system viewer instead of the browser.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Translate", "Key": "TranslateEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Disables automatic translation prompts.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Spellcheck", "Key": "SpellcheckEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Disables the built-in spellchecker to save CPU cycles.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Promotions", "Key": "PromotionsEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Disables Brave promotional notifications.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Search Suggestions", "Key": "SearchSuggestEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Disables predictive search suggestions in the URL bar.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Printing", "Key": "PrintingEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Disables the browser print function.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Default Browser Prompt", "Key": "DefaultBrowserSettingEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Stops Brave from asking to be the default browser.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Developer Tools", "Key": "DeveloperToolsDisabled", "Value": True, "Type": "bool",
         "ToolTip": "Disables F12 / Inspect Element.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Disable Brave Playlist", "Key": "BravePlaylistEnabled", "Value": False, "Type": "bool",
         "ToolTip": "Removes the Brave Playlist media feature.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
    ]

    permission_settings = [
        {"Name": "Location", "Key": "DefaultGeolocationSetting", "Options": ["Not Set", "Ask", "Block", "Allow"],
         "ToolTip": "Allows sites to request your physical location.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Camera", "Key": "DefaultVideoCaptureSetting", "Options": ["Not Set", "Ask", "Block"],
         "ToolTip": "Allows sites to record video via your webcam.\n\nSuggested Settings for Privacy: Ask | Security: Ask"},
        {"Name": "Microphone", "Key": "DefaultAudioCaptureSetting", "Options": ["Not Set", "Ask", "Block"],
         "ToolTip": "Allows sites to record audio via your microphone.\n\nSuggested Settings for Privacy: Ask | Security: Ask"},
        {"Name": "Notifications", "Key": "DefaultNotificationsSetting", "Options": ["Not Set", "Ask", "Block", "Allow"],
         "ToolTip": "Allows sites to send you native desktop push notifications.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "JavaScript", "Key": "DefaultJavaScriptSetting", "Options": ["Not Set", "Allow", "Block"],
         "ToolTip": "Allows sites to run interactive scripts. Blocking this breaks almost all websites.\n\nSuggested Settings for Privacy: Allow | Security: Allow"},
        {"Name": "Images", "Key": "DefaultImagesSetting", "Options": ["Not Set", "Allow", "Block"],
         "ToolTip": "Allows sites to load and display images.\n\nSuggested Settings for Privacy: Not Set | Security: Not Set"},
        {"Name": "Pop-ups and Redirects", "Key": "DefaultPopupsSetting", "Options": ["Not Set", "Block", "Allow"],
         "ToolTip": "Allows sites to open new windows or redirect you without your input.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "USB Devices", "Key": "DefaultWebUsbGuardSetting", "Options": ["Not Set", "Ask", "Block"],
         "ToolTip": "Allows sites to request direct connection to your plugged-in USB devices.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Serial Ports", "Key": "DefaultSerialGuardSetting", "Options": ["Not Set", "Ask", "Block"],
         "ToolTip": "Allows sites to request connection to hardware via serial ports.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "HID Devices", "Key": "DefaultWebHidGuardSetting", "Options": ["Not Set", "Ask", "Block"],
         "ToolTip": "Allows sites to request access to Human Interface Devices (e.g. controllers).\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "File Editing", "Key": "DefaultFileSystemReadGuardSetting", "Options": ["Not Set", "Ask", "Block"],
         "ToolTip": "Allows sites to read and save files directly to your local file system.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Clipboard", "Key": "DefaultClipboardSetting", "Options": ["Not Set", "Ask", "Block"],
         "ToolTip": "Allows sites to read text and images copied to your clipboard.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Window Management", "Key": "DefaultWindowPlacementSetting", "Options": ["Not Set", "Ask", "Block", "Allow"],
         "ToolTip": "Allows sites to open windows on specific monitors or in fullscreen.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Local Fonts", "Key": "DefaultLocalFontsSetting", "Options": ["Not Set", "Ask", "Block"],
         "ToolTip": "Allows sites to fingerprint your device based on locally installed fonts.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Payment Handlers", "Key": "PaymentMethodQueryEnabled", "Options": ["Not Set", "Block", "Allow"],
         "ToolTip": "Allows sites to check if you have local payment apps installed.\n\nSuggested Settings for Privacy: Block | Security: Block"},
    ]

    ALL_FEATURES = telemetry_features + privacy_features + brave_features + perf_features
    MANAGED_KEYS = {item["Key"] for item in ALL_FEATURES}
    MANAGED_KEYS.update({item["Key"] for item in permission_settings})
    MANAGED_KEYS.update({
        "DefaultFileSystemWriteGuardSetting",
        "SafeBrowsingProtectionLevel",
        "DnsOverHttpsMode",
    })

    root = tk.Tk()
    root.title("SlimBrave - Revived v1.1.0 (macOS)")
    root.geometry("1040x550")
    root.minsize(900, 400)
    root.configure(bg="#191919")

    transparent_gif = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
    icon_img = tk.PhotoImage(master=root, data=base64.b64decode(transparent_gif))
    root.iconphoto(False, icon_img)

    class ToolTip:
        def __init__(self, widget, text):
            self.widget = widget
            self.text = text
            self.tooltip_window = None
            self.show_id = None
            self.widget.bind("<Enter>", self.on_enter)
            self.widget.bind("<Leave>", self.on_leave)

        def on_enter(self, event=None):
            if self.show_id:
                self.widget.after_cancel(self.show_id)
            self.show_id = self.widget.after(800, self.show)

        def on_leave(self, event=None):
            if self.show_id:
                self.widget.after_cancel(self.show_id)
                self.show_id = None
            self.hide()

        def show(self):
            if self.tooltip_window:
                return
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + 25
            self.tooltip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            label = tk.Label(
                tw,
                text=self.text,
                justify="left",
                background="#2d2d2d",
                foreground="white",
                relief="solid",
                borderwidth=1,
                font=("sans-serif", 10, "normal"),
                padx=8,
                pady=6,
                wraplength=420,
            )
            label.pack(ipadx=1)

        def hide(self):
            if self.tooltip_window:
                self.tooltip_window.destroy()
                self.tooltip_window = None

    def create_tooltip(widget, text):
        ToolTip(widget, text)

    style = ttk.Style()
    style.theme_use("clam")

    style.configure("TCheckbutton", background="#232323", foreground="white", font=("sans-serif", 9))
    style.map("TCheckbutton", background=[("active", "#232323")])

    style.configure(
        "Dark.TCombobox",
        fieldbackground="#161616",
        background="#161616",
        foreground="white",
        arrowcolor="white",
        selectbackground="#333333",
        selectforeground="white",
    )
    style.map(
        "Dark.TCombobox",
        fieldbackground=[("readonly", "#161616")],
        background=[("readonly", "#161616")],
        selectbackground=[("readonly", "#333333")],
        selectforeground=[("readonly", "white")],
    )

    style.configure(
        "Dark.Vertical.TScrollbar",
        background="#333333",
        troughcolor="#1a1a1a",
        bordercolor="#1a1a1a",
        arrowcolor="white",
        relief="flat",
    )
    style.map("Dark.Vertical.TScrollbar", background=[("active", "#555555")])

    button_padding = (15, 8)
    button_styles = {
        "Orange.TButton": "#E65100",
        "Export.TButton": "#0D47A1",
        "Import.TButton": "#1976D2",
        "Pull.TButton": "#F57F17",
        "Apply.TButton": "#2E7D32",
        "Reset.TButton": "#C62828",
        "Plist.TButton": "#6A1B9A",
    }
    active_styles = {
        "Orange.TButton": "#BF360C",
        "Export.TButton": "#0A3D91",
        "Import.TButton": "#1565C0",
        "Pull.TButton": "#E65100",
        "Apply.TButton": "#1B5E20",
        "Reset.TButton": "#B71C1C",
        "Plist.TButton": "#4A148C",
    }
    for sty, color in button_styles.items():
        style.configure(
            sty,
            background=color,
            foreground="white",
            font=("sans-serif", 9 if sty != "Orange.TButton" else 10, "bold"),
            borderwidth=0,
            relief="flat",
            padding=button_padding,
        )
        style.map(sty, background=[("active", active_styles[sty])], foreground=[("active", "white")])

    global_is_dirty = False
    suspend_dirty_tracking = False
    baseline_state = ""
    all_feature_vars = {}
    all_perm_vars = {}

    status_var = tk.StringVar(value="Ready. Hover over options for details.")
    save_status_var = tk.StringVar(value="Changes Applied ✔")

    def set_status(msg):
        status_var.set(msg)
        write_log(msg)
        root.update_idletasks()

    def set_dirty_state(is_dirty):
        nonlocal global_is_dirty
        if suspend_dirty_tracking:
            return
        global_is_dirty = is_dirty
        if is_dirty:
            save_status_var.set("Changes Need To Be Saved.....")
            save_status_label.config(fg="#FFD700")
        else:
            save_status_var.set("Changes Applied ✔")
            save_status_label.config(fg="#90EE90")

    def get_ui_snapshot():
        return {
            "Features": [key for key, var in all_feature_vars.items() if var.get() == 1],
            "Permissions": {key: var.get() for key, var in all_perm_vars.items() if var.get() != "Not Set"},
            "SafeBrowsing": sb_var.get(),
            "DnsMode": dns_var.get(),
        }

    def update_baseline():
        nonlocal baseline_state
        baseline_state = json.dumps(get_ui_snapshot(), sort_keys=True)

    def check_dirty_state(*args):
        if suspend_dirty_tracking:
            return
        current_json = json.dumps(get_ui_snapshot(), sort_keys=True)
        set_dirty_state(current_json != baseline_state)

    def save_current_state():
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(get_ui_snapshot(), f, indent=4)
            write_log(f"State baseline saved to {STATE_FILE}")
        except Exception as e:
            write_log(f"Failed to save state baseline: {e}")

    def run_cmd(cmd, check=False):
        return subprocess.run(cmd, capture_output=True, text=True, check=check)

    def normalize_bool(val):
        if isinstance(val, bool):
            return val
        if isinstance(val, int):
            return bool(val)
        if isinstance(val, str):
            s = val.strip().lower()
            if s in {"1", "true", "yes", "on"}:
                return True
            if s in {"0", "false", "no", "off"}:
                return False
        return None

    def load_plist_file(path):
        with open(path, "rb") as f:
            data = plistlib.load(f)
        if not isinstance(data, dict):
            raise ValueError("The selected plist does not contain a dictionary at the root.")
        return data

    def write_xml_plist(path, data):
        with open(path, "wb") as f:
            plistlib.dump(data, f, fmt=plistlib.FMT_XML, sort_keys=True)

    def export_current_domain_dict():
        fd, tmp_path = tempfile.mkstemp(suffix=".plist")
        os.close(fd)
        try:
            res = run_cmd(["defaults", "export", DOMAIN, tmp_path])
            if res.returncode != 0:
                return {}
            return load_plist_file(tmp_path)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def import_domain_dict(domain_dict):
        fd, tmp_path = tempfile.mkstemp(suffix=".plist")
        os.close(fd)
        try:
            write_xml_plist(tmp_path, domain_dict)
            res = run_cmd(["defaults", "import", DOMAIN, tmp_path])
            if res.returncode != 0:
                err = res.stderr.strip() or res.stdout.strip() or "defaults import failed"
                raise RuntimeError(err)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def wrap_backup_payload(kind, payload):
        return {
            "__SlimBrave__": {
                "format_version": 2,
                "kind": kind,
                "created": datetime.datetime.now().isoformat(timespec="seconds"),
            },
            "Payload": payload,
        }

    def extract_backup_payload(data):
        if "__SlimBrave__" in data and isinstance(data.get("Payload"), dict):
            return data["__SlimBrave__"].get("kind", ""), data["Payload"]
        return "", data

    def save_snapshot_if_missing():
        if os.path.exists(SNAPSHOT_FILE):
            return
        payload = export_current_domain_dict()
        write_xml_plist(SNAPSHOT_FILE, wrap_backup_payload("full_domain_backup", payload))
        write_log(f"Created pre-SlimBrave full-domain snapshot at {SNAPSHOT_FILE}")

    def export_domain_backup(path):
        payload = export_current_domain_dict()
        write_xml_plist(path, wrap_backup_payload("full_domain_backup", payload))
        write_log(f"Exported Brave full-domain backup to {path}")

    def remove_path(path):
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path, ignore_errors=True)
            elif os.path.exists(path):
                os.remove(path)
        except Exception as e:
            write_log(f"Failed removing {path}: {e}")

    def clear_applicable_caches():
        cache_paths = [
            BRAVE_CACHE_DIR,
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "Cache"),
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "Code Cache"),
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "GPUCache"),
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "DawnCache"),
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "GrShaderCache"),
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "ShaderCache"),
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "Service Worker", "CacheStorage"),
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "Service Worker", "ScriptCache"),
            os.path.join(BRAVE_SUPPORT_DIR, "Crashpad", "completed"),
            os.path.join(BRAVE_SUPPORT_DIR, "Crashpad", "reports"),
            os.path.join(BRAVE_SUPPORT_DIR, "SingletonLock"),
            os.path.join(BRAVE_SUPPORT_DIR, "SingletonCookie"),
            os.path.join(BRAVE_SUPPORT_DIR, "SingletonSocket"),
        ]
        for path in cache_paths:
            if os.path.exists(path):
                remove_path(path)
                write_log(f"Removed cache/state path: {path}")

    def flush_pref_cache():
        run_cmd(["killall", "cfprefsd"])
        time.sleep(0.5)

    def brave_is_running():
        res = run_cmd(["pgrep", "-if", "Brave Browser"])
        return res.returncode == 0 and bool(res.stdout.strip())

    def wait_for_brave_exit(timeout=8):
        end = time.time() + timeout
        while time.time() < end:
            if not brave_is_running():
                return True
            time.sleep(0.35)
        return not brave_is_running()

    def stop_brave_for_operation(operation_name):
        if not brave_is_running():
            return True

        ok = messagebox.askokcancel(
            "Close Brave Required",
            f"Brave is currently running.\n\n"
            f"It must be fully closed before {operation_name} so it cannot re-save or overwrite"
            f" the preference domain during the operation.\n\n"
            f"Click OK to close Brave and continue.",
        )
        if not ok:
            set_status("Operation cancelled by user.")
            return False

        set_status("Closing Brave cleanly…")
        run_cmd(["osascript", "-e", 'tell application "Brave Browser" to quit'])
        if wait_for_brave_exit(6):
            return True

        set_status("Brave still running, sending TERM to Brave processes…")
        run_cmd(["pkill", "-TERM", "-if", "Brave Browser"])
        wait_for_brave_exit(4)
        run_cmd(["pkill", "-TERM", "-if", "Brave Browser Helper"])
        if wait_for_brave_exit(4):
            return True

        set_status("Brave still running, forcing final shutdown…")
        run_cmd(["pkill", "-KILL", "-if", "Brave Browser"])
        run_cmd(["pkill", "-KILL", "-if", "Brave Browser Helper"])
        time.sleep(1.0)

        if brave_is_running():
            messagebox.showerror(
                "Brave Still Running",
                "SlimBrave could not stop all Brave processes.\n\n"
                "Please close Brave manually and try again."
            )
            return False
        return True

    def remove_managed_pref_files():
        for path in (USER_MANAGED_PREFS, SYSTEM_MANAGED_PREFS):
            if os.path.exists(path):
                try:
                    os.remove(path)
                    write_log(f"Removed managed preferences file: {path}")
                except Exception as e:
                    write_log(f"Could not remove managed prefs file {path}: {e}")

    def ui_to_managed_payload():
        payload = {}

        for feat in ALL_FEATURES:
            if all_feature_vars[feat["Key"]].get() == 1:
                payload[feat["Key"]] = feat["Value"]

        for perm in permission_settings:
            sel = all_perm_vars[perm["Key"]].get()
            key = perm["Key"]
            if sel == "Not Set":
                continue
            if key == "PaymentMethodQueryEnabled":
                if sel == "Block":
                    payload[key] = 0
                elif sel == "Allow":
                    payload[key] = 1
                continue

            val = None
            if sel == "Ask":
                val = 3
            elif sel == "Block":
                val = 2
            elif sel == "Allow":
                val = 1

            if val is not None:
                payload[key] = val
                if key == "DefaultFileSystemReadGuardSetting":
                    payload["DefaultFileSystemWriteGuardSetting"] = val

        if sb_var.get() == "On":
            payload["SafeBrowsingProtectionLevel"] = 1
        elif sb_var.get() == "Off":
            payload["SafeBrowsingProtectionLevel"] = 0

        if dns_var.get() == "On":
            payload["DnsOverHttpsMode"] = "automatic"
        elif dns_var.get() == "Off":
            payload["DnsOverHttpsMode"] = "off"

        return payload

    def apply_managed_payload(payload):
        domain_dict = export_current_domain_dict()

        for key in MANAGED_KEYS:
            domain_dict.pop(key, None)

        domain_dict.update(payload)
        import_domain_dict(domain_dict)
        flush_pref_cache()

    def restore_full_domain_payload(payload):
        import_domain_dict(payload)
        flush_pref_cache()

    def filter_managed_keys_from_plist(data):
        filtered = {}
        for key in MANAGED_KEYS:
            if key in data:
                filtered[key] = data[key]
        return filtered

    def reload_ui_from_registry():
        nonlocal suspend_dirty_tracking
        suspend_dirty_tracking = True

        for var in all_feature_vars.values():
            var.set(0)
        for var in all_perm_vars.values():
            var.set("Not Set")
        sb_var.set("")
        dns_var.set("")

        domain_data = export_current_domain_dict()
        any_loaded = False

        for feat in ALL_FEATURES:
            key = feat["Key"]
            if key not in domain_data:
                continue
            any_loaded = True
            value = domain_data.get(key)

            if feat["Type"] == "array":
                if isinstance(value, list) and len(value) > 0:
                    all_feature_vars[key].set(1)
            elif feat["Type"] == "bool":
                if normalize_bool(value) == feat["Value"]:
                    all_feature_vars[key].set(1)
            else:
                if value == feat["Value"]:
                    all_feature_vars[key].set(1)

        for perm in permission_settings:
            key = perm["Key"]
            value = domain_data.get(key)

            if value is None and key == "DefaultFileSystemReadGuardSetting":
                value = domain_data.get("DefaultFileSystemWriteGuardSetting")

            if value is None:
                continue

            any_loaded = True

            try:
                value = int(value)
            except Exception:
                continue

            if key == "PaymentMethodQueryEnabled":
                if value == 0:
                    all_perm_vars[key].set("Block")
                elif value == 1:
                    all_perm_vars[key].set("Allow")
                continue

            if value == 3:
                all_perm_vars[key].set("Ask")
            elif value == 2:
                all_perm_vars[key].set("Block")
            elif value == 1:
                all_perm_vars[key].set("Allow")

        sb_val = domain_data.get("SafeBrowsingProtectionLevel")
        if sb_val is not None:
            any_loaded = True
            try:
                sb_int = int(sb_val)
                if sb_int == 1:
                    sb_var.set("On")
                elif sb_int == 0:
                    sb_var.set("Off")
            except Exception:
                pass

        dns_val = domain_data.get("DnsOverHttpsMode")
        if isinstance(dns_val, str):
            any_loaded = True
            dns_val = dns_val.strip().lower()
            if dns_val == "automatic":
                dns_var.set("On")
            elif dns_val == "off":
                dns_var.set("Off")

        suspend_dirty_tracking = False
        update_baseline()
        check_dirty_state()

        if not any_loaded:
            set_status("No SlimBrave-managed Brave policy settings found.")
        else:
            set_status("UI reloaded from current Brave macOS preference domain.")

    def export_settings():
        f = filedialog.asksaveasfilename(defaultextension=".json", initialfile="SlimBraveSettings.json")
        if not f:
            return
        with open(f, "w", encoding="utf-8") as file:
            json.dump(get_ui_snapshot(), file, indent=4)
        set_status(f"Settings exported to {f}")

    def import_settings():
        f = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not f:
            return

        with open(f, "r", encoding="utf-8") as file:
            data = json.load(file)

        nonlocal suspend_dirty_tracking
        suspend_dirty_tracking = True

        for var in all_feature_vars.values():
            var.set(0)
        for var in all_perm_vars.values():
            var.set("Not Set")

        for key in data.get("Features", []):
            if key in all_feature_vars:
                all_feature_vars[key].set(1)

        for key, val in data.get("Permissions", {}).items():
            if key in all_perm_vars:
                all_perm_vars[key].set(val)

        sb_var.set(data.get("SafeBrowsing", ""))
        dns_var.set(data.get("DnsMode", ""))

        suspend_dirty_tracking = False
        check_dirty_state()
        set_status("Settings imported from JSON. Pending save.")

    def import_plist():
        f = filedialog.askopenfilename(
            filetypes=[("Property List / XML", "*.plist *.xml"), ("All files", "*.*")]
        )
        if not f:
            return

        try:
            raw = load_plist_file(f)
            kind, payload = extract_backup_payload(raw)

            if not stop_brave_for_operation("restoring Brave settings"):
                return

            set_status("Restoring Brave settings from plist…")

            if kind == "full_domain_backup":
                restore_full_domain_payload(payload)
                clear_applicable_caches()
                reload_ui_from_registry()
                set_dirty_state(False)
                messagebox.showinfo(
                    "Restore Successful",
                    "Full Brave preference-domain backup restored successfully.\n"
                    "Applicable caches were also cleared."
                )
                return

            if kind == "managed_policy_backup":
                apply_managed_payload(payload)
                clear_applicable_caches()
                reload_ui_from_registry()
                set_dirty_state(False)
                messagebox.showinfo(
                    "Restore Successful",
                    "SlimBrave managed keys were restored successfully.\n"
                    "Applicable caches were also cleared."
                )
                return

            filtered = filter_managed_keys_from_plist(payload)
            if filtered:
                apply_managed_payload(filtered)
                clear_applicable_caches()
                reload_ui_from_registry()
                set_dirty_state(False)
                messagebox.showinfo(
                    "Restore Successful",
                    "Managed Brave keys were extracted from the selected plist and restored successfully.\n"
                    "Applicable caches were also cleared."
                )
                return

            if messagebox.askyesno(
                "Plain Backup Detected",
                "This plist does not look like a SlimBrave-wrapped backup and does not contain only "
                "recognized SlimBrave keys.\n\n"
                "Do you want to restore it as a full Brave preference-domain backup anyway?\n\n"
                "Use YES only if this is a Brave backup.plist / defaults export you trust."
            ):
                restore_full_domain_payload(payload)
                clear_applicable_caches()
                reload_ui_from_registry()
                set_dirty_state(False)
                messagebox.showinfo(
                    "Restore Successful",
                    "Plain Brave plist restored as a full-domain backup.\n"
                    "Applicable caches were also cleared."
                )
            else:
                set_status("Restore cancelled.")
        except Exception as e:
            write_log(f"Plist restore failed: {e}")
            messagebox.showerror(
                "Restore Failed",
                "Failed to restore the selected plist.\n\n"
                f"{e}\n\n"
                "This version reads plist files natively with plistlib, so if this still fails the file itself "
                "is likely malformed or not a plist dictionary."
            )

    def apply_settings():
        if not stop_brave_for_operation("applying settings"):
            return

        try:
            save_snapshot_if_missing()

            if messagebox.askyesno(
                "Backup Settings",
                "Would you like to export your current Brave settings to a safe XML .plist backup on your Desktop "
                "before applying changes? (Recommended)"
            ):
                backup_path = os.path.expanduser("~/Desktop/Brave_Policies_Backup.plist")
                export_domain_backup(backup_path)
                write_xml_plist(LAST_EXPORT_FILE, wrap_backup_payload("full_domain_backup", export_current_domain_dict()))

            set_status("Applying SlimBrave settings safely…")
            payload = ui_to_managed_payload()
            apply_managed_payload(payload)

            save_current_state()
            update_baseline()
            check_dirty_state()

            set_status("Settings applied successfully.")
            messagebox.showinfo("SlimBrave", "Settings applied successfully. Open Brave to test.")
        except Exception as e:
            write_log(f"Apply failed: {e}")
            messagebox.showerror("Apply Failed", f"An error occurred while applying settings:\n{e}")

    def reset_settings():
        if not messagebox.askyesno(
            "Confirm Repair Reset",
            "This will attempt to restore Brave to the state it had before SlimBrave first applied settings.\n\n"
            "The operation will:\n"
            "- fully close Brave\n"
            "- restore the saved pre-SlimBrave full-domain snapshot if available\n"
            "- otherwise remove all SlimBrave-managed keys\n"
            "- remove stray managed-preferences plist files\n"
            "- clear applicable Brave caches/state paths\n\n"
            "Continue?"
        ):
            return

        if not stop_brave_for_operation("repair reset"):
            return

        try:
            set_status("Running repair reset…")
            restored_snapshot = False

            if os.path.exists(SNAPSHOT_FILE):
                snapshot_raw = load_plist_file(SNAPSHOT_FILE)
                kind, payload = extract_backup_payload(snapshot_raw)
                if kind == "full_domain_backup" and isinstance(payload, dict):
                    restore_full_domain_payload(payload)
                    restored_snapshot = True
                    write_log(f"Restored baseline snapshot from {SNAPSHOT_FILE}")
                else:
                    restore_full_domain_payload(snapshot_raw)
                    restored_snapshot = True
                    write_log(f"Restored legacy baseline snapshot from {SNAPSHOT_FILE}")
            else:
                current = export_current_domain_dict()
                for key in MANAGED_KEYS:
                    current.pop(key, None)
                import_domain_dict(current)
                write_log("No baseline snapshot found. Removed managed keys from live domain only.")

            remove_managed_pref_files()
            clear_applicable_caches()
            flush_pref_cache()
            reload_ui_from_registry()

            if restored_snapshot:
                set_status("Brave restored to pre-SlimBrave state and caches cleared.")
                messagebox.showinfo(
                    "Repair Successful",
                    "Brave was restored to the saved pre-SlimBrave baseline and applicable caches were cleared."
                )
            else:
                set_status("SlimBrave-managed settings removed and caches cleared.")
                messagebox.showinfo(
                    "Repair Successful",
                    "SlimBrave-managed settings were removed and applicable caches were cleared.\n\n"
                    "No original baseline snapshot was available, so unrelated Brave settings could not be restored."
                )
        except Exception as e:
            write_log(f"Reset failed: {e}")
            messagebox.showerror("Reset Failed", f"An error occurred during reset:\n{e}")

    def apply_preset(preset_type):
        nonlocal suspend_dirty_tracking
        suspend_dirty_tracking = True

        for var in all_feature_vars.values():
            var.set(0)

        for perm in permission_settings:
            name = perm["Name"]
            if name == "JavaScript":
                all_perm_vars[perm["Key"]].set("Allow")
            elif name in ["Camera", "Microphone"]:
                all_perm_vars[perm["Key"]].set("Ask")
            elif name == "Images":
                all_perm_vars[perm["Key"]].set("Not Set")
            else:
                if "Block" in perm["Options"]:
                    all_perm_vars[perm["Key"]].set("Block")
                else:
                    all_perm_vars[perm["Key"]].set("Not Set")

        if preset_type == "privacy":
            privacy_keys = [
                "MetricsReportingEnabled", "SafeBrowsingExtendedReportingEnabled",
                "UrlKeyedAnonymizedDataCollectionEnabled", "FeedbackSurveysEnabled",
                "BraveP3AEnabled", "BraveStatsPingEnabled", "BraveWebDiscoveryEnabled",
                "AutofillAddressEnabled", "AutofillCreditCardEnabled", "PasswordManagerEnabled",
                "BrowserSignin", "WebRtcIPHandling", "BlockThirdPartyCookies",
                "EnableDoNotTrack", "IPFSEnabled", "PromptForDownloadLocation",
                "ClearBrowsingDataOnExitList", "HttpsOnlyMode",
                "BraveRewardsDisabled", "BraveWalletDisabled", "BraveVPNDisabled",
                "BraveAIChatEnabled", "TorDisabled", "BraveNewsDisabled",
                "BraveTalkDisabled", "BraveSpeedreaderEnabled", "BraveWaybackMachineEnabled",
                "BackgroundModeEnabled", "MediaRecommendationsEnabled", "ShoppingListEnabled",
                "AlwaysOpenPdfExternally", "PromotionsEnabled", "SearchSuggestEnabled",
                "DefaultBrowserSettingEnabled", "BravePlaylistEnabled"
            ]
            for key in privacy_keys:
                if key in all_feature_vars:
                    all_feature_vars[key].set(1)
            sb_var.set("Off")
            dns_var.set("Off")
            set_status("Loaded: High Privacy + Moderate Security preset.")

        elif preset_type == "security":
            security_keys = [
                "MetricsReportingEnabled", "SafeBrowsingExtendedReportingEnabled",
                "UrlKeyedAnonymizedDataCollectionEnabled", "FeedbackSurveysEnabled",
                "BraveP3AEnabled", "BraveStatsPingEnabled", "BraveWebDiscoveryEnabled",
                "WebRtcIPHandling", "QuicAllowed", "BlockThirdPartyCookies",
                "EnableDoNotTrack", "ForceGoogleSafeSearch", "IPFSEnabled",
                "PromptForDownloadLocation", "HttpsOnlyMode",
                "BraveRewardsDisabled", "BraveWalletDisabled", "BraveVPNDisabled",
                "BraveAIChatEnabled", "TorDisabled", "SyncDisabled",
                "BraveNewsDisabled", "BraveTalkDisabled", "BraveSpeedreaderEnabled",
                "BraveWaybackMachineEnabled", "BackgroundModeEnabled",
                "AlwaysOpenPdfExternally", "DeveloperToolsDisabled", "BravePlaylistEnabled"
            ]
            for key in security_keys:
                if key in all_feature_vars:
                    all_feature_vars[key].set(1)
            sb_var.set("On")
            dns_var.set("On")
            set_status("Loaded: High Security + Moderate Privacy preset.")

        suspend_dirty_tracking = False
        check_dirty_state()

    root.grid_rowconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=0)
    root.grid_columnconfigure(0, weight=1)

    container = tk.Frame(root, bg="#191919")
    container.grid(row=0, column=0, sticky="nsew")
    container.grid_rowconfigure(1, weight=1)
    container.grid_columnconfigure(0, weight=1)

    top_frame = tk.Frame(container, bg="#191919")
    top_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 15))
    inner_top = tk.Frame(top_frame, bg="#191919")
    inner_top.pack(fill="x")

    tk.Label(inner_top, text="Quick Toggles:", font=("sans-serif", 12, "bold"), fg="#87CEFA", bg="#191919").pack(side="left", padx=(0, 10))

    btn_priv = ttk.Button(inner_top, text="High Privacy + Moderate Security", style="Orange.TButton",
                          command=lambda: apply_preset("privacy"))
    btn_priv.pack(side="left", padx=10)
    create_tooltip(btn_priv, "Applies the recommended preset for High Privacy and Moderate Security.")

    btn_sec = ttk.Button(inner_top, text="High Security + Moderate Privacy", style="Orange.TButton",
                         command=lambda: apply_preset("security"))
    btn_sec.pack(side="left", padx=10)
    create_tooltip(btn_sec, "Applies the recommended preset for High Security and Moderate Privacy.")

    save_status_label = tk.Label(inner_top, textvariable=save_status_var, bg="#191919",
                                 fg="#90EE90", font=("sans-serif", 10, "bold"))
    save_status_label.pack(side="right", padx=(50, 0))

    class ScrollableFrame(tk.Frame):
        def __init__(self, parent, bg, **kwargs):
            super().__init__(parent, bg=bg, **kwargs)
            self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
            self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                           style="Dark.Vertical.TScrollbar")
            self.inner_frame = tk.Frame(self.canvas, bg=bg)

            self.canvas.configure(yscrollcommand=self.scrollbar.set)
            self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

            self.inner_frame.bind("<Configure>", self._on_inner_configure)
            self.canvas.bind("<Configure>", self._on_canvas_configure)

            self.scrollbar.pack(side="right", fill="y")
            self.canvas.pack(side="left", fill="both", expand=True)

            self._bind_mousewheel(self.canvas)
            self._bind_mousewheel(self.inner_frame)

        def _on_inner_configure(self, event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        def _on_canvas_configure(self, event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)

        def _on_mousewheel(self, event):
            if event.num == 4:
                delta = -1
            elif event.num == 5:
                delta = 1
            else:
                delta = -1 * int(event.delta / 120) if event.delta else 0
                if sys.platform == "darwin" and event.delta:
                    delta = -1 if event.delta > 0 else 1
            self.canvas.yview_scroll(delta, "units")

        def _bind_mousewheel(self, widget):
            widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
            widget.bind("<Button-4>", self._on_mousewheel, add="+")
            widget.bind("<Button-5>", self._on_mousewheel, add="+")
            for child in widget.winfo_children():
                self._bind_mousewheel(child)

        def bind_children(self):
            self._bind_mousewheel(self.inner_frame)

        def scroll(self, delta):
            self.canvas.yview_scroll(int(delta), "units")

    main_frame = tk.Frame(container, bg="#191919")
    main_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 5))
    main_frame.grid_columnconfigure(0, weight=1)
    main_frame.grid_columnconfigure(1, weight=1)
    main_frame.grid_columnconfigure(2, weight=1)
    main_frame.grid_rowconfigure(0, weight=1)

    left_scroll = ScrollableFrame(main_frame, bg="#191919")
    left_scroll.grid(row=0, column=0, sticky="nsew", padx=6)
    mid_scroll = ScrollableFrame(main_frame, bg="#191919")
    mid_scroll.grid(row=0, column=1, sticky="nsew", padx=6)
    right_scroll = ScrollableFrame(main_frame, bg="#191919")
    right_scroll.grid(row=0, column=2, sticky="nsew", padx=6)

    left_panel = tk.Frame(left_scroll.inner_frame, bg="#232323", bd=0, highlightthickness=1, highlightbackground="#3c3c3c")
    left_panel.pack(fill="both", expand=True)
    mid_panel = tk.Frame(mid_scroll.inner_frame, bg="#232323", bd=0, highlightthickness=1, highlightbackground="#3c3c3c")
    mid_panel.pack(fill="both", expand=True)
    right_panel = tk.Frame(right_scroll.inner_frame, bg="#232323", bd=0, highlightthickness=1, highlightbackground="#3c3c3c")
    right_panel.pack(fill="both", expand=True)

    def populate_checkboxes(parent, title, feature_list):
        tk.Label(parent, text=title, font=("sans-serif", 11, "bold"), fg="#FFA07A", bg="#232323").pack(anchor="w", pady=(8, 4), padx=12)
        for feat in feature_list:
            var = tk.IntVar()
            all_feature_vars[feat["Key"]] = var
            var.trace_add("write", check_dirty_state)
            cb = ttk.Checkbutton(parent, text=feat["Name"], variable=var)
            cb.pack(anchor="w", padx=16, pady=1)
            create_tooltip(cb, feat["ToolTip"])

    populate_checkboxes(left_panel, "Telemetry and Reporting", telemetry_features)
    populate_checkboxes(left_panel, "Privacy and Security", privacy_features)
    populate_checkboxes(mid_panel, "Brave Features", brave_features)
    populate_checkboxes(mid_panel, "Performance and Bloat", perf_features)

    tk.Label(right_panel, text="Site Permissions", font=("sans-serif", 11, "bold"), fg="#FFA07A", bg="#232323").pack(anchor="w", pady=(8, 6), padx=12)

    for perm in permission_settings:
        frame = tk.Frame(right_panel, bg="#232323")
        frame.pack(fill="x", padx=16, pady=1)
        lbl = tk.Label(frame, text=perm["Name"], fg="white", bg="#232323", width=16, anchor="w", font=("sans-serif", 9))
        lbl.pack(side="left")
        create_tooltip(lbl, perm["ToolTip"])

        var = tk.StringVar(value="Not Set")
        all_perm_vars[perm["Key"]] = var
        var.trace_add("write", check_dirty_state)
        cb = ttk.Combobox(frame, textvariable=var, values=perm["Options"], state="readonly", width=10, style="Dark.TCombobox")
        cb.pack(side="right")
        create_tooltip(cb, perm["ToolTip"])

    spacer = tk.Frame(right_panel, bg="#232323", height=8)
    spacer.pack(fill="x")

    sb_f = tk.Frame(right_panel, bg="#232323")
    sb_f.pack(fill="x", padx=16, pady=2)
    sb_lbl = tk.Label(sb_f, text="Safe Browsing:", fg="white", bg="#232323", width=12, anchor="w", font=("sans-serif", 9))
    sb_lbl.pack(side="left")
    sb_var = tk.StringVar()
    sb_var.trace_add("write", check_dirty_state)
    sb_cb = ttk.Combobox(sb_f, textvariable=sb_var, values=["On", "Off"], state="readonly", width=10, style="Dark.TCombobox")
    sb_cb.pack(side="left", padx=8)
    sb_tt = "On = Standard Safe Browsing. Off = Disabled entirely.\n\nSuggested Settings for Privacy: Off | Security: On"
    create_tooltip(sb_lbl, sb_tt)
    create_tooltip(sb_cb, sb_tt)

    dns_f = tk.Frame(right_panel, bg="#232323")
    dns_f.pack(fill="x", padx=16, pady=2)
    dns_lbl = tk.Label(dns_f, text="DNS Over HTTPS:", fg="white", bg="#232323", width=12, anchor="w", font=("sans-serif", 9))
    dns_lbl.pack(side="left")
    dns_var = tk.StringVar()
    dns_var.trace_add("write", check_dirty_state)
    dns_cb = ttk.Combobox(dns_f, textvariable=dns_var, values=["On", "Off"], state="readonly", width=10, style="Dark.TCombobox")
    dns_cb.pack(side="left", padx=8)
    dns_tt = "Forces encrypted DNS lookups.\n\nSuggested Settings for Privacy: Off | Security: On"
    create_tooltip(dns_lbl, dns_tt)
    create_tooltip(dns_cb, dns_tt)

    left_scroll.bind_children()
    mid_scroll.bind_children()
    right_scroll.bind_children()

    bottom_bar = tk.Frame(root, bg="#2d2d2d", height=70)
    bottom_bar.grid(row=1, column=0, sticky="ew")
    bottom_bar.grid_propagate(False)

    btn_frame = tk.Frame(bottom_bar, bg="#2d2d2d")
    btn_frame.pack(side="top", fill="x", pady=5)

    ttk.Button(btn_frame, text="Export Settings", style="Export.TButton", command=export_settings).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Import JSON", style="Import.TButton", command=import_settings).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Restore Plist/XML", style="Plist.TButton", command=import_plist).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Pull Settings", style="Pull.TButton", command=reload_ui_from_registry).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Apply Settings", style="Apply.TButton", command=apply_settings).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Reset All", style="Reset.TButton", command=reset_settings).pack(side="left", expand=True, padx=5)

    status_label = tk.Label(bottom_bar, textvariable=status_var, bg="#2d2d2d", fg="#aaaaaa",
                            font=("courier", 10), anchor="w", padx=10)
    status_label.pack(side="bottom", fill="x")

    root.after(100, reload_ui_from_registry)
    root.mainloop()


if __name__ == "__main__":
    dependency_setup()
    main()
