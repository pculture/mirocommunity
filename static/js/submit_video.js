// maybe not the most elegantly named function.
function replace_submit_video_and_setup_callbacks(result) {
    $('#submit_box_content').html(result);
    $('#submit_box_content form').ajaxForm(replace_submit_video_and_setup_callbacks);
}

function start_submit_process() {
    jQuery.get($('#submit_button').attr('href'),
               replace_submit_video_and_setup_callbacks);
    $('#hover_wrap').css('display', 'block');
    return false;
}

function close_submit_box() {
    $('#hover_wrap').css('display', 'none');
    return false;
}    

function add_submit_callback() {
    $('#submit_button').click(start_submit_process);
    $('#close_submit_box span').click(close_submit_box);
}