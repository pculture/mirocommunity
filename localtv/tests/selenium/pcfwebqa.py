#!/usr/bin/env python

from selenium import webdriver
browser = webdriver.Firefox() #BROWSER TO USE FOR TESTING
#base_url = "http://localhost:8081"
base_url = "http://dalmatia.dev.mirocommunity.org/" #URL OF THE SUT
admin_user = "seleniumTestAdmin" # ADMIN USER
admin_pass = "TestAdmin" # ADMIN PASSWORD
normal_user = "seleniumTestUser"
normal_pass = "selenium"

