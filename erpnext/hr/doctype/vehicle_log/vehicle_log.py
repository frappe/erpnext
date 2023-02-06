# -*- coding: utf-8 -*-quantity
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cstr
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
import json

class VehicleLog(Document):
	# def validate(self):
	# 	if flt(self.odometer) < flt(self.last_odometer):
	# 		frappe.throw(_("Current Odometer Value should be greater than Last Odometer Value {0}").format(self.last_odometer))

	def on_submit(self):
		frappe.db.set_value("Vehicle", self.license_plate, "last_odometer", self.odometer)
		if self.maintenance_type =="Internal":
			make_material_request(self)
		else:
			make_expense_claim(self)
		

	def on_cancel(self):
		distance_travelled = self.odometer - self.last_odometer
		if(distance_travelled > 0):
			updated_odometer_value = int(frappe.db.get_value("Vehicle", self.license_plate, "last_odometer")) - distance_travelled
			frappe.db.set_value("Vehicle", self.license_plate, "last_odometer", updated_odometer_value)

@frappe.whitelist()
def make_expense_claim(docname):
	expense_claim = frappe.db.exists("Expense Claim", {"vehicle_log": docname.name})
	if expense_claim:
		frappe.throw(_("Expense Claim {0} already exists for the Vehicle Log").format(expense_claim))

	vehicle_log = frappe.get_doc("Vehicle Log", docname.name)
	service_expense = sum([flt(d.expense_amount) for d in vehicle_log.service_detail])

	claim_amount = service_expense + (flt(vehicle_log.price) * flt(vehicle_log.fuel_qty) or 1)
	if not claim_amount:
		frappe.throw(_("No additional expenses has been added"))

	exp_claim = frappe.new_doc("Expense Claim")
	exp_claim.employee = vehicle_log.employee
	exp_claim.vehicle_log = vehicle_log.name
	exp_claim.remark = _("Expense Claim for Vehicle Log {0}").format(vehicle_log.name)
	exp_claim.append("expenses", {
		"expense_date": vehicle_log.date,
		"description": _("Vehicle Expenses"),
		"amount": claim_amount
	})
	return exp_claim.as_dict()
def make_material_request(data):  
    mr = frappe.new_doc("Material Request")
    mr.material_request_type = "Material Issue"
    mr.cost_association=data.cost_association
    mr.company = data.company
    mr.title="Issue Request for Vehicle Log"
    # mr.customer = data['customer'] or '_Test Customer'
    mr.vehicle_log=data.name
    mr.sub_branch=data.sub_branch
    mr.transaction_date=data.date
    mr.schedule_date=data.date
    mr.naming_series="MAT-MR-.YYYY.-"
    mr.request_from="RMS"
    for item in data.service_detail:
        warehouse=get_warehouse(item.item_code,data.company)
        i={}
        i['item_code']= item.item_code
        i["qty"]= item.qty
        i["uom"]= item.uom 
        i["conversion_factor"]= 1
        i["schedule_date"]= data.date 
        i["cost_center"]= data.cost_center
        i["warehouse"]=warehouse[1]
        mr.append("items", i)
    # mr.items=items
    mr.insert(ignore_permissions=True)
    mr.submit()
    return mr
def get_warehouse(item,company):
    warehouse=frappe.db.get_list('Item Default',
    filters={
        'company':company,
        'parent':item
    },
    fields=['company', 'default_warehouse'],
    as_list=True
    )
    return warehouse[0]