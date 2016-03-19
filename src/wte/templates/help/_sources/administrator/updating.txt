********
Updating
********

Preparation
===========

Before updating the Web Teaching Environment, perform the following three
steps to put the Web Teaching Environment into a state that is ready for the
update:

1. The first step is to download the latest Web Teaching Environment release
   from https://bitbucket.org/mhall/web-teaching-environment.
2. Next stop the Web Teaching Environment application. How to do this depends
   on how you have deployed it (see :doc:`deployment`).
3. Finally, make a backup of the database. This will allow you to roll-back the
   application in case of there being any issues that arise during or after the
   update.

Update
======

To perform the actual update of the Web Teaching Environment, first activate
the `virtual environment`_ you previously installed the Web Teaching
Environment into. To install the new version you downloaded, run the following
command:: 

  pip install WebTeachingEnvironment-x.y.z.tar.gz

This will install the downloaded version and also automatically install and
update any libraries the Web Teaching Environment depends on.

.. Next update the database to the latest schema by running::

   WTE update-database <configuration.ini>

Restart
=======

You can then re-start the Web Teaching Environment and test that the update
has installed successfully.

.. _`virtual environment`: https://pypi.python.org/pypi/virtualenv
