// maybe not the most elegantly named function.
function replace_submit_video_and_setup_callbacks(result) {
    page = $(result);
    if (page.attr('id') == 'next') {
        location.href = page.attr('href');
        return;
    }
    $('#submit_box_content').html(result);
    $('#close_submit_box span').click(close_submit_box);
    $('#submit_box_content form').ajaxForm(replace_submit_video_and_setup_callbacks);
}

function start_submit_process() {
    $("object").hide();
    jQuery.get($('#submit_button').attr('href'),
               replace_submit_video_and_setup_callbacks);
    $('#hover_wrap').css('display', 'block');
    return false;
}

function close_submit_box() {
    $("object").show();
    $('#hover_wrap').css('display', 'none');
    return false;
}

function add_submit_callback() {
    $('#submit_button').click(start_submit_process);
}