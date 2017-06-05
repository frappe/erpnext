# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ReportCard(Document):
	
	x_results = frappe.call("erpnext.schools.api.getstudentsresultinfo",'STUD00079')
	results = []

	for i in x_results:
		results.append(frappe._dict(i))

	table_headers = [['Course'],[]]

	for i in results[0]['score_breakdown']:
		table_headers[0].append(i['criteria'])
		table_headers[1].append(i['maximum_score'])

	table_headers[0].extend(['Total Score','Grade'])
	table_headers[1].append(results[0]['maximum_score'])
