import urllib.parse
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from database.supabase import get_supabase
from utils.constants import OAUTH_REDIRECT_PORT
from utils.logger import logger

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    tokens = {}
    completed_event = threading.Event()

    def log_message(self, format, *args):
        # Suppress server logging to console to keep outputs clean
        pass

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path == "/callback":
            # 1. Check if PKCE auth code is present in query parameters
            code = query.get("code", [None])[0]
            if code:
                try:
                    logger.info("PKCE Authorization code received. Exchanging code for session...")
                    supabase = get_supabase()
                    res = supabase.auth.exchange_code_for_session({"auth_code": code})
                    
                    if res and res.session:
                        OAuthCallbackHandler.tokens = {
                            "access_token": res.session.access_token,
                            "refresh_token": res.session.refresh_token
                        }
                        
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html")
                        self.end_headers()
                        
                        success_html = """
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>Login Successful</title>
                            <style>
                                body {
                                    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
                                    background: linear-gradient(145deg, #0D0D12, #111118, #0A0A0F);
                                    color: #F0F0F5;
                                    text-align: center;
                                    padding-top: 100px;
                                    margin: 0;
                                    min-height: 100vh;
                                }
                                .container {
                                    max-width: 460px;
                                    margin: 0 auto;
                                    background: rgba(255, 255, 255, 0.03);
                                    border: 1px solid rgba(255, 255, 255, 0.07);
                                    border-top: 1px solid rgba(255, 255, 255, 0.15);
                                    backdrop-filter: blur(20px);
                                    padding: 48px;
                                    border-radius: 24px;
                                    box-shadow: 0 8px 40px rgba(0,0,0,0.4);
                                }
                                .success-icon {
                                    font-size: 56px;
                                    color: rgba(160,170,255,0.8);
                                    margin-bottom: 20px;
                                }
                                h1 { font-size: 22px; margin-bottom: 10px; color: #F0F0F5; font-weight: 600; }
                                p { color: #8E8E9A; }
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <div class="success-icon">✓</div>
                                <h1>Successfully Logged In!</h1>
                                <p>You can close this browser tab now and return to the TailChat desktop application.</p>
                            </div>
                        </body>
                        </html>
                        """
                        self.wfile.write(success_html.encode("utf-8"))
                        OAuthCallbackHandler.completed_event.set()
                        return
                    else:
                        raise ValueError("No session returned from exchange.")
                except Exception as e:
                    logger.error(f"Failed to exchange PKCE auth code: {e}")
                    self.send_response(400)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(f"Authentication failed: {str(e)}".encode("utf-8"))
                    return

            # 2. Implicit/Implicit grant flow: Fallback to JS hash parsing
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            
            # Render page to extract hash fragment (client-side tokens)
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Connecting to TailChat...</title>
                <style>
                    body {
                        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
                        background: linear-gradient(145deg, #0D0D12, #111118, #0A0A0F);
                        color: #F0F0F5;
                        text-align: center;
                        padding-top: 100px;
                        margin: 0;
                        min-height: 100vh;
                    }
                    .container {
                        max-width: 460px;
                        margin: 0 auto;
                        background: rgba(255, 255, 255, 0.03);
                        border: 1px solid rgba(255, 255, 255, 0.07);
                        border-top: 1px solid rgba(255, 255, 255, 0.15);
                        backdrop-filter: blur(20px);
                        padding: 48px;
                        border-radius: 24px;
                        box-shadow: 0 8px 40px rgba(0,0,0,0.4);
                    }
                    .spinner {
                        border: 3px solid rgba(255, 255, 255, 0.06);
                        border-left-color: rgba(160,170,255,0.6);
                        border-radius: 50%;
                        width: 44px;
                        height: 44px;
                        animation: spin 1s linear infinite;
                        margin: 0 auto 24px;
                    }
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                    h1 { font-size: 22px; margin-bottom: 10px; color: #F0F0F5; font-weight: 600; }
                    p { color: #8E8E9A; }
                </style>
            </head>
            <body>
                <div class="container" id="content-container">
                    <div class="spinner"></div>
                    <h1>Connecting to TailChat</h1>
                    <p>Transferring authentication session. Please do not close this tab...</p>
                </div>
                
                <script>
                    const hash = window.location.hash.substring(1);
                    if (hash) {
                        window.location.href = "/token?" + hash;
                    } else {
                        const container = document.getElementById("content-container");
                        if (container) {
                            container.innerHTML = "<h1>Authentication Failed</h1><p>No authorization data was found in the URL. Please close this and try again.</p>";
                        }
                    }
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))

        elif path == "/token":
            access_token = query.get("access_token", [None])[0]
            refresh_token = query.get("refresh_token", [None])[0]

            if access_token and refresh_token:
                OAuthCallbackHandler.tokens = {
                    "access_token": access_token,
                    "refresh_token": refresh_token
                }
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                
                success_html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Login Successful</title>
                    <style>
                        body {
                            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
                            background: linear-gradient(145deg, #0D0D12, #111118, #0A0A0F);
                            color: #F0F0F5;
                            text-align: center;
                            padding-top: 100px;
                            margin: 0;
                            min-height: 100vh;
                        }
                        .container {
                            max-width: 460px;
                            margin: 0 auto;
                            background: rgba(255, 255, 255, 0.03);
                            border: 1px solid rgba(255, 255, 255, 0.07);
                            border-top: 1px solid rgba(255, 255, 255, 0.15);
                            backdrop-filter: blur(20px);
                            padding: 48px;
                            border-radius: 24px;
                            box-shadow: 0 8px 40px rgba(0,0,0,0.4);
                        }
                        .success-icon {
                            font-size: 56px;
                            color: rgba(160,170,255,0.8);
                            margin-bottom: 20px;
                        }
                        h1 { font-size: 22px; margin-bottom: 10px; color: #F0F0F5; font-weight: 600; }
                        p { color: #8E8E9A; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="success-icon">✓</div>
                        <h1>Successfully Logged In!</h1>
                        <p>You can close this browser tab now and return to the TailChat desktop application.</p>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(success_html.encode("utf-8"))
                OAuthCallbackHandler.completed_event.set()
            else:
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"Invalid OAuth response.")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

def start_oauth_server():
    """Starts the localhost HTTP redirect server."""
    server = HTTPServer(("localhost", OAUTH_REDIRECT_PORT), OAuthCallbackHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return server

def run_google_login(timeout: int = 120) -> dict | None:
    """
    Triggers Google OAuth login. Opens the browser, listens for login token callbacks.
    Returns session dict {"access_token": ..., "refresh_token": ...} or None if failed/timed out.
    """
    OAuthCallbackHandler.tokens = {}
    OAuthCallbackHandler.completed_event.clear()

    # Start loopback webserver
    server = start_oauth_server()
    logger.info(f"OAuth Loopback server started on localhost:{OAUTH_REDIRECT_PORT}")

    try:
        # Get OAuth URL from Supabase
        supabase = get_supabase()
        res = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": f"http://localhost:{OAUTH_REDIRECT_PORT}/callback"
            }
        })
        
        # Access the oauth authorization url
        oauth_url = getattr(res, "url", None)
        if not oauth_url and isinstance(res, dict):
            oauth_url = res.get("url")
            
        if not oauth_url:
            logger.error("Failed to get OAuth URL from Supabase.")
            return None

        logger.info("Opening system browser to authenticate...")
        webbrowser.open(oauth_url)

        # Wait for the login callback event
        success = OAuthCallbackHandler.completed_event.wait(timeout)
        if success:
            logger.info("OAuth session tokens received successfully.")
            tokens = OAuthCallbackHandler.tokens
            
            # Apply session directly to Supabase client
            supabase.auth.set_session(
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"]
            )
            return tokens
        else:
            logger.warning("OAuth login timed out or was cancelled by the user.")
            return None

    except Exception as e:
        logger.error(f"Error during Google OAuth process: {e}")
        return None
    finally:
        # Stop loopback server
        logger.info("Shutting down OAuth loopback server...")
        try:
            # Shutdown in a background thread to prevent deadlocking the Login QThread on Windows
            threading.Thread(target=server.shutdown, daemon=True).start()
            server.server_close()
            logger.info("OAuth loopback server closed.")
        except Exception as e:
            logger.debug(f"Error during OAuth server shutdown: {e}")
