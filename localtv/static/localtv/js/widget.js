/*
# This file is part of Miro Community.
# Copyright (C) 2010 Participatory Culture Foundation
# 
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
# 
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.
*/

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
                if (t.opts.source.search(/[?]/) > -1) {
                    ajax_path = ajax_path + '&';
                } else {
                    ajax_path = ajax_path + '?';
                }
                t.scriptTag = MiroCommunity.jsonP(ajax_path + 'jsoncallback=MiroCommunity.callback_' + t.counter);
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
                widget_wrapper = document.getElementById(this.id);
                if (this.opts.width) {
                    widget_wrapper.style.width = this.opts.width + 'px';
                } else if (this.opts.size === 'small') {
                    widget_wrapper.style.width = '108px';
                } else if (this.opts.size === 'medium') {
                   widget_wrapper.style.width = '160px';
                } else if (this.opts.size == 'large') {
                    widget_wrapper.style.width = '242px';
                }
                if (this.opts.border) {
                    widget_wrapper.style.background = this.opts.border;
                }
                widget_wrapper.className = widget_wrapper.className + ' mc-widget-' + this.opts.size;
                div = document.createElement('div');
                if (this.opts.bg) {
                    div.style.background = this.opts.bg;
                }
                title = MiroCommunity.createElement('div', {className: 'mc-widget-title'});
                if (this.opts.text) {
                    title.style.color = this.opts.text;
                }
                title.innerHTML = this.opts.title ? this.opts.title : 'Watch Videos from Miro Community';
                div.appendChild(title);
                ul = MiroCommunity.createElement('ul', {className: "mc-loading"});
                div.appendChild(ul);
                footer_box = MiroCommunity.createElement('div', {className: "mc-footer"});
                if (this.opts.logo) {
                    img = MiroCommunity.createElement('img', {src: this.opts.logo})
                    a = MiroCommunity.createElement('a', {href: "http://" + this.opts.domain + '/'});
                    a.appendChild(img);
                    footer_box.appendChild(a);
                }
                more_link = MiroCommunity.createElement('a', {href: "http://" + this.opts.domain + '/'});
                more_link.innerText = more_link.textContent = 'See More';
                more_link_wrapper = document.createElement('div');
                more_link_wrapper.appendChild(more_link);
                footer_box.appendChild(more_link_wrapper);
                div.appendChild(footer_box);
                widget_wrapper.appendChild(div);
            },
            update_v2: function(div, json) {
                links = div.getElementsByTagName('a');
                more_link = links[links.length-1];
                more_link.href = json.link;
                var ul = div.getElementsByTagName('ul')[0];
                ul.innerHTML = ul.className = '';
                var count = this.opts.count ? this.opts.count : 4;
                var li = null;
                var widget_size = this.opts.size;
                flat_bg = MiroCommunity.createElement('img', {src: 'http://' + this.opts.domain + '/images/widget/flat_' + widget_size + '.png',
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
                    if (video.thumbnail) {
                        link.appendChild(flat_bg.cloneNode(false));
                    }
                    if (widget_size !== 'small') {
                        title_span = MiroCommunity.createSpan(video.title, 'mc-title');
                        when_span = MiroCommunity.createSpan(video.when, 'mc-when');
                        if (this.opts.text) {
                            title_span.style.color = when_span.style.color = this.opts.text;
                        }
                        link.appendChild(title_span);
                        link.appendChild(when_span);
                    }
                    if (widget_size === 'large') {
                        fake_description = document.createElement('div');
                        fake_description.innerHTML = video.description;
                        fake_description_divs = fake_description.getElementsByTagName('div');
                        for(j=0; j < fake_description_divs.length; j++) {
                            div = fake_description_divs[j];
                            if (div.className === 'miro-community-description') {
                                desc_span = MiroCommunity.createSpan(div.innerText || div.textContent, 'mc-description');
                                if (this.opts.text) {
                                    desc_span.style.color = this.opts.text;
                                }
                                link.appendChild(desc_span);
                            }
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
            }
        };
    }();
}