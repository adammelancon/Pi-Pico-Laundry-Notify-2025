import socket
import network
import time

# This function will run on the Second Core
def run_server(machines_data, ip_address):
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    
    print(f"Web Interface started on http://{ip_address}")

    while True:
        try:
            # Accept new connection
            cl, addr = s.accept()
            request = cl.recv(1024)
            # We don't really care what the request is (GET /), just serve the page
            
            # --- GENERATE HTML ---
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Laundry Status</title>
                <meta http-equiv="refresh" content="5">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: sans-serif; text-align: center; background: #222; color: #eee; }
                    .card { background: #333; margin: 20px; padding: 20px; border-radius: 10px; }
                    .status { font-size: 2em; font-weight: bold; }
                    .RUNNING { color: #00ff00; }
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
                
                # Calculate Duration
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
                    <p><small>Vibration Level: {vibe}</small></p>
                </div>
                """

            html += "</body></html>"
            
            # --- SEND RESPONSE ---
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + html
            cl.send(response)
            cl.close()
            
        except Exception as e:
            print(f"Web Server Error: {e}")
            # Don't crash the thread, just close connection and retry
            if 'cl' in locals():
                cl.close()
