# Setting Up USB Copy and Media Player Services on Raspberry Pi

This guide provides instructions to set up two services on a Raspberry Pi:
1. A **USB Copy Service** that automatically copies files from USB flash drives to `/home/apex/`.
2. A **Media Player Service** that plays videos based on GPIO button inputs, starting with the desktop environment.

## Prerequisites
- Raspberry Pi running Raspberry Pi OS (e.g., Bullseye or Bookworm).
- USB flash drives for testing the USB copy service.
- GPIO buttons connected to pins 13, 19, 26, 21, 20, and 16 for the media player.
- Video files (`1.mp4`, `2.mp4`, `3.mp4`, `4.mp4`) in `/home/pi/Videos/`.
- Internet connection for installing packages.

## USB Copy Service Setup

### Step 1: Install Dependencies
Update package lists and install required packages:
```bash
sudo apt-get update
sudo apt-get install python3 python3-pip libudev-dev
sudo pip3 install pyudev
```

### Step 2: Save the USB Copy Script
Save the following script to `/usr/local/bin/usb_copy_service.py`:

**File**: `usb_copy_service.py`
```python
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
```

```bash
sudo nano /usr/local/bin/usb_copy_service.py
# Paste the script, save, and exit
sudo chmod +x /usr/local/bin/usb_copy_service.py
```

### Step 3: Create the Systemd Service File
Create the systemd service file at `/etc/systemd/system/usb-copy.service`:

**File**: `usb-copy.service`
```text
[Unit]
Description=USB Flash Drive Auto Copy Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/usb_copy_service.py
Restart=always
User=apex
WorkingDirectory=/home/apex

[Install]
WantedBy=multi-user.target
```

```bash
sudo nano /etc/systemd/system/usb-copy.service
# Paste the service file, save, and exit
sudo chmod 644 /etc/systemd/system/usb-copy.service
```

### Step 4: Enable and Start the Service
```bash
sudo systemctl enable usb-copy.service
sudo systemctl start usb-copy.service
```

### Step 5: Verify the Service
Check the service status:
```bash
sudo systemctl status usb-copy.service
```
View logs:
```bash
journalctl -u usb-copy.service
```

### Notes
- The script monitors USB devices using `pyudev`.
- Files are copied to `/home/apex/`, skipping existing files.
- Ensure the `apex` user has write permissions to `/home/apex/`.
- The service runs continuously, restarting on failure.

## Media Player Service Setup

### Step 1: Install Dependencies
Install VLC and Python dependencies. If `apt` fails to find VLC, use Snap.

#### Option 1: Install VLC via apt
```bash
sudo apt-get update
sudo apt-get install vlc python3-rpi.gpio python3-pip
sudo pip3 install python-vlc
```

#### Option 2: Install VLC via Snap (if apt fails)
```bash
sudo apt-get install snapd
sudo snap install vlc
sudo pip3 install python-vlc
```

#### Verify Installations
```bash
vlc --version  # or `snap run vlc --version` for Snap
python3 -c "import vlc; print(vlc.__version__)"
```

#### Fix Repository Issues (if needed)
If VLC is not found via `apt`, check `/etc/apt/sources.list`:
```bash
sudo nano /etc/apt/sources.list
```
Ensure it includes:
```
deb http://raspbian.raspberrypi.org/raspbian/ bookworm main contrib non-free rpi
```
Update again:
```bash
sudo apt-get update
```

### Step 2: Save the Media Player Script
Save the following script to `/usr/local/bin/media_player_service.py`:

**File**: `media_player_service.py`
```python
import time
import RPi.GPIO as GPIO
import vlc
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pin definitions
BUTTON_PINS = {
    13: "/home/pi/Videos/1.mp4",  # Button 1
    19: "/home/pi/Videos/2.mp4",  # Button 2
    26: "/home/pi/Videos/3.mp4",  # Button 3
    21: "/home/pi/Videos/4.mp4",  # Button 4
    20: "pause",                  # Button 5
    16: "stop"                    # Button 6
}

def setup_gpio():
    """Initialize GPIO pins."""
    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        for pin in BUTTON_PINS:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        logger.info("GPIO initialized successfully")
    except Exception as e:
        logger.error(f"GPIO setup error: {e}")
        raise

def setup_media_player():
    """Initialize VLC media player."""
    try:
        player = vlc.MediaPlayer()
        player.toggle_fullscreen()
        logger.info("Media player initialized successfully")
        return player
    except Exception as e:
        logger.error(f"Media player setup error: {e}")
        raise

def play_video(player, fname):
    """Play a video file."""
    try:
        player.stop()
        media = vlc.Media(fname)
        player.set_media(media)
        player.play()
        logger.info(f"Playing video: {fname}")
    except Exception as e:
        logger.error(f"Playback error for {fname}: {e}")

def main():
    try:
        # Initialize components
        setup_gpio()
        media_player = setup_media_player()
        
        logger.info("Starting main loop")
        while True:
            for pin, action in BUTTON_PINS.items():
                if GPIO.input(pin) == GPIO.LOW:
                    if action == "pause":
                        media_player.pause()
                        logger.info("Video paused")
                    elif action == "stop":
                        media_player.stop()
                        logger.info("Video stopped")
                    else:
                        play_video(media_player, action)
                    time.sleep(0.2)  # Debounce delay
            time.sleep(0.01)  # Reduce CPU usage
            
    except KeyboardInterrupt:
        logger.info("Shutting down")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        media_player.stop()
        GPIO.cleanup()
        logger.info("Cleanup complete")

if __name__ == "__main__":
    main()
```

```bash
sudo nano /usr/local/bin/media_player_service.py
# Paste the script, save, and exit
sudo chmod +x /usr/local/bin/media_player_service.py
```

### Step 3: Create the Systemd Service File
Create the systemd service file at `/etc/systemd/system/media-player.service`:

**File**: `media-player.service`
```text
[Unit]
Description=Media Player GPIO Service
After=graphical.target
Requires=graphical.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/media_player_service.py
Restart=always
User=pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
WorkingDirectory=/home/pi
TimeoutStartSec=30

[Install]
WantedBy=graphical.target
```

```bash
sudo nano /etc/systemd/system/media-player.service
# Paste the service file, save, and exit
sudo chmod 644 /etc/systemd/system/media-player.service
```

### Step 4: Enable and Start the Service
```bash
sudo systemctl enable media-player.service
sudo systemctl start media-player.service
```

### Step 5: Verify the Service
Check the service status:
```bash
sudo systemctl status media-player.service
```
View logs:
```bash
journalctl -u media-player.service
```

### Notes
- The service starts after the desktop environment (`graphical.target`).
- Uses GPIO pins 13, 19, 26, 21 (play videos), 20 (pause), and 16 (stop).
- Videos must exist at `/home/pi/Videos/`.
- Ensure the `pi` user has permissions for the videos and X display.
- If Snap-installed VLC is used, test the script manually first:
  ```bash
  python3 /usr/local/bin/media_player_service.py
  ```

## Troubleshooting

### USB Copy Service
- **Permission Issues**: Ensure `apex` user has write access to `/home/apex/`.
- **USB Not Detected**: Check `pyudev` installation and USB mount points (`lsblk`).
- **Logs**: Use `journalctl -u usb-copy.service` for errors.

### Media Player Service
- **VLC Not Found**:
  - Reinstall VLC via Snap if `apt` fails.
  - Verify `python-vlc` with `python3 -c "import vlc"`.
- **GPIO Errors**: Check wiring and pin numbers.
- **Display Issues**: Ensure `DISPLAY=:0` and `XAUTHORITY` are set correctly.
- **Logs**: Use `journalctl -u media-player.service` for errors.

### General
- **OS Version**: Check with `cat /etc/os-release`. Bookworm may require Snap for VLC.
- **Backup**: Back up your SD card before making changes.
- **Dependencies**: Fix broken packages with `sudo apt-get install -f`.

## Testing
- **USB Copy**: Insert a USB drive and check if files copy to `/home/apex/`.
- **Media Player**: Press GPIO buttons to verify video playback, pause, and stop.

This setup ensures both services run reliably, with the USB copy service starting on boot and the media player service starting with the desktop environment.