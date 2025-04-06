# Changelog

All notable changes to this project will be documented in this file.

---

## [v1.5.1] - Documentation Updates
**Release Date**: 2025-04-06

### Added
- Updated `README.md` with detailed usage instructions, including examples for single and batch downloads.
- Added information about the `-w` argument for parallel downloads.
- Included troubleshooting tips and common error fixes.

### Changed
- Improved the `help()` function to include a description of the `-w` argument.

---

## [v1.5.0] - Improved Source Detection and Bait Handling
**Release Date**: 2025-04-06

### Added
- Introduced functionality to identify and ignore "bait" sources using a predefined list.
- Enhanced Method 6 to support additional patterns like `var a168c = '...'` for extracting encoded sources.
- Added a `clean_base64` function to safely handle and validate Base64 strings.

### Changed
- Improved error handling and debugging output for better traceability.
- Ensured flexibility by allowing easy extension of "bait" patterns and encoded source patterns.

---

## [v1.4.0] - Forked by MPZ-00
**Release Date**: 2025-01-14

### Changed
- General improvements and fixes to the downloader script.

---

## [v1.3.1] - Forked by HerobrineTV
**Release Date**: 2025-03-15

### Fixed
- Resolved issues with finding download links.
- Updated the script to handle changes in voe.sx URLs, including Base64-encoded keys.
- Added more user agents to better mimic browser behavior.

---

## [v1.2.4] - Initial Stable Release
**Release Date**: 2024-07-15

### Added
- Basic functionality to download single and multiple videos from `voe.sx`.
- Support for batch downloads using a file with links.
- Output videos saved in the same folder where the script is executed.

---

## [v1.2.3] - Help Description Updated
**Release Date**: 2024-07-14

### Changed
- Revised the help descriptions to provide clearer guidance on the tool's usage.

---

## [v1.2.2] - Site Update Compatibility
**Release Date**: 2024-04-21

### Fixed
- Adjusted the script to accommodate changes made to the voe.sx site.

---

## [v1.2.1] - Site Structure Adaptation
**Release Date**: 2024-02-26

### Fixed
- Updated the script in response to structural changes on the voe.sx site to ensure continued functionality.

---

## [v1.2.0] - Site Structure Update
**Release Date**: 2024-02-23

### Fixed
- Modified the script to align with recent changes to the voe.sx site.

---

## [v1.1.1] - Extended Support for Embedded Links
**Release Date**: 2023-05-11

### Added
- Added functionality to handle embedded voe.sx links, expanding the tool's versatility.

---

## [v1.1.0] - HLS Stream Download Support
**Release Date**: 2023-04-21

### Added
- Introduced support for downloading HLS streams from voe.sx, addressing the removal of direct MP4 links from the site.

---

## [v1.0.1] - Bug Fix
**Release Date**: 2023-02-24

### Fixed
- Implemented a minor bug fix caused by changes on the voe.sx platform to maintain download reliability.

---

## [v1.0.0] - Initial Release
**Release Date**: 2023-01-18

### Added
- Launched the first version of `voe-dl`, a Python-based downloader for voe.sx videos.
- Provided both Windows and Linux executables.
