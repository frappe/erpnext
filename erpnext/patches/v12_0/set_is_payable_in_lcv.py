import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "landed_cost_voucher")

	frappe.db.sql("""
		update `tabLanded Cost Voucher`
		set is_payable = if(ifnull(party, '') = '', 0, 1)
	""")
