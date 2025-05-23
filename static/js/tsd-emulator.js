/**
 * Модуль емулятора терміналу збору даних (TSD)
 * Відповідає за емуляцію інтерфейсу промислового терміналу на веб-сторінці
 * Дозволяє тестувати функціональність TSD без фізичного пристрою
 */

// Імпортуємо центральний диспетчер клавіш для обробки введення
import * as keyDispatcher from './tsd/keyDispatcher.js';

/**
 * Отримує CSRF токен з мета-тегу для захисту від CSRF атак
 * @returns {string} CSRF токен для використання в запитах
 */
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// Експортуємо функцію getCsrfToken у глобальний об'єкт window для використання в інших модулях
window.getCsrfToken = getCsrfToken;

/**
 * Ініціалізація емулятора при завантаженні сторінки
 * Налаштовує обробники подій та базовий стан інтерфейсу
 */
document.addEventListener('DOMContentLoaded', function() {
    // Змінні для відстеження поточного стану інтерфейсу
    let currentScreen = 'login-screen';  // Поточний активний екран
    let currentInput = 'login-input';    // Поточне активне поле введення
    let selectedMenuItem = 0;            // Індекс вибраного пункту меню
    let focusedInput = null;             // Елемент введення у фокусі
    
    // Отримуємо всі пункти меню для навігації
    const menuItems = document.querySelectorAll('.menu-item');
    
    /**
     * Відображає вказаний екран інтерфейсу та приховує всі інші
     * @param {string} screenId - Ідентифікатор екрану для відображення
     */
    window.showScreen = function(screenId) {
        // Hide all screens
        document.querySelectorAll('.screen-content').forEach(screen => {
            screen.classList.remove('active-screen');
        });
        
        // Show the specified screen
        const screen = document.getElementById(screenId);
        if (screen) {
            screen.classList.add('active-screen');
            currentScreen = screenId;
            
            // Set focus to the first input-value in the screen
            setTimeout(() => {
                const firstInput = screen.querySelector('.input-value');
                if (firstInput) {
                    setFocusedInput(firstInput);
                } else {
                    focusedInput = null;
                }
            }, 100);
            
            // Оновлюємо стан у диспетчері клавіш
            keyDispatcher.setTsdState({ currentScreen });
        }
    }
    
    // Запускаємо ініціалізацію емулятора
    initEmulator();
    
    /**
     * Ініціалізує емулятор терміналу збору даних
     * Налаштовує обробники подій для віртуальної клавіатури та елементів інтерфейсу
     */
    function initEmulator() {
        console.log('Ініціалізація TSD емулятора');
        
        // Додаємо обробники для віртуальної клавіатури
        document.querySelectorAll('.key').forEach(key => {
            key.addEventListener('click', async function() {
                const keyValue = this.getAttribute('data-key');
                // Використовуємо диспетчер клавіш для обробки натискань
                await keyDispatcher.handleKeyPress(keyValue);
            });
        });
        
        // Додаємо обробники кліків на елементи введення для фокусу
        document.querySelectorAll('.input-value').forEach(input => {
            input.addEventListener('click', function() {
                setFocusedInput(this);
            });
        });
        
        // Handle barcode scan
        const barcodeInput = document.getElementById('barcode-input');
        if (barcodeInput) {
            barcodeInput.addEventListener('keydown', function(event) {
                if (event.key === 'Enter') {
                    const barcode = this.value.trim();
                    if (barcode) {
                        // Отримуємо поточний стан з диспетчера клавіш
                        const state = keyDispatcher.getTsdState();
                        const currentScreen = state.currentScreen;
                        
                        // Передаємо сканування штрих-коду до відповідного обробника
                        if (currentScreen.includes('picking')) {
                            // Використовуємо обробник з модуля picking
                            if (typeof window.handlePickingBarcodeScan === 'function') {
                                window.handlePickingBarcodeScan(barcode, currentScreen);
                            }
                        } else if (currentScreen.includes('receiving')) {
                            // Використовуємо обробник з модуля receiving
                            if (typeof window.handleReceivingBarcodeScan === 'function') {
                                window.handleReceivingBarcodeScan(barcode, currentScreen);
                            }
                        } else if (currentScreen.includes('validation')) {
                            // Використовуємо обробник з модуля validation
                            if (typeof window.handleValidationBarcodeScan === 'function') {
                                window.handleValidationBarcodeScan(barcode, currentScreen);
                            }
                        } else {
                            // Використовуємо базовий обробник
                            window.processBarcode(barcode);
                        }
                        
                        this.value = ''; // Clear the input after scan
                    }
                }
            });
        }
        
        // Set initial screen
        showScreen('login-screen');
        
        // Ініціалізуємо стан TSD у диспетчері клавіш
        keyDispatcher.setTsdState({
            currentScreen,
            currentInput,
            selectedMenuItem,
            focusedInput
        });
        
        // Ініціалізуємо диспетчер клавіш
        keyDispatcher.initKeyDispatcher();
    }
    
    function setFocusedInput(inputElement) {
        // Remove focus from all input elements
        document.querySelectorAll('.input-value').forEach(input => {
            input.classList.remove('focused');
        });
        
        // Add focus to the clicked element
        if (inputElement) {
            inputElement.classList.add('focused');
            focusedInput = inputElement;
            currentInput = inputElement.id;
            
            // Оновлюємо стан у диспетчері клавіш
            keyDispatcher.setTsdState({ focusedInput, currentInput });
        }
    }
    
    // Експортуємо функцію для вибору пункту меню
    window.selectMenuItem = function(index) {
        // Remove selection from all items
        menuItems.forEach(item => item.classList.remove('selected'));
        
        // Add selection to the specified item
        if (index >= 0 && index < menuItems.length) {
            menuItems[index].classList.add('selected');
            selectedMenuItem = index;
            
            // Оновлюємо стан у диспетчері клавіш
            keyDispatcher.setTsdState({ selectedMenuItem });
        }
    }
    
    // Експортуємо функцію для очищення поля введення
    window.clearInput = function() {
        // Використовуємо функцію з диспетчера клавіш
        keyDispatcher.clearInput();
    }
    
    // Експортуємо функцію для обробки штрих-коду
    window.processBarcode = function(barcode) {
        // Використовуємо функцію з диспетчера клавіш
        keyDispatcher.processBarcode(barcode);
    }
    
    window.showMessage = function(message, type = 'info') {
        // Show a message in the current screen
        const messageElement = document.querySelector(`#${currentScreen} .screen-message`);
        if (messageElement) {
            messageElement.textContent = message;
            messageElement.className = 'screen-message';
            messageElement.classList.add(`message-${type}`);
            
            // Reset message after 3 seconds if it's an error or success
            if (type === 'error' || type === 'success') {
                setTimeout(() => {
                    if (currentScreen === 'login-screen') {
                        messageElement.textContent = 'Введіть код та натисніть F1';
                    } else if (currentScreen.includes('screen')) {
                        const defaultMessages = {
                            'menu-screen': 'Виберіть опцію (1-3) або використовуйте стрілки',
                            'receiving-screen': 'Відскануйте або введіть код та натисніть F1',
                            'picking-screen': 'Відскануйте або введіть код та натисніть F1',
                            'relocation-screen': 'Відскануйте або введіть код та натисніть F1'
                        };
                        messageElement.textContent = defaultMessages[currentScreen] || '';
                    }
                    messageElement.className = 'screen-message';
                }, 3000);
            }
        }
    }
    
    // Експортуємо функцію для навігації до опцій меню
    window.navigateToOption = function(option) {
        // Navigate to the selected menu option
        switch(option) {
            case 'receiving':
                // Start the receiving process
                document.dispatchEvent(new Event('receivingStart'));
                break;
            case 'picking':
                // Start the picking process
                document.dispatchEvent(new Event('pickingStart'));
                break;
            case 'relocation':
                window.showScreen('relocation-screen');
                currentInput = 'relocation-input';
                // Оновлюємо стан у диспетчері клавіш
                keyDispatcher.setTsdState({ currentInput });
                break;
        }
    }
    
    // Ініціалізуємо стан TSD у диспетчері клавіш
    keyDispatcher.setTsdState({
        currentScreen,
        currentInput,
        selectedMenuItem,
        focusedInput
    });
    
    // SSCC generation is now handled by the server

});