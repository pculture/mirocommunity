
/* TODO: Allow and adjust for padding */

function remove_video_and_refresh_list(video_div) {
    video_div.fadeOut(1000, function() {video_div.remove();});
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
    var viddiv = $(this);
    var video_url = $(this).find('.click_to_display').attr('href');
    var admin_rightpane = $('#admin_rightpane');
    jQuery.ajax({
            url: video_url,
            success: function(data) {
                admin_rightpane.empty().append(data);
                if (typeof edit_widgets_setup === 'function') {
                    edit_widgets_setup();
                }
                var selected = $('div.selected');
                selected.removeClass('selected');
                selected.addClass('unselected');
                viddiv.removeClass('unselected');
                viddiv.addClass('selected');
                }});
    return false;
}

function load_click_callbacks() {
    $('div.video .approve_reject .approve').click(
        run_and_disappear);
    $('div.video .approve_reject .reject').click(
        run_and_disappear);
    $('div.video .approve_reject .feature').click(
        run_and_disappear);
    $('div.video').click(load_video);
}

function scroll_admin() {
    admin_table = document.getElementById('admin_table');
    admin_leftpane = document.getElementById('admin_leftpane');
    admin_rightpane = document.getElementById('admin_rightpane');
    if (admin_rightpane.clientHeight > window.innerHeight) {
        diff = admin_rightpane.clientHeight - window.innerHeight;
    } else {
        diff = 0;
    }
    if (admin_table.offsetTop + diff > window.scrollY) {
        admin_rightpane.style.top = (admin_table.offsetTop - window.scrollY) + 'px';
    } else {
        admin_rightpane.style.top = (-diff) + 'px';
    }
    admin_rightpane.style.right = admin_table.offsetLeft + 'px';
    admin_leftpane.style.width = (admin_table.clientWidth - 590) + 'px';
    admin_rightpane.style.display = "block";
    if (admin_leftpane.clientHeight < admin_rightpane.clientHeight) {
        admin_leftpane.style.height = admin_rightpane.clientHeight + 'px';
    }
}

if ('attachEvent' in window) {
    window.attachEvent('onload', scroll_admin);
    window.attachEvent('onload', load_click_callbacks);
    window.attachEvent('onscroll', scroll_admin);
    window.attachEvent('onresize', scroll_admin);
}
else {
    window.addEventListener('load', scroll_admin, false);
    window.addEventListener('load', load_click_callbacks, false);
    window.addEventListener('scroll', scroll_admin, false);
    window.addEventListener('resize', scroll_admin, false);
}

