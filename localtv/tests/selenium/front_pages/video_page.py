#!/usr/bin/env python

from ..page import Page



class VideoPage(Page): 
    """Video Page.
    """
    _TITLE = ".title"
    _SOURCE = ".colophon a"
    _DESCRIPTION = ".video-details"
    _SUBMITTER = "div.compact:nth-child(2)" #includes the 'Submitted by: ' text
    _EXPANDER = ".shrinkydink-handle"
    _EXPANDER_TEXT = ".shrinkydink-handle-inner"
    _TAGS = "div.video-full-tags a"
    _AMARA_WIDGET = ".unisubs-subtitleMeLink .unisubs-tabTextchoose"

 
    def check_video_details(self, **kwargs):
        video_data = {
                    'title': None,
                    'tags': None,
                    'description': None,
                    'submitter': None,
                    'source': None,
                    }
        video_data.update(kwargs)
        site_vid_details = []
        for k, v in video_data.iteritems():
            if not v == None:
                print v
                site_vid_details.append(self._video_data(k, v))
        site_vid_details = [x for x in site_vid_details if not x == True]
        return site_vid_details
        

    def _video_data(self, data_field, data_value):
        vid_field = "_".join(["", data_field]).upper()
        if hasattr(self, vid_field):
            field = getattr(self, vid_field)
            if data_field == 'tags':
                pass
            elif data_value in self.get_text_by_css(field):
                return True
            else:
                return "Expected {0}, for {1} but found {2} instead.".format(data_value, data_field, self.get_text_by_css(field))


    def verify_amara_widget(self):
        if self.is_element_present(self._AMARA_WIDGET):
            return True
        
