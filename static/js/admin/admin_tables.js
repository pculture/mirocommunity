
function scroll_admin() {
    table = document.getElementById('admin_table');
    table_offset = $("#admin_table").offset();
    leftpane = document.getElementById('admin_leftpane');
    rightpane = document.getElementById('admin_rightpane');
    if (rightpane.clientHeight > window.innerHeight) {
        diff = rightpane.clientHeight - window.innerHeight;
    } else {
        diff = 0;
    }
    if (table_offset.top + diff > window.scrollY) {
        rightpane.style.top = (table_offset.top - window.scrollY) + 'px';
    } else {
        rightpane.style.top = (-diff) + 'px';
    }
    leftpane.style.width = (table.clientWidth - 590) + 'px';
    rightpane.style.display = "block";
    if (leftpane.clientHeight < rightpane.clientHeight) {
        leftpane.style.height = rightpane.clientHeight + 'px';
    }

	videolisting_row = $("#admin_videolisting_row");
	videolisting_row_offset = videolisting_row.offset();
	$("#admin_rightpane").css({
		right: "auto",
		left: (videolisting_row_offset.left + videolisting_row.width())+"px",
		position: "fixed",
		width: ($("#content").width()-500)+"px"
	});
	
	$("#admin_rightpane object, #admin_rightpane embed").css({
		width: ($("#content").width()-540)+"px"
	});
	
}

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
                $("#admin_rightpane .simple_overlay").overlay({absolute: true});
                var selected = $('div.selected');
                selected.removeClass('selected');
                selected.addClass('unselected');
                viddiv.removeClass('unselected');
                viddiv.addClass('selected');
                scroll_admin();
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
    $("#admin_rightpane .simple_overlay").overlay({absolute: true});
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

