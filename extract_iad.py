#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

DEVICE_USER = os.environ.get("IOS_USER", "root")
DEVICE_HOST = os.environ.get("IOS_HOST", "iphone.local")

def ssh(cmd):
    return subprocess.run(
        ["ssh", f"{DEVICE_USER}@{DEVICE_HOST}", cmd],
        capture_output=True, text=True, check=True
    )

def find_data_path_by_bundle_id(bundle_id):
    # Data container UUID != bundle UUID. Match via metadata plist which holds bundle id.
    meta = ".com.apple.mobile_container_manager.metadata.plist"
    cmd = (
        f'for d in /var/mobile/Containers/Data/Application/*/; do '
        f'[ -f "$d{meta}" ] && grep -a -q "{bundle_id}" "$d{meta}" && '
        f'echo "${{d%/}}" && break; '
        f'done'
    )
    result = ssh(cmd)
    path = result.stdout.strip()
    if not path:
        print(f"data container not found for: {bundle_id}")
        sys.exit(1)
    return path

def find_data_path_by_uuid(uuid):
    path = f"/var/mobile/Containers/Data/Application/{uuid}"
    result = ssh(f'[ -d "{path}" ] && echo "{path}"')
    if not result.stdout.strip():
        print(f"data container not found at: {path}")
        print("Check UUID, or this may be a bundle UUID, not a data UUID")
        sys.exit(1)
    return path

def extract_data(identifier, by_uuid):
    try:
        if by_uuid:
            data_path = find_data_path_by_uuid(identifier)
        else:
            data_path = find_data_path_by_bundle_id(identifier)
        print(f"Found data container: {data_path}")

        parent, name = data_path.rsplit('/', 1)
        out_name = identifier
        tmp_tar = f"/tmp/{out_name}_data.tar.gz"

        print("Creating archive...")
        build = (
            f'cd "{parent}" && '
            f'tar -czf "{tmp_tar}" "{name}" && '
            f'echo "Archive created"'
        )
        result = ssh(build)
        if "Archive created" not in result.stdout:
            print(f"Error creating archive: {result.stderr}")
            sys.exit(1)

        output_file = f"{out_name}_data.tar.gz"
        print("Downloading archive...")
        subprocess.run(
            ["scp", f"{DEVICE_USER}@{DEVICE_HOST}:{tmp_tar}", output_file],
            check=True
        )

        print("Extracting files...")
        subprocess.run(["tar", "-xzf", output_file], check=True)

        ssh(f'rm -f "{tmp_tar}"')

        print(f"✓ Data extracted to: ./{name}/")
        print(f"✓ Archive saved as: {output_file}")

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(e.stderr)
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Pull app data container from jailbroken iOS device.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("bundle_id", nargs="?", help="App bundle id, e.g. com.example.app")
    group.add_argument("--uuid", help="Data container UUID")
    args = parser.parse_args()

    if args.uuid:
        extract_data(args.uuid, by_uuid=True)
    else:
        extract_data(args.bundle_id, by_uuid=False)
