#!/usr/bin/env python
import time

from ..page import Page
from ..front_pages.login import Login

class AdminNav(Login, Page):
    """
     Unisubs page contains common web elements found across
     all Universal Subtitles pages. Every new page class is derived from
     UnisubsPage so that every child class can have access to common web 
     elements and methods that pertain to those elements.
    """

    _URL = '/admin/'
   

    def login(self, user, passw):
        self.open_page('accounts/login/')
        kwargs = {'user': user,
                  'passw': passw}
        self.user_login(**kwargs) 

    def open_admin_page(self, url):
        if not url:
            url = self._URL
        self.open_page(url)
        
