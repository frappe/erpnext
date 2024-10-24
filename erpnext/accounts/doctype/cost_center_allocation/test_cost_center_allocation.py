# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
from erpnext.accounts.doctype.cost_center_allocation.cost_center_allocation import (
	InvalidChildCostCenter,
	InvalidDateError,
	InvalidMainCostCenter,
	MainCostCenterCantBeChild,
	WrongPercentageAllocation,
)
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry


class TestCostCenterAllocation(IntegrationTestCase):
	def setUp(self):
		cost_centers = [
			"Main Cost Center 1",
			"Main Cost Center 2",
			"Main Cost Center 3",
			"Sub Cost Center 1",
			"Sub Cost Center 2",
			"Sub Cost Center 3",
		]
		for cc in cost_centers:
			create_cost_center(cost_center_name=cc, company="_Test Company")

	def test_gle_based_on_cost_center_allocation(self):
		cca = create_cost_center_allocation(
			"_Test Company",
			"Main Cost Center 1 - _TC",
			{"Sub Cost Center 1 - _TC": 60, "Sub Cost Center 2 - _TC": 40},
		)

		jv = make_journal_entry(
			"Cash - _TC", "Sales - _TC", 100, cost_center="Main Cost Center 1 - _TC", submit=True
		)

		expected_values = [["Sub Cost Center 1 - _TC", 0.0, 60], ["Sub Cost Center 2 - _TC", 0.0, 40]]

		gle = frappe.qb.DocType("GL Entry")
		gl_entries = (
			frappe.qb.from_(gle)
			.select(gle.cost_center, gle.debit, gle.credit)
			.where(gle.voucher_type == "Journal Entry")
			.where(gle.voucher_no == jv.name)
			.where(gle.account == "Sales - _TC")
			.orderby(gle.cost_center)
		).run(as_dict=1)

		self.assertTrue(gl_entries)

		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_values[i][0], gle.cost_center)
			self.assertEqual(expected_values[i][1], gle.debit)
			self.assertEqual(expected_values[i][2], gle.credit)

		cca.cancel()
		jv.cancel()

	def test_main_cost_center_cant_be_child(self):
		# Main cost center itself cannot be entered in child table
		cca = create_cost_center_allocation(
			"_Test Company",
			"Main Cost Center 1 - _TC",
			{"Sub Cost Center 1 - _TC": 60, "Main Cost Center 1 - _TC": 40},
			save=False,
		)

		self.assertRaises(MainCostCenterCantBeChild, cca.save)

	def test_invalid_main_cost_center(self):
		# If main cost center is used for allocation under any other cost center,
		# allocation cannot be done against it
		cca1 = create_cost_center_allocation(
			"_Test Company",
			"Main Cost Center 1 - _TC",
			{"Sub Cost Center 1 - _TC": 60, "Sub Cost Center 2 - _TC": 40},
		)

		cca2 = create_cost_center_allocation(
			"_Test Company", "Sub Cost Center 1 - _TC", {"Sub Cost Center 2 - _TC": 100}, save=False
		)

		self.assertRaises(InvalidMainCostCenter, cca2.save)

		cca1.cancel()

	def test_if_child_cost_center_has_any_allocation_record(self):
		# Check if any child cost center is used as main cost center in any other existing allocation
		cca1 = create_cost_center_allocation(
			"_Test Company",
			"Main Cost Center 1 - _TC",
			{"Sub Cost Center 1 - _TC": 60, "Sub Cost Center 2 - _TC": 40},
		)

		cca2 = create_cost_center_allocation(
			"_Test Company",
			"Main Cost Center 2 - _TC",
			{"Main Cost Center 1 - _TC": 60, "Sub Cost Center 1 - _TC": 40},
			save=False,
		)

		self.assertRaises(InvalidChildCostCenter, cca2.save)

		cca1.cancel()

	def test_total_percentage(self):
		cca = create_cost_center_allocation(
			"_Test Company",
			"Main Cost Center 1 - _TC",
			{"Sub Cost Center 1 - _TC": 40, "Sub Cost Center 2 - _TC": 40},
			save=False,
		)
		self.assertRaises(WrongPercentageAllocation, cca.save)

	def test_valid_from_based_on_existing_gle(self):
		# GLE posted against Sub Cost Center 1 on today
		jv = make_journal_entry(
			"Cash - _TC",
			"Sales - _TC",
			100,
			cost_center="Main Cost Center 1 - _TC",
			posting_date=today(),
			submit=True,
		)

		# try to set valid from as yesterday
		cca = create_cost_center_allocation(
			"_Test Company",
			"Main Cost Center 1 - _TC",
			{"Sub Cost Center 1 - _TC": 60, "Sub Cost Center 2 - _TC": 40},
			valid_from=add_days(today(), -1),
			save=False,
		)

		self.assertRaises(InvalidDateError, cca.save)

		jv.cancel()

	def test_multiple_cost_center_allocation_on_same_main_cost_center(self):
		coa1 = create_cost_center_allocation(
			"_Test Company",
			"Main Cost Center 3 - _TC",
			{"Sub Cost Center 1 - _TC": 30, "Sub Cost Center 2 - _TC": 30, "Sub Cost Center 3 - _TC": 40},
			valid_from=add_days(today(), -5),
		)

		coa2 = create_cost_center_allocation(
			"_Test Company",
			"Main Cost Center 3 - _TC",
			{"Sub Cost Center 1 - _TC": 50, "Sub Cost Center 2 - _TC": 50},
			valid_from=add_days(today(), -1),
		)

		jv = make_journal_entry(
			"Cash - _TC",
			"Sales - _TC",
			100,
			cost_center="Main Cost Center 3 - _TC",
			posting_date=today(),
			submit=True,
		)

		expected_values = {"Sub Cost Center 1 - _TC": 50, "Sub Cost Center 2 - _TC": 50}

		gle = frappe.qb.DocType("GL Entry")
		gl_entries = (
			frappe.qb.from_(gle)
			.select(gle.cost_center, gle.debit, gle.credit)
			.where(gle.voucher_type == "Journal Entry")
			.where(gle.voucher_no == jv.name)
			.where(gle.account == "Sales - _TC")
			.orderby(gle.cost_center)
		).run(as_dict=1)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertTrue(gle.cost_center in expected_values)
			self.assertEqual(gle.debit, 0)
			self.assertEqual(gle.credit, expected_values[gle.cost_center])

		coa1.cancel()
		coa2.cancel()
		jv.cancel()


def create_cost_center_allocation(
	company,
	main_cost_center,
	allocation_percentages,
	valid_from=None,
	valid_upto=None,
	save=True,
	submit=True,
):
	doc = frappe.new_doc("Cost Center Allocation")
	doc.main_cost_center = main_cost_center
	doc.company = company
	doc.valid_from = valid_from or today()
	doc.valid_upto = valid_upto
	for cc, percentage in allocation_percentages.items():
		doc.append("allocation_percentages", {"cost_center": cc, "percentage": percentage})
	if save:
		doc.save()
		if submit:
			doc.submit()

	return doc
