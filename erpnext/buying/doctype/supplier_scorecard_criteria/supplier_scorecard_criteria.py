# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class SupplierScorecardCriteria(Document):
	pass

@frappe.whitelist()
def get_scoring_criteria(criteria_name):
	criteria = frappe.get_doc("Supplier Scorecard Criteria", criteria_name)

	return criteria
	