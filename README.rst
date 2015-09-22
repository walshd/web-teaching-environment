Web Teaching Environment README
===============================

This README is primarily written for developers wishing to work on the Web
Teaching Environment. If you just want to use the Web Teaching Environment,
please consult the documentation at http://web-teaching-environment.readthedocs.org/en/latest/

Getting Started
---------------

- Clone the Mercurial repository:
  ``hg clone https://bitbucket.org/mhall/web-teaching-environment``;

- Create a new Python `virtualenv`_. If you have never used Python
  virtualenvironments, then read up on them first. For ease of interaction with
  Python virtualenvs, you can use `virtualenvwrapper`_ or
  `virtualenvwrapper-win`_;

- Setup the development environment and install the required packages:
  ``python setup.py develop``;

- Install `pycryptopp`_ (``pip install pycryptopp`) or `PyCrypto`_;

- Install the database adapter for the database you want. The Web Teaching
  Environment is tested on `MySQL`_ (``pip install mysql-python``) and
  `PostgreSQL`_ (``pip install psycopg2``);

- Generate a configuration file: ``WTE generate-config``;

- Create the database: ``WTE initialise-database <configuration.ini>``;

- Run the server: ``pserve --reload <configuration.ini>``.

.. _`virtualenv`: http://virtualenv.readthedocs.org
.. _`virtualenvwrapper`: http://virtualenvwrapper.readthedocs.org
.. _`virtualenvwrapper-win`: https://pypi.python.org/pypi/virtualenvwrapper-win
.. _`pycryptopp`: https://pypi.python.org/pypi/pycryptopp
.. _`PyCrypto`: https://www.dlitz.net/software/pycrypto/
.. _`PostgreSQL`: http://www.postgresql.org/
.. _`MySQL`: http://www.mysql.com/

Documentation
-------------

The documentation is `provided online`_.

.. image:: https://readthedocs.org/projects/web-teaching-environment/badge/?version=latest

To generate the documentation:

- Activate the ``virtualenv``;

- Install the `Sphinx`_ documentation generator: ``pip install Sphinx``;

- Switch into the ``doc`` directory;

- Build the documentation: ``make html``.

.. _`Sphinx`: http://sphinx-doc.org
.. _`provided online`: http://web-teaching-environment.readthedocs.org/
