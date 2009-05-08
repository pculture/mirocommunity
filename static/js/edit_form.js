function inline_edit_open() {
    obj = $(this);
    if (obj.hasClass('open')) {
        return false;
    }
    obj.addClass('open');
    this.oldContent = obj.text();
    obj.text('');
    if (obj.hasClass('vid_title')) {
        input = $('<input type="text" />').val($("#id_name").val());
        obj.append(input);
    } else if (obj.hasClass('description')) {
        textarea = $('<textarea cols="40" rows="10"/>').val($("#id_description").val());
        obj.append(textarea);
    }
    obj.append('<span class="save">✔</span> <span class="cancel">✖</span>');
    obj.children('.save').click(inline_save);
    obj.children('.cancel').click(inline_cancel);

}

function inline_save() {
    obj = $(this).parent();
    console.log(obj);
    if (obj.hasClass('vid_title')) {
        value = obj.children('input').val();
        $("#id_name").val(value);
        inline_post(obj)
    } else if (obj.hasClass('description')) {
        value = obj.children('textarea').val();
        $('#id_description').val(value);
        inline_post(obj);
    }
}
function inline_cancel() {
    obj = $(this).parent();
    return inline_reset(obj)
}

function inline_post(obj) {
    form = $("#edit_video_wrapper form");
    $.post(form.attr('action'), form.serialize(), function () {
        obj[0].oldContent = value;
        return inline_reset(obj);
    });
}

function inline_reset(obj) {
    obj.text(obj[0].oldContent);
    obj.removeClass('open');
    return false;
}

function edit_video_setup() {
    $(".editable").click(inline_edit_open);

}

$(document).ready(edit_video_setup);