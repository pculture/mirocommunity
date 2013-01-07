# Miro Community - Easiest way to make a video website
#
# Copyright (C) 2010, 2011, 2012 Participatory Culture Foundation
#
# Miro Community is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Miro Community is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Miro Community.  If not, see <http://www.gnu.org/licenses/>.
"""Basic webdriver commands used in all pages.

"""

import time
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys


class Page(object):
    """Basic webdriver commands available to all pages.

    All pages inherit from Page.

    """
    _DEBUG_ERROR = ".exception_value"
    _MULTIPLE_ELS = "More than 1 of this element was found on the page."

    def __init__(self, testsetup):
        self.browser = testsetup.browser  # BROWSER TO USE FOR TESTING
        self.base_url = testsetup.base_url
        self.testcase = testsetup
        self.browser.implicitly_wait(1)  # seconds

    def quit(self):
        """Quit the browser.

        """
        self.browser.quit()

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
        time.sleep(2)
        a = self.browser.switch_to_alert()
        if action == "accept":
            a.accept()
        elif action == "reject":
            a.dismiss()

    def check(self, element):
        """Check the box for the element provided by css selector.

        """
        el = self.browser.find_element_by_css_selector(element)
        if not el.is_selected():
            el.click()

    def uncheck(self, element):
        """Uncheck the box for the element provided by css selector.

        """

        el = self.browser.find_element_by_css_selector(element)
        if el.is_selected():
            el.click()

    def select_option_by_text(self, element, text):
        """Select an option based on text of the css selector.

        """
        select = Select(self.browser.find_element_by_css_selector(element))
        print select.options
        select.select_by_visible_text(text)

    def hover_by_css(self, element):
        """Hover over element of provided css selector.

        """
        mouse = webdriver.ActionChains(self.browser)
        mouse.move_to_element(element).perform()

    def click_by_css(self, element, wait_for_element=None, no_wait=False):
        """click based on the css given.

        kwargs no_wait, then use send keys to no wait for page load.
               wait_for_element, wait for a passed in element to display
        """
        try:
            elem = self.browser.find_element_by_css_selector(element)
        except:
            self.record_error(elem + "not found")
        if no_wait:
            elem.send_keys(Keys.ENTER)
        else:
            elem.click()
        if wait_for_element:
            self.wait_for_element_present(wait_for_element)

    def clear_text(self, element):
        """Clear text of css element in form.

        """
        elem = self.wait_for_element_present(element)
        elem.clear()

    def click_link_text(self, text, wait_for_element=None):
        """Click link text of the element exists, or fail.

        """
        try:
            elem = self.browser.find_element_by_link_text(text)
        except:
            url = self.browser.current_url
            self.record_error("link text: {0} not found on current page:"
                              " {1}".format(str(text), str(url)))
        elem.click()
        if wait_for_element:
            self.wait_for_element_present(wait_for_element)

    def click_link_partial_text(self, text, wait_for_element=None):
        """Click by partial link text or report error is not present.

        """
        try:
            elem = self.browser.find_element_by_partial_link_text(text)
        except:
            url = self.browser.current_url
            self.record_error("partial link text: {0} not found on current "
                              "page:{1}".format(str(text), str(url)))
        elem.click()
        if wait_for_element:
            self.wait_for_element_present(wait_for_element)

    def type_by_css(self, element, text):
        """Enter text for provided css selector.

        """
        elem = self.browser.find_element_by_css_selector(element)
        elem.send_keys(text)

    def get_text_by_css(self, element):
        """Get text of given css selector.

        """
        return self.browser.find_element_by_css_selector(element).text

    def get_size_by_css(self, element):
        """Return dict of height and width of element by css selector.

        """
        return self.browser.find_element_by_css_selector(element).size

    def submit_form_text_by_css(self, element, text):
        """Submit form using css selector for form element.

        """
        elem = self.browser.find_element_by_css_selector(element)
        elem.send_keys(text)
        elem.submit()

    def is_element_present(self, element):
        """Return when an element is found on the page.

        """
        try:
            elements_found = self.browser.find_elements_by_css_selector(
                element)
        except NoSuchElementException():
            return False
        if len(elements_found) > 0:
            return True
        else:
            return False

    def count_elements_present(self, element):
        """Return the number of elements (css) found on page.

        """
        try:
            elements_found = self.browser.find_elements_by_css_selector(
                element)
        except NoSuchElementException():
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
        except NoSuchElementException():
            return False
        if len(elements_found) > 1:
            raise Exception(self._MULTIPLE_ELS.format(element))
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
        except NoSuchElementException():
            return False
        for elem in elements_found:
            if text == elem.text:
                return True
            else:
                return False

    def verify_text_present(self, element, expected_text):
        """Verify element (by css) text is present.

        """
        elements_found = self.browser.find_elements_by_css_selector(element)
        for el in elements_found:
            print el.text
            if expected_text == el.text:
                return True
        else:
            self.record_error('did not find %s' % expected_text)

    def wait_for_element_present(self, element, wait_time=5):
        """Wait for element (by css) present on page, within x seconds.

           Settings the default to 5 since we shouldn't have to wait long for
           most things.  If using implicit_wait in webdriver_base so this
           is multiplied by the implicit wait value.

        """
        for i in range(wait_time):
            try:
                time.sleep(1)
                if self.is_element_present(element):
                    return self.browser.find_element_by_css_selector(element)
            except:
                pass
        else:
            self.record_error("Element %s is not present." % element)

    def wait_for_element_not_present(self, element, wait_time=10):
        """Wait for element (by css) to disappear on page, within 10 seconds.

           Settings the default to 10 since we shouldn't have to wait long for
           most things.  If using implicit_wait in webdriver_base so this
           is a multiplied by the implicit wait value.

        """

        for i in range(wait_time):
            try:
                time.sleep(1)
                if self.is_element_present(element) is False:
                    break
            except:
                pass
        else:
            self.record_error("Element %s is still present." % element)

    def wait_for_text_not_present(self, text):
        """Wait for text to disappear on page, within 20 seconds.

        """
        for i in range(20):
            try:
                time.sleep(1)
                if self.is_text_present(text) is False:
                    break
            except:
                pass
        else:
            raise Exception("%s is still present" % text)

    def wait_for_element_visible(self, element):
        """Wait for element (by css) visible on page, within 20 seconds.

        """

        for i in range(20):
            time.sleep(1)
            if self.is_element_visible(element):
                break
        else:
            self.record_error(element + ' has not appeared')

    def wait_for_element_not_visible(self, element):
        """Wait for element (by css) to be hidden on page, within 20 seconds.

        """
        for i in range(20):
            try:
                time.sleep(1)
                self.browser.find_elements_by_css_selector(
                    element).is_displayed()
            except:
                break
        else:
            self.record_error(element + ' has not disappeared')

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
            raise Exception("%s does not exist on the page" % element)

        if len(elements_found) > 1:
            raise Exception(self._MULTIPLE_ELS.format(element))
        return elements_found[0].get_attribute(html_attribute)

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
        elem.send_keys("PAGE_DOWN")

    def record_error(self, e=None):
        """
            Records an error.
        """
        if not e:
            e = 'webdriver error' + self.browser.current_url
        print '-------------------'
        print 'Error at ' + self.browser.current_url
        print '-------------------'
        self.testcase.tearDown()
        raise AssertionError(str(e))
