# Miro Community
# Copyright 2009 - Participatory Culture Foundation
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django import template
from django.core.urlresolvers import reverse

from localtv import models
from localtv.subsite.admin.edit_attributes import forms

WIDGET_DIRECTORY = {
    models.Feed: {
        'name': {
            'form': forms.FeedNameForm,
            'reversible_post_url': 'localtv_admin_feed_edit_title'},
        'auto_categories': {
            'form': forms.FeedAutoCategoriesForm,
            'reversible_post_url': 'localtv_admin_feed_edit_auto_categories'},
        'auto_authors': {
            'form': forms.FeedAutoAuthorsForm,
            'reversible_post_url': 'localtv_admin_feed_edit_auto_authors'}
        }}

register = template.Library()


@register.simple_tag
def editable_widget(model_instance, field_name, display_template_name=None):
    try:
        widget_data = WIDGET_DIRECTORY[model_instance.__class__][field_name]
    except KeyError:
        return # maybe raise an error here instead saying "no such
               # model or field could be found"?

    form = widget_data['form'](instance=model_instance)

    # render the display template
    
    display_template = template.loader.get_template(
        display_template_name or widget_data.get(
            'default_display_template') or
        'localtv/subsite/display_templates/%s_%s.html' % (
            model_instance._meta.object_name.lower(),
            field_name))

    display_content = display_template.render(
        template.Context(
            {'instance': model_instance}))

    # render the wrapper template, with display template data intact
    render_template = template.loader.get_template(
        'localtv/subsite/render_widget.html')
    
    post_url = reverse(
        widget_data['reversible_post_url'], kwargs={'id': model_instance.id})

    return render_template.render(
        template.Context(
            {'instance': model_instance,
             'display_content': display_content,
             'post_url': post_url,
             'form': form}))
