function showEdit(obj, show) {
    parentObj = $(obj).parents('tr');
    if (show) {
        other = parentObj.next();
    } else {
        other = parentObj.prev();
        // reset the form fields
        parentObj.find('input[type=text], input[type=file], textarea').each(function() {
            this.value = this.defaultValue;
        });
        parentObj.find('input[type=checkbox], input[type=radio]').each(function() {
            this.checked = this.defaultChecked;
        });
    }
    parentObj.hide(); other.show();
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
    action = $("#bulk_action_selector").val();
    if (action == 'edit') {
        // show the bulk edit window
       $("#massedit").show();
    } else if (action) {
        $("#bulk_action").val(action);
        bulkSubmit();
    } else {
        alert('Please select an action.');
    }
}