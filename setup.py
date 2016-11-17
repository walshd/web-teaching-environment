import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()

requires = [
    'pyramid>1.6',
    'pyramid_beaker',
    'SQLAlchemy',
    'transaction',
    'pyramid_tm',
    'pyramid_debugtoolbar',
    'zope.sqlalchemy',
    'waitress',
    'mimeparse',
    'decorator',
    'docutils',
    'pygments',
    'formencode',
    'alembic',
    'inflect',
    'asset',
    'nine',
    'pycrypto',
    'PyWebTools>=1.0.5'
    ]

setup(name='WebTeachingEnvironment',
      version='1.4.0-dev0',
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
