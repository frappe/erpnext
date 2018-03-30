import frappe

def execute():
	frappe.reload_doctype("Work Order")
	frappe.db.sql("""update `tabWork Order` set material_transferred_for_manufacturing=
		(select sum(fg_completed_qty) from `tabStock Entry`
			where docstatus=1
			and work_order=`tabWork Order`.name
			and purpose = "Material Transfer for Manufacture")""")
