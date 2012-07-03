import imaplib
import time
import re
from ..page import Page

class Google(Page):

    _GOOGLE_PAGE = "div.google-header-bar"
    _APPROVE = "input#approve_button"
    _EMAIL = "input#Email"
    _PASSWORD = "input#Passwd"
    _SUBMIT = "input#signIn.g-button"
   
    def activate_mc_user_account(self, email, password, url):
        """Activates a new Miro Community user's gmail account.

        Returns the activation url.a
        """
        print "Checking email for activation link"
        mailUser = email
        mailPassword = password
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        mail.login(mailUser, mailPassword)
        mail.select('Inbox')
        result, data = mail.uid('search', None, '(HEADER Subject "Finish Signing Up at")')
        latest_email_uid = data[0].split()[-1]
        result, data = mail.uid('fetch', latest_email_uid, '(RFC822)')
        raw_email = data[0][1]
        lines = raw_email.split('\n')
        for line in lines:
            if line.startswith(url):
                activationURL = line
                break
        else:
            print 'failed to find link'
        return activationURL



    def google_login(self, user, passw, **kwargs):
        if self.is_element_present(self._GOOGLE_PAGE):
            if self.is_element_present(self._EMAIL):
                self.type_by_css(self._EMAIL, user)
                self.type_by_css(self._PASSWORD, passw)
                self.click_by_css(self._SUBMIT)
            if self.is_element_present(self._APPROVE):  #signed in account, just needs approval to continue
                self.click_by_css(self._APPROVE)
 




