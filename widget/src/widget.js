(function () {
    window.CheckfunnelWidget = {
        isOpen: false,
        socket: null,

        init: function () {
            this.createUI();
            this.connectWebSocket();
        },

        createUI: function () {
            // Inject CSS
            const style = document.createElement('style');
            style.innerHTML = `
                #cf-chat-container { position: fixed; bottom: 30px; right: 30px; z-index: 999999; font-family: 'Inter', sans-serif; }
                #cf-chat-button { width: 65px; height: 65px; border-radius: 50%; background: linear-gradient(135deg, #007bff, #0056b3); color: white; border: none; cursor: pointer; box-shadow: 0 4px 15px rgba(0,123,255,0.4); font-size: 28px; transition: transform 0.3s ease; display: flex; align-items: center; justify-content: center;}
                #cf-chat-button:hover { transform: scale(1.1); }
                #cf-chat-window { display: none; width: 380px; height: 600px; background: #ffffff; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); flex-direction: column; overflow: hidden; margin-bottom: 20px; border: 1px solid #eaeaea; transition: all 0.3s ease; }
                #cf-chat-header { background: linear-gradient(135deg, #007bff, #0056b3); color: white; padding: 20px; font-weight: 600; font-size: 16px; display: flex; justify-content: space-between; align-items: center; }
                #cf-close-btn { background: rgba(255,255,255,0.2); border: none; color: white; cursor: pointer; font-size: 20px; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; transition: background 0.2s; }
                #cf-close-btn:hover { background: rgba(255,255,255,0.4); }
                #cf-chat-messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; background: #fcfcfc; scroll-behavior: smooth; }
                #cf-chat-input-area { display: flex; border-top: 1px solid #f0f0f0; padding: 15px; background: white; align-items: center; gap: 10px; }
                #cf-chat-input { flex: 1; padding: 12px 20px; border: 1px solid #e1e1e1; border-radius: 25px; outline: none; font-size: 14px; background: #f8f9fa; transition: border 0.2s; }
                #cf-chat-input:focus { border-color: #007bff; background: #fff; box-shadow: 0 0 0 3px rgba(0,123,255,0.1); }
                #cf-send-btn { background: #007bff; color: white; border: none; padding: 12px 20px; border-radius: 25px; cursor: pointer; font-weight: 500; font-size: 14px; transition: background 0.2s; }
                #cf-send-btn:hover { background: #0056b3; }
                .cf-msg { padding: 12px 18px; border-radius: 18px; max-width: 82%; word-wrap: break-word; font-size: 14px; line-height: 1.5; box-shadow: 0 2px 5px rgba(0,0,0,0.05); animation: fadeIn 0.3s ease; }
                @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
                .cf-msg-user { background: #007bff; color: white; align-self: flex-end; border-bottom-right-radius: 4px; }
                .cf-msg-ai { background: #ffffff; color: #333; align-self: flex-start; border-bottom-left-radius: 4px; border: 1px solid #efefef; }
                .cf-product-card { border: 1px solid #eaeaea; border-radius: 12px; padding: 15px; margin-top: 5px; background: white; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
                .cf-product-card img { max-width: 100%; border-radius: 8px; margin-bottom: 10px; }
                .cf-product-card h4 { margin: 0 0 8px 0; color: #333; font-size: 16px; }
                .cf-product-card p { margin: 0 0 15px 0; color: #666; font-size: 13px; line-height: 1.4; }
                .cf-product-card button { background: #28a745; color: white; border: none; padding: 10px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: 600; font-size: 14px; transition: background 0.2s; }
                .cf-product-card button:hover { background: #218838; }
            `;
            document.head.appendChild(style);

            // HTML
            const container = document.createElement('div');
            container.id = 'cf-chat-container';
            container.innerHTML = `
                <div id="cf-chat-window">
                    <div id="cf-chat-header">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div style="width: 10px; height: 10px; background: #28a745; border-radius: 50%; box-shadow: 0 0 5px #28a745;"></div>
                            Checkfunnel Expert
                        </div>
                        <button id="cf-close-btn">&times;</button>
                    </div>
                    <div id="cf-chat-messages">
                        <div class="cf-msg cf-msg-ai">Hi! I'm your Checkfunnel AI Expert. How can I help you today?</div>
                    </div>
                    <div id="cf-chat-input-area">
                        <input type="text" id="cf-chat-input" placeholder="Type your message..." autocomplete="off" />
                        <button id="cf-send-btn">Send</button>
                    </div>
                </div>
                <button id="cf-chat-button">💬</button>
            `;
            document.body.appendChild(container);

            // Events
            document.getElementById('cf-chat-button').addEventListener('click', () => this.toggleWindow());
            document.getElementById('cf-close-btn').addEventListener('click', () => this.toggleWindow());
            document.getElementById('cf-send-btn').addEventListener('click', () => this.sendMessage());
            document.getElementById('cf-chat-input').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.sendMessage();
            });
        },

        toggleWindow: function () {
            const win = document.getElementById('cf-chat-window');
            this.isOpen = !this.isOpen;
            win.style.display = this.isOpen ? 'flex' : 'none';
        },

        connectWebSocket: function () {
            setTimeout(() => {
                const sessionId = window.CheckfunnelTracker ? window.CheckfunnelTracker.sessionId : crypto.randomUUID();
                const host = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' ? '127.0.0.1:8000' : window.location.host;
                this.socket = new WebSocket(`ws://${host}/ws/chat/${sessionId}/`);

                this.socket.onmessage = (e) => {
                    const data = JSON.parse(e.data);
                    if (data.type === 'ai_message') {
                        this.appendMessage(data.message, 'ai');
                        if (data.suggested_product_id) {
                            this.appendProductCard(data.suggested_product_id);
                        }
                    }
                };
            }, 1000); // delay slight to ensure tracker loads session ID
        },

        sendMessage: function () {
            const input = document.getElementById('cf-chat-input');
            const msg = input.value.trim();
            if (!msg) return;

            this.appendMessage(msg, 'user');
            input.value = '';

            const behaviorMatrix = window.CheckfunnelTracker ? window.CheckfunnelTracker.behaviorMatrix : {};

            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(JSON.stringify({
                    message: msg,
                    behavior_matrix: behaviorMatrix
                }));
            } else {
                this.appendMessage("Reconnecting to the server...", "ai");
                this.connectWebSocket();
            }
        },

        appendMessage: function (text, sender) {
            if (!text) return;
            const msgs = document.getElementById('cf-chat-messages');
            const div = document.createElement('div');
            div.className = `cf-msg cf-msg-${sender}`;
            div.innerText = text;
            msgs.appendChild(div);
            msgs.scrollTop = msgs.scrollHeight;
        },

        appendProductCard: function (productId) {
            const msgs = document.getElementById('cf-chat-messages');
            const card = document.createElement('div');
            card.className = 'cf-product-card';
            card.innerHTML = `
                <img src="https://via.placeholder.com/300x150?text=Product+Image" alt="Product Image">
                <h4>Recommended Product Special</h4>
                <p>Based on your intent, we think you'll love this offer. Limited time pricing applies.</p>
                <button onclick="alert('Proceeding to Checkout!')">Add to Cart - $199</button>
            `;
            msgs.appendChild(card);
            msgs.scrollTop = msgs.scrollHeight;
        },

        triggerNudge: function () {
            if (!this.isOpen) {
                this.toggleWindow();
                let nudgeMsg = "Hello! I noticed you are exploring our site. Would you like a quick overview or have any questions I can answer right away?";
                this.appendMessage(nudgeMsg, 'ai');
            }
        }
    };

    // Ensure dom is ready
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        window.CheckfunnelWidget.init();
    } else {
        document.addEventListener('DOMContentLoaded', () => window.CheckfunnelWidget.init());
    }
})();
