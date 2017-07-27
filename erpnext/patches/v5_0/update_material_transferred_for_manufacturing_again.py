import frappe

def execute():
	pro_order_qty_transferred = frappe._dict()
	for se in frappe.db.sql("""select production_order, sum(fg_completed_qty) as transferred_qty 
		from `tabStock Entry`
		where docstatus=1 and ifnull(production_order, '') != ''
		and purpose = 'Material Transfer for Manufacture'
		group by production_order""", as_dict=1):
			pro_order_qty_transferred.setdefault(se.production_order, se.transferred_qty)
	
	for d in frappe.get_all("Production Order", filters={"docstatus": 1}, fields=["name", "qty"]):
		if d.name in pro_order_qty_transferred:
			material_transferred_for_manufacturing = pro_order_qty_transferred.get(d.name) \
				if pro_order_qty_transferred.get(d.name) <= d.qty else d.qty		
		
			frappe.db.sql("""update `tabProduction Order` set material_transferred_for_manufacturing=%s
				where name=%s""", (material_transferred_for_manufacturing, d.name))