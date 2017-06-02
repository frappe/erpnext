# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import throw, _
from frappe.model.document import Document
import time
from datetime import timedelta, date

class SupplierScorecard(Document):
	
	def validate(self):
		self.validate_standings()
		self.validate_criteria_weights()
		self.calculate_total_score()
		self.update_standing()
		
		
		
	def validate_standings(self):
		# Check that there are no overlapping scores
		for c1 in self.standings:
			for c2 in self.standings:
				if c1 != c2:
					if (c1.max_grade > c2.min_grade and c1.min_grade < c2.max_grade):
						frappe.throw(_('Overlap in scoring between ' + c1.standing_name + ' and ' + c2.standing_name))
		
		# Check that there are no missing scores
		score = 0
		for c1 in self.standings:
			for c2 in self.standings:
				if c1.min_grade == score:
					score = c1.max_grade
		if score != 100:
			frappe.throw(_('Unable to find score starting at ' + str(score) + '. You need to have standing scores covering 0 to 100'))
			
	def validate_criteria_weights(self):
	
		weight = 0
		for c in self.criteria:
			weight += c.weight
		
		if weight != 100:
			frappe.throw(_('Criteria weights must add up to 100%'))
			
	def calculate_total_score(self):
		scorecards = frappe.db.sql("""
			SELECT
				scp.name
			FROM
				`tabSupplier Scorecard Period` scp
			WHERE
				scp.scorecard = %(sc)s
			ORDER BY
				scp.end_date DESC""", 
				{"sc": self.name}, as_dict=1)
		
		period = 0
		total_score = 0
		total_max_score = 0
		for scp in scorecards:
			my_sc = frappe.get_doc('Supplier Scorecard Period', scp.name)
			my_scp_weight = self.weighting_function
			my_scp_weight = my_scp_weight.replace('period_number', str(period))
			
			my_scp_maxweight = my_scp_weight.replace('total_score', '100')
			my_scp_weight = my_scp_weight.replace('total_score', str(my_sc.total_score))
			
			max_score = my_sc.calculate_weighted_score(my_scp_maxweight)
			score = my_sc.calculate_weighted_score(my_scp_weight)
			
			total_score += score
			total_max_score += max_score
			period += 1
		self.supplier_score = round(100.0 * (total_score / total_max_score) ,1)
		
	def update_standing(self):
		# Get the setup document

		mystanding = None
		mymax = None
		myscore = 0
		for standing in self.standings:
			if (not standing.min_grade or (standing.min_grade <= self.supplier_score)) and \
				(not standing.max_grade or (standing.max_grade > self.supplier_score)):
				self.status = standing.standing_name
				self.indicator_color = standing.standing_color
				self.prevent_rfqs = standing.prevent_rfqs
				self.prevent_pos = standing.prevent_pos
				self.notify_supplier = standing.notify_supplier
				self.notify_employee = standing.notify_employee
				self.employee_link = standing.employee_link
		
		
		
@frappe.whitelist()	
def timeline_data(doctype, name):
	# Get a list of all the associated scorecards
	scs = frappe.get_doc(doctype, name)
	out = {}
	timeline_data = {}
	scorecards = frappe.db.sql("""
		SELECT
			sc.name
		FROM
			`tabSupplier Scorecard Period` sc
		WHERE
			sc.scorecard = %(scs)s""", 
			{"scs": scs.name}, as_dict=1)
	
	for sc in scorecards:
		sc = frappe.get_doc('Supplier Scorecard Period', sc.name)

		for single_date in daterange(sc.start_date, sc.end_date):
			timeline_data[time.mktime(single_date.timetuple())] =  sc.total_score
	out['timeline_data'] = timeline_data
	return out
	
def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)+1):
        yield start_date + timedelta(n)

