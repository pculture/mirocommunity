function remove_section(section) {
    section.fadeOut(500, function() {section.remove()});
}


function stop_watching_feed(eventdata) {
    jQuery.ajax({
        url: $(this).attr('href'),
        success: function() {
                remove_section($(eventdata.currentTarget).parent().parent());
            }});
    return false;
}

function toggle_auto_approve_feed(eventdata) {
    var this_anchor = $(this);
    jQuery.ajax({
        url: this_anchor.attr('href'),
        success: function(eventdata) {
                this_anchor.css('display', 'none');
                if (this_anchor.attr('class') == 'auto_approve') {
                    this_anchor.parent().find(
                        '.disable_auto_approve').css('display', 'inline');
                } else {
                    this_anchor.parent().find(
                        '.auto_approve').css('display', 'inline');
                }
            }});
    return false;
}

function load_click_callbacks() {
    $('.admin_feed_actions .stop_watching').click(stop_watching_feed);
    $('.admin_feed_actions .auto_approve').click(
        toggle_auto_approve_feed);
    $('.admin_feed_actions .disable_auto_approve').click(
        toggle_auto_approve_feed);
}

if ('attachEvent' in window) {
    window.attachEvent('onload', load_click_callbacks);
}
else {
    window.addEventListener('load', load_click_callbacks, false);
}
