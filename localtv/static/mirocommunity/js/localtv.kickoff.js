;jQuery(function($){
    // shrinkydink all .video-details classes
    $('.video-details').shrinkydink();

    function calculate_placement(element, parent, default_top) {
        var $element = $(element),
            $parent = $(parent),
            offset = $parent.offset();

        $element.appendTo('body');
        var width = $element.width(),
            height = $element.height();

        if (offset.top < height) {
            return 'bottom';
        }
        if (offset.left + $parent.width() + (width / 2) > $(window).width()) {
            return 'left';
        } else if (default_top) {
            return 'top';
        }
        return 'right';
    }
    function calculate_placement_top(element, parent) {
        return calculate_placement(element, parent, true);
    }

    $('[title]').tooltip({
        placement: calculate_placement_top
    });
    
    // add popovers to things
    // the placement function calculates the placement of the popover,
    // defaulting to right and switching to left if the popover is too close
    // to the edge.
    $('[data-toggle="popover"]').popover({
        placement: calculate_placement
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

    // Amara corrections.
    var MutationObserver = window.MutationObserver || window.WebKitMutationObserver;
    if ($('body').hasClass('video-detail') && (MutationObserver !== undefined)) {
        function fixAmara() {
            var wrapper = $('.unisubs-widget'),
                videoplayer = $('.unisubs-videoplayer'),
                video = videoplayer.children();

            wrapper.css('width', '');
            videoplayer.css({'width': '', 'height': ''});

            var container = $('.unisubs-videoTab-container'),
                link = container.find('.unisubs-subtitleMeLink'),
                nav = $('.featured-inner ul'),
                li = $('<li class="dropdown"></li>');

            link.append($('<b class="caret"></b>'));
            link.addClass('dropdown-toggle')
            li.append(link);
            nav.prepend(li);

            container.remove();

            var state = 0,
                observer = new MutationObserver(function(mutations, observer) {
                    video.css({'width': '', 'height': ''});
                    video.attr('width', "");
                    video.attr('height', "");
                    observer.disconnect();
                });
                observer.observe(video[0], {
                    attributes: true
                });
        }
        // Done when state is 3.
        var state = 0,
            observer = new MutationObserver(function(mutations, observer) {
                state += 1;
                if (state == 3) {
                    fixAmara();
                    observer.disconnect();
                };
            });
        observer.observe($('.featured-inner')[0], {
            childList: true,
            subtree: true
        });
    }
    
    // Dropdowns
    $('.nav-item-dropdown').dropdown()
    $('body').on('mouseover.localtv.dropdown', '.nav-item-dropdown', function (e) {
        $(this).dropdown('show')
    });
    $('body').on('mouseout.localtv.dropdown', '.nav-item-dropdown', function (e) {
        $(this).dropdown('hide')
    });
    
});