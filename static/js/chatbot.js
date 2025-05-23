/**
 * Модуль для обробки взаємодій з чатботом
 * Відповідає за відображення інтерфейсу чату, обробку повідомлень та комунікацію з API
 */

class ChatbotUI {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.userInput = document.getElementById('userInput');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.exampleQueries = document.querySelectorAll('.example-query');
        
        this.initEventListeners();
    }
    
    /**
     * Ініціалізація обробників подій для елементів інтерфейсу чатбота
     * Налаштовує обробку кліків, натискання клавіш та взаємодії з прикладами запитів
     */
    initEventListeners() {
        // Обробник події для кнопки відправки повідомлення
        this.sendButton.addEventListener('click', () => this.handleSendMessage());
        
        // Обробник події для відправки повідомлення при натисканні клавіші Enter
        this.userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleSendMessage();
            }
        });
        
        // Обробник події для швидкого вибору прикладів запитів
        this.exampleQueries.forEach(example => {
            example.addEventListener('click', () => {
                const query = example.getAttribute('data-query');
                this.userInput.value = query;
                this.userInput.focus();
            });
        });
    }
    
    handleSendMessage() {
        const query = this.userInput.value.trim();
        if (query) {
            this.addMessage(query, true);
            this.sendToChatbot(query);
            this.userInput.value = '';
        }
    }
    
    /**
     * Додає нове повідомлення до інтерфейсу чату
     * @param {string} content - Текст повідомлення
     * @param {boolean} isUser - Прапорець, що вказує, чи є повідомлення від користувача (true) або від бота (false)
     */
    addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        // Перевіряємо, чи містить повідомлення HTML-теги
        if (content.includes('<') && content.includes('>') && !isUser) {
            messageContent.innerHTML = content;
        } else {
            messageContent.textContent = content;
        }
        
        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        const now = new Date();
        messageTime.textContent = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
        
        messageDiv.appendChild(messageContent);
        messageDiv.appendChild(messageTime);
        
        // Вставляємо повідомлення перед індикатором набору
        this.chatMessages.insertBefore(messageDiv, this.typingIndicator);
        
        // Прокручуємо чат до останнього повідомлення
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    /**
     * Відправляє запит користувача до API чатбота та обробляє відповідь
     * @param {string} query - Текст запиту користувача
     * @returns {Promise<void>}
     */
    async sendToChatbot(query) {
        try {
            // Показуємо індикатор набору
            this.typingIndicator.style.display = 'block';
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
            
            // Відправляємо запит до API
            const response = await fetch('/wms/api/chatbot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify({ query: query })
            });
            
            const data = await response.json();
            
            // Ховаємо індикатор набору
            this.typingIndicator.style.display = 'none';
            
            // Додаємо відповідь від чатбота
            this.addMessage(data.response, false);
        } catch (error) {
            console.error('Помилка при відправці запиту:', error);
            this.typingIndicator.style.display = 'none';
            this.addMessage('Виникла помилка при обробці вашого запиту. Спробуйте ще раз пізніше.', false);
        }
    }
}

// Ініціалізація чатбота при завантаженні сторінки
document.addEventListener('DOMContentLoaded', function() {
    const chatbot = new ChatbotUI();
});