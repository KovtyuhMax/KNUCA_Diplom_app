/**
 * Модуль терміналу приймання товарів на склад
 * Відповідає за процес приймання товарів, перевірку SSCC кодів та оновлення складських запасів
 * Реалізує інтерфейс користувача для операторів приймання
 */

// Імпортуємо необхідні модулі та функції
import * as keyDispatcher from './tsd/keyDispatcher.js';
import * as receivingKeys from './tsd/keys/receivingKeys.js';
import { showMessage } from './tsd/keys/baseKeys.js';
import { processReceivingResult } from './tsd/keyDispatcher.js';

/**
 * Змінні стану процесу приймання
 * Примітка: основний стан тепер керується через диспетчер клавіш,
 * ці змінні залишені для сумісності з існуючим кодом
 */
let ssccData = null; // Дані SSCC коду, включаючи вагу та інші параметри

/**
 * Допоміжні функції для роботи з глобальними методами
 * Забезпечують сумісність з різними частинами системи
 */

/**
 * Отримує CSRF токен для захисту від CSRF атак
 * @returns {string} CSRF токен для використання в запитах
 */
function getCsrfToken() {
    return window.getCsrfToken ? window.getCsrfToken() : document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
}

/**
 * Відображає вказаний екран інтерфейсу
 * @param {string} screenId - Ідентифікатор екрану для відображення
 */
function showScreen(screenId) {
    if (typeof window.showScreen === 'function') {
        window.showScreen(screenId);
    } else {
        console.error('Функція showScreen не знайдена');
    }
}

/**
 * Встановлює фокус на вказаний елемент введення
 * @param {HTMLElement} inputElement - Елемент введення для фокусування
 */
function setFocusedInput(inputElement) {
    if (typeof window.setFocusedInput === 'function') {
        window.setFocusedInput(inputElement);
    } else if (typeof keyDispatcher.setFocusedInput === 'function') {
        keyDispatcher.setFocusedInput(inputElement);
    } else {
        console.error('Функція setFocusedInput не знайдена');
        // Резервний варіант
        if (inputElement) {
            const allInputs = document.querySelectorAll('.input-value');
            allInputs.forEach(input => input.classList.remove('focused'));
            inputElement.classList.add('focused');
        }
    }
}

/**
 * Очищає поточне поле введення
 */
function clearInput() {
    if (typeof keyDispatcher.clearInput === 'function') {
        keyDispatcher.clearInput();
    }
}

/**
 * Ініціалізація модуля приймання при завантаженні сторінки
 * Налаштовує обробники подій та експортує необхідні функції
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('TSD Receiving module initialized');
    
    // Add event listeners specific to receiving flow
    document.addEventListener('receivingStart', handleReceivingStart);
    document.addEventListener('receivingSSCCEntry', handleSSCCEntry);
    document.addEventListener('receivingItemSelection', handleItemSelection);
    document.addEventListener('receivingDataEntry', handleDataEntry);
    document.addEventListener('receivingComplete', handleReceivingComplete);
    
    // Експортуємо функцію для обробки сканування штрих-кодів
    window.handleReceivingBarcodeScan = handleReceivingBarcodeScan;
    
    // Експортуємо функції для використання з keyDispatcher
    window.confirmReceivingStart = confirmReceivingStart;
    window.handleSSCCEntry = handleSSCCEntry;
    window.handleItemSelection = handleItemSelection;
    window.navigateItemList = navigateItemList;
    window.handleDataEntry = handleDataEntry;
    window.showConfirmationAndSave = showConfirmationAndSave;
});

/**
 * Обробляє сканування штрих-кодів у режимі приймання
 * @param {string} barcode - Відсканований штрих-код
 * @param {string} screenId - Ідентифікатор поточного екрану
 */
function handleReceivingBarcodeScan(barcode, screenId) {
    console.log(`Отримано штрих-код у режимі приймання: ${barcode} на екрані ${screenId}`);
    
    // Отримуємо поточний стан з диспетчера клавіш
    const state = keyDispatcher.getTsdState();
    const currentReceivingStep = state.currentReceivingStep || 'invoice';
    
    // Обробляємо штрих-код в залежності від поточного кроку
    if (screenId.includes('receiving-invoice')) {
        // Обробка штрих-коду накладної
        processInvoiceBarcode(barcode);
    } else if (screenId.includes('receiving-sscc')) {
        // Обробка штрих-коду SSCC
        processSSCCBarcode(barcode);
    } else if (screenId.includes('receiving-item')) {
        // Обробка штрих-коду товару
        processItemBarcode(barcode);
    }
}

// Функція для обробки штрих-коду накладної
function processInvoiceBarcode(barcode) {
    console.log(`Обробка штрих-коду накладної: ${barcode}`);
    
    // Перевіряємо формат штрих-коду накладної
    if (barcode.startsWith('INV')) {
        // Отримуємо номер накладної з штрих-коду
        const invoiceNumber = barcode.substring(3);
        
        // Встановлюємо значення в поле введення
        const invoiceInput = document.getElementById('invoice-number-input');
        if (invoiceInput) {
            invoiceInput.textContent = invoiceNumber;
            
            // Оновлюємо стан у диспетчері клавіш
            keyDispatcher.setTsdState({
                currentInput: 'invoice-number-input'
            });
            
            // Автоматично перевіряємо накладну
            if (typeof window.validateInvoiceNumber === 'function') {
                window.validateInvoiceNumber(invoiceNumber);
            }
        }
    } else {
        // Показуємо повідомлення про невірний формат
        window.showMessage('Невірний формат штрих-коду накладної', 'error');
    }
}

// Функція для обробки штрих-коду SSCC
function processSSCCBarcode(barcode) {
    console.log(`Обробка штрих-коду SSCC: ${barcode}`);
    
    // Перевіряємо формат штрих-коду SSCC
    if (barcode.startsWith('00') && barcode.length === 18) {
        // Встановлюємо значення в поле введення
        const ssccInput = document.getElementById('sscc-input');
        if (ssccInput) {
            ssccInput.textContent = barcode;
            
            // Оновлюємо стан у диспетчері клавіш
            keyDispatcher.setTsdState({
                currentInput: 'sscc-input',
                currentSSCC: barcode
            });
            
            // Автоматично перевіряємо SSCC
            if (typeof window.validateSSCC === 'function') {
                window.validateSSCC(barcode);
            }
        }
    } else {
        // Показуємо повідомлення про невірний формат
        window.showMessage('Невірний формат штрих-коду SSCC', 'error');
    }
}

// Функція для обробки штрих-коду товару
function processItemBarcode(barcode) {
    console.log(`Обробка штрих-коду товару: ${barcode}`);
    
    // Перевіряємо формат штрих-коду товару (EAN-13, UPC, тощо)
    if (/^\d{8,14}$/.test(barcode)) {
        // Встановлюємо значення в поле введення
        const itemInput = document.getElementById('item-barcode-input');
        if (itemInput) {
            itemInput.textContent = barcode;
            
            // Оновлюємо стан у диспетчері клавіш
            keyDispatcher.setTsdState({
                currentInput: 'item-barcode-input'
            });
            
            // Перевіряємо товар за штрих-кодом
            checkItemByBarcode(barcode);
        }
    } else {
        // Показуємо повідомлення про невірний формат
        window.showMessage('Невірний формат штрих-коду товару', 'error');
    }
}

// Функція для перевірки товару за штрих-кодом
async function checkItemByBarcode(barcode) {
    try {
        // Отримуємо поточний стан з диспетчера клавіш
        const state = keyDispatcher.getTsdState();
        const currentOrder = state.currentOrder;
        
        if (!currentOrder) {
            window.showMessage('Спочатку виберіть накладну', 'warning');
            return;
        }
        
        // Відправляємо запит на сервер для перевірки товару
        const response = await fetch('/receiving/check-item', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.getCsrfToken()
            },
            body: JSON.stringify({
                order_id: currentOrder.id,
                barcode: barcode
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Показуємо інформацію про товар
            window.showMessage(`Знайдено: ${data.item.name}`, 'success');
            
            // Оновлюємо стан у диспетчері клавіш
            keyDispatcher.setTsdState({
                currentSku: data.item.sku,
                currentSkuInfo: data.item
            });
            
            // Переходимо до введення кількості
            setTimeout(() => {
                const quantityInput = document.getElementById('item-quantity-input');
                if (quantityInput) {
                    window.setFocusedInput(quantityInput);
                }
            }, 500);
        } else {
            window.showMessage(data.message || 'Товар не знайдено', 'error');
        }
    } catch (error) {
        console.error('Помилка при перевірці товару:', error);
        window.showMessage('Помилка при перевірці товару', 'error');
    }
}

// Handle the start of receiving process
function handleReceivingStart() {
    // Оновлюємо стан у диспетчері клавіш
    keyDispatcher.setTsdState({
        currentScreen: 'receiving-start-screen',
        currentReceivingStep: 'invoice',
        currentOrder: null,
        currentSSCC: null,
        selectedItem: null,
        tempPalletArray: []
    });
    
    // Show the receiving start screen
    showReceivingStartScreen();
}

// Show the receiving start screen with invoice selection
function showReceivingStartScreen() {
    const screen = document.getElementById('receiving-start-screen');
    if (!screen) return;

    window.showScreen('receiving-start-screen');

    // Оновлюємо стан (без focusedInput — бо DOM ще не готовий)
    keyDispatcher.setTsdState({
        currentScreen: 'receiving-start-screen',
        currentInput: 'invoice-number-input'
    });

    // Ставимо дату
    const today = new Date();
    const dateStr = today.toISOString().split('T')[0];
    document.getElementById('receiving-date-value').textContent = dateStr;

    // Завантажуємо замовлення
    loadAvailableOrders();

    // ✅ Ставимо фокус — ПІСЛЯ DOM оновлення
    setTimeout(() => {
        const firstInput = document.querySelector('#receiving-start-screen .input-value');
        if (firstInput) {
            keyDispatcher.setFocusedInput(firstInput); // 🔥 Ключовий виклик
        }
    }, 0);
}

// Load available orders from the server
function loadAvailableOrders() {
    fetch('/tsd-emulator/api/available-orders', {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Populate the order selection dropdown
            const orderSelect = document.getElementById('order-select');
            orderSelect.innerHTML = '';
            
            data.orders.forEach(order => {
                const option = document.createElement('option');
                option.value = order.invoice_number;
                option.textContent = `${order.invoice_number} - ${order.supplier_name}`;
                orderSelect.appendChild(option);
            });
            
            // Enable order selection if there are orders
            if (data.orders.length > 0) {
                orderSelect.disabled = false;
                document.getElementById('invoice-number-input').textContent = data.orders[0].invoice_number;
            } else {
                showMessage('Немає доступних замовлень для прийому', 'warning');
            }
        } else {
            showMessage(data.message || 'Помилка завантаження замовлень', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage("Помилка з'єднання з сервером", 'error');
    });
}

// Handle F1 press on the receiving start screen
window.confirmReceivingStart = async function() {
    const invoiceNumber = document.getElementById('invoice-number-input').textContent;
    const supplierInvoice = document.getElementById('supplier-invoice-input').textContent;
    const receivingDate = document.getElementById('receiving-date-value').textContent;
    
    if (!invoiceNumber) {
        showMessage('Виберіть номер замовлення', 'warning', 'receiving-start-screen');
        return;
    }
    
    // Validate invoice number before proceeding
    let isValid = false;
    if (typeof window.validateInvoiceNumber === 'function') {
        isValid = await window.validateInvoiceNumber(invoiceNumber);
    } else {
        console.warn('Функція validateInvoiceNumber не знайдена');
        isValid = true; // Припускаємо, що валідація пройшла успішно
    }
    
    if (!isValid) {
        return;
    }
    
    console.log('[confirmReceivingStart] payload =', {
        invoice_number: invoiceNumber,
        invoice_number_supplier: supplierInvoice,
        receiving_date: receivingDate
    });

    // Send data to server to start receiving process
    fetch('/tsd-emulator/api/start-receiving', {
        method: 'POST',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            invoice_number: invoiceNumber,
            invoice_number_supplier: supplierInvoice,
            receiving_date: receivingDate
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Store the selected order in the TSD state
            keyDispatcher.setTsdState({
                currentOrder: data.order,
                currentReceivingStep: 'sscc'
            });
            
            // Move to SSCC entry screen
            showSSCCEntryScreen();
        } else {
            showMessage(data.message || 'Помилка початку процесу прийому', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage("Помилка з'єднання з сервером", 'error');
    });
}

// Show the SSCC entry screen
function showSSCCEntryScreen() {
    showScreen('receiving-sscc-screen');

    // Почекаємо на наступний "tick", щоб DOM оновився
    setTimeout(() => {
        const firstInput = document.querySelector('#receiving-sscc-screen .input-value');
        console.log('[showSSCCEntryScreen] setting focus to:', firstInput?.id);

        if (firstInput) {
            firstInput.classList.add('focused');
            firstInput.focus();

            keyDispatcher.setTsdState({
                currentScreen: 'receiving-sscc-screen',
                currentInput: firstInput.id,
                focusedInput: firstInput
            });
        } else {
            console.warn('⚠️ .input-value не знайдено в #receiving-sscc-screen');
        }
    }, 0); // 0 мс — це означає "після вставлення в DOM"
    keyDispatcher.clearInput();
}

// Handle SSCC entry
window.handleSSCCEntry = async function() {
    const ssccCode = document.getElementById('sscc-input').textContent.trim();
    const state = keyDispatcher.getTsdState();
    const tempPalletArray = state.tempPalletArray || [];
    
    if (!ssccCode) {
        showMessage('Введіть SSCC код', 'warning', 'receiving-sscc-screen');
        return;
    }
    
    if (tempPalletArray.some(item => item.sscc === ssccCode)) {
        showMessage('Цей SSCC вже використовується', 'error', 'receiving-sscc-screen');
        return;
    }

    const duplicateCheck = await fetch(`/tsd-emulator/api/check-received-sscc?sscc=${ssccCode}`, {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    });
    const dupData = await duplicateCheck.json();
    
    if (dupData.exists) {
        showMessage('Цей SSCC вже був використаний!', 'error', 'receiving-sscc-screen');
        return;
    }

    // Validate SSCC code using the validation API
    let isValid = false;
    if (typeof window.validateSSCC === 'function') {
        isValid = await window.validateSSCC(ssccCode);
    } else {
        console.warn('Функція validateSSCC не знайдена');
        isValid = true; // Припускаємо, що валідація пройшла успішно
    }
    
    if (!isValid) {
        return;
    }
    
    // Fetch SSCC data including weight from scales endpoint
    try {
        const response = await fetch(`/scales/get-sscc-data?sscc=${ssccCode}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        const data = await response.json();
        
        if (!data.success) {
            showMessage(data.message || 'SSCC not found in scale records', 'error', 'receiving-sscc-screen');
            return;
        }
        
        // Store the SSCC data
        ssccData = {
            sscc: data.sscc,
            weight: data.gross_weight,
            created_at: data.created_at
        };
        
        // Store the current SSCC in the TSD state
        // Важливо: зберігаємо поточний selectedItem, якщо він є
        const currentSelectedItem = state.selectedItem;
        keyDispatcher.setTsdState({
            currentScreen: 'receiving-item-screen',
            currentSSCC: ssccCode,
            currentReceivingStep: 'item',
            selectedItem: currentSelectedItem // Зберігаємо вибраний товар між циклами
        });
        
        console.log('SSCC прийнято:', ssccCode);
        
        // Call the function to show item selection screen and load items
        // ВАЖЛИВО: Передаємо SSCC-код явно
        showItemSelectionScreen(ssccCode);
        
        showMessage('SSCC код прийнято. Товари завантажено.', 'success', 'receiving-item-screen');
    } catch (error) {
        console.error('Error fetching SSCC data:', error);
        showMessage("Помилка отримання даних SSCC", 'error', 'receiving-sscc-screen');
    }
}

// Show item selection screen
function showItemSelectionScreen(ssccCode) {
    const state = keyDispatcher.getTsdState();
    const currentOrder = state.currentOrder;
    
    // Ensure we have the SSCC code from either parameter or state
    // ВАЖЛИВО: Пріоритет надаємо параметру ssccCode, якщо він переданий
    const currentSSCC = ssccCode || state.currentSSCC;
    
    console.log('[showItemSelectionScreen] Using SSCC:', currentSSCC);
    
    if (!currentOrder) {
        showMessage('Замовлення не вибрано', 'error', 'receiving-sscc-screen');
        return;
    }
    
    if (!currentSSCC) {
        showMessage('SSCC код не вибрано', 'error', 'receiving-sscc-screen');
        return;
    }
    
    // First update the state with the current SSCC before any async operations
    // Зберігаємо поточний selectedItem, якщо він є
    const currentSelectedItem = state.selectedItem;
    keyDispatcher.setTsdState({
        currentScreen: 'receiving-item-screen',
        currentSSCC: currentSSCC, // Явно зберігаємо SSCC
        currentReceivingStep: 'item',
        selectedItem: currentSelectedItem // Зберігаємо вибраний товар
    });
    
    // Load items from the selected order
    fetch(`/tsd-emulator/api/order-items?invoice_number=${currentOrder.invoice_number}`, {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show the item selection screen
            showScreen('receiving-item-screen');
            
            // Populate the item list
            const itemList = document.getElementById('item-list');
            itemList.innerHTML = '';
            
            data.items.forEach((item, index) => {
                const itemElement = document.createElement('div');
                itemElement.classList.add('item-option');
                itemElement.setAttribute('data-item-id', item.id);
                itemElement.setAttribute('data-item-index', index);
                itemElement.textContent = `${item.sku} - ${item.product_name}`;
                itemList.appendChild(itemElement);
            });
            
            // Визначаємо, який елемент вибрати
            let selectedIndex = 0;
            let selectedItemData = data.items[0];
            
            // Якщо є збережений selectedItem, знаходимо його індекс
            if (currentSelectedItem) {
                const foundIndex = data.items.findIndex(item => item.id === currentSelectedItem.id);
                if (foundIndex >= 0) {
                    selectedIndex = foundIndex;
                    selectedItemData = data.items[foundIndex];
                }
            }
            
            // Вибираємо відповідний елемент в UI
            if (data.items.length > 0) {
                const itemElements = itemList.querySelectorAll('.item-option');
                if (itemElements[selectedIndex]) {
                    itemElements[selectedIndex].classList.add('selected');
                    itemElements[selectedIndex].scrollIntoView({ block: 'nearest' });
                }
                
                // Оновлюємо стан у диспетчері клавіш - зберігаємо SSCC та вибраний товар
                keyDispatcher.setTsdState({
                    selectedItem: selectedItemData,
                    currentSSCC: currentSSCC // Явно зберігаємо SSCC
                });
                
                // Перевіряємо, що стан правильно оновлено
                console.log('[showItemSelectionScreen] Updated state:', keyDispatcher.getTsdState());
            }
        } else {
            showMessage(data.message || 'Помилка завантаження товарів', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage("Помилка з'єднання з сервером", 'error');
    });
}

// Handle item selection
function handleItemSelection() {
    const state = keyDispatcher.getTsdState();
    const currentOrder = state.currentOrder;
    const currentSSCC = state.currentSSCC;
    
    console.log('[handleItemSelection] Current state:', state);
    console.log('[handleItemSelection] Using SSCC:', currentSSCC);
    
    // Перевіряємо наявність SSCC коду
    if (!currentSSCC) {
        console.error('[handleItemSelection] SSCC is missing in state:', state);
        showMessage('SSCC код не вибрано', 'error', 'receiving-item-screen');
        return;
    }
    
    // Перевіряємо, чи DOM повністю відрендерений
    setTimeout(() => {
        // Перевіряємо наявність вибраного елемента в DOM
        const selectedElement = document.querySelector('#item-list .selected');
        
        // Якщо елемент не знайдено, але є збережений selectedItem в стані
        if (!selectedElement && state.selectedItem) {
            console.log('[handleItemSelection] No selected element in DOM, but selectedItem exists in state');
            // Використовуємо збережений selectedItem
            keyDispatcher.setTsdState({
                currentReceivingStep: 'data',
                currentSSCC: currentSSCC, // Явно зберігаємо SSCC
                selectedItem: state.selectedItem // Явно зберігаємо вибраний товар
            });
            
            showDataEntryScreen();
            return;
        }
        
        // Якщо елемент не знайдено і немає збереженого selectedItem
        if (!selectedElement) {
            showMessage('Товар не вибрано', 'warning', 'receiving-item-screen');
            return;
        }
        
        // Отримуємо індекс вибраного товару
        const itemIndex = parseInt(selectedElement.getAttribute('data-item-index'));
        
        // Отримуємо поточні товари зі стану
        const currentItems = state.currentItems || [];
        
        // Якщо товари вже завантажені в стан, використовуємо їх
        if (currentItems.length > 0 && itemIndex < currentItems.length) {
            const selectedItem = currentItems[itemIndex];
            
            // Зберігаємо вибраний товар та SSCC в стані
            keyDispatcher.setTsdState({
                selectedItem: selectedItem,
                currentReceivingStep: 'data',
                currentSSCC: currentSSCC // Явно зберігаємо SSCC
            });
            
            showDataEntryScreen();
            return;
        }
        
        // Якщо товари не завантажені, робимо запит (це має бути рідкісний випадок)
        fetch(`/tsd-emulator/api/order-items?invoice_number=${currentOrder.invoice_number}`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(res => res.json())
        .then(data => {
            if (!data.success || !data.items || data.items.length === 0) {
                showMessage('Помилка: товари не знайдено', 'error');
                return;
            }
            
            // Зберігаємо всі товари в стані для майбутнього використання
            keyDispatcher.setTsdState({
                currentItems: data.items
            });
            
            const selectedItem = data.items[itemIndex];
            if (!selectedItem) {
                showMessage('Помилка: обраний товар не знайдено в даних', 'error');
                return;
            }
            
            // Зберігаємо вибраний товар та SSCC в стані
            keyDispatcher.setTsdState({
                selectedItem: selectedItem,
                currentReceivingStep: 'data',
                currentSSCC: currentSSCC // Явно зберігаємо SSCC
            });
            
            showDataEntryScreen();
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage("Помилка з'єднання з сервером", 'error');
        });
    }, 0); // Використовуємо setTimeout з 0 мс для гарантії, що DOM оновлено
}



// Navigate item list with arrow keys (викликається з keyDispatcher через receivingKeys)
window.navigateItemList = function(direction) {
    const state = keyDispatcher.getTsdState();
    if (state.currentReceivingStep !== 'item') return;
    
    // Store the current SSCC to preserve it
    const currentSSCC = state.currentSSCC;
    console.log('[navigateItemList] Preserving currentSSCC:', currentSSCC);
    
    // Зберігаємо поточний вибраний товар
    const currentSelectedItem = state.selectedItem;
    
    const itemList = document.getElementById('item-list');
    const items = itemList.querySelectorAll('.item-option');
    if (items.length === 0) return;
    
    // Find the currently selected item
    let currentIndex = -1;
    items.forEach((item, index) => {
        if (item.classList.contains('selected')) {
            currentIndex = index;
        }
    });
    
    // Якщо немає вибраного елемента в DOM, але є в стані, знаходимо його індекс
    if (currentIndex === -1 && currentSelectedItem) {
        items.forEach((item, index) => {
            const itemId = item.getAttribute('data-item-id');
            if (itemId && itemId === currentSelectedItem.id) {
                currentIndex = index;
            }
        });
    }
    
    // Remove selection from current item
    if (currentIndex >= 0) {
        items[currentIndex].classList.remove('selected');
    }
    
    // Calculate new index based on direction
    let newIndex = 0;
    if (direction === 'up') {
        newIndex = currentIndex <= 0 ? items.length - 1 : currentIndex - 1;
    } else if (direction === 'down') {
        newIndex = currentIndex >= items.length - 1 ? 0 : currentIndex + 1;
    } else {
        newIndex = currentIndex >= 0 ? currentIndex : 0;
    }
    
    // Apply selection to new item
    items[newIndex].classList.add('selected');
    
    // Update the selected item data
    const itemIndex = parseInt(items[newIndex].getAttribute('data-item-index'));
    const currentOrder = state.currentOrder;
    
    if (!currentOrder) return;
    
    fetch(`/tsd-emulator/api/order-items?invoice_number=${currentOrder.invoice_number}`, {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.items.length > itemIndex) {
            // Оновлюємо стан у диспетчері клавіш, зберігаючи currentSSCC та інші важливі дані
            keyDispatcher.setTsdState({
                selectedItem: data.items[itemIndex],
                currentSSCC: currentSSCC, // Явно зберігаємо SSCC
                currentReceivingStep: 'item' // Зберігаємо поточний крок
            });
            
            // Перевіряємо, що стан правильно оновлено
            console.log('[navigateItemList] Updated state with SSCC:', keyDispatcher.getTsdState().currentSSCC);
            console.log('[navigateItemList] Updated selectedItem:', keyDispatcher.getTsdState().selectedItem);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
    
    // Scroll item into view if needed
    items[newIndex].scrollIntoView({ block: 'nearest' });
}

// Show data entry screen
function showDataEntryScreen() {
    // Отримуємо поточний стан з диспетчера клавіш
    const state = keyDispatcher.getTsdState();
    const selectedItem = state.selectedItem;
    const currentSSCC = state.currentSSCC;
    
    console.log('[showDataEntryScreen] Current state:', state);
    console.log('[showDataEntryScreen] Using SSCC:', currentSSCC);
    
    // Перевіряємо наявність вибраного товару
    if (!selectedItem) {
        console.error('[showDataEntryScreen] selectedItem is missing in state:', state);
        showMessage('Товар не вибрано', 'error', 'receiving-item-screen');
        return;
    }
    
    // Перевіряємо наявність SSCC коду
    if (!currentSSCC) {
        console.error('[showDataEntryScreen] SSCC is missing in state:', state);
        showMessage('SSCC код не вибрано', 'error', 'receiving-item-screen');
        return;
    }
    
    // Показуємо екран введення даних
    showScreen('receiving-data-screen');
    
    // Оновлюємо стан у диспетчері клавіш - зберігаємо selectedItem та currentSSCC
    keyDispatcher.setTsdState({
        currentScreen: 'receiving-data-screen',
        currentInput: 'box-count-input',
        currentSSCC: currentSSCC, // Явно зберігаємо SSCC
        currentReceivingStep: 'data',
        selectedItem: selectedItem // Явно зберігаємо вибраний товар
    });
    
    clearInput();
    
    // Відображаємо SSCC код
    const ssccDisplay = document.getElementById('sscc-display');
    if (ssccDisplay) {
        ssccDisplay.textContent = currentSSCC || '';
    }
    
    // Оновлюємо екран з інформацією про вибраний товар
    const selectedItemInfo = document.getElementById('selected-item-info');
    if (selectedItemInfo && selectedItem) {
        selectedItemInfo.textContent = `${selectedItem.sku} - ${selectedItem.product_name}`;
    }
    
    // Відображаємо вагу брутто з даних SSCC
    const grossWeightDisplay = document.getElementById('gross-weight-display');
    if (grossWeightDisplay) {
        if (ssccData && ssccData.weight) {
            grossWeightDisplay.textContent = ssccData.weight.toFixed(2);
        } else {
            grossWeightDisplay.textContent = '0.00';
        }
    }
    
    // Перевіряємо, що стан правильно оновлено
    console.log('[showDataEntryScreen] Updated state:', keyDispatcher.getTsdState());
    
    // Встановлюємо фокус на перше поле введення після повного оновлення DOM
    setTimeout(() => {
        const firstInput = document.getElementById('box-count-input');
        if (firstInput) {
            setFocusedInput(firstInput);
        }
    }, 0);
}

// Handle data entry
function handleDataEntry() {
    // Отримуємо поточний стан з диспетчера клавіш
    const state = keyDispatcher.getTsdState();
    const selectedItem = state.selectedItem;
    const currentSSCC = state.currentSSCC;
    const tempPalletArray = state.tempPalletArray || [];
    
    console.log('[handleDataEntry] Current state:', state);
    console.log('[handleDataEntry] Using SSCC:', currentSSCC);
    
    if (!selectedItem) {
        showMessage('Товар не вибрано', 'error', 'receiving-data-screen');
        return;
    }
    
    if (!currentSSCC) {
        console.error('[handleDataEntry] SSCC is missing in state:', state);
        showMessage('SSCC код не вибрано', 'warning', 'receiving-data-screen');
        return;
    }
    
    // Get all the entered data
    const boxCount = parseInt(document.getElementById('box-count-input').textContent) || 0;
    const boxWeight = parseFloat(document.getElementById('box-weight-input').textContent) || 0;
    const palletWeight = parseFloat(document.getElementById('pallet-weight-input').textContent) || 0;
    
    // Get gross weight from SSCC data
    const grossWeight = ssccData && ssccData.weight ? ssccData.weight : 0;
    
    if (boxCount <= 0) {
        showMessage('Введіть кількість коробок', 'warning', 'receiving-data-screen');
        return;
    }
    
    if (boxWeight <= 0) {
        showMessage('Введіть вагу тари(ящика)', 'warning', 'receiving-data-screen');
        return;
    }
    
    if (palletWeight <= 0) {
        showMessage('Введіть вагу палети', 'warning', 'receiving-data-screen');
        return;
    }
    
    if (grossWeight <= 0) {
        showMessage('Помилка: вага брутто не отримана з SSCC', 'warning', 'receiving-data-screen');
        return;
    }
    
    // Calculate net weight based on packaging type
    let netWeight = 0;
    const packagingUnitType = selectedItem.packaging_unit_type || 'КГ';
    
    if (packagingUnitType === 'КГ') {
        netWeight = grossWeight - palletWeight - (boxWeight * boxCount);
    } else { // 'ШТ'
        netWeight = grossWeight - palletWeight - ((boxCount / (selectedItem.count || 1)) * boxWeight);
    }
    
    // Store the receiving data
    const receivingData = {
        sscc: currentSSCC,
        item_id: selectedItem.id,
        box_count: boxCount,
        gross_weight: grossWeight,
        pallet_weight: palletWeight,
        box_weight: boxWeight,
        net_weight: netWeight,
        packaging_unit_type: packagingUnitType
    };
    
    // Add to temporary array instead of sending to server immediately
    const updatedPalletArray = [...tempPalletArray, {...receivingData}];
    
    // Log the completed pallet data
    console.log('[handleDataEntry] Adding pallet data:', receivingData);
    console.log('[handleDataEntry] Updated pallet array:', updatedPalletArray);
    
    // Оновлюємо стан у диспетчері клавіш
    // We explicitly set currentSSCC to null here because we're done with this SSCC
    // and want to start with a fresh one in the next cycle
    // ВАЖЛИВО: Явно зберігаємо selectedItem для наступного циклу
    keyDispatcher.setTsdState({
        tempPalletArray: updatedPalletArray,
        currentReceivingStep: 'sscc',
        currentSSCC: null, // Явно очищаємо SSCC для наступної палети
        selectedItem: selectedItem // Явно зберігаємо вибраний товар між циклами
    });
    
    // Show success message with calculated net weight
    showMessage(`Палету додано. Вага нетто: ${netWeight.toFixed(2)} кг`, 'success', 'receiving-data-screen');
    
    // Reset for next entry
    ssccData = null;
    
    // Verify the state has been properly updated
    console.log('[handleDataEntry] Updated state:', keyDispatcher.getTsdState());
    
    // Return to SSCC entry for next pallet
    showSSCCEntryScreen();
}

// Обгортка для виклику функції saveBatchReceivingData з модуля receivingKeys
window.saveBatchReceivingData = async function() {
    const state = keyDispatcher.getTsdState();
    const success = await receivingKeys.saveBatchReceivingData(
        state.currentOrder,
        state.tempPalletArray,
        state.currentScreen || 'receiving-sscc-screen'
    );

    if (success) {
        keyDispatcher.setTsdState({
            tempPalletArray: [],
            currentSSCC: null,
            selectedItem: null
        });
        ssccData = null;
        handleReceivingComplete();
    }
};

// Handle receiving complete
function handleReceivingComplete() {
    // Reset all receiving data in keyDispatcher
    keyDispatcher.setTsdState({
        currentReceivingStep: 'invoice',
        currentOrder: null,
        currentSSCC: null,
        selectedItem: null,
        tempPalletArray: [],
        currentScreen: 'menu-screen'
    });
    
    // Reset local data
    ssccData = null;
    
    // Return to main menu
    showScreen('menu-screen');
    showMessage('Процес прийому завершено', 'success');
}

// Function to show confirmation prompt and save batch data
window.showConfirmationAndSave = function() {
    // Отримуємо поточний стан з диспетчера клавіш
    const state = keyDispatcher.getTsdState();
    const tempPalletArray = state.tempPalletArray || [];
    
    // Check if there are pallets to confirm
    if (tempPalletArray.length === 0) {
        showMessage('Немає палет для підтвердження', 'warning');
        return;
    }
    
    // Show confirmation prompt
    showConfirmationPrompt(
        `Підтвердити прийом ${tempPalletArray.length} палет?`,
        'F3 = Так, F4 = Ні',
        () => saveBatchReceivingData(),  // F3 callback
        () => showSSCCEntryScreen()      // F4 callback
    );
}

// Handle F4 key in receiving flow (cancel/back)
function handleReceivingF4() {
    // Get the current state
    const state = keyDispatcher.getTsdState();
    const currentReceivingStep = state.currentReceivingStep;
    const tempPalletArray = state.tempPalletArray || [];
    const currentSSCC = state.currentSSCC;
    
    console.log('[handleReceivingF4] Current state:', state);
    
    // Cancel current operation or go back
    switch (currentReceivingStep) {
        case 'invoice':
            // Return to main menu
            showScreen('menu-screen');
            break;
        case 'sscc':
            // If there are pallets in the array, ask for confirmation
            if (tempPalletArray.length > 0) {
                showConfirmationPrompt(
                    'Скасувати прийом? Всі незбережені дані будуть втрачені.',
                    'F3 = Так, F4 = Ні',
                    () => {
                        // Reset and return to main menu
                        keyDispatcher.setTsdState({
                            tempPalletArray: [],
                            currentSSCC: null
                        });
                        handleReceivingComplete();
                    },
                    () => showSSCCEntryScreen()
                );
            } else {
                // Go back to invoice screen
                keyDispatcher.setTsdState({
                    currentReceivingStep: 'invoice',
                    currentSSCC: null // Clear SSCC when going back to invoice screen
                });
                showReceivingStartScreen();
            }
            break;
        case 'item':
            // Go back to SSCC entry
            keyDispatcher.setTsdState({
                currentReceivingStep: 'sscc',
                // Preserve the currentSSCC when going back to SSCC entry
                currentSSCC: currentSSCC
            });
            showSSCCEntryScreen();
            break;
        case 'data':
            // Go back to item selection
            keyDispatcher.setTsdState({
                currentReceivingStep: 'item',
                // Preserve the currentSSCC when going back to item selection
                currentSSCC: currentSSCC
            });
            // Use the current SSCC from state instead of potentially undefined ssccCode variable
            showItemSelectionScreen(currentSSCC);
            break;
    }
}

// Show confirmation prompt
window.showConfirmationPrompt = function(message, instructions, confirmCallback, cancelCallback) {
    // Create or get confirmation overlay
    let overlay = document.getElementById('confirmation-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'confirmation-overlay';
        overlay.className = 'confirmation-overlay';
        document.body.appendChild(overlay);
    }
    
    // Set content
    overlay.innerHTML = `
        <div class="confirmation-box">
            <div class="confirmation-message">${message}</div>
            <div class="confirmation-instructions">${instructions}</div>
        </div>
    `;
    
    // Show overlay
    overlay.style.display = 'flex';
    
    // Store callbacks for F3/F4 handlers
    setTimeout(() => {
        window.confirmationCallbacks = {
            confirm: () => {
                hideConfirmationPrompt();
                if (confirmCallback) confirmCallback();
            },
            cancel: () => {
                hideConfirmationPrompt();
                if (cancelCallback) cancelCallback();
            }
        };
    }, 100); // 100 мс – час для DOM оновлення
};

// Hide confirmation prompt
function hideConfirmationPrompt() {
    const overlay = document.getElementById('confirmation-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
    window.confirmationCallbacks = null;
}

// Handle arrow keys in receiving flow
window.handleReceivingArrowKeys = function(direction) {
    const state = keyDispatcher.getTsdState();
    if (state.currentReceivingStep === 'item') {
        // In item selection, arrow keys navigate the list
        if (direction === 'ArrowUp') {
            navigateItemList('up');
        } else if (direction === 'ArrowDown') {
            navigateItemList('down');
        }
    }
}

// Initialize the module when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners for F3 and F4 keys
    document.addEventListener('keydown', function(event) {
        // F3 key
        if (event.key === 'F3' || event.keyCode === 114) {
            event.preventDefault();
            
            // If confirmation prompt is active, use its callback
            if (window.confirmationCallbacks) {
                window.confirmationCallbacks.confirm();
                return;
            }   else {
                const state = keyDispatcher.getTsdState();
                const result = receivingKeys.handleF3(state.currentScreen, state.currentReceivingStep, state.tempPalletArray);
                processReceivingResult(result); // 🔥 Цей виклик працює тільки якщо імпорт зроблено!
            }
        }

        // F4 key
        if (event.key === 'F4' || event.keyCode === 115) {
            event.preventDefault();
            
            // If confirmation prompt is active, use its callback
            if (window.confirmationCallbacks) {
                window.confirmationCallbacks.cancel();
                return;
            }
            
            // Otherwise handle based on current screen
            const state = keyDispatcher.getTsdState();
            if (state.currentScreen && state.currentScreen.startsWith('receiving-')) {
                handleReceivingF4();
            }
        }
    });
});