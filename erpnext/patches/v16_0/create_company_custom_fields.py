from erpnext.setup.install import create_custom_company_links


def execute():
	"""Add link fields to Company in Email Account and Communication."""
	create_custom_company_links()
