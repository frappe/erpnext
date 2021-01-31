import frappe
from erpnext.accounts.party import get_party_name


def execute():
	frappe.reload_doc('accounts', 'doctype', 'journal_entry')
	frappe.reload_doc('accounts', 'doctype', 'journal_entry_account')

	names = frappe.db.sql_list("""
		select distinct parent
		from `tabJournal Entry Account`
		where ifnull(party_type, '') != '' and ifnull(party, '') != ''
	""")

	for name in names:
		doc = frappe.get_doc("Journal Entry", name)
		for d in doc.get("accounts"):
			if d.party_type and d.party:
				d.party_name = get_party_name(d.party_type, d.party)
				frappe.db.set_value("Journal Entry Account", d.name, "party_name", d.party_name,
					update_modified=False)

		doc.clear_cache()
