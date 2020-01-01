from __future__ import unicode_literals
import frappe

def execute():
	for module, doctypes in {
		"manufacturing": ["Job Card", "Job Card Item", "Work Order", "BOM"],
		"stock": ["Stock Entry", "Stock Entry Detail", "Material Request", "Material Request Item"]}.items():
		for doctype in doctypes:
			frappe.reload_doc(module, "doctype", frappe.scrub(doctype))

	# To set Material Consumption Against as Work Order for the existing boms, work orders
	for d in ["BOM", "Work Order"]:
		frappe.db.sql(""" UPDATE `tab{0}` 
			SET 
				material_consumption_against = 'Work Order' 
			WHERE 
				docstatus < 2 """.format(d))

	# To set operation id in the stock entries / material requests which are created against job card
	for d in ["Stock Entry", "Material Request"]:
		frappe.db.sql(""" Update `tab{0}`, `tabJob Card`
			SET
				`tab{0}`.operation_id = `tabJob Card`.operation_id
			WHERE
				`tab{0}`.job_card = `tabJob Card`.name and `tab{0}`.docstatus < 2
				and `tab{0}`.job_card is not null and `tab{0}`.job_card != ''
		""".format(d))

		# To set job card, job card item in the stock entries / material requests
		child_doc = ("Stock Entry Detail"
			if d == "Stock Entry" else "Material Request Item")

		frappe.db.sql(""" Update `tab{0}`, `tab{1}`, `tabJob Card Item`
			SET
				`tab{1}`.job_card = `tab{0}`.job_card,
				`tab{1}`.job_card_item = `tabJob Card Item`.name
			WHERE
				`tab{0}`.job_card = `tabJob Card Item`.parent and `tab{0}`.docstatus < 2 and
				`tab{1}`.idx = `tabJob Card Item`.idx and `tab{1}`.item_code = `tabJob Card Item`.item_code and
				`tab{0}`.job_card is not null and `tab{0}`.job_card != '' and `tab{1}`.parent = `tab{0}`.name
		""".format(d, child_doc))

	if frappe.db.has_column("Job Card", "transferred_qty"):
		frappe.db.sql(""" UPDATE `tabJob Card`, `tabJob Card Item`
			SET
				`tabJob Card Item`.transferred_qty = `tabJob Card Item`.required_qty,
				`tabJob Card Item`.consumed_qty = 0,
				`tabJob Card`.per_transferred = 100,
				`tabJob Card`.per_consumed = 0
			WHERE
				`tabJob Card`.transferred_qty >= `tabJob Card`.for_quantity
				and `tabJob Card`.docstatus < 2 and `tabJob Card Item`.parent = `tabJob Card`.name
		""")