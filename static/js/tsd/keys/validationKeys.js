// Модуль для обробки клавіш у режимі валідації (validation)

import { showMessage } from './baseKeys.js';

// Обробник клавіші F1 для режиму валідації
export function handleF1(currentScreen) {
    if (currentScreen === 'validation-invoice-screen') {
        // Підтвердження номеру накладної
        const invoiceNumber = document.getElementById('validation-invoice-input').textContent;
        if (invoiceNumber) {
            return { action: 'validateInvoiceNumber', invoiceNumber };
        } else {
            showMessage('Введіть номер накладної', 'error', currentScreen);
            return { action: 'showError' };
        }
    } else if (currentScreen === 'validation-sscc-screen') {
        // Підтвердження SSCC коду
        const ssccCode = document.getElementById('validation-sscc-input').textContent;
        if (ssccCode) {
            return { action: 'validateSSCC', ssccCode };
        } else {
            showMessage('Введіть SSCC код', 'error', currentScreen);
            return { action: 'showError' };
        }
    }
    return { action: 'none' };
}

// Обробник клавіші F2 для режиму валідації
export function handleF2(currentScreen) {
    // Повернення до меню з екранів валідації
    return { action: 'returnToMenu' };
}

// Обробник клавіші Enter для режиму валідації
export function handleEnter(currentScreen) {
    // Обробка клавіші Enter для підтвердження введених даних
    return handleF1(currentScreen);
}

// Функція для обробки сканування штрих-коду в режимі валідації
export function handleBarcodeScan(barcode, currentScreen) {
    if (currentScreen === 'validation-invoice-screen') {
        // Обробка сканування номеру накладної
        document.getElementById('validation-invoice-input').textContent = barcode;
        return { action: 'validateInvoiceNumber', invoiceNumber: barcode };
    } else if (currentScreen === 'validation-sscc-screen') {
        // Обробка сканування SSCC коду
        document.getElementById('validation-sscc-input').textContent = barcode;
        return { action: 'validateSSCC', ssccCode: barcode };
    }
    return { action: 'none' };
}