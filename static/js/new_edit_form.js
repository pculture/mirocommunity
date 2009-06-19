function inline_edit_open() {
    var obj = $(this);
    var editable_wrapper = obj.parent('.editable');
    obj.css('display', 'none');
    editable_wrapper.children('.input_field').css('display', 'inline');
}

function insert_and_activate_action_buttons() {
    var obj = $(this);
    obj.append('<span class="save">✔</span> <span class="cancel">✖</span>');
    obj.children('.save').click(inline_save);
    obj.children('.cancel').click(inline_cancel);
}

function inline_save() {
    alert('saved, mothafuckas!');
}

function inline_cancel() {
    var obj = $(this);
    var editable_wrapper = obj.parent().parent('.editable');
    obj.parent().css('display', 'none');
    editable_wrapper.children('.display_data').css('display', 'inline');
}

function edit_widgets_setup() {
    $(".editable .display_data").click(inline_edit_open);
    var editable_inputs = $(".editable .input_field");
    editable_inputs.append('<span class="save">✔</span> <span class="cancel">✖</span>');
    editable_inputs.children('.save').click(inline_save);
    editable_inputs.children('.cancel').click(inline_cancel);
}

$(document).ready(edit_widgets_setup);