# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.custom_utils import check_future_date
from frappe.utils import flt, cint
from erpnext.controllers.stock_controller import StockController
from erpnext.fleet_management.fleet_utils import get_pol_till, get_pol_till, get_previous_km

class POLIssue(StockController):
	def __init__(self, *args, **kwargs):
		super(POLIssue, self).__init__(*args, **kwargs)
	def validate(self):
		check_future_date(self.posting_date)
		self.validate_uom_is_integer("stock_uom", "qty")
		self.update_items()
		self.validate_data()
	
	def validate_data(self):
		if not self.cost_center :
			frappe.throw("Cost Center and Warehouse are Mandatory")
		total_quantity = 0
		for a in self.items:
			if flt(a.qty) <= 0:
				frappe.throw("Quantity for <b>"+str(a.equipment)+"</b> should be greater than 0")
			total_quantity = flt(total_quantity) + flt(a.qty)
			previous_km_reading = frappe.db.sql('''
				select cur_km_reading
				from `tabPOL Issue` p inner join `tabPOL Issue Items` pi on p.name = pi.parent	
				where p.docstatus = 1 and p.name != '{}' and pi.equipment = '{}'
				and pi.uom = '{}' 
				order by p.posting_date desc, p.posting_time desc
				limit 1
			'''.format(self.name, a.equipment, a.uom))
			pv_km = 0
			if not previous_km_reading:
				pv_km = frappe.db.get_value("Equipment",a.equipment,"initial_km_reading")
			else:
				pv_km = previous_km_reading[0][0]

			if flt(pv_km) >= flt(a.cur_km_reading):
				frappe.throw("Current KM/Hr Reading cannot be less than Previous KM/Hr Reading({}) for Equipment Number <b>{}</b>".format(pv_km,a.equipment))
			a.km_difference = flt(a.cur_km_reading) - flt(pv_km)
			if a.uom == "Hour":
				a.mileage = a.qty / flt(a.km_difference)
			else :
				a.mileage = flt(a.km_difference) / a.qty
			a.previous_km = pv_km
			a.amount = flt(a.rate) * flt(a.qty)
		self.total_quantity = total_quantity
	
	def on_submit(self):
		self.check_tanker_hsd_balance()
		self.make_pol_entry()

	def on_cancel(self):
		self.delete_pol_entry()
	
	def check_tanker_hsd_balance(self):
		if not self.tanker:
			return
		received_till = get_pol_till("Stock", self.tanker, self.posting_date, self.pol_type, self.posting_time)
		issue_till = get_pol_till("Issue", self.tanker, self.posting_date, self.pol_type)
		balance = flt(received_till) - flt(issue_till)
		if flt(self.total_quantity) > flt(balance):
			frappe.throw("Not enough balance in tanker to issue. The balance is " + str(balance))	

	def make_pol_entry(self):
		if self.tanker:
			con = frappe.new_doc("POL Entry")
			con.flags.ignore_permissions = 1
			con.equipment = self.tanker
			con.pol_type = self.pol_type
			con.branch = self.branch
			con.posting_date = self.posting_date
			con.posting_time = self.posting_time
			con.qty = self.total_quantity
			con.reference_type = self.doctype
			con.reference = self.name
			con.type = "Issue"
			con.is_opening = 0
			con.submit()

		for a in self.items:
			con = frappe.new_doc("POL Entry")
			con.flags.ignore_permissions = 1
			con.equipment = a.equipment
			con.pol_type = self.pol_type
			con.branch = a.fuel_book_branch
			con.posting_date = self.posting_date
			con.posting_time = self.posting_time
			con.qty = a.qty
			con.reference_type = self.doctype
			con.reference = self.name
			con.cost_center = a.cost_center
			# if self.purpose == "Issue":
			con.type = "Receive"
			# else:
			# 	con.type = "Stock"
			con.is_opening = 0
			con.submit()

	def delete_pol_entry(self):
		frappe.db.sql("delete from `tabPOL Entry` where reference = %s", self.name)

	def update_items(self):
		for a in self.items:
			# item code 
			a.item_code = self.pol_type
			# cost center
			a.cost_center = self.cost_center		
			# Warehouse
			a.warehouse = self.warehouse
			# Expense Account
			a.equipment_category = frappe.db.get_value("Equipment", a.equipment, "equipment_category")
			budget_account = frappe.db.get_value("Equipment Category", a.equipment_category, "budget_account")
			if not budget_account:
				budget_account = frappe.db.get_value("Item Default", {'parent':self.pol_type}, "expense_account")
			if not budget_account:
				frappe.throw("Set Budget Account in Equipment Category")
			a.expense_account = budget_account
	
	# def update_stock_ledger(self):
	# 	sl_entries = []
	# 	for a in self.items:
	# 		sl_entries.append(self.get_sl_entries(a, {
	# 			"actual_qty": -1 * flt(a.qty), 
	# 			"warehouse": self.warehouse, 
	# 			"incoming_rate": 0 
	# 		}))

	# 	if self.docstatus == 2:
	# 		sl_entries.reverse()
	# 	self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')