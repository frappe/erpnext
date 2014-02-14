from setuptools import setup, find_packages
import os

version = '4.0.0-wip'

setup(
    name='erpnext',
    version=version,
    description='Open Source ERP',
    author='Web Notes Technologies',
    author_email='info@erpnext.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=("webnotes",),
)