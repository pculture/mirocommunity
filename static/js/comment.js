function comment_load(response) {
    response = $(response);
    if (response.children('#next').length) {
        location.href = response.children('#next').attr('href');
    } else {
        response.find('script').remove();
        $("#hover_wrap").find('.contentWrap').html(response);
        if (typeof Recaptcha != 'undefined') {
            recaptcha_url = $('script[src^=http://api.recaptcha.net/challenge]').attr('src');
            recaptcha_key = /k=(\w*)/.exec(recaptcha_url)[1];
            recaptcha_wrapper = document.createElement('div');
            Recaptcha.create(recaptcha_key, recaptcha_wrapper, RecaptchaOptions);
            $("#hover_wrap input[name=recaptcha_ip_field]").after(recaptcha_wrapper)
        }
        wrap = $("#hover_wrap").overlay({api: true,
                                         onClose: comment_close});
        wrap.getContent().find('form:eq(0)').ajaxForm(comment_load);
        wrap.load();
    }
}
function comment_close() {
    $("#hover_wrap .contentWrap").empty();
    if (typeof Recaptcha != 'undefined') {
        recaptcha_url = $('script[src^=http://api.recaptcha.net/challenge]').attr('src');
        recaptcha_key = /k=(\w*)/.exec(recaptcha_url)[1];
        recaptcha_wrapper = document.createElement('div');
        Recaptcha.create(recaptcha_key, recaptcha_wrapper, RecaptchaOptions);
        $("input[name=recaptcha_ip_field]").after(recaptcha_wrapper)
    }
}
$(document).ready(function() {
    $("h2.post-comment-title + form").ajaxForm(comment_load);
});