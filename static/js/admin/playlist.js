$(document).ready(function(){
    $("#playlists .playlist_thumbs").hide()
    $("#playlists .playlist_title > a").each(function(){
        parent = $(this).parent()
        thumbs = parent.next();
        flip = 0;
        $(this).click(function() {
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
        name = prompt("Enter the name for the new playlist:");
        if (!name) {
            return false;
        }
        new_playlist_form = that.next();
        new_playlist_form.find('input[name=name]').val(name);
        new_playlist_form.submit()
        return false;
    });
});