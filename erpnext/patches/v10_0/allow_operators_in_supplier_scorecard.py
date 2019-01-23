# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for criteria in frappe.get_all('Supplier Scorecard Criteria', fields=['name', 'formula'], limit_page_length=None):
		frappe.db.set_value('Supplier Scorecard Criteria', criteria.name,
			'formula', criteria.formula.replace('&lt;','<').replace('&gt;','>'))

	for criteria in frappe.get_all('Supplier Scorecard Scoring Criteria', fields=['name', 'formula'], limit_page_length=None):
		if criteria.formula: # not mandatory
			frappe.db.set_value('Supplier Scorecard Scoring Criteria', criteria.name,
				'formula', criteria.formula.replace('&lt;','<').replace('&gt;','>'))

	for sc in frappe.get_all('Supplier Scorecard', fields=['name', 'weighting_function'], limit_page_length=None):
		frappe.db.set_value('Supplier Scorecard', sc.name, 'weighting_function',
			sc.weighting_function.replace('&lt;','<').replace('&gt;','>'))