import unittest

import frappe


class TestAccountsSettings(unittest.TestCase):
	def test_stale_days(self):
		cur_settings = frappe.get_doc('Accounts Settings', 'Accounts Settings')
		cur_settings.allow_stale = 0
		cur_settings.stale_days = 0

		self.assertRaises(frappe.ValidationError, cur_settings.save)

		cur_settings.stale_days = -1
		self.assertRaises(frappe.ValidationError, cur_settings.save)
