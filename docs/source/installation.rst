============
Installation
============

This walks you through installing Miro LocalTv on your system.


Setting up virtualenv (optional)
================================

You don't necessarily need to use virtualenv, but it is highly
recommended.  Indeed, the rest of the tutorial assumes that you do.
You *can* manually manage your pythonpath and etc, but virtualenv does
that all for you and gives you a nice isolated environment.  This is
great, for example, if you have multiple websites that all need
different Django versions, using multiple virtualenv environments can
help isolate them all so that they can cleanly coexist on the same
server.

To install virtualenv, use ``easy_install``::

    sudo easy_install -UaZ virtualenv

to get the base virtualenv executable installed on your system (which
is really just used for setting up virtualenv environments).

See http://pypi.python.org/pypi/virtualenv for more details.


Installing Miro Community
=========================

Building the virtual environment
--------------------------------

Assuming you already have the virtualenv executable installed, you can
install a virtualenv environment like so::

    virtualenv /path/to/virtualenv

replacing ``/path/to/virtualenv`` with the directory you want the
virtual environment to be in.

To activate the virtual enviroment, ``cd`` to the virtual environment
directory and type the command::

    source bin/activate

You later deactivate the virtual environment with::

    deactivate


Building the directory structure
--------------------------------
Recommended additional directories


The general structure looks like this:

* *bin/*: binaries and executables

* *lib/*: python modules, both stdlib, those installed with
  setuptools, and those not in development

You don't have to do this, but I think this makes for a pretty clean
virtualenv environment to add these following directories:

* *src/*: python modules in development

* *djangoproject/*: subdirectories with django settings and root
  urls for different sites should live in here

Pip
---

The easiest way to install Miro Community is with Pip (Pip Installs Packages):

    easy_install -Uaz pip

requirements.txt
----------------

Once Pip is installed, it's easy to install Miro Community and its dependencies:

    pip install -r http://git.participatoryculture.org/localtv/plain/requirements.txt

RabbitMQ
--------

Miro Community requires an AMQP server to run.  We recommend RabbitMQ
(http://www.rabbitmq.com/) but any server should work.  Check the documentation
on their site for instructions on installing it.


Setting up the Django project
==============================

There's an example project in src/miro-community/example_project/.  You'll need
to update the settings.py file to point to the right paths, and to include the
keys for the Vimeo, uStream, bit.ly, and reCaptcha.


Apache / nginx / web server config
==================================

There are plenty of tutorials out there on how to configure this kind
of thing.  My only point to make is that if you need to use a fastcgi
script with apache or whatever, you want to use the python binary in
the bin/ directory of your virtualenv environment, like::

    #!/var/www/localtv/bin/python
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    os.environ['DJANGO_SETTINGS_MODULE'] = 'project.settings'
    from django.core.servers.fastcgi import runfastcgi
    runfastcgi(daemonize='false')

