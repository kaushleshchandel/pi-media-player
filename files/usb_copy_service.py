import os
import shutil
import time
import pyudev
from pathlib import Path

# Destination directory
DEST_DIR = Path("/home/apex")
# Ensure destination directory exists
DEST_DIR.mkdir(parents=True, exist_ok=True)

def get_mount_point(device):
    """Get the mount point of a device."""
    return device.get('MEDIA_MNT', None)

def copy_files(src, dst):
    """Copy all files from source to destination."""
    try:
        for item in os.listdir(src):
            src_path = os.path.join(src, item)
            dst_path = os.path.join(dst, item)
            
            # Skip if destination file exists
            if os.path.exists(dst_path):
                print(f"Skipping {dst_path} - already exists")
                continue
                
            if os.path.isfile(src_path):
                print(f"Copying file: {src_path} to {dst_path}")
                shutil.copy2(src_path, dst_path)
            elif os.path.isdir(src_path):
                print(f"Copying directory: {src_path} to {dst_path}")
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
    except Exception as e:
        print(f"Error copying files: {e}")

def main():
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='block', device_type='partition')
    
    print("Monitoring for USB devices...")
    
    # Check existing devices at startup
    for device in context.list_devices(subsystem='block', device_type='partition'):
        if device.get('ID_BUS') == 'usb' and device.get('MEDIA_MNT'):
            mount_point = get_mount_point(device)
            if mount_point:
                print(f"Found existing USB at {mount_point}")
                copy_files(mount_point, DEST_DIR)
    
    # Monitor for new devices
    for device in iter(monitor.poll, None):
        if device.get('ID_BUS') == 'usb' and device.action == 'add':
            time.sleep(1)  # Wait for the device to be mounted
            mount_point = get_mount_point(device)
            if mount_point:
                print(f"New USB detected at {mount_point}")
                copy_files(mount_point, DEST_DIR)

if __name__ == "__main__":
    main()