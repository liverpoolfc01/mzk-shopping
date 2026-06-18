// MZK Shopping - Shared utilities

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss flash messages after 3 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.3s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 3000);
    });
});

// Generic fetch helper
function apiFetch(url, method, data) {
    const options = {
        method: method,
        headers: {'Content-Type': 'application/json'},
    };
    if (data) {
        options.body = JSON.stringify(data);
    }
    return fetch(url, options).then(r => r.json());
}

// Update cart badge count across all elements
function updateCartBadge(count) {
    document.querySelectorAll('#cart-badge, #cart-badge-bottom, .cart-badge .badge').forEach(el => {
        el.textContent = count;
        el.style.display = count > 0 ? 'flex' : 'none';
    });
}

// Format price
function formatPrice(price) {
    return '¥' + parseFloat(price).toFixed(2);
}
