import os
import uuid
import random
import string
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app


def generate_order_no():
    """Generate unique order number: datetime + random chars"""
    now = datetime.utcnow()
    date_part = now.strftime('%Y%m%d%H%M%S')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f'{date_part}{random_part}'


def save_upload(file):
    """Save uploaded file to static/uploads/ with UUID filename.
    Returns the relative path to the file."""
    if not file or file.filename == '':
        return None

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
    if ext not in current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif', 'webp'}):
        return None

    filename = f'{uuid.uuid4().hex}.{ext}'
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)
    return f'/static/uploads/{filename}'


def format_price(price):
    """Format price as string with 2 decimal places"""
    if price is None:
        return '0.00'
    return f'{float(price):.2f}'


def apply_coupon(coupon, order_total):
    """Calculate discount amount from a coupon"""
    if coupon is None:
        return 0
    if float(order_total) < float(coupon.min_amount):
        return 0

    if coupon.type == 'fixed':
        return float(coupon.value)
    elif coupon.type == 'percent':
        return round(float(order_total) * float(coupon.value) / 100.0, 2)
    return 0


def get_param(data, key, default=None, cast=None):
    """Extract and cast parameter from dict or MultiDict.
    Works with request.get_json() (plain dict) or request.form (MultiDict)."""
    val = data.get(key)
    if val is None or val == '':
        return default
    if cast is None:
        return val
    try:
        return cast(val)
    except (ValueError, TypeError):
        return default
