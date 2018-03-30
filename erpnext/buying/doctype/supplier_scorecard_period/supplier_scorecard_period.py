# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import throw, _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
import erpnext.buying.doctype.supplier_scorecard_variable.supplier_scorecard_variable as variable_functions

class SupplierScorecardPeriod(Document):

	def validate(self):
		self.validate_criteria_weights()
		self.calculate_variables()
		self.calculate_criteria()
		self.calculate_score()

	def validate_criteria_weights(self):

		weight = 0
		for c in self.criteria:
			weight += c.weight

		if weight != 100:
			throw(_('Criteria weights must add up to 100%'))

	def calculate_variables(self):
		for var in self.variables:

			if '.' in var.path:
				method_to_call = import_string_path(var.path)
				var.value = method_to_call(self)
			else:
				method_to_call = getattr(variable_functions, var.path)
				var.value = method_to_call(self)



	def calculate_criteria(self):
		#Get the criteria
		for crit in self.criteria:

			#me = ""
			my_eval_statement = crit.formula.replace("\r", "").replace("\n", "")
			#for let in my_eval_statement:
			#	me += let.encode('hex') + " "
			#frappe.msgprint(me)

			for var in self.variables:
				if var.value:
					if var.param_name in my_eval_statement:
						my_eval_statement = my_eval_statement.replace('{' + var.param_name + '}', "{:.2f}".format(var.value))
				else:
					if var.param_name in my_eval_statement:
						my_eval_statement = my_eval_statement.replace('{' + var.param_name + '}', '0.0')

			#frappe.msgprint(my_eval_statement )

			my_eval_statement = my_eval_statement.replace('&lt;','<').replace('&gt;','>')

			try:
				crit.score = min(crit.max_score, max( 0 ,frappe.safe_eval(my_eval_statement,  None, {'max':max, 'min': min})))
			except Exception:
				frappe.throw(_("Could not solve criteria score function for {0}. Make sure the formula is valid.".format(crit.criteria_name)),frappe.ValidationError)
				crit.score = 0

	def calculate_score(self):
		myscore = 0
		for crit in self.criteria:
			myscore += crit.score * crit.weight/100.0
		self.total_score = myscore

	def calculate_weighted_score(self, weighing_function):
		my_eval_statement = weighing_function.replace("\r", "").replace("\n", "")

		for var in self.variables:
			if var.value:
				if var.param_name in my_eval_statement:
					my_eval_statement = my_eval_statement.replace('{' + var.param_name + '}', "{:.2f}".format(var.value))
			else:
				if var.param_name in my_eval_statement:
					my_eval_statement = my_eval_statement.replace('{' + var.param_name + '}', '0.0')

		my_eval_statement = my_eval_statement.replace('&lt;','<').replace('&gt;','>')

		try:
			weighed_score = frappe.safe_eval(my_eval_statement,  None, {'max':max, 'min': min})
		except Exception:
			frappe.throw(_("Could not solve weighted score function. Make sure the formula is valid."),frappe.ValidationError)
			weighed_score = 0
		return weighed_score



def import_string_path(path):
    components = path.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def post_process(source, target):
	pass


@frappe.whitelist()
def make_supplier_scorecard(source_name, target_doc=None):
	#def update_item(obj, target, source_parent):
	#	target.qty = flt(obj.qty) - flt(obj.received_qty)
	#	target.stock_qty = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.conversion_factor)
	#	target.amount = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate)
	#	target.base_amount = (flt(obj.qty) - flt(obj.received_qty)) * \
	#		flt(obj.rate) * flt(source_parent.conversion_rate)

	doc = get_mapped_doc("Supplier Scorecard", source_name,	{
		"Supplier Scorecard": {
			"doctype": "Supplier Scorecard Period"
		},
		"Supplier Scorecard Scoring Variable": {
			"doctype": "Supplier Scorecard Scoring Variable",
			"add_if_empty": True
		},
		"Supplier Scorecard Scoring Constraint": {
			"doctype": "Supplier Scorecard Scoring Constraint",
			"add_if_empty": True
		}
	}, target_doc, post_process)

	return doc

