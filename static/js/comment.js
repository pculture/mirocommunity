$(document).ready(function() {
    $("h2.post-comment-title + form").ajaxForm({success: function (response) {
        response = $(response);
        if (response.children('#next').length) {
            location.href = response.children('#next').attr('href');
        } else {
            $("#hover_wrap").find('.contentWrap').html(response);
            wrap = $("#hover_wrap").overlay({api: true});
            wrap.getContent().find('form:eq(0)').ajaxForm(
                replace_submit_video_and_setup_callbacks);
            wrap.load();
        }
    }});
});