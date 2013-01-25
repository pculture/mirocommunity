"""Basic webdriver commands used in all pages.

"""

import time
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from django.utils.importlib import import_module
from django.contrib.auth import authenticate
from django.conf import settings
from django.contrib.sites.models import Site

class Page(object):
    """Basic webdriver commands available to all pages.

    All pages inherit from Page.

    """
    _DEBUG_ERROR = ".exception_value"
    _MULTIPLE_ELS = "More than 1 of this element was found on the page."

    def __init__(self, testsetup):
        self.browser = testsetup.browser  # BROWSER TO USE FOR TESTING
        self.base_url = testsetup.base_url
        self.logger = testsetup.logger

    def _safe_find(self, element):
        self.wait_for_element_present(element)
        elem = self.browser.find_element_by_css_selector(element)
        return elem

    def quit(self):
        """Quit the browser.

        """
        self.browser.quit()

    def close_browser(self):
        self.browser.close()

    def page_refresh(self):
        self.browser.refresh()

    def page_error(self):
        """Return django debug page error information.

        """
        error_text = None
        if self.is_element_present(self._DEBUG_ERROR):
            error_text = self.get_text_by_css(self._DEBUG_ERROR)
        return [error_text, self.current_url()]

    def current_url(self):
        """Return the current page url.

        """
        return self.browser.current_url

    def handle_js_alert(self, action):
        """Accept or reject js alert.

        """
        self.logger.info('Handling alert dialog with: %s' % action)
        try:
            time.sleep(2)
            a = self.browser.switch_to_alert()
            if action == "accept":
                a.accept()
            elif action == "reject":
                a.dismiss()
        except:
            self.record_error('failed handling the expected alert')

    def check(self, element):
        """Check the box for the element provided by css selector.

        """
        el = self._safe_find(element)
        if not el.is_selected():
            el.click()

    def uncheck(self, element):
        """Uncheck the box for the element provided by css selector.

        """
        el = self._safe_find(element)
        if el.is_selected():
            el.click()

    def select_option_by_text(self, element, text):
        """Select an option based on text of the css selector.

        """
        select = Select(self._safe_find(element))
        select.select_by_visible_text(text)

    def hover_by_css(self, page_element):
        """Hover over element of provided css selector.

        """
        element = self._safe_find(page_element)
        mouseAction = webdriver.ActionChains(self.browser)
        mouseAction.move_to_element(element).perform()

    def click_item_from_pulldown(self, menu_el, menu_item_el):
        """Open a hover pulldown and choose a displayed item.

        """
        menu_element = self._safe_find(menu_el)
        menu_item_element = self._safe_find(menu_item_el)
        mouseAction = (webdriver.ActionChains(self.browser)
                       .move_to_element(menu_element)
                       .click(menu_item_element)
                       .perform())

    def click_item_after_hover(self, menu_el, menu_item_el):
        """Open a hover pulldown and choose a displayed item.

        """
        self.browser.implicitly_wait(5)        
        menu_element = self._safe_find(menu_el)
        mouseAction = (webdriver.ActionChains(self.browser)
                       .move_to_element(menu_element)
                       #.click(menu_item_element)
                       .perform())
        menu_item_element = self._safe_find(menu_item_el)
        self.wait_for_element_visible(menu_item_el)
        mouseAction = (webdriver.ActionChains(self.browser)
                       .move_to_element(menu_item_element)
                       .click(menu_item_element)
                       .perform())


    def hover_by_element(self, webdriver_object, page_element):
        """Find the css element below the webdriver element object and hover.

        """
        element = webdriver_object.find_element_by_css_selector(page_element)
        mouse = webdriver.ActionChains(self.browser)
        mouse.move_to_element(element).perform()

    def click_by_css(self, element, wait_for_element=None):
        """click based on the css given.

        kwargs no_wait, then use send keys to no wait for page load.
               wait_for_element, wait for a passed in element to display
        """
        elem = self._safe_find(element)
        elem.click()
        if wait_for_element:
            self.wait_for_element_present(wait_for_element)

    def submit_by_css(self, element):
        """Submit a form based on the css given.

        kwargs no_wait, then use send keys to no wait for page load.
               wait_for_element, wait for a passed in element to display
        """
        elem = self._safe_find(element)
        self.logger.info( 'submit')
        elem.submit()
        self.logger.info( '** done')

    def clear_text(self, element):
        """Clear text of css element in form.

        """
        elem = self._safe_find(element)
        elem.clear()

    def click_link_text(self, text, wait_for_element=None):
        """Click link text of the element exists, or fail.

        """
        try:
            elem = self.browser.find_element_by_link_text(text)
        except Exception as e:
            self.record_error(e)
        elem.click()
        if wait_for_element:
            self.wait_for_element_present(wait_for_element)

    def click_link_partial_text(self, text, wait_for_element=None):
        """Click by partial link text or report error is not present.

        """
        try:
            elem = self.browser.find_element_by_partial_link_text(text)
        except Exception as e:
            self.record_error(e)
        elem.click()
        if wait_for_element:
            self.wait_for_element_present(wait_for_element)

    def has_link_text(self, text, wait_for_element=None):
        """Return whether or not partial link text is present.
        """
        try:
            elem = self.browser.find_element_by_link_text(text)
            return True
        except NoSuchElementException:
            return False


    def type_by_css(self, element, text):
        """Enter text for provided css selector.

        """
        elem = self.wait_for_element_present(element)
        elem.send_keys(text)

    def type_special_key(self, key_name, element="body"):
        """Type a special key -see selenium/webdriver/common/keys.py.
   
        ex: ARROR_DOWN, TAB, ENTER, SPACE, DOWN... 
        If no element is specified, just send the key press to the body.
        """
        elem = self._safe_find(element)
        elem.send_keys(key_name)


    def get_text_by_css(self, element):
        """Get text of given css selector.

        """
        elem = self.wait_for_element_present(element)
        return elem.text

    def get_size_by_css(self, element):
        """Return dict of height and width of element by css selector.

        """
        elem = self._safe_find(element)
        return elem.size

    def submit_form_text_by_css(self, element, text):
        """Submit form using css selector for form element.
 
        """
        elem = self._safe_find(element)
        elem.send_keys(text)
        time.sleep(1)
        elem.submit()

    def submit_by_css(self, element):
        elem = self._safe_find(element)
        elem.submit()

    def is_element_present(self, element):
        """Return when an element is found on the page.

        """
        try:
            elem = self.browser.find_element_by_css_selector(element)
        except NoSuchElementException:
            return False
        return True

    def count_elements_present(self, element):
        """Return the number of elements (css) found on page.

        """
        try:
            elements_found = self.browser.find_elements_by_css_selector(
                element)
        except NoSuchElementException:
            return 0
        return len(elements_found)

    def is_element_visible(self, element):
        """Return whether element (by css) is visible on the page.

        """
        if not self.is_element_present(element):
            return False
        else:
            return any([e.is_displayed() for e in
                        self.browser.find_elements_by_css_selector(element)])

    def is_unique_text_present(self, element, text):
        """Return whether element (by css) text is unique).

        """
        try:
            elements_found = self.browser.find_elements_by_css_selector(
                element)
        except NoSuchElementException:
            return False
        if len(elements_found) > 1:
            self.record_error(_MULTIPLE_ELS % element)
        else:
            element_text = self.browser.find_element_by_css_selector(
                element).text
            if str(element_text) == text:
                return True
            else:
                return False

    def is_text_present(self, element, text):
        """Return whether element (by css) text is present.

        """
        try:
            elements_found = self.browser.find_elements_by_css_selector(
                element)
        except NoSuchElementException:
            return False
        for elem in elements_found:
            if text == elem.text:
                return True
            else:
                return False

    def verify_text_present(self, element, text):
        """Verify element (by css) text is present.

        """
        elements_found = self.browser.find_elements_by_css_selector(element)
        if len(elements_found) > 1:
            self.record_error(_MULTIPLE_ELS % element)
        else:
            element_text = elements_found[0].text
            if text == element_text:
                return True
            else:
                self.record_error('found:' + element_text +
                                'but was expecting: ' + text)
                return False

    def _poll_for_condition(self, condition, wait_time, error_message):
        """Poll until an arbitrary condition is met """
        start_time = time.time()
        while time.time() - start_time < wait_time:
            if condition():
                return True
            else:
                time.sleep(0.1)
        if condition():
            return True
        else:
            self.record_error(error_message)
            return False

    def wait_for_element_present(self, element, wait_time=5):
        """Wait for element (by css) present on page, within x seconds.

           Settings the default to 5 since we shouldn't have to wait long for 
           most things.  Using implicit_wait in webdriver_base so this
           is a multiplied by the implicit wait value.

        """
        self._poll_for_condition(
            lambda: self.is_element_present(element),
            wait_time,
            "Element %s is not present." % element)
        return self.browser.find_element_by_css_selector(element)

    def wait_for_element_not_present(self, element, wait_time=10):
        """Wait for element (by css) to disappear on page, within 10 seconds.

           Settings the default to 10 since we shouldn't have to wait long for 
           most things.  Using implicit_wait in webdriver_base so this
           is a multiplied by the implicit wait value.

        """

        self._poll_for_condition(
            lambda: self.is_element_present(element) is False,
            wait_time,
            "Element %s is still present." % element)
 
    def wait_for_text_not_present(self, text):
        """Wait for text to disappear on page, within 20 seconds.

        """
        self._poll_for_condition(
            lambda: self.is_text_present(text) is False,
            20,
            'The text: %s is still present after 20 seconds' % text)

    def wait_for_element_visible(self, element):
        """Wait for element (by css) visible on page, within 20 seconds.

        """
        self._poll_for_condition(
            lambda: self.is_element_visible(element),
            20,
            'The element %s is not visible after 20 seconds' % element)

    def wait_for_element_not_visible(self, element):
        """Wait for element (by css) to be hidden on page, within 20 seconds.

        """

        def check_not_visible():
            try:
                self.browser.find_elements_by_css_selector(
                    element).is_displayed()
            except:
                return True
            else:
                return False
        msg = 'The element: %s is still visible after 20 seconds' % element
        return self._poll_for_condition(check_not_visible, 20, msg)

    def get_absolute_url(self, url):
        """Return the full url.

        """
        if url.startswith("http"):
            full_url = url
        else:
            full_url = str(self.base_url) + url
        return full_url

    def get_element_attribute(self, element, html_attribute):
        """Return the attribute of an element (by css).
  
        """
        try:
            elements_found = self.browser.find_elements_by_css_selector(
                element)
        except NoSuchElementException:
            self.record_error("%s does not exist on the page" % element)
        if len(elements_found) > 1:
            self.record_error(MULTIPLE_ELS % element)
        return elements_found[0].get_attribute(html_attribute)

    def get_elements_list(self, element):
        """Return the list of elements (webdriver objects).
  
        """
        self.wait_for_element_present(element)
        elements_found = self.browser.find_elements_by_css_selector(element)
        return elements_found

    def get_sub_elements_list(self, parent_el, child_el):
        """If the parent element exists, return a list of the child elements.
  
        """
        if isinstance(parent_el, basestring):
            if not self.is_element_present(parent_el):
                return None
            else: 
                parent_el = self.browser.find_element_by_css_selector(parent_el)
        try:
            child_els = parent_el.find_elements_by_css_selector(child_el)
            return child_els
        except NoSuchElementException:
            return None



    def open_page(self, url):
        """Open a page by the full url.

        """
        self.browser.get(self.get_absolute_url(url))

    def go_back(self):
        """Go back to previous page.

        """
        self.browser.back()

    def page_down(self, elements):
        """Page down to element (by css).

        elements are a list not a single element to try to page down.
        """
        if not isinstance(elements, basestring):
            for x in elements:
                if self.is_element_present(x):
                    elem = self.browser.find_element_by_css_selector(x)
                    break
        else:
            if self.is_element_present(elements):
                elem = self.browser.find_element_by_css_selector(elements)
        try:
            elem.send_keys("PAGE_DOWN")
        except: 
            pass #Stupid but Chrome has page down issues.

    def log_in(self, username, password):
        """Log in with the specified account type - default as a no-priv user.

        """
        self.logger.info("LOG IN")
        site_obj = Site.objects.get_current()
        self.logger.info(site_obj.domain)

        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore(self._get_session_id())
        user = authenticate(username=username, password=password)
        if user is None:
            raise ValueError("Invalid auth credentials: %r/%r" %
                             (username, password))
        session['_auth_user_id'] = unicode(user.pk)
        session['_auth_user_backend'] = u'localtv.auth_backends.MirocommunityBackend'
        session.save()
        self.logger.info("session saved: %s", session.session_key)
        self.browser.add_cookie({ u'domain': 'localhost:%s' % self.__class__.server_thread.port,
                                  u'name': u'sessionid',
                                  u'value': session.session_key,
                                  u'path': u'/',
                                  u'secure': False,
                                 })
        self.logger.info("cookie saved")

    def _get_session_id(self):
        #jed - modified this because sauce fails when get_cookies used.
        try:
            cookie = self.browser.get_cookie_by_name('sessionid')
            return cookie['value']
        except:
            return None
     
        #for cookie in self.browser.get_cookies():
        #    if (cookie['domain'] == 'unisubs.example.com' and 
        #        cookie['name'] == 'sessionid'):
        #        return cookie['value']
        return None



    def record_error(self, e=None):
        """
            Records an error.
        """
        if not e:
            e = 'webdriver error: ' + self.browser.current_url
        self.logger.error(str(e) + self.browser.current_url)
        #self.browser.close()
        raise ValueError(e)


