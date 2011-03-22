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

function resetOverlay() {
    overlay_elm = this.getOverlay()
    overlay_elm.find('input[type=text], input[type=file], textarea').each(function() {
        this.value = this.defaultValue;
    });
    overlay_elm.find('input[type=checkbox], input[type=radio]').each(function() {
        this.checked = this.defaultChecked;
    });
}
function showEdit(obj) {
    overlay_elm = $(obj).parents('tr').find('.simple_overlay');
    overlay_elm.overlay({api: true,
                     onClose: resetOverlay}).load();
    return false;
}

function bulkSubmit() {
    $("#labels form:last").submit();
    $("#labels form:last button[type=submit]:eq(0)").click();
    $("#labels form:last input[type=submit]:eq(0)").click();
}

function toggleDelete(obj) {
    obj = $(obj);
    obj.next().val('checked');
    bulkSubmit();
    return false;
}

function bulkAction() {
    action_val = $("#bulk_action_selector").val();
    if (action_val == 'edit') {
        // show the bulk edit window
        $("#massedit").overlay({api: true,
                                onClose: resetOverlay}).load();
    } else if (action_val) {
        $("#bulk_action").val(action_val);
        bulkSubmit();
    } else {
        alert('Please select an action.');
    }
}

$(document).ready(function() {
    /* If the page says we didn't permit some actions, we should say so. */
    if (window.location.href.indexOf("not_all_actions_done") != -1) {
	alert("Because of your site level, we could not publish all the videos you submitted.. You should review this page and make sure that the edits you wanted saved properly.");
    }

    $("#toggle_all").click(function() {
        if (this.checked) {
            $('td:first-child > input[type=checkbox]:not(:checked)').click();
        } else {
            $('td:first-child > input[type=checkbox]:checked').click();
        }
    });
    if ($("form input[name$=-id]").length != parseInt($("input[id$=INITIAL_FORMS]").val(), 10)) {
        $("#overlay .contentWrap").html("<div id='load_error'>We're sorry, the editing page did not fully load and so you won't be able to edit existing items.  <a href='" + location.href + "'>Reload the page</a> to let it load fully.</div>").overlay({target: '#overlay', close: '#doesnotexist', closeOnClick: false, closeOnEsc: false, api: true}).load();
        $("#overlay .contentWrap a").click(function() { location.href = location.href;});
    }
    errors = $('.simple_overlay.errors');
    if (errors.length) {
        errors.overlay({api: true,
                        onClose: resetOverlay}).load();
    }
});

$.generateId = function() {
    return arguments.callee.prefix + arguments.callee.count++;
};
$.generateId.prefix = 'jq_';
$.generateId.count = 0;

$.fn.generateId = function() {
    return this.each(function() {
	this.id = $.generateId();
    });
};

$('.replace_with_href').live('click', function() {
    /* Take the "this" that we are passed, and jQuery-ify it */
    $this = $(this);
    var link_url = $this.attr('href');
    var form_plus_id = link_url.split(/.*just_the_author_field=(.*?)&/)[1];

    /* Temporarily, say that we are loading...
       Then do an asynchronous GET to render this form field */
    var elt = $("<span>Loading...</span>");
    elt.generateId();
    $this.parent().append(elt);
    $this.css('display', 'none');
    $.get($this.attr('href'), function(data) {
	/* When we get the form contents, replace the Loading... message with the data */
	$("#" + elt.attr('id')).html(data);
	/* The backend will ignore this data if it sees the hidden "skip_authors" field
	   set to True. So we have to remove that field.

	   It has an ID like:
	   id_form-7-skip_authors. The number 7 is the ID of this object, related to the
	   Django formset we have rendered.

	   To find that number, we look at the URL of the link we clicked.
	*/
	$('#id_' + form_plus_id + '-skip_authors').remove();
    });
    return false;
});
