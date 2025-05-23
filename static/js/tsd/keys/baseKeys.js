// Базовий модуль для обробки клавіш TSD

// Функція для отримання CSRF токену
function getCsrfToken() {
    // Спочатку перевіряємо, чи є глобальна функція getCsrfToken
    if (typeof window.getCsrfToken === 'function') {
        return window.getCsrfToken();
    }
    // Якщо глобальної функції немає, використовуємо резервний варіант
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    return csrfMeta ? csrfMeta.getAttribute('content') : '';
}

// Обробник клавіші Enter
export function handleEnter(currentScreen, currentInput, focusedInput) {
    // Базова логіка для клавіші Enter
    if (currentScreen === 'login-screen') {
        const loginCode = document.getElementById('login-input').textContent;
        if (loginCode.length > 0) {
            // Відправляємо запит на логін
            return { action: 'login', username: loginCode };
        }
        return false;
    } else if (currentScreen === 'menu-screen') {
        // Логіка для меню буде реалізована в окремих модулях
        return true;
    } else {
        // Загальна логіка для інших екранів
        const inputElement = focusedInput || document.getElementById(currentInput);
        if (inputElement && inputElement.textContent.length > 0) {
            return true;
        }
        return false;
    }
}

// Обробник клавіші F1 (часто використовується як підтвердження)
export function handleF1(currentScreen) {
    // F1 часто діє як Enter/підтвердження
    return handleEnter(currentScreen);
}

// Обробник клавіші F2 (часто використовується для повернення в меню)
export function handleF2(currentScreen) {
    if (currentScreen !== 'login-screen' && currentScreen !== 'menu-screen') {
        // F2 повертає до меню з операційних екранів
        return true;
    }
    return false;
}

// Обробник клавіші F3
export function handleF3(currentScreen) {
    // Базова логіка для F3
    return false;
}

// Обробник клавіші F4
export function handleF4(currentScreen) {
    // Базова логіка для F4
    return false;
}

// Обробник клавіші F5
export function handleF5(currentScreen) {
    // Базова логіка для F5
    return false;
}

// Обробник клавіші F6
export function handleF6(currentScreen) {
    // Базова логіка для F6
    return false;
}

// Обробник стрілок
export function handleArrow(key, currentScreen, selectedMenuItem, menuItems, focusedInput) {
    if (currentScreen === 'menu-screen') {
        // Навігація по пунктах меню
        if (key === 'ArrowUp' && selectedMenuItem > 0) {
            return { newMenuItem: selectedMenuItem - 1 };
        } else if (key === 'ArrowDown' && selectedMenuItem < menuItems.length - 1) {
            return { newMenuItem: selectedMenuItem + 1 };
        }
    } else {
        // Навігація між полями введення на поточному екрані
        const currentScreenElement = document.getElementById(currentScreen);
        if (currentScreenElement) {
            const inputFields = Array.from(currentScreenElement.querySelectorAll('.input-value'));
            if (inputFields.length > 1 && focusedInput) {
                const currentIndex = inputFields.indexOf(focusedInput);
                if (currentIndex !== -1) {
                    let newIndex = currentIndex;
                    
                    if (key === 'ArrowUp' && currentIndex > 0) {
                        newIndex = currentIndex - 1;
                    } else if (key === 'ArrowDown' && currentIndex < inputFields.length - 1) {
                        newIndex = currentIndex + 1;
                    }
                    
                    if (newIndex !== currentIndex) {
                        return { newFocusedInput: inputFields[newIndex] };
                    }
                }
            }
        }
    }
    return null;
}

// Обробник клавіші Clear (Escape, Delete, Backspace)
export function handleClear(currentInput, focusedInput) {
    const inputElement = focusedInput || document.getElementById(currentInput);
    if (inputElement) {
        return true;
    }
    return false;
}

// Допоміжна функція для логіну користувача
export async function loginUser(loginCode) {
    try {
        const response = await fetch('/tsd-emulator/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ username: loginCode })
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error:', error);
        return { success: false, message: "Помилка з'єднання з сервером" };
    }
}

// Експортуємо функцію для відображення повідомлень
export function showMessage(message, type = 'info', currentScreen) {
    // Показуємо повідомлення на поточному екрані
    const messageElement = document.querySelector(`#${currentScreen} .screen-message`);
    if (messageElement) {
        messageElement.textContent = message;
        messageElement.className = 'screen-message';
        messageElement.classList.add(`message-${type}`);
        
        // Скидаємо повідомлення через 3 секунди, якщо це помилка або успіх
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
        return true;
    }
    return false;
}