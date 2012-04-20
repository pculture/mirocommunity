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
			pauseOnPagerHover: true
		});
	});
	// shrinkydink all .video-details classes
	$('.video-details').shrinkydink();
	// add popovers to the video thumbs
	$('.video-grid-item').popover();
});