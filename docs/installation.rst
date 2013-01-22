Installation
============

.. note:: There are a couple of things that this installation guide assumes:

	* That you have installed `Mercurial`_ and `Git`_ on your system.
	* That you have installed `Python`_ and `virtualenv`_ on your system.

    These are basic instructions for installing a copy of Miro Community for local development and testing. You will need to modify the installation for a production environment - for example, you will need to draw up a requirements file that describes your production environment, and you will need to use your own settings file.

.. _Mercurial: http://mercurial.selenic.com/
.. _Git: http://git-scm.com/
.. _Python: http://python.org
.. _virtualenv: http://pypi.python.org/pypi/virtualenv

Creating a virtualenv
+++++++++++++++++++++

First up, you'll want to create and activate a virtual environment somewhere on your computer::

    virtualenv testenv
    cd testenv
    source bin/activate


Installing Miro Community
+++++++++++++++++++++++++

Run the following commands from the root of your (installed and activated) virtualenv::

    pip install -e git+git://github.com/pculture/mirocommunity.git@1.9.1#egg=mirocommunity --no-deps
    cd src/mirocommunity/test_mc_project
    pip install -r requirements.txt
    python manage.py syncdb # This will prompt you to create an admin user
    python manage.py runserver

Congratulations! You're running a local testing instance of Miro Community! You can access it in your web browser by navigating to `http://127.0.0.1:8000/ <http://127.0.0.1:8000>`_, and you can get the admin by navigating to `http://127.0.0.1:8000/admin/ <http://127.0.0.1:8000/admin/>`_.

If this is your first time using a Django app, you should definitely check out the `Django tutorial`_ to get a better understanding of what's going on, how to change the project settings, etc. The testing project can be a helpful place to start, but it is not meant to be used in a production setting.

.. _Django tutorial: https://docs.djangoproject.com/en/1.3/intro/tutorial01/

.. warning:: Using the test project unaltered for a production server would be *extremely insecure*, because its ``SECRET_KEY`` is not secret.
