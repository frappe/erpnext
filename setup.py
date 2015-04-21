from setuptools import setup, find_packages

<<<<<<< HEAD
version = "5.0.0-beta"
=======
version = "4.25.1"
>>>>>>> 3b8682f534f12bd72e52685d1286a2cc72713857

with open("requirements.txt", "r") as f:
	install_requires = f.readlines()

setup(
    name='erpnext',
    version=version,
    description='Open Source ERP',
    author='Frappe Technologies',
    author_email='info@erpnext.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
