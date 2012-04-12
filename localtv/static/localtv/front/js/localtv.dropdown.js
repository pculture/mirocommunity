$(function(){
	var close_dropdown = function (dropdown_target, dropdown_parent) {
			var $this = $(this),
				dropdown_parent = $this.parent();
				dropdown_target = dropdown_parent.children('[data-dropdown-target]');
			dropdown_target.hide();
			dropdown_parent.removeClass('open');
			$this.attr('data-dropdown-open', 'false');
		},
		open_dropdown = function (dropdown_target, dropdown_parent) {
			var $this = $(this),
				dropdown_parent = $this.parent();
				dropdown_target = dropdown_parent.children('[data-dropdown-target]');
			dropdown_target.show();
			dropdown_parent.addClass('open');
			$this.attr('data-dropdown-open', 'true');
		},
		toggle_dropdown = function (e) {
			var $this = $(this);
			if($this.attr('data-dropdown-open')==='true'){
				// if the dropdown menu is already open, close it
				close_dropdown.call(this);
			}else{
				// if the dropdown menu is closed, open it
				close_dropdowns(); // close other dropdowns
				open_dropdown.call(this);
			}
			e.preventDefault();
			e.stopPropagation();
		},
		close_dropdowns = function (e){
			$('[data-dropdown-open="true"]').click();
		};
	$(document.body).click(close_dropdowns);
	$('[data-dropdown] > a').on('click', toggle_dropdown);
})