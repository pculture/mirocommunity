# Copyright 2009 - Participatory Culture Foundation
# 
# This file is part of Miro Community.
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

from django import template
from django.core.urlresolvers import reverse

from localtv import models
from localtv.inline_edit import forms
from localtv.playlists.models import Playlist

WIDGET_DIRECTORY = {
    Playlist: {
        'name': {
            'form': forms.PlaylistNameForm},
        'slug': {
            'form': forms.PlaylistSlugForm},
        'description': {
            'form': forms.PlaylistDescriptionForm},
        },
    models.Video: {
        'name': {
            'form': forms.VideoNameForm},
        'when_published': {
            'form': forms.VideoWhenPublishedForm},
        'authors': {
            'form': forms.VideoAuthorsForm,
            'render_template':
                'localtv/inline_edit/render_widget_checklist.html'},
        'categories': {
            'form': forms.VideoCategoriesForm,
            'render_template':
                'localtv/inline_edit/render_widget_checklist.html'},
        'tags': {
            'form': forms.VideoTagsForm},
        'description': {
            'form': forms.VideoDescriptionField},
        'website_url': {
            'form': forms.VideoWebsiteUrlField},
        'editors_comment': {
            'form': forms.VideoEditorsComment},
        'thumbnail': {
            'form': forms.VideoThumbnailForm,
            'render_template':
                'localtv/inline_edit/render_widget_thumbnail.html'},
        },
    }

register = template.Library()

def get_display_content(model_instance, field_name,
                        display_template_name=None):
    try:
        widget_data = WIDGET_DIRECTORY[model_instance.__class__][field_name]
    except KeyError:
        return ''
    display_template = template.loader.get_template(
        display_template_name or widget_data.get(
            'default_display_template') or
        'localtv/inline_edit/%s_%s.html' % (
            model_instance._meta.object_name.lower(),
            field_name))
    return display_template.render(
        template.Context(
            {'instance': model_instance}))

@register.simple_tag
def editable_widget(model_instance, field_name, display_template_name=None,
                    form=None):
    try:
        widget_data = WIDGET_DIRECTORY[model_instance.__class__][field_name]
    except KeyError:
        return ''# maybe raise an error here instead saying "no such model or
                 # field could be found"?

    if form is None:
        form = widget_data['form'](instance=model_instance)

    # render the display template
    
    display_content = get_display_content(model_instance, field_name,
                                          display_template_name)


    # render the wrapper template, with display template data intact
    render_template = template.loader.get_template(
        widget_data.get('render_template',
                        'localtv/inline_edit/render_widget.html'))
    
    post_url = reverse(
        widget_data.get('reversible_post_url',
                        'localtv_admin_%s_edit_%s' % (
                model_instance._meta.object_name.lower(),
                field_name)), kwargs={'id': model_instance.id})

    return render_template.render(
        template.Context(
            {'instance': model_instance,
             'display_content': display_content,
             'post_url': post_url,
             'form': form}))
