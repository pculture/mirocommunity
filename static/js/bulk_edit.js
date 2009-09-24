function showEdit(obj, show) {
    parent = $(obj).parents('tr');
    if (show) {
        other = parent.next();
    } else {
        other = parent.prev();
        // reset the form fields
        parent.find('input[type=text], input[type=file], textarea').each(function() {
            this.value = this.defaultValue;
        });
        parent.find('input[type=checkbox], input[type=radio]').each(function() {
            this.checked = this.defaultChecked;
        });
    }
    parent.hide(); other.show();
    return false;
}

function toggleDelete(obj) {
    obj = $(obj);
    obj.next().val('checked');
    $("#labels form:last").submit();
    $("#labels form:last input[type=submit]:eq(0)").click();
    return false;
}

function bulkAction() {
    action = $("#bulk_action_selector").val();
    if (action == 'edit') {
        // show the bulk edit window
       $("#massedit").show();
    } else if (action) {
        $("#bulk_action").val(action);
        $("#labels form:eq(1)").submit();
    } else {
        alert('Please select an action.');
    }
}