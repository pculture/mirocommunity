function inline_edit_open() {
    var obj = $(this);
    var editable_wrapper = obj.parent('.editable');
    obj.css('display', 'none');
    editable_wrapper.children('.input_field').css('display', 'inline');
}

function insert_and_activate_action_buttons(obj) {
    if (!obj.children('.done').length) {
        obj.append('<span class="done">Done</span>');
        obj.children('.done').click(inline_save);
    }
}

function inline_save() {
    var post_data = {};
    var obj = $(this);
    var input_wrapper = obj.parent();
    var inputs = input_wrapper.find(':input');
    var editable_wrapper = input_wrapper.parent('.editable');
    var display_wrapper = editable_wrapper.children('.display_data');

    inputs.each(function() {
        post_data[this.name] = $(this).val();});
    var post_url = editable_wrapper.children('.post_url').text();
    jQuery.post(
        post_url, post_data,
        function(data) {
            if (data['post_status'] == 'SUCCESS') {
                input_wrapper.children('ul').html(data['input_html']);
                display_wrapper.html(data['display_html']);
                insert_and_activate_action_buttons(input_wrapper);
                input_wrapper.css('display', 'none');
                display_wrapper.css('display', 'inline');
            } else if (data['post_status'] == 'FAIL') {
                input_wrapper.html(data['input_html']);
                insert_and_activate_action_buttons(input_wrapper);
            }}, 'json');
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
    insert_and_activate_action_buttons(editable_inputs);
}

$(document).ready(edit_widgets_setup);