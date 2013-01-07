import urllib

from django.conf import settings
from django.core.paginator import Page
from django.template import Context, Library, Node, loader, TemplateSyntaxError


register = Library()
DEFAULT_TEMPLATE = "localtv/pagetabs.html"


def page_lists_from_page_ranges(paginator, page_ranges):

    return map(
        lambda page_range: [Page([], pagenum, paginator)
                            for pagenum in page_range],
        page_ranges)


def sectionify_paginator(paginator, page_number=1):
    tab_length = int(getattr(settings, 'PAGETABS_LENGTH', 9))
    unselected_end_tabsize = int(getattr(settings, 'PAGETABS_END_SIZE', 2))
    selected_end_tabsize = tab_length - unselected_end_tabsize - 1

    page_range = paginator.page_range

    if paginator.num_pages <= tab_length:
        return page_lists_from_page_ranges(
            paginator,
            [page_range])
    elif page_number < selected_end_tabsize:
        return page_lists_from_page_ranges(
            paginator,
            [page_range[:selected_end_tabsize],
             page_range[-unselected_end_tabsize:]])
    elif page_number > (paginator.num_pages - selected_end_tabsize + 1):
        return page_lists_from_page_ranges(
            paginator,
            [page_range[:unselected_end_tabsize],
             page_range[-selected_end_tabsize:]])
    else:
        middle_length = tab_length - (unselected_end_tabsize * 2) - 2
        # -2 for the ellipses
        if middle_length % 2:  # odd
            low_end = page_number - (middle_length + 1) / 2
            high_end = page_number + (middle_length - 1) / 2
        else:
            low_end = page_number - middle_length / 2
            high_end = page_number + middle_length / 2

        return page_lists_from_page_ranges(
            paginator,
            [page_range[:unselected_end_tabsize],
             page_range[low_end:high_end],
             page_range[-unselected_end_tabsize:]])


class PageTabNode(Node):
    def __init__(self, page, template_name):
        self.page = page
        self.template_name = template_name

    def render(self, context):
        new_context = Context()
        new_context.dicts.extend(context.dicts)

        page = self.page.resolve(context)
        pagesections = sectionify_paginator(page.paginator, page.number)

        new_context['pagesections'] = pagesections
        new_context['selected_page'] = page

        if context.get('request'):
            request = context['request']
            new_context['pagetabs_url'] = request.path
            GET_args = request.GET.copy()
            if 'page' in GET_args:
                del GET_args['page']
            new_context['pagetabs_args'] = urllib.urlencode(
                [(k, v.encode('utf8')) for k, v in GET_args.items()])

        if self.template_name is None:
            template_name = DEFAULT_TEMPLATE
        else:
            template_name = self.template_name.resolve(context)
        template = loader.get_template(template_name)
        return template.render(new_context)


@register.tag
def pagetabs(parser, token):
    """
    This tag is deprecated.

    {% pagetabs <page_var> [<template_name>] %}

    ``page_var`` is a Page object. ``template_name`` is a template name.

    """
    bits = token.split_contents()
    tag_name = bits[0]
    if len(bits) not in (2, 3):
        raise TemplateSyntaxError("{tag_name} requires one or two arguments".format(tag_name=tag_name))

    page_var = parser.compile_filter(bits[1])
    try:
        template_name = parser.compile_filter(bits[2])
    except IndexError:
        template_name = None

    return PageTabNode(page_var, template_name)
