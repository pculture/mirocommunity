function showEdit(obj, show) {
    parent = $(obj).parent().parent().parent();
    if (show) {
        other = parent.next();
    } else {
        other = parent.prev();
    }
    parent.hide(); other.show();
    return false;
}

function toggleDelete(obj) {
    obj = $(obj);
    if (obj.text() == 'Delete') {
        obj.next().val('checked');
        obj.text('Keep');
    } else {
        obj.next().val('');
        obj.text('Delete');
    }
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