T-Net validated updater-only repair
================================
This package repairs ONLY Apply_Update.ps1 in your installed T-Net folder.
It does not replace AirtelDataMonitor.exe, monitor.ps1, settings, or data history.

1. Extract this ZIP into a separate folder.
2. Close T-Net normally (including from the system tray).
3. Double-click REPAIR_UPDATER.cmd.
4. Confirm "UPDATER REPAIR INSTALLED".
5. Launch your existing T-Net shortcut and click "Check for updates".

Default installation: %LOCALAPPDATA%\AirtelDataMonitor
Existing updater gets a timestamped backup, and its replacement is limited to Apply_Update.ps1.

If installed elsewhere, open PowerShell in the extracted folder and run:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\Install_Updater_Repair.ps1" -InstallDir "C:\YOUR\EXISTING\TNET"

If a future update fails, the detailed error is displayed and stored at:
%LOCALAPPDATA%\AirtelDataMonitor\update-last-error.log

Normal update behavior:
- Exact full executable-path process check (not just executable name).
- The updater ignores its own powershell.exe process.
- Exclusive access must be possible for the target EXE and monitor.ps1.
- Re-checks locks after compilation, before replacement.
- Creates rollback backups and restores both files on partial failure.
- Never reads or writes data\usage.json, data\usage-timeline.csv, or saved settings.

Windows CI tests include successful update with T-Net closed, running installed app,
unrelated same-name process, locked engine, and data preservation. Real-device verification
on your laptop is still recommended.
