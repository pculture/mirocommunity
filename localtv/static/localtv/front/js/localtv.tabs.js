$(function(){
	var tab_toggle = function (e) {
			var $this = $(this),
				$target = $($this.attr('href'));
			
			// if the target tab is currently active, do nothing
			if ($this.hasClass('active')) return;
			
			// otherwise, deactivate other tabs and activate the selected one
			$this.siblings('.active').removeClass('active');
			$target.siblings('.tab-pane.active').removeClass('active');
			$target.addClass('active');
			
			// prevent default click behavior
			e.preventDefault();
		};
	
	$('.tabs > li > a').click(tab_toggle);
});