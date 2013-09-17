;jQuery(function($){
    // shrinkydink all .video-details classes
    $('.video-details').shrinkydink();

    $('[title]').tooltip({
        placement: 'auto top'
    });
    
    // add popovers to things
    $('[data-toggle="popover"]').popover({
        placement: 'auto right',
        container: 'body'
    });

    // Infinite Scroll
    // Only triggered if a `body.video-list-page` exists and we're on the first page
    // TODO: handle the case where we are not on the first page.
    // History!
    var History = window.History;
    if (History.enabled && $('body').hasClass('video-list-page') && $('.pagetabs').find('li:first').hasClass('selected')) {
        History.Adapter.bind(window,'statechange',function(){ // Note: We are using statechange instead of popstate
            var State = History.getState(); // Note: We are using History.getState() instead of event.state
            History.log(State.data, State.title, State.url);
        });
        $('.pagetabs').hide(); // hide pagination
        // preload the ajax loader image
        var ajax_image = new Image();
        ajax_image.src = STATIC_URL + "localtv/front/images/ajax-loader.gif";
        // kick off the infinite scrolling
        $('.grid').infinitescroll({
            navSelector: '.pagetabs',
            nextSelector: '.pagetabs > .selected + li > a',
            itemSelector: '.grid-item',
            loading: {
                msg: $("<li class=\"grid-item\" id=\"infscr-loading\">Loading&hellip;</li>"),
                // override a lot of the default behavior
                finished: function (opts) {
                    History.replaceState(null, null, "?page=" + opts.state.currPage);
                    $('#infscr-loading').remove(); // hide the spinner
                },
            },
            errorCallback: function (error) {
                if(error === "done"){
                    var $infscrLoading = $('#infscr-loading');
                    $infscrLoading.after("<li class=\"padded\" id=\"infscr-done\">End of Videos</li>");
                    $infscrLoading.remove();
                }
            }
        });
    };
    
    // Dropdowns
    $('.nav-item-dropdown').dropdown()
    $('body').on('mouseover.localtv.dropdown', '.nav-item-dropdown', function (e) {
        $(this).dropdown('show')
    });
    $('body').on('mouseout.localtv.dropdown', '.nav-item-dropdown', function (e) {
        $(this).dropdown('hide')
    });
    
});