# TailChat

**Private peer-to-peer chat, voice & video — secured by your Tailscale network.**

TailChat is a desktop application that lets people on the same [Tailscale](https://tailscale.com) network host and join private chat rooms with text messaging, voice calls, video calls, and file sharing. No public servers, no relay infrastructure — all traffic travels directly over your Tailscale mesh VPN.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Tailscale Check — What Happens on Launch](#tailscale-check--what-happens-on-launch)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Features](#features)
- [Workflow — Full App Flow](#workflow--full-app-flow)
- [Network & Protocol Design](#network--protocol-design)
- [Building the Executable](#building-the-executable)
- [Running from Source](#running-from-source)
- [Environment Variables](#environment-variables)

---

## How It Works

TailChat uses **Tailscale as the transport layer**. Tailscale assigns every device a stable private IP in the `100.64.x.x` range. TailChat uses those IPs to open direct TCP sockets between a host machine and joining peers — no port forwarding, no firewall rules needed.

```
┌──────────────┐        Tailscale VPN mesh         ┌──────────────┐
│  Host device │◄──────────────────────────────────►│ Peer device  │
│  (room host) │  TCP chat/file   UDP voice/video   │ (room guest) │
└──────────────┘                                    └──────────────┘
         │                                                  │
         └────────────── Supabase (room registry) ──────────┘
                         (room metadata only, no messages)
```

**Supabase** is used only as a room registry — it stores room names, host IPs, and member presence. All actual chat messages, voice audio, and video frames travel **directly** between devices over Tailscale.

---

## Tailscale Check — What Happens on Launch

Every time TailChat starts, the login screen runs through this exact sequence:

### Step 1 — Find the executable
`utils/helpers.py → get_tailscale_executable()`

Checks three locations in order:
1. `C:\Program Files\Tailscale\tailscale.exe` (default install path)
2. System `PATH` via `shutil.which("tailscale")`
3. `%ProgramFiles%\Tailscale\tailscale.exe` (environment variable fallback)

### Step 2 — Determine connection state
`utils/helpers.py → check_tailscale_status()`

| Result | What it means | UI response |
|---|---|---|
| `not_installed` | Executable not found anywhere | Shows "Download & Install Tailscale" button — launches the bundled `resources/tailscale-setup.exe` |
| `logged_out` / `stopped` | Installed but not authenticated or stopped | Opens browser to Tailscale login via `tailscale up`, polls every second for up to 60 s |
| `disconnected` | Running but no `100.x` IP yet | Retries automatically after 1.2 s |
| IP returned (`100.x.x.x`) | Connected and active | Proceeds to Google sign-in |

### Step 3 — Get the Tailscale IP
`utils/helpers.py → get_tailscale_ip()`

Runs `tailscale ip -4` via subprocess. If that fails (e.g. CLI not in PATH), scans all local network interfaces via Python's `socket` module looking for any IP starting with `100.` as a fallback.

### If Tailscale is NOT installed
The app shows a clear error message and launches the bundled **Tailscale installer** (`resources/tailscale-setup.exe`) via `os.startfile()`. After the user completes setup, they click "Re-check Tailscale" and the flow restarts.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **GUI framework** | [PySide6](https://doc.qt.io/qtforpython-6/) (Qt 6) | Cross-platform, mature, rich widgets |
| **UI components** | [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) (`qfluentwidgets`) | Windows 11-style polished controls |
| **Frameless window** | `qframelesswindow` | Custom title bar without OS chrome |
| **Authentication** | Google OAuth 2.0 via loopback server | Sign in with Google, no passwords |
| **Database / Auth** | [Supabase](https://supabase.com) (PostgreSQL + GoTrue) | Room registry, user profiles, RLS security |
| **Voice codec** | [PyOgg](https://github.com/TeamPyOgg/PyOgg) — Opus | Low-latency, high-quality audio at 24 kHz |
| **Audio I/O** | [SoundDevice](https://python-sounddevice.readthedocs.io/) | PortAudio bindings for mic + speaker |
| **Video capture** | [OpenCV Headless](https://opencv.org/) (`cv2`) | Camera capture, JPEG frame compression |
| **Networking** | Python `asyncio` — TCP + UDP | Chat & file transfer over TCP; voice & video over UDP |
| **Code protection** | [PyArmor](https://pyarmor.readthedocs.io/) | Obfuscates source before packaging |
| **Packaging** | [PyInstaller](https://pyinstaller.org/) | Bundles into a standalone `.exe` |
| **VPN transport** | [Tailscale](https://tailscale.com) | WireGuard-based mesh VPN — all traffic stays private |

---

## Project Structure

```
TailChat/
│
├── app.py                  # Entry point — creates QApplication, loads theme, launches window
│
├── gui/                    # All UI windows and dialogs
│   ├── main_window.py      # Root FramelessWindow + sidebar with profile avatar
│   ├── login_window.py     # Tailscale check + Google sign-in screen
│   ├── home_window.py      # Lobby — room list, peer list, host/join buttons
│   ├── room_window.py      # In-room view — chat, voice, video, file transfer
│   ├── settings_window.py  # Settings dialog — profile photo, audio, theme
│   ├── profile_window.py   # View/edit user profile (name, bio, photo, links)
│   ├── create_room.py      # "Host a Room" dialog
│   ├── image_cropper.py    # Circular profile photo crop tool
│   └── styles.py           # Global QSS stylesheets (dark + light theme)
│
├── auth/
│   ├── session.py          # UserSession singleton — holds login state, syncs to Supabase
│   └── google_login.py     # Opens browser OAuth, captures token via loopback HTTP server
│
├── network/
│   ├── host.py             # TailChatHost — asyncio TCP server for chat + file routing
│   ├── client.py           # TailChatClient — connects to host, emits Qt signals
│   └── protocol.py         # Packet format: newline-delimited JSON, 1 MB max per packet
│
├── services/
│   └── room_service.py     # Orchestrator — starts/stops host, voice, video nodes together
│
├── voice/
│   ├── microphone.py       # Captures mic input via sounddevice
│   ├── sender.py           # Encodes audio with Opus, sends UDP to voice server
│   ├── receiver.py         # Receives UDP audio, decodes Opus, hands to mixer
│   ├── speaker.py          # SpeakerMixer — plays decoded audio from all peers
│   └── voice_server.py     # UDP relay — forwards voice packets between peers in a room
│
├── video/
│   ├── camera.py           # OpenCV camera capture with start/stop/frame callback
│   ├── video_sender.py     # Captures frames, JPEG-compresses, sends UDP
│   ├── video_receiver.py   # Receives JPEG frames, decodes, emits Qt signals for display
│   └── video_server.py     # UDP relay for video frames (mirrors voice_server design)
│
├── database/
│   ├── supabase.py         # get_supabase() — singleton Supabase client
│   ├── rooms.py            # list_active_rooms(), create_room(), delete_room()
│   ├── room_members.py     # join_room_db(), leave_room_db(), get_room_members()
│   └── users.py            # get_user_profile(), upsert_user()
│
├── files/
│   ├── uploader.py         # Sends a file over the host's TCP file pipe
│   └── downloader.py       # Receives a file from the TCP file pipe, writes to disk
│
├── config/
│   ├── settings.py         # load_settings() / save_settings() — JSON config file
│   └── config.py           # Legacy config helpers
│
├── utils/
│   ├── helpers.py          # Tailscale detection + IP resolution (see above)
│   ├── constants.py        # Ports, paths, audio settings, app name
│   └── logger.py           # Rotating file logger → %APPDATA%/TailChat/logs/
│
├── resources/
│   └── tailscale-setup.exe # Bundled Tailscale installer (launched if not installed)
│
├── assets/
│   ├── images/app_logo.png # App icon
│   └── icons/              # UI icons (mic, camera, deaf, etc.)
│
├── obf_dist/               # PyArmor-obfuscated source (git-ignored)
│   └── dist/TailChat/      # Final built EXE lives here
│
├── .env                    # Secrets — git-ignored (see .env.example)
├── .env.example            # Template for required environment variables
├── requirements.txt        # Python dependencies
├── build.ps1               # One-click build script (obfuscate → package → zip)
└── BUILD_NOTES.md          # Detailed build process documentation
```

---

## Features

- **Text chat** — Room-scoped channels with message history (last 100 messages replayed on join)
- **Voice calls** — Low-latency Opus-encoded audio with mute/deafen controls.
- **Dynamic Audio Indicator** — Real-time RMS audio level calculation creates a reactive, pulsing glowing border around avatars when speaking.
- **Video calls** — 15 fps JPEG-compressed webcam stream with camera toggle
- **File transfer** — Direct peer-to-peer file sending via the host's TCP file pipe with accept/decline UI
- **Profile photos & Editor** — Upload, pan (drag), zoom (scroll), and rotate 360-degrees (slider) your circular profile photo.
- **In-App Documentation** — A dedicated "About" page with step-by-step connection guides for Tailscale, including shared vs. separate account setups.
- **Private rooms** — Optional password protection for rooms
- **Remember Me** — 7-day local session persistence (no re-login needed)
- **Theme switching** — Dark / Light theme toggle in settings
- **Tailscale-native** — No NAT traversal headaches; everything uses your mesh VPN IPs

---

## Workflow — Full App Flow

```
App launches
    │
    ▼
Login screen
    ├─ check_tailscale_status()
    │       ├─ not_installed  ──► Show installer button → launch tailscale-setup.exe
    │       ├─ stopped/logged_out ► run 'tailscale up' → poll for IP (60s)
    │       └─ connected (100.x.x.x) ──► Try loading saved 7-day session
    │                                           │
    │                              session found ──► Go to Lobby
    │                              no session   ──► Google OAuth flow
    │                                                   │
    │                                           Browser opens → user signs in
    │                                           Loopback server captures token
    │                                           Supabase Auth verifies token
    │                                           session.sync_to_supabase() upserts user
    │                                                   │
    ▼                                                   ▼
Lobby (Home screen)
    ├─ Lists active rooms from Supabase (refreshed every 10s)
    ├─ Shows online Tailscale peers (tailscale status --json)
    │
    ├─ [Host a Room]
    │       ├─ Creates room record in Supabase (name, host_ip, password hash)
    │       ├─ Starts TailChatHost (TCP chat server on port 52341)
    │       ├─ Starts file server (TCP on port 52342)
    │       ├─ Starts VoiceServer (UDP on port 52343)
    │       ├─ Starts VideoServer (UDP on port 52344)
    │       └─ Navigates to Room view
    │
    └─ [Join Selected Room]
            ├─ Reads host_ip from Supabase room record
            ├─ Connects TailChatClient to host_ip:52341 (TCP)
            ├─ Sends join packet (user_id, display_name, avatar, tailscale_ip)
            ├─ Host validates UUID format + optional password
            ├─ Receives join_ack (message history + members list)
            └─ Navigates to Room view

Room view
    ├─ Text chat  ──► send_packet() → host broadcasts to all peers
    ├─ Voice
    │       ├─ VoiceSender: mic → Opus encode → UDP → VoiceServer → all peers
    │       └─ VoiceReceiver: UDP → Opus decode → SpeakerMixer → audio output
    ├─ Video
    │       ├─ VideoSender: OpenCV frame → JPEG compress → UDP → VideoServer → peers
    │       └─ VideoReceiver: UDP → JPEG decode → Qt signal → video widget
    └─ File transfer
            ├─ Sender: QFileDialog → file_offer packet → host routes to recipient
            ├─ Recipient: accept/decline dialog → file_accept packet → host opens TCP pipe
            └─ Stream: sender connects file server → recipient connects → bytes piped directly

Leave room
    ├─ Sends leave packet
    ├─ Stops voice/video senders
    ├─ Host: closes TCP file pipe, broadcasts user_left
    ├─ Updates Supabase (removes room_member row)
    └─ Returns to Lobby
```

---

## Network & Protocol Design

### Chat — TCP, newline-delimited JSON
All chat, signalling, and file-offer packets are JSON objects terminated by `\n`.  
Max packet size: **1 MB** (enforced via `reader.readuntil(b'\n', limit=1_048_576)` to prevent DoS).

```json
{ "type": "chat", "sender_id": "uuid", "sender_name": "Alice", "content": "hello", "timestamp": "...", "channel": "general" }
{ "type": "file_offer", "file_id": "uuid", "file_name": "photo.png", "file_size": 204800, "sender_id": "...", "recipient_id": "..." }
{ "type": "voice_state", "user_id": "...", "muted": true }
```

### Voice & Video — UDP
```
[1B type][user_id_len 1B][user_id bytes][2B payload_len][payload bytes]
```
- Voice: Opus-encoded frames at 24 kHz mono, 20 ms per packet
- Video: JPEG frames at 640×360, quality 60, ~15 fps

### Ports
| Port | Protocol | Purpose |
|------|----------|---------|
| 52341 | TCP | Chat messages + signalling |
| 52342 | TCP | File transfer pipe |
| 52343 | UDP | Voice (Opus audio) |
| 52344 | UDP | Video (JPEG frames) |

---

## Building the Executable

Requires the `.venv` to be set up (see Running from Source below).

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

The script:
1. Runs **PyArmor** to obfuscate all source into `obf_dist/` (skips gracefully if trial expired — reuses existing obfuscated files)
2. Patches `obf_dist/app.py` with a plain-Python bootstrapper
3. Runs **PyInstaller** with the full `TailChat.spec` (168 hidden imports)
4. Creates `obf_dist/dist/TailChat_Release.zip`

Output: `obf_dist/dist/TailChat/TailChat.exe` + `_internal/` folder

---

## Running from Source

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
pip install pyogg pyarmor pyinstaller

# 3. Copy and fill in your secrets
copy .env.example .env
# Edit .env with your Supabase URL, anon key, and Google OAuth client ID

# 4. Run
python app.py
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
# Supabase — room registry and user auth
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# Google OAuth — sign in with Google
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com

# Cloudflare R2 — file storage (optional, for large file uploads)
R2_BUCKET_NAME=your-bucket
R2_ACCESS_KEY_ID=your-key-id
R2_SECRET_ACCESS_KEY=your-secret
R2_ENDPOINT_URL=https://account-id.r2.cloudflarestorage.com
R2_PUBLIC_URL=https://pub-xxx.r2.dev
```

> ⚠️ Never commit `.env` to version control. It is listed in `.gitignore`.

---

## Security Notes

- All traffic between peers is encrypted by **WireGuard** (Tailscale's underlying protocol)
- Source code is obfuscated with **PyArmor** before packaging
- Chat packets are capped at 1 MB to prevent memory exhaustion (DoS protection)
- Room join packets validate UUID format to reject spoofed user IDs
- Global rate limiting: max 50 packets/second per user
- Row-Level Security (RLS) is enabled on all Supabase tables

---

*Built with Python 3.10 · PySide6 6.7 · Tailscale · Supabase*
