// MZK Shopping - Cart operations

function updateQty(itemId, delta) {
    const qtyEl = document.getElementById('qty-' + itemId);
    let qty = parseInt(qtyEl.textContent) + delta;
    if (qty <= 0) {
        if (!confirm('确定删除该商品？')) return;
    }
    qty = Math.max(0, qty);

    fetch('/cart/update/' + itemId, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({quantity: qty})
    })
    .then(r => r.json())
    .then(d => {
        if (d.success) {
            if (qty === 0) {
                const item = document.getElementById('cart-item-' + itemId);
                if (item) item.remove();
            } else {
                qtyEl.textContent = qty;
            }
            updateCartBadge(d.cart_count);
            location.reload(); // Refresh to update totals
        } else {
            alert(d.message);
        }
    });
}

function removeItem(itemId) {
    if (!confirm('确定删除该商品？')) return;
    fetch('/cart/remove/' + itemId, {method: 'POST'})
        .then(r => r.json())
        .then(d => {
            if (d.success) {
                updateCartBadge(d.cart_count);
                location.reload();
            }
        });
}
