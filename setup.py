import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()

requires = [
    'pyramid>1.6',
    'pyramid_beaker<=0.8',
    'SQLAlchemy<1.2',
    'transaction<2.2',
    'pyramid_tm<2.3',
    'pyramid_debugtoolbar',
    'zope.sqlalchemy<0.8',
    'waitress<1.2',
    'mimeparse<0.2',
    'decorator<4.2',
    'docutils<0.15',
    'pygments<=2.2.0',
    'formencode<=1.3.1',
    'alembic<=0.9.6',
    'inflect<=0.2.5',
    'asset<=0.6.12',
    'nine',
    'pycrypto<=2.6.1',
    'PyWebTools>=1.0.5'
    ]

setup(name='WebTeachingEnvironment',
      version='1.3.3',
      description='The Web Teaching Environment',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages('src'),
      package_dir = {'': 'src'},
      include_package_data=True,
      zip_safe=False,
      test_suite='wte',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = wte:main
      [console_scripts]
      WTE = wte.scripts.main:main
      """,
      )
