# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import re
from frappe.model.document import Document

class SupplierScorecardCriteria(Document):
	pass

@frappe.whitelist()
def get_scoring_criteria(criteria_name):
	criteria = frappe.get_doc("Supplier Scorecard Criteria", criteria_name)

	return criteria
	
@frappe.whitelist()
def get_variables(criteria_name):
	criteria = frappe.get_doc("Supplier Scorecard Criteria", criteria_name)

	my_variables = []
	mylist = re.split('\{(.*?)\}', criteria.formula)[1:-1]
	for d in mylist:
		try:
			#var = frappe.get_doc("Supplier Scorecard Variable", {'param_name' : d})
			var = frappe.db.sql("""
				SELECT
					scv.name
				FROM
					`tabSupplier Scorecard Variable` scv
				WHERE
					param_name=%(param)s""", 
					{'param':d},)[0][0]
			my_variables.append(var)
		except Exception as e:
			pass
			
		
	#frappe.msgprint(str(my_variables))
	return my_variables
	