import os, sys, shutil, socket, threading, webbrowser, time
from datetime import datetime
from flask import Flask, render_template_string, request, send_from_directory, jsonify
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

console = Console()

# --- ЛОГИКА ПЕРЕЕЗДА ---
def organize_workspace():
    file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    
    if os.path.basename(current_dir).upper() == "LANHUB": return
    if os.path.basename(current_dir) in ["Desktop", "Рабочий стол"]:
        new_hub_dir = os.path.join(current_dir, "LANHUB")
        os.makedirs(os.path.join(new_hub_dir, "uploads"), exist_ok=True)
        shutil.copy2(file_path, os.path.join(new_hub_dir, file_name))
        if os.name == 'nt': os.startfile(new_hub_dir)
        sys.exit()

organize_workspace()

# --- КОНФИГУРАЦИЯ ---
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
CHAT_FILE = 'chat.txt'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
if not os.path.exists(CHAT_FILE): open(CHAT_FILE, 'w', encoding='utf-8').close()

# --- ИНТЕРФЕЙС (HTML/JS) ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html style="background:#121212; color:#eee; font-family:sans-serif;">
<head>
    <title>LAN HUB + IP CHAT</title>
    <style>
        .container { display: flex; height: 100vh; padding: 20px; gap: 20px; box-sizing: border-box; }
        .files-section { flex: 2; overflow-y: auto; background: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; }
        .chat-section { flex: 1.2; display: flex; flex-direction: column; background: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; }
        #chat-box { flex: 1; overflow-y: auto; border: 1px solid #333; padding: 10px; margin-bottom: 10px; font-size: 13px; background: #0f0f0f; border-radius: 5px; }
        .msg-item { margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #222; }
        .msg-ip { color: #00ffcc; font-weight: bold; }
        .msg-time { color: #666; font-size: 10px; margin-right: 5px; }
        input, button { padding: 10px; border-radius: 4px; border: 1px solid #444; background: #252525; color: white; }
        button { background: #00ffcc; color: #121212; font-weight: bold; border: none; cursor: pointer; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 15px; }
        .file-card { background: #252525; padding: 10px; border-radius: 5px; border: 1px solid #333; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="files-section">
            <h2 style="color:#00ffcc; margin-top:0;">📦 Files Area</h2>
            <form method="post" action="/upload" enctype="multipart/form-data">
                <input type="file" name="file"> <button type="submit">Upload</button>
            </form>
            <hr style="border:1px solid #333; margin:20px 0;">
            <div class="grid">
                {% for f in files %}
                <div class="file-card">
                    <a href="/dl/{{f}}" target="_blank" style="color:#00ffcc; text-decoration:none; font-size:11px; display:block; overflow:hidden;">{{f}}</a>
                    {% if f.lower().endswith(('.png','.jpg','.jpeg','.gif','.webp')) %}
                        <img src="/dl/{{f}}" style="width:100%; height:90px; object-fit:cover; margin-top:8px; border-radius:3px;">
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        <div class="chat-section">
            <h2 style="color:#00ffcc; margin-top:0;">💬 IP Chat</h2>
            <div id="chat-box"></div>
            <div style="display:flex; gap:8px;">
                <input type="text" id="msg" placeholder="Message..." style="flex:1;" onkeypress="if(event.keyCode==13)send()">
                <button onclick="send()">Send</button>
            </div>
        </div>
    </div>
    <script>
        async function loadChat() {
            const r = await fetch('/get_chat');
            const data = await r.json();
            const box = document.getElementById('chat-box');
            box.innerHTML = data.messages.map(m => `
                <div class="msg-item">
                    <span class="msg-time">${m.time}</span>
                    <span class="msg-ip">[${m.ip}]</span>: ${m.text}
                </div>
            `).join('');
            box.scrollTop = box.scrollHeight;
        }
        async function send() {
            const input = document.getElementById('msg');
            if(!input.value.trim()) return;
            await fetch('/send_chat', { method: 'POST', body: new URLSearchParams({'msg': input.value}) });
            input.value = ''; loadChat();
        }
        setInterval(loadChat, 2000); loadChat();
    </script>
</body>
</html>
'''

# --- FLASK ROUTES ---
@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE, files=os.listdir(UPLOAD_FOLDER))

@app.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('file')
    if f: f.save(os.path.join(UPLOAD_FOLDER, f.filename))
    return "<script>window.location='/';</script>"

@app.route('/get_chat')
def get_chat():
    messages = []
    if os.path.exists(CHAT_FILE):
        with open(CHAT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if "::" in line:
                    parts = line.split("::")
                    if len(parts) >= 3:
                        messages.append({"time": parts[0], "ip": parts[1], "text": parts[2].strip()})
    return jsonify({"messages": messages})

@app.route('/send_chat', methods=['POST'])
def send_chat():
    msg = request.form.get('msg', '').strip()
    user_ip = request.remote_addr
    now = datetime.now().strftime("%H:%M")
    if msg:
        with open(CHAT_FILE, 'a', encoding='utf-8') as f: 
            f.write(f"{now}::{user_ip}::{msg}\n")
        console.print(f"[dim]{now}[/dim] [bold cyan][{user_ip}][/bold cyan]: {msg}")
    return "OK"

@app.route('/dl/<path:n>')
def dl(n): return send_from_directory(UPLOAD_FOLDER, n)

# --- УТИЛИТЫ ---
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

def start_srv(h, p, table=False):
    if table:
        t = Table(title="HUB LIVE SESSION", border_style="cyan")
        t.add_column("Parameter"); t.add_column("Value")
        t.add_row("Address", f"http://{h}:{p}")
        t.add_row("IP Logging", "Enabled")
        console.print(t)
    
    url = f"http://{h if h != '0.0.0.0' else 'localhost'}:{p}"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    threading.Thread(target=lambda: app.run(host=h, port=p, debug=False, use_reloader=False), daemon=True).start()
    console.print(f"[bold green]✔ Server started![/bold green]")

# --- MAIN ---
def main():
    console.clear()
    console.print(Panel.fit("  [bold white]Local Hub + IP-Based Chat[/bold white]  ", border_style="cyan", subtitle="v1.5"))
    
    about = Table(show_header=True, header_style="bold magenta", box=None)
    about.add_column("Command", width=12); about.add_column("About")
    about.add_row("Start", "Local access only (127.0.0.1)")
    about.add_row("StartWA", "Full LAN access (your IP) + Table")
    about.add_row("Clear", "Wipe all files and chat history")
    about.add_row("Exit", "Close the hub")
    console.print(about)
    
    while True:
        cmd = Prompt.ask("\n[bold white]hub[/bold white]").lower().strip()
        if cmd == "start": start_srv("127.0.0.1", 5000)
        elif cmd == "startwa": start_srv(get_ip(), 5000, True)
        elif cmd == "clear":
            for f in os.listdir(UPLOAD_FOLDER): os.remove(os.path.join(UPLOAD_FOLDER, f))
            open(CHAT_FILE, 'w').close()
            console.print("[bold red]Hub data cleared![/bold red]")
        elif cmd in ["exit", "q"]: break
        else: console.print("[red]Unknown command.[/red]")

if __name__ == "__main__":
    main()
