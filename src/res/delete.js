window.onload = function(e) {
    console.log('HERE');
    var confirm_buttons = document.querySelectorAll('.confirmYesNo');

    for (var i = 0; i < confirm_buttons.length; i++) {
        confirm_buttons[i].addEventListener('click', function(e) {
            if (!confirm(this.getAttribute('data-confirm'))) {

                e.preventDefault();
            }
        });
    }
};