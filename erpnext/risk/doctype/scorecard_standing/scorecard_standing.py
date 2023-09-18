# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class ScorecardStanding(Document):
	pass


@frappe.whitelist()
def get_scoring_standing(standing_name):
	standing = frappe.get_doc("Scorecard Standing", standing_name)

	return standing


@frappe.whitelist()
def get_standings_list():
	standings = frappe.db.sql(
		"""
		SELECT
			scs.name
		FROM
			`tabScorecard Standing` scs""",
		{},
		as_dict=1,
	)

	return standings
