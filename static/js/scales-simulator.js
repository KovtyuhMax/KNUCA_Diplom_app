/**
 * Модуль симулятора ваг для складської системи
 * Емулює роботу промислових ваг для зважування товарів та генерації SSCC кодів
 */

/**
 * Отримує CSRF токен з мета-тегу для захисту від CSRF атак
 * @returns {string} CSRF токен для використання в запитах
 */
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

document.addEventListener('DOMContentLoaded', function() {
    /**
     * Ініціалізація елементів інтерфейсу симулятора ваг
     * Отримуємо посилання на всі необхідні DOM елементи для подальшої роботи
     */
    const weightInput = document.getElementById('weight-input');
    const weightValue = document.getElementById('weight-value');
    const generateSsccBtn = document.getElementById('generate-sscc-btn');
    const weighingResult = document.getElementById('weighing-result');
    const printLabelBtn = document.getElementById('print-label-btn');
    
    /**
     * Оновлення відображення ваги при зміні значення в полі введення
     * Конвертує введене значення у формат з двома десятковими знаками
     */
    weightInput.addEventListener('input', function() {
        const value = parseFloat(this.value) || 0;
        weightValue.textContent = value.toFixed(2);
    });
    
    /**
     * Обробник події для генерації SSCC коду при натисканні кнопки
     * Відправляє запит на сервер для створення унікального SSCC та даних етикетки
     */
    generateSsccBtn.addEventListener('click', function() {
        const weight = weightInput.value;
        
        if (!weight || isNaN(parseFloat(weight))) {
            alert('Будь ласка, введіть коректне значення ваги');
            return;
        }
        
        // Call the backend API to generate SSCC and label data
        fetch('/scales/generate-sscc', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ weight: weight })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update label preview with data from server
                document.getElementById('sscc-display').textContent = `SSCC: ${data.sscc}`;
                document.getElementById('label-sscc').textContent = data.sscc;
                document.getElementById('label-weight').textContent = data.weight;
                document.getElementById('label-date').textContent = data.date_time;
                
                // Generate barcode using JsBarcode
                const barcodeContainer = document.getElementById('barcode-container');
                barcodeContainer.innerHTML = '<svg id="barcode"></svg>';
                JsBarcode("#barcode", data.sscc, {
                    format: "CODE128",
                    width: 2,
                    height: 50,
                    displayValue: true,
                    fontSize: 12,
                    margin: 10
                });
                
                // Show the weighing result section
                weighingResult.style.display = 'block';
                
                // Set up print button event with wait function
                waitForPrintButton(() => {
                    setupPrintButton(data.sscc, data.weight, data.date_time);
                });
            } else {
                // Show error message
                alert(data.message || 'Помилка при генерації етикетки');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert("Помилка з'єднання з сервером");
        });
    });
    
    /**
     * Функція для очікування появи кнопки друку в DOM
     * Використовує інтервал для періодичної перевірки наявності елемента
     * @param {Function} callback - Функція, яка буде викликана після появи кнопки
     */
    function waitForPrintButton(callback) {
        const check = setInterval(() => {
            const btn = document.getElementById('print-label-btn');
            if (btn) {
                clearInterval(check);
                callback(btn);
            }
        }, 50);
    }
    
    /**
     * Налаштування функціональності кнопки друку етикетки
     * @param {string} sscc - Згенерований SSCC код
     * @param {string} weight - Вага товару
     * @param {string} dateTime - Дата та час зважування
     */
    function setupPrintButton(sscc, weight, dateTime) {
        // Wait for the print button to be available in DOM
        waitForPrintButton((printBtn) => {
            // Remove any existing event listeners by cloning
            const newPrintButton = printBtn.cloneNode(true);
            printBtn.parentNode.replaceChild(newPrintButton, printBtn);
            
            // Add click event listener to the new button
            newPrintButton.addEventListener('click', function() {
            // Create a new window with the label content
            const printWindow = window.open('', '_blank');
            printWindow.document.write(`
                <html>
                <head>
                    <title>SSCC Label</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        .label { border: 1px solid #000; padding: 15px; max-width: 300px; }
                        .label-title { text-align: center; font-weight: bold; margin-bottom: 10px; }
                        .label-row { margin-bottom: 5px; }
                        .barcode { text-align: center; margin: 15px 0; }
                    </style>
                    <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
                </head>
                <body>
                    <div class="label">
                        <div class="label-title">Етикетка палети</div>
                        <div class="label-row"><strong>SSCC:</strong> ${sscc}</div>
                        <div class="label-row"><strong>Вага брутто:</strong> ${weight} кг</div>
                        <div class="label-row"><strong>Дата:</strong> ${dateTime}</div>
                        <div class="barcode">
                            <svg id="printBarcode"></svg>
                        </div>
                    </div>
                    <script>
                        // Generate barcode
                        JsBarcode("#printBarcode", "${sscc}", {
                            format: "CODE128",
                            width: 2,
                            height: 50,
                            displayValue: true,
                            fontSize: 12,
                            margin: 10
                        });
                        
                        // Auto print
                        window.onload = function() {
                            window.print();
                        }
                    </script>
                </body>
                </html>
            `);
            printWindow.document.close();
        });
        });
    }
});