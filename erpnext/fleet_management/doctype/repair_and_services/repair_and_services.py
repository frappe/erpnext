# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.custom_utils import check_future_date
from erpnext.controllers.stock_controller import StockController
from frappe.utils import flt, cint, nowdate
from frappe import _, qb, throw
from frappe.model.mapper import get_mapped_doc

class RepairAndServices(StockController):
	def __init__(self, *args, **kwargs):
		super(RepairAndServices, self).__init__(*args, **kwargs)

	def validate(self):
		check_future_date(self.posting_date)
		self.update_items()
		self.calculate_total_amount()
		self.calculate_km_diff()
		self.fetch_previous_service_date()

	def fetch_previous_service_date(self):
		rs = qb.DocType("Repair And Services")
		rsi = qb.DocType("Repair And Services Item")
		for item in self.items:
			data = (qb.from_(rs)
						.inner_join(rsi)
						.on(rs.name == rsi.parent)
						.select(rs.posting_date,rs.name)
						.where((rs.equipment == self.equipment) 
							& (rs.name != self.name) 
							& (rs.docstatus == 1)
							& (rsi.item_code == item.item_code))
						.orderby(rs.posting_date,order=qb.desc)
						.orderby(rs.posting_time,order=qb.desc)
						.limit(1)).run()
			if data:
				item.last_service_date = data[0][0]
				item.last_service_ref = data[0][1]
	def on_submit(self):
		self.update_stock_ledger()
		self.make_gl_entries()

	def on_cancel(self):
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()

	def update_stock_ledger(self):
		if cint(self.out_source) == 1:
			return
		sl_entries = []
		for a in self.items:
			if a.maintain_stock:
				sl_entries.append(self.get_sl_entries(a, {
					"actual_qty": -1 * flt(a.qty), 
					"warehouse": a.warehouse, 
					"incoming_rate": 0 
				}))

		if self.docstatus == 2:
			sl_entries.reverse()
		self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')
	
	def calculate_km_diff(self):
		doc = qb.DocType("Repair And Services")
		previous_km_reading = (
								qb.from_(doc)
								.select(doc.current_km)
								.where((doc.equipment == self.equipment) & (doc.docstatus==1))
								.orderby( doc.posting_date,order=qb.desc)
								.orderby( doc.posting_time,order=qb.desc)
								.limit(1)
								.run()
								)
		pv_km = 0
		if not previous_km_reading:
			pv_km = frappe.db.get_value("Equipment",self.equipment,"initial_km_reading")
		else:
			pv_km = previous_km_reading[0][0]
		if flt(pv_km) >= flt(self.current_km):
			frappe.throw("Current KM Reading cannot be less than Previous KM Reading({}) for Equipment Number <b>{}</b>".format(pv_km,self.equipment))
		self.km_difference = flt(self.current_km) - flt(pv_km)

	def calculate_total_amount(self):
		self.total_amount = 0
		for item in self.items:
			self.total_amount += flt(item.charge_amount,2)

	def update_items(self):
		if cint(self.out_source) == 1:
			return
		for a in self.items:
			if a.maintain_stock:
				a.cost_center = self.cost_center
				a.charge_amount = flt(a.qty) * flt(a.rate)
				a.expense_account = frappe.db.get_value("Item Default", {'parent':a.item_code}, "expense_account")

@frappe.whitelist()
def make_repair_and_services_invoice(source_name, target_doc=None): 
	def update_date(obj, target, source_parent):
		target.posting_date = nowdate()
	doc = get_mapped_doc("Repair And Services", source_name, {
			"Repair And Services": {
				"doctype": "Repair And Service Invoice",
				"field_map": {
					"name": "maintenance_invoice",
					"repair_and_services_date": "posting_date",
					"outstanding_amount":"total_amount"
				},
				"postprocess": update_date,
				"validation": {"docstatus": ["=", 1]},

			},
			"Repair And Services Item": {
				"doctype": "Repair And Services Invoice Item",
				"field_map":{
					"item_name":"item_name"
				}
		}
		}, target_doc)
	return doc

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator" or "System Manager" in user_roles: 
		return

	return """(
		exists(select 1
			from `tabEmployee` as e
			where e.branch = `tabRepair And Services`.branch
			and e.user_id = '{user}')
		or
		exists(select 1
			from `tabEmployee` e, `tabAssign Branch` ab, `tabBranch Item` bi
			where e.user_id = '{user}'
			and ab.employee = e.name
			and bi.parent = ab.name
			and bi.branch = `tabRepair And Services`.branch)
	)""".format(user=user)