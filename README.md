# Med Drone Totem

A Raspberry Pi 4B-powered interactive robot face display. An animated face cycles through expressions on a small square screen, responds to sound with an audio visualizer, and displays curated messages — all switchable via capacitive touch buttons.

---

## Modes

| Mode | Description |
|---|---|
| **Face** | Animated robot face with blinking, expression cycling (normal, happy, sad, wonder, smirk, bobbing), and high-five reactions |
| **Audio Visualizer** | Radial FFT frequency bars with a waveform breathing ring, driven by a USB microphone |
| **Messages** | Pre-written phrases that morph in and out with scale/fade transitions |

---

## Hardware

| Component | Model |
|---|---|
| Computer | Raspberry Pi 4B |
| Display | Pimoroni HyperPixel 4 Square (720×720px, capacitive touch) |
| Touch buttons | Adafruit MPR121 capacitive touch breakout |
| Microphone | USB microphone |
| Power | Battery pack (USB-C) |

### Wiring

**HyperPixel 4 Square** attaches directly to the Pi's 40-pin GPIO header. It uses nearly all GPIO pins for the DPI display interface. Two I2C pins are broken out on the back of the HyperPixel board and must be used for the MPR121.

**MPR121 → HyperPixel alternate I2C (back of board):**

| MPR121 Pin | HyperPixel Back Pin |
|---|---|
| VIN | 3.3V |
| GND | GND |
| SCL | SCL (alternate) |
| SDA | SDA (alternate) |

Connect two conductive pads (copper tape, wire loops, etc.) to MPR121 electrode pins **0** (left button) and **1** (right button).

---

## Gesture Reference

| Input | Action |
|---|---|
| Quick tap left or right pad (< 200ms) | High-five — face flashes happy → wonder → happy |
| Hold left pad (≥ 200ms, release) | Previous mode |
| Hold right pad (≥ 200ms, release) | Next mode |

**Keyboard fallback (dev/desktop):**

| Key | Action |
|---|---|
| `←` | Previous mode |
| `→` | Next mode |
| `Space` | High-five |
| `1` / `2` / `3` | Set face to normal / happy / sad |
| `b` | Blink |

---

## Raspberry Pi Deployment

### 1. Install Raspberry Pi OS

Flash **Raspberry Pi OS Lite (64-bit)** or **Raspberry Pi OS Desktop (64-bit)** to a microSD card using [Raspberry Pi Imager](https://www.raspberrypi.com/software/). Enable SSH and set your username/password in the imager's advanced settings before flashing.

### 2. Install the HyperPixel 4 Square driver

Boot the Pi, SSH in, then run Pimoroni's installer:

```bash
git clone https://github.com/pimoroni/hyperpixel4
cd hyperpixel4
sudo ./install.sh
sudo reboot
```

After rebooting the display should light up. If you have the touch variant, touch events will be available automatically.

### 3. Install system dependencies

```bash
sudo apt update && sudo apt install -y \
    python3-pip \
    python3-pygame \
    portaudio19-dev \
    libsdl2-dev \
    i2c-tools
```

Enable I2C on the alternate pins (used by HyperPixel backport — check Pimoroni docs for the exact `config.txt` overlay for your HyperPixel revision):

```bash
sudo raspi-config
# Interface Options → I2C → Enable
```

Verify the MPR121 is detected on the I2C bus:

```bash
sudo i2cdetect -y 1
# Should show address 0x5a
```

### 4. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

### 5. Clone the repo and install Python dependencies

```bash
git clone https://github.com/KalaniStanton/MedDroneTotem.git
cd MedDroneTotem
uv sync
```

### 6. Configure for Pi

Open `core/config.py` and set:

```python
FULLSCREEN = True
```

### 7. Run manually to verify

```bash
uv run python main.py
```

The face mode should appear fullscreen on the HyperPixel. Test mode switching with the capacitive pads and verify the microphone works in audio visualizer mode.

### 8. Auto-start on boot (systemd)

Create the service file:

```bash
sudo nano /etc/systemd/system/meddronetotem.service
```

Paste:

```ini
[Unit]
Description=Med Drone Totem
After=graphical.target

[Service]
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/MedDroneTotem
Environment=DISPLAY=:0
ExecStart=/home/YOUR_USERNAME/.local/bin/uv run python main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
```

Replace `YOUR_USERNAME` with your Pi username, then enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable meddronetotem
sudo systemctl start meddronetotem
```

Check status:

```bash
sudo systemctl status meddronetotem
journalctl -u meddronetotem -f   # live logs
```

---

## Development (Mac / Linux desktop)

```bash
git clone https://github.com/KalaniStanton/MedDroneTotem.git
cd MedDroneTotem
uv sync
uv run python main.py
```

`FULLSCREEN = False` in `core/config.py` by default — the window opens at 720×720. Use arrow keys and Space instead of the capacitive pads.

---

## Project Structure

```
core/
  config.py          — display size, colors, message list, FULLSCREEN flag
  engine.py          — ModeManager: main loop, mode switching, event routing
  modes/
    base.py          — Mode abstract base class
    face_mode.py     — animated face (expressions, blinking, high-five)
    audio_mode.py    — FFT visualizer (radial bars + waveform ring)
    message_mode.py  — animated message display
  input/
    touch.py         — MPR121 I2C gesture engine + keyboard fallback
    audio_capture.py — threaded sounddevice mic input with FFT
main.py              — entry point
```

---

## Customizing Messages

Edit the `MESSAGES` list in `core/config.py`:

```python
MESSAGES = [
    "Hello, friend.",
    "You're doing great.",
    # add your own...
]
```
