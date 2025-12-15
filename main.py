import network
import time
import urequests
import _thread
import web_server
from machine import ADC, Pin
import rp2

# ================= CONFIGURATION =================
# Set this to TRUE to see live data in the shell
# Set to FALSE for normal operation (Notifications enabled)

# Replace the ####### with your info.

CALIBRATION_MODE = False 

SSID = "######"
PASSWORD = "######"

NTFY_URL = "https://ntfy.sh/######"

# HOME ASSISTANT CONFIGURATION
HA_IP = "192.168.1.###"
HA_PORT = "###"

WASHER_URL = f"http://{HA_IP}:{HA_PORT}/api/webhook/######"
DRYER_URL  = f"http://{HA_IP}:{HA_PORT}/api/webhook/######"

# TOGGLES: Enable/Disable sensors here
WASHER_CONNECTED = True
DRYER_CONNECTED = False

# SENSOR SETTINGS
THRESHOLD = 1500        # Adjust this if your machine is quieter/louder
START_CONFIRM_SEC = 60  # Must vibrate this long to count as "Started" 60
COOLDOWN_SEC = 300      # 5 Minutes of silence = "Finished" 300
FALSE_ALARM_TIME = 10   # Short bumps are ignored

# ================= SETUP =================
led = Pin("LED", Pin.OUT)
machines = {}

if WASHER_CONNECTED:
    print("Initializing Washer Sensor...")
    machines['Washer'] = {
        'state': 'IDLE', 
        'adc': ADC(27), # 32
        'webhook': WASHER_URL, 
        'last_vibe_time': 0, 'start_verify_time': 0, 'current_vibration': 0
    }

if DRYER_CONNECTED:
    print("Initializing Dryer Sensor...")
    machines['Dryer'] = {
        'state': 'IDLE', 
        'adc': ADC(26), # 31
        'webhook': DRYER_URL, 
        'last_vibe_time': 0, 'start_verify_time': 0, 'current_vibration': 0
    }

# ================= FUNCTIONS =================
def blink(times, speed=0.1):
    for _ in range(times):
        led.on(); time.sleep(speed)
        led.off(); time.sleep(speed)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    
    # 1. FORCE RESET: Turn WiFi OFF then ON to kill any stuck states
    wlan.active(False)
    time.sleep(0.5)
    wlan.active(True)
    
    # 2. Set Country & Power Mode (Critical for Eero/Mesh)
    rp2.country('US')
    wlan.config(pm=0xa11140)
    
    print(f"Connecting to {SSID}...")
    wlan.connect(SSID, PASSWORD)
    
    # 3. The "Status" Loop
    max_wait = 20
    while max_wait > 0:
        status = wlan.status()
        
        # Status 3 means CONNECTED
        if status == 3:
            break
            
        if status == -3:
            print("ERR: Bad Auth / Password Rejected")
            return None
            
        if status < 0:
            print(f"ERR: WiFi Status {status}")
            return None
            
        # print(f"Status: {status} (Waiting...)") # Uncomment for deep debug
        max_wait -= 1
        time.sleep(1)
            
    # Final Check
    if wlan.status() == 3:
        ip = wlan.ifconfig()[0]
        print(f"Connected! IP: {ip}")
        blink(3)
        return ip
    else:
        print("\n!!! WIFI CONNECTION FAILED !!!")
        blink(10, 0.05)
        return None

def send_alert(ha_url, machine_name):
    # In CALIBRATION_MODE, skip everything
    if CALIBRATION_MODE:
        print(f"[DEBUG] Would alert HA and Ntfy for {machine_name}")
        return

    # 1. Trigger Home Assistant (The Voice Announcement)
    try:
        print(f"Triggering Home Assistant...")
        urequests.post(ha_url)
    except Exception as e:
        print(f"HA Failed: {e}")

    # 2. Trigger Ntfy.sh (The Phone Notification)
    try:
        print(f"Sending Ntfy Push...")
        msg = f"{machine_name} has finished!"
        urequests.post(NTFY_URL, data=msg.encode('utf-8'))
    except Exception as e:
        print(f"Ntfy Failed: {e}")

def get_average_reading(adc_sensor, samples=30):
    total = 0
    for _ in range(samples):
        total += adc_sensor.read_u16()
        time.sleep(0.001)
    return total // samples

# ================= MAIN LOOP =================

# 1. Connect to WiFi
ip_address = connect_wifi()

# 2. Start Web Server (Only if WiFi succeeded)
if ip_address:
    try:
        print("Starting Web Server Thread...")
        _thread.start_new_thread(web_server.run_server, (machines, ip_address))
    except Exception as e:
        print(f"Failed to start web server: {e}")

# 3. Mode Announcement
if CALIBRATION_MODE:
    print("\n!!! CALIBRATION MODE ACTIVE !!!")
    print(f"Threshold is set to: {THRESHOLD}")
    print("Watching sensors... (Webhooks DISABLED)\n")
else:
    print("System Armed (Production Mode)...")

while True:
    current_time = time.time()
    
    for name, data in machines.items():
        vibration = get_average_reading(data['adc'])
        data['current_vibration'] = vibration 
        
        # --- DEBUG PRINTING (Only if Calibration Mode is ON) ---
        if CALIBRATION_MODE:
            bar_len = vibration // 200
            bar = "|" * bar_len
            trigger_mark = ">> ACTIVE" if vibration > THRESHOLD else ""
            print(f"[{name}] Val: {vibration:5} / Thresh: {THRESHOLD}  {bar} {trigger_mark}")

        # --- LOGIC ---
        if vibration > THRESHOLD:
            data['last_vibe_time'] = current_time 
            
            if data['state'] == 'IDLE':
                if not CALIBRATION_MODE: print(f"[{name}] Movement detected. Verifying...")
                data['state'] = 'VERIFYING'
                data['start_verify_time'] = current_time
            
            elif data['state'] == 'VERIFYING':
                duration = current_time - data['start_verify_time']
                if duration > START_CONFIRM_SEC:
                    if not CALIBRATION_MODE: print(f"--- {name} CONFIRMED STARTED ---")
                    data['state'] = 'RUNNING'
                    data['start_verify_time'] = current_time 
                    blink(2)

        silence_duration = current_time - data['last_vibe_time']
        
        if data['state'] == 'VERIFYING' and silence_duration > FALSE_ALARM_TIME:
            if not CALIBRATION_MODE: print(f"[{name}] Just a bump. Resetting to IDLE.")
            data['state'] = 'IDLE'

        if data['state'] == 'RUNNING' and silence_duration > COOLDOWN_SEC:
            print(f"--- {name} FINISHED ---")
            send_alert(data['webhook'], name)
            data['state'] = 'IDLE'
            blink(5)

    # If calibrating, run faster (0.2s) to catch spikes. 
    # If production, run slower (1.0s) to save power/cpu.
    time.sleep(0.2 if CALIBRATION_MODE else 1)
