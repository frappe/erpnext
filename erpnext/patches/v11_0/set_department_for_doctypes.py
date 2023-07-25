import frappe

# Set department value based on employee value


def execute():

	doctypes_to_update = {
		"projects": ["Activity Cost", "Timesheet"],
		"setup": ["Sales Person"],
	}

	for module, doctypes in doctypes_to_update.items():
		for doctype in doctypes:
			if frappe.db.table_exists(doctype):
				frappe.reload_doc(module, "doctype", frappe.scrub(doctype))
				frappe.db.sql(
					"""
					update `tab%s` dt
					set department=(select department from `tabEmployee` where name=dt.employee)
				"""
					% doctype
				)
