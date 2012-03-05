$(function(){
	var show_image = function(){
			var $this = $(this);
			$this.css('opacity', 1)
		},
		transition_key = Modernizr.prefixed('transition'),
		img_css_dict = {};
		
	img_css_dict[transition_key] = "opacity linear .5s";
	img_css_dict['opacity'] = 0;
	
	$('img').css(img_css_dict);
	$('img').on('load', show_image);
});