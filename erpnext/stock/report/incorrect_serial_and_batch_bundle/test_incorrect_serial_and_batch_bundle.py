# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import create_pos_invoice
from erpnext.stock.report.incorrect_serial_and_batch_bundle.incorrect_serial_and_batch_bundle import (
	execute,
)


class TestIncorrectSerialAndBatchBundleForPOS(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		from erpnext.accounts.doctype.mode_of_payment.test_mode_of_payment import (
			set_default_account_for_mode_of_payment,
		)
		from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import init_user_and_profile
		from erpnext.accounts.doctype.pos_opening_entry.test_pos_opening_entry import create_opening_entry

		super().setUpClass()
		cls.test_user, cls.pos_profile = init_user_and_profile()
		create_opening_entry(cls.pos_profile, cls.test_user.name)
		frappe.set_user("Administrator")
		mode_of_payment = frappe.get_doc("Mode of Payment", "Bank Draft")
		set_default_account_for_mode_of_payment(mode_of_payment, "_Test Company", "_Test Bank - _TC")

	def test_bundle_of_unconsolidated_pos_invoice_is_not_flagged(self):
		from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
			get_serial_nos_from_bundle,
		)
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item

		entry = make_serialized_item(
			company="_Test Company",
			target_warehouse="Stores - _TC",
			cost_center="Main - _TC",
			expense_account="Cost of Goods Sold - _TC",
		)
		pos = create_pos_invoice(
			company="_Test Company",
			debit_to="Debtors - _TC",
			account_for_change_amount="Cash - _TC",
			warehouse="Stores - _TC",
			income_account="Sales - _TC",
			expense_account="Cost of Goods Sold - _TC",
			cost_center="Main - _TC",
			item=entry.items[0].item_code,
			serial_no=[get_serial_nos_from_bundle(entry.items[0].serial_and_batch_bundle)[0]],
			rate=1000,
			do_not_save=1,
		)
		pos.append("payments", {"mode_of_payment": "Bank Draft", "amount": 1000})
		pos.insert()
		pos.submit()

		data = execute(frappe._dict({"company": "_Test Company"}))[1]

		self.assertTrue(pos.items[0].serial_and_batch_bundle)
		self.assertNotIn(pos.items[0].serial_and_batch_bundle, [row.name for row in data])
