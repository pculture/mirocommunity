/* TODO: Allow and adjust for padding */
function resize_admin() {
    var header = document.getElementById('header');
    var admin_leftpane = document.getElementById('admin_leftpane');
    var admin_rightpane = document.getElementById('admin_rightpane');
    admin_leftpane.style.height = (window.innerHeight
                                   - header.clientHeight - 15) + "px";
    admin_rightpane.style.height = admin_leftpane.style.height;
}

if ('attachEvent' in window) {
    window.attachEvent('onload', resize_admin);
    window.attachEvent('onresize', resize_admin);
}
else {
    window.addEventListener('load', resize_admin, false);
}
window.addEventListener('resize', resize_admin, false);
