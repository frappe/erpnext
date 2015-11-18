import frappe

def execute():
	for po in frappe.get_all("Purchase Order", filters={"delivered_by_supplier": 1}, fields=["name"]):
		purchase_order = frappe.get_doc("Purchase Order", po)
		
		for item in purchase_order.items:
			if item.prevdoc_doctype == "Sales Order":
				delivered_by_supplier = frappe.get_value("Sales Order Item", {"parent": item.prevdoc_docname, 
					"item_code": item.item_code}, "delivered_by_supplier")
				
				if delivered_by_supplier:
					frappe.db.set_value("Purchase Order Item", item.name, "delivered_by_supplier", 1)
					frappe.db.set_value("Purchase Order Item", item.name, "billed_amt", item.amount)
					frappe.db.set_value("Purchase Order Item", item.name, "received_qty", item.qty)
					
		update_per_received(purchase_order)
		update_per_billed(purchase_order)
	
def update_per_received(po):
	frappe.db.sql(""" update `tabPurchase Order` 
				set per_received = round((select sum(if(qty > ifnull(received_qty, 0), 
					ifnull(received_qty, 0), qty)) / sum(qty) *100 
				from `tabPurchase Order Item` 
				where parent = "%(name)s"), 2) 
			where name = "%(name)s" """ % po.as_dict())

def update_per_billed(po):
	frappe.db.sql(""" update `tabPurchase Order` 
				set per_billed = round((select sum( if(amount > ifnull(billed_amt, 0), 
					ifnull(billed_amt, 0), amount)) / sum(amount) *100 
				from `tabPurchase Order Item` 
				where parent = "%(name)s"), 2) 
			where name = "%(name)s" """ % po.as_dict())

				