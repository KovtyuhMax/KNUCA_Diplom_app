// Модуль обробки клавіш для режиму приймання

// Імпортуємо базові функції обробки клавіш
import { showMessage } from './baseKeys.js';

// Обробка клавіші F1 в режимі приймання
export function handleF1(currentScreen, currentReceivingStep) {
    // Обробка в залежності від поточного екрану
    if (currentScreen === 'receiving-start-screen') {
        // Перевіряємо, чи заповнені всі поля
        const invoiceNumber = document.getElementById('invoice-number-input')?.textContent;
        const supplierInvoice = document.getElementById('supplier-invoice-input')?.textContent;
        
        if (!invoiceNumber || !supplierInvoice) {
            showMessage('Будь ласка, заповніть всі поля', 'error', currentScreen);
            return false;
        }
        
        // Повертаємо дію для підтвердження початку приймання
        return { action: 'function', function: 'confirmReceivingStart' };
    } else if (currentScreen === 'receiving-sscc-screen') {
        // Перевіряємо, чи введено SSCC код
        const ssccCode = document.getElementById('sscc-input')?.textContent;
        
        if (!ssccCode) {
            showMessage('Введіть SSCC код', 'warning', currentScreen);
            return false;
        }
        
        // Повертаємо дію для обробки SSCC коду
        return { action: 'function', function: 'handleSSCCEntry' };
    } else if (currentScreen === 'receiving-item-screen') {
        // Повертаємо дію для вибору товару
        return { action: 'function', function: 'handleItemSelection' };
    } else if (currentScreen === 'receiving-data-screen') {
        // Повертаємо дію для введення даних
        return { action: 'function', function: 'handleDataEntry' };
    }
    
    return false;
}

// Обробник клавіші F2 для режиму прийому
export function handleF2(currentScreen, currentReceivingStep) {
    // Повернення до меню з екранів прийому
    return { action: 'returnToMenu' };
}

// Обробка клавіші F3 в режимі приймання
export function handleF3(currentScreen, currentReceivingStep, tempPalletArray) {
    // Обробка в залежності від поточного екрану
    if (currentScreen === 'receiving-sscc-screen') {
        // Перевіряємо, чи є палети для підтвердження
        if (!tempPalletArray || tempPalletArray.length === 0) {
            showMessage('Немає палет для підтвердження', 'warning', currentScreen);
            return false;
        }
        
        // Повертаємо дію для виклику централізованої функції підтвердження
        return { action: 'triggerShowConfirmationAndSave' };
    }
    
    return false;
}

// Обробник клавіші F4 для режиму прийому (відміна підтвердження)
export function handleF4(currentScreen, currentReceivingStep) {
    // Відміна підтвердження
    if (currentScreen === 'receiving-sscc-screen') {
        return { action: 'cancelConfirmation' };
    }
    return { action: 'none' };
}

// Обробка стрілок в режимі приймання
export function handleArrow(key, currentScreen, currentReceivingStep) {
    // Обробка в залежності від поточного екрану
    if (currentScreen === 'receiving-item-screen') {
        // Навігація по списку товарів
        if (key === 'ArrowUp') {
            return { action: 'navigateItemList', direction: 'up' };
        } else if (key === 'ArrowDown') {
            return { action: 'navigateItemList', direction: 'down' };
        } else {
            return false;
        }
    } else if (currentScreen === 'receiving-data-screen' || currentScreen === 'receiving-sscc-screen' || currentScreen === 'receiving-start-screen') {
        // Навігація між полями введення
        const inputs = document.querySelectorAll(`#${currentScreen} .input-value`);
        if (!inputs || inputs.length === 0) return false;
        
        const focusedInput = document.querySelector(`#${currentScreen} .input-value.focused`);
        if (!focusedInput) return false;
        
        let currentIndex = Array.from(inputs).indexOf(focusedInput);
        let newIndex = currentIndex;
        
        if (key === 'ArrowUp') {
            newIndex = Math.max(0, currentIndex - 1);
        } else if (key === 'ArrowDown') {
            newIndex = Math.min(inputs.length - 1, currentIndex + 1);
        }
        
        if (newIndex !== currentIndex) {
            return { action: 'update', newFocusedInput: inputs[newIndex] };
        }
    }
    
    return false;
}

// Обробка сканування штрих-кодів в режимі приймання
export function handleBarcodeScan(barcode, currentScreen, currentReceivingStep) {
    // Обробка в залежності від поточного екрану
    if (currentScreen === 'receiving-start-screen') {
        // Сканування штрих-коду накладної
        return { action: 'function', function: 'processInvoiceBarcode', params: [barcode] };
    } else if (currentScreen === 'receiving-sscc-screen') {
        // Сканування штрих-коду SSCC
        return { action: 'function', function: 'processSSCCBarcode', params: [barcode] };
    } else if (currentScreen === 'receiving-item-screen') {
        // Сканування штрих-коду товару
        return { action: 'function', function: 'processItemBarcode', params: [barcode] };
    }
    
    return false;
}

// Збереження даних прийому
export async function saveBatchReceivingData(selectedOrder, tempPalletArray, currentScreen) {
    if (!tempPalletArray || tempPalletArray.length === 0) {
        showMessage('Немає даних для збереження', 'warning', currentScreen);
        return false;
    }
    
    // Перевіряємо наявність необхідних даних
    if (!selectedOrder || !selectedOrder.id || !selectedOrder.invoice_number) {
        showMessage('Помилка: дані замовлення відсутні', 'error', currentScreen);
        return false;
    }
    
    // Показуємо повідомлення про завантаження
    showMessage('Збереження даних...', 'info', currentScreen);
    
    try {
        // Отримуємо CSRF-токен
        let csrfToken = '';
        if (typeof window.getCsrfToken === 'function') {
            csrfToken = window.getCsrfToken();
        } else {
            csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
        }
        
        const response = await fetch('/tsd-emulator/api/save-receiving-batch', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                order_id: selectedOrder.id,
                invoice_number: selectedOrder.invoice_number,
                invoice_number_supplier: document.getElementById('supplier-invoice-input')?.textContent || '',
                pallets: tempPalletArray
            })
        });
        
        // Перевіряємо тип відповіді
        const contentType = response.headers.get('content-type');
        let data;
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            data = {
                success: false,
                message: 'Server returned non-JSON response. Status: ' + response.status
            };
        }
        
        if (data.success) {
            // Показуємо повідомлення про успіх
            showMessage(`Дані збережено. Кількість палет: ${tempPalletArray.length}`, 'success', currentScreen);
            return true;
        } else {
            showMessage(data.message || 'Помилка збереження даних', 'error', currentScreen);
            return false;
        }
    } catch (error) {
        console.error('Error:', error);
        showMessage("Помилка з'єднання з сервером: " + error.message, 'error', currentScreen);
        return false;
    }
}