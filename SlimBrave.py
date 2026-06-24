#!/usr/bin/env python3
# SlimBrave - Revived - v1.1.2 (macOS Edition)
# Fixes:
# - Robust plist restore for old SlimBrave backups, binary plists, XML plists, and backup.plist files
# - Reset/repair can optionally restore a user-selected plist backup after scrubbing
# - Restore now stages the plist, reads it safely, writes it to the correct managed-preferences path when needed,
#   and also imports the domain properly
# - Better Brave shutdown and cache cleanup
# - Safer full-domain snapshot support for repair
# - On-screen plist restore diagnostics window

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
    print("Homebrew is a package manager for macOS that lets you easily install")
    print("and manage software. SlimBrave requires it to install a modern Python")
    print("with a working Tkinter GUI library.")
    if prompt_yes_no("Install Homebrew now?"):
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
            print_step("Homebrew installed successfully.")
            BREW_INSTALLED_SOMETHING = True
            return True
        print_step("Homebrew still not available. Exiting.")
        sys.exit(1)

    print_step("Cannot continue without Homebrew. Exiting.")
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
    except ImportError:
        return 0


def check_python_and_tk():
    global BREW_INSTALLED_SOMETHING
    brew_prefix = get_brew_prefix()
    if not brew_prefix:
        return

    current_python = sys.executable
    print_step(f"Current Python: {current_python}")

    if not is_homebrew_python():
        print_step("You are using the system Python, which ships with a deprecated Tcl/Tk.")
        print("SlimBrave needs a modern Tk that doesn’t throw deprecation warnings.")
        if prompt_yes_no("Install Homebrew Python with Tkinter now?"):
            print_step("Installing Homebrew Python + Tk (python-tk)…")
            subprocess.run(["brew", "install", "python-tk"], check=True)
            BREW_INSTALLED_SOMETHING = True
            new_python = f"{brew_prefix}/bin/python3"
            if not os.path.exists(new_python):
                print_step("Installation succeeded but could not find new Python. Exiting.")
                sys.exit(1)
            print_step(f"Relaunching with {new_python} …")
            os.execv(new_python, [new_python] + sys.argv)
        else:
            print_step("A modern Python is required. Exiting.")
            sys.exit(1)

    tk_ver = get_tk_version()
    print_step(f"Tk version: {tk_ver}")
    if tk_ver < 8.6:
        print_step("Your Tkinter is outdated (missing or old).")
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
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    import json
    import datetime
    import plistlib
    import tempfile

    DOMAIN = "com.brave.Browser"
    CONFIG_DIR = os.path.expanduser("~/.config/slimbrave")
    RESTORE_STAGING_DIR = os.path.join(CONFIG_DIR, "restore-staging")
    STATE_FILE = os.path.join(CONFIG_DIR, "SlimBraveState.json")
    LOG_FILE = os.path.join(CONFIG_DIR, "SlimBrave.log")
    SNAPSHOT_FILE = os.path.join(CONFIG_DIR, "BraveOriginalDomainBackup.plist")
    INTERNAL_LAST_EXPORT = os.path.join(CONFIG_DIR, "LastExportedBraveBackup.plist")

    USER_MANAGED_PREFS_DIR = os.path.expanduser("~/Library/Managed Preferences")
    USER_MANAGED_PREFS_FILE = os.path.join(USER_MANAGED_PREFS_DIR, f"{DOMAIN}.plist")
    SYSTEM_MANAGED_PREFS_FILE = os.path.join("/Library/Managed Preferences", f"{DOMAIN}.plist")

    BRAVE_SUPPORT_DIR = os.path.expanduser("~/Library/Application Support/BraveSoftware/Brave-Browser")
    BRAVE_CACHE_DIR = os.path.expanduser("~/Library/Caches/BraveSoftware/Brave-Browser")

    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(RESTORE_STAGING_DIR, exist_ok=True)
    os.makedirs(USER_MANAGED_PREFS_DIR, exist_ok=True)

    def write_log(message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} - {message}\n")

    def timestamp_slug():
        return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    write_log("SlimBrave macOS UI Initializing...")

    root = tk.Tk()
    root.title("SlimBrave - Revived v1.1.2 (macOS)")
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
            self.show_id = self.widget.after(1000, self.show)

        def on_leave(self, event=None):
            if self.show_id:
                self.widget.after_cancel(self.show_id)
                self.show_id = None
            self.hide()

        def show(self):
            if self.tooltip_window:
                return
            try:
                x, y, _, _ = self.widget.bbox("insert")
            except Exception:
                x, y = 0, 0
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25
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
                wraplength=430,
            )
            label.pack(ipadx=1)

        def hide(self):
            if self.tooltip_window:
                self.tooltip_window.destroy()
                self.tooltip_window = None

    def create_tooltip(widget, text):
        ToolTip(widget, text)

    telemetry_features = [
        {"Name": "Disable Metrics Reporting", "Key": "MetricsReportingEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Stops Brave from sending anonymous usage and crash reports.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Safe Browsing Reporting", "Key": "SafeBrowsingExtendedReportingEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Stops Brave from sending extended Safe Browsing data back to servers.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable URL Data Collection", "Key": "UrlKeyedAnonymizedDataCollectionEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Stops sending anonymized URLs to help improve the browser.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Feedback Surveys", "Key": "FeedbackSurveysEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Disables proactive feedback survey prompts.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable P3A Telemetry", "Key": "BraveP3AEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Disables Privacy-Preserving Product Analytics completely.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Daily Stats Ping", "Key": "BraveStatsPingEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Stops the daily active user ping.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Web Discovery", "Key": "BraveWebDiscoveryEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Prevents anonymous search/browsing data from being sent to Brave Search.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"}
    ]

    privacy_features = [
        {"Name": "Disable Autofill (Addresses)", "Key": "AutofillAddressEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Disables saving and autofilling addresses.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Autofill (Credit Cards)", "Key": "AutofillCreditCardEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Disables saving and autofilling credit cards.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Password Manager", "Key": "PasswordManagerEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Disables the built-in password manager.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Browser Sign-in", "Key": "BrowserSignin", "Value": 0, "Type": "-int", "ToolTip": "Prevents syncing your data to cloud accounts.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable WebRTC IP Leak", "Key": "WebRtcIPHandling", "Value": "disable_non_proxied_udp", "Type": "-string", "ToolTip": "Prevents your real IP address from leaking when using a VPN.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable QUIC Protocol", "Key": "QuicAllowed", "Value": "false", "Type": "-bool", "ToolTip": "Forces standard TCP, stopping UDP firewall bypasses and tracking.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Block Third Party Cookies", "Key": "BlockThirdPartyCookies", "Value": "true", "Type": "-bool", "ToolTip": "Blocks all third-party tracking cookies.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Enable Do Not Track", "Key": "EnableDoNotTrack", "Value": "true", "Type": "-bool", "ToolTip": "Sends a Do Not Track request with your browsing traffic.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Force Google SafeSearch", "Key": "ForceGoogleSafeSearch", "Value": "true", "Type": "-bool", "ToolTip": "Filters explicit search results.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Disable IPFS", "Key": "IPFSEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Stops peer-to-peer background connections to unknown nodes.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Force Incognito Mode", "Key": "IncognitoModeAvailability", "Value": 2, "Type": "-int", "ToolTip": "Forces the browser to always open in Incognito Mode.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Force Download Prompts", "Key": "PromptForDownloadLocation", "Value": "true", "Type": "-bool", "ToolTip": "Forces Brave to ask where to save a file before downloading, preventing drive-by downloads.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Clear Data on Exit", "Key": "ClearBrowsingDataOnExitList", "Value": ["browsing_history", "download_history", "cookies_and_other_site_data", "cached_images_and_files", "password_signin", "autofill", "site_settings", "hosted_app_data"], "Type": "-array", "ToolTip": "Wipes all cookies, cache, and browsing history the moment the browser closes.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Force HTTPS-Only Mode", "Key": "HttpsOnlyMode", "Value": "force_enabled", "Type": "-string", "ToolTip": "Strictly upgrades all connections to HTTPS and blocks unencrypted HTTP traffic.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"}
    ]

    brave_features = [
        {"Name": "Disable Brave Rewards and Sponsored Elements", "Key": "BraveRewardsDisabled", "Value": "true", "Type": "-bool", "ToolTip": "Completely disables the Brave Crypto Rewards system and disables sponsored backgrounds on the New Tab page.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave Wallet", "Key": "BraveWalletDisabled", "Value": "true", "Type": "-bool", "ToolTip": "Disables the built-in Brave Crypto Wallet.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave VPN", "Key": "BraveVPNDisabled", "Value": "true", "Type": "-bool", "ToolTip": "Removes the Brave VPN integration and prompts.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave AI Chat", "Key": "BraveAIChatEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Disables Brave Leo (AI Chat) integration.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Tor", "Key": "TorDisabled", "Value": "true", "Type": "-bool", "ToolTip": "Disables built-in Tor window support.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Sync", "Key": "SyncDisabled", "Value": "true", "Type": "-bool", "ToolTip": "Disables Brave Sync functionality across devices.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Disable Brave News", "Key": "BraveNewsDisabled", "Value": "true", "Type": "-bool", "ToolTip": "Removes the Brave News feed bloat from the New Tab page.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave Talk", "Key": "BraveTalkDisabled", "Value": "true", "Type": "-bool", "ToolTip": "Removes the built-in video calling integration.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Speedreader", "Key": "BraveSpeedreaderEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Completely disables the Speedreader feature, reader mode, and automatic prompts.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Wayback Machine Prompts", "Key": "BraveWaybackMachineEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Stops Brave from asking to search the Internet Archive when you hit a 404 error.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"}
    ]

    perf_features = [
        {"Name": "Disable Background Mode", "Key": "BackgroundModeEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Prevents extensions/apps from running after the browser is closed.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Media Recommendations", "Key": "MediaRecommendationsEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Disables media recommendations to save memory.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Shopping List", "Key": "ShoppingListEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Disables the shopping list feature.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Always Open PDF Externally", "Key": "AlwaysOpenPdfExternally", "Value": "true", "Type": "-bool", "ToolTip": "Forces PDFs to download and open in your system viewer instead of the browser.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Translate", "Key": "TranslateEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Disables automatic translation prompts.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Spellcheck", "Key": "SpellcheckEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Disables the built-in spellchecker to save CPU cycles.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Promotions", "Key": "PromotionsEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Disables Brave promotional notifications.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Search Suggestions", "Key": "SearchSuggestEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Disables predictive search suggestions in the URL bar.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Printing", "Key": "PrintingEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Disables the browser print function.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Default Browser Prompt", "Key": "DefaultBrowserSettingEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Stops Brave from asking to be the default browser.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Developer Tools", "Key": "DeveloperToolsDisabled", "Value": "true", "Type": "-bool", "ToolTip": "Disables F12 / Inspect Element.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Disable Brave Playlist", "Key": "BravePlaylistEnabled", "Value": "false", "Type": "-bool", "ToolTip": "Removes the Brave Playlist media feature.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"}
    ]

    permission_settings = [
        {"Name": "Location", "Key": "DefaultGeolocationSetting", "Options": ["Not Set", "Ask", "Block", "Allow"], "ToolTip": "Allows sites to request your physical location.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Camera", "Key": "DefaultVideoCaptureSetting", "Options": ["Not Set", "Ask", "Block"], "ToolTip": "Allows sites to record video via your webcam.\n\nSuggested Settings for Privacy: Ask | Security: Ask"},
        {"Name": "Microphone", "Key": "DefaultAudioCaptureSetting", "Options": ["Not Set", "Ask", "Block"], "ToolTip": "Allows sites to record audio via your microphone.\n\nSuggested Settings for Privacy: Ask | Security: Ask"},
        {"Name": "Notifications", "Key": "DefaultNotificationsSetting", "Options": ["Not Set", "Ask", "Block", "Allow"], "ToolTip": "Allows sites to send you native desktop push notifications.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "JavaScript", "Key": "DefaultJavaScriptSetting", "Options": ["Not Set", "Allow", "Block"], "ToolTip": "Allows sites to run interactive scripts. Blocking this breaks almost all websites.\n\nSuggested Settings for Privacy: Allow | Security: Allow"},
        {"Name": "Images", "Key": "DefaultImagesSetting", "Options": ["Not Set", "Allow", "Block"], "ToolTip": "Allows sites to load and display images.\n\nSuggested Settings for Privacy: Not Set | Security: Not Set"},
        {"Name": "Pop-ups and Redirects", "Key": "DefaultPopupsSetting", "Options": ["Not Set", "Block", "Allow"], "ToolTip": "Allows sites to open new windows or redirect you without your input.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "USB Devices", "Key": "DefaultWebUsbGuardSetting", "Options": ["Not Set", "Ask", "Block"], "ToolTip": "Allows sites to request direct connection to your plugged-in USB devices.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Serial Ports", "Key": "DefaultSerialGuardSetting", "Options": ["Not Set", "Ask", "Block"], "ToolTip": "Allows sites to request connection to hardware via serial ports.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "HID Devices", "Key": "DefaultWebHidGuardSetting", "Options": ["Not Set", "Ask", "Block"], "ToolTip": "Allows sites to request access to Human Interface Devices (e.g. controllers).\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "File Editing", "Key": "DefaultFileSystemReadGuardSetting", "Options": ["Not Set", "Ask", "Block"], "ToolTip": "Allows sites to read and save files directly to your local file system.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Clipboard", "Key": "DefaultClipboardSetting", "Options": ["Not Set", "Ask", "Block"], "ToolTip": "Allows sites to read text and images copied to your clipboard.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Window Management", "Key": "DefaultWindowPlacementSetting", "Options": ["Not Set", "Ask", "Block", "Allow"], "ToolTip": "Allows sites to open windows on specific monitors or in fullscreen.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Local Fonts", "Key": "DefaultLocalFontsSetting", "Options": ["Not Set", "Ask", "Block"], "ToolTip": "Allows sites to fingerprint your device based on locally installed fonts.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Payment Handlers", "Key": "PaymentMethodQueryEnabled", "Options": ["Not Set", "Block", "Allow"], "ToolTip": "Allows sites to check if you have local payment apps installed.\n\nSuggested Settings for Privacy: Block | Security: Block"}
    ]

    all_features = telemetry_features + privacy_features + brave_features + perf_features
    managed_keys = {feat["Key"] for feat in all_features}
    managed_keys.update({perm["Key"] for perm in permission_settings})
    managed_keys.update({"DefaultFileSystemWriteGuardSetting", "SafeBrowsingProtectionLevel", "DnsOverHttpsMode"})

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
    style.configure("Orange.TButton", background="#E65100", foreground="white", font=("sans-serif", 10, "bold"), borderwidth=0, relief="flat", padding=button_padding)
    style.map("Orange.TButton", background=[("active", "#BF360C")], foreground=[("active", "white")])

    style.configure("Export.TButton", background="#0D47A1", foreground="white", font=("sans-serif", 9, "bold"), borderwidth=0, relief="flat", padding=button_padding)
    style.map("Export.TButton", background=[("active", "#0A3D91")])

    style.configure("Import.TButton", background="#1976D2", foreground="white", font=("sans-serif", 9, "bold"), borderwidth=0, relief="flat", padding=button_padding)
    style.map("Import.TButton", background=[("active", "#1565C0")])

    style.configure("Pull.TButton", background="#F57F17", foreground="white", font=("sans-serif", 9, "bold"), borderwidth=0, relief="flat", padding=button_padding)
    style.map("Pull.TButton", background=[("active", "#E65100")])

    style.configure("Apply.TButton", background="#2E7D32", foreground="white", font=("sans-serif", 9, "bold"), borderwidth=0, relief="flat", padding=button_padding)
    style.map("Apply.TButton", background=[("active", "#1B5E20")])

    style.configure("Reset.TButton", background="#C62828", foreground="white", font=("sans-serif", 9, "bold"), borderwidth=0, relief="flat", padding=button_padding)
    style.map("Reset.TButton", background=[("active", "#B71C1C")])

    style.configure("Plist.TButton", background="#6A1B9A", foreground="white", font=("sans-serif", 9, "bold"), borderwidth=0, relief="flat", padding=button_padding)
    style.map("Plist.TButton", background=[("active", "#4A148C")])

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

    class ScrollableFrame(tk.Frame):
        def __init__(self, parent, bg, **kwargs):
            super().__init__(parent, bg=bg, **kwargs)
            self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
            self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview, style="Dark.Vertical.TScrollbar")
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

        def _bind_mousewheel(self, widget):
            def on_mousewheel(event):
                if event.num == 4:
                    delta = -1
                elif event.num == 5:
                    delta = 1
                else:
                    delta = event.delta if sys.platform == "darwin" else event.delta / 120
                    if delta > 0:
                        delta = 1
                    elif delta < 0:
                        delta = -1
                self.canvas.yview_scroll(int(-delta), "units")

            for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                widget.bind(ev, on_mousewheel)
            for child in widget.winfo_children():
                self._bind_mousewheel(child)

        def bind_children(self):
            self._bind_mousewheel(self.inner_frame)

        def scroll(self, delta):
            self.canvas.yview_scroll(int(-delta), "units")

    def run_cmd(cmd):
        return subprocess.run(cmd, capture_output=True, text=True)

    def run_cmd_ok(cmd, context):
        result = run_cmd(cmd)
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip() or f"Command failed: {' '.join(cmd)}"
            raise Exception(f"{context}: {err}")
        return result

    def read_default(key):
        res = run_cmd(["defaults", "read", DOMAIN, key])
        return res.stdout.strip() if res.returncode == 0 else None

    def write_default(key, vtype, val):
        if vtype == "-array":
            cmd = ["defaults", "write", DOMAIN, key, "-array"] + val
        else:
            cmd = ["defaults", "write", DOMAIN, key, vtype, str(val)]
        result = run_cmd(cmd)
        if result.returncode != 0:
            raise Exception(result.stderr.strip() or result.stdout.strip() or f"defaults write failed for {key}")

    def delete_default(key):
        run_cmd(["defaults", "delete", DOMAIN, key])

    def graceful_close_brave():
        res = run_cmd(["pgrep", "-if", "Brave Browser"])
        if not res.stdout.strip():
            return True

        ok = messagebox.askokcancel(
            "Close Brave Required",
            "Brave is currently running in the background.\n\n"
            "Chromium browsers overwrite preference files when they close. SlimBrave must close Brave BEFORE restoring, applying, or repairing settings.\n\n"
            "Click OK to close Brave and continue.",
        )
        if not ok:
            set_status("Operation cancelled by user.")
            return False

        set_status("Closing Brave gracefully...")
        run_cmd(["osascript", "-e", 'tell application "Brave Browser" to quit'])
        time.sleep(2.0)

        res = run_cmd(["pgrep", "-if", "Brave Browser"])
        if not res.stdout.strip():
            return True

        set_status("Brave still running, forcing shutdown...")
        run_cmd(["pkill", "-TERM", "-if", "Brave Browser"])
        run_cmd(["pkill", "-TERM", "-if", "Brave Browser Helper"])
        time.sleep(2.0)

        res = run_cmd(["pgrep", "-if", "Brave Browser"])
        if res.stdout.strip():
            run_cmd(["pkill", "-KILL", "-if", "Brave Browser"])
            run_cmd(["pkill", "-KILL", "-if", "Brave Browser Helper"])
            time.sleep(1.0)

        return True

    def remove_if_exists(path):
        try:
            if os.path.islink(path) or os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
        except Exception as e:
            write_log(f"Failed removing {path}: {e}")

    def clear_brave_runtime_caches():
        paths = [
            BRAVE_CACHE_DIR,
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "Cache"),
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "Code Cache"),
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "GPUCache"),
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "DawnCache"),
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "GrShaderCache"),
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "ShaderCache"),
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "Service Worker", "CacheStorage"),
            os.path.join(BRAVE_SUPPORT_DIR, "Default", "Service Worker", "ScriptCache"),
            os.path.join(BRAVE_SUPPORT_DIR, "SingletonLock"),
            os.path.join(BRAVE_SUPPORT_DIR, "SingletonCookie"),
            os.path.join(BRAVE_SUPPORT_DIR, "SingletonSocket"),
        ]
        for p in paths:
            if os.path.exists(p):
                remove_if_exists(p)
                write_log(f"Removed runtime cache/state path: {p}")

    def flush_pref_cache():
        run_cmd(["killall", "cfprefsd"])
        time.sleep(0.8)

    def plutil_xml_copy(src_path):
        fd, temp_path = tempfile.mkstemp(prefix="slimbrave-", suffix=".plist")
        os.close(fd)
        shutil.copy2(src_path, temp_path)
        result = run_cmd(["plutil", "-convert", "xml1", temp_path])
        if result.returncode != 0:
            try:
                os.remove(temp_path)
            except OSError:
                pass
            raise Exception(result.stderr.strip() or result.stdout.strip() or "plutil conversion failed")
        return temp_path

    def load_plist_any(src_path):
        try:
            with open(src_path, "rb") as f:
                return plistlib.load(f)
        except Exception:
            temp_xml = plutil_xml_copy(src_path)
            try:
                with open(temp_xml, "rb") as f:
                    return plistlib.load(f)
            finally:
                remove_if_exists(temp_xml)

    def write_xml_plist(path, data):
        with open(path, "wb") as f:
            plistlib.dump(data, f, fmt=plistlib.FMT_XML, sort_keys=True)

    def export_domain_to_path(path):
        result = run_cmd(["defaults", "export", DOMAIN, path])
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            if "does not exist" in err.lower() or "domain/default pair" in err.lower():
                write_xml_plist(path, {})
            else:
                raise Exception(err or f"defaults export failed for {DOMAIN}")

    def export_domain_dict():
        fd, temp_path = tempfile.mkstemp(prefix="slimbrave-domain-", suffix=".plist")
        os.close(fd)
        try:
            export_domain_to_path(temp_path)
            return load_plist_any(temp_path)
        finally:
            remove_if_exists(temp_path)

    def import_domain_from_dict(data_dict):
        fd, temp_path = tempfile.mkstemp(prefix="slimbrave-import-", suffix=".plist")
        os.close(fd)
        try:
            write_xml_plist(temp_path, data_dict)
            run_cmd_ok(["defaults", "import", DOMAIN, temp_path], "defaults import failed")
        finally:
            remove_if_exists(temp_path)

    def ensure_snapshot_exists():
        if os.path.exists(SNAPSHOT_FILE):
            return
        try:
            export_domain_to_path(SNAPSHOT_FILE)
            write_log(f"Created original Brave domain snapshot at {SNAPSHOT_FILE}")
        except Exception as e:
            write_log(f"Could not create original Brave domain snapshot: {e}")

    def normalize_restore_root(data):
        if not isinstance(data, dict):
            raise Exception("The selected plist is not a dictionary plist.")

        if "__SlimBrave__" in data and isinstance(data.get("Payload"), dict):
            return data["Payload"], data["__SlimBrave__"].get("kind", "wrapped")

        if DOMAIN in data and isinstance(data[DOMAIN], dict):
            return data[DOMAIN], "nested-domain"

        return data, "plain"

    def classify_restore_payload(payload):
        if not isinstance(payload, dict):
            return "invalid"
        keys = set(payload.keys())
        if not keys:
            return "empty"
        if keys.issubset(managed_keys):
            return "managed-only"
        if keys & managed_keys:
            return "mixed-domain"
        return "full-domain"

    def apply_payload_to_live_domain(payload, mode):
        current_domain = export_domain_dict()
        if not isinstance(current_domain, dict):
            current_domain = {}

        if mode == "managed-only":
            for key in managed_keys:
                current_domain.pop(key, None)
            current_domain.update(payload)
            import_domain_from_dict(current_domain)
        else:
            import_domain_from_dict(payload)

    def write_managed_plist_if_needed(payload, mode):
        if mode not in ("managed-only", "mixed-domain"):
            return False

        managed_payload = {k: v for k, v in payload.items() if k in managed_keys}
        if not managed_payload:
            return False

        write_xml_plist(USER_MANAGED_PREFS_FILE, managed_payload)
        write_log(f"Restored managed-preferences plist to {USER_MANAGED_PREFS_FILE}")
        return True

    def stage_restore_source(src_path):
        base = os.path.basename(src_path)
        staged = os.path.join(RESTORE_STAGING_DIR, f"{timestamp_slug()}-{base}")
        shutil.copy2(src_path, staged)
        write_log(f"Staged restore source at {staged}")
        return staged

    def show_restore_diagnostics(selected_path, staged_path, container_kind, mode, payload, managed_written):
        diag = tk.Toplevel(root)
        diag.title("SlimBrave Restore Diagnostics")
        diag.transient(root)
        diag.grab_set()
        diag.iconphoto(False, icon_img)
        diag.configure(bg="#1f1f1f")
        diag.geometry("860x520")
        diag.minsize(760, 420)

        outer = tk.Frame(diag, bg="#1f1f1f")
        outer.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(
            outer,
            text="Plist Restore Diagnostics",
            bg="#1f1f1f",
            fg="#87CEFA",
            font=("sans-serif", 13, "bold")
        ).pack(anchor="w", pady=(0, 10))

        details = [
            f"Selected file: {selected_path}",
            f"Staged copy: {staged_path}",
            f"Detected container: {container_kind}",
            f"Detected restore mode: {mode}",
            f"Managed-preferences plist written: {'yes' if managed_written else 'no'}",
            f"Managed-preferences target: {USER_MANAGED_PREFS_FILE if managed_written else '(not written for this restore mode)'}",
            f"Payload key count: {len(payload.keys()) if isinstance(payload, dict) else 0}",
        ]

        summary = tk.Text(
            outer,
            height=8,
            wrap="word",
            bg="#101010",
            fg="#e6e6e6",
            insertbackground="white",
            relief="flat"
        )
        summary.pack(fill="x", pady=(0, 10))
        summary.insert("1.0", "\n".join(details))
        summary.configure(state="disabled")

        tk.Label(
            outer,
            text="Payload keys restored:",
            bg="#1f1f1f",
            fg="#FFA07A",
            font=("sans-serif", 10, "bold")
        ).pack(anchor="w", pady=(0, 6))

        frame = tk.Frame(outer, bg="#1f1f1f")
        frame.pack(fill="both", expand=True)
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        keys_box = tk.Text(
            frame,
            wrap="none",
            bg="#101010",
            fg="#dcdcdc",
            insertbackground="white",
            yscrollcommand=scrollbar.set,
            relief="flat"
        )
        keys_box.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=keys_box.yview)

        if isinstance(payload, dict):
            lines = []
            for key in sorted(payload.keys()):
                value = payload[key]
                preview = repr(value)
                if len(preview) > 180:
                    preview = preview[:177] + "..."
                lines.append(f"{key} = {preview}")
            keys_box.insert("1.0", "\n".join(lines) if lines else "(No keys found)")
        else:
            keys_box.insert("1.0", "(Payload was not a dictionary)")
        keys_box.configure(state="disabled")

        btns = tk.Frame(outer, bg="#1f1f1f")
        btns.pack(fill="x", pady=(10, 0))
        tk.Button(btns, text="Close", command=diag.destroy, width=12).pack(side="right")

        diag.update_idletasks()
        x = root.winfo_rootx() + max(20, (root.winfo_width() // 2) - (diag.winfo_width() // 2))
        y = root.winfo_rooty() + max(20, (root.winfo_height() // 2) - (diag.winfo_height() // 2))
        diag.geometry(f"+{x}+{y}")
        diag.wait_window()

    def do_restore_from_plist(selected_path, invoked_from_reset=False):
        staged_path = stage_restore_source(selected_path)
        parsed = load_plist_any(staged_path)
        payload, container_kind = normalize_restore_root(parsed)
        mode = classify_restore_payload(payload)

        if mode == "invalid":
            raise Exception("The selected plist does not contain a valid dictionary payload.")
        if mode == "empty":
            raise Exception("The selected plist is empty and cannot be restored.")

        set_status("Restoring plist into Brave...")
        write_log(f"Restore detected container kind: {container_kind}, payload mode: {mode}")

        apply_payload_to_live_domain(payload, mode)
        managed_written = write_managed_plist_if_needed(payload, mode)
        flush_pref_cache()
        clear_brave_runtime_caches()
        reload_ui_from_registry()
        set_dirty_state(False)

        if managed_written:
            set_status("Plist restored to Brave and managed-preferences path successfully.")
        else:
            set_status("Plist restored to Brave successfully.")

        show_restore_diagnostics(selected_path, staged_path, container_kind, mode, payload, managed_written)

        if not invoked_from_reset:
            extra = "\n\nSlimBrave also restored the managed-preferences plist path." if managed_written else ""
            extra += f"\n\nDetection summary:\nContainer = {container_kind}\nRestore mode = {mode}"
            messagebox.showinfo("Restore Successful", f"The selected plist was read and restored successfully.{extra}")

    def restore_plist_dialog(invoked_from_reset=False):
        f = filedialog.askopenfilename(filetypes=[("Property List / XML", "*.plist *.xml"), ("All files", "*.*")])
        if not f:
            return False
        try:
            if not graceful_close_brave():
                return False
            do_restore_from_plist(f, invoked_from_reset=invoked_from_reset)
            return True
        except Exception as e:
            write_log(f"Plist restore failed: {e}")
            messagebox.showerror(
                "Restore Failed",
                "Failed to restore the selected plist.\n\n"
                f"{e}\n\n"
                "This version stages the selected file, converts it safely if needed, restores the Brave domain, and also writes"
                " the managed-preferences plist path when the backup looks like an old SlimBrave policy plist."
            )
            return False

    def remove_managed_pref_files():
        for path in (USER_MANAGED_PREFS_FILE, SYSTEM_MANAGED_PREFS_FILE):
            if os.path.exists(path):
                try:
                    os.remove(path)
                    write_log(f"Removed managed preferences file: {path}")
                except Exception as e:
                    write_log(f"Could not remove managed preferences file {path}: {e}")

    def scrub_slimbrave_keys_only():
        for feat in all_features:
            delete_default(feat["Key"])

        for perm in permission_settings:
            delete_default(perm["Key"])
            if perm["Key"] == "DefaultFileSystemReadGuardSetting":
                delete_default("DefaultFileSystemWriteGuardSetting")

        delete_default("SafeBrowsingProtectionLevel")
        delete_default("DnsOverHttpsMode")

    def restore_original_snapshot_if_present():
        if not os.path.exists(SNAPSHOT_FILE):
            return False
        try:
            snapshot_dict = load_plist_any(SNAPSHOT_FILE)
            payload, _ = normalize_restore_root(snapshot_dict)
            if not isinstance(payload, dict):
                return False
            import_domain_from_dict(payload)
            write_log(f"Restored original snapshot from {SNAPSHOT_FILE}")
            return True
        except Exception as e:
            write_log(f"Failed restoring original snapshot: {e}")
            return False

    def reload_ui_from_registry():
        nonlocal suspend_dirty_tracking
        suspend_dirty_tracking = True

        for var in all_feature_vars.values():
            var.set(0)
        for var in all_perm_vars.values():
            var.set("Not Set")
        sb_var.set("")
        dns_var.set("")

        any_loaded = False

        for feat in all_features:
            val = read_default(feat["Key"])
            if val is not None:
                any_loaded = True
                if feat["Type"] == "-array":
                    if val:
                        all_feature_vars[feat["Key"]].set(1)
                else:
                    val_str = str(val).strip().lower()
                    expected = str(feat["Value"]).lower()
                    if expected == "true" and val_str in ("1", "true"):
                        all_feature_vars[feat["Key"]].set(1)
                    elif expected == "false" and val_str in ("0", "false"):
                        all_feature_vars[feat["Key"]].set(1)
                    elif val_str == expected:
                        all_feature_vars[feat["Key"]].set(1)

        for perm in permission_settings:
            val = read_default(perm["Key"])
            if val is not None:
                any_loaded = True
                try:
                    val = int(val)
                    if val == 3:
                        all_perm_vars[perm["Key"]].set("Ask")
                    elif val == 1:
                        all_perm_vars[perm["Key"]].set("Allow")
                    elif perm["Key"] == "PaymentMethodQueryEnabled" and val == 0:
                        all_perm_vars[perm["Key"]].set("Block")
                    elif val == 2:
                        all_perm_vars[perm["Key"]].set("Block")
                except Exception:
                    pass

        sb_val = read_default("SafeBrowsingProtectionLevel")
        if sb_val is not None:
            any_loaded = True
            if sb_val == "1":
                sb_var.set("On")
            elif sb_val == "0":
                sb_var.set("Off")

        dns_val = read_default("DnsOverHttpsMode")
        if dns_val is not None:
            any_loaded = True
            if dns_val == "automatic":
                dns_var.set("On")
            elif dns_val == "off":
                dns_var.set("Off")

        suspend_dirty_tracking = False
        update_baseline()
        check_dirty_state()

        if not any_loaded:
            set_status("No Brave policy settings found – SlimBrave hasn't been configured on this system before, or Brave isn't installed.")
        else:
            set_status("UI reloaded from current macOS Brave defaults.")

    def reset_settings():
        answer = messagebox.askyesno(
            "Confirm Repair",
            "This will run a proper repair reset.\n\n"
            "SlimBrave will close Brave, scrub its managed keys, remove managed policy files, clear applicable caches, "
            "and then ask whether you want to restore a plist backup as part of the repair.\n\n"
            "Continue?"
        )
        if not answer:
            return

        if not graceful_close_brave():
            return

        set_status("Running repair reset...")
        try:
            scrub_slimbrave_keys_only()
            remove_managed_pref_files()
            restored_snapshot = restore_original_snapshot_if_present()
            flush_pref_cache()
            clear_brave_runtime_caches()
            reload_ui_from_registry()

            restore_external = messagebox.askyesno(
                "Optional Backup Restore",
                "Repair reset is complete.\n\n"
                "Do you have a plist backup you'd also like to restore to?"
            )
            if restore_external:
                ok = restore_plist_dialog(invoked_from_reset=True)
                if ok:
                    messagebox.showinfo(
                        "Repair Successful",
                        "SlimBrave repair completed and your selected plist backup was restored successfully."
                    )
                else:
                    messagebox.showwarning(
                        "Repair Complete",
                        "SlimBrave completed the scrub/reset portion, but the selected plist backup was not restored."
                    )
            else:
                if restored_snapshot:
                    messagebox.showinfo(
                        "Repair Successful",
                        "SlimBrave reset completed and the internally saved pre-SlimBrave Brave snapshot was restored."
                    )
                else:
                    messagebox.showinfo(
                        "Repair Successful",
                        "SlimBrave reset completed. Managed policy files were removed and applicable caches were cleared."
                    )
            set_status("Repair reset completed.")
        except Exception as e:
            write_log(f"Reset error: {e}")
            messagebox.showerror("Reset Failed", f"An error occurred during reset:\n{e}")

    def import_plist():
        restore_plist_dialog(invoked_from_reset=False)

    def export_settings():
        f = filedialog.asksaveasfilename(defaultextension=".json", initialfile="SlimBraveSettings.json")
        if f:
            with open(f, "w", encoding="utf-8") as file:
                json.dump(get_ui_snapshot(), file, indent=4)
            set_status(f"Settings exported to {f}")

    def import_settings():
        f = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if f:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
            nonlocal suspend_dirty_tracking
            suspend_dirty_tracking = True

            for var in all_feature_vars.values():
                var.set(0)
            if "Features" in data:
                for key in data["Features"]:
                    if key in all_feature_vars:
                        all_feature_vars[key].set(1)

            for var in all_perm_vars.values():
                var.set("Not Set")
            if "Permissions" in data:
                for k, v in data["Permissions"].items():
                    if k in all_perm_vars:
                        all_perm_vars[k].set(v)

            if "SafeBrowsing" in data:
                sb_var.set(data["SafeBrowsing"])
            if "DnsMode" in data:
                dns_var.set(data["DnsMode"])

            suspend_dirty_tracking = False
            check_dirty_state()
            set_status("Settings imported. Pending save.")

    def apply_settings():
        if not graceful_close_brave():
            return

        ensure_snapshot_exists()

        ans = messagebox.askyesno(
            "Backup Settings",
            "Would you like to export your current Brave settings to a pure XML .plist file on your Desktop before applying changes? (Recommended)"
        )
        if ans:
            set_status("Backing up current Brave domain...")
            backup_path = os.path.expanduser("~/Desktop/Brave_Policies_Backup.plist")
            export_domain_to_path(backup_path)
            export_domain_to_path(INTERNAL_LAST_EXPORT)
            write_log(f"Policies backed up to {backup_path}")

        set_status("Applying settings to macOS defaults...")

        for feat in all_features:
            if all_feature_vars[feat["Key"]].get() == 1:
                write_default(feat["Key"], feat["Type"], feat["Value"])
                write_log(f"Applied policy: {feat['Key']}")
            else:
                delete_default(feat["Key"])

        managed_payload = {}
        for perm in permission_settings:
            sel = all_perm_vars[perm["Key"]].get()
            k = perm["Key"]
            if sel == "Not Set":
                delete_default(k)
                if k == "DefaultFileSystemReadGuardSetting":
                    delete_default("DefaultFileSystemWriteGuardSetting")
            else:
                val = 0
                if sel == "Ask":
                    val = 3
                elif sel == "Block":
                    val = 0 if k == "PaymentMethodQueryEnabled" else 2
                elif sel == "Allow":
                    val = 1
                write_default(k, "-int", val)
                managed_payload[k] = val
                if k == "DefaultFileSystemReadGuardSetting":
                    write_default("DefaultFileSystemWriteGuardSetting", "-int", val)
                    managed_payload["DefaultFileSystemWriteGuardSetting"] = val
                write_log(f"Applied permission: {k} = {val}")

        if sb_var.get() == "On":
            write_default("SafeBrowsingProtectionLevel", "-int", 1)
            managed_payload["SafeBrowsingProtectionLevel"] = 1
        elif sb_var.get() == "Off":
            write_default("SafeBrowsingProtectionLevel", "-int", 0)
            managed_payload["SafeBrowsingProtectionLevel"] = 0
        else:
            delete_default("SafeBrowsingProtectionLevel")

        if dns_var.get() == "On":
            write_default("DnsOverHttpsMode", "-string", "automatic")
            managed_payload["DnsOverHttpsMode"] = "automatic"
        elif dns_var.get() == "Off":
            write_default("DnsOverHttpsMode", "-string", "off")
            managed_payload["DnsOverHttpsMode"] = "off"
        else:
            delete_default("DnsOverHttpsMode")

        for feat in all_features:
            if all_feature_vars[feat["Key"]].get() == 1:
                managed_payload[feat["Key"]] = feat["Value"]

        if managed_payload:
            write_xml_plist(USER_MANAGED_PREFS_FILE, managed_payload)
            write_log(f"Wrote managed policy plist to {USER_MANAGED_PREFS_FILE}")
        else:
            remove_if_exists(USER_MANAGED_PREFS_FILE)

        flush_pref_cache()
        save_current_state()
        update_baseline()
        check_dirty_state()

        show_custom_info("SlimBrave", "Settings applied successfully! Open Brave to see changes.")
        set_status("Settings applied successfully.")

    def show_custom_info(title, message):
        dialog = tk.Toplevel(root)
        dialog.title(title)
        dialog.transient(root)
        dialog.grab_set()
        dialog.iconphoto(False, icon_img)
        tk.Label(dialog, text=message, font=("sans-serif", 10), padx=20, pady=20).pack()
        tk.Button(dialog, text="OK", command=dialog.destroy, width=10).pack(pady=10)
        dialog.update_idletasks()
        x = root.winfo_rootx() + (root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = root.winfo_rooty() + (root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        dialog.wait_window()

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

    btn_priv = ttk.Button(inner_top, text="High Privacy + Moderate Security", style="Orange.TButton", command=lambda: apply_preset("privacy"))
    btn_priv.pack(side="left", padx=10)
    create_tooltip(btn_priv, "Applies the recommended preset for High Privacy and Moderate Security.")

    btn_sec = ttk.Button(inner_top, text="High Security + Moderate Privacy", style="Orange.TButton", command=lambda: apply_preset("security"))
    btn_sec.pack(side="left", padx=10)
    create_tooltip(btn_sec, "Applies the recommended preset for High Security and Moderate Privacy.")

    save_status_label = tk.Label(inner_top, textvariable=save_status_var, bg="#191919", fg="#90EE90", font=("sans-serif", 10, "bold"))
    save_status_label.pack(side="right", padx=(50, 0))

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

    def on_root_mousewheel(event):
        widget = root.winfo_containing(event.x_root, event.y_root)
        if not widget:
            return
        while widget:
            if isinstance(widget, ScrollableFrame):
                if event.num == 4:
                    delta = -1
                elif event.num == 5:
                    delta = 1
                else:
                    delta = event.delta if sys.platform == "darwin" else event.delta / 120
                    if delta > 0:
                        delta = 1
                    elif delta < 0:
                        delta = -1
                widget.scroll(delta)
                return
            widget = widget.master

    for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        root.bind(ev, on_root_mousewheel)

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

    status_label = tk.Label(bottom_bar, textvariable=status_var, bg="#2d2d2d", fg="#aaaaaa", font=("courier", 10), anchor="w", padx=10)
    status_label.pack(side="bottom", fill="x")

    root.after(100, reload_ui_from_registry)
    root.mainloop()


if __name__ == "__main__":
    dependency_setup()
    main()
