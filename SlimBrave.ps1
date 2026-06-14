# Slimbrave - Revived - v1.0.9

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell -ArgumentList "-File `"$($MyInvocation.MyCommand.Path)`"" -Verb RunAs
    exit
}

if (-not ("DPI" -as [type])) {
    try {
        Add-Type -TypeDefinition @"
        using System;
        using System.Runtime.InteropServices;
        public class DPI {
            [DllImport("user32.dll")]
            public static extern bool SetProcessDPIAware();
        }
"@
        [void][DPI]::SetProcessDPIAware()
        [System.Windows.Forms.Application]::EnableVisualStyles()
    } catch { }
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$registryPath = "HKLM:\SOFTWARE\Policies\BraveSoftware\Brave"
$logFile = Join-Path $PSScriptRoot "SlimBrave.log"
$stateFile = Join-Path $PSScriptRoot "SlimBraveState.json"

$global:isDirty = $false
$global:suspendDirtyTracking = $false

function Write-Log ($message) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $message" | Out-File -FilePath $logFile -Append
}

if (-not (Test-Path -Path $registryPath)) {
    [void](New-Item -Path $registryPath -Force)
    Write-Log "Created new Brave Policy registry key."
}

Clear-Host

$form = New-Object System.Windows.Forms.Form
$form.Text = "SlimBrave - Revived v1.0.9"
$form.ForeColor = [System.Drawing.Color]::White
$form.Size = New-Object System.Drawing.Size(1300, 850) 
$form.MinimumSize = New-Object System.Drawing.Size(1300, 850)
$form.MaximumSize = New-Object System.Drawing.Size([int](1300 * 1.25), [int](850 * 1.25)) 
$form.StartPosition = "CenterScreen"
$form.BackColor = [System.Drawing.Color]::FromArgb(255, 25, 25, 25)
$form.MaximizeBox = $true
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::Sizable

$allFeatures = @()
$allPerms = @()
$toolTip = New-Object System.Windows.Forms.ToolTip
$boldFont = New-Object System.Drawing.Font("Microsoft Sans Serif", 9.5, [System.Drawing.FontStyle]::Bold)

$statusBar = New-Object System.Windows.Forms.Label
$statusBar.Height = 30
$statusBar.Dock = [System.Windows.Forms.DockStyle]::Bottom
$statusBar.BackColor = [System.Drawing.Color]::FromArgb(255, 20, 20, 20)
$statusBar.ForeColor = [System.Drawing.Color]::DarkGray
$statusBar.Font = New-Object System.Drawing.Font("Consolas", 9, [System.Drawing.FontStyle]::Regular)
$statusBar.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$statusBar.Text = "Ready. Hover over options for details."
$form.Controls.Add($statusBar)

$statusPanel = New-Object System.Windows.Forms.Panel
$statusPanel.Size = New-Object System.Drawing.Size(260, 32)
$statusPanel.BackColor = [System.Drawing.Color]::FromArgb(255, 18, 18, 18)
$form.Controls.Add($statusPanel)

$saveStatusLabel = New-Object System.Windows.Forms.Label
$saveStatusLabel.Dock = [System.Windows.Forms.DockStyle]::Fill
$saveStatusLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$saveStatusLabel.Font = New-Object System.Drawing.Font("Microsoft Sans Serif", 9, [System.Drawing.FontStyle]::Bold)
$statusPanel.Controls.Add($saveStatusLabel)

function Set-DirtyState([bool]$dirty) {
    if ($global:suspendDirtyTracking) { return }
    $global:isDirty = $dirty
    if ($dirty) {
        $saveStatusLabel.Text = "Changes Need To Be Saved....."
        $saveStatusLabel.ForeColor = [System.Drawing.Color]::Gold
    } else {
        $saveStatusLabel.Text = "Changes Applied ✔"
        $saveStatusLabel.ForeColor = [System.Drawing.Color]::LightGreen
    }
    $statusPanel.Refresh()
}

function Update-Status ($text) {
    $statusBar.Text = $text
    $form.Refresh()
    Write-Log $text
}

function Set-DnsMode {
    param ([string] $dnsMode)
    $regKey = "HKLM:\Software\Policies\BraveSoftware\Brave"
    [void](Set-ItemProperty -Path $regKey -Name "DnsOverHttpsMode" -Value $dnsMode -Type String -Force)
    Update-Status "DNS Over HTTPS Mode set to $dnsMode"
}

function Set-RoundedCorners($ctrl, $r) {
    if ($ctrl.Width -le 0 -or $ctrl.Height -le 0) { return }
    $d = $r * 2
    $p = New-Object System.Drawing.Drawing2D.GraphicsPath
    $p.AddArc(0, 0, $d, $d, 180, 90)
    $p.AddArc($ctrl.Width - $d, 0, $d, $d, 270, 90)
    $p.AddArc($ctrl.Width - $d, $ctrl.Height - $d, $d, $d, 0, 90)
    $p.AddArc(0, $ctrl.Height - $d, $d, $d, 90, 90)
    $p.CloseFigure()
    $ctrl.Region = New-Object System.Drawing.Region($p)
}

$presetLabel = New-Object System.Windows.Forms.Label
$presetLabel.Text = "Quick Toggles:"
$presetLabel.AutoSize = $true
$presetLabel.Font = New-Object System.Drawing.Font("Microsoft Sans Serif", 9, [System.Drawing.FontStyle]::Bold)
$presetLabel.ForeColor = [System.Drawing.Color]::LightSkyBlue
$form.Controls.Add($presetLabel)

$btnPrivacy = New-Object System.Windows.Forms.Button
$btnPrivacy.Text = "High Privacy + Moderate Security"
$btnPrivacy.Size = New-Object System.Drawing.Size(280, 35)
$btnPrivacy.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$btnPrivacy.FlatAppearance.BorderSize = 0
$btnPrivacy.BackColor = [System.Drawing.Color]::FromArgb(255, 60, 60, 60)
$toolTip.SetToolTip($btnPrivacy, "Applies the recommended preset for High Privacy and Moderate Security.")
$form.Controls.Add($btnPrivacy)

$btnSecurity = New-Object System.Windows.Forms.Button
$btnSecurity.Text = "High Security + Moderate Privacy"
$btnSecurity.Size = New-Object System.Drawing.Size(280, 35)
$btnSecurity.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$btnSecurity.FlatAppearance.BorderSize = 0
$btnSecurity.BackColor = [System.Drawing.Color]::FromArgb(255, 60, 60, 60)
$toolTip.SetToolTip($btnSecurity, "Applies the recommended preset for High Security and Moderate Privacy.")
$form.Controls.Add($btnSecurity)

$leftPanel = New-Object System.Windows.Forms.Panel
$leftPanel.BackColor = [System.Drawing.Color]::FromArgb(255, 35, 35, 35)
$leftPanel.BorderStyle = [System.Windows.Forms.BorderStyle]::None
$leftPanel.AutoScroll = $true 
$form.Controls.Add($leftPanel)

$telemetryLabel = New-Object System.Windows.Forms.Label
$telemetryLabel.Text = "Telemetry & Reporting"
$telemetryLabel.Font = New-Object System.Drawing.Font("Microsoft Sans Serif", 10.5, [System.Drawing.FontStyle]::Bold)
$telemetryLabel.Location = New-Object System.Drawing.Point(28, 10)
$telemetryLabel.Size = New-Object System.Drawing.Size(300, 20)
$telemetryLabel.ForeColor = [System.Drawing.Color]::LightSalmon
$leftPanel.Controls.Add($telemetryLabel)

$telemetryFeatures = @(
    @{ Name = "Disable Metrics Reporting"; Key = "MetricsReportingEnabled"; Value = 0; Type = "DWord"; ToolTip = "Stops Brave from sending anonymous usage and crash reports.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Safe Browsing Reporting"; Key = "SafeBrowsingExtendedReportingEnabled"; Value = 0; Type = "DWord"; ToolTip = "Stops Brave from sending extended Safe Browsing data back to servers.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable URL Data Collection"; Key = "UrlKeyedAnonymizedDataCollectionEnabled"; Value = 0; Type = "DWord"; ToolTip = "Stops sending anonymized URLs to help improve the browser.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Feedback Surveys"; Key = "FeedbackSurveysEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables proactive feedback survey prompts.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable P3A Telemetry"; Key = "BraveP3AEnabled"; Value = "Disabled"; Type = "String"; ToolTip = "Disables Privacy-Preserving Product Analytics completely.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Daily Stats Ping"; Key = "BraveStatsPingEnabled"; Value = 0; Type = "DWord"; ToolTip = "Stops the daily active user ping.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Web Discovery"; Key = "BraveWebDiscoveryEnabled"; Value = 0; Type = "DWord"; ToolTip = "Prevents anonymous search/browsing data from being sent to Brave Search.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" }
)

[int]$leftY = 35
foreach ($feature in $telemetryFeatures) {
    $checkbox = New-Object System.Windows.Forms.CheckBox
    $checkbox.Text = $feature.Name
    $checkbox.Tag = $feature
    $checkbox.Location = New-Object System.Drawing.Point(30, $leftY)
    $checkbox.Size = New-Object System.Drawing.Size(340, 25) 
    $checkbox.Anchor = [System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Left
    $checkbox.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
    $checkbox.FlatAppearance.BorderSize = 1
    $checkbox.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(255, 80, 80, 80)
    $checkbox.FlatAppearance.CheckedBackColor = [System.Drawing.Color]::DodgerBlue
    $checkbox.Add_CheckedChanged({
        if ($this.Checked) {
            $this.ForeColor = [System.Drawing.Color]::DeepSkyBlue
        } else {
            $this.ForeColor = [System.Drawing.Color]::White
        }
        Check-DirtyState
    })
    $toolTip.SetToolTip($checkbox, $feature.ToolTip)
    $leftPanel.Controls.Add($checkbox)
    $allFeatures += $checkbox
    $leftY += 28
}

$leftY += 10

$privacyLabel = New-Object System.Windows.Forms.Label
$privacyLabel.Text = "Privacy & Security"
$privacyLabel.Font = New-Object System.Drawing.Font("Microsoft Sans Serif", 11, [System.Drawing.FontStyle]::Bold)
$privacyLabel.Location = New-Object System.Drawing.Point(28, $leftY)
$privacyLabel.Size = New-Object System.Drawing.Size(300, 20)
$privacyLabel.ForeColor = [System.Drawing.Color]::LightSalmon
$leftPanel.Controls.Add($privacyLabel)
$leftY += 25

$privacyFeatures = @(
    @{ Name = "Disable Autofill (Addresses)"; Key = "AutofillAddressEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables saving and autofilling addresses.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable Autofill (Credit Cards)"; Key = "AutofillCreditCardEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables saving and autofilling credit cards.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable Password Manager"; Key = "PasswordManagerEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables the built-in password manager.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable Browser Sign-in"; Key = "BrowserSignin"; Value = 0; Type = "DWord"; ToolTip = "Prevents syncing your data to cloud accounts.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable WebRTC IP Leak"; Key = "WebRtcIPHandling"; Value = "disable_non_proxied_udp"; Type = "String"; ToolTip = "Prevents your real IP address from leaking when using a VPN.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable QUIC Protocol"; Key = "QuicAllowed"; Value = 0; Type = "DWord"; ToolTip = "Forces standard TCP, stopping UDP firewall bypasses and tracking.`n`nSuggested Settings for Privacy: Unticked | Security: Ticked" },
    @{ Name = "Block Third Party Cookies"; Key = "BlockThirdPartyCookies"; Value = 1; Type = "DWord"; ToolTip = "Blocks all third-party tracking cookies.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Enable Do Not Track"; Key = "EnableDoNotTrack"; Value = 1; Type = "DWord"; ToolTip = "Sends a Do Not Track request with your browsing traffic.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Force Google SafeSearch"; Key = "ForceGoogleSafeSearch"; Value = 1; Type = "DWord"; ToolTip = "Filters explicit search results.`n`nSuggested Settings for Privacy: Unticked | Security: Ticked" },
    @{ Name = "Disable IPFS"; Key = "IPFSEnabled"; Value = 0; Type = "DWord"; ToolTip = "Stops peer-to-peer background connections to unknown nodes.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Force Incognito Mode"; Key = "IncognitoModeAvailability"; Value = 2; Type = "DWord"; ToolTip = "Forces the browser to always open in Incognito Mode.`n`nSuggested Settings for Privacy: Unticked | Security: Unticked" },
    @{ Name = "Force Download Prompts"; Key = "PromptForDownloadLocation"; Value = 1; Type = "DWord"; ToolTip = "Forces Brave to ask where to save a file before downloading, preventing drive-by downloads.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Clear Data on Exit"; Key = "ClearBrowsingDataOnExitList"; Value = @("browsing_history", "download_history", "cookies_and_other_site_data", "cached_images_and_files", "password_signin", "autofill", "site_settings", "hosted_app_data"); Type = "List"; ToolTip = "Wipes all cookies, cache, and browsing history the moment the browser closes.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Force HTTPS-Only Mode"; Key = "HttpsOnlyMode"; Value = "force_enabled"; Type = "String"; ToolTip = "Strictly upgrades all connections to HTTPS and blocks unencrypted HTTP traffic.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" }
)

foreach ($feature in $privacyFeatures) {
    $checkbox = New-Object System.Windows.Forms.CheckBox
    $checkbox.Text = $feature.Name
    $checkbox.Tag = $feature
    $checkbox.Location = New-Object System.Drawing.Point(30, $leftY)
    $checkbox.Size = New-Object System.Drawing.Size(340, 25)
    $checkbox.Anchor = [System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Left
    $checkbox.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
    $checkbox.FlatAppearance.BorderSize = 1
    $checkbox.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(255, 80, 80, 80)
    $checkbox.FlatAppearance.CheckedBackColor = [System.Drawing.Color]::DodgerBlue
    $checkbox.Add_CheckedChanged({
        if ($this.Checked) {
            $this.ForeColor = [System.Drawing.Color]::DeepSkyBlue
        } else {
            $this.ForeColor = [System.Drawing.Color]::White
        }
        Check-DirtyState
    })
    $toolTip.SetToolTip($checkbox, $feature.ToolTip)
    $leftPanel.Controls.Add($checkbox)
    $allFeatures += $checkbox
    $leftY += 28
}

$leftPad = New-Object System.Windows.Forms.Label
$leftPad.Location = New-Object System.Drawing.Point(0, $leftY)
$leftPad.Size = New-Object System.Drawing.Size(10, 40)
[void]$leftPanel.Controls.Add($leftPad)

$midPanel = New-Object System.Windows.Forms.Panel
$midPanel.BackColor = [System.Drawing.Color]::FromArgb(255, 35, 35, 35)
$midPanel.BorderStyle = [System.Windows.Forms.BorderStyle]::None
$midPanel.AutoScroll = $true 
$form.Controls.Add($midPanel)

[int]$midY = 10

$braveLabel = New-Object System.Windows.Forms.Label
$braveLabel.Text = "Brave Features"
$braveLabel.Font = New-Object System.Drawing.Font("Microsoft Sans Serif", 11, [System.Drawing.FontStyle]::Bold)
$braveLabel.Location = New-Object System.Drawing.Point(28, $midY)
$braveLabel.Size = New-Object System.Drawing.Size(300, 20)
$braveLabel.ForeColor = [System.Drawing.Color]::LightSalmon
$midPanel.Controls.Add($braveLabel)
$midY += 25

$braveFeatures = @(
    @{ Name = "Disable Rewards & Sponsored BGs"; Key = "BraveRewardsDisabled"; Value = 1; Type = "DWord"; ToolTip = "Completely disables the Brave Crypto Rewards system and Sponsored Background Images on the New Tab page.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Brave Wallet"; Key = "BraveWalletDisabled"; Value = 1; Type = "DWord"; ToolTip = "Disables the built-in Brave Crypto Wallet.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Brave VPN"; Key = "BraveVPNDisabled"; Value = 1; Type = "DWord"; ToolTip = "Removes the Brave VPN integration and prompts.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Brave AI Chat"; Key = "BraveAIChatEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables Brave Leo (AI Chat) integration.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Tor"; Key = "TorDisabled"; Value = 1; Type = "DWord"; ToolTip = "Disables built-in Tor window support.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Sync"; Key = "SyncDisabled"; Value = 1; Type = "DWord"; ToolTip = "Disables Brave Sync functionality across devices.`n`nSuggested Settings for Privacy: Unticked | Security: Ticked" },
    @{ Name = "Disable Brave News"; Key = "BraveNewsDisabled"; Value = 1; Type = "DWord"; ToolTip = "Removes the Brave News feed bloat from the New Tab page.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Brave Talk"; Key = "BraveTalkDisabled"; Value = "Disabled"; Type = "String"; ToolTip = "Removes the built-in video calling integration.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Speedreader"; Key = "BraveSpeedreaderEnabled"; Value = 0; Type = "DWord"; ToolTip = "Completely disables the Speedreader feature, reader mode, and automatic prompts.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Wayback Machine Prompts"; Key = "BraveWaybackMachineEnabled"; Value = 0; Type = "DWord"; ToolTip = "Stops Brave from asking to search the Internet Archive when you hit a 404 error.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" }
)

foreach ($feature in $braveFeatures) {
    $checkbox = New-Object System.Windows.Forms.CheckBox
    $checkbox.Text = $feature.Name
    $checkbox.Tag = $feature
    $checkbox.Location = New-Object System.Drawing.Point(30, $midY)
    $checkbox.Size = New-Object System.Drawing.Size(340, 25)
    $checkbox.Anchor = [System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Left
    $checkbox.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
    $checkbox.FlatAppearance.BorderSize = 1
    $checkbox.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(255, 80, 80, 80)
    $checkbox.FlatAppearance.CheckedBackColor = [System.Drawing.Color]::DodgerBlue
    $checkbox.Add_CheckedChanged({
        if ($this.Checked) {
            $this.ForeColor = [System.Drawing.Color]::DeepSkyBlue
        } else {
            $this.ForeColor = [System.Drawing.Color]::White
        }
        Check-DirtyState
    })
    $toolTip.SetToolTip($checkbox, $feature.ToolTip)
    $midPanel.Controls.Add($checkbox)
    $allFeatures += $checkbox
    $midY += 28
}

$midY += 10

$perfLabel = New-Object System.Windows.Forms.Label
$perfLabel.Text = "Performance & Bloat"
$perfLabel.Font = New-Object System.Drawing.Font("Microsoft Sans Serif", 11, [System.Drawing.FontStyle]::Bold)
$perfLabel.Location = New-Object System.Drawing.Point(28, $midY)
$perfLabel.Size = New-Object System.Drawing.Size(300, 20)
$perfLabel.ForeColor = [System.Drawing.Color]::LightSalmon
$midPanel.Controls.Add($perfLabel)
$midY += 25

$perfFeatures = @(
    @{ Name = "Disable Background Mode"; Key = "BackgroundModeEnabled"; Value = 0; Type = "DWord"; ToolTip = "Prevents extensions/apps from running after the browser is closed.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Media Recommendations"; Key = "MediaRecommendationsEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables media recommendations to save memory.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable Shopping List"; Key = "ShoppingListEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables the shopping list feature.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Always Open PDF Externally"; Key = "AlwaysOpenPdfExternally"; Value = 1; Type = "DWord"; ToolTip = "Forces PDFs to download and open in your system viewer instead of the browser.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Translate"; Key = "TranslateEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables automatic translation prompts.`n`nSuggested Settings for Privacy: Unticked | Security: Unticked" },
    @{ Name = "Disable Spellcheck"; Key = "SpellcheckEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables the built-in spellchecker to save CPU cycles.`n`nSuggested Settings for Privacy: Unticked | Security: Unticked" },
    @{ Name = "Disable Promotions"; Key = "PromotionsEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables Brave promotional notifications.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable Search Suggestions"; Key = "SearchSuggestEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables predictive search suggestions in the URL bar.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable Printing"; Key = "PrintingEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables the browser print function.`n`nSuggested Settings for Privacy: Unticked | Security: Unticked" },
    @{ Name = "Disable Default Browser Prompt"; Key = "DefaultBrowserSettingEnabled"; Value = 0; Type = "DWord"; ToolTip = "Stops Brave from asking to be the default browser.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable Developer Tools"; Key = "DeveloperToolsDisabled"; Value = 1; Type = "DWord"; ToolTip = "Disables F12 / Inspect Element.`n`nSuggested Settings for Privacy: Unticked | Security: Ticked" },
    @{ Name = "Disable Brave Playlist"; Key = "BravePlaylistEnabled"; Value = 0; Type = "DWord"; ToolTip = "Removes the Brave Playlist media feature.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" }
)

foreach ($feature in $perfFeatures) {
    $checkbox = New-Object System.Windows.Forms.CheckBox
    $checkbox.Text = $feature.Name
    $checkbox.Tag = $feature
    $checkbox.Location = New-Object System.Drawing.Point(30, $midY)
    $checkbox.Size = New-Object System.Drawing.Size(340, 25)
    $checkbox.Anchor = [System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Left
    $checkbox.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
    $checkbox.FlatAppearance.BorderSize = 1
    $checkbox.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(255, 80, 80, 80)
    $checkbox.FlatAppearance.CheckedBackColor = [System.Drawing.Color]::DodgerBlue
    $checkbox.Add_CheckedChanged({
        if ($this.Checked) {
            $this.ForeColor = [System.Drawing.Color]::DeepSkyBlue
        } else {
            $this.ForeColor = [System.Drawing.Color]::White
        }
        Check-DirtyState
    })
    $toolTip.SetToolTip($checkbox, $feature.ToolTip)
    $midPanel.Controls.Add($checkbox)
    $allFeatures += $checkbox
    $midY += 28
}

$midPad = New-Object System.Windows.Forms.Label
$midPad.Location = New-Object System.Drawing.Point(0, $midY)
$midPad.Size = New-Object System.Drawing.Size(10, 40)
[void]$midPanel.Controls.Add($midPad)

$rightPanel = New-Object System.Windows.Forms.Panel
$rightPanel.BackColor = [System.Drawing.Color]::FromArgb(255, 35, 35, 35)
$rightPanel.BorderStyle = [System.Windows.Forms.BorderStyle]::None
$rightPanel.AutoScroll = $true 
$form.Controls.Add($rightPanel)

[int]$permY = 10

$permLabel = New-Object System.Windows.Forms.Label
$permLabel.Text = "Site Permissions"
$permLabel.Font = New-Object System.Drawing.Font("Microsoft Sans Serif", 11, [System.Drawing.FontStyle]::Bold)
$permLabel.Location = New-Object System.Drawing.Point(28, $permY)
$permLabel.Size = New-Object System.Drawing.Size(300, 20)
$permLabel.ForeColor = [System.Drawing.Color]::LightSalmon
$rightPanel.Controls.Add($permLabel)
$permY += 30

$permissionSettings = @(
    @{ Name = "Location"; Key = "DefaultGeolocationSetting"; Options = @("Not Set", "Ask", "Block", "Allow"); ToolTip = "Allows sites to request your physical location.`n`nSuggested Settings for Privacy: Ask | Security: Ask" },
    @{ Name = "Camera"; Key = "DefaultVideoCaptureSetting"; Options = @("Not Set", "Ask", "Block"); ToolTip = "Allows sites to record video via your webcam.`n`nSuggested Settings for Privacy: Ask | Security: Ask" },
    @{ Name = "Microphone"; Key = "DefaultAudioCaptureSetting"; Options = @("Not Set", "Ask", "Block"); ToolTip = "Allows sites to record audio via your microphone.`n`nSuggested Settings for Privacy: Ask | Security: Ask" },
    @{ Name = "Notifications"; Key = "DefaultNotificationsSetting"; Options = @("Not Set", "Ask", "Block", "Allow"); ToolTip = "Allows sites to send you native desktop push notifications.`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "JavaScript"; Key = "DefaultJavaScriptSetting"; Options = @("Not Set", "Allow", "Block"); ToolTip = "Allows sites to run interactive scripts. Blocking this breaks almost all websites.`n`nSuggested Settings for Privacy: Allow | Security: Allow" },
    @{ Name = "Images"; Key = "DefaultImagesSetting"; Options = @("Not Set", "Allow", "Block"); ToolTip = "Allows sites to load and display images.`n`nSuggested Settings for Privacy: Not Set | Security: Not Set" },
    @{ Name = "Pop-ups & Redirects"; Key = "DefaultPopupsSetting"; Options = @("Not Set", "Block", "Allow"); ToolTip = "Allows sites to open new windows or redirect you without your input.`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "USB Devices"; Key = "DefaultWebUsbGuardSetting"; Options = @("Not Set", "Ask", "Block"); ToolTip = "Allows sites to request direct connection to your plugged-in USB devices.`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "Serial Ports"; Key = "DefaultSerialGuardSetting"; Options = @("Not Set", "Ask", "Block"); ToolTip = "Allows sites to request connection to hardware via serial ports.`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "HID Devices"; Key = "DefaultWebHidGuardSetting"; Options = @("Not Set", "Ask", "Block"); ToolTip = "Allows sites to request access to Human Interface Devices (e.g. controllers).`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "File Editing"; Key = "DefaultFileSystemReadGuardSetting"; Options = @("Not Set", "Ask", "Block"); ToolTip = "Allows sites to read and save files directly to your local file system.`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "Clipboard"; Key = "DefaultClipboardSetting"; Options = @("Not Set", "Ask", "Block"); ToolTip = "Allows sites to read text and images copied to your clipboard.`n`nSuggested Settings for Privacy: Ask | Security: Ask" },
    @{ Name = "Window Management"; Key = "DefaultWindowPlacementSetting"; Options = @("Not Set", "Ask", "Block", "Allow"); ToolTip = "Allows sites to open windows on specific monitors or in fullscreen.`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "Local Fonts"; Key = "DefaultLocalFontsSetting"; Options = @("Not Set", "Ask", "Block"); ToolTip = "Allows sites to fingerprint your device based on locally installed fonts.`n`nSuggested Settings for Privacy: Ask | Security: Ask" },
    @{ Name = "Payment Handlers"; Key = "PaymentMethodQueryEnabled"; Options = @("Not Set", "Block", "Allow"); ToolTip = "Allows sites to check if you have local payment apps installed.`n`nSuggested Settings for Privacy: Block | Security: Block" }
)

foreach ($p in $permissionSettings) {
    $lbl = New-Object System.Windows.Forms.Label
    $lbl.Text = $p.Name
    $lbl.Size = New-Object System.Drawing.Size(165, 20)
    $lbl.Location = New-Object System.Drawing.Point(30, $permY)
    $lbl.ForeColor = [System.Drawing.Color]::White
    $toolTip.SetToolTip($lbl, $p.ToolTip)
    [void]$rightPanel.Controls.Add($lbl)

    $cb = New-Object System.Windows.Forms.ComboBox
    $cb.Tag = $p
    $cb.DropDownStyle = [System.Windows.Forms.ComboBoxStyle]::DropDownList
    [void]$cb.Items.AddRange($p.Options)
    $cb.SelectedIndex = 0
    $cb.Size = New-Object System.Drawing.Size(130, 20)
    $cb.Location = New-Object System.Drawing.Point(200, [int]($permY - 3))
    $cb.BackColor = [System.Drawing.Color]::FromArgb(255, 45, 45, 45)
    $cb.ForeColor = [System.Drawing.Color]::White
    $cb.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
    $cb.Add_SelectedIndexChanged({ Check-DirtyState })
    $toolTip.SetToolTip($cb, $p.ToolTip)
    [void]$rightPanel.Controls.Add($cb)

    $allPerms += $cb
    $permY += 35
}

$permPad = New-Object System.Windows.Forms.Label
$permPad.Location = New-Object System.Drawing.Point(0, $permY)
$permPad.Size = New-Object System.Drawing.Size(10, 40)
[void]$rightPanel.Controls.Add($permPad)

$sbLabel = New-Object System.Windows.Forms.Label
$sbLabel.Text = "Safe Browsing:"
$sbLabel.Size = New-Object System.Drawing.Size(140, 20)
$form.Controls.Add($sbLabel)

$sbDropdown = New-Object System.Windows.Forms.ComboBox
$sbDropdown.Size = New-Object System.Drawing.Size(150, 20)
[void]$sbDropdown.Items.AddRange(@("On", "Off"))
$sbDropdown.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$sbDropdown.BackColor = [System.Drawing.Color]::FromArgb(255, 25, 25, 25)
$sbDropdown.ForeColor = [System.Drawing.Color]::White
$sbDropdown.Add_SelectedIndexChanged({ Check-DirtyState })
$form.Controls.Add($sbDropdown)

$sbTooltip = "On = Standard Safe Browsing. Off = Disabled entirely.`n`nSuggested Settings for Privacy: Off | Security: On"
$toolTip.SetToolTip($sbDropdown, $sbTooltip)
$toolTip.SetToolTip($sbLabel, $sbTooltip)

$dnsLabel = New-Object System.Windows.Forms.Label
$dnsLabel.Text = "DNS Over HTTPS:"
$dnsLabel.Size = New-Object System.Drawing.Size(140, 20)
$form.Controls.Add($dnsLabel)

$dnsDropdown = New-Object System.Windows.Forms.ComboBox
$dnsDropdown.Size = New-Object System.Drawing.Size(150, 20)
[void]$dnsDropdown.Items.AddRange(@("On", "Off"))
$dnsDropdown.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$dnsDropdown.BackColor = [System.Drawing.Color]::FromArgb(255, 25, 25, 25)
$dnsDropdown.ForeColor = [System.Drawing.Color]::White
$dnsDropdown.Add_SelectedIndexChanged({ Check-DirtyState })
$form.Controls.Add($dnsDropdown)

$dnsTooltip = "Forces encrypted DNS lookups.`n`nSuggested Settings for Privacy: Off | Security: On"
$toolTip.SetToolTip($dnsDropdown, $dnsTooltip)
$toolTip.SetToolTip($dnsLabel, $dnsTooltip)

$exportButton = New-Object System.Windows.Forms.Button
$exportButton.Text = "Export Settings"
$exportButton.Font = $boldFont
$exportButton.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$exportButton.FlatAppearance.BorderSize = 0
$exportButton.BackColor = [System.Drawing.Color]::FromArgb(150, 102, 102, 102)
$exportButton.ForeColor = [System.Drawing.Color]::White
$toolTip.SetToolTip($exportButton, "Export the current UI configuration to a JSON file.")
$form.Controls.Add($exportButton)

$importButton = New-Object System.Windows.Forms.Button
$importButton.Text = "Import Settings"
$importButton.Font = $boldFont
$importButton.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$importButton.FlatAppearance.BorderSize = 0
$importButton.BackColor = [System.Drawing.Color]::FromArgb(150, 102, 102, 102)
$importButton.ForeColor = [System.Drawing.Color]::White
$toolTip.SetToolTip($importButton, "Import a JSON configuration file into the UI.")
$form.Controls.Add($importButton)

$pullButton = New-Object System.Windows.Forms.Button
$pullButton.Text = "Pull Settings from Brave"
$pullButton.Font = $boldFont
$pullButton.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$pullButton.FlatAppearance.BorderSize = 0
$pullButton.BackColor = [System.Drawing.Color]::FromArgb(150, 102, 102, 102)
$pullButton.ForeColor = [System.Drawing.Color]::White
$toolTip.SetToolTip($pullButton, "Pull / Reload the current Brave settings from the registry into the SlimBrave UI.")
$form.Controls.Add($pullButton)

$saveButton = New-Object System.Windows.Forms.Button
$saveButton.Text = "Apply Settings"
$saveButton.Font = $boldFont
$saveButton.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$saveButton.FlatAppearance.BorderSize = 0
$saveButton.BackColor = [System.Drawing.Color]::FromArgb(150, 102, 102, 102)
$saveButton.ForeColor = [System.Drawing.Color]::LightGreen
$toolTip.SetToolTip($saveButton, "Apply the current UI configuration directly to the Windows Registry.")
$form.Controls.Add($saveButton)

$resetButton = New-Object System.Windows.Forms.Button
$resetButton.Text = "Reset All Settings"
$resetButton.Font = $boldFont
$resetButton.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$resetButton.FlatAppearance.BorderSize = 0
$resetButton.BackColor = [System.Drawing.Color]::FromArgb(150, 102, 102, 102)
$resetButton.ForeColor = [System.Drawing.Color]::LightCoral
$toolTip.SetToolTip($resetButton, "Erase all Brave policy settings from the registry and restore to default.")
$form.Controls.Add($resetButton)

$global:baselineStateJson = ""

function Get-UIStateSnapshot {
    $snap = [ordered]@{
        Features = @()
        Permissions = [ordered]@{}
        SafeBrowsing = $sbDropdown.SelectedItem
        DnsMode = $dnsDropdown.SelectedItem
    }
    $fList = @()
    foreach ($checkbox in $allFeatures) {
        if ($checkbox.Checked) {
            $fList += $checkbox.Tag.Key
        }
    }
    $snap.Features = $fList
    
    foreach ($perm in $allPerms) {
        if ($perm.SelectedItem -ne "Not Set") {
            $snap.Permissions[$perm.Tag.Key] = $perm.SelectedItem
        }
    }
    return $snap
}

function Update-Baseline {
    $global:baselineStateJson = Get-UIStateSnapshot | ConvertTo-Json -Depth 3 -Compress
}

function Check-DirtyState {
    if ($global:suspendDirtyTracking) { return }
    $currentJson = Get-UIStateSnapshot | ConvertTo-Json -Depth 3 -Compress
    if ($currentJson -ne $global:baselineStateJson) {
        Set-DirtyState $true
    } else {
        Set-DirtyState $false
    }
}

function Save-CurrentState {
    try {
        Get-UIStateSnapshot | ConvertTo-Json -Depth 3 | Out-File -FilePath $stateFile -Force
        Write-Log "State baseline saved to $stateFile"
    } catch {
        Write-Log "Failed to save state baseline: $_"
    }
}

function Restore-StateToUI ($stateObj) {
    $global:suspendDirtyTracking = $true
    foreach ($checkbox in $allFeatures) {
        $checkbox.Checked = $false
        $checkbox.ForeColor = [System.Drawing.Color]::White
    }

    if ($stateObj.Features) {
        foreach ($featureKey in $stateObj.Features) {
            foreach ($checkbox in $allFeatures) {
                if ($checkbox.Tag.Key -eq $featureKey) {
                    $checkbox.Checked = $true
                    break
                }
            }
        }
    }

    foreach ($perm in $allPerms) { $perm.SelectedItem = "Not Set" }

    if ($stateObj.Permissions -and $stateObj.Permissions.PSObject.Properties) {
        foreach ($prop in $stateObj.Permissions.PSObject.Properties) {
            foreach ($perm in $allPerms) {
                if ($perm.Tag.Key -eq $prop.Name) {
                    $perm.SelectedItem = $prop.Value
                    break
                }
            }
        }
    }

    if ($stateObj.SafeBrowsing) { $sbDropdown.SelectedItem = $stateObj.SafeBrowsing } else { $sbDropdown.SelectedIndex = -1 }
    if ($stateObj.DnsMode) { $dnsDropdown.SelectedItem = $stateObj.DnsMode } else { $dnsDropdown.SelectedIndex = -1 }
    
    $global:suspendDirtyTracking = $false
    Check-DirtyState
}

function Check-StateChanges {
    if (-not (Test-Path $stateFile)) {
        Save-CurrentState
        return
    }

    $savedState = Get-Content -Path $stateFile -Raw | ConvertFrom-Json
    $currentSnap = Get-UIStateSnapshot
    $diffs = @()

    foreach ($f in $allFeatures) {
        $key = $f.Tag.Key
        $name = $f.Tag.Name
        $wasEnabled = ($null -ne $savedState.Features -and $key -in $savedState.Features)
        $isNowEnabled = ($key -in $currentSnap.Features)
        if ($wasEnabled -ne $isNowEnabled) {
            $diffs += "Feature: $name`n  Expected: $(if($wasEnabled){'On'}else{'Off'}) | Found: $(if($isNowEnabled){'On'}else{'Off'})"
        }
    }

    foreach ($perm in $allPerms) {
        $key = $perm.Tag.Key
        $name = $perm.Tag.Name
        $savedVal = "Not Set"
        if ($null -ne $savedState.Permissions -and $null -ne $savedState.Permissions.PSObject.Properties[$key]) {
            $savedVal = $savedState.Permissions.PSObject.Properties[$key].Value
        }
        $currVal = "Not Set"
        if ($null -ne $currentSnap.Permissions[$key]) {
            $currVal = $currentSnap.Permissions[$key]
        }
        if ($savedVal -ne $currVal) {
            $diffs += "Permission: $name`n  Expected: $savedVal | Found: $currVal"
        }
    }

    if ($savedState.SafeBrowsing -ne $currentSnap.SafeBrowsing) {
        $diffs += "Safe Browsing:`n  Expected: $($savedState.SafeBrowsing) | Found: $($currentSnap.SafeBrowsing)"
    }
    if ($savedState.DnsMode -ne $currentSnap.DnsMode) {
        $diffs += "DNS Mode:`n  Expected: $($savedState.DnsMode) | Found: $($currentSnap.DnsMode)"
    }

    if ($diffs.Count -gt 0) {
        $diffForm = New-Object System.Windows.Forms.Form
        $diffForm.Text = "SlimBrave - Background Changes Detected"
        $diffForm.BackColor = [System.Drawing.Color]::FromArgb(255, 25, 25, 25)
        $diffForm.ForeColor = [System.Drawing.Color]::White
        $diffForm.Size = New-Object System.Drawing.Size(650, 480)
        $diffForm.StartPosition = "CenterParent"
        $diffForm.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedDialog
        $diffForm.MaximizeBox = $false

        $lblInfo = New-Object System.Windows.Forms.Label
        $lblInfo.Text = "Brave or your OS has modified policies since you last ran SlimBrave.`nReview the changes below and choose how to proceed:"
        $lblInfo.Font = New-Object System.Drawing.Font("Microsoft Sans Serif", 9.5, [System.Drawing.FontStyle]::Bold)
        $lblInfo.Location = New-Object System.Drawing.Point(20, 15)
        $lblInfo.Size = New-Object System.Drawing.Size(600, 40)
        $diffForm.Controls.Add($lblInfo)

        $lbDiffs = New-Object System.Windows.Forms.ListBox
        $lbDiffs.Location = New-Object System.Drawing.Point(20, 60)
        $lbDiffs.Size = New-Object System.Drawing.Size(590, 300)
        $lbDiffs.BackColor = [System.Drawing.Color]::FromArgb(255, 35, 35, 35)
        $lbDiffs.ForeColor = [System.Drawing.Color]::LightSalmon
        $lbDiffs.Font = New-Object System.Drawing.Font("Consolas", 9.5, [System.Drawing.FontStyle]::Regular)
        $lbDiffs.IntegralHeight = $false
        foreach ($d in $diffs) { 
            foreach($line in $d -split "`n") { [void]$lbDiffs.Items.Add($line) }
            [void]$lbDiffs.Items.Add("--------------------------------------------------")
        }
        $diffForm.Controls.Add($lbDiffs)

        $btnRevert = New-Object System.Windows.Forms.Button
        $btnRevert.Text = "Revert (Load Prior Settings)"
        $btnRevert.Location = New-Object System.Drawing.Point(20, 380)
        $btnRevert.Size = New-Object System.Drawing.Size(280, 40)
        $btnRevert.BackColor = [System.Drawing.Color]::LightGreen
        $btnRevert.ForeColor = [System.Drawing.Color]::Black
        $btnRevert.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
        $btnRevert.DialogResult = [System.Windows.Forms.DialogResult]::Yes
        $diffForm.Controls.Add($btnRevert)

        $btnKeep = New-Object System.Windows.Forms.Button
        $btnKeep.Text = "Keep Current Changes"
        $btnKeep.Location = New-Object System.Drawing.Point(330, 380)
        $btnKeep.Size = New-Object System.Drawing.Size(280, 40)
        $btnKeep.BackColor = [System.Drawing.Color]::LightSkyBlue
        $btnKeep.ForeColor = [System.Drawing.Color]::Black
        $btnKeep.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
        $btnKeep.DialogResult = [System.Windows.Forms.DialogResult]::No
        $diffForm.Controls.Add($btnKeep)

        $result = $diffForm.ShowDialog()

        if ($result -eq [System.Windows.Forms.DialogResult]::Yes) {
            Restore-StateToUI $savedState
            Update-Status "Prior settings loaded to UI. Click 'Apply Settings' to enforce."
            [System.Windows.Forms.MessageBox]::Show("Your previous SlimBrave settings have been mapped to the UI.`n`nClick 'Apply Settings' when you are ready to write them to the registry.", "Revert Initiated", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
        } else {
            Save-CurrentState
            Update-Baseline
            Check-DirtyState
            Update-Status "State baseline updated to match current system modifications."
        }
    }
}

function Update-Layout {
    if ($form.ClientSize.Width -eq 0) { return }

    $totalTopWidth = $presetLabel.Width + $btnPrivacy.Width + $btnSecurity.Width + 20
    $startX = ($form.ClientSize.Width - $totalTopWidth) / 2
    $presetLabel.Location = New-Object System.Drawing.Point($startX, 24)
    $btnPrivacy.Location = New-Object System.Drawing.Point(($presetLabel.Right + 10), 16)
    $btnSecurity.Location = New-Object System.Drawing.Point(($btnPrivacy.Right + 10), 16)
    
    $statusPanel.Location = New-Object System.Drawing.Point(($form.ClientSize.Width - $statusPanel.Width - 20), 18)

    $panelWidth = [int](($form.ClientSize.Width - 80) / 3)
    $panelHeight = [int]($form.ClientSize.Height - 250)
    
    $leftPanel.Location = New-Object System.Drawing.Point(20, 70)
    $leftPanel.Size = New-Object System.Drawing.Size($panelWidth, $panelHeight)
    
    $midPanel.Location = New-Object System.Drawing.Point(($leftPanel.Right + 20), 70)
    $midPanel.Size = New-Object System.Drawing.Size($panelWidth, $panelHeight)

    $rightPanel.Location = New-Object System.Drawing.Point(($midPanel.Right + 20), 70)
    $rightPanel.Size = New-Object System.Drawing.Size($panelWidth, $panelHeight)

    foreach ($cb in $allFeatures) {
        $cb.Width = $panelWidth - 60
    }

    $bottomY = $leftPanel.Bottom + 20
    $sbLabel.Location = New-Object System.Drawing.Point($leftPanel.Left, ($bottomY + 3))
    $sbDropdown.Location = New-Object System.Drawing.Point(($sbLabel.Right + 5), $bottomY)
    
    $dnsLabel.Location = New-Object System.Drawing.Point($leftPanel.Left, ($bottomY + 35))
    $dnsDropdown.Location = New-Object System.Drawing.Point(($dnsLabel.Right + 5), ($bottomY + 32))

    $buttonY = $form.ClientSize.Height - $statusBar.Height - 55
    $btnWidth = 200 
    $exportButton.Size = New-Object System.Drawing.Size($btnWidth, 38)
    $importButton.Size = New-Object System.Drawing.Size($btnWidth, 38)
    $pullButton.Size = New-Object System.Drawing.Size($btnWidth, 38)
    $saveButton.Size = New-Object System.Drawing.Size($btnWidth, 38)
    $resetButton.Size = New-Object System.Drawing.Size($btnWidth, 38)

    $totalBtnWidth = $btnWidth * 5
    $remainingSpace = $form.ClientSize.Width - 40 - $totalBtnWidth
    $gap = [int]($remainingSpace / 4)
    if ($gap -lt 5) { $gap = 5 }

    $exportButton.Location = New-Object System.Drawing.Point(20, $buttonY)
    $importButton.Location = New-Object System.Drawing.Point(($exportButton.Right + $gap), $buttonY)
    $pullButton.Location = New-Object System.Drawing.Point(($importButton.Right + $gap), $buttonY)
    $saveButton.Location = New-Object System.Drawing.Point(($pullButton.Right + $gap), $buttonY)
    $resetButton.Location = New-Object System.Drawing.Point(($saveButton.Right + $gap), $buttonY)

    Set-RoundedCorners $leftPanel 12
    Set-RoundedCorners $midPanel 12
    Set-RoundedCorners $rightPanel 12
    Set-RoundedCorners $btnPrivacy 10
    Set-RoundedCorners $btnSecurity 10
    Set-RoundedCorners $exportButton 10
    Set-RoundedCorners $importButton 10
    Set-RoundedCorners $pullButton 10
    Set-RoundedCorners $saveButton 10
    Set-RoundedCorners $resetButton 10
    Set-RoundedCorners $statusPanel 10
}

$form.Add_Resize({ Update-Layout })

$btnPrivacy.Add_Click({
    $global:suspendDirtyTracking = $true
    foreach ($cb in $allFeatures) { 
        $cb.Checked = $false 
        $cb.ForeColor = [System.Drawing.Color]::White
    }
    $keys = @("MetricsReportingEnabled", "SafeBrowsingExtendedReportingEnabled", "UrlKeyedAnonymizedDataCollectionEnabled", "FeedbackSurveysEnabled", "BraveP3AEnabled", "BraveStatsPingEnabled", "BraveWebDiscoveryEnabled", "AutofillAddressEnabled", "AutofillCreditCardEnabled", "PasswordManagerEnabled", "BrowserSignin", "WebRtcIPHandling", "BlockThirdPartyCookies", "EnableDoNotTrack", "IPFSEnabled", "PromptForDownloadLocation", "ClearBrowsingDataOnExitList", "HttpsOnlyMode", "BraveRewardsDisabled", "BraveWalletDisabled", "BraveVPNDisabled", "BraveAIChatEnabled", "TorDisabled", "BraveNewsDisabled", "BraveTalkDisabled", "BraveSpeedreaderEnabled", "BraveWaybackMachineEnabled", "BackgroundModeEnabled", "MediaRecommendationsEnabled", "ShoppingListEnabled", "AlwaysOpenPdfExternally", "PromotionsEnabled", "SearchSuggestEnabled", "DefaultBrowserSettingEnabled", "BravePlaylistEnabled")
    foreach ($key in $keys) {
        foreach ($cb in $allFeatures) { if ($cb.Tag.Key -eq $key) { $cb.Checked = $true; break } }
    }

    foreach ($perm in $allPerms) {
        $n = $perm.Tag.Name
        if ($n -eq "JavaScript") {
            $perm.SelectedItem = "Allow"
        } elseif ($n -eq "Camera" -or $n -eq "Microphone") {
            $perm.SelectedItem = "Ask"
        } elseif ($n -eq "Images") {
            $perm.SelectedItem = "Not Set"
        } else {
            if ($perm.Items.Contains("Block")) {
                $perm.SelectedItem = "Block"
            }
        }
    }

    $sbDropdown.SelectedItem = "Off"
    $dnsDropdown.SelectedItem = "Off"
    $global:suspendDirtyTracking = $false
    Check-DirtyState
    Update-Status "Loaded: High Privacy + Moderate Security preset."
})

$btnSecurity.Add_Click({
    $global:suspendDirtyTracking = $true
    foreach ($cb in $allFeatures) { 
        $cb.Checked = $false 
        $cb.ForeColor = [System.Drawing.Color]::White
    }
    $keys = @("MetricsReportingEnabled", "SafeBrowsingExtendedReportingEnabled", "UrlKeyedAnonymizedDataCollectionEnabled", "FeedbackSurveysEnabled", "BraveP3AEnabled", "BraveStatsPingEnabled", "BraveWebDiscoveryEnabled", "WebRtcIPHandling", "QuicAllowed", "BlockThirdPartyCookies", "EnableDoNotTrack", "ForceGoogleSafeSearch", "IPFSEnabled", "PromptForDownloadLocation", "HttpsOnlyMode", "BraveRewardsDisabled", "BraveWalletDisabled", "BraveVPNDisabled", "BraveAIChatEnabled", "TorDisabled", "SyncDisabled", "BraveNewsDisabled", "BraveTalkDisabled", "BraveSpeedreaderEnabled", "BraveWaybackMachineEnabled", "BackgroundModeEnabled", "AlwaysOpenPdfExternally", "DeveloperToolsDisabled", "BravePlaylistEnabled")
    foreach ($key in $keys) {
        foreach ($cb in $allFeatures) { if ($cb.Tag.Key -eq $key) { $cb.Checked = $true; break } }
    }

    foreach ($perm in $allPerms) {
        $n = $perm.Tag.Name
        if ($n -eq "JavaScript") {
            $perm.SelectedItem = "Allow"
        } elseif ($n -match "USB|Serial|HID|File|Window|Payment") {
            $perm.SelectedItem = "Block"
        } elseif ($n -match "Camera|Microphone|Location|Clipboard|Local Fonts") {
            $perm.SelectedItem = "Ask"
        } else {
            $perm.SelectedItem = "Not Set"
        }
    }

    $sbDropdown.SelectedItem = "On"
    $dnsDropdown.SelectedItem = "On"
    $global:suspendDirtyTracking = $false
    Check-DirtyState
    Update-Status "Loaded: High Security + Moderate Privacy preset."
})

function Reload-UIFromRegistry {
    $global:suspendDirtyTracking = $true
    foreach ($checkbox in $allFeatures) {
        $checkbox.Checked = $false
        $checkbox.ForeColor = [System.Drawing.Color]::White
    }
    foreach ($perm in $allPerms) {
        $perm.SelectedItem = "Not Set"
    }
    $sbDropdown.SelectedIndex = -1
    $dnsDropdown.SelectedIndex = -1

    $regProps = Get-ItemProperty -Path $registryPath -ErrorAction SilentlyContinue

    if ($null -ne $regProps) {
        foreach ($checkbox in $allFeatures) {
            $feature = $checkbox.Tag
            if ($feature.Type -eq "List") {
                $listPath = Join-Path $registryPath $feature.Key
                if (Test-Path $listPath) {
                    $checkbox.Checked = $true
                }
            } else {
                $val = $regProps.($feature.Key)
                if ($null -ne $val -and $val -eq $feature.Value) {
                    $checkbox.Checked = $true
                }
            }
        }

        foreach ($perm in $allPerms) {
            $k = $perm.Tag.Key
            $val = $regProps.$k
            if ($null -ne $val) {
                if ($val -eq 3) { $perm.SelectedItem = "Ask" }
                elseif ($val -eq 1) { $perm.SelectedItem = "Allow" }
                elseif ($k -eq "PaymentMethodQueryEnabled" -and $val -eq 0) { $perm.SelectedItem = "Block" }
                elseif ($val -eq 2) { $perm.SelectedItem = "Block" }
                else { $perm.SelectedItem = "Not Set" }
            }
        }

        if ($null -ne $regProps.SafeBrowsingProtectionLevel) {
            if ($regProps.SafeBrowsingProtectionLevel -eq 1) { $sbDropdown.SelectedItem = "On" }
            elseif ($regProps.SafeBrowsingProtectionLevel -eq 0) { $sbDropdown.SelectedItem = "Off" }
        }

        if ($null -ne $regProps.DnsOverHttpsMode) {
            if ($regProps.DnsOverHttpsMode -eq "automatic") { $dnsDropdown.SelectedItem = "On" }
            elseif ($regProps.DnsOverHttpsMode -eq "off") { $dnsDropdown.SelectedItem = "Off" }
        }
    }
    $global:suspendDirtyTracking = $false
    Update-Baseline
    Check-DirtyState
}

$pullButton.Add_Click({
    Reload-UIFromRegistry
    Update-Status "UI reloaded from current Brave registry settings."
})

$saveButton.Add_Click({
    $restorePrompt = [System.Windows.Forms.MessageBox]::Show("Would you like to create a System Restore point before applying these changes? (Recommended)", "System Restore", [System.Windows.Forms.MessageBoxButtons]::YesNo, [System.Windows.Forms.MessageBoxIcon]::Question)
    
    if ($restorePrompt -eq "Yes") {
        $form.Cursor = [System.Windows.Forms.Cursors]::WaitCursor
        Update-Status "Creating System Restore point (This may take a moment)..."
        try {
            Enable-ComputerRestore -Drive "C:\" -ErrorAction SilentlyContinue
            Checkpoint-Computer -Description "SlimBrave Pre-Apply Backup" -RestorePointType "MODIFY_SETTINGS" -ErrorAction Stop
            Write-Log "System Restore point created successfully."
        } catch {
            Write-Log "Failed to create System Restore point: $_"
            [System.Windows.Forms.MessageBox]::Show("Failed to create System Restore point. This can happen if System Protection is fully disabled or if Windows is rate-limiting checkpoints (1 per 24 hours).`n`nContinuing with settings application...", "Restore Point Notice", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
        }
        $form.Cursor = [System.Windows.Forms.Cursors]::Default
    }

    Update-Status "Applying settings to registry..."
    
    foreach ($checkbox in $allFeatures) {
        if ($checkbox.Checked) {
            $feature = $checkbox.Tag
            try {
                if ($feature.Type -eq "List") {
                    $listPath = Join-Path $registryPath $feature.Key
                    if (-not (Test-Path $listPath)) { [void](New-Item -Path $listPath -Force) }
                    $i = 1
                    foreach ($item in $feature.Value) {
                        [void](Set-ItemProperty -Path $listPath -Name $i.ToString() -Value $item -Type String -Force)
                        $i++
                    }
                } else {
                    [void](Set-ItemProperty -Path $registryPath -Name $feature.Key -Value $feature.Value -Type $feature.Type -Force)
                }
                Write-Log "Successfully applied policy: $($feature.Key)"
            } catch {
                Write-Log "Failed to apply policy $($feature.Key): $_"
            }
        } else {
            $feature = $checkbox.Tag
            try {
                if ($feature.Type -eq "List") {
                    $listPath = Join-Path $registryPath $feature.Key
                    if (Test-Path $listPath) { Remove-Item -Path $listPath -Recurse -Force -ErrorAction SilentlyContinue }
                } else {
                    Remove-ItemProperty -Path $registryPath -Name $feature.Key -ErrorAction SilentlyContinue
                }
            } catch { }
        }
    }

    foreach ($perm in $allPerms) {
        $sel = $perm.SelectedItem
        $k = $perm.Tag.Key
        if ($sel -eq "Not Set") {
            Remove-ItemProperty -Path $registryPath -Name $k -ErrorAction SilentlyContinue
            if ($k -eq "DefaultFileSystemReadGuardSetting") {
                Remove-ItemProperty -Path $registryPath -Name "DefaultFileSystemWriteGuardSetting" -ErrorAction SilentlyContinue
            }
        } else {
            $val = 0
            if ($sel -eq "Ask") { $val = 3 }
            if ($sel -eq "Block") {
                if ($k -eq "PaymentMethodQueryEnabled") { $val = 0 } else { $val = 2 }
            }
            if ($sel -eq "Allow") { $val = 1 }

            try {
                [void](Set-ItemProperty -Path $registryPath -Name $k -Value $val -Type DWord -Force)
                if ($k -eq "DefaultFileSystemReadGuardSetting") {
                    [void](Set-ItemProperty -Path $registryPath -Name "DefaultFileSystemWriteGuardSetting" -Value $val -Type DWord -Force)
                }
                Write-Log "Successfully applied permission policy: $k = $val"
            } catch {
                Write-Log "Failed to apply permission policy $($k): $_"
            }
        }
    }
    
    if ($sbDropdown.SelectedItem) {
        if ($sbDropdown.SelectedItem -eq "On") {
            [void](Set-ItemProperty -Path $registryPath -Name "SafeBrowsingProtectionLevel" -Value 1 -Type DWord -Force)
            Write-Log "Set SafeBrowsingProtectionLevel to 1 (On)"
        } elseif ($sbDropdown.SelectedItem -eq "Off") {
            [void](Set-ItemProperty -Path $registryPath -Name "SafeBrowsingProtectionLevel" -Value 0 -Type DWord -Force)
            Write-Log "Set SafeBrowsingProtectionLevel to 0 (Off)"
        } else {
            Remove-ItemProperty -Path $registryPath -Name "SafeBrowsingProtectionLevel" -ErrorAction SilentlyContinue
        }
    }

    if ($dnsDropdown.SelectedItem) {
        if ($dnsDropdown.SelectedItem -eq "On") { Set-DnsMode "automatic" }
        elseif ($dnsDropdown.SelectedItem -eq "Off") { Set-DnsMode "off" }
        else { Remove-ItemProperty -Path $registryPath -Name "DnsOverHttpsMode" -ErrorAction SilentlyContinue }
    }

    Save-CurrentState
    Update-Baseline
    Check-DirtyState
    Update-Status "Settings applied successfully!"

    $braveProcess = Get-Process brave -ErrorAction SilentlyContinue
    if ($braveProcess) {
        $restartPrompt = [System.Windows.Forms.MessageBox]::Show("Settings applied successfully! Brave is currently running. Would you like SlimBrave to automatically close and restart it to apply these changes?", "Restart Brave", [System.Windows.Forms.MessageBoxButtons]::YesNo, [System.Windows.Forms.MessageBoxIcon]::Question)
        if ($restartPrompt -eq "Yes") {
            Update-Status "Restarting Brave..."
            try {
                Stop-Process -Name brave -Force
                Start-Sleep -Seconds 2
                Start-Process "brave"
                Update-Status "Brave restarted successfully."
                Write-Log "Brave browser restarted successfully by user prompt."
            } catch {
                Update-Status "Failed to restart Brave automatically."
                Write-Log "Failed to restart Brave automatically: $_"
            }
        }
    } else {
        [System.Windows.Forms.MessageBox]::Show("Settings applied successfully! Open Brave to see changes.", "SlimBrave", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
    }
})

function Reset-AllSettings {
    $confirm = [System.Windows.Forms.MessageBox]::Show(
        "Warning: This will erase ALL Brave policy settings and restore them to their default state. Do you wish to continue?", 
        "Confirm SlimBrave Reset", 
        [System.Windows.Forms.MessageBoxButtons]::YesNo, 
        [System.Windows.Forms.MessageBoxIcon]::Warning
    )
    
    if ($confirm -eq "Yes") {
        Update-Status "Resetting all settings to default..."
        try {
            Remove-Item -Path $registryPath -Recurse -Force
            [void](New-Item -Path $registryPath -Force)
            
            $global:suspendDirtyTracking = $true
            foreach ($cb in $allFeatures) { 
                $cb.Checked = $false 
                $cb.ForeColor = [System.Drawing.Color]::White 
            }
            foreach ($perm in $allPerms) { $perm.SelectedItem = "Not Set" }
            $sbDropdown.SelectedIndex = -1
            $dnsDropdown.SelectedIndex = -1
            $global:suspendDirtyTracking = $false

            Write-Log "All settings successfully wiped from registry."
            
            [System.Windows.Forms.MessageBox]::Show(
                "All Brave policy settings have been successfully reset to their default values.", 
                "Reset Successful", 
                [System.Windows.Forms.MessageBoxButtons]::OK, 
                [System.Windows.Forms.MessageBoxIcon]::Information
            )
            Update-Status "Reset successful."
            return $true
        } catch {
            Write-Log "Failed to reset settings: $_"
            [System.Windows.Forms.MessageBox]::Show(
                "An error occurred while resetting the settings: $_", 
                "Reset Failed", 
                [System.Windows.Forms.MessageBoxButtons]::OK, 
                [System.Windows.Forms.MessageBoxIcon]::Error
            )
            Update-Status "Reset failed."
            return $false
        }
    }
    return $false
}

$resetButton.Add_Click({
    if (Reset-AllSettings) {
        if (-not (Test-Path -Path $registryPath)) {
            [void](New-Item -Path $registryPath -Force)
        }
        Save-CurrentState
        Update-Baseline
        Check-DirtyState
    }
})

$exportButton.Add_Click({
    $saveFileDialog = New-Object System.Windows.Forms.SaveFileDialog
    $saveFileDialog.Filter = "JSON files (*.json)|*.json|All files (*.*)|*.*"
    $saveFileDialog.Title = "Export SlimBrave Settings"
    $saveFileDialog.InitialDirectory = [Environment]::GetFolderPath("MyDocuments")
    $saveFileDialog.FileName = "SlimBraveSettings.json"
    
    if ($saveFileDialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        try {
            Get-UIStateSnapshot | ConvertTo-Json -Depth 3 | Out-File -FilePath $saveFileDialog.FileName -Force
            Update-Status "Settings exported successfully."
            Write-Log "Settings exported to $($saveFileDialog.FileName)"
            [System.Windows.Forms.MessageBox]::Show("Settings exported successfully to:`n$($saveFileDialog.FileName)", "Export Successful", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
        } catch {
            Write-Log "Export Failed: $_"
            [System.Windows.Forms.MessageBox]::Show("Failed to export settings: $_", "Export Failed", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
        }
    }
})

$importButton.Add_Click({
    $openFileDialog = New-Object System.Windows.Forms.OpenFileDialog
    $openFileDialog.Filter = "JSON files (*.json)|*.json|All files (*.*)|*.*"
    $openFileDialog.Title = "Import SlimBrave Settings"
    $openFileDialog.InitialDirectory = [Environment]::GetFolderPath("MyDocuments")
    
    if ($openFileDialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        try {
            $importedSettings = Get-Content -Path $openFileDialog.FileName -Raw | ConvertFrom-Json
            Restore-StateToUI $importedSettings
            
            Update-Status "Settings imported successfully. Pending save."
            Write-Log "Settings imported from $($openFileDialog.FileName)"
            [System.Windows.Forms.MessageBox]::Show("Settings imported successfully from:`n$($openFileDialog.FileName)`n`nClick 'Apply Settings' to enforce them.", "Import Successful", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
        } catch {
            Write-Log "Import Failed: $_"
            [System.Windows.Forms.MessageBox]::Show("Failed to import settings: $_", "Import Failed", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
        }
    }
})

Write-Log "SlimBrave UI Loaded successfully."

Reload-UIFromRegistry
Check-StateChanges
Update-Layout
[void] $form.ShowDialog()
