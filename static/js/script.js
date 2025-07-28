// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add confirmation for marking requests as fulfilled
    const fulfillButtons = document.querySelectorAll('a[href*="mark_fulfilled"]');
    fulfillButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('هل أنت متأكد من تلبية هذا الطلب؟')) {
                e.preventDefault();
            }
        });
    });

    // Password confirmation validation
    const passwordField = document.getElementById('password');
    const confirmPasswordField = document.getElementById('confirm_password');
    
    if (passwordField && confirmPasswordField) {
        const form = passwordField.closest('form');
        
        form.addEventListener('submit', function(e) {
            if (passwordField.value !== confirmPasswordField.value) {
                e.preventDefault();
                alert('كلمات المرور غير متطابقة');
            }
        });
    }
});