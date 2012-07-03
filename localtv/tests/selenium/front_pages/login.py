#!/usr/bin/env python
import time

from ..page import Page
from ..web import facebook
from ..web import twitter 
from ..web import google 
from ..web import openid

class Login(Page):
    """
     Page that displays when the user chooses to login.
     Contains, site, signin, facebook, openinstall, and google options.
     
    """
    _LOGIN_PAGE_TITLE = "h1.page-title"
    _ERROR = "ul.errorlist li"
    _FORGOT_PASS_ERROR = "div a[href='/accounts/password/reset/']"
    _TABS = {'site':
                {"css": ".login_tab_user",
                 "text": "Login/Sign Up"},
             
             'signup':
                {"css": ".login_tab_user",
                 "text": "Login/Sign Up"},

            'facebook':
                {"css": ".login_tab_facebook",
                 "text": "Facebook"},
            'twitter':
                {"css": ".login_tab_twitter",
                 "text": "Twitter"},
            'google':
                {"css": ".login_tab_google",
                 "text": "Google"},
            'openid':
                {"css": ".login_tab_openid",
                 "text": "OpenID"},

            }
    #SITE LOGIN FORM
    _LOGIN_SIDE = 'form[action*="login"] '    
    _SITE_USERNAME = _LOGIN_SIDE + 'input#id_username'
    _SITE_PASSWORD = _LOGIN_SIDE + 'input#id_password'
    _LOGIN = _LOGIN_SIDE + 'div.controls > button'

    #SITE SIGNUP FORM
    _REGISTER_SIDE = 'form[action*="register"] ' 
    _SIGNUP_USERNAME = _REGISTER_SIDE + 'input#id_username'
    _SIGNUP_EMAIL = _REGISTER_SIDE + 'input#id_email'
    _SIGNUP_PASSWORD1 = _REGISTER_SIDE + 'input#id_password1'
    _SIGNUP_PASSWORD2 = _REGISTER_SIDE + 'input#id_password2'
    _SIGNUP_SUBMIT = _REGISTER_SIDE + 'div.controls > button'

    #SOCIAL MEDIA LOGIN TABS
    _FB_LOGIN = "div#FacebookForm.tab-pane div.content-box a img"
    _TWITTER_LOGIN = "div#TwitterForm.tab-pane div.content-box a img"
    _OPEN_ID_URL = "div#OpenIDForm.tab-pane input#openid_url.openid"
    _OPEN_ID_SUBMIT = "div#OpenIDForm.tab-pane div.controls button"
    _GOOGLE = "div#GoogleForm.tab-pane input.button"


    def site(self, **kwargs):
        auth = {}
        auth.update(kwargs)
        self.type_by_css(self._SITE_USERNAME, auth['user'])
        self.type_by_css(self._SITE_PASSWORD, auth['passw'])
        self.click_by_css(self._LOGIN)
        if auth['success'] == True:
            self.login_page_gone()
        else:
            self.login_error(auth['success'])


    def login_error(self, error):
        
        if error == 'bad password':
            assert self.is_element_present(self._LOGIN), \
            'Login form not returned to view'
        elif error == 'blank value':
            self.wait_for_element_present(self._ERROR)
            assert self.verify_text_present(self._ERROR, "This field is required."), \
            'Field required message not displayed'
        elif error == 'account inactive':
            self.wait_for_element_present(self._ERROR)
            assert self.verify_text_present(self._ERROR, "This account is inactive."), \
            'Account inactive message not displayed'
        else:
            assert False, "expected an error, but not this one"
            
    def signup(self, *args):
        user, passw, email = args
        self.type_by_css(self._SIGNUP_USERNAME, user)
        self.type_by_css(self._SIGNUP_EMAIL, email)
        self.type_by_css(self._SIGNUP_PASSWORD1, passw)
        self.type_by_css(self._SIGNUP_PASSWORD2, passw)
        self.click_by_css(self._SIGNUP_SUBMIT)
              
    def facebook(self, user, passw):
        self.wait_for_element_present(self._FB_LOGIN)
        self.click_by_css(self._FB_LOGIN)
        fb_pg = facebook.FacebookAuth(self)
        fb_pg.fb_login(user, passw)


    def google(self, user, passw):
        self.wait_for_element_present(self._GOOGLE)
        self.click_by_css(self._GOOGLE)
        google_pg = google.Google(self)
        google_pg.google_login(user, passw)


    def openid(self, user, passw):
        self.wait_for_element_present(self._OPEN_ID_URL)
        self.type_by_css(self._OPEN_ID_URL, user)
        self.click_by_css(self._OPEN_ID_SUBMIT)
        openid_pg = openid.MyOpenIDAuth(self)
        openid_pg.myopenid_login(user, passw)


    def twitter(self, user, passw):
        self.wait_for_element_present(self._TWITTER_LOGIN)
        self.click_by_css(self._TWITTER_LOGIN)
        twitter_pg = twitter.TwitterAuth(self)
        twitter_pg.twitter_login(user, passw)

        
    def choose_login_tab(self, tab):
        self.click_by_css(self._TABS[tab]['css'])
        
    def user_login(self, **kwargs):
        l = {
            'tab': 'site',
            'email': None,
            'success': True,
            }
        l.update(kwargs)
        
        self.wait_for_element_present(self._TABS['site']['css'])
        if l['tab'] == 'site':
            getattr(self, 'site') (**l)
        elif l['tab'] == 'signup':
            user = l['user']
            passw = l['passw']
            email = l['email']
            getattr(self, 'signup') (user, passw, email)            
        else:
            user = l['user']
            passw = l['passw']
            self.choose_login_tab(l['tab'])
            getattr(self, l['tab']) (user, passw)

    def login_page_gone(self):
        self.wait_for_element_not_present(self._TABS['site']['css'])
        



