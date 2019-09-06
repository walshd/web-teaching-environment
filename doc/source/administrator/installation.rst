************
Installation
************

The Web Teaching Environment will run on Python 2.7, Python 3.4, and
Python 3.5 (recommended).

Core System
===========

.. To install the Web Teaching Environment, download the latest version from
   https://bitbucket.org/mhall/web-teaching-environment and install using the
   following command::

   pip install WebTeachingEnvironment-x.y.z.tar.gz

Due to the move to Github the Web Teaching Environment is currently only
available as source::

  git clone https://github.com/scmmmh/web-teaching-environment.git
  cd web-teaching-environment
  python setup.py install

It is recommended that you install the Web Teaching Environment into a
`virtual environment`_.

To enable the Web Teaching Environment to work, you must then install either
`pycryptopp`_ (Python 2.7 only) or `PyCrypto`_ package (Python 2.7 and 3.*)
to enable the use of session cookies. To install `pycryptopp`_ run::

  pip install pycryptopp

To install `PyCrypto`_ run::

  pip install pycrypto

Database Access
===============

You will also need to install database access libraries for the database you
intend to use. The Web Teaching Environment has been tested with `PostgreSQL`_
and `MySQL`_. `SQLite`_ is not supported, as it does not provide the features
required to migrate the database when the Web Teaching Environment is upgraded.
`Other database systems`_ that are supported by `SQLAlchemy`_ can be used, but
have not been tested.

To use PostgreSQL as the database, run::
  
  pip install psycopg2

For MySQL run::

  pip install mysql-python

After the installation has completed, move on to the :doc:`setup`.

.. _`virtual environment`: https://pypi.python.org/pypi/virtualenv
.. _`pycryptopp`: https://pypi.python.org/pypi/pycryptopp
.. _`PyCrypto`: https://www.dlitz.net/software/pycrypto/
.. _`PostgreSQL`: http://www.postgresql.org/
.. _`MySQL`: http://www.mysql.com/
.. _`SQLite`: http://www.sqlite.org/
.. _`Other database systems`: http://docs.sqlalchemy.org/en/rel_0_8/core/engines.html#supported-databases
.. _`SQLAlchemy`: http://www.sqlalchemy.org/
