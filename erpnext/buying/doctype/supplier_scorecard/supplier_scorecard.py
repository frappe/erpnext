# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import throw, _
from frappe.model.document import Document
import time
from datetime import timedelta, date
from frappe.utils import nowdate, get_last_day, get_first_day, getdate, add_days, add_years
from erpnext.buying.doctype.supplier_scorecard_period.supplier_scorecard_period import make_supplier_scorecard

class SupplierScorecard(Document):
	
	def validate(self):
		self.validate_standings()
		self.validate_criteria_weights()
		make_all_scorecards(self.name)
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
		if score < 100 :
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
		if total_max_score > 0:
			self.supplier_score = round(100.0 * (total_score / total_max_score) ,1)
		else:
			self.supplier_score =  100
		
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
				
				#Update supplier standing info
				frappe.db.set_value("Supplier", self.supplier, "prevent_pos", self.prevent_pos)
				frappe.db.set_value("Supplier", self.supplier, "prevent_rfqs", self.prevent_rfqs)
		
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

def refresh_scorecards():
	scorecards = frappe.db.sql("""
		SELECT
			sc.name
		FROM
			`tabSupplier Scorecard` sc""", 
			{}, as_dict=1)
	for sc in scorecards:
		# Check to see if any new scorecard periods are created
		if make_all_scorecards(sc.name) > 0:
			# Save the scorecard to update the score and standings
			sc.save()
		
		
@frappe.whitelist()
def make_all_scorecards(docname):
	
	sc = frappe.get_doc('Supplier Scorecard', docname)
	supplier = frappe.get_doc('Supplier',sc.supplier)
	
	start_date = getdate(supplier.creation)
	end_date = get_scorecard_date(sc.period, start_date)
	todays = getdate(nowdate())

	scp_count = 0
	while (start_date < todays) and (end_date <= todays):
		# check to make sure there is no scorecard period already created
		scorecards = frappe.db.sql("""
			SELECT
				scp.name
			FROM
				`tabSupplier Scorecard Period` scp
			WHERE
				scp.scorecard = %(sc)s
				AND
					(scp.start_date > %(end_date)s
					AND scp.end_date < %(start_date)s)
				OR
					(scp.start_date < %(end_date)s
					AND scp.end_date > %(start_date)s)
			ORDER BY
				scp.end_date DESC""", 
				{"sc": docname,"start_date": start_date,"end_date": end_date}, as_dict=1)
		if len(scorecards) == 0:
			period_card = make_supplier_scorecard(docname, None)
			period_card.start_date = start_date
			period_card.end_date = end_date
			period_card.save()
			scp_count = scp_count + 1
			frappe.msgprint("Created scorecard for " + sc.supplier + " between " + str(start_date) + " and " + str(end_date))
		start_date = getdate(add_days(end_date,1))
		end_date = get_scorecard_date(sc.period, start_date)
	return scp_count
	
def get_scorecard_date(period, start_date):
	if period == 'Per Day':
		end_date = getdate(add_days(start_date,1))
	elif period == 'Per Week':
		end_date = getdate(add_days(start_date,7))
	elif period == 'Per Month':
		end_date = get_last_day(start_date)
	elif period == 'Per Year':
		end_date = add_days(add_years(start_date,1), -1)
	return end_date