from __future__ import unicode_literals
import frappe
from frappe.utils import flt

def execute():
	si_list = frappe.db.sql("""
		select distinct parent
		from `tabSales Invoice Payment`
		where docstatus!=2 and parenttype = 'Sales Invoice'
		and amount != 0 and base_amount = 0
	""")

	count = 0
	for d in si_list:
		si = frappe.get_doc("Sales Invoice", d[0])
		for p in si.get("payments"):
			if p.amount and not p.base_amount:
				base_amount = flt(p.amount*si.conversion_rate, si.precision("base_paid_amount"))
				frappe.db.set_value("Sales Invoice Payment", p.name, "base_amount", base_amount, update_modified=False)

		count +=1
			
		if count % 200 == 0:
			frappe.db.commit()
