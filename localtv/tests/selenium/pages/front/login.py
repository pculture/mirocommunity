from localtv.tests.selenium.pages.front import MCFrontPage
from localtv.tests.selenium.pages.web import facebook
from localtv.tests.selenium.pages.web import twitter
from localtv.tests.selenium.pages.web import google
from localtv.tests.selenium.pages.web import openid


class LoginPage(MCFrontPage):
    """
     Page that displays when the user chooses to login.
     Contains, site, signin, facebook, openinstall, and google options.

    """
    _LOGIN_PAGE_TITLE = "h1.page-title"
    _ERROR = "ul.errorlist li"
    _FORGOT_PASSWORD = "a[href='/accounts/password/reset/']"
    _TABS = {
        'site': {
            "css": "a[href='#login']",
            "text": "Login/Sign Up"
        },
        'signup': {
            "css": "a[href='#login']",
            "text": "Login/Sign Up"
        },
        'facebook': {
            "css": "a[href='#facebook']",
            "text": "Facebook"
        },
        'twitter': {
            "css": "a[href='#twitter']",
            "text": "Twitter"
        },
        'google': {
            "css": "a[href='#google']",
            "text": "Google"
        },
        'openid': {
            "css": "a[href='#openid']",
            "text": "OpenID"
        },
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
    _FB_LOGIN = "#facebook a"
    _TWITTER_LOGIN = "#twitter a"
    _OPEN_ID_URL = "input#openid_identifier"
    _OPEN_ID_SUBMIT = "form[action*='openid'] div div.cmntrols button"
    _GOOGLE = "form[action*='google'] p input"

    def site(self, **kwargs):
        auth = {}
        auth.update(kwargs)
        self.type_by_css(self._SITE_USERNAME, auth['user'])
        self.type_by_css(self._SITE_PASSWORD, auth['passw'])
        self.click_by_css(self._LOGIN)
        if auth['success'] is True:
            self.login_page_gone()
        else:
            self.login_error(auth['success'])

    def login_error(self, error):
        error_msg = ('Please enter a correct username and password. '
                     'Note that both fields are case-sensitive.')
        if error == 'bad password':
            self.wait_for_element_present("div.message")
            assert self.is_text_present("div.message", error_msg)
        elif error == 'blank value':
            self.wait_for_element_present(self._ERROR)
            assert self.verify_text_present(self._ERROR,
                   'This field is required.'), \
                   'Field required message not displayed'
        elif error == 'account inactive':
            self.wait_for_element_present(self._ERROR)
            assert self.verify_text_present(self._ERROR,
                   'This account is inactive.'), \
                   'Account inactive message not displayed'
        else:
            assert False, "expected an error, but not this one"

    def login(self, user, passw, kind='site', email=None, success=True):
        """Log in with the specified account type - default as a no-priv user.

        Valid values for kind are: 'site', 'signup', 'facebook',
        'google', 'openid', 'twitter'

        """
        if (self.is_logged_in() and
            not self.is_text_present(self.LOGOUT['css'],
                                     self.LOGOUT['text'] % user)):
            self.logout()

        self.wait_for_element_present(self.LOGIN['css'])
        self.click_by_css(self.LOGIN['css'])
        kwargs = {'user': user,
                  'passw': passw,
                  'email': email,
                  'tab': kind,
                  'success': success,
                  }
        self.user_login(**kwargs)
        self.wait_for_element_present(self.SITE_NAME, wait_time=15)
        return self.is_logged_in()

    def signup(self, *args):
        """Complete the signup form.

        """
        user, passw, email = args
        self.type_by_css(self._SIGNUP_USERNAME, user)
        self.type_by_css(self._SIGNUP_EMAIL, email)
        self.type_by_css(self._SIGNUP_PASSWORD1, passw)
        self.type_by_css(self._SIGNUP_PASSWORD2, passw)
        self.click_by_css(self._SIGNUP_SUBMIT)

    def facebook(self, user, passw):
        """Complete the facebook login form.

        """
        self.wait_for_element_present(self._FB_LOGIN)
        self.click_by_css(self._FB_LOGIN)
        fb_pg = facebook.FacebookAuth(self)
        fb_pg.fb_login(user, passw)

    def google(self, user, passw):
        """Complete the google login form.

        """
        self.wait_for_element_present(self._GOOGLE)
        self.click_by_css(self._GOOGLE)
        google_pg = google.Google(self)
        google_pg.google_login(user, passw)

    def openid(self, user, passw):
        """Complete the openid login form.

        """
        self.wait_for_element_present(self._OPEN_ID_URL)
        self.submit_form_text_by_css(self._OPEN_ID_URL, user)
        #self.click_by_css(self._OPEN_ID_SUBMIT)
        openid_pg = openid.MyOpenIDAuth(self)
        openid_pg.myopenid_login(user, passw)

    def twitter(self, user, passw):
        """Complete the twitter login form.

        """
        self.wait_for_element_present(self._TWITTER_LOGIN)
        self.click_by_css(self._TWITTER_LOGIN)
        twitter_pg = twitter.TwitterAuth(self)
        twitter_pg.twitter_login(user, passw)

    def choose_login_tab(self, tab):
        """Open the specified login tab.

        """
        self.click_by_css(self._TABS[tab]['css'])

    def user_login(self, **kwargs):
        """Login the user of provided type with provided account info.

        """
        l = {
            'tab': 'site',
            'email': None,
            'success': True,
        }
        l.update(kwargs)

        self.wait_for_element_present(self._TABS['site']['css'])
        if l['tab'] is 'site':
            getattr(self, 'site')(**l)
        elif l['tab'] is 'signup':
            user = l['user']
            passw = l['passw']
            email = l['email']
            getattr(self, 'signup')(user, passw, email)
        else:
            user = l['user']
            passw = l['passw']
            self.choose_login_tab(l['tab'])
            getattr(self, l['tab'])(user, passw)

    def login_page_gone(self):
        """Wait for the login page to be gone.

        """
        self.wait_for_element_not_visible(self._TABS['site']['css'])
