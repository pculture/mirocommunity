function inline_edit_open() {
    obj = $(this);
    editable_wrapper = obj.parent('.editable');
    
}

function insert_and_activate_action_buttons() {
    obj = $(this);
    obj.append('<span class="save">✔</span> <span class="cancel">✖</span>');
    obj.children('.save').click(inline_save);
    obj.children('.cancel').click(inline_cancel);
}

function edit_widgets_setup() {
    $(".editable .display_data").click(inline_edit_open);
    $(".editable .input_field").click(insert_and_activate_action_buttons);
}
