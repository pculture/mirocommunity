#!/usr/bin/env python
import time
from admin_nav import AdminNav


class SettingsPage(AdminNav):
    """Describes elements and functions for the Admin Settings page.

    """

   

    _URL = '/admin/settings/'
    
    #SITE SETTINGS FORM FIELDS
    _SAVE = 'button#submit_settings'
    _TITLE = 'input#id_title'
    _TAGLINE = 'input#id_tagline'
    _CURRENT_LOGO = 'label[for="id_logo"] + a'
    _CLEAR_LOGO = 'input#logo-clear_id'
    _CHANGE_LOGO = 'input#id_logo' #File input
    _CHANGE_BACKGROUND = 'input#id_background' #File input
    _DELETE_BACKGROUND = 'input[name="delete_background"]'
    _CSS = 'textarea#id_css'
    _ABOUT = 'textarea#id_about_html'
    _SIDEBAR = 'textarea#id_sidebar_html'
    _FOOTER = 'textarea#id_footer_html'
    _DISPLAY_SUBMIT = 'input#id_display_submit_button' #Display the submit button on the main page for all users
    _SUBMIT_LOGIN = 'input#id_submission_requires_login' #Require users to login to submit video
    _ORIGINAL_DATE = 'input#id_use_original_date' #The original date posted on source.  unchecked = date added to site.
    _COMMENTS_MODERATE = 'input#id_screen_all_comments' #Hold comments for moderation
    _COMMENTS_LOGIN = 'input#id_comments_required_login' #If checked, comments require the user to be logged in.
    _PLAYLISTS_ENABLED = '#id_playlists_enabled'

       

    def open_settings_page(self):
        self.open_admin_page(self._URL)


    def save_settings(self):
        self.click_by_css(self._SAVE)

    def title(self, title):
        self.clear_text(self._TITLE)
        self.type_by_css(self._TITLE, title)

    def tagline(self, tagline):
        self.clear_text(self._TAGLINE)
        self.type_by_css(self._TAGLINE, tagline)

    def logo(self, option):
        """Upload a new logo.  If option is 'clear' then clear out existing.

        """
        if option == 'clear':
            if self.is_element_present(self._CLEAR_LOGO):
                self.click_by_css(self._CLEAR_LOGO)
        else:
            self.type_by_css(self._CHANGE_LOGO, img_path)

    def background(self, option):
        """Upload a new background.  If option is 'delete' then delete existing.

        """
        if option == 'delete':
            self.click_by_css(self._DELETE_BACKGROUND)
        else:
            self.type_by_css(self._CHANGE_BACKGROUND, img_path)


    def css(self, text):
        self.clear_text(self._CSS)
        self.type_by_css(self._CSS, text)

    def about(self, text):
        self.clear_text(self._ABOUT)
        self.type_by_css(self._ABOUT, text)

    def sidebar(self, text):
        self.clear_text(self._SIDEBAR)
        self.type_by_css(self._SIDEBAR, text)

    def footer(self, text):
        self.clear_text(self._FOOTER)
        self.type_by_css(self._FOOTER, text)    
    

    def submit_display(self, option):
        """Option can be check or uncheck.

        """
        getattr(self, option) (self._DISPLAY_SUBMIT)

    def submit_login(self, option):
        """Option can be check or uncheck.

        """
        getattr(self, option) (self._SUBMIT_LOGIN)
        
    def date(self, option):
        """Option can be check or uncheck.

        """
        getattr(self, option) (self._ORIGINAL_DATE)

    def comments_moderate(self, option):
        """Option can be check or uncheck.

        """
        getattr(self, option) (self._COMMENTS_MODERATE)

    def comments_login(self, option):
        """Option can be check or uncheck.

        """
        getattr(self, option) (self._COMMENTS_LOGIN)
        

    def playlists(self, option):
        """Choose if / how playlists are available.

        Option can be: 'No', 'Yes', 'Admins Only'
            <option value="0">No</option>
            <option value="1" selected="selected">Yes</option>
            <option value="2">Admins Only</option>

        """
        self.select_option_by_text(self._PLAYLISTS_ENABLED, option)
            
        

    def site_settings(self, **kwargs):
        self.open_settings_page()
        settings = {'title': 'Dalmatia MC Test Site',
                    'tagline': 'testing is cool',
                    'logo': 'clear',
                    'background': 'delete',
                    'css': '',
                    'about': 'testing site for mc',
                    'sidebar': '',
                    'footer': '',
                    'submit_display': 'check',
                    'submit_login': 'uncheck',
                    'date': 'check',
                    'comments_moderate': 'uncheck',
                    'comments_login': 'uncheck',
                    'playlists': 'Yes',
                    }

        settings.update(kwargs)
        for k, v in settings.iteritems():
            print k, v
            getattr(self, k) (v)
            
        self.save_settings()
        
    
            
        

       
        
        
