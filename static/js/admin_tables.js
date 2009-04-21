/* TODO: Allow and adjust for padding */

function remove_video_and_refresh_list(video_div) {
    video_div.fadeOut(1000, function() {video_div.remove()});
}

function run_and_disappear(eventdata) {
    var this_anchor = $(this);
    var video_div = this_anchor.parent().parent();
    jQuery.ajax({
        url: this_anchor.attr('href'),
        success: function() {
            remove_video_and_refresh_list(video_div);}});
    return false;
}

function load_video(eventdata) {
    var viddiv = $(this).parents('.video');
    var video_url = $(this).attr('href');
    var admin_rightpane = $('#admin_rightpane');
    jQuery.ajax({
            url: video_url,
            success: function(data) {
                admin_rightpane.empty().append(data);
                var selected = $('div.selected');
                selected.removeClass('selected');
                selected.addClass('unselected');
                selected.css('cursor', 'pointer');
                viddiv.removeClass('unselected');
                viddiv.addClass('selected');
                viddiv.css('cursor', 'default');
                }});
    return false;
}

function load_click_callbacks() {
    $('.click_to_display').click(load_video);
    $('div.video .approve_reject .approve').click(
        run_and_disappear);
    $('div.video .approve_reject .reject').click(
        run_and_disappear);
}

function resize_admin() {
    var header = document.getElementById('header');
    var above_admin_table = document.getElementById('above_admin_table');
    var admin_leftpane = document.getElementById('admin_leftpane');
    var admin_rightpane = document.getElementById('admin_rightpane');
    admin_leftpane.style.height = (window.innerHeight
                                   - header.clientHeight
                                   - above_admin_table.clientHeight
                                   - 15) + "px";
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
