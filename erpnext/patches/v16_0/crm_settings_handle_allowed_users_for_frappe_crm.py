import frappe


def execute():
	from erpnext.crm.frappe_crm_api import is_crm_installed, remove_allowed_users_on_crm_install

	if not is_crm_installed():
		return

	remove_allowed_users_on_crm_install()
