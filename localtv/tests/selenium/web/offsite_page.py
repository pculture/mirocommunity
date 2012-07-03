#!/usr/bin/env python
from unisubs_page import UnisubsPage

class OffsitePage(UnisubsPage):
    """Main page for all offsite testing to drive playback and menus.

    """
    _CAPTIONS = "span.unisubs-captionSpan"
    _WIDGET_MENU = "span.unisubs-tabTextchoose"
    
    def start_playback(self, video_position):
        self.browser.execute_script("unisubs.widget.Widget.getAllWidgets()[%s].play()" % video_position)


    def pause_playback(self, video_position):
        self.browser.execute_script("unisubs.widget.Widget.getAllWidgets()[%s].pause()" % video_position)


    def open_subs_menu(self, video_position):
        self.browser.execute_script("unisubs.widget.Widget.getAllWidgets()[%s].openMenu()" % video_position)

    def displays_subs_in_correct_position(self):
        """Return true if subs are found in correct position on video.

        """
        size = self.get_size_by_css(self._CAPTIONS)
        height = size["height"]
        if 10 < height < 80:
            return True
        else:
            self.record_error()

    def pause_playback_when_subs_appear(self, video_position):
        self.scroll_to_video(video_position)
        self.wait_for_element_visible(self._CAPTIONS)
        self.pause_playback(video_position)

    def scroll_to_video(self, video_position):
        self.wait_for_element_present(self._WIDGET_MENU)
        elements_found = self.browser.find_elements_by_css_selector(self._WIDGET_MENU)
        elem = elements_found[video_position]
        elem.send_keys("PAGE_DOWN")
        
        
                       
                       
   
       
        


        
        

    
