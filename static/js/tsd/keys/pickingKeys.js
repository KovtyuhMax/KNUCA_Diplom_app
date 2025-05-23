// Модуль для обробки клавіш у режимі відбору товарів (picking)

import { showMessage } from './baseKeys.js';

// Обробник клавіші F1 для режиму відбору
export function handleF1(currentScreen, currentOrder, currentSku, currentSkuInfo, currentItems, currentIndex, currentLotNumber) {
    if (currentScreen === 'picking-screen') {
        // Запуск процесу відбору
        return { action: 'startPicking' };
    } else if (currentScreen === 'picking-order-screen') {
        // Підтвердження номеру лота
        const lotNumber = document.getElementById('picking-order-input').textContent;
        if (lotNumber) {
            return { action: 'fetchOrderDetails', lotNumber };
        } else {
            showMessage('Введіть номер лота', 'error', currentScreen);
            return { action: 'showError' };
        }
    } else if (currentScreen === 'picking-quantity-screen') {
        // Підтвердження кількості та перехід до наступного товару або завершення лота
        const quantity = document.getElementById('picking-quantity-input').textContent.trim();
        if (quantity && !isNaN(parseInt(quantity))) {
            console.log('[handlePickingEnter] Обробка F1 на екрані:', currentScreen);
            // Спочатку виконуємо відбір з введеною кількістю
            return { 
                action: 'performPicking', 
                quantity: parseInt(quantity),
                // Додаємо параметр lot_number для фільтрації по конкретному лоту
                lotNumber: currentLotNumber,
                // Додаємо параметри для подальшої обробки після performPicking
                progressFlow: true  // Прапорець для індикації, що потрібно перейти до наступного товару або завершити лот
            };
        } else {
            showMessage('Введіть коректну кількість', 'error', currentScreen);
            console.log('[handlePickingEnter] Обробка F1:', currentScreen);
            return { action: 'showError' };
        }
    } else if (currentScreen === 'picking-result-screen') {
        // Перевіряємо, чи є ще товари в лоті
        if (currentIndex < currentItems.length - 1) {
            // Переходимо до наступного товару
            return { action: 'nextItem', newIndex: currentIndex + 1 };
        } else {
            // Якщо це був останній товар, показуємо повідомлення про завершення лота
            return { action: 'completeLot', lotNumber: currentLotNumber };
        }
    }
    return { action: 'none' };
}

// Обробник клавіші F2 для режиму відбору
export function handleF2(currentScreen) {
    // Додаємо підтвердження перед виходом з екрану комплектації
    if (currentScreen === 'picking-quantity-screen' || currentScreen === 'picking-result-screen') {
        return { action: 'confirmExit' };
    } else {
        // Для інших екранів просто повертаємось в меню без підтвердження
        return { action: 'returnToMenu' };
    }
}

// Обробник клавіші F5 для режиму відбору
export function handleF5(currentScreen, currentItems, currentIndex, currentLotNumber) {
    // Для екранів picking-result-screen та picking-quantity-screen використовуємо ту ж логіку, що і в F1
    // для забезпечення сумісності з існуючим кодом
    if (currentScreen === 'picking-result-screen' || currentScreen === 'picking-quantity-screen') {
        // Якщо це останній товар у лоті, перевіряємо, чи всі товари відібрані
        if (currentIndex >= currentItems.length - 1 && currentScreen === 'picking-result-screen') {
            // Перевіряємо, чи всі товари відібрані
            let allItemsPicked = true;
            let notPickedItems = [];
            
            for (const item of currentItems) {
                if (item.picked_quantity < item.quantity) {
                    allItemsPicked = false;
                    notPickedItems.push(`${item.sku} (відібрано ${item.picked_quantity} з ${item.quantity})`);
                }
            }
            
            // Якщо не всі товари відібрані, показуємо повідомлення і не дозволяємо завершити лот
            if (!allItemsPicked) {
                const message = `Не всі товари з лота зібрані. Незібрані товари: ${notPickedItems.join(', ')}`;
                console.log(message);
                return { 
                    action: 'showError', 
                    message: message 
                };
            }
        }
        
        // Викликаємо handleF1 з тими ж параметрами для уникнення дублювання коду
        // Передаємо null для параметрів, які не використовуються в цьому контексті
        return handleF1(currentScreen, null, null, null, currentItems, currentIndex, currentLotNumber);
    }
    return { action: 'none' };
}

// Обробник клавіші Enter для режиму відбору
export function handleEnter(currentScreen, currentItems, currentIndex, currentLotNumber) {
    // Обробка клавіші Enter для підтвердження введеної кількості
    if (currentScreen === 'picking-quantity-screen') {
        const quantity = document.getElementById('picking-quantity-input').textContent.trim();
        if (quantity && !isNaN(parseInt(quantity))) {
            console.log('[handlePickingEnter] Обробка Enter на екрані:', currentScreen);
            return { 
                action: 'performPicking', 
                quantity: parseInt(quantity),
                // Додаємо параметр lot_number для фільтрації по конкретному лоту
                lotNumber: currentLotNumber,
                // Додаємо параметри для подальшої обробки після performPicking
                progressFlow: true  // Прапорець для індикації, що потрібно перейти до наступного товару або завершити лот
            };
        } else {
            showMessage('Введіть коректну кількість з клавіатури', 'error', currentScreen);
            console.log('[handlePickingEnter] Ентер працює.:');
            return { action: 'showError' };
        }
    } else if (currentScreen === 'picking-result-screen') {
        // Перевіряємо, чи є ще товари в лоті
        if (currentIndex < currentItems.length - 1) {
            // Переходимо до наступного товару
            return { action: 'nextItem', newIndex: currentIndex + 1 };
        } else {
            // Якщо це був останній товар, показуємо повідомлення про завершення лота
            return { action: 'completeLot', lotNumber: currentLotNumber };
        }
    }
    return { action: 'none' };
}

// Функція для обробки сканування штрих-коду в режимі відбору
export function handleBarcodeScan(barcode, currentScreen) {
    if (currentScreen === 'picking-order-screen') {
        // Обробка сканування номеру лота
        document.getElementById('picking-order-input').textContent = barcode;
        return { action: 'fetchOrderDetails', lotNumber: barcode };
    } else if (currentScreen === 'picking-quantity-screen') {
        // Кількість вводиться з клавіатури, не сканується
        showMessage('Введіть кількість за допомогою клавіатури', 'info', currentScreen);
        return { action: 'showInfo' };
    }
    return { action: 'none' };
}