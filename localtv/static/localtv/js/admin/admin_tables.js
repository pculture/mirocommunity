/*
# This file is part of Miro Community.
# Copyright (C) 2010, 2011 Participatory Culture Foundation
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.
*/


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
            remove_video_and_refresh_list(video_div);},
	error: function(xhr, ajaxOptions, thrownError) {
	    alert(xhr.responseText);
	}});
    return false;
}

function load_video(eventdata) {
    var viddiv = $(this);
    var video_url = $(this).find('.video_preview').text();
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

