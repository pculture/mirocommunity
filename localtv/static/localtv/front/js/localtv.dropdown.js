$(function(){
	var toggle_dropdown = function (e) {
			var $this = $(this),
				dropdown_parent = $this.parent();
				dropdown_target = dropdown_parent.children('[data-dropdown-target]');
			if($this.attr('data-dropdown-open')==='true'){
				dropdown_target.hide()
				dropdown_parent.removeClass('open')
				$this.attr('data-dropdown-open', 'false')
			}else{
				dropdown_target.show()
				dropdown_parent.addClass('open')
				$this.attr('data-dropdown-open', 'true')
			}
			e.preventDefault();
			e.stopPropagation();
		},
		close_dropdowns = function (e){
			$('[data-dropdown-open="true"]').click()
		};
	$(document.body).click(close_dropdowns)
	$('[data-dropdown] > a').on('click', toggle_dropdown);
})