function insert_and_activate_action_buttons(obj) {
    if (!obj.children('.done').length) {
        if (obj.find('.checklist').length) {
            obj.prepend('<span class="done">Done</span>');
        } else {
            obj.append('<span class="done">Done</span>');
        }
        obj.children('.done').click(function() {obj.submit();});
    }
}

function inline_edit_open() {
    editable = $(this).parents('.editable');
    var use_absolute = false;
    editable.find('.input_field').each(
        function() {insert_and_activate_action_buttons($(this));}).ajaxForm({
            dataType: 'html',
            forceSync: true,
            beforeSubmit: function(data) {
                editable.children('.simple_overlay').overlay({api: true}).close();
            },
            success: function(data, statusText) {
                widget = $(data);
                editable.replaceWith(widget);
                widget.children('.simple_overlay').overlay({absolute: use_absolute, api: true});
            },
            error: function(xhr, status, error) {
                widget = $(xhr.responseText);
                editable.replaceWith(widget);
                widget.children('.simple_overlay').overlay({absolute: use_absolute, api:true});
                inline_edit_open.call(widget.find('a.edit_link'));
            }
        });
    api = editable.children('.simple_overlay').overlay({api: true});
    use_absolute = api.getConf().absolute;
    api.load();
    return false;
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
    $(".editable .edit_link").live('click', inline_edit_open);
});
