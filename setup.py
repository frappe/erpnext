from setuptools import setup, find_packages

<<<<<<< HEAD
version = "5.0.0-alpha"
=======
version = "4.12.0"
>>>>>>> upstream/develop

with open("requirements.txt", "r") as f:
	install_requires = f.readlines()

setup(
    name='erpnext',
    version=version,
    description='Open Source ERP',
    author='Web Notes Technologies',
    author_email='info@erpnext.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
