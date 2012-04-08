$(function(){
	var tab_toggle = function (e) {
			var $this = $(this),
				$target = $($this.attr('href')),
				$parent = $this.parent();
			
			// if the target tab is currently active, do nothing
			if ($parent.hasClass('active')) return;
			
			// otherwise, deactivate other tabs and activate the selected one
			$parent.siblings('.active').removeClass('active');
			$parent.addClass('active');
			$target.siblings('.tab-pane.active').removeClass('active');
			$target.addClass('active');
			
			// prevent default click behavior
			e.preventDefault();
		};
	
	$('.tabs > li > a').click(tab_toggle);
});