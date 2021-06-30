# Release Notes

For: uc-cdis/gen3utils

Notes since tag: 0.6.8

Notes to tag/commit: 0a5aef76b810f5a8beaf442b3982aad55fd49b6b

Generated: 2021-06-30



## New Features
  - A Check to verify workspaces run in commons only if netpolicy is "on" in
    their global block of manifest.json (#64)

## Improvements
  - Fix duplicate org name in PR links (#71)
  - Use booleans in manifest validation configuration instead of true/false
    strings (#68)

## Bug Fixes
  - `footerLogos` in portal config is optional, but when present, it must be an
    array (list) (#70)
