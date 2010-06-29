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
    $("#toggle_all").click(function() {
        if (this.checked) {
            $('td:first-child > input[type=checkbox]:not(:checked)').click();
        } else {
            $('td:first-child > input[type=checkbox]:checked').click();
        }
    });
    if ($("form input[name$=-id]").length != parseInt($("#id_form-INITIAL_FORMS").val(), 10)) {
        $("#overlay .contentWrap").html("<div id='load_error'>We're sorry, the editing page did not fully load and so you won't be able to edit existing items.  <a href='" + location.href + "'>Reload the page</a> to let it load fully.</div>").overlay({target: '#overlay', close: '#doesnotexist', closeOnClick: false, closeOnEsc: false, api: true}).load();
        $("#overlay .contentWrap a").click(function() { location.href = location.href;});
    }
    errors = $('.simple_overlay.errors');
    if (errors.length) {
        errors.overlay({api: true,
                        onClose: resetOverlay}).load();
    }
});
