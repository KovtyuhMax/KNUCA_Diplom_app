/**
 * Головний JavaScript файл для системи управління складом
 * Відповідає за ініціалізацію таблиць даних та інших базових функцій інтерфейсу
 */

// Відключення стандартних повідомлень про помилки DataTables для власної обробки
$.fn.dataTable.ext.errMode = 'none';

// Ініціалізація всіх компонентів після повного завантаження DOM
document.addEventListener('DOMContentLoaded', function() {
    // Перевірка наявності jQuery та бібліотеки DataTables
    if (typeof $ !== 'undefined' && $.fn.DataTable) {
        // Ініціалізація всіх таблиць з класом 'table' з налаштуваннями за замовчуванням
        $('table.table').DataTable({
            "responsive": true,
            "language": {
                "search": "Search:",
                "lengthMenu": "Show _MENU_ entries",
                "info": "Showing _START_ to _END_ of _TOTAL_ entries",
                "infoEmpty": "Showing 0 to 0 of 0 entries",
                "infoFiltered": "(filtered from _MAX_ total entries)"
            },
            "pageLength": 10,
            "dom": '<"top"fl>rt<"bottom"ip>'
        });
    }
    
    /**
     * Оновлення лічильника товарів з низьким запасом у навігаційній панелі
     * Отримує дані з API та оновлює відповідний індикатор
     */
    function updateLowStockCount() {
        fetch('/api/low_stock_count')
            .then(response => response.json())
            .then(data => {
                const lowStockBadge = document.getElementById('lowStockBadge');
                if (lowStockBadge) {
                    lowStockBadge.textContent = data.count;
                    if (data.count > 0) {
                        lowStockBadge.classList.remove('d-none');
                    } else {
                        lowStockBadge.classList.add('d-none');
                    }
                }
            })
            .catch(error => console.error('Error fetching low stock count:', error));
    }
    
    // Якщо на сторінці присутній індикатор низького запасу, ініціалізуємо його
    if (document.getElementById('lowStockBadge')) {
        // Початкове оновлення даних
        updateLowStockCount();
        // Налаштування автоматичного оновлення кожні 5 хвилин (300000 мс)
        setInterval(updateLowStockCount, 300000);
    }
    
    /**
     * Функція для показу модального вікна підтвердження видалення
     * @param {string} url - URL для відправки запиту на видалення
     * @param {string} name - Назва елемента, що видаляється
     */
    window.confirmDelete = function(url, name) {
        const deleteForm = document.getElementById('deleteForm');
        if (deleteForm) {
            deleteForm.action = url;
            const contractName = document.getElementById('contractName');
            if (contractName) {
                contractName.textContent = name;
            }
            const deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
            deleteModal.show();
        }
    };
    
    // Обробник зміни типу транзакції (отримання/відправлення)
    const transactionTypeSelect = document.getElementById('transaction_type');
    if (transactionTypeSelect) {
        transactionTypeSelect.addEventListener('change', function() {
            const quantityLabel = document.querySelector('label[for="quantity"]');
            if (this.value === 'receiving') {
                quantityLabel.textContent = 'Quantity to Receive';
            } else {
                quantityLabel.textContent = 'Quantity to Ship';
            }
        });
    }
    
    /**
     * Функціонал друку звіту
     * Додає обробник події для кнопки друку, який викликає стандартний діалог друку браузера
     */
    const printReportBtn = document.getElementById('printReport');
    if (printReportBtn) {
        printReportBtn.addEventListener('click', function() {
            window.print();
        });
    }
});