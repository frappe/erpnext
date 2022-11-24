# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, rounded
from erpnext.accounts.accounts_custom_functions import get_child_cost_centers,get_period_date

class ProductionTarget(Document):
	def validate(self):
		self.calculate_value()
	
	def on_update(self):
		self.check_duplicate()

	def check_duplicate(self):
		dups = frappe.db.sql("select name from `tabProduction Target` where branch = %s and location = %s and fiscal_year = %s and name != %s", (self.branch, self.location, self.fiscal_year, self.name), as_dict=True)
		for a in dups:
			frappe.throw("Update {0} to set your targets".format(frappe.get_desk_link("Production Target", a.name)))

		prod = frappe.db.sql("select production_group, count(1) as num from `tabProduction Target Item` where parent = %s group by production_group having num > 1", self.name, as_dict=True)
		for a in prod:
			frappe.throw("Can set only one target for {0} in Production Target".format(frappe.bold(a.production_group)))

		dis = frappe.db.sql("select production_group, count(1) as num from `tabDisposal Target Item` where parent = %s group by production_group having num > 1", self.name, as_dict=True)
		for a in dis:
			frappe.throw("Can set only one target for {0} in Disposal Target".format(frappe.bold(a.production_group)))

	def calculate_value(self):
		for a in self.items:
			a.quantity = flt(a.jan) + flt(a.feb) + flt(a.march) + flt(a.april) + flt(a.may) + flt(a.june) + flt(a.july) + flt(a.august) \
			+ flt(a.september) + flt(a.october) + flt(a.november) + flt(a.december)
			if flt(a.quantity) > 0 and flt(a.quantity) != flt(a.qty):
				frappe.throw("Target Quantity (Production) should be equal to {0} for {1}".format(frappe.bold(str(a.qty)), frappe.bold(a.production_group)))
		for a in self.disposal:
			a.quantity = flt(a.quarter1) + flt(a.quarter2) + flt(a.quarter3) + flt(a.quarter4)
			if flt(a.quantity) > 0 and flt(a.quantity) != flt(a.qty):
				frappe.throw("Target Quantity (Sales) should be equal to {0} for {1}".format(frappe.bold(str(a.qty)), frappe.bold(a.production_group)))

	
def get_target_value(which, cost_center, production_group, fiscal_year, from_date, to_date, is_location=None):
	if not which or which not in ("Production", "Disposal"):
		frappe.throw("You should specify whether the target is for Production or Disposal")
	if not cost_center or not production_group or not fiscal_year:
		frappe.throw("Value Missing")

	if is_location:
		cond = " a.location = '{0}'".format(cost_center)
	else:
		all_ccs = get_child_cost_centers(cost_center)
		cond = " a.cost_center in {0}".format(tuple(all_ccs))

	query = "select sum(quantity) as total, sum(jan) as q1, sum(feb) as q2, sum(march) as q3, sum(april) as q4, sum(may) as q5, sum(june) as q6, sum(july) as q7, sum(august) as q8, sum(september) as q9,  sum(october) as q10, sum(november) as q11, sum(december) as q12  from `tabProduction Target` a, `tab{0} Target Item` b where a.name = b.parent and {1} and a.fiscal_year = '{2}' and b.production_group = '{3}'".format(which, cond, fiscal_year, production_group)

	qty = frappe.db.sql(query, as_dict=True)

	q1 = qty and qty[0].q1 or 0
	q2 = qty and qty[0].q2 or 0
	q3 = qty and qty[0].q3 or 0
	q4 = qty and qty[0].q4 or 0
	q5 = qty and qty[0].q5 or 0
	q6 = qty and qty[0].q6 or 0
	q7 = qty and qty[0].q7 or 0
	q8 = qty and qty[0].q8 or 0
	q9 = qty and qty[0].q9 or 0
	q10 = qty and qty[0].q10 or 0
	q11 = qty and qty[0].q11 or 0
	q12 = qty and qty[0].q12 or 0
	
	
	return get_propotional_target(from_date, to_date, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11, q12)

def get_propotional_target(from_date, to_date, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11, q12):
	#Determine the target
	from_month = getdate(from_date).month
	try:
		to_month = getdate(to_date).month
	except:
		to_date = to_date.replace("29", "28")
		to_month = getdate(to_date).month
	if from_month == to_month:
		if from_month == 1:
			target = q1
		elif from_month == 2:
			target = q2
		elif from_month == 3:
			target = q3
		elif from_month == 4:
			target = q4
		elif from_month == 5:
			target = q5 
		elif from_month == 6:
			target = q6 
		elif from_month == 7:
			target = q7 
		elif from_month == 8:
			target = q8 
		elif from_month == 9:
			target = q9 
		elif from_month == 10:
			target = q10
		elif from_month == 11:
			target = q11 
		elif from_month == 12:
			target = q12 
		else:
			frappe.throw("INVALID DATA RECEIVED")
	else:
		if from_month == 1 and to_month == 12:
			target = q1 + q2 + q3 + q4 + q5 + q6 + q7 + q8 + q9 + q10 + q11 + q12
		elif from_month == 1 and to_month == 3:
			target = q1 + q2 + q3
		elif from_month == 4 and to_month == 6:
			target = q4 + q5 + q6
		elif from_month == 7 and to_month == 9:
			target = q7 + q8 + q9
		elif from_month == 10 and to_month == 12:
			target = q10 + q11 + q12
		elif from_month == 1 and to_month == 6:
			target = q1 + q2 + q3 + q4 + q5 + q6
		elif from_month == 7 and to_month == 12:
			target = q7 + q8 + q9 + q10 + q11 + q12
		elif from_month == 1 and to_month == 9:
			target = q1 + q2 + q3 + q4 + q5 + q6 + q7 + q8 + q9
		elif from_month == 1 and to_month == 2:	
			target = q1 + q2
		elif from_month == 1 and to_month == 4:	
			target = q1 + q2 + q3 + q4
		elif from_month == 1 and to_month == 5:	
			target = q1 + q2+ q3 + q4 + q5
		elif from_month == 1 and to_month == 7:	
			target = q1 + q2 + q3 + q4 + q5 + q6 + q7
		elif from_month == 1 and to_month == 8:	
			target = q1 + q2 + q3 + q4 + q5 + q6 + q7 + q8
		elif from_month == 1 and to_month == 10:	
			target = q1 + q2 + q3 + q4 + q5 + q6 + q7 + q8 + q9 + q10
		elif from_month == 1 and to_month == 11:	
			target = q1 + q2 + q3 + q4 + q5 + q6 + q7 + q8 + q9 + q10 + q11
		else:
			frappe.throw("INVALID DATA RECEIVED")
	return rounded(target, 2)

