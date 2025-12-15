# Pico W Laundry Monitor

A dual-core, vibration-based laundry monitoring system powered by a **Raspberry Pi Pico W**. This project monitors the vibration of a washer and dryer using piezoelectric sensors and sends notifications via **Home Assistant** (Google Home TTS) and **Ntfy.sh** (Phone Push) when a cycle finishes.

## 🚀 Features
* **False-Positive Rejection:** Requires sustained vibration (configurable) to start a cycle, preventing alerts when just loading/unloading clothes.
* **Dual-Core Architecture:** Runs the sensor loop on Core 0 and a live Web Interface on Core 1, ensuring the web server never interrupts sensor readings.
* **Dual Alerts:** Triggers a Home Assistant Webhook (for voice announcements) and sends a push notification to your phone via Ntfy.sh.
* **Auto-Calibration Mode:** Includes a debug mode to visualize raw vibration data in the console for easy sensitivity tuning.
* **WiFi Power Management:** Disables standard power-saving features to prevent connection timeouts on Mesh networks (e.g., Eero).

## 🛠 Hardware Required
* **Raspberry Pi Pico W**
* **Piezoelectric Vibration Sensors** (Analog) x2
    * *Tip: Cheap analog piezo ceramic discs work perfectly.*
* **MicroUSB Cable** (Power/Data)
* **Jumper Wires**

## 🔌 Wiring & Circuit Protection

### The "Why" behind the Resistors
Piezoelectric sensors generate voltage when vibrated. On a heavily vibrating washing machine, a large piezo disc can generate voltage spikes well above **3.3V**.

Since the Raspberry Pi Pico's ADC pins are rated for **3.3V max**, direct connection to a raw piezo sensor during a heavy spin cycle could damage the pin or the board.

### The Full Circuit (Series + Parallel)
To get clean readings and protect your Pico, use this two-resistor setup:

**Wiring for One Sensor:**
1.  **Parallel Resistor (1MΩ):** Connect across the Piezo's Red (+) and Black (-) wires.
    * *Role:* **Discharge.** Piezo sensors act like capacitors. This resistor "bleeds" the charge off to Ground so the sensor reading returns to 0 when vibration stops.
2.  **Series Resistor (10kΩ):** Connect between the Piezo's Red (+) wire and the Pico ADC Pin.
    * *Role:* **Protection.** This limits the current flowing into the Pico. If the piezo generates a high-voltage spike, this resistor prevents that spike from delivering enough current to fry the input pin.

### Summary
* **1MΩ (Parallel):** Keeps the signal clean (prevents drift).
* **10kΩ (Series):** Keeps the Pico safe (limits current).

### Pins
| Device | Pico Pin | Physical Pin |
| :--- | :--- | :--- |
| **Washer Sensor** | ADC 1 (GP27) | Pin 32 |
| **Dryer Sensor** | ADC 0 (GP26) | Pin 31 |
| **LED** (Optional) | Onboard LED | - |

## ⚙️ Configuration
Open `main.py` and edit the **Configuration** section at the top:


## 📊 Calibration

To find the correct threshold for your specific machine:

1.  Set `CALIBRATION_MODE = True` in `main.py`.
2.  Run the script in Thonny.
3.  Watch the console output while the machine is running.
4.  Set your `THRESHOLD` slightly below the average vibration values observed.
5.  Set `CALIBRATION_MODE = False` for production use.

## 🏠 Home Assistant Integration

Create an Automation in Home Assistant to handle the voice announcement.

**Trigger:** Webhook
**Webhook ID:** `washer_done_alert`

**YAML Example:**

```yaml
alias: "Notify: Washer Done"
trigger:
  - platform: webhook
    webhook_id: washer_done_alert
    local_only: true
action:
  - action: media_player.volume_set
    target:
      entity_id: media_player.your_speaker
    data:
      volume_level: 1.0
  - action: tts.google_translate_say
    target:
      entity_id: media_player.your_speaker
    data:
      message: "Attention, the washing machine has finished its cycle."
  - delay: "00:00:10" # Wait for speech to finish
  - action: media_player.volume_set
    target:
      entity_id: media_player.your_speaker
    data:
      volume_level: 0.4
```

## 📱 Web Interface

Once running, navigate to `http://<PICO_IP_ADDRESS>` to see the live status, current vibration levels, and cycle runtime.

## 📄 License

This project is open source. Feel free to modify and use it for your own home automation setup.

```
```
