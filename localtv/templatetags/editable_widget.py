from django import template
from django.core.urlresolvers import reverse

from localtv import models
from localtv.subsite.admin.edit_attributes import forms

WIDGET_DIRECTORY = {
    models.Feed: {
        'name': {
            'default_display_template':
                'localtv/subsite/display_templates/feed_name.html',
            'form': forms.FeedNameForm,
            'reversible_post_url': 'localtv_admin_feed_edit_title'},
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
        display_template_name or widget_data['default_display_template'])

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
