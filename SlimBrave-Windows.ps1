# Slimbrave - Revived - v1.2.0 (Windows)

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell -ArgumentList "-File `"$($MyInvocation.MyCommand.Path)`"" -Verb RunAs
    exit
}

if (-not ("DPI" -as [type])) {
    try {
        Add-Type -TypeDefinition '
        using System;
        using System.Runtime.InteropServices;
        public class DPI {
            [DllImport("user32.dll")]
            public static extern bool SetProcessDPIAware();
        }'
        [void][DPI]::SetProcessDPIAware()
        [System.Windows.Forms.Application]::EnableVisualStyles()
    } catch { }
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$global:registryPath = "HKLM:\SOFTWARE\Policies\BraveSoftware\Brave"
$logFile = Join-Path $PSScriptRoot "SlimBrave.log"
$stateFile = Join-Path $PSScriptRoot "SlimBraveState.json"
$global:isDirty = $false
$global:suspendDirtyTracking = $false
$global:suspendPresetTriggers = $false

function Write-Log ($message) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $message" | Out-File -FilePath $logFile -Append
}

if (-not (Test-Path -Path $global:registryPath)) {
    [void](New-Item -Path $global:registryPath -Force)
    Write-Log "Created new Brave Policy registry key."
}

Clear-Host
$form = New-Object System.Windows.Forms.Form
$form.Text = "SlimBrave - Revived v1.2.0"
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

$channelLabel = New-Object System.Windows.Forms.Label
$channelLabel.Text = "Target Channel:"
$channelLabel.AutoSize = $true
$channelLabel.Font = New-Object System.Drawing.Font("Microsoft Sans Serif", 9, [System.Drawing.FontStyle]::Bold)
$channelLabel.ForeColor = [System.Drawing.Color]::White
$form.Controls.Add($channelLabel)

$channelDropdown = New-Object System.Windows.Forms.ComboBox
$channelDropdown.DropDownStyle = [System.Windows.Forms.ComboBoxStyle]::DropDownList
[void]$channelDropdown.Items.AddRange(@("Stable", "Beta", "Nightly"))
$channelDropdown.SelectedIndex = 0
$channelDropdown.Size = New-Object System.Drawing.Size(110, 20)
$channelDropdown.BackColor = [System.Drawing.Color]::FromArgb(255, 45, 45, 45)
$channelDropdown.ForeColor = [System.Drawing.Color]::White
$channelDropdown.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$toolTip.SetToolTip($channelDropdown, "Select the Brave Browser release channel to manage.")
$form.Controls.Add($channelDropdown)

$channelDropdown.Add_SelectedIndexChanged({
    if ($global:isDirty -and -not $global:suspendDirtyTracking) {
        $msgBox = [System.Windows.Forms.MessageBox]::Show(
            "You have unsaved changes. Changing the target channel will discard them. Do you want to continue?",
            "Unsaved Changes",
            [System.Windows.Forms.MessageBoxButtons]::YesNo,
            [System.Windows.Forms.MessageBoxIcon]::Warning
        )
        if ($msgBox -eq [System.Windows.Forms.DialogResult]::No) {
            $global:suspendDirtyTracking = $true
            if ($global:registryPath -match "BraveBeta") {
                $channelDropdown.SelectedItem = "Beta"
            } elseif ($global:registryPath -match "BraveNightly") {
                $channelDropdown.SelectedItem = "Nightly"
            } else {
                $channelDropdown.SelectedItem = "Stable"
            }
            $global:suspendDirtyTracking = $false
            return
        }
    }
    if ($channelDropdown.SelectedItem -eq "Stable") {
        $global:registryPath = "HKLM:\SOFTWARE\Policies\BraveSoftware\Brave"
    } elseif ($channelDropdown.SelectedItem -eq "Beta") {
        $global:registryPath = "HKLM:\SOFTWARE\Policies\BraveSoftware\BraveBeta"
    } elseif ($channelDropdown.SelectedItem -eq "Nightly") {
        $global:registryPath = "HKLM:\SOFTWARE\Policies\BraveSoftware\BraveNightly"
    }
        if (-not (Test-Path -Path $global:registryPath)) {
        [void](New-Item -Path $global:registryPath -Force)
        Write-Log "Created new Brave Policy registry key for $($channelDropdown.SelectedItem)."
    }
        Reload-UIFromRegistry
    Update-Status "Target channel switched to $($channelDropdown.SelectedItem). UI reloaded."
})

$presetLabel = New-Object System.Windows.Forms.Label
$presetLabel.Text = "Presets:"
$presetLabel.AutoSize = $true
$presetLabel.Font = New-Object System.Drawing.Font("Microsoft Sans Serif", 9, [System.Drawing.FontStyle]::Bold)
$presetLabel.ForeColor = [System.Drawing.Color]::LightSkyBlue
$form.Controls.Add($presetLabel)

$presetDropdown = New-Object System.Windows.Forms.ComboBox
$presetDropdown.DropDownStyle = [System.Windows.Forms.ComboBoxStyle]::DropDownList
[void]$presetDropdown.Items.AddRange(@("Maximum Privacy", "High Security", "Performance Focused", "Strict Parental Controls", "Balanced Privacy", "Developer", "Brave Origin"))
$presetDropdown.SelectedIndex = 0
$presetDropdown.Size = New-Object System.Drawing.Size(200, 20)
$presetDropdown.BackColor = [System.Drawing.Color]::FromArgb(255, 45, 45, 45)
$presetDropdown.ForeColor = [System.Drawing.Color]::White
$presetDropdown.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$toolTip.SetToolTip($presetDropdown, "Select a preset to automatically configure recommended settings.")
$form.Controls.Add($presetDropdown)

$script:presetTable = [ordered]@{
    "Maximum Privacy" = @{
        Features = @('AccessibilityImageLabelsEnabled', 'AutofillAddressEnabled', 'AutofillCreditCardEnabled', 'BackgroundModeEnabled', 'BasicAuthOverHttpEnabled', 'BlockExternalExtensions', 'BlockThirdPartyCookies', 'BraveAIChatEnabled', 'BraveDeAMPEnabled', 'BraveDebouncingEnabled', 'BraveLocalAiEnabled', 'BraveNewsDisabled', 'BraveP3AEnabled', 'BravePlaylistEnabled', 'BraveRewardsDisabled', 'BraveSpeedreaderEnabled', 'BraveStatsPingEnabled', 'BraveTalkDisabled', 'BraveTrackersStrippingEnabled', 'BraveWalletDisabled', 'BraveWaybackMachineEnabled', 'BraveWebDiscoveryEnabled', 'BrowserSignin', 'DefaultJavaScriptOptimizerSetting', 'ExtensionInstallTypeBlocklist', 'ExternalProtocolDialogShowAlwaysOpenCheckbox', 'GlobalPrivacyControlEnabled', 'HttpsOnlyMode', 'MetricsReportingEnabled', 'NetworkPredictionOptions', 'OriginKeyedProcessesEnabled', 'ReduceAcceptLanguage', 'RemoteDebuggingAllowed', 'SearchSuggestEnabled', 'SitePerProcess', 'SpellCheckServiceEnabled', 'UrlKeyedAnonymizedDataCollectionEnabled', 'WebRtcIPHandling', 'XSLTEnabled', 'BraveVPNDisabled')
        Permissions = @{DefaultGeolocationSetting = 'Block'; DefaultNotificationsSetting = 'Block'; DefaultPopupsSetting = 'Block'; DefaultWebUsbGuardSetting = 'Block'; DefaultSerialGuardSetting = 'Block'; DefaultWebHidGuardSetting = 'Block'; DefaultFileSystemReadGuardSetting = 'Block'; DefaultClipboardSetting = 'Block'; DefaultWindowPlacementSetting = 'Block'; DefaultLocalFontsSetting = 'Block'; PaymentMethodQueryEnabled = 'Block'; DefaultSensorsSetting = 'Block'}
        SafeBrowsing = 'On'; DnsMode = 'Automatic'
    }
    "High Security" = @{
        Features = @('BackgroundModeEnabled', 'BasicAuthOverHttpEnabled', 'BlockExternalExtensions', 'BlockThirdPartyCookies', 'BraveAIChatEnabled', 'BraveLocalAiEnabled', 'BraveNewsDisabled', 'BraveP3AEnabled', 'BravePlaylistEnabled', 'BraveRewardsDisabled', 'BraveSpeedreaderEnabled', 'BraveStatsPingEnabled', 'BraveTalkDisabled', 'BraveWalletDisabled', 'BraveWaybackMachineEnabled', 'BraveWebDiscoveryEnabled', 'DefaultJavaScriptOptimizerSetting', 'ExtensionInstallTypeBlocklist', 'ExternalProtocolDialogShowAlwaysOpenCheckbox', 'HttpsOnlyMode', 'MetricsReportingEnabled', 'OriginKeyedProcessesEnabled', 'RemoteDebuggingAllowed', 'SSLErrorOverrideAllowed', 'SafeBrowsingProceedAnywayDisabled', 'SitePerProcess', 'UrlKeyedAnonymizedDataCollectionEnabled', 'XSLTEnabled', 'BraveVPNDisabled')
        Permissions = @{DefaultPopupsSetting = 'Block'; DefaultWebUsbGuardSetting = 'Block'; DefaultSerialGuardSetting = 'Block'; DefaultWebHidGuardSetting = 'Block'; DefaultFileSystemReadGuardSetting = 'Block'; DefaultClipboardSetting = 'Block'}
        SafeBrowsing = 'On'; DnsMode = 'Automatic'
    }
    "Performance Focused" = @{
        Features = @('BackgroundModeEnabled', 'BraveLocalAiEnabled', 'BraveNewsDisabled', 'BravePlaylistEnabled', 'BraveRewardsDisabled', 'BraveTalkDisabled', 'BraveWalletDisabled', 'EnableMediaRouter', 'HighEfficiencyModeEnabled', 'BraveVPNDisabled')
        Permissions = @{}
        SafeBrowsing = 'On'; DnsMode = ''
    }
    "Strict Parental Controls" = @{
        Features = @('AllowDeletingBrowserHistory', 'BasicAuthOverHttpEnabled', 'BraveAIChatEnabled', 'BraveLocalAiEnabled', 'BrowserGuestModeEnabled', 'ExtensionInstallBlocklist', 'ExtensionInstallTypeBlocklist', 'ForceGoogleSafeSearch', 'ForceYouTubeRestrict', 'IncognitoModeAvailability', 'PromptForDownloadLocation', 'RemoteDebuggingAllowed', 'SSLErrorOverrideAllowed', 'SafeBrowsingProceedAnywayDisabled', 'SpellCheckServiceEnabled', 'SyncDisabled', 'TorDisabled')
        Permissions = @{DefaultPopupsSetting = 'Block'; DefaultNotificationsSetting = 'Block'}
        SafeBrowsing = 'On'; DnsMode = 'Secure'
    }
    "Balanced Privacy" = @{
        Features = @('BasicAuthOverHttpEnabled', 'BlockExternalExtensions', 'BlockThirdPartyCookies', 'BraveDeAMPEnabled', 'BraveDebouncingEnabled', 'BraveLocalAiEnabled', 'BraveNewsDisabled', 'BraveP3AEnabled', 'BravePlaylistEnabled', 'BraveRewardsDisabled', 'BraveStatsPingEnabled', 'BraveTrackersStrippingEnabled', 'BraveWalletDisabled', 'ExtensionInstallTypeBlocklist', 'GlobalPrivacyControlEnabled', 'MetricsReportingEnabled', 'RemoteDebuggingAllowed', 'SpellCheckServiceEnabled', 'UrlKeyedAnonymizedDataCollectionEnabled')
        Permissions = @{DefaultPopupsSetting = 'Block'; PaymentMethodQueryEnabled = 'Block'; DefaultSensorsSetting = 'Block'}
        SafeBrowsing = 'On'; DnsMode = 'Automatic'
    }
    "Developer" = @{
        Features = @('BraveDeAMPEnabled', 'BraveDebouncingEnabled', 'BraveLocalAiEnabled', 'BraveNewsDisabled', 'BravePlaylistEnabled', 'BraveRewardsDisabled', 'BraveWalletDisabled', 'SpellCheckServiceEnabled')
        Permissions = @{}
        SafeBrowsing = 'On'; DnsMode = ''
    }
    "Brave Origin" = @{
        Features = @('BraveAIChatEnabled', 'BraveEmailAliasesEnabled', 'BraveLocalAiEnabled', 'BraveNewsDisabled', 'BraveP3AEnabled', 'BravePlaylistEnabled', 'BraveRewardsDisabled', 'BraveSpeedreaderEnabled', 'BraveStatsPingEnabled', 'BraveTalkDisabled', 'BraveWalletDisabled', 'BraveWaybackMachineEnabled', 'BraveWebDiscoveryEnabled', 'TorDisabled', 'BraveVPNDisabled')
        Permissions = @{}
        SafeBrowsing = ''; DnsMode = ''
    }
}
$script:presetPreview = $null
$script:featureMarkers = @{}

function Get-PresetChoice($entry, [string]$key, [string]$kind) {
    switch ($kind) {
        'Permission' { if ($entry.Permissions.ContainsKey($key)) { return $entry.Permissions[$key] }; return 'Not Set' }
        'SafeBrowsing' { if ($entry.SafeBrowsing) { return $entry.SafeBrowsing }; return 'Not Set' }
        'DnsMode' { if ($entry.DnsMode) { return $entry.DnsMode }; return 'Not Set' }
        'Template' { if ($entry.DnsMode -eq 'Secure') { return 'Cloudflare for Families' }; return '(Blank)' }
        default { if ($entry.Features -contains $key) { return 'Ticked' }; return 'Unticked' }
    }
}

function Get-PresetTooltip([string]$description, [string]$key, [string]$kind = 'Feature') {
    $description = ($description -split '\r?\n\r?\nSuggested Settings', 2)[0]
    $privacy = Get-PresetChoice $script:presetTable['Maximum Privacy'] $key $kind
    $security = Get-PresetChoice $script:presetTable['High Security'] $key $kind
    $rows = foreach ($name in $script:presetTable.Keys) {
        "${name}: $(Get-PresetChoice $script:presetTable[$name] $key $kind)"
    }
    return "$description`n`nSuggested Settings for Privacy: $privacy | Security: $security`n`nPreset selections:`n$($rows -join "`n")"
}

function Update-PresetColor($cb) {
    $key = $cb.Tag.Key
    if (-not $script:featureMarkers.ContainsKey($key)) { return }
    $marker = $script:featureMarkers[$key]
    $reason = ''
    $color = [System.Drawing.Color]::White
    if ($cb.Checked) {
        $color = [System.Drawing.Color]::DeepSkyBlue
        if ($script:presetPreview) {
            $script:presetPreview.Seen[$key] = $true
            if (-not $script:presetPreview.Retained.ContainsKey($key)) {
                $color = [System.Drawing.Color]::LightGreen
                $reason = if ($script:presetPreview.Selected -contains $key) { 'Added by Preset' } else { 'Manually Added, Preset Disabled This' }
            }
        }
    } elseif ($script:presetPreview -and $script:presetPreview.Seen.ContainsKey($key)) {
        $color = [System.Drawing.Color]::LightCoral
        $reason = if ($script:presetPreview.Selected -contains $key) { 'Removed from Preset' } else { 'Removed from your Current Configuration' }
    }
    $cb.ForeColor = $color
    $marker.ForeColor = $color
    $toolTip.SetToolTip($marker, $reason)
    $marker.Visible = [bool]$reason
}

$presetDropdown.Add_SelectedIndexChanged({
    if ($global:suspendPresetTriggers -or -not $presetDropdown.SelectedItem) { return }
    $name = [string]$presetDropdown.SelectedItem
    $entry = $script:presetTable[$name]
    if (-not $entry) { return }
    $seen = @{}
    $retained = @{}
    foreach ($cb in $allFeatures) {
        $key = $cb.Tag.Key
        if ($cb.Checked -or $entry.Features -contains $key) { $seen[$key] = $true }
        if ($cb.Checked -and $entry.Features -contains $key) { $retained[$key] = $true }
    }
    $script:presetPreview = @{ Seen = $seen; Retained = $retained; Selected = $entry.Features }
    $global:suspendDirtyTracking = $true
    try {
        foreach ($cb in $allFeatures) { $cb.Checked = ($entry.Features -contains $cb.Tag.Key) }
        foreach ($perm in $allPerms) { $perm.SelectedItem = (Get-PresetChoice $entry $perm.Tag.Key 'Permission') }
        if ($entry.SafeBrowsing) { $sbDropdown.SelectedItem = $entry.SafeBrowsing } else { $sbDropdown.SelectedIndex = -1 }
        if ($entry.DnsMode) { $dnsDropdown.SelectedItem = $entry.DnsMode } else { $dnsDropdown.SelectedIndex = -1 }
        $dnsTplInput.Text = if ($entry.DnsMode -eq 'Secure') { 'https://family.cloudflare-dns.com/dns-query{?dns}' } else { '' }
    } finally { $global:suspendDirtyTracking = $false }
    foreach ($cb in $allFeatures) { Update-PresetColor $cb }
    Check-DirtyState
    Update-Status "${name} preview: green = added, blue = kept, red = unticked. Apply to save."
})

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
        $saveStatusLabel.Text = "Changes Need To Be Saved..."
        $saveStatusLabel.ForeColor = [System.Drawing.Color]::Gold
    } else {
        $snap = Get-UIStateSnapshot
        $saveStatusLabel.Text = if ($snap.Features.Count -or $snap.Permissions.Count -or $snap.SafeBrowsing -or $snap.DnsMode) { "Profile Active [OK]" } else { "Unmanaged" }
        $saveStatusLabel.ForeColor = [System.Drawing.Color]::LightGreen
    }
    $statusPanel.Refresh()
}

function Update-Status ($text) {
    $statusBar.Text = $text
    $form.Refresh()
    Write-Log $text
}


function Assert-DoHTemplate ([string]$Mode, [string]$Template) {
    if ($Template -match '[\p{Cc}\p{Cf}]') { throw 'DoH template contains control or formatting characters.' }
    if ($Mode -notin @('Secure','Custom','Automatic')) { return }
    if ([string]::IsNullOrWhiteSpace($Template)) {
        if ($Mode -ne 'Automatic') { throw 'Secure DNS requires an HTTPS DoH template.' }
        return
    }
    foreach ($token in ($Template.Trim() -split ' +')) {
        $url = $token -creplace '\{\?dns\}$',''
        $uri = $null
        if ($url -match '[{}\\]' -or -not [Uri]::TryCreate($url, [UriKind]::Absolute, [ref]$uri) -or
            $uri.Scheme -ne 'https' -or -not $uri.Host -or $uri.UserInfo -or $uri.Fragment) {
            throw 'Use an HTTPS DoH endpoint, optionally ending in {?dns}.'
        }
    }
}

function Remove-BravePolicyValue ([string]$Name) {
    $key = Get-Item -LiteralPath $global:registryPath -ErrorAction Stop
    if ($key.GetValueNames() -contains $Name) {
        Remove-ItemProperty -LiteralPath $global:registryPath -Name $Name -ErrorAction Stop
    }
}

function Test-SlimBraveList ($Feature) {
    $path = Join-Path $global:registryPath $Feature.Key
    if (-not (Test-Path -LiteralPath $path -ErrorAction Stop)) { return $false }
    $key = Get-Item -LiteralPath $path -ErrorAction Stop
    if ($key.SubKeyCount -ne 0 -or $key.ValueCount -ne $Feature.Value.Count) { return $false }
    for ($i = 0; $i -lt $Feature.Value.Count; $i++) {
        $value = $key.GetValue([string]($i + 1))
        if ($value -isnot [string] -or $value -cne $Feature.Value[$i]) { return $false }
    }
    return $true
}

function Remove-SlimBraveList ($Feature) {
    $path = Join-Path $global:registryPath $Feature.Key
    if (Test-SlimBraveList $Feature) { Remove-Item -LiteralPath $path -ErrorAction Stop }
    elseif (Test-Path -LiteralPath $path -ErrorAction Stop) { Write-Log "Preserved nonmatching policy list: $($Feature.Key)" }
}

function Remove-RetiredPolicies {
    $retired = @{
        SafeBrowsingExtendedReportingEnabled = 0
        MediaRecommendationsEnabled = 0
        ShoppingListEnabled = 0
        AlternateErrorPagesEnabled = 0
        DNSInterceptionChecksEnabled = 0
        EnableDoNotTrack = 1
        IPFSEnabled = 0
        FeedbackSurveysEnabled = 0
        PromotionsEnabled = 0
        SafeSitesFilterBehavior = 1
    }
    $key = Get-Item -LiteralPath $global:registryPath -ErrorAction Stop
    foreach ($name in $retired.Keys) {
        if ($key.GetValueNames() -contains $name -and $key.GetValueKind($name) -eq 'DWord' -and $key.GetValue($name) -eq $retired[$name]) {
            Remove-BravePolicyValue $name
        }
    }
}

function Set-DnsMode {
    param ([string] $dnsMode)
    [void](Set-ItemProperty -Path $global:registryPath -Name "DnsOverHttpsMode" -Value $dnsMode -Type String -Force -ErrorAction Stop)
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

$leftPanel = New-Object System.Windows.Forms.Panel
$leftPanel.BackColor = [System.Drawing.Color]::FromArgb(255, 35, 35, 35)
$leftPanel.BorderStyle = [System.Windows.Forms.BorderStyle]::None
$leftPanel.AutoScroll = $true 
$form.Controls.Add($leftPanel)

$telemetryLabel = New-Object System.Windows.Forms.Label
$telemetryLabel.Text = "Telemetry and Reporting"
$telemetryLabel.Font = New-Object System.Drawing.Font("Microsoft Sans Serif", 10.5, [System.Drawing.FontStyle]::Bold)
$telemetryLabel.Location = New-Object System.Drawing.Point(28, 10)
$telemetryLabel.Size = New-Object System.Drawing.Size(300, 25)
$telemetryLabel.ForeColor = [System.Drawing.Color]::LightSalmon
$leftPanel.Controls.Add($telemetryLabel)

$telemetryFeatures = @(
    @{ Name = "Disable Metrics Reporting"; Key = "MetricsReportingEnabled"; Value = 0; Type = "DWord"; ToolTip = "Prevents crash-report uploads; Brave does not send Chromium usage statistics." },
    @{ Name = "Disable URL Data Collection"; Key = "UrlKeyedAnonymizedDataCollectionEnabled"; Value = 0; Type = "DWord"; ToolTip = "Stops sending anonymized URLs to help improve the browser.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable P3A Telemetry"; Key = "BraveP3AEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables Privacy-Preserving Product Analytics completely.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Daily Stats Ping"; Key = "BraveStatsPingEnabled"; Value = 0; Type = "DWord"; ToolTip = "Stops the daily active user ping.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Web Discovery"; Key = "BraveWebDiscoveryEnabled"; Value = 0; Type = "DWord"; ToolTip = "Prevents anonymous search/browsing data from being sent to Brave Search.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Limit Variations"; Key = "ChromeVariations"; Value = 1; Type = "DWord"; ToolTip = "Limits server-side studies to critical fixes (value 1). Can suppress fingerprint masking, clean-link copying and image metadata stripping. Restart Brave." }
)

[int]$leftY = 40
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
    $toolTip.SetToolTip($checkbox, (Get-PresetTooltip $feature.ToolTip $feature.Key))
    $leftPanel.Controls.Add($checkbox)
    $allFeatures += $checkbox
    $marker = New-Object System.Windows.Forms.Label
    $marker.Text = '(?)'
    $marker.Size = New-Object System.Drawing.Size(27, 20)
    $marker.Visible = $false
    $leftPanel.Controls.Add($marker)
    $script:featureMarkers[$feature.Key] = $marker
    $checkbox.Add_CheckedChanged({ if (-not $global:suspendDirtyTracking) { Update-PresetColor $this } })
    $leftY += 28
}

$leftY += 10
$privacyLabel = New-Object System.Windows.Forms.Label
$privacyLabel.Text = "Privacy and Security"
$privacyLabel.Font = New-Object System.Drawing.Font("Microsoft Sans Serif", 11, [System.Drawing.FontStyle]::Bold)
$privacyLabel.Location = New-Object System.Drawing.Point(28, $leftY)
$privacyLabel.Size = New-Object System.Drawing.Size(300, 25)
$privacyLabel.ForeColor = [System.Drawing.Color]::LightSalmon
$leftPanel.Controls.Add($privacyLabel)

$leftY += 30
$privacyFeatures = @(
    @{ Name = "Disable Autofill (Addresses)"; Key = "AutofillAddressEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables saving and autofilling addresses.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable Autofill (Credit Cards)"; Key = "AutofillCreditCardEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables saving and autofilling credit cards.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable Password Manager"; Key = "PasswordManagerEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables the built-in password manager.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable Browser Sign-in"; Key = "BrowserSignin"; Value = 0; Type = "DWord"; ToolTip = "Prevents syncing your data to cloud accounts.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable WebRTC IP Leak"; Key = "WebRtcIPHandling"; Value = "disable_non_proxied_udp"; Type = "String"; ToolTip = "Prevents your real IP address from leaking when using a VPN.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable QUIC Protocol"; Key = "QuicAllowed"; Value = 0; Type = "DWord"; ToolTip = "Disables QUIC for web requests; WebRTC and WebTransport can still use UDP." },
    @{ Name = "Block Third Party Cookies"; Key = "BlockThirdPartyCookies"; Value = 1; Type = "DWord"; ToolTip = "Blocks all third-party tracking cookies.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Enable Global Privacy Control"; Key = "GlobalPrivacyControlEnabled"; Value = 1; Type = "DWord"; ToolTip = "Enables GPC to tell sites not to sell or share your data.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Enable De-AMP"; Key = "BraveDeAMPEnabled"; Value = 1; Type = "DWord"; ToolTip = "Bypasses Google AMP pages and redirects you to the original website.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Enable Debouncing"; Key = "BraveDebouncingEnabled"; Value = 1; Type = "DWord"; ToolTip = "Skips known tracking redirect hops before you reach your destination.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Strip URL Trackers"; Key = "BraveTrackersStrippingEnabled"; Value = 1; Type = "DWord"; ToolTip = "Automatically removes tracking parameters from URLs.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Reduce Language Fingerprinting"; Key = "ReduceAcceptLanguage"; Value = 1; Type = "DWord"; ToolTip = "Reduces the language data sent to sites to prevent fingerprinting.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Force Download Prompts"; Key = "PromptForDownloadLocation"; Value = 1; Type = "DWord"; ToolTip = "Forces Brave to ask where to save a file before downloading, preventing drive-by downloads.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Clear Data on Exit"; Key = "ClearBrowsingDataOnExitList"; Value = @("browsing_history", "download_history", "cookies_and_other_site_data", "cached_images_and_files", "password_signin", "autofill", "site_settings", "hosted_app_data"); Type = "List"; ToolTip = "Wipes all cookies, cache, and browsing history the moment the browser closes.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Force HTTPS-Only Mode"; Key = "HttpsOnlyMode"; Value = "force_enabled"; Type = "String"; ToolTip = "Requests strict HTTPS upgrades. Where Brave uses Chromium HTTPS-First, this may seed the setting rather than lock it. Check brave://settings/security." },
    @{ Name = "Disable Network Prediction"; Key = "NetworkPredictionOptions"; Value = 2; Type = "DWord"; ToolTip = "Stops speculative DNS lookups and preconnects to sites you never clicked.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable Password Leak Detection"; Key = "PasswordLeakDetectionEnabled"; Value = 0; Type = "DWord"; ToolTip = "Pins the Google-backed leak check off as managed policy.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" }
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
    $toolTip.SetToolTip($checkbox, (Get-PresetTooltip $feature.ToolTip $feature.Key))
    $leftPanel.Controls.Add($checkbox)
    $allFeatures += $checkbox
    $marker = New-Object System.Windows.Forms.Label
    $marker.Text = '(?)'
    $marker.Size = New-Object System.Drawing.Size(27, 20)
    $marker.Visible = $false
    $leftPanel.Controls.Add($marker)
    $script:featureMarkers[$feature.Key] = $marker
    $checkbox.Add_CheckedChanged({ if (-not $global:suspendDirtyTracking) { Update-PresetColor $this } })
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
$braveLabel.Size = New-Object System.Drawing.Size(300, 25)
$braveLabel.ForeColor = [System.Drawing.Color]::LightSalmon
$midPanel.Controls.Add($braveLabel)

$midY += 30
$braveFeatures = @(
    @{ Name = "Disable Brave Rewards and Sponsored Elements"; Key = "BraveRewardsDisabled"; Value = 1; Type = "DWord"; ToolTip = "Disables Rewards and Brave-sponsored new tab imagery, not Brave Search ads. Some background ads key fetching may remain." },
    @{ Name = "Disable Brave Wallet"; Key = "BraveWalletDisabled"; Value = 1; Type = "DWord"; ToolTip = "Disables the built-in Brave Crypto Wallet.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Brave VPN"; Key = "BraveVPNDisabled"; Value = 1; Type = "DWord"; ToolTip = "Removes the Brave VPN integration and prompts.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Brave AI Chat"; Key = "BraveAIChatEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables Brave Leo (AI Chat) integration.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Local AI (On-Device)"; Key = "BraveLocalAiEnabled"; Value = 0; Type = "DWord"; ToolTip = "Keeps Local AI off. The Neo audit found it off by default on Release, but on in Beta and Nightly." },
    @{ Name = "Disable Tor"; Key = "TorDisabled"; Value = 1; Type = "DWord"; ToolTip = "Disables built-in Tor window support.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Sync"; Key = "SyncDisabled"; Value = 1; Type = "DWord"; ToolTip = "Disables Sync and removes this device from its sync chain. Rejoin with a code after lifting the policy." },
    @{ Name = "Disable Brave News"; Key = "BraveNewsDisabled"; Value = 1; Type = "DWord"; ToolTip = "Disables the News feed; some Windows profiles can still show an empty News sidebar panel." },
    @{ Name = "Disable Brave Talk"; Key = "BraveTalkDisabled"; Value = 1; Type = "DWord"; ToolTip = "Removes the built-in video calling integration.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Speedreader"; Key = "BraveSpeedreaderEnabled"; Value = 0; Type = "DWord"; ToolTip = "Completely disables the Speedreader feature, reader mode, and automatic prompts.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Wayback Machine Prompts"; Key = "BraveWaybackMachineEnabled"; Value = 0; Type = "DWord"; ToolTip = "Stops Brave from asking to search the Internet Archive when you hit a 404 error.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable XSLT"; Key = "XSLTEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables legacy XML transforms; some RSS feeds or sitemaps may display unstyled." },
    @{ Name = "Disable JavaScript Optimization"; Key = "DefaultJavaScriptOptimizerSetting"; Value = 2; Type = "DWord"; ToolTip = "Hardens the JavaScript engine at the cost of slower script-heavy sites." },
    @{ Name = "Force Site Isolation"; Key = "SitePerProcess"; Value = 1; Type = "DWord"; ToolTip = "Locks desktop site isolation on. Restart Brave." },
    @{ Name = "Isolate Origins"; Key = "OriginKeyedProcessesEnabled"; Value = 1; Type = "DWord"; ToolTip = "Separates most origins into processes; can increase RAM use. Restart Brave." },
    @{ Name = "Disable Google Image Descriptions"; Key = "AccessibilityImageLabelsEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables server-generated image descriptions for screen-reader users." },
    @{ Name = "Force YouTube Restricted Mode"; Key = "ForceYouTubeRestrict"; Value = 2; Type = "DWord"; ToolTip = "Enforces Strict Restricted Mode on YouTube." },
    @{ Name = "Block Safe Browsing Bypass"; Key = "SafeBrowsingProceedAnywayDisabled"; Value = 1; Type = "DWord"; ToolTip = "Prevents clicking through Safe Browsing warnings." },
    @{ Name = "Block Certificate Warning Bypass"; Key = "SSLErrorOverrideAllowed"; Value = 0; Type = "DWord"; ToolTip = "Prevents clicking through certificate errors." },
    @{ Name = "Prevent Deleting History"; Key = "AllowDeletingBrowserHistory"; Value = 0; Type = "DWord"; ToolTip = "Disables user-initiated history deletion in the browser." },
    @{ Name = "Disable App Launch Remember Option"; Key = "ExternalProtocolDialogShowAlwaysOpenCheckbox"; Value = 0; Type = "DWord"; ToolTip = "Removes the Always Allow checkbox from external app launch prompts." },
    @{ Name = "Block Camera Access"; Key = "VideoCaptureAllowed"; Value = 0; Type = "DWord"; ToolTip = "Blocks camera requests except where an explicit capture allowlist applies." },
    @{ Name = "Block Microphone Access"; Key = "AudioCaptureAllowed"; Value = 0; Type = "DWord"; ToolTip = "Blocks microphone requests except where an explicit capture allowlist applies." },
    @{ Name = "Block Command-Line Extensions"; Key = "ExtensionInstallTypeBlocklist"; Value = @("command_line"); Type = "List"; ToolTip = "Blocks --load-extension after restart, not --disable-extensions-except. Can break test shortcuts." },
    @{ Name = "Block Local Network Access"; Key = "LocalNetworkAccessBlockedForUrls"; Value = @("*"); Type = "List"; ToolTip = "Blocks local network requests from matching origins subject to higher-priority rules. Can break casting and local integrations." },
    @{ Name = "Block Browser Dynamic Code"; Key = "DynamicCodeSettings"; Value = 1; Type = "DWord"; ToolTip = "Windows browser-process hardening. May break third-party software such as print drivers; restart Brave." },
    @{ Name = "Disable Email Aliases"; Key = "BraveEmailAliasesEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables Brave's Email Aliases forwarding feature.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" }
)

$midY += $braveLabel.Height + 8
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
    $toolTip.SetToolTip($checkbox, (Get-PresetTooltip $feature.ToolTip $feature.Key))
    $midPanel.Controls.Add($checkbox)
    $allFeatures += $checkbox
    $marker = New-Object System.Windows.Forms.Label
    $marker.Text = '(?)'
    $marker.Size = New-Object System.Drawing.Size(27, 20)
    $marker.Visible = $false
    $midPanel.Controls.Add($marker)
    $script:featureMarkers[$feature.Key] = $marker
    $checkbox.Add_CheckedChanged({ if (-not $global:suspendDirtyTracking) { Update-PresetColor $this } })
    $midY += 28
}

$midY += 10
$perfLabel = New-Object System.Windows.Forms.Label
$perfLabel.Text = "Performance and Bloat"
$perfLabel.Font = New-Object System.Drawing.Font("Microsoft Sans Serif", 11, [System.Drawing.FontStyle]::Bold)
$perfLabel.Location = New-Object System.Drawing.Point(28, $midY)
$perfLabel.Size = New-Object System.Drawing.Size(300, 25)
$perfLabel.ForeColor = [System.Drawing.Color]::LightSalmon
$midPanel.Controls.Add($perfLabel)

$midY += 30
$perfFeatures = @(
    @{ Name = "Disable Background Mode"; Key = "BackgroundModeEnabled"; Value = 0; Type = "DWord"; ToolTip = "Prevents extensions/apps from running after the browser is closed.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Always Open PDF Externally"; Key = "AlwaysOpenPdfExternally"; Value = 1; Type = "DWord"; ToolTip = "Forces PDFs to download and open in your system viewer instead of the browser.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Disable Translate"; Key = "TranslateEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables automatic translation prompts.`n`nSuggested Settings for Privacy: Unticked | Security: Unticked" },
    @{ Name = "Disable Spellcheck"; Key = "SpellcheckEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables the built-in spellchecker completely to save CPU cycles.`n`nSuggested Settings for Privacy: Unticked | Security: Unticked" },
    @{ Name = "Disable Enhanced Spell Check"; Key = "SpellCheckServiceEnabled"; Value = 0; Type = "DWord"; ToolTip = "Drops the Google web-service callout while keeping offline spellcheck active.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable Search Suggestions"; Key = "SearchSuggestEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables predictive search suggestions in the URL bar.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable Printing"; Key = "PrintingEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables the browser print function.`n`nSuggested Settings for Privacy: Unticked | Security: Unticked" },
    @{ Name = "Disable Default Browser Prompt"; Key = "DefaultBrowserSettingEnabled"; Value = 0; Type = "DWord"; ToolTip = "Stops Brave from asking to be the default browser.`n`nSuggested Settings for Privacy: Ticked | Security: Unticked" },
    @{ Name = "Disable Developer Tools"; Key = "DeveloperToolsDisabled"; Value = 1; Type = "DWord"; ToolTip = "Blocks developer tools and may break Brave full-page screenshots." },
    @{ Name = "Disable Brave Playlist"; Key = "BravePlaylistEnabled"; Value = 0; Type = "DWord"; ToolTip = "Removes the Brave Playlist media feature.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Enable Memory Saver"; Key = "HighEfficiencyModeEnabled"; Value = 1; Type = "DWord"; ToolTip = "Forces Chromium High Efficiency Mode on to aggressively save RAM.`n`nSuggested Settings for Privacy: Unticked | Security: Unticked" },
    @{ Name = "Force Hardware Acceleration"; Key = "HardwareAccelerationModeEnabled_Force"; RegistryName = "HardwareAccelerationModeEnabled"; Value = 1; Type = "DWord"; ToolTip = "Pins the default hardware acceleration on so it can't drift.`n`nSuggested Settings for Privacy: Unticked | Security: Unticked" },
    @{ Name = "Disable Hardware Acceleration"; Key = "HardwareAccelerationModeEnabled_Disable"; RegistryName = "HardwareAccelerationModeEnabled"; Value = 0; Type = "DWord"; ToolTip = "Troubleshooting setting to turn off GPU acceleration. Fixes driver faults, screen-sharing bugs, and YouTube playback crashes.`n`nSuggested Settings for Privacy: Unticked | Security: Unticked" },
    @{ Name = "Disable Media Router (Cast)"; Key = "EnableMediaRouter"; Value = 0; Type = "DWord"; ToolTip = "Disables Chromecast casting support.`n`nSuggested Settings for Privacy: Unticked | Security: Unticked" }
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
    $toolTip.SetToolTip($checkbox, (Get-PresetTooltip $feature.ToolTip $feature.Key))
    $midPanel.Controls.Add($checkbox)
    $allFeatures += $checkbox
    $marker = New-Object System.Windows.Forms.Label
    $marker.Text = '(?)'
    $marker.Size = New-Object System.Drawing.Size(27, 20)
    $marker.Visible = $false
    $midPanel.Controls.Add($marker)
    $script:featureMarkers[$feature.Key] = $marker
    $checkbox.Add_CheckedChanged({ if (-not $global:suspendDirtyTracking) { Update-PresetColor $this } })
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
$accessLabel = New-Object System.Windows.Forms.Label
$accessLabel.Text = "Permissions & Access"
$accessLabel.Font = New-Object System.Drawing.Font("Microsoft Sans Serif", 11, [System.Drawing.FontStyle]::Bold)
$accessLabel.Location = New-Object System.Drawing.Point(28, $permY)
$accessLabel.Size = New-Object System.Drawing.Size(300, 25)
$accessLabel.ForeColor = [System.Drawing.Color]::LightSalmon
$rightPanel.Controls.Add($accessLabel)

$permY += 30
$accessFeatures = @(
    @{ Name = "Disable Guest Mode"; Key = "BrowserGuestModeEnabled"; Value = 0; Type = "DWord"; ToolTip = "Disables the guest profile escape hatch.`n`nSuggested Settings for Privacy: Unticked | Security: Ticked" },
    @{ Name = "Block All Extensions"; Key = "ExtensionInstallBlocklist"; Value = @("*"); Type = "List"; ToolTip = "Completely blocks all extension installations.`n`nSuggested Settings for Privacy: Unticked | Security: Unticked" },
    @{ Name = "Block Sideloaded Extensions"; Key = "BlockExternalExtensions"; Value = 1; Type = "DWord"; ToolTip = "Blocks silent extension installs while leaving user-chosen extensions working.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Force Google SafeSearch"; Key = "ForceGoogleSafeSearch"; Value = 1; Type = "DWord"; ToolTip = "Filters explicit search results.`n`nSuggested Settings for Privacy: Unticked | Security: Ticked" },
    @{ Name = "Force Incognito Mode"; Key = "IncognitoModeAvailability"; Value = 2; Type = "DWord"; ToolTip = "Forces the browser to always open in Incognito Mode.`n`nSuggested Settings for Privacy: Unticked | Security: Unticked" },
    @{ Name = "Block Remote Debugging"; Key = "RemoteDebuggingAllowed"; Value = 0; Type = "DWord"; ToolTip = "Stops the --remote-debugging-port cookie theft vector.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" },
    @{ Name = "Require HTTPS for Basic Auth"; Key = "BasicAuthOverHttpEnabled"; Value = 0; Type = "DWord"; ToolTip = "Stops base64 credentials from going out over cleartext HTTP.`n`nSuggested Settings for Privacy: Ticked | Security: Ticked" }
)

foreach ($feature in $accessFeatures) {
    $checkbox = New-Object System.Windows.Forms.CheckBox
    $checkbox.Text = $feature.Name
    $checkbox.Tag = $feature
    $checkbox.Location = New-Object System.Drawing.Point(30, $permY)
    $checkbox.Size = New-Object System.Drawing.Size(340, 25)
    $checkbox.Anchor = [System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Left
    $checkbox.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
    $checkbox.FlatAppearance.BorderSize = 1
    $checkbox.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(255, 80, 80, 80)
    $checkbox.FlatAppearance.CheckedBackColor = [System.Drawing.Color]::DodgerBlue
    $checkbox.Add_CheckedChanged({
        if ($this.Checked) { $this.ForeColor = [System.Drawing.Color]::DeepSkyBlue } else { $this.ForeColor = [System.Drawing.Color]::White }
        Check-DirtyState
    })
    $toolTip.SetToolTip($checkbox, (Get-PresetTooltip $feature.ToolTip $feature.Key))
    $rightPanel.Controls.Add($checkbox)
    $allFeatures += $checkbox
    $marker = New-Object System.Windows.Forms.Label
    $marker.Text = '(?)'
    $marker.Size = New-Object System.Drawing.Size(27, 20)
    $marker.Visible = $false
    $rightPanel.Controls.Add($marker)
    $script:featureMarkers[$feature.Key] = $marker
    $checkbox.Add_CheckedChanged({ if (-not $global:suspendDirtyTracking) { Update-PresetColor $this } })
    $permY += 28
}

$permY += 10
$permLabel = New-Object System.Windows.Forms.Label
$permLabel.Text = "Site Default Permissions"
$permLabel.Font = New-Object System.Drawing.Font("Microsoft Sans Serif", 11, [System.Drawing.FontStyle]::Bold)
$permLabel.Location = New-Object System.Drawing.Point(28, $permY)
$permLabel.Size = New-Object System.Drawing.Size(300, 25)
$permLabel.ForeColor = [System.Drawing.Color]::LightSalmon
$rightPanel.Controls.Add($permLabel)

$permY += 35
$permissionSettings = @(
    @{ Name = "Location"; Key = "DefaultGeolocationSetting"; Options = @("Not Set", "Ask", "Block", "Allow"); ToolTip = "Allows sites to request your physical location.`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "Notifications"; Key = "DefaultNotificationsSetting"; Options = @("Not Set", "Block", "Allow"); ToolTip = "Allows sites to send you native desktop push notifications.`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "JavaScript"; Key = "DefaultJavaScriptSetting"; Options = @("Not Set", "Allow", "Block"); ToolTip = "Allows sites to run interactive scripts. Blocking this breaks almost all websites.`n`nSuggested Settings for Privacy: Allow | Security: Allow" },
    @{ Name = "Images"; Key = "DefaultImagesSetting"; Options = @("Not Set", "Allow", "Block"); ToolTip = "Allows sites to load and display images.`n`nSuggested Settings for Privacy: Not Set | Security: Not Set" },
    @{ Name = "Pop-ups and Redirects"; Key = "DefaultPopupsSetting"; Options = @("Not Set", "Block", "Allow"); ToolTip = "Allows sites to open new windows or redirect you without your input.`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "USB Devices"; Key = "DefaultWebUsbGuardSetting"; Options = @("Not Set", "Ask", "Block"); ToolTip = "Allows sites to request direct connection to your plugged-in USB devices.`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "Serial Ports"; Key = "DefaultSerialGuardSetting"; Options = @("Not Set", "Ask", "Block"); ToolTip = "Allows sites to request connection to hardware via serial ports.`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "HID Devices"; Key = "DefaultWebHidGuardSetting"; Options = @("Not Set", "Ask", "Block"); ToolTip = "Allows sites to request access to Human Interface Devices (e.g. controllers).`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "File Editing"; Key = "DefaultFileSystemReadGuardSetting"; Options = @("Not Set", "Ask", "Block"); ToolTip = "Allows sites to read and save files directly to your local file system.`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "Clipboard"; Key = "DefaultClipboardSetting"; Options = @("Not Set", "Ask", "Block"); ToolTip = "Allows sites to read text and images copied to your clipboard.`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "Window Management"; Key = "DefaultWindowPlacementSetting"; Options = @("Not Set", "Ask", "Block"); ToolTip = "Allows sites to open windows on specific monitors or in fullscreen.`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "Local Fonts"; Key = "DefaultLocalFontsSetting"; Options = @("Not Set", "Ask", "Block"); ToolTip = "Allows sites to fingerprint your device based on locally installed fonts.`n`nSuggested Settings for Privacy: Block | Security: Block" },
    @{ Name = "Payment Handlers"; Key = "PaymentMethodQueryEnabled"; Options = @("Not Set", "Block", "Allow"); ToolTip = "Block hides saved payment capability: canMakePayment returns true; hasEnrolledInstrument returns false." },
    @{ Name = "Motion Sensors"; Key = "DefaultSensorsSetting"; Options = @("Not Set", "Block", "Allow"); ToolTip = "Allows sites to access device orientation and motion sensors.`n`nSuggested Settings for Privacy: Block | Security: Block" }
)

foreach ($p in $permissionSettings) {
    $lbl = New-Object System.Windows.Forms.Label
    $lbl.Text = $p.Name
    $lbl.Size = New-Object System.Drawing.Size(165, 20)
    $lbl.Location = New-Object System.Drawing.Point(30, $permY)
    $lbl.ForeColor = [System.Drawing.Color]::White
    $toolTip.SetToolTip($lbl, (Get-PresetTooltip $p.ToolTip $p.Key "Permission"))
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
    $toolTip.SetToolTip($cb, (Get-PresetTooltip $p.ToolTip $p.Key "Permission"))
    [void]$rightPanel.Controls.Add($cb)
    $allPerms += $cb
    $permY += 35
}

$permPad = New-Object System.Windows.Forms.Label
$permPad.Location = New-Object System.Drawing.Point(0, $permY)
$permPad.Size = New-Object System.Drawing.Size(10, 40)
[void]$rightPanel.Controls.Add($permPad)

# Mutual Exclusivity Logic for Hardware Acceleration
$haForceCb = $allFeatures | Where-Object { $_.Tag.Key -eq "HardwareAccelerationModeEnabled_Force" }
$haDisableCb = $allFeatures | Where-Object { $_.Tag.Key -eq "HardwareAccelerationModeEnabled_Disable" }
if ($haForceCb -and $haDisableCb) {
    $haForceCb.Add_CheckedChanged({ if ($this.Checked -and $haDisableCb.Checked) { $haDisableCb.Checked = $false } })
    $haDisableCb.Add_CheckedChanged({ if ($this.Checked -and $haForceCb.Checked) { $haForceCb.Checked = $false } })
}

$sbLabel = New-Object System.Windows.Forms.Label
$sbLabel.Text = "Safe Browsing:"
$sbLabel.Size = New-Object System.Drawing.Size(110, 20)
$form.Controls.Add($sbLabel)

$sbDropdown = New-Object System.Windows.Forms.ComboBox
$sbDropdown.Size = New-Object System.Drawing.Size(150, 20)
[void]$sbDropdown.Items.AddRange(@("On", "Enhanced", "Off"))
$sbDropdown.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$sbDropdown.BackColor = [System.Drawing.Color]::FromArgb(255, 25, 25, 25)
$sbDropdown.ForeColor = [System.Drawing.Color]::White
$sbDropdown.Add_SelectedIndexChanged({ Check-DirtyState })
$form.Controls.Add($sbDropdown)

$sbTooltip = Get-PresetTooltip 'On uses Standard Safe Browsing. Off disables it. Not Set leaves Brave defaults.' '' 'SafeBrowsing'
$toolTip.SetToolTip($sbDropdown, $sbTooltip)
$toolTip.SetToolTip($sbLabel, $sbTooltip)

$dnsLabel = New-Object System.Windows.Forms.Label
$dnsLabel.Text = "DNS Over HTTPS:"
$dnsLabel.Size = New-Object System.Drawing.Size(130, 20)
$form.Controls.Add($dnsLabel)

$dnsDropdown = New-Object System.Windows.Forms.ComboBox
$dnsDropdown.Size = New-Object System.Drawing.Size(150, 20)
[void]$dnsDropdown.Items.AddRange(@("Automatic", "Off", "Secure", "Custom"))
$dnsDropdown.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$dnsDropdown.BackColor = [System.Drawing.Color]::FromArgb(255, 25, 25, 25)
$dnsDropdown.ForeColor = [System.Drawing.Color]::White
$dnsDropdown.Add_SelectedIndexChanged({ Check-DirtyState })
$form.Controls.Add($dnsDropdown)

$dnsTooltip = Get-PresetTooltip 'Automatic can fall back to unencrypted DNS. Secure requires an HTTPS resolver.' '' 'DnsMode'
$toolTip.SetToolTip($dnsDropdown, $dnsTooltip)
$toolTip.SetToolTip($dnsLabel, $dnsTooltip)

$dnsTplLabel = New-Object System.Windows.Forms.Label
$dnsTplLabel.Text = "DoH Template:"
$dnsTplLabel.Size = New-Object System.Drawing.Size(110, 20)
$form.Controls.Add($dnsTplLabel)

$dnsTplInput = New-Object System.Windows.Forms.TextBox
$dnsTplInput.Size = New-Object System.Drawing.Size(300, 20)
$dnsTplInput.BackColor = [System.Drawing.Color]::FromArgb(255, 25, 25, 25)
$dnsTplInput.ForeColor = [System.Drawing.Color]::White
$dnsTplInput.BorderStyle = [System.Windows.Forms.BorderStyle]::FixedSingle
$dnsTplInput.Add_TextChanged({ Check-DirtyState })
$form.Controls.Add($dnsTplInput)

$dnsTplTooltip = Get-PresetTooltip 'Optional for Automatic; required for Secure or Custom.' '' 'Template'
$toolTip.SetToolTip($dnsTplInput, $dnsTplTooltip)
$toolTip.SetToolTip($dnsTplLabel, $dnsTplTooltip)

$exportButton = New-Object System.Windows.Forms.Button
$exportButton.Text = "Export Settings"
$exportButton.Font = $boldFont
$exportButton.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$exportButton.FlatAppearance.BorderSize = 0
$exportButton.BackColor = [System.Drawing.Color]::FromArgb(150, 102, 102, 102)
$exportButton.ForeColor = [System.Drawing.Color]::FromArgb(29, 255, 227)
$toolTip.SetToolTip($exportButton, "Export the current UI configuration to a JSON file.")
$form.Controls.Add($exportButton)

$importButton = New-Object System.Windows.Forms.Button
$importButton.Text = "Import Settings"
$importButton.Font = $boldFont
$importButton.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$importButton.FlatAppearance.BorderSize = 0
$importButton.BackColor = [System.Drawing.Color]::FromArgb(150, 102, 102, 102)
$importButton.ForeColor = [System.Drawing.Color]::LightSkyBlue
$toolTip.SetToolTip($importButton, "Import a JSON configuration file into the UI.")
$form.Controls.Add($importButton)

$pullButton = New-Object System.Windows.Forms.Button
$pullButton.Text = "Pull Settings from Brave"
$pullButton.Font = $boldFont
$pullButton.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$pullButton.FlatAppearance.BorderSize = 0
$pullButton.BackColor = [System.Drawing.Color]::FromArgb(150, 102, 102, 102)
$pullButton.ForeColor = [System.Drawing.Color]::FromArgb(251, 84, 43)
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
$toolTip.SetToolTip($resetButton, "Erase SlimBrave policy settings from the registry and restore to default.")
$form.Controls.Add($resetButton)

$global:baselineStateJson = ""

function Get-UIStateSnapshot {
    $snap = [ordered]@{
        Features = @()
        Permissions = [ordered]@{}
        SafeBrowsing = $sbDropdown.SelectedItem
        DnsMode = $dnsDropdown.SelectedItem
        DnsTemplate = $dnsTplInput.Text
    }
    $fList = @()
    foreach ($checkbox in $allFeatures) {
        if ($checkbox.Checked) {
            $fList += $checkbox.Tag.Key
        }
    }
    $snap.Features = $fList
    
    foreach ($perm in $allPerms) {
        if ($perm.SelectedItem -and $perm.SelectedItem -ne "Not Set") {
            $snap.Permissions[$perm.Tag.Key] = $perm.SelectedItem
        }
    }
    return $snap
}

function Update-Baseline {
    $script:presetPreview = $null
    foreach ($cb in $allFeatures) { Update-PresetColor $cb }
    $priorPresetSuspend = $global:suspendPresetTriggers
    $global:suspendPresetTriggers = $true
    try { $presetDropdown.SelectedIndex = -1 } finally { $global:suspendPresetTriggers = $priorPresetSuspend }
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
    $global:suspendPresetTriggers = $true
    
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
    if ($null -ne $stateObj.DnsTemplate) { $dnsTplInput.Text = $stateObj.DnsTemplate } else { $dnsTplInput.Text = "" }
    
    $global:suspendPresetTriggers = $false
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
    if ($savedState.DnsTemplate -ne $currentSnap.DnsTemplate) {
        $diffs += "DNS Template:`n  Expected: $($savedState.DnsTemplate) | Found: $($currentSnap.DnsTemplate)"
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

function Set-MiddleColumnLayout {
    $scrollY = -$midPanel.AutoScrollPosition.Y
    $midPanel.SuspendLayout()
    try {
        $midPanel.AutoScrollPosition = [System.Drawing.Point]::Empty
        $inset = 28
        $rowLeft = 30
        # Reserve room for the preview marker and a vertical scrollbar.
        $width = [Math]::Max(1, $midPanel.ClientSize.Width - $rowLeft - 36 - [System.Windows.Forms.SystemInformation]::VerticalScrollBarWidth)
        $y = 10
        foreach ($group in @(@{ Header = $braveLabel; Rows = $braveFeatures }, @{ Header = $perfLabel; Rows = $perfFeatures })) {
            $header = $group.Header
            $headerHeight = [Math]::Max(25, $header.Font.Height + 5)
            $header.SetBounds($inset, $y, $width, $headerHeight)
            $y += $headerHeight + 8
            foreach ($feature in $group.Rows) {
                $cb = $script:middleCheckboxes[$feature.Key]
                $marker = $script:featureMarkers[$feature.Key]
                $textWidth = [Math]::Max(1, $width - 34)
                $words = $feature.Name -split '\s+'
                $lines = @()
                $line = ''
                foreach ($word in $words) {
                    $candidate = if ($line) { "$line $word" } else { $word }
                    if ($line -and [System.Windows.Forms.TextRenderer]::MeasureText($candidate, $cb.Font).Width -gt $textWidth) {
                        $lines += $line
                        $line = $word
                    } else { $line = $candidate }
                }
                if ($line) { $lines += $line }
                $cb.Text = $lines -join "`r`n"
                $rowHeight = [Math]::Max(25, $lines.Count * ($cb.Font.Height + 2) + 8)
                $cb.SetBounds($rowLeft, $y, $width, $rowHeight)
                $marker.Location = New-Object System.Drawing.Point(($cb.Right + 2), ($y + [int](($rowHeight - $marker.Height) / 2)))
                $y += $rowHeight + 3
            }
            $y += 10
        }
        $midPad.Top = $y
        $midPad.Height = 8
        $midPanel.AutoScroll = ($midPad.Bottom -gt $midPanel.ClientSize.Height)
    } finally {
        $midPanel.ResumeLayout($true)
    }
    if ($midPanel.AutoScroll -and $scrollY -gt 0) {
        $midPanel.AutoScrollPosition = New-Object System.Drawing.Point(0, $scrollY)
    }
}

$script:middleCheckboxes = @{}
foreach ($cb in $allFeatures) {
    if ($cb.Parent -eq $midPanel) { $script:middleCheckboxes[$cb.Tag.Key] = $cb }
}

function Update-Layout {
    if ($form.ClientSize.Width -eq 0) { return }

    $channelLabel.Location = New-Object System.Drawing.Point(20, 24)
    $channelDropdown.Location = New-Object System.Drawing.Point(($channelLabel.Right + 15), 22)

    $totalTopWidth = $presetLabel.Width + $presetDropdown.Width + 10
    $startX = ($form.ClientSize.Width - $totalTopWidth) / 2
    $presetLabel.Location = New-Object System.Drawing.Point($startX, 24)
    $presetDropdown.Location = New-Object System.Drawing.Point(($presetLabel.Right + 5), 22)
    
    $statusPanel.Location = New-Object System.Drawing.Point(($form.ClientSize.Width - $statusPanel.Width - 20), 18)

    $panelWidth = [int](($form.ClientSize.Width - 80) / 3)
    $panelHeight = [int]($form.ClientSize.Height - 250)
    
    $leftPanel.Location = New-Object System.Drawing.Point(20, 70)
    $leftPanel.Size = New-Object System.Drawing.Size($panelWidth, $panelHeight)
    
    $midPanel.Location = New-Object System.Drawing.Point(($leftPanel.Right + 20), 70)
    $midPanel.Size = New-Object System.Drawing.Size($panelWidth, $panelHeight)

    $rightPanel.Location = New-Object System.Drawing.Point(($midPanel.Right + 20), 70)
    $rightPanel.Size = New-Object System.Drawing.Size($panelWidth, $panelHeight)

    Set-MiddleColumnLayout

    foreach ($cb in $allFeatures) {
        if ($cb.Parent -eq $midPanel) { continue }
        $cb.Width = $panelWidth - 95
        $marker = $script:featureMarkers[$cb.Tag.Key]
        $marker.Location = New-Object System.Drawing.Point(($cb.Right + 2), ($cb.Top + 3))
    }

    foreach ($panel in @($leftPanel, $rightPanel)) {
        $offset = $panel.AutoScrollPosition.Y
        $bottom = 0
        foreach ($control in $panel.Controls) {
            if ($control.Bottom - $offset -gt $bottom) { $bottom = $control.Bottom - $offset }
        }
        if ($bottom -le $panel.ClientSize.Height) {
            $panel.AutoScrollPosition = [System.Drawing.Point]::Empty
            $panel.AutoScroll = $false
        } else {
            $panel.AutoScroll = $true
        }
    }

    $bottomY = $leftPanel.Bottom + 20
    
    $sbLabel.Location = New-Object System.Drawing.Point($leftPanel.Left, ($bottomY + 3))
    $dnsLabel.Location = New-Object System.Drawing.Point($leftPanel.Left, ($bottomY + 35))

    $alignedDropdownX = $dnsLabel.Right + 5
    $sbDropdown.Location = New-Object System.Drawing.Point($alignedDropdownX, $bottomY)
    $dnsDropdown.Location = New-Object System.Drawing.Point($alignedDropdownX, ($bottomY + 32))

    $dnsTplLabel.Location = New-Object System.Drawing.Point(($dnsDropdown.Right + 20), ($bottomY + 35))
    $dnsTplInput.Location = New-Object System.Drawing.Point(($dnsTplLabel.Right + 5), ($bottomY + 32))

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
    Set-RoundedCorners $exportButton 10
    Set-RoundedCorners $importButton 10
    Set-RoundedCorners $pullButton 10
    Set-RoundedCorners $saveButton 10
    Set-RoundedCorners $resetButton 10
    Set-RoundedCorners $statusPanel 10
}

$form.Add_Resize({ Update-Layout })

function Reload-UIFromRegistry {
    $global:suspendDirtyTracking = $true
    $global:suspendPresetTriggers = $true

    foreach ($checkbox in $allFeatures) {
        $checkbox.Checked = $false
        $checkbox.ForeColor = [System.Drawing.Color]::White
    }
    foreach ($perm in $allPerms) {
        $perm.SelectedItem = "Not Set"
    }
    $sbDropdown.SelectedIndex = -1
    $dnsDropdown.SelectedIndex = -1
    $dnsTplInput.Text = ""

    $regProps = Get-ItemProperty -Path $global:registryPath -ErrorAction SilentlyContinue

    if ($null -ne $regProps) {
        foreach ($checkbox in $allFeatures) {
            $feature = $checkbox.Tag
            $regName = if ($feature.RegistryName) { $feature.RegistryName } else { $feature.Key }
            
            if ($feature.Type -eq "List") {
                $listPath = Join-Path $global:registryPath $regName
                if (Test-SlimBraveList $feature) {
                    $checkbox.Checked = $true
                }
            } else {
                $val = $regProps.($regName)
                if ($null -ne $val -and $val -eq $feature.Value) {
                    $checkbox.Checked = $true
                }
            }
        }

        foreach ($perm in $allPerms) {
            $k = $perm.Tag.Key
            $val = $regProps.$k
            if ($null -ne $val) {
                if ($val -eq 3 -and $perm.Items.Contains("Ask")) { $perm.SelectedItem = "Ask" }
                elseif ($val -eq 1 -and $perm.Items.Contains("Allow")) { $perm.SelectedItem = "Allow" }
                elseif ($k -eq "PaymentMethodQueryEnabled" -and $val -eq 0) { $perm.SelectedItem = "Block" }
                elseif ($val -eq 2) { $perm.SelectedItem = "Block" }
                else { $perm.SelectedItem = "Not Set" }
            }
        }

        if ($null -ne $regProps.SafeBrowsingProtectionLevel) {
            if ($regProps.SafeBrowsingProtectionLevel -eq 1) { $sbDropdown.SelectedItem = "On" }
            elseif ($regProps.SafeBrowsingProtectionLevel -eq 2) { $sbDropdown.SelectedItem = "Enhanced" }
            elseif ($regProps.SafeBrowsingProtectionLevel -eq 0) { $sbDropdown.SelectedItem = "Off" }
        }

        if ($null -ne $regProps.DnsOverHttpsMode) {
            if ($regProps.DnsOverHttpsMode -eq "automatic") { $dnsDropdown.SelectedItem = "Automatic" }
            elseif ($regProps.DnsOverHttpsMode -eq "off") { $dnsDropdown.SelectedItem = "Off" }
            elseif ($regProps.DnsOverHttpsMode -eq "secure") {
                if ([string]::IsNullOrWhiteSpace($regProps.DnsOverHttpsTemplates)) {
                    $dnsDropdown.SelectedItem = "Secure"
                } else {
                    $dnsDropdown.SelectedItem = "Secure"
                }
            }
        }
        
        if ($null -ne $regProps.DnsOverHttpsTemplates) {
            $dnsTplInput.Text = $regProps.DnsOverHttpsTemplates
        }
    }

    $global:suspendPresetTriggers = $false
    $global:suspendDirtyTracking = $false
    Update-Baseline
    Check-DirtyState
}

$pullButton.Add_Click({
    Reload-UIFromRegistry
    Update-Status "UI reloaded from current Brave registry settings."
})

$saveButton.Add_Click({
    $mode = $dnsDropdown.SelectedItem
    try { Assert-DoHTemplate $mode $dnsTplInput.Text } catch {
        [void][System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'DNS validation failed')
        return
    }

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
    
    try {
        foreach ($checkbox in $allFeatures) {
            $feature = $checkbox.Tag
            $regName = if ($feature.RegistryName) { $feature.RegistryName } else { $feature.Key }
            
            if ($checkbox.Checked) {
                try {
                    if ($feature.Type -eq "List") {
                        $listPath = Join-Path $global:registryPath $regName
                        if (Test-Path -LiteralPath $listPath) {
                            if (-not (Test-SlimBraveList $feature)) { throw "Existing $regName list differs; it was not overwritten." }
                            continue
                        }
                        [void](New-Item -Path $listPath -Force -ErrorAction Stop)
                        $i = 1
                        foreach ($item in $feature.Value) {
                            [void](Set-ItemProperty -Path $listPath -Name $i.ToString() -Value $item -Type String -Force -ErrorAction Stop)
                            $i++
                        }
                    } else {
                        [void](Set-ItemProperty -Path $global:registryPath -Name $regName -Value $feature.Value -Type $feature.Type -Force -ErrorAction Stop)
                    }
                    Write-Log "Successfully applied policy: $regName"
                } catch {
                    throw "Could not apply $($regName): $_"
                }
            } else {
                # Smart removal: Check if another enabled property shares this exact RegistryName
                $isManagedByOther = $false
                foreach ($otherCb in $allFeatures) {
                    if ($otherCb -ne $checkbox -and $otherCb.Checked) {
                        $otherRegName = if ($otherCb.Tag.RegistryName) { $otherCb.Tag.RegistryName } else { $otherCb.Tag.Key }
                        if ($otherRegName -eq $regName) { 
                            $isManagedByOther = $true
                            break 
                        }
                    }
                }
                if (-not $isManagedByOther) {
                    try {
                        if ($feature.Type -eq "List") {
                            $listPath = Join-Path $global:registryPath $regName
                            Remove-SlimBraveList $feature
                        } else {
                            Remove-BravePolicyValue $regName
                        }
                    } catch { throw }
                }
            }
        }

        foreach ($perm in $allPerms) {
            $sel = $perm.SelectedItem
            $k = $perm.Tag.Key
            if (-not $sel -or $sel -eq "Not Set") {
                Remove-BravePolicyValue $k
                if ($k -eq "DefaultFileSystemReadGuardSetting") {
                    Remove-BravePolicyValue "DefaultFileSystemWriteGuardSetting"
                }
            } else {
                $val = 0
                if ($sel -eq "Ask") { $val = 3 }
                if ($sel -eq "Block") {
                    if ($k -eq "PaymentMethodQueryEnabled") { $val = 0 } else { $val = 2 }
                }
                if ($sel -eq "Allow") { $val = 1 }
                try {
                    [void](Set-ItemProperty -Path $global:registryPath -Name $k -Value $val -Type DWord -Force -ErrorAction Stop)
                    if ($k -eq "DefaultFileSystemReadGuardSetting") {
                        [void](Set-ItemProperty -Path $global:registryPath -Name "DefaultFileSystemWriteGuardSetting" -Value $val -Type DWord -Force -ErrorAction Stop)
                    }
                    Write-Log "Successfully applied permission policy: $k = $val"
                } catch {
                    throw "Could not apply $($k): $_"
                }
            }
        }
        
        if ($sbDropdown.SelectedItem) {
            if ($sbDropdown.SelectedItem -eq "On") {
                [void](Set-ItemProperty -Path $global:registryPath -Name "SafeBrowsingProtectionLevel" -Value 1 -Type DWord -Force -ErrorAction Stop)
                Write-Log "Set SafeBrowsingProtectionLevel to 1 (On)"
            } elseif ($sbDropdown.SelectedItem -eq "Off") {
                [void](Set-ItemProperty -Path $global:registryPath -Name "SafeBrowsingProtectionLevel" -Value 0 -Type DWord -Force -ErrorAction Stop)
                Write-Log "Set SafeBrowsingProtectionLevel to 0 (Off)"
            } elseif ($sbDropdown.SelectedItem -eq 'Enhanced') {
                [void](Set-ItemProperty -Path $global:registryPath -Name 'SafeBrowsingProtectionLevel' -Value 2 -Type DWord -ErrorAction Stop)
            } else {
                Remove-BravePolicyValue "SafeBrowsingProtectionLevel"
            }
        }

        if ($mode -in @('Automatic','Secure','Custom')) {
            if ($dnsTplInput.Text.Trim()) {
                [void](Set-ItemProperty -Path $global:registryPath -Name 'DnsOverHttpsTemplates' -Value $dnsTplInput.Text.Trim() -Type String -Force -ErrorAction Stop)
            } else { Remove-BravePolicyValue 'DnsOverHttpsTemplates' }
            if ($mode -eq 'Automatic') { Set-DnsMode 'automatic' } else { Set-DnsMode 'secure' }
        } elseif ($mode -eq 'Off') {
            Set-DnsMode 'off'
            Remove-BravePolicyValue 'DnsOverHttpsTemplates'
        } else {
            Remove-BravePolicyValue 'DnsOverHttpsMode'
            Remove-BravePolicyValue 'DnsOverHttpsTemplates'
        }
        Remove-RetiredPolicies

    } catch {
        Set-DirtyState $true
        Update-Status 'Apply failed; earlier registry writes may have succeeded.'
        [void][System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'Apply failed')
        return
    }

    Save-CurrentState
    Update-Baseline
    Check-DirtyState
    Update-Status "Settings applied successfully!"

    [void][System.Windows.Forms.MessageBox]::Show('Settings applied. Restart Brave normally if needed, then check brave://policy.', 'SlimBrave')
})

function Reset-AllSettings {
    $confirm = [System.Windows.Forms.MessageBox]::Show(
        "Warning: This will erase all SlimBrave policy settings from the registry. Do you wish to continue?", 
        "Confirm SlimBrave Reset", 
        [System.Windows.Forms.MessageBoxButtons]::YesNo, 
        [System.Windows.Forms.MessageBoxIcon]::Warning
    )
    
    if ($confirm -eq "Yes") {
        Update-Status "Resetting SlimBrave settings..."
        try {
            Remove-RetiredPolicies
            foreach ($cb in $allFeatures) {
                $feature = $cb.Tag
                $regName = if ($feature.RegistryName) { $feature.RegistryName } else { $feature.Key }
                
                if ($feature.Type -eq "List") {
                    $listPath = Join-Path $global:registryPath $regName
                    Remove-SlimBraveList $feature
                } else {
                    Remove-BravePolicyValue $regName
                }
            }

            foreach ($perm in $allPerms) {
                Remove-BravePolicyValue $perm.Tag.Key
            }

            Remove-BravePolicyValue "SafeBrowsingProtectionLevel"
            Remove-BravePolicyValue "DnsOverHttpsMode"
            Remove-BravePolicyValue "DnsOverHttpsTemplates"
            Remove-BravePolicyValue "DefaultFileSystemWriteGuardSetting"

            $global:suspendPresetTriggers = $true
            $global:suspendDirtyTracking = $true
            
            foreach ($cb in $allFeatures) { 
                 $cb.Checked = $false 
                 $cb.ForeColor = [System.Drawing.Color]::White 
             }
            foreach ($perm in $allPerms) { $perm.SelectedItem = "Not Set" }
            $sbDropdown.SelectedIndex = -1
            $dnsDropdown.SelectedIndex = -1
            $dnsTplInput.Text = ""
            
            $global:suspendDirtyTracking = $false
            $global:suspendPresetTriggers = $false

            Write-Log "SlimBrave settings successfully wiped from registry."
            
            [System.Windows.Forms.MessageBox]::Show(
                "All SlimBrave policy settings have been successfully reset.", 
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
        if (-not (Test-Path -Path $global:registryPath)) {
            [void](New-Item -Path $global:registryPath -Force)
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
    
    $docsPath = [Environment]::GetFolderPath("MyDocuments")
    try {
        $invokingUser = (Get-CimInstance Win32_ComputerSystem).UserName
        if ($invokingUser) {
            $username = $invokingUser.Split('\')[-1]
            $testPath = "C:\Users\$username\Documents"
            if (Test-Path $testPath) { $docsPath = $testPath }
        }
    } catch {}
    
    $saveFileDialog.InitialDirectory = $docsPath
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


function Read-SlimBraveImport ([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    try {
        if ($stream.Length -gt 1MB) { throw 'Settings file exceeds 1 MiB.' }
        $reader = New-Object IO.StreamReader($stream, [Text.Encoding]::UTF8, $true)
        try { $raw = $reader.ReadToEnd() } finally { $reader.Dispose() }
    } finally { $stream.Dispose() }
    if (-not $raw.TrimStart().StartsWith('{')) { throw 'Expected a JSON settings object.' }
    $obj = ConvertFrom-Json -InputObject $raw -ErrorAction Stop
    if ($obj -isnot [pscustomobject]) { throw 'Expected a JSON settings object.' }
    $notes = New-Object 'System.Collections.Generic.List[string]'
    foreach ($prop in $obj.PSObject.Properties) {
        if ($prop.Name -cnotin @('Features','Permissions','SafeBrowsing','DnsMode','DnsTemplate')) { $notes.Add('Unknown field') }
    }
    $keys = @()
    if ($null -ne $obj.Features) {
        if ($obj.Features -isnot [array]) { throw 'Features must be an array.' }
        foreach ($k in $obj.Features) {
            if ($k -isnot [string]) { throw 'Feature identifiers must be strings.' }
            $match = $allFeatures | Where-Object { $_.Tag.Key -ceq $k } | Select-Object -First 1
            if (-not $match) {
                $notes.Add('Ignored feature: ' + (($k -replace '[\p{Cc}\p{Cf}]','') | ForEach-Object { $_.Substring(0,[Math]::Min(80,$_.Length)) }))
                continue
            }
            $reg = $match.Tag.RegistryName
            if ($reg) {
                foreach ($other in $allFeatures) {
                    if ($other.Tag.RegistryName -eq $reg -and $other.Tag.Key -cne $k -and $other.Tag.Key -cin $keys) {
                        $keys = @($keys | Where-Object { $_ -cne $other.Tag.Key })
                        $notes.Add("Replaced conflicting feature: $($other.Tag.Key)")
                    }
                }
            }
            if ($k -cnotin $keys) { $keys += $k }
        }
    }
    $perms = [ordered]@{}
    if ($null -ne $obj.Permissions) {
        if ($obj.Permissions -isnot [pscustomobject]) { throw 'Permissions must be a JSON object.' }
        foreach ($prop in $obj.Permissions.PSObject.Properties) {
            $match = $allPerms | Where-Object { $_.Tag.Key -ceq $prop.Name } | Select-Object -First 1
            if (-not $match -or $prop.Value -isnot [string] -or $prop.Value -cnotin $match.Tag.Options) {
                $notes.Add('Ignored unsupported permission or value: ' + (($prop.Name -replace '[\p{Cc}\p{Cf}]','') | ForEach-Object { $_.Substring(0,[Math]::Min(80,$_.Length)) }))
                continue
            }
            $perms[$prop.Name] = $prop.Value
        }
    }
    if ($null -ne $obj.SafeBrowsing -and ($obj.SafeBrowsing -isnot [string] -or $obj.SafeBrowsing -cnotin @('On','Off','Enhanced'))) { throw 'Invalid Safe Browsing setting.' }
    if ($null -ne $obj.DnsMode -and ($obj.DnsMode -isnot [string] -or $obj.DnsMode -cnotin @('Automatic','Off','Secure','Custom'))) { throw 'Invalid DNS mode.' }
    if ($null -ne $obj.DnsTemplate -and $obj.DnsTemplate -isnot [string]) { throw 'DNS template must be text.' }
    Assert-DoHTemplate $obj.DnsMode $obj.DnsTemplate
    if (-not ($keys.Count -or $perms.Count -or $obj.SafeBrowsing -or $obj.DnsMode)) { throw 'No applicable settings; the current selections were preserved.' }
    return [pscustomobject]@{
        State = [pscustomobject]@{ Features = $keys; Permissions = [pscustomobject]$perms; SafeBrowsing = $obj.SafeBrowsing; DnsMode = $obj.DnsMode; DnsTemplate = $obj.DnsTemplate }
        Notes = $notes
    }
}

$importButton.Add_Click({
    $openFileDialog = New-Object System.Windows.Forms.OpenFileDialog
    $openFileDialog.Filter = "JSON files (*.json)|*.json|All files (*.*)|*.*"
    $openFileDialog.Title = "Import SlimBrave Settings"
    
    $docsPath = [Environment]::GetFolderPath("MyDocuments")
    try {
        $invokingUser = (Get-CimInstance Win32_ComputerSystem).UserName
        if ($invokingUser) {
            $username = $invokingUser.Split('\')[-1]
            $testPath = "C:\Users\$username\Documents"
            if (Test-Path $testPath) { $docsPath = $testPath }
        }
    } catch {}
    
    $openFileDialog.InitialDirectory = $docsPath
    
    if ($openFileDialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        try {
            $result = Read-SlimBraveImport $openFileDialog.FileName
            $prior = Get-UIStateSnapshot | ConvertTo-Json -Depth 4 | ConvertFrom-Json
            try {
                Restore-StateToUI $result.State
                foreach ($cb in $allFeatures) { Update-PresetColor $cb }
            } catch {
                Restore-StateToUI $prior
                throw
            }
            $message = 'Settings staged. Review them before clicking Apply.'
            if ($result.Notes.Count) {
                $message += "`n`n" + (($result.Notes | Select-Object -First 5) -join "`n")
                if ($result.Notes.Count -gt 5) { $message += "`nand $($result.Notes.Count - 5) more." }
            }
            Update-Status 'Settings imported; review before applying.'
            [void][System.Windows.Forms.MessageBox]::Show($message, 'Import successful')
        } catch {
            Write-Log "Import Failed: $_"
            [System.Windows.Forms.MessageBox]::Show("Failed to import settings: $_", "Import Failed", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
        }
    }
})

Write-Log "SlimBrave UI Loaded successfully."
$form.Add_Shown({
    $form.ActiveControl = $null
})

Reload-UIFromRegistry
Update-Layout

[void] $form.ShowDialog()
