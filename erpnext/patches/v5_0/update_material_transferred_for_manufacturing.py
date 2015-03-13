import frappe

def execute():
	frappe.reload_doctype("Production Order")
	frappe.db.sql("""update `tabProduction Order` set material_transferred_for_manufacturing=
		(select sum(fg_completed_qty) from `tabStock Entry`
			where docstatus=1
			and production_order=`tabProduction Order`.name
			and purpose = "Material Transfer for Manufacture")""")
