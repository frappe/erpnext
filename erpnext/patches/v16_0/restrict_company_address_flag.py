from erpnext.setup.install import (
	create_address_and_contact_custom_fields,
	setup_company_address_permissions,
)


def execute():
	"""Move the company address flag to permlevel 1 and grant it to the managing roles."""
	create_address_and_contact_custom_fields()
	setup_company_address_permissions()
