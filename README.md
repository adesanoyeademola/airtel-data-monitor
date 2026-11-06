# Airtel Data Monitor

Windows data-usage monitoring for an Android Airtel hotspot.

## Status
The public update channel is being configured. **There is no installable update published yet.**

## Update design
Future signed-off releases will provide a version manifest, downloadable Windows update package and SHA-256 checksum. An updater installed on Windows will verify the package before updating the existing app. It will retain local history and settings, offer an explicit update confirmation and support rollback.

The update mechanism measures Windows adapter traffic, **not** carrier-billed data or iPhone traffic.

## Privacy
Never upload SIM information, personal usage records, local application settings, credentials, tokens or files from `%LOCALAPPDATA%\AirtelDataMonitor` to this public repository.
