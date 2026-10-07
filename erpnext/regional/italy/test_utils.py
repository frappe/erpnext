from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.regional.italy.utils import set_payment_schedule_swift_number


class TestItalyUtils(FrappeTestCase):
	def test_set_payment_schedule_swift_number_reads_bank(self):
		# the SWIFT code lives on Bank, not on Bank Account: it is read through the account's bank
		values = {
			("Bank Account", "_Test Bank Account", "bank"): "_Test Bank",
			("Bank", "_Test Bank", "swift_number"): "BCITITMM",
		}
		doc = frappe._dict(
			payment_schedule=[
				frappe._dict(bank_account="_Test Bank Account"),
				frappe._dict(bank_account=None, bank_account_swift_number="STALE"),
			]
		)

		with patch("frappe.get_cached_value", side_effect=lambda *args: values.get(args)):
			set_payment_schedule_swift_number(doc)

		self.assertEqual(doc.payment_schedule[0].bank_account_swift_number, "BCITITMM")
		self.assertIsNone(doc.payment_schedule[1].bank_account_swift_number)
