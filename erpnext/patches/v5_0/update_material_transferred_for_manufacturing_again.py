import frappe

def execute():
	wo_order_qty_transferred = frappe._dict()
	for se in frappe.db.sql("""select work_order, sum(fg_completed_qty) as transferred_qty 
		from `tabStock Entry`
		where docstatus=1 and ifnull(work_order, '') != ''
		and purpose = 'Material Transfer for Manufacture'
		group by work_order""", as_dict=1):
			wo_order_qty_transferred.setdefault(se.work_order, se.transferred_qty)
	
	for d in frappe.get_all("Work Order", filters={"docstatus": 1}, fields=["name", "qty"]):
		if d.name in wo_order_qty_transferred:
			material_transferred_for_manufacturing = wo_order_qty_transferred.get(d.name) \
				if wo_order_qty_transferred.get(d.name) <= d.qty else d.qty		
		
			frappe.db.sql("""update `tabWork Order` set material_transferred_for_manufacturing=%s
				where name=%s""", (material_transferred_for_manufacturing, d.name))