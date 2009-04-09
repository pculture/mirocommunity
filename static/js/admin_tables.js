/* TODO: Allow and adjust for padding */

var DEBUG_DATA = null;
function load_video(eventdata) {
    var viddiv = $(eventdata.currentTarget);
    var video_id = $('span.video_id', viddiv).text();
    jQuery.ajax({
            url: '/admin/preview_video/?video_id=' + video_id,
            complete: function(response, status) {
                if (status == "success") {
                    alert('yesss');
                    DEBUG_DATA = response;
                } else {
                    alert('failboat');
                    DEBUG_DATA = response;
                }}});
}

function load_click_callbacks() {
    $('div.unselected').bind('click', load_video);
    // var viddivs = $('div.video');
    // for (i=0; i< viddivs.length; i++) {
    //     viddivs[i];
    // for (i=0; );
}

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
    window.attachEvent('onload', load_click_callbacks);
    window.attachEvent('onresize', resize_admin);
}
else {
    window.addEventListener('load', resize_admin, false);
    window.addEventListener('load', load_click_callbacks, false);
}
window.addEventListener('resize', resize_admin, false);
