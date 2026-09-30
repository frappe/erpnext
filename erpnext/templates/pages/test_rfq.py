# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.utils import formatdate

from erpnext.buying.doctype.request_for_quotation.mapper import make_supplier_quotation_from_rfq
from erpnext.buying.doctype.request_for_quotation.test_request_for_quotation import (
	make_request_for_quotation,
)
from erpnext.templates.pages.rfq import get_link_quotation
from erpnext.tests.utils import ERPNextTestSuite


class TestRFQPage(ERPNextTestSuite):
	"""Exercise the query-builder helper backing the RFQ supplier-portal page.

	``get_link_quotation`` joins Supplier Quotation Item -> Supplier Quotation and
	returns the linked quotations for a given (supplier, rfq) pair. The assertions
	below seed a real RFQ + Supplier Quotation and verify the converted query
	returns the expected row(s) on both engines.
	"""

	def test_get_link_quotation_returns_linked_quotation(self):
		# Seed: RFQ for _Test Supplier / _Test Supplier 1, then a Supplier Quotation
		# raised against it for _Test Supplier.
		rfq = make_request_for_quotation()
		supplier = rfq.suppliers[0].supplier  # "_Test Supplier"

		sq = make_supplier_quotation_from_rfq(rfq.name, for_supplier=supplier)
		sq.submit()

		# Sanity: the mapper stamps the child rows with the source RFQ, which is
		# the column the converted query filters on.
		self.assertEqual(sq.items[0].request_for_quotation, rfq.name)

		# Seed a second Supplier Quotation Item under the SAME parent + RFQ so the
		# Supplier Quotation Item -> Supplier Quotation join yields two identical rows.
		# distinct() must collapse them back to one; without it len(result) would be 2.
		dup = frappe.new_doc("Supplier Quotation Item")
		dup.update(sq.items[0].as_dict())
		dup.idx = sq.items[0].idx + 1
		dup.flags.name_set = True
		dup.name = frappe.generate_hash("sqi-rfq", 12)
		dup.db_insert()

		result = get_link_quotation(supplier, rfq.name)

		# Real-state assertion: exactly the seeded quotation comes back, with the
		# selected/derived columns the page template consumes.
		self.assertIsNotNone(result)
		# genuinely exercises distinct(): two SQ-item join rows collapse to one
		self.assertEqual(len(result), 1)

		row = result[0]
		self.assertEqual(row.name, sq.name)
		self.assertEqual(row.status, "Submitted")
		# transaction_date is post-processed through formatdate() by the helper.
		self.assertEqual(row.transaction_date, formatdate(sq.transaction_date))
		self.assertEqual({r.name for r in result}, {sq.name})

	def test_get_link_quotation_filters_by_supplier(self):
		# The quotation belongs to supplier[0]; supplier[1] must see nothing for
		# this RFQ. Guards the ``sq.supplier == supplier`` predicate.
		rfq = make_request_for_quotation()
		seeded_supplier = rfq.suppliers[0].supplier
		other_supplier = rfq.suppliers[1].supplier

		sq = make_supplier_quotation_from_rfq(rfq.name, for_supplier=seeded_supplier)
		sq.submit()

		self.assertIsNone(get_link_quotation(other_supplier, rfq.name))

	def test_get_link_quotation_no_quotation(self):
		# An RFQ with no Supplier Quotation raised yet returns None (helper coerces
		# an empty list to None). Guards the ``request_for_quotation == rfq`` filter.
		rfq = make_request_for_quotation()
		supplier = rfq.suppliers[0].supplier

		self.assertIsNone(get_link_quotation(supplier, rfq.name))
