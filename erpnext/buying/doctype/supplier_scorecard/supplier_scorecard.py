# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import time
from datetime import timedelta

import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.utils import add_days, add_years, get_last_day, getdate, nowdate

from erpnext.buying.doctype.supplier_scorecard_period.supplier_scorecard_period import (
	make_supplier_scorecard,
)


class SupplierScorecard(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.buying.doctype.supplier_scorecard_scoring_criteria.supplier_scorecard_scoring_criteria import (
			SupplierScorecardScoringCriteria,
		)
		from erpnext.buying.doctype.supplier_scorecard_scoring_standing.supplier_scorecard_scoring_standing import (
			SupplierScorecardScoringStanding,
		)

		criteria: DF.Table[SupplierScorecardScoringCriteria]
		employee: DF.Link | None
		indicator_color: DF.Data | None
		notify_employee: DF.Check
		notify_supplier: DF.Check
		period: DF.Literal["Per Week", "Per Month", "Per Year"]
		prevent_pos: DF.Check
		prevent_rfqs: DF.Check
		standings: DF.Table[SupplierScorecardScoringStanding]
		status: DF.Data | None
		supplier: DF.Link | None
		supplier_score: DF.Data | None
		warn_pos: DF.Check
		warn_rfqs: DF.Check
		weighting_function: DF.SmallText
	# end: auto-generated types

	def validate(self):
		self.validate_standings()
		self.validate_criteria_weights()
		self.calculate_total_score()
		self.update_standing()

	def on_update(self):
		# Guard against recursion: the save() below re-enters on_update().
		if self.flags.in_rescore:
			return
		if make_all_scorecards(self.name) > 0:
			# New periods were created; re-save to refresh score and standings.
			self.flags.in_rescore = True
			try:
				self.save()
			finally:
				self.flags.in_rescore = False

	def validate_standings(self):
		# Standings must form a continuous chain of bands covering 0 to 100 with no gaps or overlaps
		expected_min = 0
		for standing in sorted(self.standings, key=lambda s: s.min_grade or 0):
			if standing.min_grade >= standing.max_grade:
				throw(
					_("Standing {0} must have a minimum grade lower than its maximum grade").format(
						standing.standing_name
					)
				)
			if standing.min_grade != expected_min:
				throw(_("Standing scores must be continuous and cover 0 to 100 without gaps or overlaps"))
			expected_min = standing.max_grade
		if expected_min < 100:
			throw(_("Standing scores must cover the full range from 0 to 100"))

	def validate_criteria_weights(self):
		weight = 0
		for c in self.criteria:
			weight += c.weight

		if weight != 100:
			throw(_("Criteria weights must add up to 100%"))

	def calculate_total_score(self):
		scorecards = frappe.get_all(
			"Supplier Scorecard Period",
			fields=["name"],
			filters={"scorecard": self.name, "docstatus": 1},
			order_by="end_date desc",
		)

		period = 0
		total_score = 0
		total_max_score = 0
		for scp in scorecards:
			my_sc = frappe.get_doc("Supplier Scorecard Period", scp.name)
			my_scp_weight = self.weighting_function
			my_scp_weight = my_scp_weight.replace("{period_number}", str(period))

			my_scp_maxweight = my_scp_weight.replace("{total_score}", "100")
			my_scp_weight = my_scp_weight.replace("{total_score}", str(my_sc.total_score))

			max_score = my_sc.calculate_weighted_score(my_scp_maxweight)
			score = my_sc.calculate_weighted_score(my_scp_weight)

			total_score += score
			total_max_score += max_score
			period += 1
		if total_max_score > 0:
			self.supplier_score = round(100.0 * (total_score / total_max_score), 1)
		else:
			self.supplier_score = 100

	def update_standing(self):
		highest_grade = max((s.max_grade for s in self.standings if s.max_grade), default=0)
		for standing in self.standings:
			if self.score_within_standing(standing, highest_grade):
				self.apply_standing(standing)

	def score_within_standing(self, standing, highest_grade):
		score = self.supplier_score
		above_min = not standing.min_grade or standing.min_grade <= score
		if standing.max_grade and standing.max_grade == highest_grade:
			# Top band is inclusive of its upper bound so a perfect score still maps to a standing
			return above_min and score <= standing.max_grade
		return above_min and (not standing.max_grade or standing.max_grade > score)

	def apply_standing(self, standing):
		self.status = standing.standing_name
		self.indicator_color = standing.standing_color
		self.notify_supplier = standing.notify_supplier
		self.notify_employee = standing.notify_employee
		self.employee_link = standing.employee_link

		for fieldname in ("prevent_pos", "prevent_rfqs", "warn_rfqs", "warn_pos"):
			self.set(fieldname, standing.get(fieldname))
			frappe.db.set_value("Supplier", self.supplier, fieldname, self.get(fieldname))


@frappe.whitelist()
def get_timeline_data(doctype: str, name: str):
	# Get a list of all the associated scorecards

	out = {}
	timeline_data = {}

	scorecards = frappe.get_all(
		"Supplier Scorecard Period",
		fields=["name", "start_date", "end_date", "total_score"],
		filters={"scorecard": name, "docstatus": 1},
		order_by="end_date desc",
	)

	for sc in scorecards:
		for single_date in daterange(sc.start_date, sc.end_date):
			timeline_data[time.mktime(single_date.timetuple())] = sc.total_score

	out["timeline_data"] = timeline_data
	return out


def daterange(start_date, end_date):
	for n in range(int((end_date - start_date).days) + 1):
		yield start_date + timedelta(n)


def refresh_scorecards():
	"""
	Refresh the scorecards
	"""
	scorecards = frappe.get_list("Supplier Scorecard", fields=["name"], pluck="name", limit_page_length=0)
	for sc_name in scorecards:
		# Check to see if any new scorecard periods are created
		if make_all_scorecards(sc_name) > 0:
			# Save the scorecard to update the score and standings
			frappe.get_doc("Supplier Scorecard", sc_name).save()


@frappe.whitelist(methods=["POST"])
def make_all_scorecards(docname: str):
	sc = frappe.get_doc("Supplier Scorecard", docname)
	supplier = frappe.get_doc("Supplier", sc.supplier)
	supplier.check_permission("write")

	start_date = getdate(supplier.creation)
	end_date = get_scorecard_date(sc.period, start_date)
	todays = getdate(nowdate())

	scp_count = 0
	first_start_date = todays
	last_end_date = todays

	while (start_date < todays) and (end_date <= todays):
		# check to make sure there is no scorecard period already created
		scorecards = frappe.get_all(
			"Supplier Scorecard Period",
			fields=["name"],
			filters={
				"scorecard": docname,
				"docstatus": 1,
				"start_date": ["<", end_date],
				"end_date": [">", start_date],
			},
			order_by="end_date desc",
		)
		if len(scorecards) == 0:
			period_card = make_supplier_scorecard(docname, None)
			period_card.start_date = start_date
			period_card.end_date = end_date
			period_card.insert(ignore_permissions=True)
			period_card.submit()
			scp_count = scp_count + 1
			if start_date < first_start_date:
				first_start_date = start_date
			last_end_date = end_date

		start_date = getdate(add_days(end_date, 1))
		end_date = get_scorecard_date(sc.period, start_date)
	if scp_count > 0:
		frappe.msgprint(
			_("Created {0} scorecards for {1} between:").format(scp_count, sc.supplier)
			+ " "
			+ str(first_start_date)
			+ " - "
			+ str(last_end_date)
		)
	return scp_count


def get_scorecard_date(period, start_date):
	if period == "Per Week":
		end_date = getdate(add_days(start_date, 7))
	elif period == "Per Month":
		end_date = get_last_day(start_date)
	elif period == "Per Year":
		end_date = add_days(add_years(start_date, 1), -1)
	return end_date


def get_default_scorecard_variables():
	return [
		{
			"param_name": "total_accepted_items",
			"variable_label": "Total Accepted Items",
			"path": "get_total_accepted_items",
		},
		{
			"param_name": "total_accepted_amount",
			"variable_label": "Total Accepted Amount",
			"path": "get_total_accepted_amount",
		},
		{
			"param_name": "total_rejected_items",
			"variable_label": "Total Rejected Items",
			"path": "get_total_rejected_items",
		},
		{
			"param_name": "total_rejected_amount",
			"variable_label": "Total Rejected Amount",
			"path": "get_total_rejected_amount",
		},
		{
			"param_name": "total_received_items",
			"variable_label": "Total Received Items",
			"path": "get_total_received_items",
		},
		{
			"param_name": "total_received_amount",
			"variable_label": "Total Received Amount",
			"path": "get_total_received_amount",
		},
		{
			"param_name": "rfq_response_days",
			"variable_label": "RFQ Response Days",
			"path": "get_rfq_response_days",
		},
		{
			"param_name": "sq_total_items",
			"variable_label": "SQ Total Items",
			"path": "get_sq_total_items",
		},
		{
			"param_name": "sq_total_number",
			"variable_label": "SQ Total Number",
			"path": "get_sq_total_number",
		},
		{
			"param_name": "rfq_total_number",
			"variable_label": "RFQ Total Number",
			"path": "get_rfq_total_number",
		},
		{
			"param_name": "rfq_total_items",
			"variable_label": "RFQ Total Items",
			"path": "get_rfq_total_items",
		},
		{
			"param_name": "tot_item_days",
			"variable_label": "Total Item Days",
			"path": "get_item_workdays",
		},
		{
			"param_name": "on_time_shipment_num",
			"variable_label": "# of On Time Shipments",
			"path": "get_on_time_shipments",
		},
		{
			"param_name": "cost_of_delayed_shipments",
			"variable_label": "Cost of Delayed Shipments",
			"path": "get_cost_of_delayed_shipments",
		},
		{
			"param_name": "cost_of_on_time_shipments",
			"variable_label": "Cost of On Time Shipments",
			"path": "get_cost_of_on_time_shipments",
		},
		{
			"param_name": "total_working_days",
			"variable_label": "Total Working Days",
			"path": "get_total_workdays",
		},
		{
			"param_name": "tot_cost_shipments",
			"variable_label": "Total Cost of Shipments",
			"path": "get_total_cost_of_shipments",
		},
		{
			"param_name": "tot_days_late",
			"variable_label": "Total Days Late",
			"path": "get_total_days_late",
		},
		{
			"param_name": "total_shipments",
			"variable_label": "Total Shipments",
			"path": "get_total_shipments",
		},
		{
			"param_name": "total_ordered",
			"variable_label": "Total Ordered",
			"path": "get_ordered_qty",
		},
		{
			"param_name": "total_invoiced",
			"variable_label": "Total Invoiced",
			"path": "get_invoiced_qty",
		},
	]


def get_default_scorecard_standing():
	return [
		{
			"min_grade": 0.0,
			"prevent_rfqs": 1,
			"warn_rfqs": 0,
			"notify_supplier": 0,
			"max_grade": 30.0,
			"prevent_pos": 1,
			"warn_pos": 0,
			"standing_color": "Red",
			"notify_employee": 0,
			"standing_name": "Very Poor",
		},
		{
			"min_grade": 30.0,
			"prevent_rfqs": 0,
			"warn_rfqs": 1,
			"notify_supplier": 0,
			"max_grade": 50.0,
			"prevent_pos": 0,
			"warn_pos": 1,
			"standing_color": "Yellow",
			"notify_employee": 0,
			"standing_name": "Poor",
		},
		{
			"min_grade": 50.0,
			"prevent_rfqs": 0,
			"warn_rfqs": 0,
			"notify_supplier": 0,
			"max_grade": 80.0,
			"prevent_pos": 0,
			"warn_pos": 0,
			"standing_color": "Green",
			"notify_employee": 0,
			"standing_name": "Average",
		},
		{
			"min_grade": 80.0,
			"prevent_rfqs": 0,
			"warn_rfqs": 0,
			"notify_supplier": 0,
			"max_grade": 100.0,
			"prevent_pos": 0,
			"warn_pos": 0,
			"standing_color": "Blue",
			"notify_employee": 0,
			"standing_name": "Excellent",
		},
	]


def make_default_records():
	install_variable_docs = get_default_scorecard_variables()
	for d in install_variable_docs:
		d["doctype"] = "Supplier Scorecard Variable"
		frappe.get_doc(d).insert(ignore_if_duplicate=True)

	install_standing_docs = get_default_scorecard_standing()
	for d in install_standing_docs:
		d["doctype"] = "Supplier Scorecard Standing"
		frappe.get_doc(d).insert(ignore_if_duplicate=True)
