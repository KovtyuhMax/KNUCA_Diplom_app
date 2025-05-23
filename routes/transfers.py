from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models.pending_transfer import PendingTransferRequest
from models.storage import StorageLocation
from extensions import db
from utils.decorators import position_required

# Визначаємо позиції, які мають доступ до управління переміщеннями
TRANSFER_ACCESS_POSITIONS = ['Оператор', 'Начальник зміни', 'Керівник']

transfers_bp = Blueprint('transfers', __name__)

@transfers_bp.route('/pending-transfers')
@login_required
@position_required(TRANSFER_ACCESS_POSITIONS)
def pending_transfers_list():
    """Відображає список незавершених запитів на переміщення"""
    # Отримуємо всі незавершені запити на переміщення
    pending_transfers = PendingTransferRequest.query.filter_by(confirmed=False).all()
    
    # Групуємо запити за SKU для зручності
    grouped_transfers = {}
    for transfer in pending_transfers:
        if transfer.sku not in grouped_transfers:
            grouped_transfers[transfer.sku] = []
        grouped_transfers[transfer.sku].append(transfer)
    
    return render_template('transfers/pending_transfers.html', 
                           transfers=pending_transfers,
                           grouped_transfers=grouped_transfers)

@transfers_bp.route('/pending-transfers/confirm/<int:transfer_id>', methods=['POST'])
@login_required
@position_required(TRANSFER_ACCESS_POSITIONS)
def confirm_transfer(transfer_id):
    """Підтверджує запит на переміщення"""
    transfer = PendingTransferRequest.query.get_or_404(transfer_id)

    try:
        transfer.confirm_transfer()
        message = f'Переміщення товару {transfer.sku} успішно підтверджено'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=True, message=message)
        flash(message, 'success')
    except ValueError as e:
        message = f'Помилка підтвердження переміщення: {str(e)}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, message=message)
        flash(message, 'danger')
    except Exception as e:
        message = f'Непередбачена помилка: {str(e)}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, message=message)
        flash(message, 'danger')

    return redirect(url_for('transfers.pending_transfers_list'))

@transfers_bp.route('/pending-transfers/confirm-all-sku/<string:sku>', methods=['POST'])
@login_required
@position_required(TRANSFER_ACCESS_POSITIONS)
def confirm_all_transfers_for_sku(sku):
    """Підтверджує всі запити на переміщення для конкретного SKU"""
    transfers = PendingTransferRequest.query.filter_by(sku=sku, confirmed=False).all()

    success_count = 0
    error_count = 0

    for transfer in transfers:
        try:
            transfer.confirm_transfer()
            success_count += 1
        except Exception:
            error_count += 1

    message_success = f'Успішно підтверджено {success_count} переміщень для товару {sku}'
    message_error = f'Не вдалося підтвердити {error_count} переміщень для товару {sku}'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(
            success=success_count > 0,
            message=message_success if success_count > 0 else message_error
        )

    if success_count > 0:
        flash(message_success, 'success')
    if error_count > 0:
        flash(message_error, 'warning')

    return redirect(url_for('transfers.pending_transfers_list'))