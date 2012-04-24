;(function($){
	var Shrinkydink = function (element, options) {
			this.element = element;
			this.cache = {};
		};
	
	Shrinkydink.prototype = {
		constructor: Shrinkydink,
		animationSpeed: 200,
		lineCount: 3,
		_getLineHeight: function () {
			if (!this.cache.lineHeight) {
				var temp = $('<div>N</div>').css('width', 100).appendTo(this.element);
				this.cache.lineHeight = temp.innerHeight();
				temp.remove();
			}
			return this.cache.lineHeight;
		},
		_getFullHeight: function () {
			var windowWidth = $(window).width();
			// if the height hasn't been cached yet or the window width has changed since the last time it was
			if (!this.cache.fullHeight || windowWidth != this.cache.windowWidth) {
				// cache the window width for comparison later
				this.cache.windowWidth = windowWidth;
				// get the current height of the element
				var currheight = this.element.height();
				// briefly expand the element to measure it
				this.element.css('height', 'auto');
				this.cache.fullHeight = this.element.height();
				// shrink it back to its previous height
				this.element.css('height', currheight);
			}
			return this.cache.fullHeight;
		},
		initialize: function () {
			// short-circuit, if the element is not tall enough to be worth shrinking
			if (this._getLineHeight() * this.lineCount >= this.element.height() ) return;
			console.log(this._getLineHeight() * this.lineCount, this.element.height());
			// otherwise, run the stuff
			this.handle = $('<a href="#" class="shrinkydink-handle"><span class="shrinkydink-handle-inner"></span></a>').data('shrinkydink-target', this.element);
			this.handleInner = $('.shrinkydink-handle-inner', this.handle);
			this.element.after(this.handle);
			this.element.css('overflow', 'hidden');
			this.shrink(true);
		},
		shrink: function (instant) {
			if (instant) {
				this.element.css({height:this._getLineHeight() * this.lineCount});
			} else {
				this.element.animate({height:this._getLineHeight() * this.lineCount}, this.animationSpeed);
			}
			this.element.data('shrinkydink-state', 'shrunk');
			this.element.toggleClass('shrunk');
			this.handleInner.html('Read More');
		},
		expand: function () {
			this.element.animate({height: this._getFullHeight()}, this.animationSpeed);
			this.element.data('shrinkydink-state', 'expanded');
			this.handleInner.html('Collapse');
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
	
	$(document).on('click.shrinkydink', '.shrinkydink-handle', function ( e ) {
		var $this = $(this),
			$target = $this.data('shrinkydink-target');
		$target.shrinkydink('toggle');
		return false;
	});
	
})(jQuery);