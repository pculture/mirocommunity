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
            versioned: function(method, args) {
                func = null;
                if (this.opts.version !== undefined) {
                    func = this[method + '_v' + this.opts.version]
                }
                if (!func) {
                    func = this[method];
                }
                return func.apply(this, Array.prototype.slice.call(arguments, 1));
            },
            render: function () {
                this.addStyle();
                if (this.opts.version && this.opts.version !== 1) {
                    widget_class = 'mc-widget-v' + this.opts.version
                } else {
                    widget_class = 'mc-widget'
                }
                document.write('<div id="' + this.id + '" class="' + widget_class + '"></div>');
                this.versioned('beforeLoad');
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
            },
            load: function() {
                var t = this;
                ajax_path = 'http://' + t.opts.domain + '/feeds/json/' + t.opts.source;
                MiroCommunity['callback_' + t.counter] = function(json) {
                    t.scriptTag.parentNode.removeChild(t.scriptTag);
                    t.scriptTag = null;
                    var div = document.getElementById(t.id);
                    t.versioned('update', div, json);
                };
                t.scriptTag = MiroCommunity.jsonP(ajax_path + '/?jsoncallback=MiroCommunity.callback_' + t.counter);
            },
            // Widget version 1
            beforeLoad: function () {
                width = this.opts.width ? this.opts.width : 300;
                div = document.getElementById(this.id);
                title = MiroCommunity.createElement('h2')
                title.innerText = this.opts.title ? this.opts.title : 'Watch Videos from Miro Community';
                div.appendChild(title);
                ul = MiroCommunity.createElement('ul', {className: "mc-loading"});
                ul.style.width = width + 'px';
                div.appendChild(ul);
                footer = MiroCommunity.createElement('a', {className: "mc-from",
                                                           href: "http://" + this.opts.domain + '/'})
                footer.innerText = this.opts.domain;
                div.appendChild(footer);
            },
            update: function(div, json) {
                var ul = div.getElementsByTagName('ul')[0];
                ul.innerHTML = ul.className = '';
                var count = this.opts.count ? this.opts.count : 4;
                var li = null;
                for (var i=0; i < json.items.length && i < count; i++) {
                    video = json.items[i];
                    li = MiroCommunity.createElement('li', {className: 'mc-video'});
                    link = MiroCommunity.createElement('a', {href: video.link});
                    thumb = MiroCommunity.createElement('span', {className: 'mc-thumbnail'});
                    var thumbnail = null;
                    if (video.thumbnail) {
                        thumbnail = video.thumbnail;
                    } else {
                        thumbnail = 'http://' + this.opts.domain + '/images/default_vid.gif';
                    }
                    thumb.appendChild(MiroCommunity.createElement('img', {
                        width: 120,
                        height: 90,
                        src: thumbnail}));
                    thumb.appendChild(MiroCommunity.createSpan('', 'mc-play'));
                    link.appendChild(thumb);
                    link.appendChild(MiroCommunity.createSpan(video.title, 'mc-title'));
                    link.appendChild(MiroCommunity.createSpan(video.when, 'mc-when'));
                    li.appendChild(link);
                    ul.appendChild(li);
                }
                if (li !== null) {
                    li.className += ' mc-last';
                }
            },
            // Widget version 2
            beforeLoad_v2: function () {
                wrapper = document.getElementById(this.id);
                if (this.opts.width) {
                    wrapper.style.width = this.opts.width + 'px';
                } else if (this.opts.size === 'small') {
                    wrarpper.style.width = '110px';
                } else if (this.opts.size === 'medium') {
                    wrapper.style.width = '170px';
                } else if (this.opts.size == 'large') {
                    wrapper.style.width = '260px';
                }
                wrapper.className = wrapper.className + ' mc-widget-' + this.opts.size;
                div = document.createElement('div');
                title = MiroCommunity.createElement('div', {className: 'mc-widget-title'});
                title.innerText = this.opts.title ? this.opts.title : 'Watch Videos from Miro Community';
                div.appendChild(title);
                ul = MiroCommunity.createElement('ul', {className: "mc-loading"});
                div.appendChild(ul);
                footer_box = MiroCommunity.createElement('div', {className: "mc-footer"});
                if (this.opts.logo) {
                    footer_box.appendChild(MiroCommunity.createElement('img', {src: this.opts.logo}));
                }
                more_link = MiroCommunity.createElement('a', {href: "http://" + this.opts.domain + '/'});
                more_link.innerText = 'See More';
                more_link_wrapper = document.createElement('div');
                more_link_wrapper.appendChild(more_link);
                footer_box.appendChild(more_link_wrapper);
                div.appendChild(footer_box);
                wrapper.appendChild(div);
            },
            update_v2: function(div, json) {
                var ul = div.getElementsByTagName('ul')[0];
                ul.innerHTML = ul.className = '';
                var count = this.opts.count ? this.opts.count : 4;
                var li = null;
                var widget_size = this.opts.size;
                flat_bg = MiroCommunity.createElement('img', {src: 'http://' + this.opts.domain + '/images/widget/flat.png',
                                                              className: 'mc-flat-bg'});
                separator = MiroCommunity.createElement('div', {className: 'mc-separator'});
                for (var i=0; i < json.items.length && i < count; i++) {
                    video = json.items[i];
                    li = MiroCommunity.createElement('li', {className: 'mc-video'});
                    if (video.thumbnail) {
                        for (j=0; j < video.thumbnails_resized.length; j++){
                            resized = video.thumbnails_resized[j];
                            width = resized.width; height = resized.height;
                            if ((width === 140 && height === 110 && widget_size == 'medium') ||
                                (width === 88 && height == 68 && widget_size == 'small') ||
                                (width === 222 && height == 169 && widget_size == 'large')) {
                                li.style.backgroundImage = 'url(' + resized.url + ')';
                            }
                        }
                    }
                    box = document.createElement('div');
                    link = MiroCommunity.createElement('a', {href: video.link});
                    link.appendChild(flat_bg.cloneNode(false));
                    link.appendChild(MiroCommunity.createSpan(video.title, 'mc-title'));
                    link.appendChild(MiroCommunity.createSpan(video.when, 'mc-when'));
                    fake_description = document.createElement('div');
                    fake_description.innerHTML = video.description;
                    fake_description_divs = fake_description.getElementsByTagName('div');
                    for(j=0; j < fake_description_divs.length; j++) {
                        div = fake_description_divs[j];
                        if (div.className === 'miro-community-description') {
                            link.appendChild(MiroCommunity.createSpan(div.innerHTML, 'mc-description'));
                        }
                    }
                    box.appendChild(link);
                    li.appendChild(box);
                    li.appendChild(separator.cloneNode(false));
                    ul.appendChild(li);
                }
                if (li !== null) {
                    li.className += ' mc-last';
                }
            },
        };
    }();
}