#!/usr/bin/env python

import time
from localtv.tests.selenium.pages import Page


class SubmitPage(Page):
    """
     Submit Video Page

    """
    _URL = 'submit_video/'
    _INPUT_URL = 'input#id_url'
    _ERROR = 'ul.errorlist li'
    _SUBMIT = 'footer.form-actions > button'
    _MESSAGE = 'div.message'
    _DUP_MESSAGES = [('It appears that we already have a copy of that video '   
                      'here... sorry! You can submit another video if you '
                      'like.'),
                     ('It appears that we already have a copy of that video '
                      'here')]

    #SUBMIT FORM FIELDS
    _TITLE = 'input#id_name'  # direct and embed
    _EMBED = 'textarea#id_embed'  # embed only
    _WEBSITE = 'input#id_website_url'  # direct videos only
    _THUMB_FILE = 'input#id_thumbnail_file'  # direct and embed
    _THUMB_URL = 'input#id_thumbnail'  # direct and embed
    _DESCRIPTION = 'textarea#id_description'  # direct and embed
    _TAGS = 'input#id_tags'  # all
    _CONTACT = 'input#id_contact'
    _NOTES = 'textarea#id_notes'

    _FORM_DEFAULTS = {'tags': 'test_tag',
                      'contact': None,
                      'notes': None,
                      'title': None,
                      'website': None,
                      'embed': None,
                      'thumb_file': None,
                      'thumb_url': None,
                      'description': None
                      }
    #VIDEO SUBMITTED OR DUPLICATED LINK
    _SUBMITTED_VID_LINK = 'div.message a'

    def submit_a_valid_video(self, **kwargs):
        """Submit a video url via the submit form.

        It is expected that the url is valid.
        """

        url = kwargs['url']
        form = kwargs['form']
        self.open_page(self._URL)
        self._submit_video(url)

        if form == 'duplicate':
            return self._duplicate()
        else:
            form_action = "_".join(["", form, "form"])
            for field in kwargs.keys():
                if field not in self._FORM_DEFAULTS.keys():
                    kwargs.pop(field)
            getattr(self, form_action)(**kwargs)
            self._submit_form()
            return self._submitted_video()

    def _error_message(self):
        if self.is_element_visible(self._ERROR):
            return True

    def _error_message_text(self):
        """Return the displayed error message text.

        """
        if self.is_element_visible(self._ERROR):
            return self.get_text_by_css(self._ERROR)

    def _submit_video(self, url):
        """Enter the video url in the form.

        """
        self.type_by_css(self._INPUT_URL, url)
        self.click_by_css(self._SUBMIT)

    def _is_the_correct_submit_form(self, form):
        """Verify the expected submit form is displayed, via the url.
   
        """
        try:
            time.sleep(3)
            assert form in self.current_url()
        except AssertionError, e:
            raise(AssertionError("Expecting the {0} form, got {1}:{2}"
                                 .format(form, self.current_url(), e)))
                
    def _add_tags(self, **kwargs):
        """Add any tags to the form.

        """
        tags = kwargs.get('tags', None)
        if tags is None:
            pass
        elif isinstance(tags, basestring):
            self.clear_text(self._TAGS)
            self.type_by_css(self._TAGS, tags)
        else:
            self.clear_text(self._TAGS)
            self.type_by_css(self._TAGS, ", ".join(tags))

    def _scraped_form(self, **kwargs):
        """Verify it is the scraped form and add additional metadata.

        """
        self._is_the_correct_submit_form('scraped')
        self._add_tags(**kwargs)

    def _embed_form(self, **kwargs):
        """Verify it is the embed form and add additional metadata.

        """

        self._is_the_correct_submit_form('embed')
        self._add_tags(**kwargs)
        self._populate_form(**kwargs)

    def _direct_form(self, **kwargs):
        """Verify it is the direct form and add additional metadata.

        """

        self._is_the_correct_submit_form('directlink')
        self._add_tags(**kwargs)
        self._populate_form(**kwargs)

    def _populate_form(self, **kwargs):
        """Enter the provided metadata in the form.

        """
        form_fields = self._FORM_DEFAULTS
        form_fields.update(kwargs)
        for k, v in form_fields.iteritems():
            field = "_" + str(k).upper()
            if v:
                if self.is_element_present(getattr(self, field)):
                    self.type_by_css(getattr(self, field), v)

    def _submitted_video(self):
        """Return the site url of th submitted video.

        """
        self.wait_for_element_present(self._SUBMITTED_VID_LINK)
        video_link = self.get_element_attribute(
            self._SUBMITTED_VID_LINK, 'href')
        return video_link

    def _duplicate(self):
        """Handle duplicate video submission detection.

        """
        message = self.get_text_by_css(self._MESSAGE)
        for mess in self._DUP_MESSAGES:
            if mess in message:
                print "Duplicate video detected"
                return self._submitted_video()

    def _submit_form(self):
        """Submit the form.

        """
        self.click_by_css(self._SUBMIT)
