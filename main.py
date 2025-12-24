import network
import time
import urequests
import _thread
import web_server
from machine import ADC, Pin
import rp2
import secrets

# ================= CONFIGURATION =================
CALIBRATION_MODE = False 

# Pull from secrets.py
SSID = secrets.WIFI_SSID
PASSWORD = secrets.WIFI_PASSWORD
NTFY_URL = secrets.NTFY_URL

# Rebuild URLs using secrets
HA_IP = secrets.HA_IP
HA_PORT = secrets.HA_PORT
WASHER_URL = f"http://{HA_IP}:{HA_PORT}/api/webhook/{secrets.WASHER_WEBHOOK_ID}"
DRYER_URL  = f"http://{HA_IP}:{HA_PORT}/api/webhook/{secrets.DRYER_WEBHOOK_ID}"

# TOGGLES: Enable/Disable sensors here
WASHER_CONNECTED = True
DRYER_CONNECTED = False

# SENSOR SETTINGS (Adjusted for Peak Sensing)
THRESHOLD = 2500        # Recommended starting point for Peak sensing
START_CONFIRM_SEC = 30  # Sustained vibration to count as "Started"
COOLDOWN_SEC = 360      # 6 Minutes of silence = "Finished"
FALSE_ALARM_TIME = 10   # Short bumps are ignored

# ================= SETUP =================
led = Pin("LED", Pin.OUT)
machines = {}

if WASHER_CONNECTED:
    print("Initializing Washer Sensor...")
    machines['Washer'] = {
        'state': 'IDLE', 
        'adc': ADC(27),
        'webhook': WASHER_URL, 
        'last_vibe_time': 0, 
        'start_verify_time': 0, 
        'current_vibration': 0,
        'max_peak': 0  # <--- Field for tracking session high
    }

# ================= FUNCTIONS =================
def get_max_peak(adc_sensor, samples=1000):
    """Samples quickly to catch the highest vibration peak."""
    max_val = 0
    for _ in range(samples):
        val = adc_sensor.read_u16()
        if val > max_val:
            max_val = val
    return max_val

def blink(times, speed=0.1):
    for _ in range(times):
        led.on(); time.sleep(speed)
        led.off(); time.sleep(speed)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False); time.sleep(0.5); wlan.active(True)
    rp2.country('US')
    wlan.config(pm=0xa11140)
    print(f"Connecting to {SSID}...")
    wlan.connect(SSID, PASSWORD)
    
    max_wait = 20
    while max_wait > 0:
        if wlan.status() == 3: break
        max_wait -= 1; time.sleep(1)
            
    if wlan.status() == 3:
        ip = wlan.ifconfig()[0]
        print(f"Connected! IP: {ip}")
        blink(3); return ip
    else:
        print("\n!!! WIFI CONNECTION FAILED !!!")
        blink(10, 0.05); return None

def send_alert(ha_url, machine_name):
    if CALIBRATION_MODE: return
    try: urequests.post(ha_url)
    except Exception as e: print(f"HA Failed: {e}")
    try:
        msg = f"{machine_name} has finished!"
        urequests.post(NTFY_URL, data=msg.encode('utf-8'))
    except Exception as e: print(f"Ntfy Failed: {e}")

# ================= MAIN LOOP =================
ip_address = connect_wifi()
if ip_address:
    try:
        _thread.start_new_thread(web_server.run_server, (machines, ip_address))
    except Exception as e: print(f"Failed to start web server: {e}")

while True:
    current_time = time.time()
    for name, data in machines.items():
        vibration = get_max_peak(data['adc'])
        data['current_vibration'] = vibration 
        
        # Track the highest peak seen in this session
        if vibration > data['max_peak']:
            data['max_peak'] = vibration

        if CALIBRATION_MODE:
            print(f"[{name}] Peak: {vibration:5} / Session Max: {data['max_peak']} / Thresh: {THRESHOLD}")

        # LOGIC
        if vibration > THRESHOLD:
            data['last_vibe_time'] = current_time 
            if data['state'] == 'IDLE':
                data['state'] = 'VERIFYING'
                data['start_verify_time'] = current_time
            elif data['state'] == 'VERIFYING':
                if (current_time - data['start_verify_time']) > START_CONFIRM_SEC:
                    data['state'] = 'RUNNING'
                    data['start_verify_time'] = current_time 
                    blink(2)

        silence_duration = current_time - data['last_vibe_time']
        if data['state'] == 'VERIFYING' and silence_duration > FALSE_ALARM_TIME:
            data['state'] = 'IDLE'

        if data['state'] == 'RUNNING' and silence_duration > COOLDOWN_SEC:
            print(f"--- {name} FINISHED ---")
            send_alert(data['webhook'], name)
            data['state'] = 'IDLE'
            data['max_peak'] = 0  # Reset max peak for next load
            blink(5)

    time.sleep(0.1 if CALIBRATION_MODE else 1)