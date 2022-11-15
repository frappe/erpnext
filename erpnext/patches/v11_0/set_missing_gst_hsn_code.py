import frappe
from erpnext.controllers.taxes_and_totals import get_itemised_tax_breakup_html

def execute():
	company = frappe.db.sql_list("select name from tabCompany where country = 'India'")
	if not company:
		return

	doctypes = ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice",
		"Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice"]

	for dt in doctypes:
		date_field = "posting_date"
		if dt in ["Quotation", "Sales Order", "Supplier Quotation", "Purchase Order"]:
			date_field = "transaction_date"

		transactions = frappe.db.sql("""
			select dt.name, dt_item.name as child_name
			from `tab{dt}` dt, `tab{dt} Item` dt_item
			where dt.name = dt_item.parent
				and dt.`{date_field}` > '2018-06-01'
				and dt.docstatus = 1
				and ifnull(dt_item.gst_hsn_code, '') = ''
				and ifnull(dt_item.item_code, '') != ''
				and dt.company in ({company})
		""".format(dt=dt, date_field=date_field, company=", ".join(['%s']*len(company))), tuple(company), as_dict=1)

		if not transactions:
			continue

		transaction_rows_name = [d.child_name for d in transactions]

		frappe.db.sql("""
			update `tab{dt} Item` dt_item
			set dt_item.gst_hsn_code = (select gst_hsn_code from tabItem where name=dt_item.item_code)
			where dt_item.name in ({rows_name})
		""".format(dt=dt, rows_name=", ".join(['%s']*len(transaction_rows_name))), tuple(transaction_rows_name))

		parent = set([d.name for d in transactions])
		for t in list(parent):
			trans_doc = frappe.get_doc(dt, t)
			hsnwise_tax = get_itemised_tax_breakup_html(trans_doc)
			frappe.db.set_value(dt, t, "other_charges_calculation", hsnwise_tax, update_modified=False)