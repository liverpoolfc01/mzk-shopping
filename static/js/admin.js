// MZK Shopping - Admin utilities
// Functions defined inline in templates for simplicity.
// This file serves as a placeholder for any shared admin functionality.

document.addEventListener('DOMContentLoaded', function() {
    // Set default datetime-local values to now if empty
    const now = new Date();
    const nowStr = now.toISOString().slice(0, 16);
    const monthLater = new Date(now.getTime() + 30*24*60*60*1000).toISOString().slice(0, 16);

    document.querySelectorAll('input[type="datetime-local"]').forEach(input => {
        if (!input.value && input.id && input.id.includes('start')) {
            input.value = nowStr;
        } else if (!input.value && input.id && input.id.includes('end')) {
            input.value = monthLater;
        }
    });
});
