;jQuery(function($){

	// start anything which has a [data-cycle] attribute cycling
	$('.carousel').each(function(){
		var $this = $(this),
			pager = $('<div class="carousel-pager"></div>').appendTo($this.parent());
		$this.cycle({
			fx: 'scrollUp',
			pause: true, // pause on hover
			timeout: 6000, // 6 seconds between slides
			pager: pager,
			pauseOnPagerHover: true,
			slideResize: false,
			containerResize: false,
			slideExpr: '.video-large'
		});
	});
	
	// shrinkydink all .video-details classes
	$('.video-details').shrinkydink();
	
	// add popovers to things
	// the placement function calculates the placement of the popover,
	// defaulting to right and switching to left if the popover is too close
	// to the edge.
	$('body').popover({selector: '.popover-trigger', placement: function (element) {
		var position = this.getPosition();
		// distance from edge of hover element + width of hover element + width of popover
		return (position.left + position.width + 300 > $(window).width()) ? 'left' : 'right';
	}});

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