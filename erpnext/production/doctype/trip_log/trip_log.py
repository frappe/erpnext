# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.custom_utils import check_future_date
from frappe.utils import flt, cint
from frappe import _, qb, throw, bold
from pypika.terms import Case

class TripLog(Document):
	def validate(self):
		check_future_date(self.posting_date)
		self.get_transporter_rate()

	def get_transporter_rate(self):
		total_qty = total_amount = 0
		tr = qb.DocType("Transporter Rate")
		tdr = qb.DocType("Transporter Distance Rate")
		for a in self.items:
			rate = 0
			expense_account = 0
			if flt(a.qty) <= 0:
				throw('Qty must greater than 0 at row {}'.format(a.idx),title="Invalid Qty")
			total_qty = flt(total_qty) + flt(a.qty)
			if cint(a.eligible_for_transporter_payment) == 1:
				if not a.equipment:
					frappe.throw("Please insert Vehicle/Equipment",title="Equipment Missing")
				rate_data = (qb.from_(tr)
							.inner_join(tdr)
							.on(tr.name == tdr.parent)
							.select(tr.name,tdr.rate,tr.expense_account)
							.where((tdr.distance == a.distance)
								&(self.posting_date >= tr.from_date)
								&(self.posting_date <= tr.to_date)
								&(tr.from_warehouse == self.warehouse)
								&(tr.disabled==0))
							.orderby(tr.from_date, order=qb.desc)
							.limit(1)
							).run()
				if rate_data:
					a.rate = rate_data[0][1]
					a.expense_account = rate_data[0][2]
					a.transporter_rate = rate_data[0][0]
					if a.qty :
						a.amount = flt(a.rate) * flt(a.qty)
						total_amount += flt(a.amount)
					else:
						frappe.throw("Please provide the Qty")	
				else:
					frappe.throw("Define Transporter Rate for distance {} in Transporter Rate at row {}".format(bold(a.distance),bold(a.idx)))
			else:
				a.rate = 0
				a.amount = 0
				a.expense_account = ''
		self.total_qty = total_qty
		self.total_amount = total_amount
# query permission
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator" or "System Manager" in user_roles: 
		return

	return """(
		exists(select 1
			from `tabEmployee` as e
			where e.branch = `tabTrip Log`.branch
			and e.user_id = '{user}')
		or
		exists(select 1
			from `tabEmployee` e, `tabAssign Branch` ab, `tabBranch Item` bi
			where e.user_id = '{user}'
			and ab.employee = e.name
			and bi.parent = ab.name
			and bi.branch = `tabTrip Log`.branch)
	)""".format(user=user)