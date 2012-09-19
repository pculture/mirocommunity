;jQuery(function($){
    function scroll_admin() {
        table = document.getElementById('admin_table');
        table_offset = $("#admin_table").offset();
        leftpane = document.getElementById('admin_leftpane');
        rightpane = document.getElementById('admin_rightpane');
        if (rightpane.clientHeight > window.innerHeight) {
            diff = rightpane.clientHeight - window.innerHeight;
        } else {
            diff = 0;
        }
        if (table_offset.top + diff > window.scrollY) {
            rightpane.style.top = (table_offset.top - window.scrollY) + 'px';
        } else {
            rightpane.style.top = (-diff) + 'px';
        }
        leftpane.style.width = (table.clientWidth - 590) + 'px';
        rightpane.style.display = "block";
        if (leftpane.clientHeight < rightpane.clientHeight) {
            leftpane.style.height = rightpane.clientHeight + 'px';
        }

        videolisting_row = $("#admin_videolisting_row");
        videolisting_row_offset = videolisting_row.offset();
        $("#admin_rightpane").css({
            right: "auto",
            left: (videolisting_row_offset.left + videolisting_row.width())+"px",
            position: "fixed",
            width: ($("#content").width()-500)+"px"
        });
        
        $("#admin_rightpane object, #admin_rightpane embed").css({
            width: ($("#content").width()-540)+"px"
        });
        
    }

    /* TODO: Allow and adjust for padding */

    function remove_video_and_refresh_list(video_div) {
        video_div.fadeOut(1000, function() {video_div.remove();});
    }

    function run_and_disappear(eventdata) {
        var this_anchor = $(this);
        var video_div = this_anchor.parent().parent();
        jQuery.ajax({
            url: this_anchor.attr('href'),
            success: function() {
                remove_video_and_refresh_list(video_div);},
        error: function(xhr, ajaxOptions, thrownError) {
            alert(xhr.responseText);
        }});
        return false;
    }

    function load_video(eventdata) {
        var viddiv = $(this);
        var video_url = $(this).find('.video_preview').text();
        var admin_rightpane = $('#admin_rightpane');
        jQuery.ajax({
                url: video_url,
                success: function(data) {
                    admin_rightpane.empty().append(data);
                    if (typeof edit_widgets_setup === 'function') {
                        edit_widgets_setup();
                    }
                    $("#admin_rightpane .simple_overlay").overlay({absolute: true});
                    var selected = $('div.selected');
                    selected.removeClass('selected');
                    selected.addClass('unselected');
                    viddiv.removeClass('unselected');
                    viddiv.addClass('selected');
                    scroll_admin();
                    adjust_video_size();
                    }});
        return false;
    }

    function adjust_video_size() {
        var wrapper = $("#video_wrapper");
        var video_element = wrapper.children()
        var width = video_element.attr('width');
        var height = video_element.attr('height');
        if (width && height) {
            var available_width = 357;
            if (width > available_width) {
                scale = available_width / width;
                height = parseInt(scale * height);
                width = available_width;
                video_element.attr('width', width).attr('height', height);
            }
        }
    }
    $('div.video').click(load_video);
    // load the first video
    $('div.video').eq(0).click()

    $('div.video .approve_reject .approve').click(run_and_disappear);
    $('div.video .approve_reject .reject').click(run_and_disappear);
    $('div.video .approve_reject .feature').click(run_and_disappear);
    $("#admin_rightpane .simple_overlay").overlay({absolute: true});

    scroll_admin();
    $(window).scroll(scroll_admin);
    $(window).resize(scroll_admin);
    $(adjust_video_size);
});
