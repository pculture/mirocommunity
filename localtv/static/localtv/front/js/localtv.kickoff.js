;jQuery(function($){
	
	// if a shebang is present in the URI, redirect
	if (window.location.hash.search('#!') === 0) {
		window.location = window.location.href.replace(/#!/g,'')
	}
	
	// start anything which has a [data-cycle] attribute cycling
	$('.carousel').each(function(){
		var $this = $(this),
			pager = $('<div class="carousel-pager"></div>').appendTo($this.parent());
		$this.cycle({
			fx: 'scrollUp',
			pause: true, // pause on hover
			timeout: 6000, // 6 seconds between slides
			pager: pager,
			pauseOnPagerHover: true
		});
	});
	
	// shrinkydink all .video-details classes
	$('.video-details').shrinkydink();
	
	// add popovers to the video thumbs
	$('.video-grid-item').popover();
	
	// Infinite Scroll
	$('.pagetabs').hide(); // hide pagination
	// preload the ajax loader image
	var ajax_image = new Image();
	ajax_image.src = STATIC_URL + "localtv/front/images/ajax-loader.gif";
	// kick off the infinite scrolling
	$('.video-grid').infinitescroll({
		loading: {
			img: null,
			// override a lot of the default behavior
			finished: function (opts) {
				window.location.hash = "#!?page=" + opts.state.currPage;
				$('#infscr-loading').remove();
			},
			start: function (opts) {
				opts.loading.msg = $("<li class=\"media-item loading\" id=\"infscr-loading\">Loading&hellip;</li>")
				$(opts.navSelector).hide();
				opts.loading.msg
					.appendTo(opts.loading.selector)
					.show(opts.loading.speed, function () {
						beginAjax(opts);
					});
			}
		},
		navSelector: '.pagetabs',
		nextSelector: '.pagetabs > .selected + li > a',
		itemSelector: '.media-item'
	});
	
});