function inline_edit_open() {
    $(this).parents('.editable').children('.simple_overlay').overlay({api: true}).load();
    return false;
}

function insert_and_activate_action_buttons(obj) {
    if (!obj.children('.done').length) {
        if (obj.find('.checklist').length) {
            obj.prepend('<span class="done">Done</span>');
        } else {
            obj.append('<span class="done">Done</span>');
        }
        obj.children('.done').click(inline_save);
    }
}

function inline_save() {
    var editable_wrapper = $(this).parents('.editable');
    var input_wrapper = editable_wrapper.find('.input_field');
    var inputs = input_wrapper.find(':input');
    var display_wrapper = editable_wrapper.children('.display_data');

    var post_data = inputs.serialize();
    var post_url = editable_wrapper.children('.post_url').text();

    jQuery.post(
        post_url, post_data,
        function(data) {
            if (data['post_status'] == 'SUCCESS') {
                input_wrapper.children('ul').html(data['input_html']);
                display_wrapper.html(data['display_html']);
                insert_and_activate_action_buttons(input_wrapper);
                editable_wrapper.children('.simple_overlay').overlay({api: true}).close();
            } else if (data['post_status'] == 'FAIL') {
                input_wrapper.html(data['input_html']);
                insert_and_activate_action_buttons(input_wrapper);
            }}, 'json');
}

$(document).ready(function() {
    // create custom animation algorithm for jQuery called "drop"
    $.easing.drop = function (x, t, b, c, d) {
        return -c * (Math.sqrt(1 - (t/=d)*t) - 1) + b;
    };
     $.tools.overlay.conf.expose = '#789';
    // create custom overlay effect for jQuery Overlay
    $.tools.overlay.addEffect("drop",
                              // loading animation
                              function(done) {
                                  var animateProps = {
                                      top: '+=55',
                                      opacity: 1,
                                      width: '+=20'
                                  };
                                  this.getOverlay().animate(animateProps, "medium", 'drop', done).show();
                              },
                              // closing animation
                              function(done) {
                                  var animateProps = {
                                      top: '-=55',
                                      opacity: 0,
                                      width: '-=20'
                                  };
                                  this.getOverlay().animate(animateProps, "fast", 'drop', function()  {
                                      $(this).hide();
                                      done.call();
                                  });
                              }
                             );
    $(".editable .edit_link").live('click', inline_edit_open)
    $(".editable .input_field").each(
        function() {insert_and_activate_action_buttons($(this));});
});
