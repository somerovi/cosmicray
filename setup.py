#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Note: To use the 'upload' functionality of this file, you must:
#   $ pip install twine

import io
import os
import sys
from shutil import rmtree

from setuptools import find_packages, setup, Command

AUTHOR = 'Samir Omerovic'
EMAIL = 'somerovi@gmail.com'
URL = 'https://github.com/somerovi/cosmicray'
NAME = 'cosmicray'
SUMMARY = "Develop a client for your HTTP API and document its quirks and features"
DESCRIPTION = ''
PACKAGES = ['cosmicray']
REQUIRED = [
    'colorama==0.3.9',
    'requests==2.18.4',
    'six==1.11.0'
]

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.rst' is present in your MANIFEST.in file!
with io.open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    DESCRIPTION = '\n' + f.read()

# Load the package's __version__.py module as a dictionary.
about = {}
with open(os.path.join(here, NAME, '__version__.py')) as f:
    exec(f.read(), about)

class UploadCommand(Command):
    """Support setup.py upload."""

    description = 'Build and publish the package.'
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status('Removing previous builds…')
            rmtree(os.path.join(here, 'dist'))
        except OSError:
            pass

        self.status('Building Source and Wheel (universal) distribution…')
        cmd = '{0} setup.py sdist bdist_wheel --universal'.format(sys.executable)
        os.system(cmd)

        twine = sys.executable.replace('python', 'twine')
        self.status('Uploading the package to PyPi via Twine…')
        os.system('{0} upload dist/*'.format(twine))

        sys.exit()


# Where the magic happens:
setup(
    name=NAME,
    version=about['__version__'],
    description=SUMMARY,
    long_description=DESCRIPTION,
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    packages=PACKAGES,
    install_requires=REQUIRED,
    include_package_data=True,
    license='MIT',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],
    # $ setup.py publish support.
    cmdclass={
        'upload': UploadCommand,
    },
)
