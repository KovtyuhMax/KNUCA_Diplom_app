/**
 * Модуль валідації товарів на терміналі збору даних (TSD)
 * Відповідає за перевірку правильності товарів при прийманні та інвентаризації
 */

// Імпортуємо диспетчер клавіш для керування станом та обробки введення
import * as keyDispatcher from './tsd/keyDispatcher.js';

/**
 * Ініціалізація модуля валідації при завантаженні сторінки
 * Налаштовує обробники подій та експортує необхідні функції
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('TSD Validation module initialized');
    
    // Експортуємо функції для використання в диспетчері клавіш
    window.validateInvoiceNumber = validateInvoiceNumber;
    window.validateSSCC = validateSSCC;
    window.handleValidationBarcodeScan = handleValidationBarcodeScan;
    
    // Слухаємо подію початку валідації
    document.addEventListener('validationStart', function() {
        startValidation();
    });
});

/**
 * Обробляє сканування штрих-кодів у режимі валідації
 * Розпізнає тип штрих-коду та перенаправляє на відповідний обробник
 * @param {string} barcode - Відсканований штрих-код
 * @param {string} screenId - Ідентифікатор поточного екрану
 */
function handleValidationBarcodeScan(barcode, screenId) {
    console.log(`Отримано штрих-код у режимі валідації: ${barcode} на екрані ${screenId}`);
    
    // Обробляємо штрих-код в залежності від поточного екрану
    if (screenId.includes('validation-invoice')) {
        // Обробка штрих-коду накладної
        processValidationInvoiceBarcode(barcode);
    } else if (screenId.includes('validation-sscc')) {
        // Обробка штрих-коду SSCC
        processValidationSSCCBarcode(barcode);
    }
}

/**
 * Обробляє штрих-код накладної у режимі валідації
 * Перевіряє формат та встановлює значення у відповідне поле
 * @param {string} barcode - Відсканований штрих-код накладної
 */
function processValidationInvoiceBarcode(barcode) {
    console.log(`Обробка штрих-коду накладної для валідації: ${barcode}`);
    
    // Перевіряємо формат штрих-коду накладної
    if (barcode.startsWith('INV')) {
        // Отримуємо номер накладної з штрих-коду
        const invoiceNumber = barcode.substring(3);
        
        // Встановлюємо значення в поле введення
        const invoiceInput = document.getElementById('validation-invoice-input');
        if (invoiceInput) {
            invoiceInput.textContent = invoiceNumber;
            
            // Оновлюємо стан у диспетчері клавіш
            keyDispatcher.setTsdState({
                currentInput: 'validation-invoice-input'
            });
            
            // Автоматично перевіряємо накладну
            validateInvoiceNumber(invoiceNumber);
        }
    } else {
        // Показуємо повідомлення про невірний формат
        window.showMessage('Невірний формат штрих-коду накладної', 'error');
    }
}

/**
 * Обробляє штрих-код SSCC у режимі валідації
 * Перевіряє формат та встановлює значення у відповідне поле
 * @param {string} barcode - Відсканований штрих-код SSCC
 */
function processValidationSSCCBarcode(barcode) {
    console.log(`Обробка штрих-коду SSCC для валідації: ${barcode}`);
    
    // Перевіряємо формат штрих-коду SSCC
    if (barcode.startsWith('00') && barcode.length === 18) {
        // Встановлюємо значення в поле введення
        const ssccInput = document.getElementById('validation-sscc-input');
        if (ssccInput) {
            ssccInput.textContent = barcode;
            
            // Оновлюємо стан у диспетчері клавіш
            keyDispatcher.setTsdState({
                currentInput: 'validation-sscc-input',
                currentSSCC: barcode
            });
            
            // Автоматично перевіряємо SSCC
            validateSSCC(barcode);
        }
    } else {
        // Показуємо повідомлення про невірний формат
        window.showMessage('Невірний формат штрих-коду SSCC', 'error');
    }
}

/**
 * Запускає процес валідації товарів
 * Скидає стан та відображає початковий екран валідації
 */
function startValidation() {
    // Оновлюємо стан у диспетчері клавіш
    keyDispatcher.setTsdState({
        currentScreen: 'validation-invoice-screen'
    });
    
    // Показуємо екран валідації накладної
    window.showScreen('validation-invoice-screen');
}

// Function to validate invoice number
window.validateInvoiceNumber = async function(invoiceNumber) {
    if (!invoiceNumber || invoiceNumber.trim() === '') {
        showMessage('Введіть номер накладної', 'warning');
        return false;
    }
    
    try {
        const response = await fetch('/validation/check-invoice', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ invoice_number: invoiceNumber })
        });
        
        const data = await response.json();
        
        if (!data.valid) {
            showMessage(data.message, 'error');
            return false;
        }
        
        return true;
    } catch (error) {
        console.error('Error validating invoice number:', error);
        showMessage("Помилка перевірки номера накладної", 'error');
        return false;
    }
}

// Function to validate SSCC code
window.validateSSCC = async function(ssccCode) {
    if (!ssccCode || ssccCode.trim() === '') {
        showMessage('Введіть SSCC код', 'warning');
        return false;
    }
    
    try {
        const response = await fetch('/validation/validate-sscc', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ sscc: ssccCode })
        });
        
        const data = await response.json();
        
        if (!data.valid) {
            showMessage(data.message, 'error');
            return false;
        }
        
        return true;
    } catch (error) {
        console.error('Error validating SSCC code:', error);
        showMessage("Помилка перевірки SSCC коду", 'error');
        return false;
    }
}

// Функції валідації вже інтегровані в оригінальні функції в tsd-receiving.js
// Тому немає потреби перевизначати їх тут