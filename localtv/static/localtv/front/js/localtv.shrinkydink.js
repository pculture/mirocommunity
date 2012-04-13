;(function($){
	var Shrinkydink = function (element, options) {
			this.element = element;
			this.cache = {};
		};
	
	Shrinkydink.prototype = {
		constructor: Shrinkydink,
		_getLineHeight: function () {
			if (!this.cache.lineHeight) {
				var temp = $('<div>N</div>').css('width', 100).appendTo(this.element);
				this.cache.lineHeight = temp.innerHeight();
				temp.remove();
			}
			return this.cache.lineHeight;
		},
		initialize: function () {
			this.handle = $('<a href="#" data-shrinkydinkhandle="true" class="shrinkydink-handle">More</a>').data('shrinkydink-target', this.element);
			this.element.after(this.handle);
			this.element.css('overflow', 'hidden');
			this.shrink();
		},
		shrink: function () {
			this.element.height(this._getLineHeight()*3);
			this.element.data('shrinkydink-state', 'shrunk');
			this.handle.html('More');
		},
		expand: function () {
			this.element.height('auto');
			this.element.data('shrinkydink-state', 'expanded');
			this.handle.html('Less');
		},
		toggle: function () {
			if (this.element.data('shrinkydink-state') === 'shrunk'){
				this.expand();
			}else{
				this.shrink();
			}
		}
	};
	
	$.fn.shrinkydink = function (options) {
		return this.each(function () {
			var $this = $(this),
				data = $this.data('shrinkydink');
			if (!data) {
				// if shrinkydink has not been initialized on this element, do so
				$this.data('shrinkydink', new Shrinkydink($this));
				$this.shrinkydink('initialize');
			} else if (typeof options == 'string') {
				// otherwise, issue a shrinkydink command
				data[options]();
			}
		});
	};
	
	$(document).on('click.shrinkydink', '[data-shrinkydinkhandle]', function ( e ) {
		var $this = $(this),
			$target = $this.data('shrinkydink-target');
		$target.shrinkydink('toggle');
		return false;
	});
	
})(jQuery);