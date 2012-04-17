;jQuery(function($){
	// start anything which has a [data-cycle] attribute cycling
	$('[data-cycle]').cycle({fx: 'scrollUp'});
	// shrinkydink all .video-details classes
	$('.video-details').shrinkydink();
	// add popovers to the video thumbs
	$('.video-grid-item').popover({delay:{show: 250, hide: 0}});
});