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

function showBulk() {
    if ($("td:first-child input[type=checkbox]:checked").length) {
        first = $("td:first-child input[type=checkbox]:checked:eq(0)");
        editable = first.parent().parent();
        massedit_children = $("#massedit").children('input, textarea');
        editable.children('input, textarea').each(function (index) {
            massedit_children.eq(index).val(this.val());
        });
        $("#massedit").show();
    } else {
        $("#massedit").hide();
    }
}