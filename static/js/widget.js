if (typeof MiroCommunity === 'undefined') {
    MiroCommunity = {
        Widget: function(args) {
            this.init(args);
        },
        jsonP: function(path) {
            script = document.createElement('script');
            script.type = 'text/javascript';
            script.src = path;
            document.getElementsByTagName('head')[0].appendChild(script);
            return script;
        },
        createElement: function(name, attrs) {
            elm = document.createElement(name);
            for (attr in attrs) {
                elm[attr] = attrs[attr];
            }
            return elm;
        },
        createSpan: function(content, className) {
            span = document.createElement('span');
            span.className = className;
            span.innerHTML = content;
            return span;
        }
    };
    MiroCommunity.Widget._counter = 0;
    MiroCommunity.Widget._addedStyles = false;
    MiroCommunity.Widget.prototype = function() {
        return {
            init: function(options) {
                this.opts = options;
                this.counter = ++MiroCommunity.Widget._counter;
                this.id = 'mc-widget-' + this.counter;
                this.scriptTag = null;
            },
            render: function () {
                this.addStyle();
                document.write('<div id="' + this.id + '" class="mc-widget">');
                document.write('<h2>Watch Videos from Miro Community</h2><ul class="mc-loading"><li><span/></li></ul>');
                document.write('<a class="mc-from" href="http://' + this.opts.domain + '/">' + this.opts.domain + '</a></div>');
                this.load();
            },
            addStyle: function() {
            head = document.getElementsByTagName('head')[0];
                if (!MiroCommunity.Widget._addedStyles && this.opts.stylesheet !== '') {
                    link = document.createElement('link');
                    link.rel = 'stylesheet';
                    if (this.opts.stylesheet) {
                        link.href = this.opts.stylesheet;
                    } else {
                        link.href = 'http://' + this.opts.domain + '/css/widget.css';
                    }
                    head.appendChild(link);
                    MiroCommunity.Widget._addedStyles = true;
                }
                style = document.createElement('style');
                style.type = 'text/css';
                width = this.opts.width ? this.opts.width : 300;
                style.innerText = '#' + this.id + ', #' + this.id + ' ul {width: ' + width + 'px;}';
                head.appendChild(style);
            },
            load: function() {
                var t = this;
                ajax_path = 'http://' + t.opts.domain + '/feeds/json/' + t.opts.source;
                MiroCommunity['callback_' + t.counter] = function(json) {
                    t.scriptTag.parentNode.removeChild(t.scriptTag);
                    t.scriptTag = null;
                    var div = document.getElementById(t.id);
                    t.update(div, json);
                };
                t.scriptTag = MiroCommunity.jsonP(ajax_path + '?jsoncallback=MiroCommunity.callback_' + t.counter);
            },
            update: function(div, json) {
                var ul = div.getElementsByTagName('ul')[0];
                ul.innerHTML = ul.className = '';
                var count = this.opts.count ? this.opts.count : 4;
                var li = null;
                for (var i=0; i < json.items.length && i < count; i++) {
                    item = json.items[i];
                    li = MiroCommunity.createElement('li', {className: 'mc-video'});
                    link = MiroCommunity.createElement('a', {href: item.link});
                    thumb = MiroCommunity.createElement('span', {className: 'mc-thumbnail'});
                    thumb.appendChild(MiroCommunity.createElement('img', {
                        width: 120,
                        height: 90,
                        src: item.thumbnail}));
                    thumb.appendChild(MiroCommunity.createSpan('', 'mc-play'));
                    link.appendChild(thumb);
                    link.appendChild(MiroCommunity.createSpan(item.title, 'mc-title'));
                    link.appendChild(MiroCommunity.createSpan(item.when, 'mc-when'));
                    li.appendChild(link);
                    ul.appendChild(li);
                }
                if (li !== null) {
                    li.className += ' mc-last';
                }
            }
        };
    }();
}