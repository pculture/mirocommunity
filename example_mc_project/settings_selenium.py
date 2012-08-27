from settings import *
import os

INSTALLED_APPS + ('django_nose', 'localtv.tests.selenium')
RESULTS_DIR = os.path.join(os.path.dirname(os.getcwd()), 'localtv', 'tests', 'selenium', 'Results')

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

TEST_BROWSER = 'Firefox'

xunitfile = '--xunit-file=%s' % os.path.join(RESULTS_DIR, "nosetests.xml")
NOSE_ARGS = ['--with-xunit',
             #'--xunit-file=nosetests.xml',
             xunitfile,
             '--nocapture',
             '--nologcapture', 
             '--logging-filter=-selenium.webdriver.remote.remote_connection', 
             '--verbosity=2'
            ]
