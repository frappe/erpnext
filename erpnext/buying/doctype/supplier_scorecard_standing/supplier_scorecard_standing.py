# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class SupplierScorecardStanding(Document):
	pass


@frappe.whitelist()
def get_scoring_standing(standing_name):
	standing = frappe.get_doc("Supplier Scorecard Standing", standing_name)

	return standing


@frappe.whitelist()
def get_standings_list():
	standings = frappe.db.sql("""
		SELECT
			scs.name
		FROM
			`tabSupplier Scorecard Standing` scs""",
			{}, as_dict=1)

	return standings