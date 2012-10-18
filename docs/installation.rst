Installation
============

.. note:: There are a couple of things that this installation guide assumes:

	* That you have installed `Mercurial`_ and `Git`_ on your system.
	* That you have installed `Python 2.7`_ and `virtualenv`_ on your system.
	* That you have created and activated a virtualenv.

.. _Mercurial: http://mercurial.selenic.com/
.. _Git: http://git-scm.com/
.. _Python 2.7: http://python.org
.. _virtualenv: http://pypi.python.org/pypi/virtualenv

Run the following commands::

	pip install -r https://raw.github.com/pculture/mirocommunity/1.8.6/example_mc_project/requirements.txt
	cd lib/python2.7/site-packages/example_mc_project
	python manage.py syncdb # This will prompt you to create an admin user
	python manage.py runserver

Congratulations! You're running a local instance of Miro Community! You can access it in your web browser by navigating to `http://127.0.0.1:8000/ <http://127.0.0.1:8000>`_, and you can get the admin by navigating to `http://127.0.0.1:8000/admin/ <http://127.0.0.1:8000/admin/>`_.

If this is your first time using a Django app, you should definitely check out the `Django tutorial`_ to get a better understanding of what's going on, how to change the project settings, etc. In the long run, the example_project is meant as just that – an example.

.. _Django tutorial: https://docs.djangoproject.com/en/1.3/intro/tutorial01/

.. warning:: Using the example project unaltered for a production server would be *extremely insecure*. Don't do it.