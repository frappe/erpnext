# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cstr
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document

class VehicleLog(Document):
	def validate(self):
		last_odometer=frappe.db.get_value("Vehicle", self.license_plate, "last_odometer")
		if flt(self.odometer) < flt(last_odometer):
			frappe.throw(_("Current Odometer reading entered should be greater than initial Vehicle Odometer {0}").format(last_odometer))
		for service_detail in self.service_detail:
			if (service_detail.service_item or service_detail.type or service_detail.frequency or service_detail.expense_amount):
					if not (service_detail.service_item and service_detail.type and service_detail.frequency and service_detail.expense_amount):
							frappe.throw(_("Service Item,Type,frequency and expense amount are required"))
							
	def on_submit(self):
		frappe.db.sql("update `tabVehicle` set last_odometer=%s where license_plate=%s",
			(self.odometer, self.license_plate))
	
@frappe.whitelist()
def get_make_model(license_plate):
	vehicle=frappe.get_doc("Vehicle",license_plate)
	return (vehicle.make,vehicle.model)

@frappe.whitelist()
def make_expense_claim(docname):
	def check_exp_claim_exists():
		exp_claim = frappe.db.sql("""select name from `tabExpense Claim` where vehicle_log=%s""",vehicle_log.name)
		return exp_claim[0][0] if exp_claim else ""
	def calc_service_exp():
		total_exp_amt=0
		exp_claim = check_exp_claim_exists()
		if exp_claim:
			frappe.throw(_("Expense Claim {0} already exists for the Vehicle Log").format(exp_claim))
		for serdetail in vehicle_log.service_detail:
			total_exp_amt = total_exp_amt + serdetail.expense_amount
		return total_exp_amt
		
	vehicle_log = frappe.get_doc("Vehicle Log", docname)
	exp_claim = frappe.new_doc("Expense Claim")
	exp_claim.employee=vehicle_log.employee
	exp_claim.vehicle_log=vehicle_log.name
	exp_claim.remark=_("Expense Claim for Vehicle Log {0}").format(vehicle_log.name)
	fuel_price=vehicle_log.price
	total_claim_amt=calc_service_exp() + fuel_price
	exp_claim.append("expenses",{
		"expense_date":vehicle_log.date,
		"description":_("Vehicle Expenses"),
		"claim_amount":total_claim_amt
	})
	return exp_claim.as_dict()
