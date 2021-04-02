from __future__ import unicode_literals
import frappe
from frappe.utils import flt

def execute():
	frappe.reload_doc('accounts', 'doctype', 'mode_of_payment')

	frappe.db.sql(""" update `tabMode of Payment` set type = 'Cash' where (type is null or type = '') and name = 'Cash'""")

	for data in frappe.db.sql("""select name from `tabSales Invoice` where is_pos=1 and docstatus<2 and
		(ifnull(paid_amount, 0) - ifnull(change_amount, 0)) > ifnull(grand_total, 0) and modified > '2016-05-01'""", as_dict=1):
		if data.name:
			si_doc = frappe.get_doc("Sales Invoice", data.name)
			remove_payment = []
			mode_of_payment = [d.mode_of_payment for d in si_doc.payments if flt(d.amount) > 0]
			if mode_of_payment != set(mode_of_payment):
				for payment_data in si_doc.payments:
					if payment_data.idx != 1 and payment_data.amount == si_doc.grand_total:
						remove_payment.append(payment_data)
						frappe.db.sql(""" delete from `tabSales Invoice Payment` 
							where name = %(name)s""", {'name': payment_data.name})

			if len(remove_payment) > 0:
				for d in remove_payment:
					si_doc.remove(d)

				si_doc.set_paid_amount()
				si_doc.db_set("paid_amount", si_doc.paid_amount, update_modified = False)
				si_doc.db_set("base_paid_amount", si_doc.base_paid_amount, update_modified = False)