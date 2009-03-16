function start_submit_process() {
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