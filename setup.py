# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in xhr/__init__.py
from xhr import __version__ as version

setup(
	name='xhr',
	version=version,
	description='X HR',
	author='vinhnguyen.t090@gmail.com',
	author_email='vinhnguyen.t090@gmail.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
