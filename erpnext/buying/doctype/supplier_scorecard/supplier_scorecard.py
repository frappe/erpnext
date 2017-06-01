# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import nowdate, get_last_day, get_first_day, getdate, add_days, add_years
import erpnext.buying.doctype.supplier_scorecard_variable.supplier_scorecard_variable as variable_functions

class SupplierScorecard(Document):

	def validate(self):
		self.calculate_variables()
		self.calculate_criteria()
		self.calculate_score()
		self.update_standing()
		
	def calculate_variables(self):
		for var in self.variables:
			
			if '.' in var.path:
				method_to_call = import_string_path(var.path)
				var.value = method_to_call(self)
				#pass
			else:
				method_to_call = getattr(variable_functions, var.path)
				var.value = method_to_call(self)
				#pass
			
		
		
	def calculate_criteria(self):
		#Get the criteria 
		for crit in self.criteria:
			
			me = ""
			my_eval_statement = crit.formula.replace("\r", "").replace("\n", "")
			for let in my_eval_statement:
				me += let.encode('hex') + " "
			frappe.msgprint(me)
			
			for var in self.variables:
				if var.value:
					if var.param_name in my_eval_statement:
						my_eval_statement = my_eval_statement.replace(var.param_name, "{:.2f}".format(var.value))
				else:
					if var.param_name in my_eval_statement:
						my_eval_statement = my_eval_statement.replace(var.param_name, '0.0')
						
			my_eval_statement = my_eval_statement.replace('&lt;','<').replace('&gt;','>')
			frappe.msgprint(my_eval_statement + " = " + "{:.2f}".format(crit.score))
			crit.score = frappe.safe_eval(my_eval_statement,  None, None)
			
		
	def calculate_score(self):
		myscore = 0
		for crit in self.criteria:
			myscore += crit.score * crit.weight/100.0
		self.total_score = myscore
		
	def update_standing(self):
		# Get the setup document
		setup_doc = frappe.get_doc('Supplier Scorecard Setup', self.scorecard)
		
		mystanding = None
		mymax = None
		myscore = 0
		for standing in setup_doc.standings:
			if (not standing.min_grade or (standing.min_grade <= self.total_score)) and \
				(not standing.max_grade or (standing.max_grade > self.total_score)):
				self.status = standing.standing_name
				self.indicator_color = standing.standing_color
				self.prevent_rfq = standing.prevent_rfq
				self.prevent_po = standing.prevent_po
				self.notify_supplier = standing.notify_supplier
				self.notify_other = standing.notify_other
				self.other_link = standing.other_link
		
	
	def get_scorecard_dates(self, period):
		
		if period == 'Per Day':
			self.end_date = getdate(add_days(nowdate(),-1))
			self.start_date = getdate(add_days(nowdate(),-2))
		elif period == 'Per Week':
			self.end_date = getdate(add_days(nowdate(),-1))
			self.start_date = getdate(add_days(nowdate(),-7))
		elif period == 'Per Month':
			self.start_date  = get_first_day(nowdate(), 0,-1)
			self.end_date = get_last_day(self.start_date)
		elif period == 'Per Year':
			self.start_date  = get_first_day(nowdate(), -1,0)
			self.end_date = add_days(add_years(self.start_date,1), -1)
			

	
def import_string_path(path):
    components = path.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def post_process(source, target):
	target.get_scorecard_dates(source.period)
		

@frappe.whitelist()
def make_supplier_scorecard(source_name, target_doc=None):
	#def update_item(obj, target, source_parent):
	#	target.qty = flt(obj.qty) - flt(obj.received_qty)
	#	target.stock_qty = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.conversion_factor)
	#	target.amount = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate)
	#	target.base_amount = (flt(obj.qty) - flt(obj.received_qty)) * \
	#		flt(obj.rate) * flt(source_parent.conversion_rate)

	doc = get_mapped_doc("Supplier Scorecard Setup", source_name,	{
		"Supplier Scorecard Setup": {
			"doctype": "Supplier Scorecard"
		},
		"Supplier Scorecard Scoring Variable": {
			"doctype": "Supplier Scorecard Scoring Variable",
			"add_if_empty": True
		},
		"Supplier Scorecard Scoring Variable": {
			"doctype": "Supplier Scorecard Scoring Variable",
			"add_if_empty": True
		}
	}, target_doc, post_process)

	return doc
	
	