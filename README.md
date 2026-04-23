# iOS Extraction Scripts

Pull IPA or app data container from a jailbroken iOS device over SSH.
## Requirements

- Jailbroken iOS device
- OpenSSH installed on device (Sileo/Cydia package `openssh`)
- Device reachable over network (USB-over-IP or Wi-Fi)
- `ssh` + `scp` on host machine
- `zip` and `tar` on device (ships with most jailbreaks)

## One-time SSH key setup

Avoid typing password on every call.

```bash
ssh-keygen -t ed25519 -N ""
ssh-copy-id mobile@192.168.1.17
```

Windows (no `ssh-copy-id`):

```bash
type %USERPROFILE%\.ssh\id_ed25519.pub | ssh mobile@192.168.1.17 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Verify:

```bash
ssh mobile@192.168.1.17
```

Should connect without prompt.

## Environment

Scripts read `IOS_USER` and `IOS_HOST`:

```bash
export IOS_USER=mobile
export IOS_HOST=192.168.1.17
```

Defaults: `root@iphone.local`.

Note: `mobile` user may hit permission errors on some bundle or data paths. If `tar`/`cp` fails with `Permission denied`, use `root` instead.

## Usage

### Extract IPA

By bundle id (walks containers, greps Info.plist):

```bash
python3 extract_ipa.py com.example.app
```

By known bundle container UUID (direct, faster):

```bash
python3 extract_ipa.py --uuid 1A2B3C4D-5E6F-7G8H-9I0J-1K2L3M4N5O6P
```

Output: `<identifier>.ipa` in current directory.

### Extract app data container

By bundle id:

```bash
python3 extract_iad.py com.example.app
```

By known data container UUID:

```bash
python3 extract_iad.py --uuid 9Z8Y7X6W-5V4U-3T2S-1R0Q-PONMLKJIHGFE
```

Output: `<identifier>_data.tar.gz` + extracted folder.

## Bundle UUID vs Data UUID

Two different random UUIDs per installed app:

- **Bundle UUID** → `/var/containers/Bundle/Application/<UUID>/AppName.app` (binary, assets)
- **Data UUID** → `/var/mobile/Containers/Data/Application/<UUID>/` (Documents, Library, tmp)

They do not match. Use the correct UUID for the correct script, or pass the bundle id and let the script find both.

## Unzipping the IPA

IPA = zip archive.

```bash
unzip com.example.app.ipa -d com.example.app
```

Windows PowerShell (rename `.ipa` to `.zip` first if Expand-Archive refuses):

```powershell
Expand-Archive com.example.app.ipa -DestinationPath com.example.app
```

Structure:

```
Payload/
└── AppName.app/
    ├── AppName              Mach-O binary
    ├── Info.plist
    ├── *.nib, *.car, assets
    └── _CodeSignature/
```

## FairPlay encryption

App Store apps are FairPlay-encrypted. A raw `.app` copy from Bundle container yields an encrypted binary — useless for static analysis.

Check with `otool -l AppName | grep -A4 LC_ENCRYPTION_INFO`. If `cryptid 1`, encrypted.

For a decrypted IPA use:

- `frida-ios-dump` — https://github.com/AloneMonkey/frida-ios-dump
- `bagbak` — https://github.com/ChiChou/bagbak

These dump the decrypted image from a running process.

## Security notes

- Default jailbreak root password is `alpine`. Change via `passwd` on device before exposing SSH to any network.
- Prefer key auth over passwords.
- Never commit your SSH private key.
