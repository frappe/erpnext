import frappe

def execute():
	from erpnext.setup.page.setup_wizard.install_fixtures import get_journal_entry_types
	for d in get_journal_entry_types():
		frappe.get_doc(d).insert(ignore_permissions=True)
