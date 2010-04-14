function comment_form_callback(response) {
    parsed = $("<div/>").html(response);
    next = parsed.find('#next').attr('href');
    if ((next == location.pathname) ||
        (next == location.href)) {
        $('#comment_form').clearForm();
        location.href = location.href + '#comments';
        location.reload();
        return;
    }
    form = parsed.find('form');
    if (form.length) {
        // problems with the form submission
        $("#comment_form").replaceWith(form);
        recaptcha_ajax_field = $("#comment_form #recaptcha_ajax_field");
        if (typeof recaptcha_ajax_callback !== 'undefined') {
            recaptcha_ajax_callback();
        }
        $("#comment_form").ajaxForm(comment_form_ajax_options);
    } else {
        $("#comment_form").clearForm().find('.errorlist').remove();
        $("#overlay .contentWrap").empty().append(parsed.find('.comment_posted'));
        $("#overlay").overlay({api:true}).load();
    }
}

comment_form_ajax_options = {
    success: comment_form_callback,
    dataType: 'html'
}

$(document).ready(function() {
    $("#comment_form").ajaxForm(comment_form_ajax_options);
});