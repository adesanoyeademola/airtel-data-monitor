# T-Net iPhone: beta installation from Windows

This iPhone edition is entirely independent of T-Net Windows. It records available on-device network interface counters and attempts to catch up when reopened. It does not require a VPN or Android-side application.

## Obtain the iPhone app

The **Build T-Net iPhone IPA** GitHub Actions workflow builds on a macOS runner. Its release is **T-Net iPhone 0.1 (Unsigned Beta)**, with the asset `T-Net-iPhone-v0.1-unsigned.ipa`. If a release is not visible, the build has not succeeded.

## Install from Windows 11

1. Download the unsigned IPA from the repository's [Releases](https://github.com/adesanoyeademola/airtel-data-monitor/releases).
2. Download [Sideloadly](https://sideloadly.io/) from its official website and follow its Windows setup for Apple device drivers.
3. Connect your unlocked iPhone to Windows with a USB data cable. Tap **Trust** if prompted.
4. In Sideloadly select your iPhone, drag in the IPA, sign in **locally in Sideloadly** with your own Apple Account and start sideloading.
5. On the iPhone, follow device-management trust instructions if prompted and enable **Developer Mode** under **Settings → Privacy & Security** if required. iOS may restart during this setup.
6. Open **T-Net** from the Home Screen. Grant Background App Refresh where available.
7. With a free Apple Account, renew the app signature every 7 days; Sideloadly can automate refreshing if paired with the Windows computer (via USB or Wi-Fi). This is an Apple signing requirement, **not** a connection needed for T-Net's usage monitoring.

**Never share your Apple password or verification code in this GitHub repository or with ChatGPT.** Enter credentials only into the chosen local signing tool.

## Limits of this beta

- iOS can suspend the app in the background. Accumulated counters may be available on return, but uninterrupted monitoring and exact accounting are not guaranteed.
- Interface names `en0` and `pdp_ip*` are heuristics, not a public guarantee. Test real-device readings.
- First launch establishes a baseline; previous usage cannot be recovered.
- Long sampling gaps, restarts, interface changes, or counter resets may omit usage or misallocate usage across dates.
- The app does not fetch Airtel balance. It does not use a VPN.
- The first iPhone build is not verified on the user's device and may need further fixes.

This repository contains unsigned source and release assets only. No usage records, Apple ID, signing keys, or device identifiers should be added to the public repository.
