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

function comment_form_callback(response) {
    parsed = $("<div/>").html(response);
    next_link = parsed.find('#next').attr('href');
    full_path = location.protocol + '//' + location.host + location.pathname;
    if ((next_link == location.pathname) ||
        (next_link == full_path)) {
        $('#comment_form').clearForm();
        location.href = full_path + '#comments';
        location.reload();
        return;
    }
    form = parsed.find('form');
    if (form.length) {
        // problems with the form submission
        $("#comment_form").replaceWith(form);
        recaptcha_ajax_field = $("#comment_form #recaptcha_ajax_field");
        if (typeof recaptcha_ajax_callback !== 'undefined') {
            recaptcha_ajax_callback();
        }
        $("#comment_form").ajaxForm(comment_form_ajax_options);
    } else {
        $("#comment_form").clearForm().find('.errorlist').remove();
        $("#overlay .contentWrap").empty().append(parsed.find('.comment_posted'));
        $("#overlay").overlay({api:true}).load();
    }
}

comment_form_ajax_options = {
    success: comment_form_callback,
    dataType: 'html'
}

$(document).ready(function() {
    $("#comment_form").ajaxForm(comment_form_ajax_options);
});
