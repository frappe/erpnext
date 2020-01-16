from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.sql("""update `tabPurchase Order Item` set billed_amt = 0
			where delivered_by_supplier=1 and docstatus=1""")
			
	drop_ship_pos = frappe.db.sql("""select distinct parent from `tabPurchase Order Item` 
		where delivered_by_supplier=1 and docstatus=1""")
		
	for po in drop_ship_pos:
		invoices = frappe.db.sql("""select distinct parent from `tabPurchase Invoice Item`
			where purchase_order=%s and docstatus=1""", po[0])
		if invoices:
			for inv in invoices:
				frappe.get_doc("Purchase Invoice", inv[0]).update_qty(update_modified=False)
		else:
			frappe.db.sql("""update `tabPurchase Order` set per_billed=0 where name=%s""", po[0])