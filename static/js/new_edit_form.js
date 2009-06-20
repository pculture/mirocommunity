function inline_edit_open() {
    var obj = $(this);
    var editable_wrapper = obj.parent('.editable');
    obj.css('display', 'none');
    editable_wrapper.children('.input_field').css('display', 'inline');
}

function insert_and_activate_action_buttons(obj) {
    obj.append('<span class="save">✔</span> <span class="cancel">✖</span>');
    obj.children('.save').click(inline_save);
    obj.children('.cancel').click(inline_cancel);
}

function inline_save() {
    var post_data = {};
    var obj = $(this);
    var input_wrapper = obj.parent();
    var inputs = input_wrapper.children(':input');
    var editable_wrapper = input_wrapper.parent('.editable');
    var display_wrapper = editable_wrapper.parent('.display_data');
    inputs.each(function() {
            post_data[this.name] = this.value;});
    var post_url = editable_wrapper.children('.post_url').text();
    jQuery.post(
        post_url, post_data,
        function(data) {
            if (data['post_status'] == 'SUCCESS') {
                input_wrapper.html(data['input_html']);
                display_wrapper.html(data['display_html']);
                insert_and_activate_action_buttons(input_wrapper);
                input_wrapper.css('display', 'none');
                display_wrapper.css('display', 'inline');
            } else {

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