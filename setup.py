from setuptools import setup, find_packages
from pip.req import parse_requirements

version = "6.14.0"
requirements = parse_requirements("requirements.txt", session="")

setup(
	name='erpnext',
	version=version,
	description='Open Source ERP',
	author='Frappe Technologies',
	author_email='info@erpnext.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=[str(ir.req) for ir in requirements],
	dependency_links=[str(ir._link) for ir in requirements if ir._link]
)
