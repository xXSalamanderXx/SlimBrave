#!/usr/bin/env python3
# SlimBrave - Revived - v1.1.0 (macOS)

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
    print("Homebrew is required if SlimBrave needs to install a modern Python/Tk environment.")
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
    import uuid

    CONFIG_DIR = os.path.expanduser("~/.config/slimbrave")
    STATE_FILE = os.path.join(CONFIG_DIR, "SlimBraveState.json")
    LOG_FILE = os.path.join(CONFIG_DIR, "SlimBrave.log")
    USER_MANAGED_PREFS_DIR = os.path.expanduser("~/Library/Managed Preferences")

    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(USER_MANAGED_PREFS_DIR, exist_ok=True)

    # Dynamic Channel Variables
    DOMAIN = ""
    USER_MANAGED_PREFS_FILE = ""
    SYSTEM_MANAGED_PREFS_FILE = ""
    BRAVE_SUPPORT_DIR = ""
    BRAVE_USER_DATA_DIR = ""
    BRAVE_DEFAULT_PROFILE_DIR = ""
    BRAVE_LOCAL_STATE_FILE = ""
    BRAVE_CACHE_DIR = ""
    current_channel_info = {}

    def update_paths_for_channel(channel_info):
        nonlocal DOMAIN, USER_MANAGED_PREFS_FILE, SYSTEM_MANAGED_PREFS_FILE
        nonlocal BRAVE_SUPPORT_DIR, BRAVE_USER_DATA_DIR, BRAVE_DEFAULT_PROFILE_DIR
        nonlocal BRAVE_LOCAL_STATE_FILE, BRAVE_CACHE_DIR

        DOMAIN = channel_info["Domain"]
        USER_MANAGED_PREFS_FILE = os.path.join(USER_MANAGED_PREFS_DIR, f"{DOMAIN}.plist")
        SYSTEM_MANAGED_PREFS_FILE = os.path.join("/Library/Managed Preferences", f"{DOMAIN}.plist")

        BRAVE_SUPPORT_DIR = os.path.expanduser(f"~/Library/Application Support/BraveSoftware/{channel_info['Dir']}")
        BRAVE_USER_DATA_DIR = BRAVE_SUPPORT_DIR
        BRAVE_DEFAULT_PROFILE_DIR = os.path.join(BRAVE_USER_DATA_DIR, "Default")
        BRAVE_LOCAL_STATE_FILE = os.path.join(BRAVE_USER_DATA_DIR, "Local State")
        BRAVE_CACHE_DIR = os.path.expanduser(f"~/Library/Caches/BraveSoftware/{channel_info['Dir']}")

    def write_log(message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} - {message}\n")

    def timestamp_slug():
        return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    write_log("SlimBrave UI started.")

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
        {"Name": "Enable Global Privacy Control", "Key": "GlobalPrivacyControlEnabled", "Value": True, "Type": "bool", "ToolTip": "Enables GPC to tell sites not to sell or share your data.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Enable De-AMP", "Key": "BraveDeAMPEnabled", "Value": True, "Type": "bool", "ToolTip": "Bypasses Google AMP pages and redirects you to the original website.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Enable Debouncing", "Key": "BraveDebouncingEnabled", "Value": True, "Type": "bool", "ToolTip": "Skips known tracking redirect hops before you reach your destination.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Strip URL Trackers", "Key": "BraveTrackersStrippingEnabled", "Value": True, "Type": "bool", "ToolTip": "Automatically removes tracking parameters from URLs.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Reduce Language Fingerprinting", "Key": "ReduceAcceptLanguage", "Value": True, "Type": "bool", "ToolTip": "Reduces the language data sent to sites to prevent fingerprinting.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
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
        {"Name": "Disable Brave Rewards", "Key": "BraveRewardsDisabled", "Value": True, "Type": "bool", "ToolTip": "Completely disables the Brave Crypto Rewards system.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
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
    managed_keys.update({"DefaultFileSystemWriteGuardSetting", "SafeBrowsingProtectionLevel", "DnsOverHttpsMode", "DnsOverHttpsTemplates"})

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
                padx=12,
                pady=8,
                wraplength=400,
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
        "Preset.TButton": "#E65100",
        "Export.TButton": "#0D47A1",
        "Import.TButton": "#1976D2",
        "Reload.TButton": "#F57F17",
        "Apply.TButton": "#2E7D32",
        "Reset.TButton": "#C62828"
    }
    active_styles = {
        "Preset.TButton": "#BF360C",
        "Export.TButton": "#0A3D91",
        "Import.TButton": "#1565C0",
        "Reload.TButton": "#E65100",
        "Apply.TButton": "#1B5E20",
        "Reset.TButton": "#B71C1C"
    }

    for sty, color in button_styles.items():
        style.configure(
            sty,
            background=color,
            foreground="white",
            font=("sans-serif", 9 if sty != "Preset.TButton" else 10, "bold"),
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
    
    global HAS_PROMPTED_CLEANUP
    HAS_PROMPTED_CLEANUP = False

    status_var = tk.StringVar(value="Ready.")
    save_status_var = tk.StringVar(value="Unmanaged ❌")

    # Determine installed channels
    channels_dict = {
        "Release": {"Domain": "com.brave.Browser", "App": "Brave Browser", "Dir": "Brave-Browser"},
        "Beta": {"Domain": "com.brave.Browser.beta", "App": "Brave Browser Beta", "Dir": "Brave-Browser-Beta"},
        "Dev": {"Domain": "com.brave.Browser.dev", "App": "Brave Browser Dev", "Dir": "Brave-Browser-Dev"},
        "Nightly": {"Domain": "com.brave.Browser.nightly", "App": "Brave Browser Nightly", "Dir": "Brave-Browser-Nightly"}
    }
    installed_channels = {}
    for name, info in channels_dict.items():
        if os.path.exists(f"/Applications/{info['App']}.app") or os.path.exists(os.path.expanduser(f"~/Applications/{info['App']}.app")):
            installed_channels[name] = info
    
    if not installed_channels:
        installed_channels["Release"] = channels_dict["Release"]

    current_channel_info = list(installed_channels.values())[0]
    update_paths_for_channel(current_channel_info)

    def is_profile_installed():
        try:
            profile_id = f"com.slimbrave.profile.{DOMAIN}"
            
            res1 = subprocess.run(["profiles", "list"], capture_output=True, text=True)
            if profile_id in res1.stdout or "SlimBrave Policy" in res1.stdout:
                return True
                
            res2 = subprocess.run(["profiles", "list", "-output", "stdout-xml", "-type", "configuration"], capture_output=True, text=True)
            if profile_id in res2.stdout or "SlimBrave Policy" in res2.stdout:
                return True
                
            res3 = subprocess.run(["system_profiler", "SPConfigurationProfileDataType"], capture_output=True, text=True)
            if profile_id in res3.stdout or "SlimBrave Policy" in res3.stdout:
                return True
                
            return False
        except Exception:
            return False

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
            save_status_var.set("UnSaved ⚠️")
            save_status_label.config(fg="#FFD700")
        else:
            if is_profile_installed():
                save_status_var.set("Profile Active ✅")
                save_status_label.config(fg="#90EE90")
            else:
                save_status_var.set("Unmanaged ❌")
                save_status_label.config(fg="#aaaaaa")

    def get_ui_snapshot():
        return {
            "Features": [key for key, var in all_feature_vars.items() if var.get() == 1],
            "Permissions": {key: var.get() for key, var in all_perm_vars.items() if var.get() != "Not Set"},
            "SafeBrowsing": sb_var.get(),
            "DnsMode": dns_var.get(),
            "DnsTemplate": dns_tpl_var.get()
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
            write_log(f"State Saved \u2705 to {STATE_FILE}")
        except Exception as e:
            write_log(f"State save failed: {e}")

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
        def __init__(self, parent, title="Working"):
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

            self.close_btn = tk.Button(btns, text="OK", state="disabled", command=self.top.destroy, width=10)
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

        tk.Button(outer, text="OK", command=win.destroy, width=10).pack(side="right", pady=(10, 0))
        win.update_idletasks()

    def choose_reset_mode():
        result = {"value": None}

        win = tk.Toplevel(root)
        win.title("Reset")
        win.transient(root)
        win.grab_set()
        win.configure(bg="#1f1f1f")
        win.geometry("520x280")
        win.minsize(480, 260)
        win.iconphoto(False, icon_img)

        outer = tk.Frame(win, bg="#1f1f1f")
        outer.pack(fill="both", expand=True, padx=18, pady=16)

        tk.Label(outer, text="Choose reset mode", bg="#1f1f1f", fg="#87CEFA", font=("sans-serif", 13, "bold")).pack(anchor="w", pady=(0, 10))

        msg = (
            "Light Reset\n"
            "Removes SlimBrave settings and clears Brave runtime caches.\n"
            "Keeps your current Brave profile.\n\n"
            "Hard Reset\n"
            "DESTRUCTIVE: Moves your current Brave profile to a backup folder\n"
            "and forces Brave to create a fresh profile on next launch."
        )
        tk.Label(outer, text=msg, bg="#1f1f1f", fg="white", justify="left", anchor="w", font=("sans-serif", 10)).pack(fill="x", pady=(0, 18))

        btns = tk.Frame(outer, bg="#1f1f1f")
        btns.pack(side="bottom", fill="x")

        def pick(value):
            result["value"] = value
            win.destroy()

        tk.Button(btns, text="Light Reset", command=lambda: pick("light"), width=12).pack(side="left")
        tk.Button(btns, text="Hard Reset", command=lambda: pick("hard"), width=12).pack(side="left", padx=8)
        tk.Button(btns, text="Cancel", command=lambda: pick(None), width=10).pack(side="right")

        win.protocol("WM_DELETE_WINDOW", lambda: pick(None))
        win.wait_window()
        return result["value"]

    def plist_load_any(path):
        with open(path, "rb") as f:
            return plistlib.load(f)

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
                    warnings.append(f"Skipped {key}: expected bool")
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
                    warnings.append(f"Skipped {key}: expected array")
                continue

            if key in INT_POLICY_KEYS:
                try:
                    cleaned[key] = int(value)
                except Exception:
                    warnings.append(f"Skipped {key}: expected int")
                continue

            if key in CONTENT_SETTING_KEYS:
                try:
                    iv = int(value)
                    if iv in (1, 2, 3):
                        cleaned[key] = iv
                    else:
                        warnings.append(f"Skipped {key}: invalid value {iv}")
                except Exception:
                    warnings.append(f"Skipped {key}: invalid value")
                continue

            if key == "PaymentMethodQueryEnabled":
                b = coerce_bool(value)
                if b is None:
                    try:
                        b = bool(int(value))
                    except Exception:
                        b = None
                if b is None:
                    warnings.append(f"Skipped {key}: invalid value")
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
                    warnings.append(f"Skipped {key}: invalid value")
                continue

            if key == "DnsOverHttpsMode":
                s = str(value).strip().lower()
                if s in {"automatic", "off", "secure"}:
                    cleaned[key] = s
                else:
                    warnings.append(f"Skipped {key}: invalid value")
                continue
            
            if key == "DnsOverHttpsTemplates":
                cleaned[key] = str(value)
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

    def write_mobileconfig(payload):
        PROFILE_IDENTIFIER = f"com.slimbrave.profile.{DOMAIN}"
        profile_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, PROFILE_IDENTIFIER)).upper()
        payload_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{PROFILE_IDENTIFIER}.payload")).upper()
        
        mobileconfig = {
            "PayloadContent": [
                {
                    "PayloadType": "com.apple.ManagedClient.preferences",
                    "PayloadVersion": 1,
                    "PayloadIdentifier": f"{PROFILE_IDENTIFIER}.payload",
                    "PayloadUUID": payload_uuid,
                    "PayloadEnabled": True,
                    "PayloadContent": {
                        DOMAIN: {
                            "Forced": [
                                {
                                    "mcx_preference_settings": payload
                                }
                            ]
                        }
                    }
                }
            ],
            "PayloadDisplayName": f"SlimBrave Policy ({DOMAIN})",
            "PayloadIdentifier": PROFILE_IDENTIFIER,
            "PayloadType": "Configuration",
            "PayloadUUID": profile_uuid,
            "PayloadVersion": 1,
            "PayloadScope": "System"
        }
        
        config_path = os.path.expanduser(f"~/Desktop/SlimBrave-{DOMAIN}.mobileconfig")
        with open(config_path, "wb") as f:
            plistlib.dump(mobileconfig, f, fmt=plistlib.FMT_XML)
            
        write_log(f"Wrote Configuration Profile: {config_path}")
        return config_path

    def remove_mobileconfig_profile():
        try:
            profile_identifier = f"com.slimbrave.profile.{DOMAIN}"
            res = run_cmd(["profiles", "remove", "-identifier", profile_identifier, "-forced"])
            return res.returncode == 0
        except Exception:
            return False

    def remove_managed_pref_files():
        removed = []
        for path in (USER_MANAGED_PREFS_FILE, SYSTEM_MANAGED_PREFS_FILE):
            if os.path.exists(path):
                try:
                    os.remove(path)
                    removed.append(path)
                    write_log(f"Removed managed prefs file: {path}")
                except Exception as e:
                    try:
                        res = run_cmd(["osascript", "-e", f'do shell script "rm -f \\"{path}\\"" with administrator privileges'])
                        if not os.path.exists(path):
                            removed.append(path)
                            write_log(f"Removed managed prefs file (via sudo): {path}")
                        else:
                            write_log(f"Failed removing managed prefs file {path}: {e}")
                    except Exception as ex:
                        write_log(f"Failed removing managed prefs file {path}: {ex}")
        return removed

    def strip_legacy_policy_keys_from_live_domain():
        domain_data = defaults_export_domain_dict()
        if not isinstance(domain_data, dict) or not domain_data:
            return []

        removed = []
        for key in list(domain_data.keys()):
            if key in managed_keys:
                removed.append(key)
                domain_data.pop(key, None)

        actual_removed = []
        if removed:
            for r_key in removed:
                res = run_cmd(["defaults", "delete", DOMAIN, r_key])
                if res.returncode == 0:
                    actual_removed.append(r_key)

        return sorted(actual_removed)

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

        dns_mode = dns_var.get()
        if dns_mode == "Automatic":
            payload["DnsOverHttpsMode"] = "automatic"
        elif dns_mode == "Off":
            payload["DnsOverHttpsMode"] = "off"
        elif dns_mode == "Secure":
            payload["DnsOverHttpsMode"] = "secure"
        elif dns_mode == "Custom":
            payload["DnsOverHttpsMode"] = "secure"

        tpl = dns_tpl_var.get().strip()
        if tpl and dns_mode in ["Secure", "Custom"]:
            payload["DnsOverHttpsTemplates"] = tpl

        return payload

    def apply_payload_to_ui(payload):
        nonlocal suspend_dirty_tracking
        suspend_dirty_tracking = True

        for var in all_feature_vars.values():
            var.set(0)
        for var in all_perm_vars.values():
            var.set("Not Set")
        sb_var.set("")
        dns_var.set("Automatic")
        dns_tpl_var.set("")

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
                dns_var.set("Automatic")
            elif d == "off":
                dns_var.set("Off")
            elif d == "secure":
                if payload.get("DnsOverHttpsTemplates"):
                    dns_var.set("Custom")
                else:
                    dns_var.set("Secure")

        if "DnsOverHttpsTemplates" in payload:
            dns_tpl_var.set(str(payload["DnsOverHttpsTemplates"]))

        suspend_dirty_tracking = False
        update_baseline()
        check_dirty_state()
        
    def apply_json_state_to_ui(data):
        nonlocal suspend_dirty_tracking
        suspend_dirty_tracking = True

        for var in all_feature_vars.values():
            var.set(0)
        for var in all_perm_vars.values():
            var.set("Not Set")
        sb_var.set("")
        dns_var.set("Automatic")
        dns_tpl_var.set("")

        for key in data.get("Features", []):
            if key in all_feature_vars:
                all_feature_vars[key].set(1)

        for key, val in data.get("Permissions", {}).items():
            if key in all_perm_vars:
                all_perm_vars[key].set(val)

        if "SafeBrowsing" in data:
            sb_var.set(data["SafeBrowsing"])
        if "DnsMode" in data:
            dns_var.set(data["DnsMode"])
        if "DnsTemplate" in data:
            dns_tpl_var.set(data["DnsTemplate"])

        suspend_dirty_tracking = False
        update_baseline()
        check_dirty_state()

    def prompt_legacy_cleanup():
        ans = messagebox.askyesno(
            "Legacy Configurations Detected",
            "SlimBrave detected old legacy plist configurations on your system.\n\n"
            "Because you are now utilizing the modern Configuration Profile standard, these old files can cause conflicts and prevent Brave from applying your policies properly.\n\n"
            "Would you like SlimBrave to safely clean up these deprecated files now?"
        )
        if ans:
            removed_files = remove_managed_pref_files()
            removed_keys = strip_legacy_policy_keys_from_live_domain()
            flush_pref_cache()
            
            msg = "Cleanup successful!\n\n"
            if removed_files:
                msg += f"Policy files removed: {len(removed_files)}\n"
            if removed_keys:
                msg += f"Live keys removed: {len(removed_keys)}\n"
            if not removed_files and not removed_keys:
                msg += "No conflicting files were actually found during the sweep."
                
            messagebox.showinfo("Cleanup Complete", msg.strip())
            reload_ui_from_registry()

    def reload_ui_from_registry():
        global HAS_PROMPTED_CLEANUP
        
        profile_active = is_profile_installed()
        
        legacy_files = [p for p in (USER_MANAGED_PREFS_FILE, SYSTEM_MANAGED_PREFS_FILE) if os.path.exists(p)]
        has_legacy = bool(legacy_files)
        
        if profile_active:
            if has_legacy:
                status = "Settings loaded. (Profile Active, Legacy Plists Found ⚠️)"
            else:
                status = "Settings loaded. (Profile Installed ✅)"
        elif has_legacy:
            status = "Settings loaded. (Legacy Plist Mode ⚠️)"
        else:
            status = "No SlimBrave policies active."

        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                apply_json_state_to_ui(data)
                
                if not data.get("Features") and not data.get("Permissions"):
                    if not profile_active and not has_legacy:
                        status = "Ready."
            except Exception as e:
                write_log(f"Failed to read local state JSON: {e}")
                apply_payload_to_ui({})
        elif has_legacy:
            payload = merged_policy_source_for_ui()
            apply_payload_to_ui(payload)
        else:
            apply_payload_to_ui({})
            if not profile_active:
                status = "Ready."

        set_status(status)

        if profile_active and has_legacy and not HAS_PROMPTED_CLEANUP:
            HAS_PROMPTED_CLEANUP = True
            root.after(500, prompt_legacy_cleanup)

    def pgrep_any(pattern):
        res = run_cmd(["pgrep", "-if", pattern])
        return bool(res.stdout.strip())

    def kill_brave_family(progress=None):
        nonlocal current_channel_info
        app_name = current_channel_info["App"]
        patterns = [
            app_name,
            f"{app_name} Helper",
            "Brave Crashpad",
        ]

        try:
            run_cmd(["osascript", "-e", f'tell application "{app_name}" to quit'])
        except Exception:
            pass
        time.sleep(2.0)

        for pat in patterns:
            run_cmd(["pkill", "-TERM", "-if", pat])
        time.sleep(2.0)

        if pgrep_any(app_name):
            for pat in patterns:
                run_cmd(["pkill", "-KILL", "-if", pat])
            time.sleep(1.5)

        still_running = pgrep_any(app_name)
        if progress:
            progress.log(f"{app_name} is still running." if still_running else f"{app_name} is closed.")
        return not still_running

    def flush_pref_cache():
        time.sleep(0.5)

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
                lines.append(f"User policy file read error: {e}")

        if os.path.exists(SYSTEM_MANAGED_PREFS_FILE):
            try:
                raw = plist_load_any(SYSTEM_MANAGED_PREFS_FILE)
                if isinstance(raw, dict):
                    system_payload = raw
            except Exception as e:
                lines.append(f"System policy file read error: {e}")

        try:
            legacy_payload = defaults_export_domain_dict()
        except Exception as e:
            lines.append(f"Live domain read error: {e}")

        user_managed_keys = sorted(k for k in user_payload.keys() if k in managed_keys)
        system_managed_keys = sorted(k for k in system_payload.keys() if k in managed_keys)
        legacy_managed_keys = sorted(k for k in legacy_payload.keys() if k in managed_keys) if isinstance(legacy_payload, dict) else []

        lines.append(f"User policy file: {'found' if os.path.exists(USER_MANAGED_PREFS_FILE) else 'not found'}")
        lines.append(f"System policy file: {'found' if os.path.exists(SYSTEM_MANAGED_PREFS_FILE) else 'not found'}")
        lines.append(f"User policy keys: {len(user_managed_keys)}")
        lines.append(f"System policy keys: {len(system_managed_keys)}")
        lines.append(f"Legacy live-domain keys: {len(legacy_managed_keys)}")

        risky_live_permission_keys = [k for k in legacy_managed_keys if k in CONTENT_SETTING_KEYS or k == "PaymentMethodQueryEnabled"]
        if risky_live_permission_keys:
            lines.append("")
            lines.append("Legacy keys found in live domain:")
            lines.extend([f" - {k}" for k in risky_live_permission_keys])

        for scope_name, payload in (
            ("user policy file", user_payload),
            ("system policy file", system_payload),
            ("live domain", legacy_payload if isinstance(legacy_payload, dict) else {}),
        ):
            if "PaymentMethodQueryEnabled" in payload and not isinstance(payload["PaymentMethodQueryEnabled"], bool):
                lines.append(f"Suspicious type in {scope_name}: PaymentMethodQueryEnabled")

        lines.append(f"Local State: {'found' if os.path.exists(BRAVE_LOCAL_STATE_FILE) else 'not found'}")
        lines.append(f"Default/Preferences: {'found' if os.path.exists(os.path.join(BRAVE_DEFAULT_PROFILE_DIR, 'Preferences')) else 'not found'}")

        return lines

    def check_and_close_brave():
        nonlocal current_channel_info
        app_name = current_channel_info["App"]
        if not pgrep_any(app_name):
            return True

        ok = messagebox.askokcancel(
            f"Close {app_name}",
            f"{app_name} is open.\n\nClose it now to continue?"
        )
        if not ok:
            set_status("Cancelled.")
            return False

        progress = ProgressDialog(root, f"Closing {app_name}")
        progress.step(20, f"Closing {app_name}...")
        stopped = kill_brave_family(progress)
        if not stopped:
            progress.finish(f"{app_name} is still open.")
            messagebox.showerror("Brave", f"Could not close {app_name}.\n\nPlease close it and try again.")
            return False

        progress.finish(f"{app_name} is closed.")
        return True

    def confirm_hard_reset():
        return messagebox.askyesno(
            "Confirm Hard Reset",
            "Hard Reset is destructive.\n\n"
            "It will move your current Brave profile to a backup folder and Brave will start with a fresh profile on next launch.\n\n"
            "You may lose signed-in sessions, extension state, local settings, and site data in the active profile.\n\n"
            "Continue?"
        )

    def export_settings():
        f = filedialog.asksaveasfilename(defaultextension=".json", initialfile="SlimBraveSettings.json")
        if not f:
            return
        with open(f, "w", encoding="utf-8") as file:
            json.dump(get_ui_snapshot(), file, indent=4)
        set_status("Settings exported.")

    def import_settings():
        f = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not f:
            return

        with open(f, "r", encoding="utf-8") as file:
            data = json.load(file)

        apply_json_state_to_ui(data)
        set_status("JSON loaded.")

    def apply_settings():
        if not check_and_close_brave():
            return

        payload = build_managed_payload_from_ui()
        cleaned_payload, warnings = sanitize_managed_payload(payload)

        progress = ProgressDialog(root, "Apply")
        profile_was_installed = False
        profile_removed = False

        try:
            progress.step(10, "Preparing settings...")
            progress.log(f"Keys selected: {len(cleaned_payload)}")

            progress.step(55, "Generating Configuration Profile...")
            if cleaned_payload:
                config_path = write_mobileconfig(cleaned_payload)
                progress.log(f"Wrote: {config_path}")
                run_cmd(["open", config_path])
            else:
                profile_was_installed = is_profile_installed()
                if profile_was_installed:
                    if remove_mobileconfig_profile():
                        progress.log("Configuration Profile natively removed via CLI.")
                        profile_removed = True
                    else:
                        progress.log("Configuration Profile requires manual removal via System Settings.")
                progress.log("No policies selected. Profile cleared.")

            progress.step(75, "Refreshing macOS cache...")
            flush_pref_cache()

            progress.step(90, "Refreshing app...")
            save_current_state()
            reload_ui_from_registry()
            set_dirty_state(False)

            if warnings:
                progress.log("")
                progress.log("Warnings:")
                for w in warnings:
                    progress.log(f" - {w}")

            progress.finish("SlimBrave Profile Generated!")
            
            if cleaned_payload:
                messagebox.showinfo(
                    "Action Required", 
                    "A .mobileconfig file has been saved to your Desktop and opened.\n\n"
                    "To finish applying or updating the policies:\n"
                    "1. A 'Profile Downloaded' notification will appear on your Mac.\n"
                    "2. Open System Settings.\n"
                    "3. Navigate to 'Privacy & Security' -> 'Profiles' (or 'General' -> 'Device Management').\n"
                    "4. Double-click 'SlimBrave Policy'.\n"
                    "   • If installing for the first time, click 'Install'.\n"
                    "   • If updating settings, macOS will ask to replace the old profile. Click 'Replace' or 'Update'.\n\n"
                    "5. Once complete, you can safely delete the .mobileconfig file from your Desktop.\n\n"
                    "6. Finally, click the 'Reload' button in SlimBrave to verify the profile is active!"
                )
            else:
                if profile_was_installed and not profile_removed:
                    messagebox.showwarning(
                        "Manual Removal Required",
                        "SlimBrave settings cleared locally, but macOS blocked automatic removal of the active Configuration Profile.\n\n"
                        "You must manually delete it by going to macOS System Settings -> Privacy & Security -> Profiles, selecting 'SlimBrave Policy', and clicking the '-' button."
                    )
                else:
                    messagebox.showinfo("Apply", "SlimBrave settings cleared successfully!")

            set_status("SlimBrave Application Complete!")
        except Exception as e:
            write_log(f"Apply failed: {e}")
            progress.finish("Something Went Wrong, Please Read Logs for More Details")
            set_status("Something Went Wrong, Please Read Logs for More Details")
            messagebox.showerror("Apply", "Something Went Wrong, Please Read Logs for More Details.\n\n" + str(e))

    def do_light_reset():
        progress = ProgressDialog(root, "Light Reset")
        try:
            progress.step(5, "Closing Brave...")
            stopped = kill_brave_family(progress)
            if not stopped:
                raise Exception("Brave could not be closed.")

            progress.step(20, "Checking current settings...")
            diagnosis_lines = diagnose_policy_sources()
            for line in diagnosis_lines:
                progress.log(line)

            progress.step(40, "Removing old legacy policy files...")
            removed_files = remove_managed_pref_files()
            if removed_files:
                for p in removed_files:
                    progress.log(f"Removed: {p}")
            else:
                progress.log("No legacy policy files found.")
                
            progress.step(42, "Removing Configuration Profile (if installed)...")
            profile_installed_initially = is_profile_installed()
            if profile_installed_initially:
                profile_removed = remove_mobileconfig_profile()
                if profile_removed:
                    progress.log("Configuration Profile natively removed via CLI.")
                else:
                    progress.log("Configuration Profile requires manual removal via System Settings.")
            else:
                progress.log("No Configuration Profile detected.")
                profile_removed = True

            progress.step(60, "Removing old live-domain keys...")
            removed_keys = strip_legacy_policy_keys_from_live_domain()
            progress.log(f"Removed keys: {len(removed_keys)}")
            for k in removed_keys:
                progress.log(f" - {k}")

            progress.step(75, "Refreshing macOS cache...")
            flush_pref_cache()

            progress.step(88, "Clearing Brave caches...")
            cache_removed = clear_brave_runtime_caches()
            progress.log(f"Cache paths cleared: {len(cache_removed)}")
            flush_pref_cache()
            progress.log("macOS preference cache refreshed again.")

            progress.step(96, "Refreshing app...")
            apply_payload_to_ui({})
            save_current_state()
            reload_ui_from_registry()
            set_dirty_state(False)

            report = [
                "Light Reset finished.",
                "",
                "Checks:",
                *diagnosis_lines,
                "",
                f"Legacy files removed: {len(removed_files)}",
                f"Profile CLI removal: {'Success / Not Required' if profile_removed else 'Manual removal required'}",
                f"Old live-domain keys removed: {len(removed_keys)}",
                f"Cache paths cleared: {len(cache_removed)}",
                "",
                "Your Brave profile was kept."
            ]

            progress.finish("Done.")
            show_text_report("Light Reset Summary", report)
            
            if not profile_removed:
                messagebox.showwarning("Manual Removal Required", "Light Reset finished, but Apple blocked the automatic removal of your SlimBrave Configuration Profile.\n\nYou must manually delete it by going to macOS System Settings -> Privacy & Security -> Profiles.")
            else:
                messagebox.showinfo("Light Reset", "Light Reset finished successfully.")
                
            set_status("Light Reset finished.")
        except Exception as e:
            write_log(f"Light reset failed: {e}")
            progress.finish("Failed.")
            messagebox.showerror("Light Reset", f"Light Reset failed.\n\n{e}")

    def do_hard_reset():
        if not confirm_hard_reset():
            set_status("Hard Reset cancelled.")
            return

        progress = ProgressDialog(root, "Hard Reset")
        try:
            progress.step(5, "Closing Brave...")
            stopped = kill_brave_family(progress)
            if not stopped:
                raise Exception("Brave could not be closed.")

            progress.step(15, "Checking current settings...")
            diagnosis_lines = diagnose_policy_sources()
            for line in diagnosis_lines:
                progress.log(line)

            progress.step(30, "Removing old legacy policy files...")
            removed_files = remove_managed_pref_files()
            if removed_files:
                for p in removed_files:
                    progress.log(f"Removed: {p}")
            else:
                progress.log("No legacy policy files found.")
                
            progress.step(42, "Removing Configuration Profile (if installed)...")
            profile_installed_initially = is_profile_installed()
            if profile_installed_initially:
                profile_removed = remove_mobileconfig_profile()
                if profile_removed:
                    progress.log("Configuration Profile natively removed via CLI.")
                else:
                    progress.log("Configuration Profile requires manual removal via System Settings.")
            else:
                progress.log("No Configuration Profile detected.")
                profile_removed = True

            progress.step(45, "Removing old live-domain keys...")
            removed_keys = strip_legacy_policy_keys_from_live_domain()
            progress.log(f"Removed keys: {len(removed_keys)}")
            for k in removed_keys:
                progress.log(f" - {k}")

            progress.step(58, "Refreshing macOS cache...")
            flush_pref_cache()

            progress.step(70, "Clearing Brave caches...")
            cache_removed = clear_brave_runtime_caches()
            progress.log(f"Cache paths cleared: {len(cache_removed)}")
            flush_pref_cache()
            progress.log("macOS preference cache refreshed again.")

            progress.step(84, "Moving Brave profile to backup...")
            backup_path = quarantine_brave_user_data()
            if backup_path:
                progress.log(f"Backup: {backup_path}")
            else:
                progress.log("Created a new Brave data folder.")

            progress.step(95, "Refreshing app...")
            os.makedirs(BRAVE_USER_DATA_DIR, exist_ok=True)
            apply_payload_to_ui({})
            save_current_state()
            reload_ui_from_registry()
            set_dirty_state(False)

            report = [
                "Hard Reset finished.",
                "",
                "Checks:",
                *diagnosis_lines,
                "",
                f"Legacy files removed: {len(removed_files)}",
                f"Profile CLI removal: {'Success / Not Required' if profile_removed else 'Manual removal required'}",
                f"Old live-domain keys removed: {len(removed_keys)}",
                f"Cache paths cleared: {len(cache_removed)}",
                f"Profile backup: {backup_path if backup_path else '(new folder created)'}",
                "",
                "A fresh Brave profile will be created on next launch."
            ]

            progress.finish("Done.")
            show_text_report("Hard Reset Summary", report)
            
            if not profile_removed:
                messagebox.showwarning("Manual Removal Required", "Hard Reset finished, but Apple blocked the automatic removal of your SlimBrave Configuration Profile.\n\nYou must manually delete it by going to macOS System Settings -> Privacy & Security -> Profiles.")
            else:
                messagebox.showinfo("Hard Reset", "Hard Reset finished successfully.")
                
            set_status("Hard Reset finished.")
        except Exception as e:
            write_log(f"Hard reset failed: {e}")
            progress.finish("Failed.")
            messagebox.showerror("Hard Reset", f"Hard Reset failed.\n\n{e}")

    def reset_settings():
        mode = choose_reset_mode()
        if mode == "light":
            do_light_reset()
        elif mode == "hard":
            do_hard_reset()
        else:
            set_status("Reset cancelled.")

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
                "ClearBrowsingDataOnExitList", "HttpsOnlyMode", "GlobalPrivacyControlEnabled",
                "BraveDeAMPEnabled", "BraveDebouncingEnabled", "BraveTrackersStrippingEnabled",
                "ReduceAcceptLanguage", "BraveRewardsDisabled", "BraveWalletDisabled", "BraveVPNDisabled",
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
            dns_tpl_var.set("")
            set_status("Privacy preset loaded.")

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
            dns_var.set("Automatic")
            dns_tpl_var.set("")
            set_status("Security preset loaded.")

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

    tk.Label(inner_top, text="Channel:", font=("sans-serif", 12, "bold"), fg="#87CEFA", bg="#191919").pack(side="left")

    chan_var = tk.StringVar(value=list(installed_channels.keys())[0])
    def on_channel_change(*args):
        nonlocal current_channel_info
        sel = chan_var.get()
        if sel in installed_channels:
            current_channel_info = installed_channels[sel]
            update_paths_for_channel(current_channel_info)
            reload_ui_from_registry()
            
    chan_var.trace_add("write", on_channel_change)
    chan_cb = ttk.Combobox(inner_top, textvariable=chan_var, values=list(installed_channels.keys()), state="readonly", width=10, style="Dark.TCombobox")
    chan_cb.pack(side="left", padx=(5, 20))
    create_tooltip(chan_cb, "Select which installed Brave release channel you would like to manage policies for.\n\nChanging this will load the corresponding settings.")

    tk.Label(inner_top, text="Quick Presets:", font=("sans-serif", 12, "bold"), fg="#87CEFA", bg="#191919").pack(side="left", padx=(0, 10))

    btn_priv = ttk.Button(inner_top, text="Privacy", style="Preset.TButton", command=lambda: apply_preset("privacy"))
    btn_priv.pack(side="left", padx=10)
    create_tooltip(btn_priv, "Applies the recommended preset for High Privacy and Moderate Security.")

    btn_sec = ttk.Button(inner_top, text="Security", style="Preset.TButton", command=lambda: apply_preset("security"))
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
    dns_cb = ttk.Combobox(dns_f, textvariable=dns_var, values=["Automatic", "Off", "Secure", "Custom"], state="readonly", width=10, style="Dark.TCombobox")
    dns_cb.pack(side="left", padx=8)
    dns_tt = "Forces encrypted DNS lookups.\n\nSuggested Settings for Privacy: Off | Security: On"
    create_tooltip(dns_lbl, dns_tt)
    create_tooltip(dns_cb, dns_tt)

    dns_tpl_f = tk.Frame(right_panel, bg="#232323")
    dns_tpl_f.pack(fill="x", padx=16, pady=2)
    dns_tpl_lbl = tk.Label(dns_tpl_f, text="DoH Template:", fg="white", bg="#232323", width=12, anchor="w", font=("sans-serif", 9))
    dns_tpl_lbl.pack(side="left")
    dns_tpl_var = tk.StringVar()
    dns_tpl_var.trace_add("write", check_dirty_state)
    dns_tpl_entry = tk.Entry(dns_tpl_f, textvariable=dns_tpl_var, bg="#161616", fg="white", insertbackground="white", relief="flat")
    dns_tpl_entry.pack(side="left", fill="x", expand=True, padx=8)
    dns_tpl_tt = "Specifies the DoH resolver URL template when 'Custom' or 'Secure' is selected.\n\nSuggested Settings for Privacy: (Blank) | Security: (Blank)"
    create_tooltip(dns_tpl_entry, dns_tpl_tt)

    left_scroll.bind_children()
    mid_scroll.bind_children()
    right_scroll.bind_children()

    bottom_bar = tk.Frame(root, bg="#2d2d2d", height=70)
    bottom_bar.grid(row=1, column=0, sticky="ew")
    bottom_bar.grid_propagate(False)

    btn_frame = tk.Frame(bottom_bar, bg="#2d2d2d")
    btn_frame.pack(side="top", fill="x", pady=5)

    ttk.Button(btn_frame, text="Export JSON", style="Export.TButton", command=export_settings).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Import JSON", style="Import.TButton", command=import_settings).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Reload", style="Reload.TButton", command=reload_ui_from_registry).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Apply", style="Apply.TButton", command=apply_settings).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Reset", style="Reset.TButton", command=reset_settings).pack(side="left", expand=True, padx=5)

    status_label = tk.Label(bottom_bar, textvariable=status_var, bg="#2d2d2d", fg="#aaaaaa", font=("courier", 10), anchor="w", padx=10)
    status_label.pack(side="bottom", fill="x")

    root.after(100, reload_ui_from_registry)
    root.mainloop()

if __name__ == "__main__":
    dependency_setup()
    main()
