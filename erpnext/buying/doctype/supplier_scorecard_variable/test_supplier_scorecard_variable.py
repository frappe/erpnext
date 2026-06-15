# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.utils import flt, getdate

from erpnext.buying.doctype.purchase_order.mapper import make_purchase_invoice as make_pi_from_po
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.doctype.supplier.test_supplier import create_supplier
from erpnext.buying.doctype.supplier_scorecard_variable.supplier_scorecard_variable import (
	VariablePathNotFound,
	get_cost_of_delayed_shipments,
	get_cost_of_on_time_shipments,
	get_invoiced_qty,
	get_item_workdays,
	get_late_shipments,
	get_on_time_shipments,
	get_ordered_qty,
	get_total_accepted_amount,
	get_total_accepted_items,
	get_total_cost_of_shipments,
	get_total_days_late,
	get_total_received,
	get_total_received_amount,
	get_total_received_items,
	get_total_rejected_amount,
	get_total_rejected_items,
	get_total_shipments,
	get_total_workdays,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestSupplierScorecardVariable(ERPNextTestSuite):
	def test_variable_exist(self):
		for d in test_existing_variables:
			my_doc = frappe.get_doc("Supplier Scorecard Variable", d.get("name"))
			self.assertEqual(my_doc.param_name, d.get("param_name"))
			self.assertEqual(my_doc.variable_label, d.get("variable_label"))
			self.assertEqual(my_doc.path, d.get("path"))

	def test_path_exists(self):
		for d in test_good_variables:
			if frappe.db.exists(d):
				frappe.delete_doc(d.get("doctype"), d.get("name"))
			frappe.get_doc(d).insert()

		for d in test_bad_variables:
			self.assertRaises(VariablePathNotFound, frappe.get_doc(d).insert)


test_existing_variables = [
	{
		"param_name": "total_accepted_items",
		"name": "Total Accepted Items",
		"doctype": "Supplier Scorecard Variable",
		"variable_label": "Total Accepted Items",
		"path": "get_total_accepted_items",
	},
]

test_good_variables = [
	{
		"param_name": "good_variable1",
		"name": "Good Variable 1",
		"doctype": "Supplier Scorecard Variable",
		"variable_label": "Good Variable 1",
		"path": "get_total_accepted_items",
	},
]

test_bad_variables = [
	{
		"param_name": "fake_variable1",
		"name": "Fake Variable 1",
		"doctype": "Supplier Scorecard Variable",
		"variable_label": "Fake Variable 1",
		"path": "get_fake_variable1",
	},
]


class TestSupplierScorecardVariableMetrics(ERPNextTestSuite):
	"""Exercise the module-level get_* metric functions.

	Each function accepts a `scorecard` carrying ``supplier``/``start_date``/
	``end_date`` (in production a Supplier Scorecard Period document). A
	``frappe._dict`` with those attributes is a faithful stand-in, since the
	functions only ever read ``scorecard.supplier``, ``scorecard.start_date``,
	``scorecard.end_date`` and ``scorecard.get("start_date"/"end_date")``.

	Fixtures use a freshly-generated supplier so the date-windowed queries see
	only the documents created here -- no contamination from shared
	``_Test Supplier`` data. Amounts assume the PO/PR currency equals the
	company currency (conversion_rate == 1), which holds for ``_Test Company``.
	"""

	# Fixed past window fully inside the auto-created test fiscal years.
	START_DATE = "2023-07-01"
	END_DATE = "2023-07-31"

	def _scorecard(self, supplier):
		return frappe._dict(
			{
				"supplier": supplier,
				"start_date": getdate(self.START_DATE),
				"end_date": getdate(self.END_DATE),
				"company": "_Test Company",
			}
		)

	def _make_po(self, supplier, qty, rate, schedule_date, transaction_date=None):
		"""Submit a PO for `supplier` with a single _Test Item line.

		``create_purchase_order`` hardcodes the item schedule date, so the PO is
		built unsaved and the header/line dates are overridden before submit.
		"""
		po = create_purchase_order(
			supplier=supplier,
			qty=qty,
			rate=rate,
			transaction_date=transaction_date or self.START_DATE,
			do_not_save=True,
		)
		po.schedule_date = schedule_date
		po.items[0].schedule_date = schedule_date
		po.set_missing_values()
		po.insert()
		po.submit()
		return po

	def _receive_po(self, po, posting_date):
		"""Fully receive `po` on `posting_date` via the PO->PR mapper so the
		Purchase Receipt Item carries ``purchase_order_item`` (required by the
		on-time / days-late joins)."""
		from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt

		pr = make_purchase_receipt(po.name)
		pr.posting_date = posting_date
		pr.set_posting_time = 1
		pr.insert()
		pr.submit()
		return pr

	def _build_received_scenario(self):
		"""One supplier, two fully-received POs:

		* PO_A: qty 10 @ 100, scheduled 2023-07-10, received 2023-07-08 (on time)
		* PO_B: qty  5 @ 200, scheduled 2023-07-20, received 2023-07-25 (5d late)

		Returns (scorecard, supplier).
		"""
		supplier = create_supplier(supplier_name=frappe.generate_hash(length=10)).name

		po_a = self._make_po(supplier, qty=10, rate=100, schedule_date="2023-07-10")
		po_b = self._make_po(supplier, qty=5, rate=200, schedule_date="2023-07-20")

		self._receive_po(po_a, posting_date="2023-07-08")
		self._receive_po(po_b, posting_date="2023-07-25")

		return self._scorecard(supplier), supplier

	# ----- pure date helper (no fixtures) -----

	def test_get_total_workdays(self):
		sc = self._scorecard("irrelevant")
		expected = (getdate(self.END_DATE) - getdate(self.START_DATE)).days
		self.assertEqual(get_total_workdays(sc), expected)
		self.assertEqual(get_total_workdays(sc), 30)

	# ----- Purchase Order based counts / costs -----

	def test_total_shipments_and_cost(self):
		sc, _supplier = self._build_received_scenario()

		# Two PO lines scheduled inside the window.
		self.assertEqual(get_total_shipments(sc), 2)
		# base_amount = qty * rate (conversion 1): 10*100 + 5*200 = 2000.
		self.assertAlmostEqual(flt(get_total_cost_of_shipments(sc)), 2000.0, places=2)

	def test_ordered_qty(self):
		sc, _supplier = self._build_received_scenario()
		# Sum of PO total_qty for submitted POs in the transaction-date window.
		self.assertAlmostEqual(flt(get_ordered_qty(sc)), 15.0, places=2)

	def test_metrics_isolated_to_window(self):
		"""A PO scheduled outside the window must not be counted."""
		supplier = create_supplier(supplier_name=frappe.generate_hash(length=10)).name
		self._make_po(supplier, qty=7, rate=100, schedule_date="2023-07-15")
		# Scheduled in August -> outside the July window.
		self._make_po(supplier, qty=3, rate=100, schedule_date="2023-08-15")

		sc = self._scorecard(supplier)
		self.assertEqual(get_total_shipments(sc), 1)
		self.assertAlmostEqual(flt(get_total_cost_of_shipments(sc)), 700.0, places=2)

	# ----- Purchase Receipt based counts / amounts -----

	def test_received_counts_and_amounts(self):
		sc, _supplier = self._build_received_scenario()

		# Two PR lines posted inside the window.
		self.assertEqual(get_total_received(sc), 2)
		# received_qty: 10 + 5
		self.assertAlmostEqual(flt(get_total_received_items(sc)), 15.0, places=2)
		# received_qty * base_rate: 10*100 + 5*200 = 2000
		self.assertAlmostEqual(flt(get_total_received_amount(sc)), 2000.0, places=2)

	def test_accepted_and_rejected(self):
		sc, _supplier = self._build_received_scenario()

		# Nothing rejected via the mapper -> clean zero edge case.
		self.assertAlmostEqual(flt(get_total_rejected_items(sc)), 0.0, places=2)
		self.assertAlmostEqual(flt(get_total_rejected_amount(sc)), 0.0, places=2)
		# Accepted qty == ordered/received qty here.
		self.assertAlmostEqual(flt(get_total_accepted_items(sc)), 15.0, places=2)
		self.assertAlmostEqual(flt(get_total_accepted_amount(sc)), 2000.0, places=2)

	# ----- on-time vs late (PR posting_date vs PO schedule_date) -----

	def test_on_time_and_late_shipments(self):
		sc, _supplier = self._build_received_scenario()

		# PO_A received on/before its schedule_date and fully -> on time.
		self.assertEqual(get_on_time_shipments(sc), 1)
		# late = total_shipments - on_time = 2 - 1
		self.assertEqual(get_late_shipments(sc), 1)

	def test_on_time_and_delayed_cost(self):
		sc, _supplier = self._build_received_scenario()

		# Only PO_A's receipt is on time: base_amount 10 * 100 = 1000.
		self.assertAlmostEqual(flt(get_cost_of_on_time_shipments(sc)), 1000.0, places=2)
		# delayed = total_cost - on_time_cost = 2000 - 1000
		self.assertAlmostEqual(flt(get_cost_of_delayed_shipments(sc)), 1000.0, places=2)

	def test_total_days_late_delivered(self):
		sc, _supplier = self._build_received_scenario()

		# Only PO_B is late: DATEDIFF(2023-07-25, 2023-07-20) * qty 5 = 5 * 5 = 25.
		# Both POs are fully received, so the "missed" (undelivered) branch is 0.
		self.assertAlmostEqual(flt(get_total_days_late(sc)), 25.0, places=2)

	# ----- undelivered (missed) path: item workdays & days-late -----

	def test_undelivered_item_workdays_and_days_late(self):
		"""A submitted-but-unreceived PO drives the received_qty < qty branch."""
		supplier = create_supplier(supplier_name=frappe.generate_hash(length=10)).name
		# qty 4, scheduled 2023-07-15, never received -> received_qty 0 < 4.
		self._make_po(supplier, qty=4, rate=100, schedule_date="2023-07-15")
		sc = self._scorecard(supplier)

		# DATEDIFF(end_date 2023-07-31, schedule 2023-07-15) * qty 4 = 16 * 4 = 64.
		self.assertAlmostEqual(flt(get_item_workdays(sc)), 64.0, places=2)
		# No receipts -> delivered-late branch 0; missed branch uses
		# (qty - received_qty) = 4 -> 16 * 4 = 64.
		self.assertAlmostEqual(flt(get_total_days_late(sc)), 64.0, places=2)

	# ----- Purchase Invoice based qty -----

	def test_invoiced_qty(self):
		supplier = create_supplier(supplier_name=frappe.generate_hash(length=10)).name
		po = self._make_po(supplier, qty=8, rate=100, schedule_date="2023-07-12")

		pi = make_pi_from_po(po.name)
		pi.posting_date = "2023-07-14"
		pi.set_posting_time = 1
		pi.insert()
		pi.submit()

		sc = self._scorecard(supplier)
		self.assertAlmostEqual(flt(get_invoiced_qty(sc)), 8.0, places=2)

	# ----- empty-supplier guards (defaults) -----

	def test_zero_defaults_for_unknown_supplier(self):
		sc = self._scorecard(create_supplier(supplier_name=frappe.generate_hash(length=10)).name)

		self.assertEqual(get_total_shipments(sc), 0)
		self.assertEqual(get_total_received(sc), 0)
		self.assertAlmostEqual(flt(get_total_received_amount(sc)), 0.0, places=2)
		self.assertAlmostEqual(flt(get_total_cost_of_shipments(sc)), 0.0, places=2)
		self.assertAlmostEqual(flt(get_ordered_qty(sc)), 0.0, places=2)
		self.assertAlmostEqual(flt(get_invoiced_qty(sc)), 0.0, places=2)
		self.assertAlmostEqual(flt(get_total_days_late(sc)), 0.0, places=2)
		self.assertEqual(get_on_time_shipments(sc), 0)
