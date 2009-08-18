function inline_edit_open() {
    obj = $(this);
    if (obj.hasClass('open')) {
        is_file = obj.children('input[type=file]');
        return is_file; // file inputs need return true
    }
    obj.addClass('open');
    this.oldContent = obj.html();
    obj.text('');
    if (obj.hasClass('vid_title')) {
        input = $('<input type="text" />').val($("#id_name").val());
        obj.append(input);
    } else if (obj.hasClass('description')) {
        textarea = $('<textarea cols="40" rows="10"/>').val($("#id_description").val());
        obj.append(textarea);
    } else if (obj.hasClass('thumbnail')) {
        input = $('<input type="text" />').val($("#id_thumbnail_url").val());
        input2 = $('<input type="file" name="thumbnail"/>');
        obj.append('Thumbnail URL');
        obj.append(input);
        obj.append('or upload: ')
        obj.append(input2);
    } else if (obj.hasClass('tags')) {
        input = $('<input type="text" />').val($("#id_tags").val());
        obj.append(input);
    } else if (obj.hasClass('categories')) {
        input = $("#id_categories").clone().attr('id', '');
        obj.append(input);
    } else if (obj.hasClass('authors')) {
        input = $("#id_authors").clone().attr('id', '');
        obj.append(input);
    }
    obj.append('<span class="save">✔</span> <span class="cancel">✖</span>');
    obj.children('.save').click(inline_save);
    obj.children('.cancel').click(inline_cancel);

}

function inline_save() {
    obj = $(this).parent();
    if (obj.hasClass('vid_title')) {
        value = obj.children('input').val();
        $("#id_name").val(value);
        inline_post(obj);
    } else if (obj.hasClass('description')) {
        value = obj.children('textarea').val();
        $('#id_description').val(value);
        inline_post(obj);
    } else if (obj.hasClass('thumbnail')) {
        input = obj.children('input');
        console.log(input);
        input.replaceWith($('<span>Uploading...</span>'));
        $("#id_thumbnail_url").val(input.eq(0).val());
        old_input = $("#id_thumbnail");
        old_input.after(input.eq(1));
        old_input.remove();
        inline_post(obj);
    } else if (obj.hasClass('tags')) {
        value = obj.children('input').val();
        $("#id_tags").val(value);
        inline_post(obj);
    } else if (obj.hasClass('categories')) {
        value = obj.children('select').val();
        $("#id_categories").val(value);
        inline_post(obj);
    } else if (obj.hasClass('authors')) {
        value = obj.children('select').val();
        $("#id_authors").val(value);
        inline_post(obj);
    }
}

function inline_cancel() {
    obj = $(this).parent();
    return inline_reset(obj);
}

function inline_post(obj) {
    $("#edit_video_wrapper form").submit();
}

function inline_reset(obj) {
    obj.html(obj[0].oldContent);
    obj.removeClass('open');
    return false;
}

function edit_video_setup() {
    $(".editable").click(inline_edit_open);

}

$(document).ready(edit_video_setup);