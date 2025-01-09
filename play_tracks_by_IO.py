import pygame
import RPi.GPIO as GPIO
import time

# Macro-like constant for playback duration
PLAYBACK_DURATION = 120  # Time in seconds

# SHOULD_LOOP defines the loop behavior for the sound:
# -1 = loop indefinitely, 0 = play once (no loop)
SHOULD_LOOP = -1

# GPIO pin setup
GPIO.setmode(GPIO.BCM)
input_pins = [0, 1, 2, 3, 4, 5]  # GPIO0 to GPIO5

# Set up GPIO pins as input with pull-up resistors
for pin in input_pins:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Initialize Pygame Mixer
pygame.mixer.init(frequency=22050, size=-8, channels=2, buffer=4096)  # Default settings for Pygame mixer

# Load tracks
tracks = [
    pygame.mixer.Sound("wav_files/track1.wav"),
    pygame.mixer.Sound("wav_files/track2.wav"),
    pygame.mixer.Sound("wav_files/track3.wav"),
    pygame.mixer.Sound("wav_files/track4.wav"),
    pygame.mixer.Sound("wav_files/track5.wav"),
    pygame.mixer.Sound("wav_files/track6.wav"),
]

bg_tracks = [
    pygame.mixer.Sound("wav_files/track0a.wav"),
    pygame.mixer.Sound("wav_files/track0b.wav"),
]

# Initialize states
channels = [None] * len(tracks)  # Store channel objects
bg_channels = [None] * len(bg_tracks)  # Store channel objects

timer_start = None  # Timer for playback
playing = False  # Flag to indicate if tracks are currently playing

def play_all_tracks_muted():
    """
    Start all tracks in muted mode.
    """
    global channels, playing, bg_channels
    print("\r\n**********************************************************\r\n")
    print("The 1st toy has been inserted! Audio system is starting...")
    print("\r\n**********************************************************\r\n")
    print("Initializing audio playback...")

    for i, track in enumerate(bg_tracks):
        if bg_channels[i] is None:  # Only start if not already playing
            channel = track.play(loops=SHOULD_LOOP)  # Play in loop
            if channel is not None:
                channel.set_volume(1)  #Play with volumn
                bg_channels[i] = channel
    print("Background tracks are now playing")

    for i, track in enumerate(tracks):
        if channels[i] is None:  # Only start if not already playing
            channel = track.play(loops=SHOULD_LOOP)  # Play in loop
            if channel is not None:
                channel.set_volume(0)  # Start muted
                channels[i] = channel
    playing = True
    print("All tracks are now playing (muted).")


def unmute_track(index):
    """
    Unmute the track corresponding to the GPIO pin.
    """
    if channels[index] is None:
        # If the track is not playing, restart it
        print(f"Restarting track {index + 1}.")
        channels[index] = tracks[index].play(loops=SHOULD_LOOP)
    if channels[index] is not None:
        channels[index].set_volume(1)  # Full volume
        print(f"Track {index + 1} unmuted.")


def mute_track(index):
    """
    Mute the track corresponding to the GPIO pin.
    """
    if channels[index] is not None:
        channels[index].set_volume(0)  # Mute
        print(f"Track {index + 1} muted.")


def stop_all_tracks():
    """
    Stop all tracks and reset states.
    """
    global channels, timer_start, playing
    print("\r\n**********************************************************\r\n")
    print("Playback time is over. Thank you for playing!")
    print("Stopping all tracks.")
    print("\r\n**********************************************************\r\n")

    for i, channel in enumerate(channels):
        if channel is not None:
            channel.stop()
            channels[i] = None

    for i, channel in enumerate(bg_channels):
        if channel is not None:
            channel.stop()
            bg_channels[i] = None

    timer_start = None
    playing = False


def gpio_callback(channel):
    """
    Callback function triggered when GPIO events are detected.
    Handles both rising and falling edges.
    """
    global timer_start, playing
    pin_index = input_pins.index(channel)  # Find index of triggered GPIO pin
    pin_state = GPIO.input(channel)

    print(f"GPIO {channel} detected. State: {'HIGH' if pin_state else 'LOW'}")

    if not playing and pin_state == GPIO.LOW:
        play_all_tracks_muted()  # Start tracks if not already started

    if pin_state == GPIO.LOW:
        # Falling edge: Unmute the corresponding track and reset the timer
        timer_start=time.time() #reset the timer when a new toy is inserted
        print("timer reset!")
        unmute_track(pin_index)
    elif pin_state == GPIO.HIGH:
        # Rising edge: Mute the corresponding track
        mute_track(pin_index)


# Add event detection for GPIO pins
for pin in input_pins:
    GPIO.add_event_detect(pin, GPIO.BOTH, callback=gpio_callback, bouncetime=300)


# Main loop to manage the playback timer
try:
    print("Waiting for GPIO events...")
    while True:
        if timer_start is not None:
            elapsed_time = time.time() - timer_start
            if elapsed_time >= PLAYBACK_DURATION:
                stop_all_tracks()  # Stop all tracks after the configured duration
        time.sleep(0.1)  # Small delay to avoid high CPU usage
except KeyboardInterrupt:
    print("\nProgram interrupted by user.")
finally:
    GPIO.cleanup()
    pygame.mixer.quit()
    print("GPIO cleaned up and mixer closed.")
