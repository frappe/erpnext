import frappe

def execute():
	frappe.db.sql("""update `tabStock Entry` set purpose='Material Transfer for Manufacture'
		where ifnull(production_order, '')!='' and purpose='Material Transfer'""")
