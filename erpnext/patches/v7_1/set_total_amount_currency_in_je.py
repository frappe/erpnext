import frappe
from erpnext import get_default_currency

def execute():
	frappe.reload_doc("accounts", "doctype", "journal_entry")

	frappe.db.sql(""" update `tabJournal Entry` set total_amount_currency = %s
		where ifnull(multi_currency, 0) = 0
		and (pay_to_recd_from is not null or pay_to_recd_from != "") """, get_default_currency())

	for je in frappe.db.sql(""" select name from `tabJournal Entry` where multi_currency = 1
		and (pay_to_recd_from is not null or pay_to_recd_from != "")""", as_dict=1):

		doc = frappe.get_doc("Journal Entry", je.name)
		for d in doc.get('accounts'):
			if d.party_type and d.party:
				total_amount_currency = d.account_currency

			elif frappe.db.get_value("Account", d.account, "account_type") in ["Bank", "Cash"]:
				total_amount_currency = d.account_currency

		frappe.db.set_value("Journal Entry", je.name, "total_amount_currency",
			total_amount_currency, update_modified=False)
