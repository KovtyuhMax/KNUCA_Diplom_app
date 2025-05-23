/**
 * Центральний модуль для диспетчеризації клавіш терміналу збору даних (TSD)
 * Відповідає за обробку натискань клавіш, керування станом інтерфейсу
 * та координацію роботи різних режимів терміналу
 */

// Імпортуємо спеціалізовані модулі обробки клавіш для різних режимів роботи
import * as baseKeys from './keys/baseKeys.js';
import * as pickingKeys from './keys/pickingKeys.js';
import * as receivingKeys from './keys/receivingKeys.js';
import * as validationKeys from './keys/validationKeys.js';


/**
 * Глобальні змінні для відстеження стану терміналу
 * Зберігають інформацію про поточний екран, вибрані елементи,
 * активне замовлення та інші параметри роботи
 */
let currentScreen = 'login-screen';      // Поточний активний екран
let currentInput = 'login-input';        // Поточне активне поле введення
let selectedMenuItem = 0;                // Індекс вибраного пункту меню
let focusedInput = null;                 // Елемент введення у фокусі
let currentOrder = null;                 // Поточне замовлення
let currentSku = null;                   // Поточний артикул товару
let currentSkuInfo = null;               // Інформація про поточний товар
let currentLotNumber = null;             // Номер поточного лота
let currentItems = [];                   // Список товарів у поточному замовленні
let currentIndex = 0;                    // Індекс поточного товару в списку
let currentReceivingStep = 'invoice';    // Поточний крок процесу приймання
let tempPalletArray = [];                // Тимчасовий масив для зберігання даних палет
let selectedItem = null;                 // Вибраний товар у списку

// Ініціалізація глобальної змінної для зберігання SSCC коду
window.currentSSCC = null;

/**
 * Ініціалізація диспетчера клавіш терміналу
 * Налаштовує обробники подій та експортує необхідні функції
 */
export function initKeyDispatcher() {
    console.log('Ініціалізація диспетчера клавіш TSD');
    
    // Додаємо глобальний обробник натискань клавіш
    document.addEventListener('keydown', handleKeyDown);
    
    // Експортуємо функції для встановлення стану в глобальний об'єкт window
    // для доступу з інших модулів
    window.setTsdState = setTsdState;
}

/**
 * Встановлює стан терміналу збору даних
 * Оновлює змінні стану на основі переданих параметрів
 * @param {Object} state - Об'єкт з параметрами стану для оновлення
 */
export function setTsdState(state) {
    
    // Зберігаємо попередні значення важливих змінних
    const prevSSCC = window.currentSSCC;
    const prevSelectedItem = selectedItem;
    
    // Оновлюємо базові поля стану
    if (state.currentScreen) currentScreen = state.currentScreen;
    if (state.currentInput) currentInput = state.currentInput;
    if (state.selectedMenuItem !== undefined) selectedMenuItem = state.selectedMenuItem;
    if (state.focusedInput) focusedInput = state.focusedInput;
    if (state.currentOrder) currentOrder = state.currentOrder;
    if (state.currentSku) currentSku = state.currentSku;
    if (state.currentSkuInfo) currentSkuInfo = state.currentSkuInfo;
    if (state.currentLotNumber) currentLotNumber = state.currentLotNumber;
    if (state.currentItems) currentItems = state.currentItems;
    if (state.currentIndex !== undefined) currentIndex = state.currentIndex;
    if (state.currentReceivingStep) currentReceivingStep = state.currentReceivingStep;
    if (state.tempPalletArray) tempPalletArray = state.tempPalletArray;
    
    // Handle selectedItem separately to ensure it's not accidentally reset
    // Only update if explicitly provided or if explicitly set to null
    if ('selectedItem' in state) {
        selectedItem = state.selectedItem;
    } else {
        // Якщо selectedItem не передано, зберігаємо попереднє значення
    }
    
    // Handle currentSSCC separately to ensure it's not accidentally reset
    // Only update if explicitly provided or if explicitly set to null
    if ('currentSSCC' in state) {
        window.currentSSCC = state.currentSSCC;
    } else {
        // Якщо currentSSCC не передано, зберігаємо попереднє значення
    }
}

/**
 * Повертає поточний стан терміналу збору даних
 * @returns {Object} Об'єкт, що містить всі поточні параметри стану
 */
export function getTsdState() {
    return {
        currentScreen,
        currentInput,
        selectedMenuItem,
        focusedInput,
        currentOrder,
        currentSku,
        currentSkuInfo,
        currentLotNumber,
        currentItems,
        currentIndex,
        currentReceivingStep,
        tempPalletArray,
        selectedItem, // Додаємо вибраний товар до стану
        currentSSCC: window.currentSSCC // Get from window to ensure persistence
    };
}

/**
 * Головний обробник натискання клавіш
 * Перетворює фізичні клавіші на логічні дії терміналу
 * @param {KeyboardEvent} event - Подія натискання клавіші
 * @returns {Promise<void>}
 */
async function handleKeyDown(event) {
    // Відображення фізичної клавіатури на клавіші TSD
    let tsdKey = mapKeyboardToTSD(event.key);
    if (tsdKey) {
        event.preventDefault();
        console.log('[keydown]', event.key, 'currentScreen:', getTsdState().currentScreen);
        await handleKeyPress(tsdKey);
    }
}

// Відображення фізичної клавіатури на клавіші TSD
function mapKeyboardToTSD(key) {
    // Відображення фізичних клавіш клавіатури на клавіші TSD
    const keyMap = {
        'Enter': 'Enter',
        'F1': 'F1',
        'F2': 'F2',
        'F3': 'F3',
        'F4': 'F4',
        'F5': 'F5',
        'F6': 'F6',
        'ArrowUp': 'ArrowUp',
        'ArrowDown': 'ArrowDown',
        'ArrowLeft': 'ArrowLeft',
        'ArrowRight': 'ArrowRight',
        'Escape': 'Clear',
        'Delete': 'Clear',
        'Backspace': 'Clear',
        ',': ',',
        '.': '.'
    };
    
    // Відображення цифрових клавіш
    if (/^[0-9]$/.test(key)) {
        return key;
    }
    
    // Відображення буквених клавіш (перетворення на верхній регістр)
    if (/^[a-zA-Z]$/.test(key)) {
        return key.toUpperCase();
    }
    
    return keyMap[key];
}

// Обробка натискання клавіш
export async function handleKeyPress(key) {
    // Отримуємо поточний стан TSD
    const state = getTsdState();
    
    // Обробка клавіш в залежності від поточного екрану
    if (key === 'F1') {
        // Обробка F1 в залежності від екрану
        if (state.currentScreen.includes('picking')) {
            // Використовуємо обробник з модуля picking
            const result = pickingKeys.handleF1(
                state.currentScreen,
                state.currentOrder,
                state.currentSku,
                state.currentSkuInfo,
                state.currentItems,
                state.currentIndex,
                state.currentLotNumber
            );
            await processKeyResult(result);
            if (typeof window.processPickingResult === 'function') {
                window.processPickingResult(result);
            }
        } else if (state.currentScreen === 'receiving-item-screen') {
            console.log('[F1] executing handleItemSelection');
            const result = { action: 'function', function: 'handleItemSelection' };
            await processKeyResult(result);
        } else if (state.currentScreen.includes('receiving')) {
            console.log('[F1] executing receivingKeys.handleF1');
            const result = receivingKeys.handleF1(state.currentScreen, state.currentReceivingStep);
            await processKeyResult(result);
        } else if (state.currentScreen.includes('validation')) {
            // Використовуємо обробник з модуля validation
            const result = validationKeys.handleF1(state.currentScreen);
            await processKeyResult(result);
        } else {
            console.log('[F1] executing baseKeys.handleF1');
            // Використовуємо базовий обробник
            const result = baseKeys.handleF1(state.currentScreen);
            console.log('[handleKeyPress] result:', result);
            await processKeyResult(result);
        }
    } else if (key === 'F2') {
        // Обробка F2 в залежності від екрану
        if (state.currentScreen.includes('receiving')) {
            // Використовуємо обробник з модуля receiving
            const result = receivingKeys.handleF2(state.currentScreen, state.currentReceivingStep);
            await processKeyResult(result);
        } else if (state.currentScreen.includes('validation')) {
            // Використовуємо обробник з модуля validation
            const result = validationKeys.handleF2(state.currentScreen);
            await processKeyResult(result);
        } else if (state.currentScreen === 'picking-result-screen') {
            const lotNumber = state.currentLotNumber;
                window.completeLot(lotNumber);
            const result = {
                action: 'navigate',
                screen: 'picking-order-screen',
                state: {
                    currentScreen: 'picking-order-screen',
                    currentInput: 'picking-order-input',
                    currentOrder: null,
                    currentSku: null,
                    currentSkuInfo: null,
                    currentItems: [],
                    currentIndex: 0,
                    currentLotNumber: null
                }
            };
            await processKeyResult(result);
        } else if (state.currentScreen.includes('picking')) {
            // Використовуємо обробник з модуля picking
            const result = pickingKeys.handleF2(state.currentScreen);
            await processKeyResult(result);
        } else {
            // Використовуємо базовий обробник
            const result = baseKeys.handleF2(state.currentScreen);
            await processKeyResult(result);
        }
    } else if (key === 'F3') {
        // Обробка F3 в залежності від екрану
        if (state.currentScreen.includes('receiving')) {
            // Використовуємо обробник з модуля receiving
            const result = receivingKeys.handleF3(state.currentScreen, state.currentReceivingStep, state.tempPalletArray);
            await processReceivingResult(result);
        } else {
            // Використовуємо базовий обробник
            const result = baseKeys.handleF3(state.currentScreen);
            await processKeyResult(result);
        }
    } else if (key === 'F4') {
        // Обробка F4 в залежності від екрану
        if (state.currentScreen.includes('receiving')) {
            // Використовуємо обробник з модуля receiving
            const result = receivingKeys.handleF4(state.currentScreen, state.currentReceivingStep);
            await processKeyResult(result);
        } else {
            // Використовуємо базовий обробник
            const result = baseKeys.handleF4(state.currentScreen);
            await processKeyResult(result);
        }
    } else if (key === 'F5') {
        // Обробка F5 в залежності від екрану
        if (state.currentScreen.includes('picking')) {
            // Використовуємо обробник з модуля picking
            const result = pickingKeys.handleF5(state.currentScreen, state.currentItems, state.currentIndex, state.currentLotNumber);
            await processKeyResult(result);
        } else {
            // Використовуємо базовий обробник
            const result = baseKeys.handleF5(state.currentScreen);
            await processKeyResult(result);
        }
    } else if (key === 'F6') {
        // Обробка F6 в залежності від екрану
        const result = baseKeys.handleF6(state.currentScreen);
        await processKeyResult(result);
    } else if (key === 'Enter') {
        // Обробка Enter в залежності від екрану
        if (state.currentScreen.includes('picking')) {
            // Використовуємо обробник з модуля picking
            const result = pickingKeys.handleEnter(
                state.currentScreen,
                state.currentItems,
                state.currentIndex,
                state.currentLotNumber
            );
            await processKeyResult(result);
        } else if (state.currentScreen.includes('validation')) {
            // Використовуємо обробник з модуля validation
            const result = validationKeys.handleEnter(state.currentScreen);
            await processKeyResult(result);
        } else {
            // Використовуємо базовий обробник
            const result = await baseKeys.handleEnter(state.currentScreen, state.currentInput, state.focusedInput);
            await processKeyResult(result);
        }
    } else if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(key)) {
        const state = getTsdState();
        console.log('[handleKeyPress] screen:', state.currentScreen, 'key:', key);
    
        // 🧠 лише ті екрани, де дійсно треба викликати receivingKeys
        if (state.currentScreen === 'receiving-item-screen') {
            const result = receivingKeys.handleArrow(
                key,
                state.currentScreen,
                state.currentReceivingStep
            );
            console.log('[handleArrow result]', result);
            await processKeyResult(result);
        } else {
            // 🟢 у всіх інших випадках використовуємо базову стрілкову логіку
            const result = baseKeys.handleArrow(
                key,
                state.currentScreen,
                state.selectedMenuItem,
                document.querySelectorAll('.menu-item'),
                state.focusedInput
            );
            await processKeyResult(result);
        }
    } else if (key === 'Clear') {
        // Обробка клавіші Clear (очищення поля введення)
        clearInput();
    } else if (/^[0-9.,]$/.test(key)) {
        // Обробка цифрових клавіш та розділових знаків
        appendToInput(key);
    }
}


// Очищення поточного поля введення
export function clearInput() {
    // Отримуємо поточний стан
    const state = getTsdState();
    // Очищення поточного поля введення
    const inputElement = state.focusedInput || document.getElementById(state.currentInput);
    if (inputElement) {
        inputElement.textContent = '';
    }
}

// Обробка клавіші Enter
function handleEnterKey() {
    // Визначаємо, який модуль обробки клавіш використовувати
    let result;
    
    if (currentScreen.startsWith('picking-')) {
        // Використовуємо модуль обробки клавіш для режиму відбору
        result = pickingKeys.handleEnter(currentScreen);
        processPickingResult(result);
    } else if (currentScreen.startsWith('receiving-')) {
        // Використовуємо модуль обробки клавіш для режиму прийому
        // Для режиму прийому Enter зазвичай не має спеціальної обробки
        // Тому використовуємо базовий обробник
        result = baseKeys.handleEnter(currentScreen, currentInput, focusedInput);
        processBaseResult(result);
    } else {
        // Використовуємо базовий модуль обробки клавіш
        result = baseKeys.handleEnter(currentScreen, currentInput, focusedInput);
        processBaseResult(result);
    }
}

// Обробка результатів натискання клавіш
async function processKeyResult(result) {
    if (!result) return;

    if (typeof result === 'object') {
        if (result.newMenuItem !== undefined) {
            selectMenuItem(result.newMenuItem);
        }

        if (result.newFocusedInput) {
            setFocusedInput(result.newFocusedInput);
        }
    }

    if (result?.action === 'confirmReceivingStart') {
        processReceivingResult(result); // ✅ тепер викличе window.confirmReceivingStart()
    }

    if (result?.action === 'navigateItemList') {
        processReceivingResult(result);
        return;
    }
    
    // Обробка результатів в залежності від типу
    if (result.action === 'navigate') {
        // Навігація на інший екран
        if (typeof window.showScreen === 'function') {
            window.showScreen(result.screen);
        }
        
        // Оновлення стану
        if (result.state) {
            setTsdState(result.state);
        }
    } else if (result.action === 'function') {
        // Виклик функції
        if (typeof window[result.function] === 'function') {
            window[result.function](...(result.params || []));
        }
    } else if (result.action === 'update') {
        // Оновлення стану
        if (result.state) {
            setTsdState(result.state);
        }
    } else if (result.action === 'triggerShowConfirmationAndSave') {
        // Виклик централізованої функції підтвердження
        if (typeof window.showConfirmationAndSave === 'function') {
            window.showConfirmationAndSave();
        }
    } else if (result.action === 'login') {
        // Обробка логіну користувача
        const data = await baseKeys.loginUser(result.username);
        if (data.success) {
            window.showScreen('menu-screen');
            window.selectMenuItem(0);
            document.body.focus();
            setTsdState({ currentScreen: 'menu-screen' });
            window.showMessage(data.message, 'success');
        } else {
            window.showMessage(data.message, 'error');
        }
    } else if (result === true) {
        const state = getTsdState();
        if (state.currentScreen === 'menu-screen') {
            const menuItems = document.querySelectorAll('.menu-item');
            const selectedOption = menuItems[state.selectedMenuItem]?.getAttribute('data-option');
            if (selectedOption) {
                navigateToOption(selectedOption);
            }
        }
    }
}

// Обробка клавіш стрілок
export function handleArrowKey(key) {
    const state = getTsdState();
    console.log('[handleArrow] focusedInput in state:', state.focusedInput?.id);

    let result;

    if (state.currentScreen.startsWith('picking-')) {
        result = baseKeys.handleArrow(
            key,
            state.currentScreen,
            state.selectedMenuItem,
            document.querySelectorAll('.menu-item'),
            state.focusedInput
        );
        processBaseResult(result);
    } else if (state.currentScreen === 'receiving-item-screen') {
        result = receivingKeys.handleArrow(
            key,
            state.currentScreen,
            state.currentReceivingStep
        );
        processReceivingResult(result);
    } else {
        result = baseKeys.handleArrow(
            key,
            state.currentScreen,
            state.selectedMenuItem,
            document.querySelectorAll('.menu-item'),
            state.focusedInput
        );
        processBaseResult(result);
    }
}


// Обробка результату від модуля обробки клавіш для режиму відбору
window.processPickingResult = function(result) {
    if (!result) return;
    
    switch (result.action) {
        case 'startPicking':
            // Запуск процесу відбору
            document.dispatchEvent(new Event('pickingStart'));
            break;
        case 'fetchOrderDetails':
            // Отримання деталей замовлення
            if (typeof window.fetchOrderDetails === 'function') {
                window.fetchOrderDetails(result.lotNumber);
            }
            break;
        case 'performPicking':
            console.log('[dispatcher] performPicking action received:', result);
            // Виконання відбору
            if (typeof window.performPicking === 'function') {
                // Передаємо параметр progressFlow для автоматичного переходу до наступного товару
                window.performPicking(result.quantity, result.progressFlow, result.lotNumber);
            } else {
                console.log('[dispatcher] performPicking is NOT a function');
            }   
            break;
        case 'nextItem':
            // Перехід до наступного товару
            currentIndex = result.newIndex;
            if (typeof window.showCurrentItem === 'function') {
                window.showCurrentItem();
            }
            window.showMessage('Перехід до наступного товару', 'info');
            break;
        case 'completeLot':
            // Завершення лота
            if (typeof window.completeLot === 'function') {
                window.completeLot(result.lotNumber);
            } else {
                console.log('[dispatcher] completeLot is NOT a function');
                
                // Резервний варіант, якщо функція не знайдена
                const resultElement = document.getElementById('picking-result');
                if (resultElement) {
                    resultElement.innerHTML = `
                        <div class="result-success">Лот завершено</div>
                        <div>Всі товари з лота ${result.lotNumber} успішно відібрані</div>
                    `;
                }
                
                // Оновлюємо повідомлення на екрані
                const screenMessage = document.querySelector('#picking-result-screen .screen-message');
                if (screenMessage) {
                    screenMessage.textContent = 'Натисніть F2 для повернення в меню';
                }
                
                // Показуємо екран результату
                window.showScreen('picking-result-screen');
            }
            break;
        case 'confirmExit':
            // Підтвердження виходу
            if (confirm('Ви впевнені, що хочете вийти з режиму комплектації? Незбережений прогрес буде втрачено.')) {
                // Повернення до меню
                window.showScreen('menu-screen');
                window.selectMenuItem(0);
            }
            break;
        case 'returnToMenu':
            // Повернення до меню без підтвердження
            window.showScreen('menu-screen');
            window.selectMenuItem(0);
            break;
        case 'validateInvoiceNumber':
            // Валідація номеру накладної
            if (typeof window.validateInvoiceNumber === 'function') {
                window.validateInvoiceNumber(result.invoiceNumber);
            }
            break;
        case 'validateSSCC':
            // Валідація SSCC коду
            if (typeof window.validateSSCC === 'function') {
                window.validateSSCC(result.ssccCode);
            }
            break;
        case 'showError':
        case 'showInfo':
        case 'showWarning':
            // Повідомлення вже показано в обробнику
            break;
        case 'none':
        default:
            // Нічого не робимо
            break;
    }
}

// Обробка результату від модуля обробки клавіш для режиму прийому
export function processReceivingResult(result) {
    if (!result) return;
    
    switch (result.action) {
        case 'confirmReceivingStart':
            // Підтвердження початку прийому
            if (typeof window.confirmReceivingStart === 'function') {
                window.confirmReceivingStart();
            }
            break;
        case 'handleSSCCEntry':
            // Обробка введення SSCC
            if (typeof window.handleSSCCEntry === 'function') {
                window.handleSSCCEntry(result.ssccCode);
            }
            break;
        case 'handleItemSelection':
            // Обробка вибору товару
            if (typeof window.handleItemSelection === 'function') {
                window.handleItemSelection();
            }
            break;
        case 'handleDataEntry':
            // Обробка введення даних
            if (typeof window.handleDataEntry === 'function') {
                window.handleDataEntry();
            }
            break;
        case 'navigateItemList':
            // Навігація по списку товарів
            if (typeof window.navigateItemList === 'function') {
                window.navigateItemList(result.direction);
            }
            break;
        case 'triggerShowConfirmationAndSave':
            // Виклик централізованої функції підтвердження
            if (typeof window.showConfirmationAndSave === 'function') {
                window.showConfirmationAndSave();
            }
            break;
        case 'cancelConfirmation':
            // Відміна підтвердження
            if (typeof window.cancelConfirmation === 'function') {
                window.cancelConfirmation();
            }
            break;
        case 'returnToMenu':
            // Повернення до меню
            window.showScreen('menu-screen');
            window.selectMenuItem(0);
            break;
        case 'showError':
        case 'showInfo':
        case 'showWarning':
            // Повідомлення вже показано в обробнику
            break;
        case 'none':
        default:
            // Нічого не робимо
            break;
    }
}

// Обробка результату від базового модуля обробки клавіш
function processBaseResult(result) {
    if (!result) return;
    
    // Якщо результат є об'єктом з властивостями
    if (typeof result === 'object') {
        // Обробка зміни вибраного пункту меню
        if (result.newMenuItem !== undefined) {
            selectMenuItem(result.newMenuItem);
        }
        
        // Обробка зміни фокусу на полі введення
        if (result.newFocusedInput) {
            setFocusedInput(result.newFocusedInput);
        }
    } else if (result === true) {
        // Якщо результат є true, виконуємо стандартну дію
        if (currentScreen === 'login-screen') {
            const loginCode = document.getElementById('login-input').textContent;
            if (loginCode.length > 0) {
                // Відправляємо запит на логін
                fetch('/tsd-emulator/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                    },
                    body: JSON.stringify({ username: loginCode })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Успішний логін
                        window.showScreen('menu-screen');
                        selectMenuItem(0); // Вибираємо перший пункт меню
                        // Показуємо вітальне повідомлення
                        window.showMessage(data.message, 'success');
                    } else {
                        // Невдалий логін
                        window.showMessage(data.message, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    window.showMessage("Помилка з'єднання з сервером", 'error');
                });
            }
        } else if (currentScreen === 'menu-screen') {
            // Навігація до вибраного пункту меню
            const menuItems = document.querySelectorAll('.menu-item');
            const selectedOption = menuItems[selectedMenuItem].getAttribute('data-option');
            navigateToOption(selectedOption);
        }
    }
}

// Вибір пункту меню
function selectMenuItem(index) {
    // Знімаємо вибір з усіх пунктів
    const menuItems = document.querySelectorAll('.menu-item');
    menuItems.forEach(item => item.classList.remove('selected'));
    
    // Додаємо вибір до вказаного пункту
    if (index >= 0 && index < menuItems.length) {
        menuItems[index].classList.add('selected');
        setTsdState({ selectedMenuItem: index });
    }
}

// Встановлення фокусу на полі введення
function setFocusedInput(inputElement) {
    // Знімаємо фокус з усіх
    document.querySelectorAll('.input-value').forEach(input => {
        input.classList.remove('focused');
    });

    // Додаємо фокус до нового елемента
    if (inputElement) {
        inputElement.classList.add('focused');
        inputElement.focus(); // якщо це input або div з tabindex

        // ❗ ОНОВЛЕННЯ СТАНУ — критично важливо
        setTsdState({
            focusedInput: inputElement,
            currentInput: inputElement.id
        });
    }
}

// Навігація до вибраного пункту меню
function navigateToOption(option) {
    // Навігація до вибраного пункту меню
    switch(option) {
        case 'receiving':
            // Запуск процесу прийому
            document.dispatchEvent(new Event('receivingStart'));
            break;
        case 'picking':
            // Запуск процесу відбору
            document.dispatchEvent(new Event('pickingStart'));
            break;
        case 'relocation':
            window.showScreen('relocation-screen');
            currentInput = 'relocation-input';
            break;
    }
}

// Обробка сканування штрих-коду
export function processBarcode(barcode) {
    // Обробка штрих-коду в залежності від поточного екрану
    console.log(`Обробка штрих-коду: ${barcode} на екрані: ${currentScreen}`);
    
    let result;
    
    if (currentScreen.startsWith('picking-')) {
        // Використовуємо модуль обробки клавіш для режиму відбору
        result = pickingKeys.handleBarcodeScan(barcode, currentScreen);
        processPickingResult(result);
    } else if (currentScreen.startsWith('receiving-')) {
        // Використовуємо модуль обробки клавіш для режиму прийому
        result = receivingKeys.handleBarcodeScan(barcode, currentScreen, currentReceivingStep);
        processReceivingResult(result);
    } else {
        // Показуємо повідомлення про успіх на поточному екрані
        const messageElement = document.querySelector(`#${currentScreen} .screen-message`);
        if (messageElement) {
            if (currentScreen === 'picking-screen') {
                messageElement.textContent = `Товар відібрано: ${barcode}`;
            } else if (currentScreen === 'relocation-screen') {
                messageElement.textContent = `Товар переміщено: ${barcode}`;
            }
            
            // Скидаємо повідомлення через 3 секунди
            setTimeout(() => {
                if (currentScreen === 'picking-screen') {
                    messageElement.textContent = 'Відскануйте або введіть код та натисніть F1';
                } else if (currentScreen === 'relocation-screen') {
                    messageElement.textContent = 'Відскануйте або введіть код та натисніть F1';
                }
            }, 3000);
        }
    }
}

// Функція для додавання символу до поточного поля введення
export function appendToInput(key) {
    const inputElement = focusedInput || document.getElementById(currentInput);
    if (inputElement) {
        // Додаємо символ до значення поля введення
        inputElement.textContent += key;
    }
}

// Ініціалізуємо диспетчер клавіш при завантаженні сторінки
document.addEventListener('DOMContentLoaded', initKeyDispatcher);