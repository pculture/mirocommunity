$(function(){
	var toggle_dropdown = function (e) {
		var $this = $(this),
			dropdown_parent = $this.parent();
			dropdown_target = dropdown_parent.children('[data-dropdown-target]');
		if($this.data('open')){
			dropdown_target.hide()
			dropdown_parent.removeClass('open')
			$this.data('open', false)
		}else{
			dropdown_target.show()
			dropdown_parent.addClass('open')
			$this.data('open', true)
		}
		e.preventDefault()
	};
	$('[data-dropdown] > a').on('click', toggle_dropdown);
})