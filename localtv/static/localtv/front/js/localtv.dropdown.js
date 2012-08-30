/* ========================================================================
 * This dropdown javascript does require that the dropdown target be nested
 * inside of the dropdown element, and be styled based on the presence or
 * absence of the 'open' tag on the dropdown element. E.g.,
 *
 *     .dropdown{
 *         display:none;
 *     }
 *     .dropdown.open{
 *         display:block;
 *     }
 *
 * ======================================================================== */

;(function($){
	
	var Dropdown = function (element) {
		this.element = element;
		this.open = false;
	};
	
	Dropdown.prototype = {
		hide: function () {
				this.open = false;
				this.element.removeClass('open');
			},
		show: function () {
				this.open = true;
				this.element.addClass('open');
			},
		toggle: function () {
				if (this.open) return this.close();
				this.open();
			}
	};
	
	$.fn.dropdown = function (option) {
		return this.each(function () {
			var $this = $(this),
				data = $this.data('dropdown');
			if (!data) $this.data('dropdown', new Dropdown($this));
			if (typeof option == 'string') data[option]();
		});
	};
	
}(jQuery));