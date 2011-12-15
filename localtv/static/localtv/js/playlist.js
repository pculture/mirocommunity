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

$(document).ready(function(){
    $("#id_playlist").append('<option value="new">New Playlist...</option>');
    $("#playlists + form + form").hide()
    $("#playlists .playlist_thumbs").hide()
    $("#playlists .playlist_title > a").each(function(){
        flip = 0;
        $(this).click(function() {
            parent = $(this).parent();
            thumbs = parent.next();
            if (++flip % 2) {
                parent.addClass('open')
                thumbs.show(400);
            } else {
                parent.removeClass('open')
                thumbs.hide();
            }
            return false;
        });
    });
    $("#id_playlist").parents('form').submit(function() {
        that = $(this);
        field = that.find("#id_playlist");
        if (!field.val()) {
            return false;
        }
        if (field.val() != 'new') {
            // keep going!
            return true;
        }
        if (!(name = prompt("Enter the name for the new playlist:"))) {
            return false;
        }
        if (name == "") {
            return false;
        }

        new_playlist_form = that.next();
        new_playlist_form.find('input[name=name]').val(name);
        new_playlist_form.submit()
        return false;
    });
});