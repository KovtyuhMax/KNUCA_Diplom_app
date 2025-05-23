/**
 * Модуль терміналу комплектації складських замовлень
 * Відповідає за процес відбору товарів за замовленнями клієнтів
 * Реалізує інтерфейс користувача для комплектувальників
 */

// Імпортуємо диспетчер клавіш та модуль обробки клавіш для режиму відбору
import * as keyDispatcher from './tsd/keyDispatcher.js';
import * as pickingKeys from './tsd/keys/pickingKeys.js';

/**
 * Змінні стану процесу комплектації
 * Примітка: основний стан тепер керується через диспетчер клавіш,
 * ці змінні залишені для сумісності з існуючим кодом
 */
let currentOrder = null;      // Поточне замовлення
let currentSku = null;        // Поточний артикул товару
let currentSkuInfo = null;    // Інформація про поточний товар
let currentLotNumber = null;  // Номер поточного лота
let currentScreen = null;     // Поточний екран інтерфейсу
let currentItems = [];        // Масив всіх товарів у лоті
let currentIndex = 0;         // Індекс поточного товару в лоті

/**
 * Ініціалізація модуля комплектації при завантаженні сторінки
 * Налаштовує обробники подій та експортує необхідні функції
 */
document.addEventListener('DOMContentLoaded', function() {
    // Listen for picking start event
    document.addEventListener('pickingStart', function() {
        startPicking();
    });
    
    // Завантажуємо доступні лоти при ініціалізації
    loadAvailableLots();
    
    // Експортуємо функції для використання в диспетчері клавіш
    window.startPicking = startPicking;
    window.fetchOrderDetails = fetchOrderDetails;
    window.showCurrentItem = showCurrentItem;
    window.handlePickingF5 = handlePickingF5;
    window.handlePickingEnter = handlePickingEnter;
});


/**
 * Запуск процесу комплектації
 * Скидає всі змінні стану та відображає екран вибору лота
 */
function startPicking() {
    // Reset state
    currentOrder = null;
    currentSku = null;
    currentSkuInfo = null;
    currentLotNumber = null;
    currentItems = [];
    currentIndex = 0;
    
    // Оновлюємо стан у диспетчері клавіш
    keyDispatcher.setTsdState({
        currentOrder: null,
        currentSku: null,
        currentSkuInfo: null,
        currentLotNumber: null,
        currentItems: [],
        currentIndex: 0,
        currentScreen: 'picking-order-screen'
    });
    
    // Show lot input screen
    window.showScreen('picking-order-screen');
    
    // Оновлюємо заголовок екрану для сканування лота
    const screenTitle = document.querySelector('#picking-order-screen .screen-title');
    if (screenTitle) {
        screenTitle.textContent = 'Сканування лота';
    }
    
    // Оновлюємо підказку для введення лота
    const inputLabel = document.querySelector('#picking-order-screen .input-label');
    if (inputLabel) {
        inputLabel.textContent = 'Введіть або відскануйте номер лота:';
    }
    
    // Оновлюємо список доступних лотів
    loadAvailableLots();
}

/**
 * Обробник натискання клавіші F1 у режимі комплектації
 * Використовується для отримання довідкової інформації або допомоги
 */
window.handlePickingF1 = function() {
    // Отримуємо актуальний стан з диспетчера клавіш
    const state = keyDispatcher.getTsdState();
    
    // Викликаємо обробник F1 з модуля pickingKeys.js
    const result = pickingKeys.handleF1(
        state.currentScreen,
        state.currentOrder,
        state.currentSku,
        state.currentSkuInfo,
        state.currentItems,
        state.currentIndex,
        state.currentLotNumber
    );
    
    // Обробляємо результат через диспетчер
    console.log('[handlePickingF1] Calling processPickingResult with:', result);
    window.processPickingResult(result);
};

/**
 * Обробник натискання клавіші F5 у режимі комплектації
 * Використовується для переходу до наступного товару в списку
 */
window.handlePickingF5 = function() {
    // Отримуємо актуальний стан з диспетчера клавіш
    const state = keyDispatcher.getTsdState();
    
    // Викликаємо обробник F5 з модуля pickingKeys.js
    const result = pickingKeys.handleF5(
        state.currentScreen,
        state.currentItems,
        state.currentIndex,
        state.currentLotNumber
    );
    
    // Обробляємо результат через диспетчер
    console.log('[handlePickingF5] Calling processPickingResult with:', result);
    window.processPickingResult(result);
};

/**
 * Обробник натискання клавіші F2 у режимі комплектації
 * Використовується для повернення до головного меню
 */
window.handlePickingF2 = function() {
    // Отримуємо актуальний стан з диспетчера клавіш
    const state = keyDispatcher.getTsdState();
    currentScreen = state.currentScreen;
    
    // Додаємо підтвердження перед виходом з екрану комплектації
    if (currentScreen === 'picking-quantity-screen' || currentScreen === 'picking-result-screen') {
        if (confirm('Ви впевнені, що хочете вийти з режиму комплектації? Незбережений прогрес буде втрачено.')) {
            // Return to menu
            window.showScreen('menu-screen');
            window.selectMenuItem(0);
        }
    } else {
        // Для інших екранів просто повертаємось в меню без підтвердження
        window.showScreen('menu-screen');
        window.selectMenuItem(0);
    }
};

/**
 * Обробник натискання клавіші Enter у режимі комплектації
 * Підтверджує введені дані або виконує основну дію на поточному екрані
 */
window.handlePickingEnter = function () {
    // Отримуємо актуальний стан з диспетчера клавіш
    const state = keyDispatcher.getTsdState();
    
    console.log('[handlePickingEnter] Обробка Enter на екрані:', state.currentScreen);
    
    // Викликаємо обробник Enter з модуля pickingKeys.js
    const result = pickingKeys.handleEnter(
        state.currentScreen,
        state.currentItems,
        state.currentIndex,
        state.currentLotNumber
    );
    
    // Обробляємо результат через диспетчер
    console.log('[handlePickingEnter] Calling processPickingResult with:', result);
    window.processPickingResult(result);
};



/**
 * Отримує деталі замовлення з сервера за номером лота
 * @param {string} lotNumber - Номер лота для завантаження
 */
function fetchOrderDetails(lotNumber) {
    window.showMessage('Завантаження даних лота...', 'info');
    
    fetch('/tsd-emulator/picking/order', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ lot_number: lotNumber })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Store order and lot details
            if (data.lot_status === 'packed') {
                window.showMessage('Цей лот вже завершено', 'error');
                return;
            }
            currentOrder = {
                id: data.order_id || 0,
                order_number: data.order_number
            };
            currentLotNumber = data.lot_number;
            
            // Зберігаємо всі товари з лота
            // Явно додаємо order_id до кожного товару для забезпечення ізоляції між замовленнями
            currentItems = (data.items || []).map(item => ({
                ...item,
                order_id: data.order_id // Явно зберігаємо order_id для кожного товару
            }));
            currentIndex = 0; // Починаємо з першого товару
            
            // Оновлюємо стан у диспетчері клавіш
            keyDispatcher.setTsdState({
                currentOrder,
                currentLotNumber,
                currentItems,
                currentIndex
            });
            
            // Якщо в лоті немає товарів, показуємо повідомлення
            if (currentItems.length === 0) {
                window.showMessage('Лот не містить товарів', 'error');
                return;
            }
            
            // Показуємо інформацію про поточний товар
            showCurrentItem();
        } else {
            window.showMessage(data.message || 'Помилка завантаження даних лота', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        window.showMessage('Помилка з\'єднання з сервером', 'error');
    });
}

// Функція для відображення інформації про поточний товар
function showCurrentItem() {
    // Отримуємо актуальний стан з диспетчера клавіш
    const state = keyDispatcher.getTsdState();
    currentItems = state.currentItems;
    currentIndex = state.currentIndex;
    
    // Отримуємо поточний товар з масиву
    const item = currentItems[currentIndex];
    
    // Зберігаємо інформацію про поточний товар
    currentSku = item.sku;
    currentSkuInfo = {
        sku: item.sku,
        name: item.product_name,
        quantity: item.quantity,
        picked_quantity: item.picked_quantity || 0,
        location: item.location || 'Не вказано' // Додаємо інформацію про адресу зберігання
    };
    
    // Оновлюємо стан у диспетчері клавіш
    keyDispatcher.setTsdState({
        currentSku,
        currentSkuInfo,
        currentScreen: 'picking-quantity-screen'
    });
    
    // Відображаємо інформацію про товар з виділеною адресою зберігання
    const skuInfo = document.getElementById('sku-info');
    skuInfo.innerHTML = `
        <div>Товар: ${currentSkuInfo.sku}</div>
        <div>Назва: ${currentSkuInfo.name || 'Невідомо'}</div>
        <div>Потрібно: ${currentSkuInfo.quantity} шт.</div>
        <div>Відібрано: ${currentSkuInfo.picked_quantity || 0} шт.</div>
        <div>Залишилось: ${currentSkuInfo.quantity - (currentSkuInfo.picked_quantity || 0)} шт.</div>
        <div class="storage-location"><strong>Адреса: ${currentSkuInfo.location}</strong></div>
    `;
    
    // Очищаємо поле введення кількості
    document.getElementById('picking-quantity-input').textContent = '';
    
    // Переходимо до екрану введення кількості
    window.showScreen('picking-quantity-screen');
    
    // Оновлюємо повідомлення на екрані з інструкцією про F5
    const screenMessage = document.querySelector('#picking-quantity-screen .screen-message');
    if (screenMessage) {
        screenMessage.textContent = 'Введіть кількість з клавіатури та натисніть Enter';
    }
}

// Perform picking operation
window.performPicking = function(quantity, progressFlow, lotNumber) {
    const state = keyDispatcher.getTsdState();
    const currentOrder = state.currentOrder;
    const currentSku = state.currentSku;
    const currentItems = state.currentItems;
    const currentIndex = state.currentIndex;
    const currentLotNumber = lotNumber || state.currentLotNumber;
    
    console.log('performPicking called with:', quantity, 'progressFlow:', progressFlow, 'lotNumber:', currentLotNumber);
    if (!currentOrder || !currentSku || !currentLotNumber) {
        window.showMessage('Помилка: Дані замовлення, товару або лоту відсутні', 'error');
        return;
    }
    
    // Перевіряємо, що кількість є числом
    if (isNaN(quantity) || quantity <= 0) {
        window.showMessage('Введіть коректну кількість з клавіатури', 'error');
        return;
    }
    
    // Validate quantity
    const currentSkuInfo = state.currentSkuInfo;
    const remaining = currentSkuInfo.quantity - (currentSkuInfo.picked_quantity || 0);
    if (quantity > remaining) {
        window.showMessage(`Кількість перевищує необхідну. Максимум: ${remaining}`, 'error');
        return;
    }
    
    window.showMessage('Виконується комплектація...', 'info');
    
    
    console.log('Sending performPicking payload:', {
        order_id: currentOrder.id,
        sku: currentSku,
        requested_quantity: quantity,
        lot_number: currentLotNumber
    });
    
    fetch('/tsd-emulator/picking/perform', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            order_id: currentOrder.id,
            sku: currentSku,
            requested_quantity: quantity,
            lot_number: currentLotNumber
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Server returned ' + response.status);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Перевіряємо, чи фактично було відібрано товар
            if (data.actual_quantity === 0) {
                window.showMessage('Не вдалося відібрати жодного ящика товару', 'error');
                return;
            }
            
            // Update the picked quantity in current item info
            const updatedSkuInfo = {
                ...currentSkuInfo,
                picked_quantity: (currentSkuInfo.picked_quantity || 0) + quantity
            };
            
            // Оновлюємо кількість відібраного товару в масиві currentItems
            // Переконуємося, що оновлюємо тільки товари з поточного замовлення
            const updatedItems = [...currentItems];
            if (updatedItems[currentIndex]) {
                updatedItems[currentIndex].picked_quantity = updatedSkuInfo.picked_quantity;
                // Явно зберігаємо order_id для кожного товару для забезпечення ізоляції між замовленнями
                updatedItems[currentIndex].order_id = currentOrder.id;
                
                // Виводимо інформацію про оновлення кількості для діагностики
                console.log(`Оновлено кількість для SKU ${updatedItems[currentIndex].sku}: ${updatedItems[currentIndex].picked_quantity} з ${updatedItems[currentIndex].quantity}`);
            }
            
            // Оновлюємо стан у диспетчері клавіш
            keyDispatcher.setTsdState({
                currentSku: updatedSkuInfo.sku,
                currentSkuInfo: updatedSkuInfo,
                currentItems: updatedItems
            });
            
            // Display result
            const resultElement = document.getElementById('picking-result');
            const pickedItems = Array.isArray(data.picked_items) ? data.picked_items : [];
            
            resultElement.innerHTML = `
                <div class="result-success">Товар успішно відібрано</div>
                <div>SKU: ${currentSku}</div>
                <div>Назва: ${updatedSkuInfo.name}</div>
                <div>Кількість: ${quantity} шт.</div>
                ${data.underpicked ? '<div class="warning">Відібрано менше ніж запитано!</div>' : ''}
                ${pickedItems.map(item => `
                    <div class="picked-item">
                        <div>SSCC: ${item.sscc}</div>
                        <div>Місце: ${item.location}</div>
                        <div>Кількість: ${item.box_count} шт.</div>
                        <div>Вага: ${item.weight.toFixed(2)} кг</div>
                    </div>
                `).join('')}
            `;
            
            // Додаємо підказку про натискання F5 для продовження
            if (currentIndex < currentItems.length - 1) {
                resultElement.innerHTML += `
                    <div class="next-item-hint">Натисніть F1 для переходу до наступного товару</div>
                `;
            } else {
                resultElement.innerHTML += `
                    <div class="all-picked">Це останній товар у лоті</div>
                    <div class="next-item-hint">Натисніть F1 для завершення лота</div>
                `;
            }
            
            // Show result screen
            window.showScreen('picking-result-screen');
            keyDispatcher.setTsdState({ currentScreen: 'picking-result-screen' });
            
            // Оновлюємо повідомлення на екрані
            const screenMessage = document.querySelector('#picking-result-screen .screen-message');
            if (screenMessage) {
                screenMessage.textContent = 'Натисніть F1 для продовження або F2 для повернення в меню';
            }
            
            // If all items are picked, update order status
            if (data.all_items_picked) {
                keyDispatcher.setTsdState({
                    currentOrder: {
                        ...currentOrder,
                        status: 'packed'
                    }
                });
            }
            
            // Якщо встановлено прапорець progressFlow, автоматично переходимо до наступного товару
            if (progressFlow) {
                console.log('[performPicking] progressFlow is true, automatically moving to next item');
                // Викликаємо F5 для переходу до наступного товару
                setTimeout(() => {
                    window.handlePickingF5();
                }, 5000); // Невелика затримка для відображення результату
            }
        } else {
            window.showMessage(data.message || 'Помилка комплектації', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        window.showMessage('Помилка з\'єднання з сервером', 'error');
    });
}

// Helper function to get human-readable status
function getStatusText(status) {
    const statusMap = {
        'created': 'Створено',
        'processing': 'В обробці',
        'assembling': 'Комплектується',
        'packed': 'Скомплектовано',
        'completed': 'Завершено',
        'cancelled': 'Скасовано'
    };
    
    return statusMap[status] || status;
}

// Функція для завершення лота та оновлення його статусу в базі даних
window.completeLot = function(lotNumber) {
    if (!lotNumber) {
        window.showMessage('Помилка: Номер лота не вказано', 'error');
        return;
    }
    
    window.showMessage('Завершення лота...', 'info');
    
    // Отримуємо актуальний стан з диспетчера клавіш
    const state = keyDispatcher.getTsdState();
    const currentItems = state.currentItems;
    const currentIndex = state.currentIndex;
    
    // Перевіряємо, чи всі товари відібрані перед відправкою запиту на сервер
    let allItemsPicked = true;
    let notPickedItems = [];
    
    for (const item of currentItems) {
        if (item.picked_quantity < item.quantity) {
            allItemsPicked = false;
            notPickedItems.push(`${item.sku} (відібрано ${item.picked_quantity} з ${item.quantity})`);
        }
    }
    
    // Якщо не всі товари відібрані, показуємо повідомлення і не відправляємо запит
    if (!allItemsPicked) {
        const message = `Не всі товари з лота зібрані. Незібрані товари: ${notPickedItems.join(', ')}`;
        window.showMessage(message, 'error');
        
        // Показуємо детальну інформацію на екрані
        const resultElement = document.getElementById('picking-result');
        if (resultElement) {
            resultElement.innerHTML = `
                <div class="result-error">Лот не може бути завершено</div>
                <div>Не всі товари з лота ${lotNumber} відібрані</div>
                <div>Незібрані товари:</div>
                <ul>
                    ${notPickedItems.map(item => `<li>${item}</li>`).join('')}
                </ul>
                <div>Будь ласка, завершіть відбір всіх товарів перед завершенням лота</div>
            `;
        }
        return;
    }
    
    fetch('/tsd-emulator/picking/complete-lot', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ lot_number: lotNumber })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Оновлюємо інформацію на екрані
            const resultElement = document.getElementById('picking-result');
            if (resultElement) {
                resultElement.innerHTML = `
                    <div class="result-success">Лот успішно завершено</div>
                    <div>Всі товари з лота ${lotNumber} успішно відібрані</div>
                    <div>Статус лота: ${getStatusText('packed')}</div>
                `;
                
            }
            
            
            // Оновлюємо повідомлення на екрані
            const screenMessage = document.querySelector('#picking-result-screen .screen-message');
            if (screenMessage) {
                screenMessage.textContent = 'Натисніть F2 для повернення в меню';
                loadAvailableLots();
                document.getElementById('picking-order-input').innerHTML = '';
            }
            
            window.showMessage('Лот успішно завершено', 'success');
            keyDispatcher.setTsdState({
                currentOrder: null,
                currentLotNumber: null,
                currentItems: [],
                currentSku: null,
                currentSkuInfo: null,
                currentIndex: 0
            });
        } else {
            window.showMessage(data.message || 'Помилка завершення лота', 'error');
            
            // Показуємо детальну інформацію про помилку на екрані
            const resultElement = document.getElementById('picking-result');
            if (resultElement) {
                resultElement.innerHTML = `
                    <div class="result-error">Помилка завершення лота</div>
                    <div>${data.message || 'Невідома помилка'}</div>
                    <div>Будь ласка, перевірте, що всі товари відібрані правильно</div>
                `;
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        window.showMessage('Помилка з\'єднання з сервером', 'error');
    });
}

// Update the navigateToOption function in tsd-emulator.js to use this module
window.navigateToPickingOption = function() {
    // Start the picking process
    document.dispatchEvent(new Event('pickingStart'));
};

function loadAvailableLots() {
    fetch('/tsd-emulator/picking/available-lots')
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          const lotSelect = document.getElementById('lotSelector');
          lotSelect.innerHTML = '';
  
          data.lots.forEach(lot => {
            const option = document.createElement('option');
            option.value = lot.lot_number;
            option.textContent = `${lot.lot_number} (${lot.sku_list.join(', ')})`;
            lotSelect.appendChild(option);
          });
          const currentScreen = keyDispatcher.getTsdState().currentScreen;

          if (data.lots.length === 1 && currentScreen === 'picking-order-screen') {
            const singleLot = data.lots[0].lot_number;
            document.getElementById('picking-order-input').textContent = singleLot;
            fetchOrderDetails(singleLot);
          }
        }
      });
  }

window.onLotSelected = function () {
  const lot = document.getElementById('lotSelector').value;
  if (lot) {
    // Автоматично заповнюємо поле введення обраним значенням
    document.getElementById('picking-order-input').textContent = lot;
    
    // Викликаємо функцію обробки штрих-коду
    fetchOrderDetails(lot);
  }
}