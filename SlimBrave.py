#!/usr/bin/env python3
# SlimBrave - Revived - v1.2.0 (macOS Edition)
# Major fixes:
# - Stops using the live com.brave.Browser domain as the primary managed policy store
# - Writes SlimBrave-managed policies to ~/Library/Managed Preferences/com.brave.Browser.plist
# - Strips legacy SlimBrave keys from the live domain during apply/restore/repair
# - Deep de-crash repair with progress bar and on-screen diagnostics
# - Quarantines the full Brave user-data folder during aggressive repair
# - Safe plist restore: filters to SlimBrave-managed keys only
# - UI reload reads managed prefs first, then legacy live-domain keys only for migration visibility

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
    print("Homebrew is required if SlimBrave needs to bootstrap a modern Python/Tk environment.")
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

    USER_MANAGED_PREFS_DIR = os.path.expanduser("~/Library/Managed Preferences")
    USER_MANAGED_PREFS_FILE = os.path.join(USER_MANAGED_PREFS_DIR, f"{DOMAIN}.plist")
    SYSTEM_MANAGED_PREFS_FILE = os.path.join("/Library/Managed Preferences", f"{DOMAIN}.plist")

    BRAVE_SUPPORT_DIR = os.path.expanduser("~/Library/Application Support/BraveSoftware/Brave-Browser")
    BRAVE_USER_DATA_DIR = BRAVE_SUPPORT_DIR
    BRAVE_DEFAULT_PROFILE_DIR = os.path.join(BRAVE_USER_DATA_DIR, "Default")
    BRAVE_LOCAL_STATE_FILE = os.path.join(BRAVE_USER_DATA_DIR, "Local State")
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

    telemetry_features = [
        {"Name": "Disable Metrics Reporting", "Key": "MetricsReportingEnabled", "Value": False, "Type": "bool", "ToolTip": "Stops Brave from sending anonymous usage and crash reports.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Safe Browsing Reporting", "Key": "SafeBrowsingExtendedReportingEnabled", "Value": False, "Type": "bool", "ToolTip": "Stops Brave from sending extended Safe Browsing data back to servers.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable URL Data Collection", "Key": "UrlKeyedAnonymizedDataCollectionEnabled", "Value": False, "Type": "bool", "ToolTip": "Stops sending anonymized URLs to help improve the browser.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Feedback Surveys", "Key": "FeedbackSurveysEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables proactive feedback survey prompts.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable P3A Telemetry", "Key": "BraveP3AEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables Privacy-Preserving Product Analytics completely.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Daily Stats Ping", "Key": "BraveStatsPingEnabled", "Value": False, "Type": "bool", "ToolTip": "Stops the daily active user ping.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Web Discovery", "Key": "BraveWebDiscoveryEnabled", "Value": False, "Type": "bool", "ToolTip": "Prevents anonymous search/browsing data from being sent to Brave Search.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
    ]

    privacy_features = [
        {"Name": "Disable Autofill (Addresses)", "Key": "AutofillAddressEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables saving and autofilling addresses.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Autofill (Credit Cards)", "Key": "AutofillCreditCardEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables saving and autofilling credit cards.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Password Manager", "Key": "PasswordManagerEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables the built-in password manager.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Browser Sign-in", "Key": "BrowserSignin", "Value": 0, "Type": "int", "ToolTip": "Prevents syncing your data to cloud accounts.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable WebRTC IP Leak", "Key": "WebRtcIPHandling", "Value": "disable_non_proxied_udp", "Type": "string", "ToolTip": "Prevents your real IP address from leaking when using a VPN.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable QUIC Protocol", "Key": "QuicAllowed", "Value": False, "Type": "bool", "ToolTip": "Forces standard TCP, stopping UDP firewall bypasses and tracking.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Block Third Party Cookies", "Key": "BlockThirdPartyCookies", "Value": True, "Type": "bool", "ToolTip": "Blocks all third-party tracking cookies.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Enable Do Not Track", "Key": "EnableDoNotTrack", "Value": True, "Type": "bool", "ToolTip": "Sends a Do Not Track request with your browsing traffic.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Force Google SafeSearch", "Key": "ForceGoogleSafeSearch", "Value": True, "Type": "bool", "ToolTip": "Filters explicit search results.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Disable IPFS", "Key": "IPFSEnabled", "Value": False, "Type": "bool", "ToolTip": "Stops peer-to-peer background connections to unknown nodes.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Force Incognito Mode", "Key": "IncognitoModeAvailability", "Value": 2, "Type": "int", "ToolTip": "Forces the browser to always open in Incognito Mode.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Force Download Prompts", "Key": "PromptForDownloadLocation", "Value": True, "Type": "bool", "ToolTip": "Forces Brave to ask where to save a file before downloading, preventing drive-by downloads.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Clear Data on Exit", "Key": "ClearBrowsingDataOnExitList", "Value": [
            "browsing_history",
            "download_history",
            "cookies_and_other_site_data",
            "cached_images_and_files",
            "password_signin",
            "autofill",
            "site_settings",
            "hosted_app_data"
        ], "Type": "array", "ToolTip": "Wipes all cookies, cache, and browsing history the moment the browser closes.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Force HTTPS-Only Mode", "Key": "HttpsOnlyMode", "Value": "force_enabled", "Type": "string", "ToolTip": "Strictly upgrades all connections to HTTPS and blocks unencrypted HTTP traffic.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
    ]

    brave_features = [
        {"Name": "Disable Brave Rewards and Sponsored Elements", "Key": "BraveRewardsDisabled", "Value": True, "Type": "bool", "ToolTip": "Completely disables the Brave Crypto Rewards system and disables sponsored backgrounds on the New Tab page.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave Wallet", "Key": "BraveWalletDisabled", "Value": True, "Type": "bool", "ToolTip": "Disables the built-in Brave Crypto Wallet.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave VPN", "Key": "BraveVPNDisabled", "Value": True, "Type": "bool", "ToolTip": "Removes the Brave VPN integration and prompts.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave AI Chat", "Key": "BraveAIChatEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables Brave Leo (AI Chat) integration.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Tor", "Key": "TorDisabled", "Value": True, "Type": "bool", "ToolTip": "Disables built-in Tor window support.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Sync", "Key": "SyncDisabled", "Value": True, "Type": "bool", "ToolTip": "Disables Brave Sync functionality across devices.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Disable Brave News", "Key": "BraveNewsDisabled", "Value": True, "Type": "bool", "ToolTip": "Removes the Brave News feed bloat from the New Tab page.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave Talk", "Key": "BraveTalkDisabled", "Value": True, "Type": "bool", "ToolTip": "Removes the built-in video calling integration.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Speedreader", "Key": "BraveSpeedreaderEnabled", "Value": False, "Type": "bool", "ToolTip": "Completely disables the Speedreader feature, reader mode, and automatic prompts.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Wayback Machine Prompts", "Key": "BraveWaybackMachineEnabled", "Value": False, "Type": "bool", "ToolTip": "Stops Brave from asking to search the Internet Archive when you hit a 404 error.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
    ]

    perf_features = [
        {"Name": "Disable Background Mode", "Key": "BackgroundModeEnabled", "Value": False, "Type": "bool", "ToolTip": "Prevents extensions/apps from running after the browser is closed.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Media Recommendations", "Key": "MediaRecommendationsEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables media recommendations to save memory.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Shopping List", "Key": "ShoppingListEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables the shopping list feature.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Always Open PDF Externally", "Key": "AlwaysOpenPdfExternally", "Value": True, "Type": "bool", "ToolTip": "Forces PDFs to download and open in your system viewer instead of the browser.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Translate", "Key": "TranslateEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables automatic translation prompts.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Spellcheck", "Key": "SpellcheckEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables the built-in spellchecker to save CPU cycles.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Promotions", "Key": "PromotionsEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables Brave promotional notifications.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Search Suggestions", "Key": "SearchSuggestEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables predictive search suggestions in the URL bar.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Printing", "Key": "PrintingEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables the browser print function.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Default Browser Prompt", "Key": "DefaultBrowserSettingEnabled", "Value": False, "Type": "bool", "ToolTip": "Stops Brave from asking to be the default browser.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Developer Tools", "Key": "DeveloperToolsDisabled", "Value": True, "Type": "bool", "ToolTip": "Disables F12 / Inspect Element.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Disable Brave Playlist", "Key": "BravePlaylistEnabled", "Value": False, "Type": "bool", "ToolTip": "Removes the Brave Playlist media feature.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
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
        {"Name": "Payment Handlers", "Key": "PaymentMethodQueryEnabled", "Options": ["Not Set", "Block", "Allow"], "ToolTip": "Allows sites to check if you have local payment apps installed.\n\nSuggested Settings for Privacy: Block | Security: Block"},
    ]

    ALL_FEATURES = telemetry_features + privacy_features + brave_features + perf_features
    managed_keys = {feat["Key"] for feat in ALL_FEATURES}
    managed_keys.update({perm["Key"] for perm in permission_settings})
    managed_keys.update({"DefaultFileSystemWriteGuardSetting", "SafeBrowsingProtectionLevel", "DnsOverHttpsMode"})

    BOOL_POLICY_KEYS = {feat["Key"] for feat in ALL_FEATURES if feat["Type"] == "bool"}
    STRING_POLICY_KEYS = {feat["Key"] for feat in ALL_FEATURES if feat["Type"] == "string"}
    ARRAY_POLICY_KEYS = {feat["Key"] for feat in ALL_FEATURES if feat["Type"] == "array"}
    INT_POLICY_KEYS = {feat["Key"] for feat in ALL_FEATURES if feat["Type"] == "int"}

    CONTENT_SETTING_KEYS = {
        "DefaultGeolocationSetting",
        "DefaultVideoCaptureSetting",
        "DefaultAudioCaptureSetting",
        "DefaultNotificationsSetting",
        "DefaultJavaScriptSetting",
        "DefaultImagesSetting",
        "DefaultPopupsSetting",
        "DefaultWebUsbGuardSetting",
        "DefaultSerialGuardSetting",
        "DefaultWebHidGuardSetting",
        "DefaultFileSystemReadGuardSetting",
        "DefaultFileSystemWriteGuardSetting",
        "DefaultClipboardSetting",
        "DefaultWindowPlacementSetting",
        "DefaultLocalFontsSetting",
    }

    root = tk.Tk()
    root.title("SlimBrave - Revived v1.2.0 (macOS)")
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
                wraplength=430,
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

    def coerce_bool(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            s = value.strip().lower()
            if s in {"1", "true", "yes", "on"}:
                return True
            if s in {"0", "false", "no", "off"}:
                return False
        return None

    class ProgressDialog:
        def __init__(self, parent, title="SlimBrave Progress"):
            self.top = tk.Toplevel(parent)
            self.top.title(title)
            self.top.transient(parent)
            self.top.grab_set()
            self.top.configure(bg="#1f1f1f")
            self.top.geometry("820x500")
            self.top.minsize(760, 430)
            self.top.iconphoto(False, icon_img)

            self.msg_var = tk.StringVar(value="Starting...")
            self.pb_var = tk.DoubleVar(value=0)

            outer = tk.Frame(self.top, bg="#1f1f1f")
            outer.pack(fill="both", expand=True, padx=12, pady=12)

            tk.Label(outer, text=title, bg="#1f1f1f", fg="#87CEFA", font=("sans-serif", 13, "bold")).pack(anchor="w", pady=(0, 8))
            tk.Label(outer, textvariable=self.msg_var, bg="#1f1f1f", fg="white", anchor="w", justify="left", font=("sans-serif", 10)).pack(fill="x", pady=(0, 8))

            self.pb = ttk.Progressbar(outer, orient="horizontal", mode="determinate", maximum=100, variable=self.pb_var)
            self.pb.pack(fill="x", pady=(0, 10))

            log_frame = tk.Frame(outer, bg="#1f1f1f")
            log_frame.pack(fill="both", expand=True)

            sb = tk.Scrollbar(log_frame)
            sb.pack(side="right", fill="y")

            self.text = tk.Text(log_frame, wrap="word", bg="#101010", fg="#dcdcdc", insertbackground="white", relief="flat", yscrollcommand=sb.set)
            self.text.pack(side="left", fill="both", expand=True)
            sb.config(command=self.text.yview)

            btns = tk.Frame(outer, bg="#1f1f1f")
            btns.pack(fill="x", pady=(10, 0))

            self.close_btn = tk.Button(btns, text="Close", state="disabled", command=self.top.destroy, width=12)
            self.close_btn.pack(side="right")

            self.top.update_idletasks()

        def step(self, percent, message):
            self.pb_var.set(percent)
            self.msg_var.set(message)
            self.log(message)
            self.top.update_idletasks()

        def log(self, message):
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.text.insert("end", f"[{timestamp}] {message}\n")
            self.text.see("end")
            self.top.update_idletasks()

        def finish(self, message):
            self.step(100, message)
            self.close_btn.config(state="normal")

    def show_text_report(title, lines):
        win = tk.Toplevel(root)
        win.title(title)
        win.transient(root)
        win.grab_set()
        win.configure(bg="#1f1f1f")
        win.geometry("860x560")
        win.minsize(780, 460)
        win.iconphoto(False, icon_img)

        outer = tk.Frame(win, bg="#1f1f1f")
        outer.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(outer, text=title, bg="#1f1f1f", fg="#87CEFA", font=("sans-serif", 13, "bold")).pack(anchor="w", pady=(0, 8))

        frame = tk.Frame(outer, bg="#1f1f1f")
        frame.pack(fill="both", expand=True)

        sb = tk.Scrollbar(frame)
        sb.pack(side="right", fill="y")

        txt = tk.Text(frame, wrap="word", bg="#101010", fg="#dcdcdc", insertbackground="white", relief="flat", yscrollcommand=sb.set)
        txt.pack(side="left", fill="both", expand=True)
        sb.config(command=txt.yview)

        txt.insert("1.0", "\n".join(lines))
        txt.configure(state="disabled")

        tk.Button(outer, text="Close", command=win.destroy, width=12).pack(side="right", pady=(10, 0))
        win.update_idletasks()

    def plist_load_any(path):
        with open(path, "rb") as f:
            return plistlib.load(f)

    def plist_dump_xml(path, data):
        with open(path, "wb") as f:
            plistlib.dump(data, f, fmt=plistlib.FMT_XML, sort_keys=True)

    def defaults_export_domain_dict():
        fd, temp_path = tempfile.mkstemp(prefix="slimbrave-domain-", suffix=".plist")
        os.close(fd)
        try:
            res = run_cmd(["defaults", "export", DOMAIN, temp_path])
            if res.returncode != 0:
                return {}
            data = plist_load_any(temp_path)
            return data if isinstance(data, dict) else {}
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    def defaults_import_domain_dict(data):
        fd, temp_path = tempfile.mkstemp(prefix="slimbrave-import-", suffix=".plist")
        os.close(fd)
        try:
            plist_dump_xml(temp_path, data)
            res = run_cmd(["defaults", "import", DOMAIN, temp_path])
            if res.returncode != 0:
                err = res.stderr.strip() or res.stdout.strip() or "defaults import failed"
                raise Exception(err)
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    def normalize_restore_root(data):
        if not isinstance(data, dict):
            raise Exception("Selected plist is not a dictionary plist.")

        if "__SlimBrave__" in data and isinstance(data.get("Payload"), dict):
            return data["Payload"], f"wrapped:{data['__SlimBrave__'].get('kind', 'unknown')}"

        if DOMAIN in data and isinstance(data.get(DOMAIN), dict):
            return data[DOMAIN], "nested-domain"

        return data, "plain-dict"

    def sanitize_managed_payload(raw_payload):
        cleaned = {}
        warnings = []

        if not isinstance(raw_payload, dict):
            return {}, ["Payload was not a dictionary."]

        for key, value in raw_payload.items():
            if key not in managed_keys:
                continue

            if key in BOOL_POLICY_KEYS:
                b = coerce_bool(value)
                if b is None:
                    warnings.append(f"Skipped {key}: expected bool, got {type(value).__name__}")
                    continue
                cleaned[key] = b
                continue

            if key in STRING_POLICY_KEYS:
                cleaned[key] = str(value)
                continue

            if key in ARRAY_POLICY_KEYS:
                if isinstance(value, list):
                    cleaned[key] = [str(x) for x in value]
                else:
                    warnings.append(f"Skipped {key}: expected array, got {type(value).__name__}")
                continue

            if key in INT_POLICY_KEYS:
                try:
                    cleaned[key] = int(value)
                except Exception:
                    warnings.append(f"Skipped {key}: expected int, got {type(value).__name__}")
                continue

            if key in CONTENT_SETTING_KEYS:
                try:
                    iv = int(value)
                    if iv in (1, 2, 3):
                        cleaned[key] = iv
                    else:
                        warnings.append(f"Skipped {key}: invalid content-setting value {iv}")
                except Exception:
                    warnings.append(f"Skipped {key}: invalid content-setting type {type(value).__name__}")
                continue

            if key == "PaymentMethodQueryEnabled":
                b = coerce_bool(value)
                if b is None:
                    try:
                        b = bool(int(value))
                    except Exception:
                        b = None
                if b is None:
                    warnings.append(f"Skipped {key}: expected bool-compatible value, got {type(value).__name__}")
                else:
                    cleaned[key] = b
                continue

            if key == "SafeBrowsingProtectionLevel":
                try:
                    iv = int(value)
                    if iv in (0, 1):
                        cleaned[key] = iv
                    else:
                        warnings.append(f"Skipped {key}: invalid value {iv}")
                except Exception:
                    warnings.append(f"Skipped {key}: expected int 0/1")
                continue

            if key == "DnsOverHttpsMode":
                s = str(value).strip().lower()
                if s in {"automatic", "off"}:
                    cleaned[key] = s
                else:
                    warnings.append(f"Skipped {key}: invalid value {value!r}")
                continue

            cleaned[key] = value

        if "DefaultFileSystemReadGuardSetting" in cleaned and "DefaultFileSystemWriteGuardSetting" not in cleaned:
            cleaned["DefaultFileSystemWriteGuardSetting"] = cleaned["DefaultFileSystemReadGuardSetting"]

        return cleaned, warnings

    def read_managed_prefs_dict():
        if os.path.exists(USER_MANAGED_PREFS_FILE):
            try:
                data = plist_load_any(USER_MANAGED_PREFS_FILE)
                if isinstance(data, dict):
                    cleaned, _ = sanitize_managed_payload(data)
                    return cleaned
            except Exception as e:
                write_log(f"Could not read user managed prefs: {e}")

        if os.path.exists(SYSTEM_MANAGED_PREFS_FILE):
            try:
                data = plist_load_any(SYSTEM_MANAGED_PREFS_FILE)
                if isinstance(data, dict):
                    cleaned, _ = sanitize_managed_payload(data)
                    return cleaned
            except Exception as e:
                write_log(f"Could not read system managed prefs: {e}")

        return {}

    def write_user_managed_prefs_dict(payload):
        os.makedirs(USER_MANAGED_PREFS_DIR, exist_ok=True)
        plist_dump_xml(USER_MANAGED_PREFS_FILE, payload)
        write_log(f"Wrote managed preferences to {USER_MANAGED_PREFS_FILE}")

    def remove_managed_pref_files():
        removed = []
        for path in (USER_MANAGED_PREFS_FILE, SYSTEM_MANAGED_PREFS_FILE):
            if os.path.exists(path):
                try:
                    os.remove(path)
                    removed.append(path)
                    write_log(f"Removed managed preferences file: {path}")
                except Exception as e:
                    write_log(f"Failed removing managed prefs file {path}: {e}")
        return removed

    def strip_legacy_policy_keys_from_live_domain():
        domain_data = defaults_export_domain_dict()
        if not isinstance(domain_data, dict):
            domain_data = {}

        removed = []
        for key in list(domain_data.keys()):
            if key in managed_keys:
                removed.append(key)
                domain_data.pop(key, None)

        defaults_import_domain_dict(domain_data)
        return sorted(removed)

    def build_managed_payload_from_ui():
        payload = {}

        for feat in ALL_FEATURES:
            if all_feature_vars[feat["Key"]].get() != 1:
                continue

            if feat["Type"] == "bool":
                payload[feat["Key"]] = bool(feat["Value"])
            elif feat["Type"] == "int":
                payload[feat["Key"]] = int(feat["Value"])
            elif feat["Type"] == "string":
                payload[feat["Key"]] = str(feat["Value"])
            elif feat["Type"] == "array":
                payload[feat["Key"]] = list(feat["Value"])

        for perm in permission_settings:
            sel = all_perm_vars[perm["Key"]].get()
            key = perm["Key"]

            if sel == "Not Set":
                continue

            if key == "PaymentMethodQueryEnabled":
                payload[key] = (sel == "Allow")
                continue

            if sel == "Ask":
                payload[key] = 3
            elif sel == "Block":
                payload[key] = 2
            elif sel == "Allow":
                payload[key] = 1

            if key == "DefaultFileSystemReadGuardSetting":
                payload["DefaultFileSystemWriteGuardSetting"] = payload[key]

        if sb_var.get() == "On":
            payload["SafeBrowsingProtectionLevel"] = 1
        elif sb_var.get() == "Off":
            payload["SafeBrowsingProtectionLevel"] = 0

        if dns_var.get() == "On":
            payload["DnsOverHttpsMode"] = "automatic"
        elif dns_var.get() == "Off":
            payload["DnsOverHttpsMode"] = "off"

        return payload

    def apply_payload_to_ui(payload):
        nonlocal suspend_dirty_tracking
        suspend_dirty_tracking = True

        for var in all_feature_vars.values():
            var.set(0)
        for var in all_perm_vars.values():
            var.set("Not Set")
        sb_var.set("")
        dns_var.set("")

        for feat in ALL_FEATURES:
            key = feat["Key"]
            if key not in payload:
                continue

            value = payload[key]
            if feat["Type"] == "array":
                if isinstance(value, list) and len(value) > 0:
                    all_feature_vars[key].set(1)
            elif feat["Type"] == "bool":
                if coerce_bool(value) == bool(feat["Value"]):
                    all_feature_vars[key].set(1)
            elif feat["Type"] == "int":
                try:
                    if int(value) == int(feat["Value"]):
                        all_feature_vars[key].set(1)
                except Exception:
                    pass
            elif feat["Type"] == "string":
                if str(value) == str(feat["Value"]):
                    all_feature_vars[key].set(1)

        for perm in permission_settings:
            key = perm["Key"]
            if key not in payload:
                continue

            if key == "PaymentMethodQueryEnabled":
                b = coerce_bool(payload[key])
                if b is True:
                    all_perm_vars[key].set("Allow")
                elif b is False:
                    all_perm_vars[key].set("Block")
                continue

            try:
                iv = int(payload[key])
            except Exception:
                continue

            if iv == 3:
                all_perm_vars[key].set("Ask")
            elif iv == 2:
                all_perm_vars[key].set("Block")
            elif iv == 1:
                all_perm_vars[key].set("Allow")

        if "SafeBrowsingProtectionLevel" in payload:
            try:
                sbv = int(payload["SafeBrowsingProtectionLevel"])
                if sbv == 1:
                    sb_var.set("On")
                elif sbv == 0:
                    sb_var.set("Off")
            except Exception:
                pass

        if "DnsOverHttpsMode" in payload:
            d = str(payload["DnsOverHttpsMode"]).strip().lower()
            if d == "automatic":
                dns_var.set("On")
            elif d == "off":
                dns_var.set("Off")

        suspend_dirty_tracking = False
        update_baseline()
        check_dirty_state()

    def merged_policy_source_for_ui():
        payload = {}
        payload.update(read_managed_prefs_dict())

        legacy = defaults_export_domain_dict()
        if isinstance(legacy, dict):
            for key in managed_keys:
                if key in legacy and key not in payload:
                    payload[key] = legacy[key]

        payload, _ = sanitize_managed_payload(payload)
        return payload

    def pgrep_any(pattern):
        res = run_cmd(["pgrep", "-if", pattern])
        return bool(res.stdout.strip())

    def kill_brave_family(progress=None):
        patterns = [
            "Brave Browser",
            "Brave Browser Helper",
            "Brave Crashpad",
        ]

        try:
            run_cmd(["osascript", "-e", 'tell application "Brave Browser" to quit'])
        except Exception:
            pass
        time.sleep(2.0)

        for pat in patterns:
            run_cmd(["pkill", "-TERM", "-if", pat])
        time.sleep(2.0)

        if pgrep_any("Brave"):
            for pat in patterns:
                run_cmd(["pkill", "-KILL", "-if", pat])
            time.sleep(1.5)

        still_running = pgrep_any("Brave")
        if progress:
            progress.log("Brave running after stop attempt: yes" if still_running else "Brave fully stopped.")
        return not still_running

    def flush_pref_cache():
        run_cmd(["killall", "cfprefsd"])
        time.sleep(0.8)

    def clear_brave_runtime_caches():
        paths = [
            BRAVE_CACHE_DIR,
            os.path.join(BRAVE_DEFAULT_PROFILE_DIR, "Cache"),
            os.path.join(BRAVE_DEFAULT_PROFILE_DIR, "Code Cache"),
            os.path.join(BRAVE_DEFAULT_PROFILE_DIR, "GPUCache"),
            os.path.join(BRAVE_DEFAULT_PROFILE_DIR, "DawnCache"),
            os.path.join(BRAVE_DEFAULT_PROFILE_DIR, "GrShaderCache"),
            os.path.join(BRAVE_DEFAULT_PROFILE_DIR, "ShaderCache"),
            os.path.join(BRAVE_DEFAULT_PROFILE_DIR, "Service Worker", "CacheStorage"),
            os.path.join(BRAVE_DEFAULT_PROFILE_DIR, "Service Worker", "ScriptCache"),
            os.path.join(BRAVE_USER_DATA_DIR, "Crashpad", "completed"),
            os.path.join(BRAVE_USER_DATA_DIR, "Crashpad", "reports"),
            os.path.join(BRAVE_USER_DATA_DIR, "SingletonLock"),
            os.path.join(BRAVE_USER_DATA_DIR, "SingletonCookie"),
            os.path.join(BRAVE_USER_DATA_DIR, "SingletonSocket"),
        ]

        removed = []
        for path in paths:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path, ignore_errors=True)
                removed.append(path)
            elif os.path.exists(path):
                try:
                    os.remove(path)
                    removed.append(path)
                except Exception:
                    pass
        return removed

    def quarantine_brave_user_data():
        if not os.path.exists(BRAVE_USER_DATA_DIR):
            os.makedirs(BRAVE_USER_DATA_DIR, exist_ok=True)
            return None

        backup_path = BRAVE_USER_DATA_DIR + f".SlimBraveQuarantine-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        shutil.move(BRAVE_USER_DATA_DIR, backup_path)
        os.makedirs(BRAVE_USER_DATA_DIR, exist_ok=True)
        return backup_path

    def diagnose_policy_sources():
        lines = []
        user_payload = {}
        system_payload = {}
        legacy_payload = {}

        if os.path.exists(USER_MANAGED_PREFS_FILE):
            try:
                raw = plist_load_any(USER_MANAGED_PREFS_FILE)
                if isinstance(raw, dict):
                    user_payload = raw
            except Exception as e:
                lines.append(f"User managed prefs read error: {e}")

        if os.path.exists(SYSTEM_MANAGED_PREFS_FILE):
            try:
                raw = plist_load_any(SYSTEM_MANAGED_PREFS_FILE)
                if isinstance(raw, dict):
                    system_payload = raw
            except Exception as e:
                lines.append(f"System managed prefs read error: {e}")

        try:
            legacy_payload = defaults_export_domain_dict()
        except Exception as e:
            lines.append(f"Live domain export error: {e}")

        user_managed_keys = sorted(k for k in user_payload.keys() if k in managed_keys)
        system_managed_keys = sorted(k for k in system_payload.keys() if k in managed_keys)
        legacy_managed_keys = sorted(k for k in legacy_payload.keys() if k in managed_keys) if isinstance(legacy_payload, dict) else []

        lines.append(f"User managed prefs file exists: {'yes' if os.path.exists(USER_MANAGED_PREFS_FILE) else 'no'}")
        lines.append(f"System managed prefs file exists: {'yes' if os.path.exists(SYSTEM_MANAGED_PREFS_FILE) else 'no'}")
        lines.append(f"Managed keys found in user managed prefs: {len(user_managed_keys)}")
        lines.append(f"Managed keys found in system managed prefs: {len(system_managed_keys)}")
        lines.append(f"Legacy managed keys found in live com.brave.Browser domain: {len(legacy_managed_keys)}")

        if legacy_managed_keys:
            lines.append("")
            lines.append("High-risk legacy keys still present in the live Brave domain:")
            lines.extend([f" - {k}" for k in legacy_managed_keys])

        risky_live_permission_keys = [k for k in legacy_managed_keys if k in CONTENT_SETTING_KEYS or k == "PaymentMethodQueryEnabled"]
        if risky_live_permission_keys:
            lines.append("")
            lines.append("Likely crash-risk keys found in live domain (these should not stay there):")
            lines.extend([f" - {k}" for k in risky_live_permission_keys])

        for scope_name, payload in (
            ("user managed prefs", user_payload),
            ("system managed prefs", system_payload),
            ("live domain", legacy_payload if isinstance(legacy_payload, dict) else {}),
        ):
            if "PaymentMethodQueryEnabled" in payload and not isinstance(payload["PaymentMethodQueryEnabled"], bool):
                lines.append(f"Suspicious type in {scope_name}: PaymentMethodQueryEnabled = {type(payload['PaymentMethodQueryEnabled']).__name__}")

        lines.append(f"Local State exists: {'yes' if os.path.exists(BRAVE_LOCAL_STATE_FILE) else 'no'}")
        lines.append(f"Default/Preferences exists: {'yes' if os.path.exists(os.path.join(BRAVE_DEFAULT_PROFILE_DIR, 'Preferences')) else 'no'}")

        return lines

    def ensure_snapshot_exists():
        if os.path.exists(SNAPSHOT_FILE):
            return
        try:
            data = defaults_export_domain_dict()
            plist_dump_xml(SNAPSHOT_FILE, data if isinstance(data, dict) else {})
            write_log(f"Created original Brave domain snapshot at {SNAPSHOT_FILE}")
        except Exception as e:
            write_log(f"Could not create original Brave domain snapshot: {e}")

    def check_and_close_brave():
        if not pgrep_any("Brave"):
            return True

        ok = messagebox.askokcancel(
            "Close Brave Required",
            "Brave is currently running.\n\nSlimBrave must fully close Brave and its helpers before applying, restoring, or repairing settings."
        )
        if not ok:
            set_status("Operation cancelled by user.")
            return False

        progress = ProgressDialog(root, "Closing Brave")
        progress.step(20, "Sending Brave a normal quit request...")
        stopped = kill_brave_family(progress)
        if not stopped:
            progress.finish("Brave could not be fully stopped. Close it manually and retry.")
            messagebox.showerror("Brave Still Running", "SlimBrave could not stop every Brave process. Please close Brave manually and try again.")
            return False

        progress.finish("Brave closed successfully.")
        return True

    def reload_ui_from_registry():
        payload = merged_policy_source_for_ui()
        apply_payload_to_ui(payload)
        if payload:
            set_status("UI reloaded from managed prefs plus any legacy SlimBrave keys still found in the live domain.")
        else:
            set_status("No SlimBrave-managed Brave policy settings found.")

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

    def apply_settings():
        if not check_and_close_brave():
            return

        ensure_snapshot_exists()
        payload = build_managed_payload_from_ui()
        cleaned_payload, warnings = sanitize_managed_payload(payload)

        progress = ProgressDialog(root, "Applying SlimBrave Settings")
        try:
            progress.step(10, "Building managed policy payload from the UI...")
            progress.log(f"Managed keys selected: {len(cleaned_payload)}")

            progress.step(30, "Removing legacy SlimBrave keys from the live Brave domain...")
            removed = strip_legacy_policy_keys_from_live_domain()
            progress.log(f"Legacy keys removed from com.brave.Browser: {len(removed)}")

            progress.step(55, "Writing the managed policy plist only...")
            if cleaned_payload:
                write_user_managed_prefs_dict(cleaned_payload)
                progress.log(f"Wrote {len(cleaned_payload)} managed keys to {USER_MANAGED_PREFS_FILE}")
            else:
                if os.path.exists(USER_MANAGED_PREFS_FILE):
                    os.remove(USER_MANAGED_PREFS_FILE)
                progress.log("No keys selected; removed user managed policy plist if present.")

            progress.step(75, "Flushing macOS preference cache...")
            flush_pref_cache()

            progress.step(90, "Refreshing UI state...")
            save_current_state()
            reload_ui_from_registry()
            set_dirty_state(False)

            if warnings:
                progress.log("")
                progress.log("Sanitizer warnings:")
                for w in warnings:
                    progress.log(f" - {w}")

            progress.finish("Settings applied safely.")
            show_text_report(
                "Apply Diagnostics",
                [
                    "SlimBrave now writes policy to the managed-preferences plist only.",
                    f"Managed plist path: {USER_MANAGED_PREFS_FILE}",
                    f"Managed keys written: {len(cleaned_payload)}",
                    f"Legacy live-domain keys removed: {len(removed)}",
                    "",
                    "Warnings:" if warnings else "Warnings: none",
                    *([f" - {w}" for w in warnings] if warnings else []),
                ],
            )
            set_status("Settings applied safely.")
        except Exception as e:
            write_log(f"Apply failed: {e}")
            progress.finish("Apply failed.")
            messagebox.showerror("Apply Failed", f"An error occurred while applying settings:\n{e}")

    def import_plist():
        f = filedialog.askopenfilename(filetypes=[("Property List / XML", "*.plist *.xml"), ("All files", "*.*")])
        if not f:
            return

        if not check_and_close_brave():
            return

        progress = ProgressDialog(root, "Restoring SlimBrave Plist")
        try:
            progress.step(10, "Reading the selected plist...")
            staged = os.path.join(RESTORE_STAGING_DIR, f"{timestamp_slug()}-{os.path.basename(f)}")
            shutil.copy2(f, staged)
            raw = plist_load_any(staged)

            progress.step(25, "Normalizing the plist payload...")
            payload, container_kind = normalize_restore_root(raw)
            progress.log(f"Detected container type: {container_kind}")

            progress.step(45, "Filtering to SlimBrave-managed keys only...")
            cleaned_payload, warnings = sanitize_managed_payload(payload)
            skipped_count = len(payload.keys()) - len(cleaned_payload.keys()) if isinstance(payload, dict) else 0
            progress.log(f"Managed keys restored from file: {len(cleaned_payload)}")
            progress.log(f"Non-managed or invalid keys skipped: {skipped_count}")

            if not cleaned_payload:
                raise Exception("The selected plist did not contain any valid SlimBrave-managed keys after filtering.")

            progress.step(65, "Stripping old legacy keys from the live Brave domain...")
            removed = strip_legacy_policy_keys_from_live_domain()
            progress.log(f"Legacy live-domain keys removed: {len(removed)}")

            progress.step(80, "Writing the cleaned managed policy plist...")
            write_user_managed_prefs_dict(cleaned_payload)

            progress.step(92, "Flushing caches and refreshing UI...")
            flush_pref_cache()
            clear_brave_runtime_caches()
            reload_ui_from_registry()
            set_dirty_state(False)

            progress.finish("Restore completed safely.")
            report = [
                f"Selected file: {f}",
                f"Staged copy: {staged}",
                f"Detected container type: {container_kind}",
                f"Managed keys restored: {len(cleaned_payload)}",
                f"Legacy live-domain keys removed: {len(removed)}",
                f"Managed prefs target: {USER_MANAGED_PREFS_FILE}",
                "",
                "Restored keys:",
                *[f" - {k}" for k in sorted(cleaned_payload.keys())],
                "",
                "Warnings:" if warnings else "Warnings: none",
                *([f" - {w}" for w in warnings] if warnings else []),
            ]
            show_text_report("Restore Diagnostics", report)
            set_status("Plist restored safely into managed preferences.")
        except Exception as e:
            write_log(f"Plist restore failed: {e}")
            progress.finish("Restore failed.")
            messagebox.showerror(
                "Restore Failed",
                "The selected plist could not be restored safely.\n\n"
                f"{e}\n\n"
                "This restore path only writes SlimBrave-managed keys and will not re-import the whole Brave domain."
            )

    def reset_settings():
        proceed = messagebox.askyesno(
            "Aggressive De-Crash Repair",
            "This repair is aggressive on purpose.\n\n"
            "It will:\n"
            " - fully stop Brave and helper processes\n"
            " - diagnose legacy policy locations\n"
            " - remove user/system managed policy plists\n"
            " - strip old SlimBrave keys from the live com.brave.Browser domain\n"
            " - flush cfprefsd and clear Brave caches\n"
            " - quarantine the ENTIRE Brave user-data folder into a timestamped backup\n"
            " - recreate a fresh Brave profile directory\n\n"
            "This is the closest safe way to de-crash Brave from policy/profile corruption.\n\n"
            "Continue?"
        )
        if not proceed:
            return

        progress = ProgressDialog(root, "Deep Brave Repair")
        try:
            progress.step(5, "Stopping Brave and all helper processes...")
            stopped = kill_brave_family(progress)
            if not stopped:
                raise Exception("Brave could not be stopped completely.")

            progress.step(15, "Diagnosing current policy sources...")
            diagnosis_lines = diagnose_policy_sources()
            for line in diagnosis_lines:
                progress.log(line)

            progress.step(28, "Removing managed policy plist files...")
            removed_files = remove_managed_pref_files()
            if removed_files:
                for p in removed_files:
                    progress.log(f"Removed managed policy file: {p}")
            else:
                progress.log("No managed policy plist files were present.")

            progress.step(42, "Removing legacy SlimBrave keys from the live Brave domain...")
            removed_keys = strip_legacy_policy_keys_from_live_domain()
            progress.log(f"Legacy policy keys removed from com.brave.Browser: {len(removed_keys)}")
            if removed_keys:
                for k in removed_keys:
                    progress.log(f" - {k}")

            progress.step(55, "Flushing macOS preference cache...")
            flush_pref_cache()

            progress.step(68, "Clearing Brave runtime caches...")
            cache_removed = clear_brave_runtime_caches()
            progress.log(f"Runtime cache paths removed: {len(cache_removed)}")

            progress.step(82, "Quarantining the Brave user-data profile...")
            backup_path = quarantine_brave_user_data()
            if backup_path:
                progress.log(f"Quarantined profile backup: {backup_path}")
            else:
                progress.log("No existing Brave user-data directory was present; created a clean one.")

            progress.step(92, "Recreating a clean profile shell and refreshing UI...")
            os.makedirs(BRAVE_USER_DATA_DIR, exist_ok=True)
            reload_ui_from_registry()
            set_dirty_state(False)

            report = [
                "Deep repair completed.",
                "",
                "Diagnosis:",
                *diagnosis_lines,
                "",
                f"Managed policy files removed: {len(removed_files)}",
                f"Legacy live-domain keys removed: {len(removed_keys)}",
                f"Runtime cache paths removed: {len(cache_removed)}",
                f"Quarantined Brave profile backup: {backup_path if backup_path else '(fresh folder created only)'}",
                "",
                "Result:",
                "Brave should now start with a fresh profile and without legacy SlimBrave policy writes in the live com.brave.Browser domain.",
                "If Brave still crashes after this repair, the remaining suspects are the Brave app install itself or a non-SlimBrave external factor.",
            ]

            progress.finish("Deep repair completed.")
            show_text_report("Deep Repair Diagnostics", report)
            messagebox.showinfo(
                "Repair Finished",
                "Deep repair completed.\n\n"
                "Brave's old profile was quarantined and a fresh profile area was created.\n"
                "Open Brave and test search plus Site Settings again."
            )
            set_status("Deep repair completed.")
        except Exception as e:
            write_log(f"Deep repair failed: {e}")
            progress.finish("Deep repair failed.")
            messagebox.showerror("Repair Failed", f"The deep repair failed:\n{e}")

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

    btn_priv = ttk.Button(inner_top, text="High Privacy + Moderate Security", style="Orange.TButton", command=lambda: apply_preset("privacy"))
    btn_priv.pack(side="left", padx=10)
    create_tooltip(btn_priv, "Applies the recommended preset for High Privacy and Moderate Security.")

    btn_sec = ttk.Button(inner_top, text="High Security + Moderate Privacy", style="Orange.TButton", command=lambda: apply_preset("security"))
    btn_sec.pack(side="left", padx=10)
    create_tooltip(btn_sec, "Applies the recommended preset for High Security and Moderate Privacy.")

    save_status_label = tk.Label(inner_top, textvariable=save_status_var, bg="#191919", fg="#90EE90", font=("sans-serif", 10, "bold"))
    save_status_label.pack(side="right", padx=(50, 0))

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

    status_label = tk.Label(bottom_bar, textvariable=status_var, bg="#2d2d2d", fg="#aaaaaa", font=("courier", 10), anchor="w", padx=10)
    status_label.pack(side="bottom", fill="x")

    root.after(100, reload_ui_from_registry)
    root.mainloop()


if __name__ == "__main__":
    dependency_setup()
    main()
