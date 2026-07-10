# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from pypika.terms import Criterion

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.utilities.query import get_filter_conditions_qb


class TestQueryHelpers(ERPNextTestSuite):
	def test_get_filter_conditions_qb_negation_dict(self):
		# get_filter_conditions_qb is the query-builder equivalent of get_filters_cond, so it must
		# honour the same dict shorthand where a string value prefixed with "!" means "not equal"
		# ({"istable": "!1"} -> istable != "1"), not a literal istable = "!1".
		def _where(filters):
			dt = frappe.qb.DocType("DocType")
			criteria = get_filter_conditions_qb("DocType", filters, ignore_permissions=True)
			return frappe.qb.from_(dt).select(dt.name).where(Criterion.all(criteria)).get_sql()

		# "!1" -> not-equal, mirroring the legacy get_filters_cond rewrite
		self.assertIn("<>", _where({"istable": "!1"}))
		self.assertNotIn("'!1'", _where({"istable": "!1"}))
		# plain value stays equality; explicit [op, value] still honoured
		self.assertIn("=", _where({"istable": "1"}))
		self.assertNotIn("<>", _where({"istable": "1"}))
		self.assertIn("<>", _where({"istable": ["!=", "1"]}))
