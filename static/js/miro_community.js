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

if (!('placeholder' in document.createElement('input'))) {
    var has_placeholder = false;
    // browser doesn't support the HTML5 placeholder attribute
    function placeholder_fallback() {
        function copyAttributes(from_elm, to_elm) {
            attributes = ['id', 'name', 'placeholder']
            for (idx in attributes) {
                attribute = attributes[idx];
                to_elm.attr(attribute, from_elm.attr(attribute));
            };
            from_elm.replaceWith(to_elm);
            return to_elm;
        }
        $('input[placeholder]').each(function() {
            var that = $(this);
            if (!this.defaultValue) {
                that.addClass('placeholder');
            }
            function setPlaceholder() {
                if (!that.val()) {
                    if (that.attr('type') === 'password') {
                        that = copyAttributes(that,
                                              $("<input type='text' />"));
                        that.addClass('fake_password');
                    }
                    that.addClass('placeholder');
                    return that.val(that.attr('placeholder'));
                } else {
                    return that;
                }
            };
            function removePlaceholder() {
                if (that.hasClass('placeholder')) {
                    if (that.hasClass('fake_password')) {
                        that = copyAttributes(that,
                                              $("<input type='password' />"));
                        that.focus(removePlaceholder).blur(setPlaceholder).focus();
                    } else {
                        that.val('').removeClass('placeholder');
                    }
                }
            };
            setPlaceholder().focus(removePlaceholder).blur(setPlaceholder);
        });
    }
    $("form").live('submit', function() {
        $(this).find('input.placeholder').val('');
    });
} else {
    var has_placeholder = true;
}

function setup_submit_callbacks(wrap, result) {
    page = $(result);
    if (page.filter('#next').length) {
        href = page.filter('#next').attr('href');
        if (window.location.pathname === href) {
            window.location.reload(true);
        } else {
            location.href = href;
        }
        return;
    }
    function callback(result){setup_submit_callbacks(wrap, result);}
    form = wrap.getOverlay().find('.contentWrap').html(result).find('form:eq(0)');
    if (!has_placeholder) placeholder_fallback();
    form.ajaxForm({
        success: callback,
        beforeSerialize: function() {
            if (!has_placeholder) {form.find('input.placeholder').val('');}
        }}).find('button').click(function(){form.ajaxSubmit(callback);});
}
$(document).ready( function(){
    $("#nav li").mouseover(function(){$(this).addClass('sfhover');}).mouseout(function(){$(this).removeClass('sfhover');}).filter('.categories a:eq(0)').click(function() {return false;}).css('cursor', 'default');
    if (!has_placeholder) placeholder_fallback();
    if ($.browser.msie && /^[5-7]/.exec($.browser.version)) {
        // early MSIE browsers mess up the z-index, so don't do the expose
        // thing when we run into it
        expose = null;
    } else {
        expose = '#000';
    }

    $('a[rel^=#]').overlay({
        expose: expose,
        //effect: 'apple',

        onBeforeLoad: function() {
            if (this.getTrigger().attr("href") != "#") {
                wrap = this;
                $.get(this.getTrigger().attr("href"),
                      function(result){setup_submit_callbacks(wrap, result);});
            }
        }
    });
    $("#login form input[type=text], #login form input[type=password]").live('focus', function() {
        if ($(this).val() == $(this)[0].defaultValue) {
            $(this).val("");
        }
    }).live('blur', function() {
        if ($(this).val() === "") {
            $(this).val($(this)[0].defaultValue);
        }
    });
    $("#login .tabs li a").live('click', function() {
        This = $(this);
        Parent = This.parent();
        Class = This.attr("class");
        if (Class !== "") {
            $("#login .tabs_content > div:visible").hide(500);
            $("#login .tabs_content > div#"+Class).show(500);
            $("#login .tabs li.active").removeClass("active");
            Parent.addClass("active");
        }
        return false;
    });
    if(!has_placeholder) placeholder_fallback();
}).ajaxStart(function() {
    indicator = $("#load-indicator");
    if (!indicator.length) {
        return;
    }
    if ((!indicator.queue().length)) {
	indicator.animate({bottom: 0}, 'fast');
    }
}).ajaxStop(function() {
    $("#load-indicator").stop().css('bottom', '-30px');
});
