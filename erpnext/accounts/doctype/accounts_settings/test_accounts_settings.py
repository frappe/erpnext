import frappe

from erpnext.accounts.doctype.accounts_settings.accounts_settings import get_posting_date_confirmation
from erpnext.tests.utils import ERPNextTestSuite


class TestAccountsSettings(ERPNextTestSuite):
	def test_posting_date_confirmation_uses_current_setting(self):
		for enabled in (0, 1, 0):
			frappe.db.set_single_value("Accounts Settings", "confirm_before_resetting_posting_date", enabled)
			self.assertEqual(get_posting_date_confirmation(), enabled)

	def test_stale_days(self):
		cur_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
		cur_settings.allow_stale = 0
		cur_settings.stale_days = 0

		self.assertRaises(frappe.ValidationError, cur_settings.save)

		cur_settings.stale_days = -1
		self.assertRaises(frappe.ValidationError, cur_settings.save)
