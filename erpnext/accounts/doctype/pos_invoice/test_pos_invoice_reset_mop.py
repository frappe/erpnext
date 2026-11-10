# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

# Regression test for https://github.com/frappe/erpnext/issues/56501
# AttributeError: 'POSInvoice' object has no attribute 'is_created_using_pos'
# when calling reset_mode_of_payments on a draft POS Invoice.

from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import (
	POSInvoiceTestMixin,
	create_pos_invoice,
)
from erpnext.accounts.doctype.pos_opening_entry.test_pos_opening_entry import create_opening_entry


class TestPOSInvoiceResetModeOfPayments(POSInvoiceTestMixin):
	def setUp(self):
		super().setUp()
		create_opening_entry(self.pos_profile, self.test_user.name)

	def test_reset_mode_of_payments_does_not_raise_attribute_error(self):
		"""Calling reset_mode_of_payments on a draft POS Invoice must not raise
		AttributeError for the missing is_created_using_pos attribute.

		update_multi_mode_option accesses doc.is_created_using_pos, which is a
		field on SalesInvoice but does not exist on POSInvoice, causing the error
		reported in #56501 when a user tries to edit a saved draft order.
		"""
		inv = create_pos_invoice(do_not_submit=True)

		# This call must not raise AttributeError on the missing field.
		inv.reset_mode_of_payments()

		# Payments should have been repopulated from the POS profile.
		self.assertTrue(len(inv.payments) > 0, "Payments should be populated after reset")
