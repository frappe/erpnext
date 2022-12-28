# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.custom_utils import check_future_date
from erpnext.controllers.stock_controller import StockController
from frappe.utils import flt, cint, nowdate,time_diff_in_hours
from frappe import _, qb, throw
from frappe.model.mapper import get_mapped_doc
from erpnext.custom_workflow import validate_workflow_states
from erpnext.stock.stock_ledger import get_valuation_rate


class RepairAndServices(StockController):
	def __init__(self, *args, **kwargs):
		super(RepairAndServices, self).__init__(*args, **kwargs)

	def validate(self):
		validate_workflow_states(self)
		check_future_date(self.posting_date)
		self.update_items()
		self.calculate_total_amount()
		self.calculate_km_diff()
		self.fetch_previous_service_date()
		self.calculate_total_hr()
		
	def on_update(self):
		self.calculate_total_hr()

	def on_submit(self):
		self.calculate_total_hr()

	def calculate_total_hr(self):
		if self.start_date and self.end_date:
			if self.start_date > self.end_date:
				throw("Start Date cannot be greater than end date")
			self.total_hrs = time_diff_in_hours(self.end_date, self.start_date)
	def fetch_previous_service_date(self):
		rs = qb.DocType("Repair And Services")
		rsi = qb.DocType("Repair And Services Item")
		for item in self.items:
			data = (qb.from_(rs)
						.inner_join(rsi)
						.on(rs.name == rsi.parent)
						.select(rs.posting_date,rs.name,rs.current_km)
						.where((rs.equipment == self.equipment) 
							& (rs.name != self.name) 
							& (rs.docstatus == 1)
							& (rsi.item_code == item.item_code))
						.orderby(rs.posting_date,order=qb.desc)
						.orderby(rs.posting_time,order=qb.desc)
						.limit(1)).run()
			if data:
				item.last_service_date 	= data[0][0]
				item.last_service_ref 	= data[0][1]
				item.previous_km 		= flt(data[0][2])
				item.km_difference 		= flt(self.current_km) - flt(data[0][2])
	# def on_submit(self):
	# 	self.update_stock_ledger()
	# 	self.make_gl_entries()

	# def on_cancel(self):
	# 	self.update_stock_ledger()
	# 	self.make_gl_entries_on_cancel()

	def update_stock_ledger(self):
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
		self.total_amount = self.total_out_source_amt = self.total_stock_amt = 0
		for item in self.items:
			if flt(item.maintain_stock) == 1:
				self.total_stock_amt += flt(item.rate,2) * flt(item.qty)
			else:
				self.total_out_source_amt += flt(item.rate,2) * flt(item.qty)
			self.total_amount += flt(item.charge_amount,2)

	def update_items(self):
		for a in self.items:
			if flt(a.maintain_stock) == 1:
				if not a.warehouse:
					a.warehouse = self.set_warehouse
				a.rate = get_valuation_rate(
						a.item_code,
						a.warehouse,
						self.doctype,
						self.name,
						company=self.company
				)
				a.cost_center = self.cost_center
				a.charge_amount = flt(a.qty) * flt(a.rate)
				a.expense_account = frappe.db.get_value("Item Default", {'parent':a.item_code}, "expense_account")

@frappe.whitelist()
def make_mr(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc
	def set_missing_values(source, target):
		target.material_request_type = "Material Issue"
		for a in source.items:
			# if (a.qty_in_warehouse <= 0 and a.qty_required > 0) or (a.qty_in_warehouse > 0 and a.qty_required > a.qty_in_warehouse and a.qty_required > 0):
			if a.maintain_stock == 1 and a.qty > 0:
				row = target.append("items",{})
				row.warehouse = a.warehouse
				row.item_code = a.item_code
				row.item_name = a.item_name
				row.uom = a.uom
				row.stock_uom = a.uom
				row.qty = flt(a.qty)
				row.rate = flt(a.rate)
				row.cost_center = a.cost_center
				row.issue_to_equipment = source.equipment
				row.amount = flt(a.charge_amount)
	def update_item(obj, target, source_parent):
		target.issue_to_equipment = source_parent.equipment
		target.stock_uom = obj.uom

	doclist = get_mapped_doc("Repair And Services", source_name, 	{
		"Repair And Services": {
			"doctype": "Material Request",
			"field_map": {
					"repair_and_services": "name"
				},
		},
		# "Repair And Services Item": {
		# 	"doctype": "Material Request Item",
		# 	"postprocess": update_item,
		# }
	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def make_repair_and_services_invoice(source_name, target_doc=None): 
	def update_date(obj, target, source_parent):
		target.posting_date = nowdate()
	def set_missing_values(source, target):
		for a in source.items:
			# if (a.qty_in_warehouse <= 0 and a.qty_required > 0) or (a.qty_in_warehouse > 0 and a.qty_required > a.qty_in_warehouse and a.qty_required > 0):
			if a.maintain_stock == 0 and a.qty > 0:
				row = target.append("items",{})
				row.type = a.type
				row.charge_amount = a.charge_amount
				row.item_code = a.item_code
				row.item_name = a.item_name
				row.uom = a.uom
				row.qty = flt(a.qty)
				row.rate = flt(a.rate)
				row.maintain_stock = a.maintain_stock
				row.description = a.description
				row.issue_to_equipment = source.equipment
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
			# "Repair And Services Item": {
			# 	"doctype": "Repair And Services Invoice Item",
			# 	"field_map":{
			# 		"item_name":"item_name",
			# 	},
			# }
		}, target_doc,set_missing_values)
	return doc

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator" or "System Manager" in user_roles: 
		return

	return """(
		`tabRepair And Services`.owner = '{user}'
		or
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