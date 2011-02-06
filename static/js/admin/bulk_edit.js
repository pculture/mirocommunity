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
    /* If the overlay div exists, great -- show that in the overlay: */
    overlay_elm = $(obj).parents('tr').find('.simple_overlay');
    if (overlay_elm.length > 0) {
	overlay_elm.overlay({api: true,
			     onClose: resetOverlay}).load();
    }
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
    if (window.location.href.indexOf("not_all_actions_done") {
	alert("Due to your site level, we did not complete all of your bulk edits. You should review this page and make sure that the edits you wanted saved properly.");
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
