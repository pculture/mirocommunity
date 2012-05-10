$(function () {
	var DURATION = .5, // in seconds
		show_image = function () {
			var $this = $(this);
			// if css transitions work, just swap the opacity, otherwise fall back to jQuery animation
			if (Modernizr.csstransitions) {
				$this.css('opacity', 1);
			} else {
				$this.animate({'opacity': 1}, DURATION);
			}
		},
		transition_key = Modernizr.prefixed('transition'),
		img_css_dict = {};
	
	// Prepare each image's initial CSS
	img_css_dict[transition_key] = "opacity linear " + DURATION + "s";
	img_css_dict['opacity'] = 0;
	
	// Set each image's initial CSS
	$('img').each(function () {
		var $this = $(this);
		if (!this.complete) $this.css(img_css_dict);
	});
	// Set the load event for each image
	$('img').on('load', show_image);
});