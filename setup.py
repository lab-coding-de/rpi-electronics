#!/usr/bin/env python
""" A collection of python modules for interfacing electronics with the Raspberry Pi.

"""

from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, "README.rst")) as fobj:
    readme = fobj.read()

config = {
    "name": "rpi-electronics",
    "version": "0.1.1",
    "author": "Falk Ziegler",
    "author_email": "falk.ziegler@lab-coding.de",
    "maintainer": "Falk Ziegler",
    "license": "MIT",
    "description": (__doc__ or "").split("\n")[0],
    "long_description": readme,
    "install_requires": [],
    "packages": find_packages(exclude=[])
}

setup(**config)
