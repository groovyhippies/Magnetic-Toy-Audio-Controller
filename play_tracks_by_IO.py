import pygame
import RPi.GPIO as GPIO
import time
import mcp3008
import subprocess

# Define constants for easy ADc's modification
V_REF = 5.0         # ADC reference voltage
V_SENSOR_MAX = 4.7  # Maximum output voltage of the sensor
ADC_MAX = 1024      # Full-scale ADC value
# Calculate the ADC value corresponding to the sensor's max output
ADC_SENSOR_MAX = (V_SENSOR_MAX / V_REF) * ADC_MAX

# Macro-like constant for playback duration
PLAYBACK_DURATION = 120  # Time in seconds

# SHOULD_LOOP defines the loop behavior for the sound:
# -1 = loop indefinitely, 0 = play once (no loop)
SHOULD_LOOP = -1

# GPIO pin setup
GPIO.setmode(GPIO.BCM)
#input_pins = [0, 1, 2, 3, 4, 5]  # GPIO0 to GPIO5
input_pins = [0, 5, 6, 13, 19, 26]

# Set up GPIO pins as input with pull-up resistors
for pin in input_pins:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Initialize Pygame Mixer
# Keep retrying pygame.mixer.init() until it succeeds
while True:
    try:
        pygame.mixer.init(frequency=48000, size=-16, channels=2, buffer=1024)
        print("Audio initialized successfully!", flush=True)
        break  # Exit loop if successful
    except pygame.error as e:
        print(f"Pygame audio init failed: {e}. Retrying in 2 seconds...", flush=True)
        time.sleep(2)  # Wait before retrying

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

adc = mcp3008.MCP3008()  # Initialize MCP3008 ADC

timer_start = None  # Timer for playback
playing = False  # Flag to indicate if tracks are currently playing


def get_adc_value():
    """
    Read the ADC value and return it.
    """
    try:
        value = adc.read([mcp3008.CH0])[0]  # Read raw data from CH0
        return value
    except Exception as e:
        print(f"Error reading ADC: {e}")
        return 512  # Default midpoint value on error


def adjust_bg_volumes():
    """
    Adjust the volumes of the two background tracks based on ADC value.
    """
    adc_value = get_adc_value()
    #volume_a = adc_value / 1024  # Scale to range 0.0 to 1.0
    volume_a = adc_value / ADC_SENSOR_MAX  # Normalize 0.0 to 1.0
    volume_a = min(volume_a, 1.0)  # Ensure it does not exceed 1.0
    volume_b = 1.0 - volume_a  # Complementary volume

    if bg_channels[0] is not None:
        bg_channels[0].set_volume(volume_a)
    if bg_channels[1] is not None:
        bg_channels[1].set_volume(volume_b)


def play_all_tracks_muted():
    """
    Start all tracks in muted mode.
    """
    global channels, playing, bg_channels
    print("\r\n**********************************************************\r\n")
    print("The 1st toy has been inserted! Audio system is starting...")
    print("\r\n**********************************************************\r\n")
    print("Initializing audio playback...")

    initial_adc_value = get_adc_value()
    volume_a = initial_adc_value / 1024  # Scale to range 0.0 to 1.0
    volume_b = 1.0 - volume_a  # Complementary volume

    print(f"Initial ADC Value: {initial_adc_value}")
    print(f"Initial Volumes -> Track0a: {volume_a}, Track0b: {volume_b}")

    for i, track in enumerate(bg_tracks):
        if bg_channels[i] is None:  # Only start if not already playing
            channel = track.play(loops=SHOULD_LOOP)  # Play in loop
            if channel is not None:
                bg_channels[i] = channel

    # Adjust volumes before playback
    adjust_bg_volumes()
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
        timer_start = time.time()  # Reset the timer when a new toy is inserted
        print("Timer reset!")
        unmute_track(pin_index)
    elif pin_state == GPIO.HIGH:
        # Rising edge: Mute the corresponding track
        mute_track(pin_index)

# Notify the user that the program has finished its init process

# Command to play the audio file
command = ["aplay", "-D", "default", "/usr/share/sounds/alsa/Front_Center.wav"]

# Execute the command
result = subprocess.run(command, capture_output=True, text=True)

# Print any output or error messages
print("Output:", result.stdout)
print("Error:", result.stderr)


# Add event detection for GPIO pins
for pin in input_pins:
    GPIO.add_event_detect(pin, GPIO.BOTH, callback=gpio_callback, bouncetime=300)

# Main loop to manage the playback timer and adjust volumes
try:
    print("Waiting for GPIO events...")
    while True:
        if timer_start is not None:
            elapsed_time = time.time() - timer_start
            if elapsed_time >= PLAYBACK_DURATION:
                stop_all_tracks()  # Stop all tracks after the configured duration

        # Continuously adjust background track volumes
        if playing:
            adjust_bg_volumes()

        time.sleep(0.1)  # Small delay to avoid high CPU usage
except KeyboardInterrupt:
    print("\nProgram interrupted by user.")
finally:
    GPIO.cleanup()
    pygame.mixer.quit()
    adc.close()
    print("GPIO cleaned up and mixer closed.")
