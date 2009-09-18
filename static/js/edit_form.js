function old_inline_edit_open() {
    obj = $(this);
    if (obj.hasClass('open')) {
        is_file = Boolean(obj.children('input[type=file]').length);
        return is_file; // file inputs need return true
    }
    obj.addClass('open');
    obj[0].oldContent = obj.html();
    obj.text('');
    if (obj.hasClass('thumbnail')) {
        input = $('<input type="text" />').val($("#id_thumbnail_url").val());
        input2 = $('<input type="file" name="thumbnail"/>');
        obj.append('Thumbnail URL');
        obj.append(input);
        obj.append('or upload: ');
        obj.append(input2);
    } else {
        obj.removeClass('open');
        obj.html(this.oldContent);
        return;
    }
    obj.append('<span class="save med_button"><span>Save Changes</span></span> <span class="cancel med_button"><span>Cancel</span></span>');
    obj.children('.save').click(old_inline_save);
    obj.children('.cancel').click(old_inline_cancel);

}

function old_inline_save() {
    obj = $(this).parent();
    if (obj.hasClass('thumbnail')) {
        input = obj.children('input');
        input.replaceWith($('<span>Uploading...</span>'));
        $("#id_thumbnail_url").val(input.eq(0).val());
        old_input = $("#id_thumbnail");
        old_input.after(input.eq(1));
        old_input.remove();
        old_inline_post(obj);
     }
}

function old_inline_cancel() {
    obj = $(this).parent();
    return old_inline_reset(obj);
}

function old_inline_post(obj) {
    $("#edit_video_wrapper form").submit();
}

function old_inline_reset(obj) {
    obj.html(obj[0].oldContent);
    obj.removeClass('open');
    obj.find('.editable.thumbnail').click(old_inline_edit_open);
    return false;
}

function edit_video_setup() {
    $(".editable.thumbnail").click(old_inline_edit_open);

}

$(document).ready(edit_video_setup);