import socket
import network
import time

# This function runs on the Second Core
def run_server(machines_data, ip_address):
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    
    print(f"Web Interface started on http://{ip_address}")

    while True:
        try:
            cl, addr = s.accept()
            request = cl.recv(1024)
            
            # --- GENERATE HTML ---
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Laundry Status</title>
                <meta http-equiv="refresh" content="5">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <link id="favicon" rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🔴</text></svg>">
                <style>
                    body { font-family: sans-serif; text-align: center; background: #222; color: #eee; }
                    .card { background: #333; margin: 20px; padding: 20px; border-radius: 10px; border: 1px solid #444; }
                    .status { font-size: 2em; font-weight: bold; }
                    .RUNNING { color: #00ff00; text-shadow: 0 0 10px #00ff00; }
                    .IDLE { color: #888; }
                    .VERIFYING { color: #ffaa00; }
                </style>
            </head>
            <body>
                <h1>Laundry Monitor</h1>
            """
            
            # Loop through machines to create cards
            for name, data in machines_data.items():
                state = data['state']
                vibe = data.get('current_vibration', 0)
                max_vibe = data.get('max_peak', 0)
                
                duration_str = "--:--"
                if state == 'RUNNING':
                    elapsed = time.time() - data['start_verify_time']
                    mins = int(elapsed // 60)
                    secs = int(elapsed % 60)
                    duration_str = f"{mins}m {secs}s"
                
                html += f"""
                <div class="card">
                    <h2>{name}</h2>
                    <div class="status {state}">{state}</div>
                    <p>Runtime: {duration_str}</p>
                    <p>Session Max: {max_vibe}</p> 
                    <p><small>Current Vibration: {vibe}</small></p>
                </div>
                """
            t = time.localtime()
            timestamp = f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d}" # HH:MM:SS format
            
            html += f"""
                <div style="margin-top: 30px; color: #666; font-size: 0.8em;">
                    Last Updated: {timestamp}
                </div>
            """
            
            # Add the script once after the machine loop is finished
            html += """
                <script>
                    function updateFavicon() {
                        const isRunning = document.querySelector('.RUNNING') !== null;
                        const favicon = document.getElementById('favicon');
                        const emoji = isRunning ? '🟢' : '🔴';
                        favicon.setAttribute('href', `data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>${emoji}</text></svg>`);
                    }
                    updateFavicon();
                </script>
            </body></html>
            """            
            
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + html
            cl.send(response)
            cl.close()
            
        except Exception as e:
            print(f"Web Server Error: {e}")
            if 'cl' in locals():
                cl.close()