// maybe not the most elegantly named function.
function replace_submit_video_and_setup_callbacks(result) {
    page = $(result);
    if (page.filter('#next').length) {
        location.href = page.filter('#next').attr('href');
        return;
    };
    $("#hover_wrap .contentWrap").html(page);
    $('#hover_wrap form:eq(0)').ajaxForm(replace_submit_video_and_setup_callbacks);
}

$(document).ready( function(){
    $("#nav li").mouseover(function(){$(this).addClass('sfhover');}).mouseout(function(){$(this).removeClass('sfhover');});
    $('.overlayLoad').overlay({
        target: '#hover_wrap',
        onBeforeLoad: function () {
            $.get(this.getTrigger().attr('href'),
                  replace_submit_video_and_setup_callbacks);
        }
    });
});
