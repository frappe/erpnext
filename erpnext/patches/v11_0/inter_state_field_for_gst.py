import frappe
from erpnext.regional.india.setup  import make_custom_fields

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	make_custom_fields()

	frappe.reload_doc("accounts", "doctype", "sales_taxes_and_charges")
	frappe.reload_doc("accounts", "doctype", "purchase_taxes_and_charges")
	frappe.reload_doc("accounts", "doctype", "sales_taxes_and_charges_template")
	frappe.reload_doc("accounts", "doctype", "purchase_taxes_and_charges_template")

	if frappe.db.has_column("Sales Taxes And Charges Template", "is_inter_state") and\
		frappe.db.has_column("Purchase Taxes And Charges Template", "is_inter_state"):

		igst_accounts = frappe.get_list("GST Account",
		{"parent": "GST Settings"},
		["igst_account"], as_list=True)

		cgst_accounts = frappe.get_list("GST Account",
		{"parent": "GST Settings"},
		["cgst_account"], as_list=True)

		if not igst_accounts:
			return
		for doctype in ["Sales Taxes And Charges", "Purchase Taxes And Charges"]:
			frappe.db.sql('''
				UPDATE `tab%s Template` tct, `tab%s` tc
				SET tct.is_inter_state = 1
				WHERE
					tct.name = tc.parent
				AND
					tc.account_head in (%s)
				AND
					tc.account_head not in ( %s)
			''', (doctype, doctype, d.get("igst_account"), d.get("cgst_account"))

			select * from `tabSales Taxes And Charges Template` st, `tabSales Taxes And Charges` stc where stc.parent = st.name and stc.account_head in ("Freight and Forwarding Charges - NFECT", "Freight and Forwarding Charges - _TC") and stc.account_head not in ("CGST - NFECT", "Creditors - T")
