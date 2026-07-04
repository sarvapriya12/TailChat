from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, 
                               QFrame, QHBoxLayout)
from PySide6.QtCore import Qt
from qfluentwidgets import SmoothScrollArea

class AboutPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #121212;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header = QWidget()
        header.setFixedHeight(64)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(32, 0, 32, 0)
        title = QLabel("ℹ  About TailChat & Networking")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #F8F8F2; background: transparent;")
        h_lay.addWidget(title)
        h_lay.addStretch()
        main_layout.addWidget(header)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(255,255,255,0.05); max-height: 1px; border: none;")
        main_layout.addWidget(sep)
        
        # Scroll Area
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")
        
        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(40, 24, 40, 40)
        c_lay.setSpacing(24)
        
        # HTML Content
        html_content = """
        <style>
            h2 { color: #8B5CF6; font-size: 22px; font-weight: 700; margin-bottom: 12px; margin-top: 0px; }
            h3 { color: #A78BFA; font-size: 16px; font-weight: 600; margin-top: 16px; margin-bottom: 8px; }
            p { color: #D1D5DB; font-size: 14px; line-height: 1.5; margin-bottom: 10px; }
            .code-block { 
                background-color: #1E1E1E; 
                color: #10B981; 
                padding: 12px; 
                border-radius: 6px; 
                font-family: Consolas, monospace; 
                font-size: 13px; 
                margin: 8px 0; 
                border: 1px solid rgba(255,255,255,0.1); 
            }
            .highlight { color: #FBCFE8; font-weight: 600; }
        </style>
        
        <h2>How TailChat Works</h2>
        <p>TailChat is a <b>Peer-to-Peer (P2P)</b> secure chat application. This means that unlike Discord or Slack, your messages, files, voice, and video data <b>do not go through a central server</b>. Instead, they flow directly between your computer and your friend's computer.</p>
        <p>Because home internet routers typically block direct connections to protect against hackers, TailChat requires you to use <b>Tailscale</b>. Tailscale creates a secure Virtual Private Network (VPN) mesh, giving each device a unique <span class="highlight">100.x.y.z</span> IP address that allows direct, secure communication across the internet.</p>

        <br>
        <h2>Step-by-Step Connection Guide</h2>
        
        <h3>Step 1: Install Tailscale</h3>
        <p>Both you and your friend need to install Tailscale and log in.</p>
        <p>If you don't have it installed, you can download it from their official website:</p>
        <p class="code-block">https://tailscale.com/download</p>
        
        <h3>Step 2: Connect Your Networks</h3>
        <p>Your connection method depends on whether you are using the same Google Account or different ones:</p>
        <p><b>Scenario A: Same Gmail Account</b></p>
        <p>If you both log into Tailscale with the exact same Gmail ID, you are automatically placed on the same secure network (Tailnet). You don't need to do anything else!</p>
        <br>
        <p><b>Scenario B: Different Gmail Accounts</b></p>
        <p>Since you are on different accounts, Tailscale puts you in separate private networks. You must bridge them using one of these two methods:</p>
        <p>- <i>Node Sharing</i>: You can generate a specific share link for your computer from the Tailscale Admin Console and send it to your friend.</p>
        <p>- <i>Invite to Tailnet</i>: You can invite your friend's email address to completely join your Tailscale network via the Tailscale Admin Console.</p>

        <h3>Step 3: Verify the Connection</h3>
        <p>Before using TailChat, verify that your computers can securely talk to each other over Tailscale. Open your terminal or command prompt (CMD/PowerShell) and ping your friend's Tailscale IP (e.g., 100.100.100.100):</p>
        <p class="code-block">ping 100.x.y.z</p>
        <p>If you see replies, your secure tunnel is established!</p>

        <h3>Step 4: Host and Join</h3>
        <p>Once you are both connected to Tailscale and can ping each other:</p>
        <p>1. <b>User A</b> opens TailChat and clicks <span class="highlight">Host a Room</span> in the Lobby.</p>
        <p>2. TailChat securely registers the room's existence and User A's Tailscale IP onto the central database.</p>
        <p>3. <b>User B</b> opens TailChat, sees the room in the Lobby, and clicks <span class="highlight">Join</span>.</p>
        <p>4. User B's app fetches User A's Tailscale IP and establishes a direct socket connection. <b>You're now chatting P2P!</b></p>
        <p><i>Note: TailChat uses your Tailscale IP behind the scenes. This means even if you test the app using the same Gmail ID on multiple computers, TailChat will still safely treat you as separate users without conflicting!</i></p>
        """
        
        text_label = QLabel(html_content)
        text_label.setWordWrap(True)
        text_label.setTextFormat(Qt.RichText)
        text_label.setOpenExternalLinks(True)
        text_label.setStyleSheet("background: transparent;")
        
        c_lay.addWidget(text_label)
        c_lay.addStretch()
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll, stretch=1)
