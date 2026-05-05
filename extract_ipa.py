#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

DEVICE_USER = os.environ.get("IOS_USER", "root")
DEVICE_HOST = os.environ.get("IOS_HOST", "iphone.local")
PORT = "2222"

def ssh(cmd):
    return subprocess.run(
        ["ssh", "-p", PORT, f"{DEVICE_USER}@{DEVICE_HOST}", cmd],
        capture_output=True, text=True, check=True
    )

def find_app_path_by_bundle_id(bundle_id):
    # Walk Bundle containers, grep ASCII bundle id out of binary Info.plist
    cmd = (
        f'for p in /var/containers/Bundle/Application/*/*.app; do '
        f'grep -a -q "{bundle_id}" "$p/Info.plist" 2>/dev/null && echo "$p" && break; '
        f'done'
    )
    result = ssh(cmd)
    path = result.stdout.strip()
    if not path:
        print(f".app not found for bundle id: {bundle_id}")
        print("Check bundle id, or app may be system app in /Applications")
        sys.exit(1)
    return path

def find_app_path_by_uuid(uuid):
    # Bundle UUID dir has exactly one *.app inside
    container = f"/var/containers/Bundle/Application/{uuid}"
    result = ssh(f'ls -d {container}/*.app 2>/dev/null')
    path = result.stdout.strip().splitlines()
    if not path:
        print(f".app not found under {container}")
        print("Check UUID, or this may be a data UUID, not a bundle UUID")
        sys.exit(1)
    return path[0]

def extract_ipa(identifier, by_uuid):
    try:
        if by_uuid:
            app_path = find_app_path_by_uuid(identifier)
        else:
            app_path = find_app_path_by_bundle_id(identifier)
        print(f"Found app: {app_path}")

        out_name = identifier
        tmp_ipa = f"/tmp/{out_name}.ipa"

        # Repackage as IPA: Payload/<App>.app zipped at root
        print("Building IPA...")
        build = (
            f'cd /tmp && rm -rf Payload "{tmp_ipa}" && mkdir Payload && '
            f'cp -R "{app_path}" Payload/ && '
            f'zip -qr "{tmp_ipa}" Payload && rm -rf Payload && '
            f'echo "IPA built"'
        )
        result = ssh(build)
        if "IPA built" not in result.stdout:
            print(f"Error building IPA: {result.stderr}")
            sys.exit(1)

        output_file = f"{out_name}.ipa"
        print("Downloading IPA...")
        subprocess.run(
            ["scp", "-P", PORT, f"{DEVICE_USER}@{DEVICE_HOST}:{tmp_ipa}", output_file],
            check=True
        )

        ssh(f'rm -f "{tmp_ipa}"')

        print(f"✓ IPA saved: {output_file}")
        print("Note: App Store apps stay FairPlay-encrypted. Use frida-ios-dump or bagbak for decrypted IPA.")

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(e.stderr)
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Pull IPA from jailbroken iOS device.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("bundle_id", nargs="?", help="App bundle id, e.g. com.example.app")
    group.add_argument("--uuid", help="Bundle container UUID")
    args = parser.parse_args()

    if args.uuid:
        extract_ipa(args.uuid, by_uuid=True)
    else:
        extract_ipa(args.bundle_id, by_uuid=False)
