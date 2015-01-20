# coding: utf-8
import os
import re

from setuptools import setup, find_packages


# https://bitbucket.org/zzzeek/alembic/raw/f38eaad4a80d7e3d893c3044162971971ae0
# 09bf/setup.py
with open(
    os.path.join(os.path.dirname(__file__), 'cicli', 'app.py')
) as app_file:
    VERSION = re.compile(
        r".*__version__ = '(.*?)'", re.S
    ).match(app_file.read()).group(1)

with open("README.md") as readme:
    long_description = readme.read()

setup(
    name='cicli',
    description=(
        'CiCLI is a CircleCI command line tool.'
    ),
    long_description=long_description,
    version=VERSION,
    url='https://github.com/fastmonkeys/cicli',
    license='BSD',
    author=u'Teemu Kokkonen, Raúl García',
    author_email='teemu@fastmonkeys.com, raul@fastmonkeys.com',
    packages=find_packages('.', exclude=['examples*', 'test*']),
    entry_points={
        'console_scripts': [ 'cicli = cicli.app:main' ],
    },
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS :: MacOS X',
        'Topic :: Utilities',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Database',
        'Topic :: Software Development :: Version Control',
    ],
    install_requires = [
        'click==3.1',
        'dateutils==0.6.6',
        'requests==2.5.1'
    ]
)
