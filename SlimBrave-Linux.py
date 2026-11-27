#!/usr/bin/env python3
# SlimBrave - Revived - v1.2.0 (Linux)

import subprocess
import sys
import os
import shutil
import time
import base64
import json
import tempfile
import datetime
import unicodedata
from urllib.parse import urlsplit

def validate_dns(mode, template):
    if type(template) is not str or len(template) > 4096 or any(
            unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in template):
        raise ValueError("Invalid DNS template text.")
    if mode in {"Secure", "Custom"} and not template.strip():
        raise ValueError("Secure DNS requires an HTTPS DoH template.")
    if mode in {"Automatic", "Secure", "Custom"}:
        for token in template.split():
            url = token[:-6] if token.endswith("{?dns}") else token
            parsed = urlsplit(url)
            if (any(c in url for c in "{}\\#") or parsed.scheme != "https" or not parsed.hostname
                    or parsed.username is not None or parsed.password is not None):
                raise ValueError("Use an HTTPS DoH endpoint, optionally ending in {?dns}.")
            _ = parsed.port


def read_config(path):
    def unique(pairs):
        result, seen = {}, set()
        for key, value in pairs:
            folded = key.casefold()
            if not key or folded in seen:
                raise ValueError("Empty or duplicate JSON key.")
            seen.add(folded)
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError("Non-finite JSON number.")

    with open(path, "rb") as stream:
        raw = stream.read(1048577)
    if len(raw) > 1048576:
        raise ValueError("Settings file exceeds 1 MiB.")
    return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique, parse_constant=reject_constant)


def dependency_setup():
    print("=" * 60)
    print(" SlimBrave - Dependency Check (Linux)")
    print("=" * 60)

    try:
        import tkinter
    except ImportError:
        print("\n[SlimBrave] Tkinter not found!")
        print("Please install the Python Tkinter package using your system's package manager.")
        print("  Debian/Ubuntu: sudo apt update && sudo apt install python3-tk")
        print("  Arch Linux:    sudo pacman -S tk")
        print("  Fedora/RedHat: sudo dnf install python3-tkinter")
        sys.exit(1)

    print("\n[SlimBrave] All required dependencies OK. Launching SlimBrave interface...")
    time.sleep(1)

def main():
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog

    CONFIG_DIR = os.path.expanduser("~/.config/slimbrave")
    STATE_FILE = os.path.join(CONFIG_DIR, "SlimBraveState.json")
    LOG_FILE = os.path.join(CONFIG_DIR, "SlimBrave.log")

    os.makedirs(CONFIG_DIR, exist_ok=True)

    # Linux paths
    POLICY_DIR = "/etc/brave/policies/managed"
    POLICY_FILE = os.path.join(POLICY_DIR, "slimbrave.json")
    
    BRAVE_SUPPORT_DIR = ""
    BRAVE_USER_DATA_DIR = ""
    BRAVE_DEFAULT_PROFILE_DIR = ""
    BRAVE_LOCAL_STATE_FILE = ""
    BRAVE_CACHE_DIR = ""
    current_channel_info = {}

    def update_paths_for_channel(channel_info):
        nonlocal BRAVE_SUPPORT_DIR, BRAVE_USER_DATA_DIR, BRAVE_DEFAULT_PROFILE_DIR
        nonlocal BRAVE_LOCAL_STATE_FILE, BRAVE_CACHE_DIR

        app_dir = channel_info["Dir"]
        BRAVE_SUPPORT_DIR = os.path.expanduser(f"~/.config/BraveSoftware/{app_dir}")
        BRAVE_USER_DATA_DIR = BRAVE_SUPPORT_DIR
        BRAVE_DEFAULT_PROFILE_DIR = os.path.join(BRAVE_USER_DATA_DIR, "Default")
        BRAVE_LOCAL_STATE_FILE = os.path.join(BRAVE_USER_DATA_DIR, "Local State")
        BRAVE_CACHE_DIR = os.path.expanduser(f"~/.cache/BraveSoftware/{app_dir}")

    def write_log(message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} - {message}\n")

    write_log("SlimBrave UI started on Linux.")

    telemetry_features = [
        {"Name": "Disable Metrics Reporting", "Key": "MetricsReportingEnabled", "Value": False, "Type": "bool", "ToolTip": 'Stops crash-report uploads; Brave does not send Chromium usage statistics.'},
        {"Name": "Disable URL Data Collection", "Key": "UrlKeyedAnonymizedDataCollectionEnabled", "Value": False, "Type": "bool", "ToolTip": "Stops sending anonymized URLs to help improve the browser.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable P3A Telemetry", "Key": "BraveP3AEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables Privacy-Preserving Product Analytics completely.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Daily Stats Ping", "Key": "BraveStatsPingEnabled", "Value": False, "Type": "bool", "ToolTip": "Stops the daily active user ping.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Web Discovery", "Key": "BraveWebDiscoveryEnabled", "Value": False, "Type": "bool", "ToolTip": "Prevents anonymous search/browsing data from being sent to Brave Search.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Limit Variations", "Key": "ChromeVariations", "Value": 1, "Type": "int", "ToolTip": 'Allows only studies marked critical (not browser security updates). Can suppress fingerprint masking, clean-link copying and image metadata stripping. Restart Brave.'},
    ]

    privacy_features = [
        {"Name": "Disable Autofill (Addresses)", "Key": "AutofillAddressEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables saving and autofilling addresses.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Autofill (Credit Cards)", "Key": "AutofillCreditCardEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables saving and autofilling credit cards.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Password Manager", "Key": "PasswordManagerEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables the built-in password manager.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Browser Sign-in", "Key": "BrowserSignin", "Value": 0, "Type": "int", "ToolTip": "Prevents syncing your data to cloud accounts.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable WebRTC IP Leak", "Key": "WebRtcIPHandling", "Value": "disable_non_proxied_udp", "Type": "string", "ToolTip": "Restricts non-proxied WebRTC UDP; can affect calls and is not a VPN leak guarantee.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable QUIC Protocol", "Key": "QuicAllowed", "Value": False, "Type": "bool", "ToolTip": 'Disables QUIC for web requests; WebRTC and WebTransport can still use UDP.'},
        {"Name": "Block Third Party Cookies", "Key": "BlockThirdPartyCookies", "Value": True, "Type": "bool", "ToolTip": "Blocks all third-party tracking cookies.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Enable Global Privacy Control", "Key": "GlobalPrivacyControlEnabled", "Value": True, "Type": "bool", "ToolTip": "Enables GPC to tell sites not to sell or share your data.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Enable De-AMP", "Key": "BraveDeAMPEnabled", "Value": True, "Type": "bool", "ToolTip": "Bypasses Google AMP pages and redirects you to the original website.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Enable Debouncing", "Key": "BraveDebouncingEnabled", "Value": True, "Type": "bool", "ToolTip": "Skips known tracking redirect hops before you reach your destination.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Strip URL Trackers", "Key": "BraveTrackersStrippingEnabled", "Value": True, "Type": "bool", "ToolTip": "Automatically removes tracking parameters from URLs.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Reduce Language Fingerprinting", "Key": "ReduceAcceptLanguage", "Value": True, "Type": "bool", "ToolTip": "Reduces the language data sent to sites to prevent fingerprinting.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Force Download Prompts", "Key": "PromptForDownloadLocation", "Value": True, "Type": "bool", "ToolTip": "Prompts for a download location; does not guarantee protection from malicious downloads.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Clear Data on Exit", "Key": "ClearBrowsingDataOnExitList", "Value": [
            "browsing_history", "download_history", "cookies_and_other_site_data", 
            "cached_images_and_files", "password_signin", "autofill", "site_settings", "hosted_app_data"
        ], "Type": "array", "ToolTip": "Opt-in. Can remove saved passwords, cookies, history, autofill, site settings and other data.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Force HTTPS-Only Mode", "Key": "HttpsOnlyMode", "Value": "force_enabled", "Type": "string", "ToolTip": 'Requests strict HTTPS. On Chromium HTTPS-First builds this may initialize the setting rather than lock it.'},
        {"Name": "Disable Network Prediction", "Key": "NetworkPredictionOptions", "Value": 2, "Type": "int", "ToolTip": "Stops speculative DNS lookups and preconnects to sites you never clicked.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Password Leak Detection", "Key": "PasswordLeakDetectionEnabled", "Value": False, "Type": "bool", "ToolTip": "Pins the Google-backed leak check off as managed policy.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
    ]

    brave_features = [
        {"Name": "Disable Brave Rewards", "Key": "BraveRewardsDisabled", "Value": True, "Type": "bool", "ToolTip": "Completely disables the Brave Crypto Rewards system.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave Wallet", "Key": "BraveWalletDisabled", "Value": True, "Type": "bool", "ToolTip": "Disables the built-in Brave Crypto Wallet.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave VPN", "Key": "BraveVPNDisabled", "Value": True, "Type": "bool", "ToolTip": 'No effect on Linux builds.'},
        {"Name": "Disable Brave AI Chat", "Key": "BraveAIChatEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables Brave Leo (AI Chat) integration.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Local AI (On-Device)", "Key": "BraveLocalAiEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables on-device AI models. Requires Brave 1.94+.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Tor", "Key": "TorDisabled", "Value": True, "Type": "bool", "ToolTip": "Disables built-in Tor window support.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Sync", "Key": "SyncDisabled", "Value": True, "Type": "bool", "ToolTip": 'Removes this device from the Sync chain. Rejoin with a code after lifting the policy.'},
        {"Name": "Disable Brave News", "Key": "BraveNewsDisabled", "Value": True, "Type": "bool", "ToolTip": "Removes the Brave News feed bloat from the New Tab page.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Brave Talk", "Key": "BraveTalkDisabled", "Value": True, "Type": "bool", "ToolTip": "Removes the built-in video calling integration.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Speedreader", "Key": "BraveSpeedreaderEnabled", "Value": False, "Type": "bool", "ToolTip": "Completely disables the Speedreader feature, reader mode, and automatic prompts.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Wayback Machine Prompts", "Key": "BraveWaybackMachineEnabled", "Value": False, "Type": "bool", "ToolTip": "Stops Brave from asking to search the Internet Archive when you hit a 404 error.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Email Aliases", "Key": "BraveEmailAliasesEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables Brave's Email Aliases forwarding feature.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
    ]

    perf_features = [
        {"Name": "Disable Background Mode", "Key": "BackgroundModeEnabled", "Value": False, "Type": "bool", "ToolTip": "Prevents extensions/apps from running after the browser is closed.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Always Open PDF Externally", "Key": "AlwaysOpenPdfExternally", "Value": True, "Type": "bool", "ToolTip": "Forces PDFs to download and open in your system viewer instead of the browser.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Disable Translate", "Key": "TranslateEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables automatic translation prompts.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Spellcheck", "Key": "SpellcheckEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables the built-in spellchecker completely to save CPU cycles.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Enhanced Spell Check", "Key": "SpellCheckServiceEnabled", "Value": False, "Type": "bool", "ToolTip": "Drops the Google web-service callout while keeping offline spellcheck active.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Search Suggestions", "Key": "SearchSuggestEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables predictive search suggestions in the URL bar.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Printing", "Key": "PrintingEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables the browser print function.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Default Browser Prompt", "Key": "DefaultBrowserSettingEnabled", "Value": False, "Type": "bool", "ToolTip": "Stops Brave from asking to be the default browser.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked"},
        {"Name": "Disable Developer Tools", "Key": "DeveloperToolsDisabled", "Value": True, "Type": "bool", "ToolTip": "Disables F12 / Inspect Element.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Disable Brave Playlist", "Key": "BravePlaylistEnabled", "Value": False, "Type": "bool", "ToolTip": "Removes the Brave Playlist media feature.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Enable Memory Saver", "Key": "HighEfficiencyModeEnabled", "Value": True, "Type": "bool", "ToolTip": "Forces Chromium High Efficiency Mode on to aggressively save RAM.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Force Hardware Acceleration", "Key": "HardwareAccelerationModeEnabled_Force", "RealKey": "HardwareAccelerationModeEnabled", "Value": True, "Type": "bool", "ToolTip": "Pins the default hardware acceleration on so it can't drift.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Hardware Acceleration", "Key": "HardwareAccelerationModeEnabled_Disable", "RealKey": "HardwareAccelerationModeEnabled", "Value": False, "Type": "bool", "ToolTip": "Troubleshooting setting to turn off GPU acceleration. Fixes driver faults, screen-sharing bugs, and YouTube playback crashes.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Disable Media Router (Cast)", "Key": "EnableMediaRouter", "Value": False, "Type": "bool", "ToolTip": "Disables Chromecast casting support.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
    ]

    access_features = [
        {'Name': 'Remove Always Allow for External Apps', 'Key': 'ExternalProtocolDialogShowAlwaysOpenCheckbox', 'Value': False, 'Type': 'bool', 'ToolTip': 'Removes the remember-choice checkbox from external app prompts.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked'},
        {'Name': 'Block Camera Access', 'Key': 'VideoCaptureAllowed', 'Value': False, 'Type': 'bool', 'ToolTip': 'Blocks camera requests except applicable policy exceptions.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked'},
        {'Name': 'Block Microphone Access', 'Key': 'AudioCaptureAllowed', 'Value': False, 'Type': 'bool', 'ToolTip': 'Blocks microphone requests except applicable policy exceptions.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked'},
        {'Name': 'Block Local Network Access', 'Key': 'LocalNetworkAccessBlockedForUrls', 'Value': ['*'], 'Type': 'array', 'ToolTip': 'Can break local integrations, casting and device web interfaces.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked'},
        {'Name': 'Prevent Deleting History', 'Key': 'AllowDeletingBrowserHistory', 'Value': False, 'Type': 'bool', 'ToolTip': 'Disables user-initiated history deletion, not history collection.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked'},
        {'Name': 'Block Certificate Warning Bypass', 'Key': 'SSLErrorOverrideAllowed', 'Value': False, 'Type': 'bool', 'ToolTip': 'Disables proceeding past certificate errors.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked'},
        {'Name': 'Block Safe Browsing Bypass', 'Key': 'SafeBrowsingProceedAnywayDisabled', 'Value': True, 'Type': 'bool', 'ToolTip': 'Disables proceeding past Safe Browsing warnings.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked'},
        {'Name': 'Force YouTube Restricted Mode', 'Key': 'ForceYouTubeRestrict', 'Value': 2, 'Type': 'int', 'ToolTip': 'Enforces Strict Restricted Mode.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked'},
        {'Name': 'Block Command-Line Extensions', 'Key': 'ExtensionInstallTypeBlocklist', 'Value': ['command_line'], 'Type': 'array', 'ToolTip': 'Blocks --load-extension; may affect development shortcuts.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked'},
        {'Name': 'Disable Google Image Descriptions', 'Key': 'AccessibilityImageLabelsEnabled', 'Value': False, 'Type': 'bool', 'ToolTip': 'Prevents server-generated labels for screen-reader users.\n\nSuggested Settings for Privacy: Ticked | Security: Unticked'},
        {'Name': 'Isolate Origins', 'Key': 'OriginKeyedProcessesEnabled', 'Value': True, 'Type': 'bool', 'ToolTip': 'Separates most origins into processes; may increase RAM use.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked'},
        {'Name': 'Force Site Isolation', 'Key': 'SitePerProcess', 'Value': True, 'Type': 'bool', 'ToolTip': 'Locks site isolation on; restart required.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked'},
        {'Name': 'Disable JavaScript Optimization', 'Key': 'DefaultJavaScriptOptimizerSetting', 'Value': 2, 'Type': 'int', 'ToolTip': 'Hardens JavaScript execution at a possible performance cost.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked'},
        {'Name': 'Disable XSLT', 'Key': 'XSLTEnabled', 'Value': False, 'Type': 'bool', 'ToolTip': 'Disables legacy XML transformations; may affect XML and RSS rendering.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked'},
        {"Name": "Disable Guest Mode", "Key": "BrowserGuestModeEnabled", "Value": False, "Type": "bool", "ToolTip": "Disables the guest profile escape hatch.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Block All Extensions", "Key": "ExtensionInstallBlocklist", "Value": ["*"], "Type": "array", "ToolTip": "Completely blocks all extension installations.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Block Sideloaded Extensions", "Key": "BlockExternalExtensions", "Value": True, "Type": "bool", "ToolTip": "Blocks silent extension installs while leaving user-chosen extensions working.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Force Google SafeSearch", "Key": "ForceGoogleSafeSearch", "Value": True, "Type": "bool", "ToolTip": "Filters explicit search results.\n\nSuggested Settings for Privacy: Unticked | Security: Ticked"},
        {"Name": "Force Incognito Mode", "Key": "IncognitoModeAvailability", "Value": 2, "Type": "int", "ToolTip": "Forces the browser to always open in Incognito Mode.\n\nSuggested Settings for Privacy: Unticked | Security: Unticked"},
        {"Name": "Block Remote Debugging", "Key": "RemoteDebuggingAllowed", "Value": False, "Type": "bool", "ToolTip": "Stops the --remote-debugging-port cookie theft vector.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
        {"Name": "Require HTTPS for Basic Auth", "Key": "BasicAuthOverHttpEnabled", "Value": False, "Type": "bool", "ToolTip": "Stops base64 credentials from going out over cleartext HTTP.\n\nSuggested Settings for Privacy: Ticked | Security: Ticked"},
    ]

    permission_settings = [
        {"Name": "Location", "Key": "DefaultGeolocationSetting", "Options": ["Not Set", "Ask", "Block", "Allow"], "ToolTip": "Allows sites to request your physical location.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Notifications", "Key": "DefaultNotificationsSetting", "Options": ["Not Set", "Block", "Allow"], "ToolTip": "Allows sites to send you native desktop push notifications.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "JavaScript", "Key": "DefaultJavaScriptSetting", "Options": ["Not Set", "Allow", "Block"], "ToolTip": "Allows sites to run interactive scripts. Blocking this breaks almost all websites.\n\nSuggested Settings for Privacy: Allow | Security: Allow"},
        {"Name": "Images", "Key": "DefaultImagesSetting", "Options": ["Not Set", "Allow", "Block"], "ToolTip": "Allows sites to load and display images.\n\nSuggested Settings for Privacy: Not Set | Security: Not Set"},
        {"Name": "Pop-ups and Redirects", "Key": "DefaultPopupsSetting", "Options": ["Not Set", "Block", "Allow"], "ToolTip": "Allows sites to open new windows or redirect you without your input.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "USB Devices", "Key": "DefaultWebUsbGuardSetting", "Options": ["Not Set", "Ask", "Block"], "ToolTip": "Allows sites to request direct connection to your plugged-in USB devices.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Serial Ports", "Key": "DefaultSerialGuardSetting", "Options": ["Not Set", "Ask", "Block"], "ToolTip": "Allows sites to request connection to hardware via serial ports.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "HID Devices", "Key": "DefaultWebHidGuardSetting", "Options": ["Not Set", "Ask", "Block"], "ToolTip": "Allows sites to request access to Human Interface Devices (e.g. controllers).\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "File Editing", "Key": "DefaultFileSystemReadGuardSetting", "Options": ["Not Set", "Ask", "Block"], "ToolTip": "Allows sites to read and save files directly to your local file system.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Clipboard", "Key": "DefaultClipboardSetting", "Options": ["Not Set", "Ask", "Block"], "ToolTip": "Allows sites to read text and images copied to your clipboard.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Window Management", "Key": "DefaultWindowPlacementSetting", "Options": ["Not Set", "Ask", "Block"], "ToolTip": "Allows sites to open windows on specific monitors or in fullscreen.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Local Fonts", "Key": "DefaultLocalFontsSetting", "Options": ["Not Set", "Ask", "Block"], "ToolTip": "Allows sites to fingerprint your device based on locally installed fonts.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Payment Handlers", "Key": "PaymentMethodQueryEnabled", "Options": ["Not Set", "Block", "Allow"], "ToolTip": "Allows sites to check if you have local payment apps installed.\n\nSuggested Settings for Privacy: Block | Security: Block"},
        {"Name": "Motion Sensors", "Key": "DefaultSensorsSetting", "Options": ["Not Set", "Block", "Allow"], "ToolTip": "Allows sites to access device orientation and motion sensors.\n\nSuggested Settings for Privacy: Block | Security: Block"},
    ]

    ALL_FEATURES = telemetry_features + privacy_features + brave_features + perf_features + access_features
    managed_keys = {feat.get("RealKey", feat["Key"]) for feat in ALL_FEATURES}
    managed_keys.update({perm["Key"] for perm in permission_settings})
    managed_keys.update({
        "DefaultFileSystemWriteGuardSetting", "SafeBrowsingProtectionLevel", 
        "DnsOverHttpsMode", "DnsOverHttpsTemplates", "BraveShieldsDisabledForUrls", "BraveShieldsEnabledForUrls"
    })

    BOOL_POLICY_KEYS = {feat.get("RealKey", feat["Key"]) for feat in ALL_FEATURES if feat["Type"] == "bool"}
    STRING_POLICY_KEYS = {feat.get("RealKey", feat["Key"]) for feat in ALL_FEATURES if feat["Type"] == "string"}
    ARRAY_POLICY_KEYS = {feat.get("RealKey", feat["Key"]) for feat in ALL_FEATURES if feat["Type"] == "array"}
    INT_POLICY_KEYS = {feat.get("RealKey", feat["Key"]) for feat in ALL_FEATURES if feat["Type"] == "int"}
    ARRAY_POLICY_KEYS.update({"BraveShieldsDisabledForUrls", "BraveShieldsEnabledForUrls"})

    CONTENT_SETTING_KEYS = {
        "DefaultGeolocationSetting", "DefaultVideoCaptureSetting", "DefaultAudioCaptureSetting",
        "DefaultNotificationsSetting", "DefaultJavaScriptSetting", "DefaultImagesSetting",
        "DefaultPopupsSetting", "DefaultWebUsbGuardSetting", "DefaultSerialGuardSetting",
        "DefaultWebHidGuardSetting", "DefaultFileSystemReadGuardSetting", "DefaultFileSystemWriteGuardSetting",
        "DefaultClipboardSetting", "DefaultWindowPlacementSetting", "DefaultLocalFontsSetting",
        "DefaultSensorsSetting",
    }

    # Compiled out keys for Brave Origin detection logic
    compiled_out_keys = {
        "BraveRewardsDisabled", "BraveWalletDisabled", "BraveVPNDisabled",
        "BraveAIChatEnabled", "BraveLocalAiEnabled", "BraveNewsDisabled",
        "BraveTalkDisabled", "BravePlaylistEnabled", "BraveWebDiscoveryEnabled",
        "BraveSpeedreaderEnabled", "TorDisabled", "BraveEmailAliasesEnabled",
        "BraveWaybackMachineEnabled"
    }

    root = tk.Tk()
    root.title("SlimBrave - Revived v1.2.0 (Linux)")
    root.geometry("1100x600")
    root.minsize(980, 450)
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
                tw, text=self.text, justify="left", background="#2d2d2d", foreground="white",
                relief="solid", borderwidth=1, font=("sans-serif", 10, "normal"),
                padx=12, pady=8, wraplength=400,
            )
            label.pack(ipadx=1)

        def hide(self):
            if self.tooltip_window:
                self.tooltip_window.destroy()
                self.tooltip_window = None

    def create_tooltip(widget, text):
        return ToolTip(widget, text)

    style = ttk.Style()
    style.theme_use("clam")
    
    for state, color in {"Retained": "#87CEFA", "Added": "#90EE90",
                         "Removed": "#FF8585", "Neutral": "white"}.items():
        name = f"{state}.TCheckbutton"
        style.configure(name, foreground=color)
        style.map(name, foreground=[("!disabled", color)])

    style.configure("TCheckbutton", background="#232323", foreground="white", font=("sans-serif", 9))
    style.map("TCheckbutton", 
              background=[("active", "#232323")],
              foreground=[("selected", "#87CEFA"), ("!selected", "white")],
              indicatorcolor=[("selected", "#87CEFA"), ("!selected", "#161616")])

    style.configure(
        "Dark.TCombobox", fieldbackground="#161616", background="#161616",
        foreground="white", arrowcolor="white", selectbackground="#333333", selectforeground="white",
    )
    style.map(
        "Dark.TCombobox", fieldbackground=[("readonly", "#161616")],
        background=[("readonly", "#161616")], selectbackground=[("readonly", "#333333")],
        selectforeground=[("readonly", "white")],
    )

    style.configure(
        "Dark.Vertical.TScrollbar", background="#333333", troughcolor="#1a1a1a",
        bordercolor="#1a1a1a", arrowcolor="white", relief="flat",
    )
    style.map("Dark.Vertical.TScrollbar", background=[("active", "#555555")])

    button_padding = (15, 8)
    button_styles = {
        "Preset.TButton": "#E65100", "Export.TButton": "#0D47A1", "Import.TButton": "#1976D2",
        "Reload.TButton": "#F57F17", "Apply.TButton": "#2E7D32", "Reset.TButton": "#C62828"
    }
    active_styles = {
        "Preset.TButton": "#BF360C", "Export.TButton": "#0A3D91", "Import.TButton": "#1565C0",
        "Reload.TButton": "#E65100", "Apply.TButton": "#1B5E20", "Reset.TButton": "#B71C1C"
    }

    for sty, color in button_styles.items():
        style.configure(
            sty, background=color, foreground="white",
            font=("sans-serif", 9 if sty != "Preset.TButton" else 10, "bold"),
            borderwidth=0, relief="flat", padding=button_padding,
        )
        style.map(sty, background=[("active", active_styles[sty])], foreground=[("active", "white")])

    global_is_dirty = False
    suspend_dirty_tracking = False
    baseline_state = ""
    all_feature_vars = {}
    feature_widgets = {}
    preset_preview = None

    def refresh_preset_colors(*_):
        if suspend_dirty_tracking:
            return
        for key, widget in feature_widgets.items():
            widget, marker, reason_tip = widget
            checked = bool(all_feature_vars[key].get())
            if preset_preview is None:
                reason_tip.on_leave()
                marker.pack_forget()
                widget.configure(style="TCheckbutton")
                continue
            retained, seen, selected = preset_preview
            if checked:
                seen.add(key)
            state = ("Retained" if key in retained else "Added") if checked else (
                "Removed" if key in seen else "Neutral")
            widget.configure(style=f"{state}.TCheckbutton")
            if state == "Added":
                reason = "Added by Preset" if key in selected else "Manually Added, Preset Disabled This"
                color = "#90EE90"
            elif state == "Removed":
                reason = "Removed from Preset" if key in selected else "Removed from your Current Configuration"
                color = "#FF8585"
            else:
                reason_tip.on_leave()
                marker.pack_forget()
                continue
            if reason_tip.text != reason:
                reason_tip.on_leave()
                reason_tip.text = reason
            marker.configure(fg=color)
            if not marker.winfo_manager():
                marker.pack(side="left", padx=(4, 0))

    all_perm_vars = {}

    status_var = tk.StringVar(value="Ready.")
    save_status_var = tk.StringVar(value="Unmanaged ❌")

    channels_dict = {
        "Release": {"App": "Brave Browser", "Dir": "Brave-Browser", "Execs": ["brave", "brave-browser", "brave-browser-stable"]},
        "Beta": {"App": "Brave Browser Beta", "Dir": "Brave-Browser-Beta", "Execs": ["brave-browser-beta", "brave-beta"]},
        "Dev": {"App": "Brave Browser Dev", "Dir": "Brave-Browser-Dev", "Execs": ["brave-browser-dev", "brave-dev"]},
        "Nightly": {"App": "Brave Browser Nightly", "Dir": "Brave-Browser-Nightly", "Execs": ["brave-browser-nightly", "brave-nightly"]},
        "Origin": {"App": "Brave Origin", "Dir": "Brave-Browser", "Execs": ["brave-origin", "brave-browser-origin"]}
    }
    
    installed_channels = {}
    for name, info in channels_dict.items():
        if name == "Origin":
            if os.path.exists("/opt/brave-origin-bin") or os.path.exists("/opt/brave.com/brave-origin") or shutil.which("brave-origin") or shutil.which("brave-browser-origin"):
                installed_channels[name] = info
        else:
            if os.path.exists(os.path.expanduser(f"~/.config/BraveSoftware/{info['Dir']}")) or any(shutil.which(x) for x in info["Execs"]):
                installed_channels[name] = info
    
    if not installed_channels:
        installed_channels["Release"] = channels_dict["Release"]

    is_origin_only = len(installed_channels) == 1 and "Origin" in installed_channels
    current_channel_info = list(installed_channels.values())[0]
    update_paths_for_channel(current_channel_info)

    def is_profile_installed():
        return os.path.exists(POLICY_FILE)

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
        features_list = []
        for key, var in all_feature_vars.items():
            if var.get() == 1:
                # Exclude compiled-out keys from local state JSON & Exports if Origin-only
                if is_origin_only and key in compiled_out_keys:
                    continue
                features_list.append(key)
                
        return {
            "Features": features_list,
            "Permissions": {key: var.get() for key, var in all_perm_vars.items() if var.get() != "Not Set"},
            "SafeBrowsing": sb_var.get(),
            "DnsMode": dns_var.get(),
            "DnsTemplate": dns_tpl_var.get()
        }

    def update_baseline():
        nonlocal baseline_state, preset_preview
        baseline_state = json.dumps(get_ui_snapshot(), sort_keys=True)
        preset_preview = None
        refresh_preset_colors()

    def check_dirty_state(*args):
        if suspend_dirty_tracking:
            return
        current_json = json.dumps(get_ui_snapshot(), sort_keys=True)
        set_dirty_state(current_json != baseline_state)

    def save_current_state():
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(get_ui_snapshot(), f, indent=4)
            write_log(f"State Saved ✅ to {STATE_FILE}")
        except Exception as e:
            write_log(f"State save failed: {e}")

    def elevated(command):
        for path in ("/usr/bin/pkexec", "/usr/bin/sudo"):
            if os.access(path, os.X_OK):
                return [path, *command]
        raise RuntimeError("Install pkexec or sudo to change system policy.")

    def change_system_policy(payload):
        if payload is None:
            subprocess.run(elevated(["/usr/bin/rm", "-f", "--", POLICY_FILE]),
                           capture_output=True, text=True, check=True)
            return
        script = r'''set -eu
umask 022
/usr/bin/mkdir -p -- "$1"
tmp=$(/usr/bin/mktemp "$1/.slimbrave.XXXXXXXX")
trap '/usr/bin/rm -f -- "$tmp"' EXIT
/usr/bin/cat > "$tmp"
/usr/bin/chmod 0644 "$tmp"
/usr/bin/sync -f "$tmp"
/usr/bin/mv -fT -- "$tmp" "$2"
/usr/bin/sync -f "$1"
'''
        subprocess.run(elevated(["/bin/sh", "-c", script, "slimbrave", POLICY_DIR, POLICY_FILE]),
                       input=json.dumps(payload, indent=4) + "\n", capture_output=True, text=True, check=True)

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

        if "BraveShieldsDisabledForUrls" in cleaned and "BraveShieldsEnabledForUrls" in cleaned:
            disabled_set = set(cleaned["BraveShieldsDisabledForUrls"])
            enabled_set = set(cleaned["BraveShieldsEnabledForUrls"])
            overlap = disabled_set.intersection(enabled_set)
            if overlap:
                warnings.append("Stripped contradictory URLs found in both Shields Disabled and Enabled policies.")
                cleaned["BraveShieldsDisabledForUrls"] = list(disabled_set - overlap)
                cleaned["BraveShieldsEnabledForUrls"] = list(enabled_set - overlap)

        return cleaned, warnings

    def read_managed_prefs_json():
        if os.path.exists(POLICY_FILE):
            try:
                with open(POLICY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    cleaned, _ = sanitize_managed_payload(data)
                    return cleaned
            except Exception as e:
                write_log(f"Could not read policy JSON: {e}")
        return {}

    def merged_policy_source_for_ui():
        payload = read_managed_prefs_json()
        payload, _ = sanitize_managed_payload(payload)
        return payload

    def build_managed_payload_from_ui():
        payload = {}

        for feat in ALL_FEATURES:
            if all_feature_vars[feat["Key"]].get() != 1:
                continue

            actual_key = feat.get("RealKey", feat["Key"])

            if feat["Type"] == "bool":
                payload[actual_key] = bool(feat["Value"])
            elif feat["Type"] == "int":
                payload[actual_key] = int(feat["Value"])
            elif feat["Type"] == "string":
                payload[actual_key] = str(feat["Value"])
            elif feat["Type"] == "array":
                payload[actual_key] = list(feat["Value"])

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
        if tpl and dns_mode in ["Automatic", "Secure", "Custom"]:
            payload["DnsOverHttpsTemplates"] = tpl

        # Discard compiled-out policies if the user exclusively uses Brave Origin
        if is_origin_only:
            for k in compiled_out_keys:
                payload.pop(k, None)

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
        dns_tpl_var.set("")

        for feat in ALL_FEATURES:
            key = feat["Key"]
            actual_key = feat.get("RealKey", key)
            if actual_key not in payload:
                continue

            value = payload[actual_key]
            if feat["Type"] == "array":
                if value == feat["Value"]:
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

            choice = {1: "Allow", 2: "Block", 3: "Ask"}.get(iv)
            if choice in perm["Options"]:
                all_perm_vars[key].set(choice)

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
        check_dirty_state()

    def reload_ui_from_registry():
        # Only imports are staged. Reload reflects the installed system policy.
        payload = merged_policy_source_for_ui()
        apply_payload_to_ui(payload)
        set_status("Settings loaded. (Profile Installed ✅)" if is_profile_installed()
                   else "No SlimBrave policies active.")

    def pgrep_exact(pattern):
        try:
            res = run_cmd(["pgrep", "-x", pattern])
            return bool(res.stdout.strip())
        except Exception:
            return False

    def singleton_lock_pid():
        lock_path = os.path.join(BRAVE_USER_DATA_DIR, "SingletonLock")
        try:
            target = os.readlink(lock_path)
            pid_part = target.rsplit("-", 1)[-1]
            return int(pid_part) if pid_part.isdigit() else None
        except OSError:
            return None

    def kill_brave_family(progress=None):
        exec_names = current_channel_info["Execs"]

        for pat in exec_names:
            run_cmd(["killall", pat])
            run_cmd(["pkill", "-TERM", "-x", pat])
        time.sleep(2.0)

        for pat in exec_names:
            if pgrep_exact(pat):
                run_cmd(["pkill", "-KILL", "-x", pat])
        time.sleep(1.5)

        still_running = any(pgrep_exact(pat) for pat in exec_names)
        if progress:
            app_name = current_channel_info["App"]
            progress.log(f"{app_name} is still running." if still_running else f"{app_name} is closed.")
        return not still_running

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
        payload = {}

        if os.path.exists(POLICY_FILE):
            try:
                with open(POLICY_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    payload = raw
            except Exception as e:
                lines.append(f"Policy file read error: {e}")

        managed_keys_found = sorted(k for k in payload.keys() if k in managed_keys)

        lines.append(f"System policy file: {'found' if os.path.exists(POLICY_FILE) else 'not found'} ({POLICY_FILE})")
        lines.append(f"System policy keys active: {len(managed_keys_found)}")

        if "PaymentMethodQueryEnabled" in payload and not isinstance(payload["PaymentMethodQueryEnabled"], bool):
            lines.append(f"Suspicious type in policy: PaymentMethodQueryEnabled")

        lines.append(f"Local State: {'found' if os.path.exists(BRAVE_LOCAL_STATE_FILE) else 'not found'}")
        lines.append(f"Default/Preferences: {'found' if os.path.exists(os.path.join(BRAVE_DEFAULT_PROFILE_DIR, 'Preferences')) else 'not found'}")

        return lines

    def check_and_close_brave():
        app_name = current_channel_info["App"]
        exec_names = current_channel_info["Execs"]
        
        is_running = False
        pid = singleton_lock_pid()
        if pid is not None and os.path.isdir(f"/proc/{pid}"):
            is_running = True
        elif any(pgrep_exact(pat) for pat in exec_names):
            is_running = True

        if not is_running:
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
        try:
            with open(f, "w", encoding="utf-8") as file:
                json.dump(get_ui_snapshot(), file, indent=4)
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        set_status("Settings exported.")

    def import_settings():
        f = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not f:
            return

        try:
            data = read_config(f)
            if type(data) is not dict:
                raise ValueError("Expected a settings object.")
            features = data.get("Features", [])
            permissions = data.get("Permissions", {})
            if type(features) is not list or type(permissions) is not dict:
                raise ValueError("Expected a Features array and a Permissions object.")
            known = {row["Key"]: row.get("RealKey", row["Key"]) for row in ALL_FEATURES}
            options = {row["Key"]: row["Options"] for row in permission_settings}
            allowed = {"Features", "Permissions", "SafeBrowsing", "DnsMode", "DnsTemplate"}
            notes = ["Unknown field: " + ascii(k)[:80] for k in data.keys() - allowed]
            selected = {}
            for key in features:
                if type(key) is not str or key not in known or (is_origin_only and key in compiled_out_keys):
                    notes.append("Ignored feature: " + ascii(key)[:80])
                    continue
                real = known[key]
                if real in selected and key != selected[real]:
                    notes.append("Replaced conflicting feature: " + selected[real])
                selected[real] = key
            cleaned = {}
            for key, value in permissions.items():
                if key not in options or value not in options[key]:
                    notes.append("Ignored permission or value: " + ascii(key)[:80])
                elif value != "Not Set":
                    cleaned[key] = value
            sb = data.get("SafeBrowsing") or ""
            mode = data.get("DnsMode") or ""
            template = data.get("DnsTemplate", "")
            if sb not in ("", "On", "Off") or mode not in ("", "Automatic", "Off", "Secure", "Custom"):
                raise ValueError("Invalid Safe Browsing or DNS mode.")
            validate_dns(mode, template)
            if not (selected or cleaned or sb or mode):
                raise ValueError("No applicable settings; existing selections were preserved.")
        except (OSError, ValueError, RecursionError) as exc:
            messagebox.showerror("Import failed", str(exc))
            return
        apply_json_state_to_ui(dict(Features=list(selected.values()), Permissions=cleaned,
                                   SafeBrowsing=sb, DnsMode=mode, DnsTemplate=template))
        refresh_preset_colors()
        set_status("Settings staged. Review before applying.")
        if notes:
            messagebox.showinfo("Import notes", "\n".join(notes[:5]) +
                                (f"\nand {len(notes) - 5} more" if len(notes) > 5 else ""))

    def apply_settings():
        dns_mode = dns_var.get()
        tpl = dns_tpl_var.get().strip()
        try:
            validate_dns(dns_mode, dns_tpl_var.get())
        except ValueError as exc:
            messagebox.showerror("DNS validation failed", str(exc))
            return

        if not check_and_close_brave():
            return

        payload = build_managed_payload_from_ui()
        cleaned_payload, warnings = sanitize_managed_payload(payload)

        progress = ProgressDialog(root, "Apply")
        profile_was_installed = False

        try:
            progress.step(10, "Preparing settings...")
            progress.log(f"Keys selected: {len(cleaned_payload)}")

            progress.step(55, "Applying System Policy via pkexec/sudo...")
            change_system_policy(cleaned_payload or None)
            progress.log("Wrote policy file." if cleaned_payload else "Removed SlimBrave policy file.")

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
                    "Apply Complete", 
                    f"SlimBrave policies have been successfully written to:\n{POLICY_FILE}\n\n"
                    "Restart Brave and navigate to 'brave://policy' to verify your settings."
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
                
            progress.step(42, "Removing System Policy (if installed)...")
            profile_installed_initially = is_profile_installed()
            profile_removed = False
            if profile_installed_initially:
                cmd = []
                cmd = elevated(["/usr/bin/rm", "-f", "--", POLICY_FILE])
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    progress.log("Policy natively removed.")
                    profile_removed = True
                else:
                    progress.log("Policy requires manual removal (permission issue).")
            else:
                progress.log("No Policy detected.")
                profile_removed = True

            progress.step(88, "Clearing Brave caches...")
            cache_removed = clear_brave_runtime_caches()
            progress.log(f"Cache paths cleared: {len(cache_removed)}")

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
                f"Policy removal: {'Success / Not Required' if profile_removed else 'Manual removal required'}",
                f"Cache paths cleared: {len(cache_removed)}",
                "",
                "Your Brave profile was kept."
            ]

            progress.finish("Done.")
            show_text_report("Light Reset Summary", report)
            
            if not profile_removed:
                messagebox.showwarning("Manual Removal Required", f"Light Reset finished, but the automatic removal of your SlimBrave Policy failed.\n\nYou must manually delete it with sudo:\n{POLICY_FILE}")
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
                
            progress.step(42, "Removing System Policy (if installed)...")
            profile_installed_initially = is_profile_installed()
            profile_removed = False
            if profile_installed_initially:
                cmd = []
                cmd = elevated(["/usr/bin/rm", "-f", "--", POLICY_FILE])
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    progress.log("Policy natively removed.")
                    profile_removed = True
                else:
                    progress.log("Policy requires manual removal (permission issue).")
            else:
                progress.log("No Policy detected.")
                profile_removed = True

            progress.step(70, "Clearing Brave caches...")
            cache_removed = clear_brave_runtime_caches()
            progress.log(f"Cache paths cleared: {len(cache_removed)}")

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
                f"Policy removal: {'Success / Not Required' if profile_removed else 'Manual removal required'}",
                f"Cache paths cleared: {len(cache_removed)}",
                f"Profile backup: {backup_path if backup_path else '(new folder created)'}",
                "",
                "A fresh Brave profile will be created on next launch."
            ]

            progress.finish("Done.")
            show_text_report("Hard Reset Summary", report)
            
            if not profile_removed:
                messagebox.showwarning("Manual Removal Required", f"Hard Reset finished, but the automatic removal of your SlimBrave Policy failed.\n\nYou must manually delete it with sudo:\n{POLICY_FILE}")
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

    PRESETS = {'Maximum Privacy': (['AccessibilityImageLabelsEnabled',
                          'AutofillAddressEnabled',
                          'AutofillCreditCardEnabled',
                          'BackgroundModeEnabled',
                          'BasicAuthOverHttpEnabled',
                          'BlockExternalExtensions',
                          'BlockThirdPartyCookies',
                          'BraveAIChatEnabled',
                          'BraveDeAMPEnabled',
                          'BraveDebouncingEnabled',
                          'BraveLocalAiEnabled',
                          'BraveNewsDisabled',
                          'BraveP3AEnabled',
                          'BravePlaylistEnabled',
                          'BraveRewardsDisabled',
                          'BraveSpeedreaderEnabled',
                          'BraveStatsPingEnabled',
                          'BraveTalkDisabled',
                          'BraveTrackersStrippingEnabled',
                          'BraveWalletDisabled',
                          'BraveWaybackMachineEnabled',
                          'BraveWebDiscoveryEnabled',
                          'BrowserSignin',
                          'DefaultJavaScriptOptimizerSetting',
                          'ExtensionInstallTypeBlocklist',
                          'ExternalProtocolDialogShowAlwaysOpenCheckbox',
                          'GlobalPrivacyControlEnabled',
                          'HttpsOnlyMode',
                          'MetricsReportingEnabled',
                          'NetworkPredictionOptions',
                          'OriginKeyedProcessesEnabled',
                          'ReduceAcceptLanguage',
                          'RemoteDebuggingAllowed',
                          'SearchSuggestEnabled',
                          'SitePerProcess',
                          'SpellCheckServiceEnabled',
                          'UrlKeyedAnonymizedDataCollectionEnabled',
                          'WebRtcIPHandling',
                          'XSLTEnabled'],
                         {'DefaultGeolocationSetting': 'Block',
                          'DefaultNotificationsSetting': 'Block',
                          'DefaultPopupsSetting': 'Block',
                          'DefaultWebUsbGuardSetting': 'Block',
                          'DefaultSerialGuardSetting': 'Block',
                          'DefaultWebHidGuardSetting': 'Block',
                          'DefaultFileSystemReadGuardSetting': 'Block',
                          'DefaultClipboardSetting': 'Block',
                          'DefaultWindowPlacementSetting': 'Block',
                          'DefaultLocalFontsSetting': 'Block',
                          'PaymentMethodQueryEnabled': 'Block',
                          'DefaultSensorsSetting': 'Block'},
                         'On',
                         'Automatic'),
     'High Security': (['BackgroundModeEnabled',
                        'BasicAuthOverHttpEnabled',
                        'BlockExternalExtensions',
                        'BlockThirdPartyCookies',
                        'BraveAIChatEnabled',
                        'BraveLocalAiEnabled',
                        'BraveNewsDisabled',
                        'BraveP3AEnabled',
                        'BravePlaylistEnabled',
                        'BraveRewardsDisabled',
                        'BraveSpeedreaderEnabled',
                        'BraveStatsPingEnabled',
                        'BraveTalkDisabled',
                        'BraveWalletDisabled',
                        'BraveWaybackMachineEnabled',
                        'BraveWebDiscoveryEnabled',
                        'DefaultJavaScriptOptimizerSetting',
                        'ExtensionInstallTypeBlocklist',
                        'ExternalProtocolDialogShowAlwaysOpenCheckbox',
                        'HttpsOnlyMode',
                        'MetricsReportingEnabled',
                        'OriginKeyedProcessesEnabled',
                        'RemoteDebuggingAllowed',
                        'SSLErrorOverrideAllowed',
                        'SafeBrowsingProceedAnywayDisabled',
                        'SitePerProcess',
                        'UrlKeyedAnonymizedDataCollectionEnabled',
                        'XSLTEnabled'],
                       {'DefaultPopupsSetting': 'Block',
                        'DefaultWebUsbGuardSetting': 'Block',
                        'DefaultSerialGuardSetting': 'Block',
                        'DefaultWebHidGuardSetting': 'Block',
                        'DefaultFileSystemReadGuardSetting': 'Block',
                        'DefaultClipboardSetting': 'Block'},
                       'On',
                       'Automatic'),
     'Performance Focused': (['BackgroundModeEnabled',
                              'BraveLocalAiEnabled',
                              'BraveNewsDisabled',
                              'BravePlaylistEnabled',
                              'BraveRewardsDisabled',
                              'BraveTalkDisabled',
                              'BraveWalletDisabled',
                              'EnableMediaRouter',
                              'HighEfficiencyModeEnabled'],
                             {},
                             'On',
                             ''),
     'Strict Parental Controls': (['AllowDeletingBrowserHistory',
                                   'BasicAuthOverHttpEnabled',
                                   'BraveAIChatEnabled',
                                   'BraveLocalAiEnabled',
                                   'BrowserGuestModeEnabled',
                                   'ExtensionInstallBlocklist',
                                   'ExtensionInstallTypeBlocklist',
                                   'ForceGoogleSafeSearch',
                                   'ForceYouTubeRestrict',
                                   'IncognitoModeAvailability',
                                   'PromptForDownloadLocation',
                                   'RemoteDebuggingAllowed',
                                   'SSLErrorOverrideAllowed',
                                   'SafeBrowsingProceedAnywayDisabled',
                                   'SpellCheckServiceEnabled',
                                   'SyncDisabled',
                                   'TorDisabled'],
                                  {'DefaultPopupsSetting': 'Block',
                                   'DefaultNotificationsSetting': 'Block'},
                                  'On',
                                  'Secure'),
     'Balanced Privacy': (['BasicAuthOverHttpEnabled',
                           'BlockExternalExtensions',
                           'BlockThirdPartyCookies',
                           'BraveDeAMPEnabled',
                           'BraveDebouncingEnabled',
                           'BraveLocalAiEnabled',
                           'BraveNewsDisabled',
                           'BraveP3AEnabled',
                           'BravePlaylistEnabled',
                           'BraveRewardsDisabled',
                           'BraveStatsPingEnabled',
                           'BraveTrackersStrippingEnabled',
                           'BraveWalletDisabled',
                           'ExtensionInstallTypeBlocklist',
                           'GlobalPrivacyControlEnabled',
                           'MetricsReportingEnabled',
                           'RemoteDebuggingAllowed',
                           'SpellCheckServiceEnabled',
                           'UrlKeyedAnonymizedDataCollectionEnabled'],
                          {'DefaultPopupsSetting': 'Block',
                           'PaymentMethodQueryEnabled': 'Block',
                           'DefaultSensorsSetting': 'Block'},
                          'On',
                          'Automatic'),
     'Developer': (['BraveDeAMPEnabled',
                    'BraveDebouncingEnabled',
                    'BraveLocalAiEnabled',
                    'BraveNewsDisabled',
                    'BravePlaylistEnabled',
                    'BraveRewardsDisabled',
                    'BraveWalletDisabled',
                    'SpellCheckServiceEnabled'],
                   {},
                   'On',
                   ''),
     'Brave Origin': (['BraveAIChatEnabled',
                       'BraveEmailAliasesEnabled',
                       'BraveLocalAiEnabled',
                       'BraveNewsDisabled',
                       'BraveP3AEnabled',
                       'BravePlaylistEnabled',
                       'BraveRewardsDisabled',
                       'BraveSpeedreaderEnabled',
                       'BraveStatsPingEnabled',
                       'BraveTalkDisabled',
                       'BraveWalletDisabled',
                       'BraveWaybackMachineEnabled',
                       'BraveWebDiscoveryEnabled',
                       'TorDisabled'],
                      {},
                      '',
                      '')}
    FAMILY_DOH = "https://family.cloudflare-dns.com/dns-query{?dns}"

    def preset_tooltip(text, key, permission=False):
        description = text.split("\n\nSuggested Settings", 1)[0]
        def choice(name):
            features, perms, _, _ = PRESETS[name]
            if key == "SafeBrowsing":
                return PRESETS[name][2] or "Not Set"
            if key == "DnsMode":
                return PRESETS[name][3] or "Not Set"
            if is_origin_only and key in compiled_out_keys:
                return "Unticked (not managed on Origin-only installs)"
            if permission:
                return perms.get(key, "Not Set")
            return "Ticked" if key in features else "Unticked"
        reference = f"Suggested Settings for Privacy: {choice('Maximum Privacy')} | Security: {choice('High Security')}"
        states = "\n".join(f"{name}: {choice(name)}" for name in PRESETS)
        return f"{description}\n\n{reference}\n\nPreset selections:\n{states}"

    def apply_preset(preset_type):
        nonlocal suspend_dirty_tracking, preset_preview
        if preset_type not in PRESETS:
            return
        features, permissions, safe_browsing, dns_mode = PRESETS[preset_type]
        before = {key for key, var in all_feature_vars.items() if var.get()}
        selected = {key for key in features if not (is_origin_only and key in compiled_out_keys)}
        preset_preview = (before & selected, before | selected, selected)
        suspend_dirty_tracking = True
        try:
            for key, var in all_feature_vars.items():
                var.set(int(key in features and not (is_origin_only and key in compiled_out_keys)))
            for key, var in all_perm_vars.items():
                var.set(permissions.get(key, "Not Set"))
            sb_var.set(safe_browsing)
            dns_var.set(dns_mode)
            dns_tpl_var.set(FAMILY_DOH if dns_mode == "Secure" else "")
        finally:
            suspend_dirty_tracking = False
        refresh_preset_colors()
        check_dirty_state()
        set_status(f"{preset_type} preview: green = added, blue = kept, red = unticked. Apply to save.")

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
    create_tooltip(chan_cb, "Select which installed Brave release channel you would like to target for clearing caches and processes. Note: Linux applies the JSON policy universally to all installed Brave channels.")

    tk.Label(inner_top, text="Presets:", font=("sans-serif", 12, "bold"), fg="#87CEFA", bg="#191919").pack(side="left", padx=(10, 5))

    preset_var = tk.StringVar(value="Maximum Privacy")
    
    def on_preset_change(*args):
        apply_preset(preset_var.get())
        
    preset_var.trace_add("write", on_preset_change)
    
    preset_cb = ttk.Combobox(inner_top, textvariable=preset_var, values=["Maximum Privacy", "High Security", "Performance Focused", "Strict Parental Controls", "Balanced Privacy", "Developer", "Brave Origin"], state="readonly", width=22, style="Dark.TCombobox")
    preset_cb.pack(side="left", padx=5)
    create_tooltip(preset_cb, "Select a preset to automatically configure recommended settings.")

    save_status_label = tk.Label(inner_top, textvariable=save_status_var, bg="#191919", fg="#90EE90", font=("sans-serif", 10, "bold"))
    save_status_label.pack(side="right", padx=(50, 0))

    class ScrollableFrame(tk.Frame):
        def __init__(self, parent, bg, **kwargs):
            super().__init__(parent, bg=bg, **kwargs)
            self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
            self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._scrollbar_view, style="Dark.Vertical.TScrollbar")
            self.inner_frame = tk.Frame(self.canvas, bg=bg)

            self.canvas.configure(yscrollcommand=self.scrollbar.set)
            self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

            self.inner_frame.bind("<Configure>", self._on_inner_configure)
            self.canvas.bind("<Configure>", self._on_canvas_configure)

            self.scrollbar.pack(side="right", fill="y")
            self.canvas.pack(side="left", fill="both", expand=True)

            self._bind_mousewheel(self.canvas)

        def _has_overflow(self):
            bounds = self.canvas.bbox(self.canvas_window)
            return bool(bounds and bounds[3] > self.canvas.winfo_height())

        def _sync_scrollregion(self):
            canvas = self.canvas
            bounds = canvas.bbox(self.canvas_window)
            if not bounds:
                return
            canvas.configure(scrollregion=(0, 0, canvas.winfo_width(),
                                           max(bounds[3], canvas.winfo_height())))
            if not self._has_overflow():
                canvas.yview_moveto(0)

        def _on_inner_configure(self, event):
            self._sync_scrollregion()

        def _on_canvas_configure(self, event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)
            self._sync_scrollregion()

        def _scrollbar_view(self, *args):
            if self._has_overflow():
                self.canvas.yview(*args)

        def _on_mousewheel(self, event):
            if event.num == 4:
                delta = -1
            elif event.num == 5:
                delta = 1
            else:
                delta = -int(event.delta / 120) if event.delta else 0
            self.scroll(delta)
            return "break"

        def _bind_mousewheel(self, widget):
            widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
            widget.bind("<Button-4>", self._on_mousewheel, add="+")
            widget.bind("<Button-5>", self._on_mousewheel, add="+")
            for child in widget.winfo_children():
                self._bind_mousewheel(child)

        def bind_children(self):
            self._bind_mousewheel(self.inner_frame)

        def scroll(self, delta):
            if delta and self._has_overflow():
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
            row = tk.Frame(parent, bg="#232323")
            row.pack(anchor="w", padx=16, pady=1)
            cb = ttk.Checkbutton(row, text=feat["Name"], variable=var)
            cb.pack(side="left")
            marker = tk.Label(row, text="(?)", bg="#232323", padx=0, pady=0,
                              font=("sans-serif", 9))
            feature_widgets[feat["Key"]] = (cb, marker, create_tooltip(marker, ""))
            var.trace_add("write", refresh_preset_colors)
            create_tooltip(cb, preset_tooltip(feat["ToolTip"], feat["Key"]))

    populate_checkboxes(left_panel, "Telemetry and Reporting", telemetry_features)
    populate_checkboxes(left_panel, "Privacy and Security", privacy_features)
    populate_checkboxes(mid_panel, "Brave Features", brave_features)
    populate_checkboxes(mid_panel, "Performance and Bloat", perf_features)
    populate_checkboxes(right_panel, "Permissions & Access", access_features)
    
    def enforce_mutually_exclusive(key1, key2):
        def trace_func(*args, trigger=None):
            if all_feature_vars[key1].get() == 1 and all_feature_vars[key2].get() == 1:
                if trigger == key1:
                    all_feature_vars[key2].set(0)
                else:
                    all_feature_vars[key1].set(0)
        all_feature_vars[key1].trace_add("write", lambda *a: trace_func(*a, trigger=key1))
        all_feature_vars[key2].trace_add("write", lambda *a: trace_func(*a, trigger=key2))
        
    enforce_mutually_exclusive("HardwareAccelerationModeEnabled_Force", "HardwareAccelerationModeEnabled_Disable")

    tk.Label(right_panel, text="Site Default Permissions", font=("sans-serif", 11, "bold"), fg="#FFA07A", bg="#232323").pack(anchor="w", pady=(12, 6), padx=12)

    for perm in permission_settings:
        frame = tk.Frame(right_panel, bg="#232323")
        frame.pack(fill="x", padx=16, pady=1)
        lbl = tk.Label(frame, text=perm["Name"], fg="white", bg="#232323", width=16, anchor="w", font=("sans-serif", 9))
        lbl.pack(side="left")
        create_tooltip(lbl, preset_tooltip(perm["ToolTip"], perm["Key"], permission=True))

        var = tk.StringVar(value="Not Set")
        all_perm_vars[perm["Key"]] = var
        var.trace_add("write", check_dirty_state)
        cb = ttk.Combobox(frame, textvariable=var, values=perm["Options"], state="readonly", width=10, style="Dark.TCombobox")
        cb.pack(side="right")
        create_tooltip(cb, preset_tooltip(perm["ToolTip"], perm["Key"], permission=True))

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
    sb_tt = preset_tooltip("On uses Standard Safe Browsing. Off removes phishing and malware warnings. Not Set leaves the browser default.", "SafeBrowsing")
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
    dns_tt = preset_tooltip("Automatic can fall back to unencrypted DNS. Secure requires a trusted DoH endpoint. Off disables browser DoH, not system DNS encryption.", "DnsMode")
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

    ttk.Button(btn_frame, text="Export Settings", style="Export.TButton", command=export_settings).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Import Settings", style="Import.TButton", command=import_settings).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Pull Settings from Brave", style="Reload.TButton", command=reload_ui_from_registry).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Apply Settings", style="Apply.TButton", command=apply_settings).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="Reset All Settings", style="Reset.TButton", command=reset_settings).pack(side="left", expand=True, padx=5)

    status_label = tk.Label(bottom_bar, textvariable=status_var, bg="#2d2d2d", fg="#aaaaaa", font=("courier", 10), anchor="w", padx=10)
    status_label.pack(side="bottom", fill="x")

    root.after(100, reload_ui_from_registry)
    root.mainloop()

if __name__ == "__main__":
    if os.geteuid() == 0:
        sys.exit("Run SlimBrave as your desktop user; it elevates system policy operations as needed.")
    dependency_setup()
    main()
