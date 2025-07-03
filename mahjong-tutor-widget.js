/**
 * Mahjong Tutor Widget
 * A JavaScript widget that can be embedded in any website
 * to provide Mahjong tutoring functionality
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        apiUrl: 'https://your-api-domain.com/api',  // Replace with your API URL
        widgetId: 'mahjong-tutor-widget',
        maxMessageLength: 1000,
        imageMaxSize: 5 * 1024 * 1024  // 5MB
    };

    // Widget class
    class MahjongTutorWidget {
        constructor(options = {}) {
            this.config = { ...CONFIG, ...options };
            this.isOpen = false;
            this.isLoading = false;
            this.conversationHistory = [];
            
            this.init();
        }

        init() {
            this.createWidget();
            this.attachEventListeners();
            this.loadConversationHistory();
        }

        createWidget() {
            // Create widget container
            const widget = document.createElement('div');
            widget.id = this.config.widgetId;
            widget.innerHTML = this.getWidgetHTML();
            document.body.appendChild(widget);

            // Add styles
            this.addStyles();
        }

        getWidgetHTML() {
            return `
                <!-- Floating Button -->
                <div class="mahjong-tutor-button" id="mahjong-tutor-button">
                    <div class="mahjong-tutor-icon">🀄</div>
                    <div class="mahjong-tutor-text">Mahjong Tutor</div>
                </div>

                <!-- Chat Widget -->
                <div class="mahjong-tutor-chat" id="mahjong-tutor-chat">
                    <div class="mahjong-tutor-header">
                        <div class="mahjong-tutor-title">
                            <span class="mahjong-tutor-icon">🀄</span>
                            Mahjong Tutor
                        </div>
                        <button class="mahjong-tutor-close" id="mahjong-tutor-close">×</button>
                    </div>
                    
                    <div class="mahjong-tutor-messages" id="mahjong-tutor-messages">
                        <div class="mahjong-tutor-message mahjong-tutor-bot">
                            <div class="mahjong-tutor-avatar">🀄</div>
                            <div class="mahjong-tutor-content">
                                <div class="mahjong-tutor-text">
                                    Welcome! I'm your Mahjong tutor. Ask me about strategy, rules, or upload an image of your tiles for analysis.
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="mahjong-tutor-input-area">
                        <div class="mahjong-tutor-image-preview" id="mahjong-tutor-image-preview"></div>
                        <div class="mahjong-tutor-input-container">
                            <input type="file" id="mahjong-tutor-image-input" accept="image/*" style="display: none;">
                            <button class="mahjong-tutor-image-btn" id="mahjong-tutor-image-btn">📷</button>
                            <input type="text" id="mahjong-tutor-input" placeholder="Ask about Mahjong strategy..." maxlength="${this.config.maxMessageLength}">
                            <button class="mahjong-tutor-send" id="mahjong-tutor-send">Send</button>
                        </div>
                    </div>

                    <div class="mahjong-tutor-loading" id="mahjong-tutor-loading">
                        <div class="mahjong-tutor-spinner"></div>
                        <div>Thinking...</div>
                    </div>
                </div>
            `;
        }

        addStyles() {
            const style = document.createElement('style');
            style.textContent = `
                /* Widget Styles */
                .mahjong-tutor-button {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    background: #d32f2f;
                    color: white;
                    border-radius: 50px;
                    padding: 12px 20px;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                    z-index: 9999;
                    font-family: Arial, sans-serif;
                    font-size: 14px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    transition: all 0.3s ease;
                }

                .mahjong-tutor-button:hover {
                    background: #b71c1c;
                    transform: translateY(-2px);
                }

                .mahjong-tutor-icon {
                    font-size: 18px;
                }

                .mahjong-tutor-chat {
                    position: fixed;
                    bottom: 80px;
                    right: 20px;
                    width: 350px;
                    height: 500px;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.3);
                    z-index: 10000;
                    font-family: Arial, sans-serif;
                    display: none;
                    flex-direction: column;
                    overflow: hidden;
                }

                .mahjong-tutor-chat.open {
                    display: flex;
                }

                .mahjong-tutor-header {
                    background: #d32f2f;
                    color: white;
                    padding: 15px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .mahjong-tutor-title {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-weight: bold;
                }

                .mahjong-tutor-close {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 20px;
                    cursor: pointer;
                    padding: 0;
                    width: 24px;
                    height: 24px;
                }

                .mahjong-tutor-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 15px;
                    display: flex;
                    flex-direction: column;
                    gap: 15px;
                }

                .mahjong-tutor-message {
                    display: flex;
                    gap: 10px;
                    align-items: flex-start;
                }

                .mahjong-tutor-message.mahjong-tutor-user {
                    flex-direction: row-reverse;
                }

                .mahjong-tutor-avatar {
                    width: 32px;
                    height: 32px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 16px;
                    flex-shrink: 0;
                }

                .mahjong-tutor-bot .mahjong-tutor-avatar {
                    background: #f5f5f5;
                }

                .mahjong-tutor-user .mahjong-tutor-avatar {
                    background: #d32f2f;
                    color: white;
                }

                .mahjong-tutor-content {
                    flex: 1;
                    max-width: 250px;
                }

                .mahjong-tutor-text {
                    background: #f5f5f5;
                    padding: 10px 12px;
                    border-radius: 15px;
                    font-size: 14px;
                    line-height: 1.4;
                    word-wrap: break-word;
                }

                .mahjong-tutor-user .mahjong-tutor-text {
                    background: #d32f2f;
                    color: white;
                }

                .mahjong-tutor-image {
                    max-width: 100%;
                    border-radius: 10px;
                    margin-top: 5px;
                }

                .mahjong-tutor-input-area {
                    border-top: 1px solid #eee;
                    padding: 15px;
                }

                .mahjong-tutor-image-preview {
                    margin-bottom: 10px;
                    position: relative;
                }

                .mahjong-tutor-image-preview img {
                    max-width: 100%;
                    max-height: 100px;
                    border-radius: 5px;
                }

                .mahjong-tutor-image-preview .remove-image {
                    position: absolute;
                    top: -5px;
                    right: -5px;
                    background: #d32f2f;
                    color: white;
                    border: none;
                    border-radius: 50%;
                    width: 20px;
                    height: 20px;
                    cursor: pointer;
                    font-size: 12px;
                }

                .mahjong-tutor-input-container {
                    display: flex;
                    gap: 10px;
                    align-items: center;
                }

                .mahjong-tutor-image-btn {
                    background: #f5f5f5;
                    border: none;
                    padding: 8px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                }

                .mahjong-tutor-input {
                    flex: 1;
                    border: 1px solid #ddd;
                    border-radius: 20px;
                    padding: 10px 15px;
                    font-size: 14px;
                    outline: none;
                }

                .mahjong-tutor-send {
                    background: #d32f2f;
                    color: white;
                    border: none;
                    padding: 10px 15px;
                    border-radius: 20px;
                    cursor: pointer;
                    font-size: 14px;
                }

                .mahjong-tutor-send:disabled {
                    background: #ccc;
                    cursor: not-allowed;
                }

                .mahjong-tutor-loading {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(255,255,255,0.9);
                    display: none;
                    align-items: center;
                    justify-content: center;
                    flex-direction: column;
                    gap: 10px;
                }

                .mahjong-tutor-loading.show {
                    display: flex;
                }

                .mahjong-tutor-spinner {
                    width: 30px;
                    height: 30px;
                    border: 3px solid #f3f3f3;
                    border-top: 3px solid #d32f2f;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }

                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }

                /* Mobile responsiveness */
                @media (max-width: 480px) {
                    .mahjong-tutor-chat {
                        width: calc(100vw - 40px);
                        height: 80vh;
                        bottom: 10px;
                        right: 20px;
                        left: 20px;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        attachEventListeners() {
            const button = document.getElementById('mahjong-tutor-button');
            const chat = document.getElementById('mahjong-tutor-chat');
            const closeBtn = document.getElementById('mahjong-tutor-close');
            const input = document.getElementById('mahjong-tutor-input');
            const sendBtn = document.getElementById('mahjong-tutor-send');
            const imageBtn = document.getElementById('mahjong-tutor-image-btn');
            const imageInput = document.getElementById('mahjong-tutor-image-input');

            button.addEventListener('click', () => this.toggleChat());
            closeBtn.addEventListener('click', () => this.toggleChat());
            sendBtn.addEventListener('click', () => this.sendMessage());
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.sendMessage();
            });
            imageBtn.addEventListener('click', () => imageInput.click());
            imageInput.addEventListener('change', (e) => this.handleImageUpload(e));
        }

        toggleChat() {
            const chat = document.getElementById('mahjong-tutor-chat');
            this.isOpen = !this.isOpen;
            
            if (this.isOpen) {
                chat.classList.add('open');
                document.getElementById('mahjong-tutor-input').focus();
            } else {
                chat.classList.remove('open');
            }
        }

        async sendMessage() {
            const input = document.getElementById('mahjong-tutor-input');
            const message = input.value.trim();
            
            if (!message && !this.selectedImage) return;
            
            // Add user message
            this.addMessage(message, 'user', this.selectedImage);
            
            // Clear input
            input.value = '';
            this.clearImagePreview();
            
            // Show loading
            this.setLoading(true);
            
            try {
                // Send to API
                const response = await this.callAPI(message, this.selectedImage);
                
                // Add bot response
                this.addMessage(response.response, 'bot');
                
                // Save conversation
                this.saveConversation();
                
            } catch (error) {
                console.error('Chat error:', error);
                this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
            } finally {
                this.setLoading(false);
                this.selectedImage = null;
            }
        }

        async callAPI(message, imageData) {
            const response = await fetch(`${this.config.apiUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    image: imageData
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'API request failed');
            }

            return response.json();
        }

        addMessage(text, type, imageData = null) {
            const messages = document.getElementById('mahjong-tutor-messages');
            const messageEl = document.createElement('div');
            messageEl.className = `mahjong-tutor-message mahjong-tutor-${type}`;
            
            const avatar = type === 'user' ? '👤' : '🀄';
            
            let imageHtml = '';
            if (imageData) {
                imageHtml = `<img src="data:image/jpeg;base64,${imageData}" class="mahjong-tutor-image" alt="Uploaded image">`;
            }
            
            messageEl.innerHTML = `
                <div class="mahjong-tutor-avatar">${avatar}</div>
                <div class="mahjong-tutor-content">
                    <div class="mahjong-tutor-text">${text}</div>
                    ${imageHtml}
                </div>
            `;
            
            messages.appendChild(messageEl);
            messages.scrollTop = messages.scrollHeight;
            
            // Store in conversation history
            this.conversationHistory.push({
                text: text,
                type: type,
                image: imageData,
                timestamp: new Date().toISOString()
            });
        }

        handleImageUpload(event) {
            const file = event.target.files[0];
            if (!file) return;

            // Check file size
            if (file.size > this.config.imageMaxSize) {
                alert('Image too large. Please choose an image under 5MB.');
                return;
            }

            // Check file type
            if (!file.type.startsWith('image/')) {
                alert('Please select an image file.');
                return;
            }

            // Convert to base64
            const reader = new FileReader();
            reader.onload = (e) => {
                const base64 = e.target.result.split(',')[1];
                this.selectedImage = base64;
                this.showImagePreview(e.target.result);
            };
            reader.readAsDataURL(file);
        }

        showImagePreview(src) {
            const preview = document.getElementById('mahjong-tutor-image-preview');
            preview.innerHTML = `
                <img src="${src}" alt="Image preview">
                <button class="remove-image" onclick="mahjongTutorWidget.clearImagePreview()">×</button>
            `;
        }

        clearImagePreview() {
            const preview = document.getElementById('mahjong-tutor-image-preview');
            preview.innerHTML = '';
            this.selectedImage = null;
        }

        setLoading(loading) {
            const loadingEl = document.getElementById('mahjong-tutor-loading');
            const sendBtn = document.getElementById('mahjong-tutor-send');
            
            this.isLoading = loading;
            
            if (loading) {
                loadingEl.classList.add('show');
                sendBtn.disabled = true;
            } else {
                loadingEl.classList.remove('show');
                sendBtn.disabled = false;
            }
        }

        saveConversation() {
            try {
                localStorage.setItem('mahjong-tutor-conversation', JSON.stringify(this.conversationHistory));
            } catch (e) {
                console.warn('Could not save conversation to localStorage');
            }
        }

        loadConversationHistory() {
            try {
                const saved = localStorage.getItem('mahjong-tutor-conversation');
                if (saved) {
                    this.conversationHistory = JSON.parse(saved);
                    // Don't restore old messages to keep widget clean
                }
            } catch (e) {
                console.warn('Could not load conversation from localStorage');
            }
        }
    }

    // Initialize widget when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.mahjongTutorWidget = new MahjongTutorWidget();
        });
    } else {
        window.mahjongTutorWidget = new MahjongTutorWidget();
    }

})();