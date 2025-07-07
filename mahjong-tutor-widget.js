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
            this.isMinimized = false;
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
                <!-- Floating Button (only visible when chat is closed) -->
                <div class="mahjong-tutor-button" id="mahjong-tutor-button">
                    <div class="mahjong-tutor-icon">🀄</div>
                    <div class="mahjong-tutor-text">Mahjong Tutor</div>
                </div>

                <!-- Chat Widget -->
                <div class="mahjong-tutor-chat" id="mahjong-tutor-chat">
                    <div class="mahjong-tutor-header" id="mahjong-tutor-header">
                        <div class="mahjong-tutor-title">
                            <span class="mahjong-tutor-icon">🀄</span>
                            Mahjong Tutor
                        </div>
                        <div class="mahjong-tutor-controls">
                            <button class="mahjong-tutor-minimize" id="mahjong-tutor-minimize">−</button>
                            <button class="mahjong-tutor-close" id="mahjong-tutor-close">×</button>
                        </div>
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
                /* Reset and base styles */
                * {
                    box-sizing: border-box;
                }

                /* Floating Button - Bottom Right Corner */
                .mahjong-tutor-button {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    background: #d32f2f;
                    color: white;
                    border-radius: 50px;
                    padding: 12px 20px;
                    cursor: pointer;
                    box-shadow: 0 6px 20px rgba(0,0,0,0.3);
                    z-index: 9999;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                    font-size: 14px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    border: none;
                    user-select: none;
                }

                .mahjong-tutor-button:hover {
                    background: #b71c1c;
                    transform: translateY(-2px);
                    box-shadow: 0 8px 25px rgba(0,0,0,0.4);
                }

                .mahjong-tutor-button.hidden {
                    opacity: 0;
                    pointer-events: none;
                    transform: scale(0.8);
                }

                .mahjong-tutor-icon {
                    font-size: 20px;
                }

                /* Chat Widget - Mobile App Style */
                .mahjong-tutor-chat {
                    position: fixed;
                    background: white;
                    z-index: 10000;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                    display: none;
                    flex-direction: column;
                    overflow: hidden;
                    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                    
                    /* Desktop: 1/3 of screen, right side */
                    right: 0;
                    top: 0;
                    width: 33.33vw;
                    height: 100vh;
                    min-width: 400px;
                    border-radius: 0;
                    box-shadow: -4px 0 20px rgba(0,0,0,0.3);
                }

                .mahjong-tutor-chat.open {
                    display: flex;
                    animation: slideInFromRight 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                }

                .mahjong-tutor-chat.minimized {
                    height: 60px;
                    animation: minimizeChat 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                }

                @keyframes slideInFromRight {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }

                @keyframes minimizeChat {
                    from {
                        height: 100vh;
                    }
                    to {
                        height: 60px;
                    }
                }

                /* Header */
                .mahjong-tutor-header {
                    background: #d32f2f;
                    color: white;
                    padding: 15px 20px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-shrink: 0;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    cursor: pointer;
                    user-select: none;
                }

                .mahjong-tutor-header:hover {
                    background: #c62d2d;
                }

                .mahjong-tutor-chat:not(.minimized) .mahjong-tutor-header {
                    cursor: default;
                }

                .mahjong-tutor-chat:not(.minimized) .mahjong-tutor-header:hover {
                    background: #d32f2f;
                }

                .mahjong-tutor-title {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    font-weight: 600;
                    font-size: 16px;
                }

                .mahjong-tutor-controls {
                    display: flex;
                    gap: 10px;
                }

                .mahjong-tutor-minimize,
                .mahjong-tutor-close {
                    background: rgba(255,255,255,0.2);
                    border: none;
                    color: white;
                    font-size: 18px;
                    cursor: pointer;
                    padding: 8px;
                    width: 36px;
                    height: 36px;
                    border-radius: 6px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: background-color 0.2s ease;
                }

                .mahjong-tutor-minimize:hover,
                .mahjong-tutor-close:hover {
                    background: rgba(255,255,255,0.3);
                }

                /* Messages Area */
                .mahjong-tutor-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 20px;
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                    background: #f8f9fa;
                    scroll-behavior: smooth;
                }

                .mahjong-tutor-chat.minimized .mahjong-tutor-messages {
                    display: none;
                }

                .mahjong-tutor-message {
                    display: flex;
                    gap: 12px;
                    align-items: flex-start;
                    animation: messageSlideIn 0.3s ease-out;
                }

                .mahjong-tutor-message.mahjong-tutor-user {
                    flex-direction: row-reverse;
                }

                @keyframes messageSlideIn {
                    from {
                        opacity: 0;
                        transform: translateY(10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                .mahjong-tutor-avatar {
                    width: 36px;
                    height: 36px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 18px;
                    flex-shrink: 0;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }

                .mahjong-tutor-bot .mahjong-tutor-avatar {
                    background: linear-gradient(135deg, #f5f5f5, #e8e8e8);
                }

                .mahjong-tutor-user .mahjong-tutor-avatar {
                    background: linear-gradient(135deg, #d32f2f, #b71c1c);
                    color: white;
                }

                .mahjong-tutor-content {
                    flex: 1;
                    max-width: calc(100% - 60px);
                }

                .mahjong-tutor-text {
                    background: white;
                    padding: 12px 16px;
                    border-radius: 18px;
                    font-size: 14px;
                    line-height: 1.4;
                    word-wrap: break-word;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    border: 1px solid #e0e0e0;
                }

                .mahjong-tutor-user .mahjong-tutor-text {
                    background: #d32f2f;
                    color: white;
                    border: none;
                }

                .mahjong-tutor-image {
                    max-width: 100%;
                    border-radius: 12px;
                    margin-top: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }

                /* Input Area */
                .mahjong-tutor-input-area {
                    border-top: 1px solid #e0e0e0;
                    padding: 20px;
                    background: white;
                    flex-shrink: 0;
                }

                .mahjong-tutor-chat.minimized .mahjong-tutor-input-area {
                    display: none;
                }

                .mahjong-tutor-image-preview {
                    margin-bottom: 12px;
                    position: relative;
                }

                .mahjong-tutor-image-preview img {
                    max-width: 100%;
                    max-height: 120px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }

                .mahjong-tutor-image-preview .remove-image {
                    position: absolute;
                    top: -8px;
                    right: -8px;
                    background: #d32f2f;
                    color: white;
                    border: none;
                    border-radius: 50%;
                    width: 24px;
                    height: 24px;
                    cursor: pointer;
                    font-size: 14px;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.2);
                }

                .mahjong-tutor-input-container {
                    display: flex;
                    gap: 12px;
                    align-items: center;
                    background: #f8f9fa;
                    border-radius: 24px;
                    padding: 8px;
                }

                .mahjong-tutor-image-btn {
                    background: white;
                    border: 1px solid #e0e0e0;
                    padding: 10px;
                    border-radius: 20px;
                    cursor: pointer;
                    font-size: 18px;
                    transition: all 0.2s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 40px;
                    height: 40px;
                }

                .mahjong-tutor-image-btn:hover {
                    background: #f0f0f0;
                    transform: scale(1.05);
                }

                .mahjong-tutor-input {
                    flex: 1;
                    border: none;
                    background: transparent;
                    padding: 12px 16px;
                    font-size: 14px;
                    outline: none;
                    color: #333;
                }

                .mahjong-tutor-input::placeholder {
                    color: #999;
                }

                .mahjong-tutor-send {
                    background: #d32f2f;
                    color: white;
                    border: none;
                    padding: 10px 16px;
                    border-radius: 20px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 600;
                    transition: all 0.2s ease;
                    min-width: 60px;
                }

                .mahjong-tutor-send:hover:not(:disabled) {
                    background: #b71c1c;
                    transform: scale(1.05);
                }

                .mahjong-tutor-send:disabled {
                    background: #ccc;
                    cursor: not-allowed;
                    transform: none;
                }

                /* Loading Overlay */
                .mahjong-tutor-loading {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(255,255,255,0.95);
                    display: none;
                    align-items: center;
                    justify-content: center;
                    flex-direction: column;
                    gap: 16px;
                }

                .mahjong-tutor-loading.show {
                    display: flex;
                }

                .mahjong-tutor-spinner {
                    width: 40px;
                    height: 40px;
                    border: 3px solid #f3f3f3;
                    border-top: 3px solid #d32f2f;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }

                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }

                /* Mobile Responsiveness */
                @media (max-width: 768px) {
                    .mahjong-tutor-chat {
                        /* Mobile: Full screen */
                        width: 100vw !important;
                        height: 100vh !important;
                        min-width: unset !important;
                        right: 0 !important;
                        top: 0 !important;
                        border-radius: 0 !important;
                        box-shadow: none !important;
                    }

                    .mahjong-tutor-chat.minimized {
                        height: 60px !important;
                        width: 100vw !important;
                        top: auto !important;
                        bottom: 0 !important;
                    }

                    .mahjong-tutor-button {
                        bottom: 80px;
                    }

                    .mahjong-tutor-messages {
                        padding: 16px;
                    }

                    .mahjong-tutor-input-area {
                        padding: 16px;
                    }
                }

                /* Tablet Adjustments */
                @media (min-width: 769px) and (max-width: 1024px) {
                    .mahjong-tutor-chat {
                        width: 40vw !important;
                        min-width: 380px !important;
                    }
                }

                /* Large Desktop Adjustments */
                @media (min-width: 1400px) {
                    .mahjong-tutor-chat {
                        width: 28vw !important;
                        min-width: 420px !important;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        attachEventListeners() {
            const button = document.getElementById('mahjong-tutor-button');
            const chat = document.getElementById('mahjong-tutor-chat');
            const closeBtn = document.getElementById('mahjong-tutor-close');
            const minimizeBtn = document.getElementById('mahjong-tutor-minimize');
            const input = document.getElementById('mahjong-tutor-input');
            const sendBtn = document.getElementById('mahjong-tutor-send');
            const imageBtn = document.getElementById('mahjong-tutor-image-btn');
            const imageInput = document.getElementById('mahjong-tutor-image-input');

            button.addEventListener('click', () => this.openChat());
            closeBtn.addEventListener('click', () => this.closeChat());
            minimizeBtn.addEventListener('click', () => this.toggleMinimize());
            
            // Click header to maximize when minimized (but not on buttons)
            const header = document.getElementById('mahjong-tutor-header');
            if (header) {
                header.addEventListener('click', (e) => {
                    // Don't trigger if clicking on buttons
                    if (e.target.closest('.mahjong-tutor-minimize') || 
                        e.target.closest('.mahjong-tutor-close')) {
                        return;
                    }
                    
                    if (this.isMinimized) {
                        this.toggleMinimize();
                    }
                });
            }

            sendBtn.addEventListener('click', () => this.sendMessage());
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.sendMessage();
            });
            imageBtn.addEventListener('click', () => imageInput.click());
            imageInput.addEventListener('change', (e) => this.handleImageUpload(e));
        }

        openChat() {
            const button = document.getElementById('mahjong-tutor-button');
            const chat = document.getElementById('mahjong-tutor-chat');
            
            this.isOpen = true;
            this.isMinimized = false;
            
            // Hide floating button and show chat
            button.classList.add('hidden');
            chat.classList.add('open');
            chat.classList.remove('minimized');
            
            // Focus input after animation
            setTimeout(() => {
                const input = document.getElementById('mahjong-tutor-input');
                if (input) input.focus();
            }, 100);
        }

        closeChat() {
            const button = document.getElementById('mahjong-tutor-button');
            const chat = document.getElementById('mahjong-tutor-chat');
            
            this.isOpen = false;
            this.isMinimized = false;
            
            // Hide chat and show floating button
            chat.classList.remove('open', 'minimized');
            button.classList.remove('hidden');
        }

        toggleMinimize() {
            const chat = document.getElementById('mahjong-tutor-chat');
            const minimizeBtn = document.getElementById('mahjong-tutor-minimize');
            
            this.isMinimized = !this.isMinimized;
            
            if (this.isMinimized) {
                chat.classList.add('minimized');
                minimizeBtn.innerHTML = '▢'; // Maximize icon
            } else {
                chat.classList.remove('minimized');
                minimizeBtn.innerHTML = '−'; // Minimize icon
                
                // Focus input when maximizing
                setTimeout(() => {
                    const input = document.getElementById('mahjong-tutor-input');
                    if (input) input.focus();
                }, 100);
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