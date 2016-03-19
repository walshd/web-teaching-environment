**********
Deployment
**********

In-production deployment has been tested using `Apache2`_ and `mod_wsgi`_.
For other deployment scenarios, please consult the `pyramid deployment`_
documentation.

Deploying with Apache2 & mod_wsgi
=================================

To deploy the Experiment Support System via `Apache2`_ and `mod_wsgi`_ add the
following settings to the VirtualHost configuration::

    WSGIDaemonProcess wte user=www-data group=www-data processes=1 threads=4 python-path=/path/to/virtualenv/lib/python2.7/site-packages
    WSGIScriptAlias /web-teaching-environment /path/to/the/application.wsgi
    <Location /wte>
        WSGIProcessGroup wte
    </Location>

.. note:: Use the ``processes`` option to specify the number of parallel
   processes to create. How many you need depends on the amount of load
   you are expecting.

Then create the following script to to run the application via `WSGI`_. Adapt
it by replacing the paths with the paths to where the Web Teaching Environment
is installed::

    import os
    os.chdir(os.path.dirname(__file__))
    import site
    import sys

    # Remember original sys.path.
    prev_sys_path = list(sys.path) 

    site.addsitedir('/path/to/virtualenv/lib/python2.7/site-packages')

    # Reorder sys.path so new directories at the front.
    new_sys_path = [] 
    for item in list(sys.path): 
        if item not in prev_sys_path: 
            new_sys_path.append(item) 
            sys.path.remove(item) 
    sys.path[:0] = new_sys_path 

    from pyramid.paster import get_app
    from paste.script.util.logging_config import fileConfig
    fileConfig('/path/to/the/application/production.ini')
    application = get_app('/path/to/the/application/production.ini', 'main')


.. _WSGI: http://wsgi.readthedocs.org/en/latest/
.. _mod_wsgi: http://code.google.com/p/modwsgi/
.. _Apache2: http://httpd.apache.org/
.. _`pyramid deployment`: http://docs.pylonsproject.org/projects/pyramid_cookbook/en/latest/deployment/index.html

Running Timed Tasks
===================

The Web Teaching Environment provides a number of automated tasks that can be
set up from within it. To ensure that the automated tasks are actually executed
the following command needs to be run regularly::

   WTE run-timed-tasks <configuration.ini>

In the Web Teaching Environment the automated tasks can be scheduled to a
maximum precision of one (1) minute. To ensure that tasks are run close to the
desired time, the command should be run once a minute.

Running the command has been tested using Cron, but any other command scheduler
should work as well. If you have installed WTE into a virtualenv, then in your
command scheduler instructions you need to activate the virtualenv first,
before running the command.

.. note:: You should probably not run the command more frequently than once
   every 20 seconds as otherwise it is possible that tasks are run multiple
   times.
