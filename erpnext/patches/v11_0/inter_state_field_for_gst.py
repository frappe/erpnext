import frappe
from erpnext.regional.india.setup  import make_custom_fields

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return
	frappe.reload_doc("hr", "doctype", "Employee Tax Exemption Declaration")
	frappe.reload_doc("hr", "doctype", "Employee Tax Exemption Proof Submission")
	make_custom_fields()

	frappe.reload_doc("accounts", "doctype", "sales_taxes_and_charges")
	frappe.reload_doc("accounts", "doctype", "purchase_taxes_and_charges")
	frappe.reload_doc("accounts", "doctype", "sales_taxes_and_charges_template")
	frappe.reload_doc("accounts", "doctype", "purchase_taxes_and_charges_template")

	# set is_inter_state in Taxes And Charges Templates
	if frappe.db.has_column("Sales Taxes and Charges Template", "is_inter_state") and\
		frappe.db.has_column("Purchase Taxes and Charges Template", "is_inter_state"):

		igst_accounts = set(frappe.db.sql_list('''SELECT igst_account from `tabGST Account` WHERE parent = "GST Settings"'''))
		cgst_accounts = set(frappe.db.sql_list('''SELECT cgst_account FROM `tabGST Account` WHERE parenttype = "GST Settings"'''))

		when_then_sales = get_formatted_data("Sales Taxes and Charges", igst_accounts, cgst_accounts)
		when_then_purchase = get_formatted_data("Purchase Taxes and Charges", igst_accounts, cgst_accounts)

		if when_then_sales:
			frappe.db.sql('''update `tabSales Taxes and Charges Template`
				set is_inter_state = Case {when_then} Else 0 End
			'''.format(when_then=" ".join(when_then_sales)))

		if when_then_purchase:
			frappe.db.sql('''update `tabPurchase Taxes and Charges Template`
				set is_inter_state = Case {when_then} Else 0 End
			'''.format(when_then=" ".join(when_then_purchase)))

def get_formatted_data(doctype, igst_accounts, cgst_accounts):
	# fetch all the rows data from child table
	all_details = frappe.db.sql('''
		select parent, account_head from `tab{doctype}`
		where parenttype="{doctype} Template"'''.format(doctype=doctype), as_dict=True)

	# group the data in the form "parent: [list of accounts]""
	group_detail = {}
	for i in all_details:
		if  not i['parent'] in group_detail: group_detail[i['parent']] = []
		for j in all_details:
			if i['parent']==j['parent']:
				group_detail[i['parent']].append(j['account_head'])

	# form when_then condition based on - if list of accounts for a document
	# matches any account in igst_accounts list and not matches any in cgst_accounts list
	when_then = []
	for i in group_detail:
		temp = set(group_detail[i])
		if not temp.isdisjoint(igst_accounts) and temp.isdisjoint(cgst_accounts):
			when_then.append('''When name='{name}' Then 1'''.format(name=i))

	return when_then
