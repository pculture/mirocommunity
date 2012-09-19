$('a#started_hide').live('click', function() {
    /* Do two things:
       One, a POST to /admin/hide_get_started... */
    $.post("/admin/hide_get_started");
    
    /* Two, a jQuery .hide() on the get_started div. */
    $('#get_started').fadeOut();
    
    /* Finally, stop the event from propagating. */
    return false;
});