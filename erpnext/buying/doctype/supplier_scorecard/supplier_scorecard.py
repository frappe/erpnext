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
		score = make_all_scorecards(self.name)
		if score > 0:
			self.save()

	def validate_standings(self):
		# Check that there are no overlapping scores and check that there are no missing scores
		score = 0
		for c1 in self.standings:
			for c2 in self.standings:
				if c1 != c2:
					if c1.max_grade > c2.min_grade and c1.min_grade < c2.max_grade:
						throw(
							_("Overlap in scoring between {0} and {1}").format(
								c1.standing_name, c2.standing_name
							)
						)
				if c2.min_grade == score:
					score = c2.max_grade
		if score < 100:
			throw(
				_(
					"Unable to find score starting at {0}. You need to have standing scores covering 0 to 100"
				).format(score)
			)

	def validate_criteria_weights(self):
		weight = 0
		for c in self.criteria:
			weight += c.weight

		if weight != 100:
			throw(_("Criteria weights must add up to 100%"))

	def calculate_total_score(self):
		scorecards = frappe.db.sql(
			"""
			SELECT
				scp.name
			FROM
				`tabSupplier Scorecard Period` scp
			WHERE
				scp.scorecard = %(sc)s
				AND scp.docstatus = 1
			ORDER BY
				scp.end_date DESC""",
			{"sc": self.name},
			as_dict=1,
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
		# Get the setup document

		for standing in self.standings:
			if (not standing.min_grade or (standing.min_grade <= self.supplier_score)) and (
				not standing.max_grade or (standing.max_grade > self.supplier_score)
			):
				self.status = standing.standing_name
				self.indicator_color = standing.standing_color
				self.notify_supplier = standing.notify_supplier
				self.notify_employee = standing.notify_employee
				self.employee_link = standing.employee_link

				# Update supplier standing info
				for fieldname in ("prevent_pos", "prevent_rfqs", "warn_rfqs", "warn_pos"):
					self.set(fieldname, standing.get(fieldname))
					frappe.db.set_value("Supplier", self.supplier, fieldname, self.get(fieldname))


@frappe.whitelist()
def get_timeline_data(doctype, name):
	# Get a list of all the associated scorecards
	scs = frappe.get_doc(doctype, name)
	out = {}
	timeline_data = {}
	scorecards = frappe.db.sql(
		"""
		SELECT
			sc.name
		FROM
			`tabSupplier Scorecard Period` sc
		WHERE
			sc.scorecard = %(scs)s
			AND sc.docstatus = 1""",
		{"scs": scs.name},
		as_dict=1,
	)

	for sc in scorecards:
		start_date, end_date, total_score = frappe.db.get_value(
			"Supplier Scorecard Period", sc.name, ["start_date", "end_date", "total_score"]
		)
		for single_date in daterange(start_date, end_date):
			timeline_data[time.mktime(single_date.timetuple())] = total_score

	out["timeline_data"] = timeline_data
	return out


def daterange(start_date, end_date):
	for n in range(int((end_date - start_date).days) + 1):
		yield start_date + timedelta(n)


def refresh_scorecards():
	scorecards = frappe.db.sql(
		"""
		SELECT
			sc.name
		FROM
			`tabSupplier Scorecard` sc""",
		{},
		as_dict=1,
	)
	for sc in scorecards:
		# Check to see if any new scorecard periods are created
		if make_all_scorecards(sc.name) > 0:
			# Save the scorecard to update the score and standings
			frappe.get_doc("Supplier Scorecard", sc.name).save()


@frappe.whitelist()
def make_all_scorecards(docname):
	sc = frappe.get_doc("Supplier Scorecard", docname)
	supplier = frappe.get_doc("Supplier", sc.supplier)

	start_date = getdate(supplier.creation)
	end_date = get_scorecard_date(sc.period, start_date)
	todays = getdate(nowdate())

	scp_count = 0
	first_start_date = todays
	last_end_date = todays

	while (start_date < todays) and (end_date <= todays):
		# check to make sure there is no scorecard period already created
		scorecards = frappe.db.sql(
			"""
			SELECT
				scp.name
			FROM
				`tabSupplier Scorecard Period` scp
			WHERE
				scp.scorecard = %(sc)s
				AND scp.docstatus = 1
				AND (
					(scp.start_date > %(end_date)s
					AND scp.end_date < %(start_date)s)
				OR
					(scp.start_date < %(end_date)s
					AND scp.end_date > %(start_date)s))
			ORDER BY
				scp.end_date DESC""",
			{"sc": docname, "start_date": start_date, "end_date": end_date},
			as_dict=1,
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


def make_default_records():
	install_variable_docs = [
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
	install_standing_docs = [
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

	for d in install_variable_docs:
		try:
			d["doctype"] = "Supplier Scorecard Variable"
			frappe.get_doc(d).insert()
		except frappe.NameError:
			pass
	for d in install_standing_docs:
		try:
			d["doctype"] = "Supplier Scorecard Standing"
			frappe.get_doc(d).insert()
		except frappe.NameError:
			pass
