#!/usr/bin/env python3
# Slimbrave - Revived - v1.0.9 (macOS Edition) with auto-dependency handling

import subprocess
import sys
import os
import shutil
import time

# ----------------------------------------------------------------------
# 1. Dependency checks and self‑repair (runs before anything else)
# ----------------------------------------------------------------------
BREW_INSTALLED_SOMETHING = False   # tracks if we installed/upgraded via brew

def print_step(msg):
    print(f"\n[SlimBrave] {msg}")

def prompt_yes_no(question):
    while True:
        ans = input(f"{question} [y/n]: ").strip().lower()
        if ans in ('y', 'yes'):
            return True
        if ans in ('n', 'no'):
            return False
        print("Please answer 'y' or 'n'.")

def get_brew_prefix():
    if os.path.exists("/opt/homebrew/bin/brew"):
        return "/opt/homebrew"
    elif os.path.exists("/usr/local/bin/brew"):
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
        else:
            print_step("Homebrew still not available. Exiting.")
            sys.exit(1)
    else:
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
        return   # should not happen

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
            os.environ["SLIMBRAVE_DEPENDENCIES_CHECKED"] = "1"
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
            os.environ["SLIMBRAVE_DEPENDENCIES_CHECKED"] = "1"
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print_step("Cannot run without a working Tk. Exiting.")
            sys.exit(1)

def run_cleanup():
    if shutil.which("brew") and BREW_INSTALLED_SOMETHING:
        print_step("Running brew cleanup…")
        subprocess.run(["brew", "cleanup"], check=False)

def dependency_setup():
    if os.environ.get("SLIMBRAVE_DEPENDENCIES_CHECKED") == "1":
        print_step("Dependencies already checked. Proceeding to GUI…")
        return

    print("=" * 60)
    print(" SlimBrave – Dependency Check")
    print("=" * 60)

    check_homebrew()
    check_python_and_tk()
    run_cleanup()

    os.environ["SLIMBRAVE_DEPENDENCIES_CHECKED"] = "1"
    print_step("All dependencies OK. Launching SlimBrave interface…")
    time.sleep(1)

# ----------------------------------------------------------------------
# 2. The actual SlimBrave application
# ----------------------------------------------------------------------
def main():
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    import json
    import datetime
    import base64

    # --- macOS Configuration & Paths ---
    DOMAIN = "com.brave.Browser"
    CONFIG_DIR = os.path.expanduser("~/.config/slimbrave")
    STATE_FILE = os.path.join(CONFIG_DIR, "SlimBraveState.json")
    LOG_FILE = os.path.join(CONFIG_DIR, "SlimBrave.log")

    os.makedirs(CONFIG_DIR, exist_ok=True)

    def write_log(message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a") as f:
            f.write(f"{timestamp} - {message}\n")

    write_log("SlimBrave macOS UI Initializing...")

    # Create root window FIRST
    root = tk.Tk()
    root.title("SlimBrave - Revived v1.0.9 (macOS)")
    root.geometry("1040x550")
    root.minsize(900, 400)
    root.configure(bg="#191919")

    # Transparent icon (removes Python rocket)
    transparent_gif = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
    icon_img = tk.PhotoImage(master=root, data=base64.b64decode(transparent_gif))
    root.iconphoto(False, icon_img)

    # --- Tooltip with 1-second hover delay, no flicker ---
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
            x, y, cx, cy = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25
            self.tooltip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            label = tk.Label(tw, text=self.text, justify='left',
                             background="#2d2d2d", foreground="white", relief='solid', borderwidth=1,
                             font=("sans-serif", 10, "normal"), padx=8, pady=6, wraplength=400)
            label.pack(ipadx=1)

        def hide(self):
            if self.tooltip_window:
                self.tooltip_window.destroy()
                self.tooltip_window = None

    def create_tooltip(widget, text):
        ToolTip(widget, text)

    # --- Feature Dictionaries (unchanged for brevity) ---
    telemetry_features = [
        {"Name": "Disable Metrics Reporting", "Key": "MetricsReportingEnabled", "Value": 0, "Type": "-int", "ToolTip": "Stops Brave from sending anonymous usage and crash reports.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Safe Browsing Reporting", "Key": "SafeBrowsingExtendedReportingEnabled", "Value": 0, "Type": "-int", "ToolTip": "Stops Brave from sending extended Safe Browsing data back to servers.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable URL Data Collection", "Key": "UrlKeyedAnonymizedDataCollectionEnabled", "Value": 0, "Type": "-int", "ToolTip": "Stops sending anonymized URLs to help improve the browser.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Feedback Surveys", "Key": "FeedbackSurveysEnabled", "Value": 0, "Type": "-int", "ToolTip": "Disables proactive feedback survey prompts.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable P3A Telemetry", "Key": "BraveP3AEnabled", "Value": "Disabled", "Type": "-string", "ToolTip": "Disables Privacy-Preserving Product Analytics completely.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Daily Stats Ping", "Key": "BraveStatsPingEnabled", "Value": 0, "Type": "-int", "ToolTip": "Stops the daily active user ping.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Web Discovery", "Key": "BraveWebDiscoveryEnabled", "Value": 0, "Type": "-int", "ToolTip": "Prevents anonymous search/browsing data from being sent to Brave Search.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"}
    ]

    privacy_features = [
        {"Name": "Disable Autofill (Addresses)", "Key": "AutofillAddressEnabled", "Value": 0, "Type": "-int", "ToolTip": "Disables saving and autofilling addresses.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Autofill (Credit Cards)", "Key": "AutofillCreditCardEnabled", "Value": 0, "Type": "-int", "ToolTip": "Disables saving and autofilling credit cards.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Password Manager", "Key": "PasswordManagerEnabled", "Value": 0, "Type": "-int", "ToolTip": "Disables the built-in password manager.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Browser Sign-in", "Key": "BrowserSignin", "Value": 0, "Type": "-int", "ToolTip": "Prevents syncing your data to cloud accounts.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable WebRTC IP Leak", "Key": "WebRtcIPHandling", "Value": "disable_non_proxied_udp", "Type": "-string", "ToolTip": "Prevents your real IP address from leaking when using a VPN.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable QUIC Protocol", "Key": "QuicAllowed", "Value": 0, "Type": "-int", "ToolTip": "Forces standard TCP, stopping UDP firewall bypasses and tracking.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Block Third Party Cookies", "Key": "BlockThirdPartyCookies", "Value": 1, "Type": "-int", "ToolTip": "Blocks all third-party tracking cookies.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Enable Do Not Track", "Key": "EnableDoNotTrack", "Value": 1, "Type": "-int", "ToolTip": "Sends a Do Not Track request with your browsing traffic.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Force Google SafeSearch", "Key": "ForceGoogleSafeSearch", "Value": 1, "Type": "-int", "ToolTip": "Filters explicit search results.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Disable IPFS", "Key": "IPFSEnabled", "Value": 0, "Type": "-int", "ToolTip": "Stops peer-to-peer background connections to unknown nodes.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Force Incognito Mode", "Key": "IncognitoModeAvailability", "Value": 2, "Type": "-int", "ToolTip": "Forces the browser to always open in Incognito Mode.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Force Download Prompts", "Key": "PromptForDownloadLocation", "Value": 1, "Type": "-int", "ToolTip": "Forces Brave to ask where to save a file before downloading, preventing drive-by downloads.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Clear Data on Exit", "Key": "ClearBrowsingDataOnExitList", "Value": ["browsing_history", "download_history", "cookies_and_other_site_data", "cached_images_and_files", "password_signin", "autofill", "site_settings", "hosted_app_data"], "Type": "-array", "ToolTip": "Wipes all cookies, cache, and browsing history the moment the browser closes.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Force HTTPS-Only Mode", "Key": "HttpsOnlyMode", "Value": "force_enabled", "Type": "-string", "ToolTip": "Strictly upgrades all connections to HTTPS and blocks unencrypted HTTP traffic.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"}
    ]

    brave_features = [
        {"Name": "Disable Rewards and Sponsored Elements", "Key": "BraveRewardsDisabled", "Value": 1, "Type": "-int", "ToolTip": "Completely disables the Brave Crypto Rewards system and disables sponsored backgrounds on the New Tab page.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave Wallet", "Key": "BraveWalletDisabled", "Value": 1, "Type": "-int", "ToolTip": "Disables the built-in Brave Crypto Wallet.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave VPN", "Key": "BraveVPNDisabled", "Value": 1, "Type": "-int", "ToolTip": "Removes the Brave VPN integration and prompts.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave AI Chat", "Key": "BraveAIChatEnabled", "Value": 0, "Type": "-int", "ToolTip": "Disables Brave Leo (AI Chat) integration.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Tor", "Key": "TorDisabled", "Value": 1, "Type": "-int", "ToolTip": "Disables built-in Tor window support.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Sync", "Key": "SyncDisabled", "Value": 1, "Type": "-int", "ToolTip": "Disables Brave Sync functionality across devices.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Disable Brave News", "Key": "BraveNewsDisabled", "Value": 1, "Type": "-int", "ToolTip": "Removes the Brave News feed bloat from the New Tab page.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave Talk", "Key": "BraveTalkDisabled", "Value": "Disabled", "Type": "-string", "ToolTip": "Removes the built-in video calling integration.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Speedreader", "Key": "BraveSpeedreaderEnabled", "Value": 0, "Type": "-int", "ToolTip": "Completely disables the Speedreader feature, reader mode, and automatic prompts.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Wayback Machine Prompts", "Key": "BraveWaybackMachineEnabled", "Value": 0, "Type": "-int", "ToolTip": "Stops Brave from asking to search the Internet Archive when you hit a 404 error.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"}
    ]

    perf_features = [
        {"Name": "Disable Background Mode", "Key": "BackgroundModeEnabled", "Value": 0, "Type": "-int", "ToolTip": "Prevents extensions/apps from running after the browser is closed.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Media Recommendations", "Key": "MediaRecommendationsEnabled", "Value": 0, "Type": "-int", "ToolTip": "Disables media recommendations to save memory.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Shopping List", "Key": "ShoppingListEnabled", "Value": 0, "Type": "-int", "ToolTip": "Disables the shopping list feature.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Always Open PDF Externally", "Key": "AlwaysOpenPdfExternally", "Value": 1, "Type": "-int", "ToolTip": "Forces PDFs to download and open in your system viewer instead of the browser.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Translate", "Key": "TranslateEnabled", "Value": 0, "Type": "-int", "ToolTip": "Disables automatic translation prompts.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Spellcheck", "Key": "SpellcheckEnabled", "Value": 0, "Type": "-int", "ToolTip": "Disables the built-in spellchecker to save CPU cycles.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Promotions", "Key": "PromotionsEnabled", "Value": 0, "Type": "-int", "ToolTip": "Disables Brave promotional notifications.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Search Suggestions", "Key": "SearchSuggestEnabled", "Value": 0, "Type": "-int", "ToolTip": "Disables predictive search suggestions in the URL bar.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Printing", "Key": "PrintingEnabled", "Value": 0, "Type": "-int", "ToolTip": "Disables the browser print function.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Default Browser Prompt", "Key": "DefaultBrowserSettingEnabled", "Value": 0, "Type": "-int", "ToolTip": "Stops Brave from asking to be the default browser.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Developer Tools", "Key": "DeveloperToolsDisabled", "Value": 1, "Type": "-int", "ToolTip": "Disables F12 / Inspect Element.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Disable Brave Playlist", "Key": "BravePlaylistEnabled", "Value": 0, "Type": "-int", "ToolTip": "Removes the Brave Playlist media feature.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"}
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

    # --- UI Setup & Global State ---
    style = ttk.Style()
    style.theme_use('clam')

    style.configure("TCheckbutton", background="#232323", foreground="white", font=("sans-serif", 9))
    style.map("TCheckbutton", background=[('active', '#232323')])

    style.configure("Dark.TCombobox",
                    fieldbackground="#1a1a1a", background="#1a1a1a", foreground="white",
                    arrowcolor="white", selectbackground="#333333", selectforeground="white")

    style.configure("Orange.TButton",
                    background="#E65100", foreground="white", font=("sans-serif", 10, "bold"),
                    borderwidth=2, relief="raised")
    style.map("Orange.TButton",
              background=[('active', '#BF360C')],
              foreground=[('active', 'white')])

    style.configure("Import.TButton",
                    background="#1976D2", foreground="white", font=("sans-serif", 9, "bold"),
                    borderwidth=2, relief="raised")
    style.map("Import.TButton",
              background=[('active', '#1565C0')])
    style.configure("Export.TButton",
                    background="#0D47A1", foreground="white", font=("sans-serif", 9, "bold"),
                    borderwidth=2, relief="raised")
    style.map("Export.TButton",
              background=[('active', '#0A3D91')])
    style.configure("Pull.TButton",
                    background="#F57F17", foreground="white", font=("sans-serif", 9, "bold"),
                    borderwidth=2, relief="raised")
    style.map("Pull.TButton",
              background=[('active', '#E65100')])
    style.configure("Apply.TButton",
                    background="#2E7D32", foreground="white", font=("sans-serif", 9, "bold"),
                    borderwidth=2, relief="raised")
    style.map("Apply.TButton",
              background=[('active', '#1B5E20')])
    style.configure("Reset.TButton",
                    background="#C62828", foreground="white", font=("sans-serif", 9, "bold"),
                    borderwidth=2, relief="raised")
    style.map("Reset.TButton",
              background=[('active', '#B71C1C')])

    global_is_dirty = False
    suspend_dirty_tracking = False
    baseline_state = ""
    all_feature_vars = {}
    all_perm_vars = {}

    def set_status(msg):
        status_var.set(msg)
        write_log(msg)
        root.update_idletasks()

    def set_dirty_state(is_dirty):
        global global_is_dirty
        if suspend_dirty_tracking: return
        global_is_dirty = is_dirty
        if is_dirty:
            save_status_var.set("Changes Need To Be Saved.....")
            save_status_label.config(fg="#FFD700")
        else:
            save_status_var.set("Changes Applied ✔")
            save_status_label.config(fg="#90EE90")

    def get_ui_snapshot():
        snap = {
            "Features": [key for key, var in all_feature_vars.items() if var.get() == 1],
            "Permissions": {key: var.get() for key, var in all_perm_vars.items() if var.get() != "Not Set"},
            "SafeBrowsing": sb_var.get(),
            "DnsMode": dns_var.get()
        }
        return snap

    def update_baseline():
        global baseline_state
        baseline_state = json.dumps(get_ui_snapshot(), sort_keys=True)

    def check_dirty_state(*args):
        if suspend_dirty_tracking: return
        current_json = json.dumps(get_ui_snapshot(), sort_keys=True)
        set_dirty_state(current_json != baseline_state)

    def save_current_state():
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(get_ui_snapshot(), f, indent=4)
            write_log(f"State baseline saved to {STATE_FILE}")
        except Exception as e:
            write_log(f"Failed to save state baseline: {e}")

    # --- Layout Construction ---
    root.grid_rowconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=0)
    root.grid_columnconfigure(0, weight=1)

    container = tk.Frame(root, bg="#191919")
    container.grid(row=0, column=0, sticky="nsew")
    container.grid_rowconfigure(1, weight=1)
    container.grid_columnconfigure(0, weight=1)

    top_frame = tk.Frame(container, bg="#191919")
    top_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 0))
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

    save_status_var = tk.StringVar(value="Changes Applied ✔")
    save_status_label = tk.Label(top_frame, textvariable=save_status_var, bg="#191919",
                                 fg="#90EE90", font=("sans-serif", 10, "bold"))
    save_status_label.pack(side="right", padx=30)

    main_frame = tk.Frame(container, bg="#191919")
    main_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 5))
    main_frame.grid_rowconfigure(0, weight=1)
    main_frame.grid_columnconfigure(0, weight=1)
    main_frame.grid_columnconfigure(1, weight=1)
    main_frame.grid_columnconfigure(2, weight=1)

    left_panel = tk.Frame(main_frame, bg="#232323", bd=0, highlightthickness=1, highlightbackground="#3c3c3c")
    left_panel.grid(row=0, column=0, sticky="nsew", padx=3)
    mid_panel = tk.Frame(main_frame, bg="#232323", bd=0, highlightthickness=1, highlightbackground="#3c3c3c")
    mid_panel.grid(row=0, column=1, sticky="nsew", padx=3)
    right_panel = tk.Frame(main_frame, bg="#232323", bd=0, highlightthickness=1, highlightbackground="#3c3c3c")
    right_panel.grid(row=0, column=2, sticky="nsew", padx=3)

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
        f = tk.Frame(right_panel, bg="#232323")
        f.pack(fill="x", padx=16, pady=1)
        lbl = tk.Label(f, text=perm["Name"], fg="white", bg="#232323", width=16, anchor="w", font=("sans-serif", 9))
        lbl.pack(side="left")
        create_tooltip(lbl, perm["ToolTip"])
        
        var = tk.StringVar(value="Not Set")
        all_perm_vars[perm["Key"]] = var
        var.trace_add("write", check_dirty_state)
        cb = ttk.Combobox(f, textvariable=var, values=perm["Options"], state="readonly", width=10, style="Dark.TCombobox")
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

    # --- Backend Communication ---
    def run_cmd(cmd):
        return subprocess.run(cmd, capture_output=True, text=True)

    def read_default(key):
        res = run_cmd(["defaults", "read", DOMAIN, key])
        return res.stdout.strip() if res.returncode == 0 else None

    def write_default(key, vtype, val):
        if vtype == "-array":
            cmd = ["defaults", "write", DOMAIN, key, "-array"] + val
        else:
            cmd = ["defaults", "write", DOMAIN, key, vtype, str(val)]
        run_cmd(cmd)

    def delete_default(key):
        run_cmd(["defaults", "delete", DOMAIN, key])

    def reload_ui_from_registry():
        global suspend_dirty_tracking
        suspend_dirty_tracking = True
        
        for var in all_feature_vars.values(): var.set(0)
        for var in all_perm_vars.values(): var.set("Not Set")
        sb_var.set("")
        dns_var.set("")
        
        all_feats = telemetry_features + privacy_features + brave_features + perf_features
        any_loaded = False
        
        for feat in all_feats:
            val = read_default(feat["Key"])
            if val is not None:
                any_loaded = True
                if feat["Type"] == "-array":
                    if val: all_feature_vars[feat["Key"]].set(1)
                else:
                    if str(val) == str(feat["Value"]):
                        all_feature_vars[feat["Key"]].set(1)
                        
        for perm in permission_settings:
            val = read_default(perm["Key"])
            if val is not None:
                any_loaded = True
                try:
                    val = int(val)
                    if val == 3: all_perm_vars[perm["Key"]].set("Ask")
                    elif val == 1: all_perm_vars[perm["Key"]].set("Allow")
                    elif perm["Key"] == "PaymentMethodQueryEnabled" and val == 0: all_perm_vars[perm["Key"]].set("Block")
                    elif val == 2: all_perm_vars[perm["Key"]].set("Block")
                except: pass
                
        sb_val = read_default("SafeBrowsingProtectionLevel")
        if sb_val:
            any_loaded = True
            if sb_val == "1": sb_var.set("On")
            elif sb_val == "0": sb_var.set("Off")
        
        dns_val = read_default("DnsOverHttpsMode")
        if dns_val:
            any_loaded = True
            if dns_val == "automatic": dns_var.set("On")
            elif dns_val == "off": dns_var.set("Off")
        
        suspend_dirty_tracking = False
        update_baseline()
        check_dirty_state()
        if not any_loaded:
            set_status("No Brave settings found – maybe Brave is not installed or has never been configured.")
            show_custom_info("Pull Settings", "No Brave policy settings were detected.\n\n"
                                               "This usually means Brave Browser is not installed, or you have never modified its settings via SlimBrave or the command line.")
        else:
            set_status("UI reloaded from current macOS Brave defaults.")

    def apply_settings():
        ans = messagebox.askyesno("Backup Settings", "Would you like to export your current Brave policies to a .plist file on your Desktop before applying changes? (Recommended)")
        if ans:
            set_status("Backing up current policies...")
            backup_path = os.path.expanduser("~/Desktop/Brave_Policies_Backup.plist")
            run_cmd(["sh", "-c", f"defaults read {DOMAIN} > '{backup_path}'"])
            write_log(f"Policies backed up to {backup_path}")
            
        set_status("Applying settings to macOS defaults...")
        
        all_feats = telemetry_features + privacy_features + brave_features + perf_features
        for feat in all_feats:
            if all_feature_vars[feat["Key"]].get() == 1:
                write_default(feat["Key"], feat["Type"], feat["Value"])
                write_log(f"Applied policy: {feat['Key']}")
            else:
                delete_default(feat["Key"])
                
        for perm in permission_settings:
            sel = all_perm_vars[perm["Key"]].get()
            k = perm["Key"]
            if sel == "Not Set":
                delete_default(k)
                if k == "DefaultFileSystemReadGuardSetting": delete_default("DefaultFileSystemWriteGuardSetting")
            else:
                val = 0
                if sel == "Ask": val = 3
                elif sel == "Block": val = 0 if k == "PaymentMethodQueryEnabled" else 2
                elif sel == "Allow": val = 1
                write_default(k, "-int", val)
                if k == "DefaultFileSystemReadGuardSetting": write_default("DefaultFileSystemWriteGuardSetting", "-int", val)
                write_log(f"Applied permission: {k} = {val}")
                
        if sb_var.get() == "On": write_default("SafeBrowsingProtectionLevel", "-int", 1)
        elif sb_var.get() == "Off": write_default("SafeBrowsingProtectionLevel", "-int", 0)
        else: delete_default("SafeBrowsingProtectionLevel")
        
        if dns_var.get() == "On": write_default("DnsOverHttpsMode", "-string", "automatic")
        elif dns_var.get() == "Off": write_default("DnsOverHttpsMode", "-string", "off")
        else: delete_default("DnsOverHttpsMode")
        
        save_current_state()
        update_baseline()
        check_dirty_state()
        
        res = run_cmd(["pgrep", "-i", "brave"])
        if res.stdout.strip():
            restart = messagebox.askyesno("Restart Brave", "Settings applied! Brave is currently running. Close and restart it now to apply changes?")
            if restart:
                set_status("Restarting Brave...")
                run_cmd(["killall", "Brave Browser"])
                root.after(2000, lambda: run_cmd(["open", "-a", "Brave Browser"]))
                set_status("Brave restarted successfully.")
        else:
            messagebox.showinfo("SlimBrave", "Settings applied successfully! Open Brave to see changes.")
            set_status("Settings applied successfully.")

    def reset_settings():
        if messagebox.askyesno("Confirm Reset", "Warning: This will erase ALL Brave policy settings. Continue?"):
            set_status("Resetting all settings to default...")
            run_cmd(["defaults", "delete", DOMAIN])
            reload_ui_from_registry()
            messagebox.showinfo("Reset Successful", "All Brave policies wiped.")

    def export_settings():
        f = filedialog.asksaveasfilename(defaultextension=".json", initialfile="SlimBraveSettings.json")
        if f:
            with open(f, "w") as file:
                json.dump(get_ui_snapshot(), file, indent=4)
            set_status(f"Settings exported to {f}")

    def import_settings():
        f = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if f:
            with open(f, "r") as file:
                data = json.load(file)
                global suspend_dirty_tracking
                suspend_dirty_tracking = True
                
                for var in all_feature_vars.values(): var.set(0)
                if "Features" in data:
                    for key in data["Features"]:
                        if key in all_feature_vars: all_feature_vars[key].set(1)
                
                for var in all_perm_vars.values(): var.set("Not Set")
                if "Permissions" in data:
                    for k, v in data["Permissions"].items():
                        if k in all_perm_vars: all_perm_vars[k].set(v)
                        
                if "SafeBrowsing" in data: sb_var.set(data["SafeBrowsing"])
                if "DnsMode" in data: dns_var.set(data["DnsMode"])
                
                suspend_dirty_tracking = False
                check_dirty_state()
                set_status("Settings imported. Pending save.")

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

    # --- BOTTOM BAR (always visible via grid) ---
    bottom_bar = tk.Frame(root, bg="#2d2d2d", height=70)
    bottom_bar.grid(row=1, column=0, sticky="ew")
    bottom_bar.grid_propagate(False)

    btn_frame = tk.Frame(bottom_bar, bg="#2d2d2d")
    btn_frame.pack(side="top", fill="x", pady=5)

    ttk.Button(btn_frame, text="Export Settings", style="Export.TButton", command=export_settings).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Import Settings", style="Import.TButton", command=import_settings).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Pull Settings from Brave", style="Pull.TButton", command=reload_ui_from_registry).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Apply Settings", style="Apply.TButton", command=apply_settings).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Reset All Settings", style="Reset.TButton", command=reset_settings).pack(side="left", expand=True, padx=5)

    status_var = tk.StringVar(value="Ready. Hover over options for details.")
    status_label = tk.Label(bottom_bar, textvariable=status_var, bg="#2d2d2d", fg="#aaaaaa",
                            font=("courier", 10), anchor="w", padx=10)
    status_label.pack(side="bottom", fill="x")

    # --- Startup ---
    root.after(100, reload_ui_from_registry)
    root.mainloop()

# ----------------------------------------------------------------------
# 3. Entry point
# ----------------------------------------------------------------------
if __name__ == "__main__":
    dependency_setup()
    main()
