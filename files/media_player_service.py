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