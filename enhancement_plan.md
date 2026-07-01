# TailChat - Codebase Audit & Enhancement Plan

## 🔒 1. Security Vulnerabilities Found

### CRITICAL
| # | File | Issue | Fix |
|---|------|-------|-----|
| 1 | [.env](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/.env) | **Google OAuth `clientSecret` hardcoded** in plaintext. If this repo is pushed to GitHub, anyone can impersonate your Google OAuth app. | Move `clientSecret` to a system environment variable or encrypted keyring. Never commit it. |
| 2 | [.env](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/.env) | **Supabase Anon Key exposed**. While Anon keys are designed to be public, combined with RLS misconfigurations, this can allow unauthenticated data access. | Ensure RLS is enabled on ALL tables (already done). Add `.env` to `.gitignore`. |
| 3 | [network/protocol.py:19](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/network/protocol.py#L16-L27) | **No maximum line length on `reader.readline()`**. A malicious client can send an infinitely long line to exhaust server RAM (OOM attack). | Use `reader.readuntil(b'\n', limit=1_048_576)` to cap at 1MB. |
| 4 | [network/host.py:79](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/network/host.py#L79) | **No validation of `user_id` from join packet**. A client can spoof any user_id (e.g., the host's) and impersonate them in chat, file transfers, and voice. | Validate the join packet `user_id` against the authenticated Supabase session token. |

### HIGH
| # | File | Issue | Fix |
|---|------|-------|-----|
| 5 | [network/host.py:118](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/network/host.py#L118) | **No input sanitization on chat `content`**. HTML injection is possible — a user can send `<script>` tags that render in the `QTextEdit` via `append()`. | Escape HTML entities with `html.escape()` before broadcasting. |
| 6 | [files/downloader.py:29](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/files/downloader.py#L29) | **Path traversal risk**: The `save_path` comes from `QFileDialog`, but the file_name from the sender's packet is not validated. A crafted `../../../` filename could write to system directories. | Use `os.path.basename()` on the filename before constructing save path. |
| 7 | [voice/voice_server.py:55](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/voice/voice_server.py#L55) | **No user_id validation on UDP voice packets**. Any machine on the Tailscale network can send spoofed voice data with a forged user_id. | Maintain a set of authenticated user_ids from the TCP join flow and reject unknown UDP senders. |
| 8 | [network/host.py:106](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/network/host.py#L106) | **No rate limiting on chat messages**. A client can flood the room with thousands of messages per second. | Implement a per-user rate limiter (e.g., max 10 messages/second). |

### MEDIUM
| # | File | Issue | Fix |
|---|------|-------|-----|
| 9 | [auth/session.py:42](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/auth/session.py#L42) | `"last_seen_at": "now()"` is sent as a literal string, not a database function call. Supabase will store it as the string `"now()"`. | Use `datetime.datetime.utcnow().isoformat()` instead. |
| 10 | [network/host.py:240-242](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/network/host.py#L240-L242) | **Dangling file connections**: If only one party (sender or recipient) connects to the file server and the other never does, the first connection hangs open forever, leaking sockets. | Add a 30-second timeout for unmatched file connections. |

---

## ⚡ 2. Performance Bottlenecks Found

| # | File | Issue | Impact | Fix |
|---|------|-------|--------|-----|
| 1 | [services/room_service.py:170](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/services/room_service.py#L170) | `leave_room()` calls `future.result()` **without timeout**, blocking the Qt main thread indefinitely if cleanup hangs. | HIGH | Add `timeout=5` to prevent UI freezes. |
| 2 | [config/settings.py:38-41](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/config/settings.py#L38-L41) | `get_setting()` reads and parses the JSON file from disk on **every call**. This is called frequently during file transfers. | MEDIUM | Cache settings in memory; reload only on save. |
| 3 | [gui/room_window.py:194](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/gui/room_window.py#L194) | `refresh_roster()` calls `get_room_members()` which makes a Supabase HTTP API call on the main thread. | MEDIUM | Move to a background thread with `QTimer` and signals. |
| 4 | [voice/speaker.py:60](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/voice/speaker.py#L60) | Speaker mixer callback acquires a `threading.Lock` inside the audio callback (real-time thread). Lock contention causes audio glitches. | MEDIUM | Use lock-free `collections.deque` instead of `queue.Queue` with lock. |
| 5 | [network/host.py:122-123](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/network/host.py#L122-L123) | `message_history.pop(0)` on a list is O(n). | LOW | Use `collections.deque(maxlen=100)`. |

---

## 🐛 3. Code Quality Issues

| # | File | Issue |
|---|------|-------|
| 1 | [gui/room_window.py:392-442](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/gui/room_window.py#L392-L442) | `on_transfer_finished` has dead/incomplete code paths (`if ... and not ... and msg == "Accepting..."`) that never execute. |
| 2 | [network/host.py:222](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/network/host.py#L222) | Host file pipe uses fixed 64KB chunks — should also use adaptive chunking for consistency. |
| 3 | [voice/sender.py:2](file:///D:/otherAndGames/SIDE%20PROJECTS/TailChat/voice/sender.py#L2) | `from pyogg.opus import OpusEncoder` — works but fragile. Should add a try/except fallback. |
| 4 | Multiple files | Missing `__init__.py` in some package directories. |

---

## 🎥 4. Video Calling Feature — Implementation Plan

### Architecture
We will use **OpenCV** (`cv2`) for camera capture and **JPEG compression** for frame encoding, streamed over the existing **UDP voice infrastructure** (extended to carry both audio and video). The UI will use Discord-style dark theme with a video grid panel.

### New Files to Create
| File | Purpose |
|------|---------|
| `video/camera.py` | Camera capture using OpenCV with start/stop/frame callback |
| `video/video_sender.py` | Captures frames, compresses to JPEG, sends over UDP |
| `video/video_receiver.py` | Receives JPEG frames over UDP, decodes, emits Qt signals |
| `video/video_server.py` | UDP forwarding server for video frames (like voice_server.py) |

### Files to Modify
| File | Changes |
|------|---------|
| `gui/room_window.py` | Add video grid panel, camera/deafen controls, Discord-style bottom bar |
| `gui/styles.py` | Add Discord-inspired dark theme for video panels and controls |
| `services/room_service.py` | Start/stop video server, sender, receiver alongside voice |
| `network/client.py` | Add `video_state_changed` signal for camera on/off |
| `network/host.py` | Route `video_state` packets |
| `utils/constants.py` | Add `DEFAULT_VIDEO_PORT` |
| `requirements.txt` | Add `opencv-python` |

### Discord-Style Controls
Bottom bar with circular icon buttons:
- 🎤 **Mic Toggle** — mute/unmute microphone
- 🔇 **Deafen Toggle** — mute ALL incoming audio + video (like Discord)
- 📹 **Camera Toggle** — turn camera on/off
- 📞 **Leave Call** — leave the room

### Video Protocol
- UDP packets: `[1B type][1B user_id_len][user_id][2B frame_len][JPEG bytes]`
- Max frame size: ~50KB (320×240 JPEG at quality 60)
- Target FPS: 15fps (balanced quality/bandwidth)
- Separate UDP port from voice to avoid head-of-line blocking

> [!IMPORTANT]
> This plan covers security fixes, performance optimizations, and full video calling with Discord-style UI. Shall I proceed with implementation?
