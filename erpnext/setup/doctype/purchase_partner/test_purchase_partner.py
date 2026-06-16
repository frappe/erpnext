# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.tests.utils import ERPNextTestSuite


class TestPurchasePartner(ERPNextTestSuite):
	def setUp(self):
		self.partner = make_purchase_partner()

	def tearDown(self):
		frappe.delete_doc("Purchase Partner", self.partner.name, force=True)

	def test_purchase_partner_creation(self):
		self.assertEqual(self.partner.commission_rate, 10.0)
		self.assertEqual(self.partner.territory, "_Test Territory")

	def test_commission_calculated_on_purchase_order(self):
		po = create_purchase_order(do_not_submit=True)
		po.purchase_partner = self.partner.name
		po.commission_rate = self.partner.commission_rate
		# grant_commission defaults to 1 fetched from item, ensure it's set
		for item in po.items:
			item.grant_commission = 1
		po.save()

		self.assertEqual(po.commission_rate, 10.0)
		expected_commission = po.base_net_total * 10.0 / 100.0
		self.assertAlmostEqual(po.total_commission, expected_commission, places=2)
		self.assertAlmostEqual(po.amount_eligible_for_commission, po.base_net_total, places=2)

	def test_commission_zero_when_grant_commission_false(self):
		po = create_purchase_order(do_not_submit=True)
		po.purchase_partner = self.partner.name
		po.commission_rate = 10.0
		for item in po.items:
			item.grant_commission = 0
		po.save()

		self.assertEqual(po.total_commission, 0)
		self.assertEqual(po.amount_eligible_for_commission, 0)

	def test_commission_rate_validation(self):
		po = create_purchase_order(do_not_submit=True)
		po.purchase_partner = self.partner.name
		po.commission_rate = 110.0
		with self.assertRaises(frappe.ValidationError):
			po.save()

	def test_commission_on_purchase_invoice(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice

		pi = make_purchase_invoice(do_not_save=True)
		pi.purchase_partner = self.partner.name
		pi.commission_rate = self.partner.commission_rate
		for item in pi.items:
			item.grant_commission = 1
		pi.save()

		self.assertEqual(pi.commission_rate, 10.0)
		expected_commission = pi.base_net_total * 10.0 / 100.0
		self.assertAlmostEqual(pi.total_commission, expected_commission, places=2)

	def test_purchase_partner_commission_summary_report(self):
		from erpnext.buying.report.purchase_partner_commission_summary.purchase_partner_commission_summary import (
			execute,
		)

		po = create_purchase_order(do_not_submit=True)
		po.purchase_partner = self.partner.name
		po.commission_rate = 10.0
		for item in po.items:
			item.grant_commission = 1
		po.save()
		po.submit()

		columns, data = execute(
			{
				"company": "_Test Company",
				"doctype": "Purchase Order",
				"purchase_partner": self.partner.name,
			}
		)

		self.assertTrue(len(columns) > 0)
		self.assertTrue(any(row.get("purchase_partner") == self.partner.name for row in data))

		po.cancel()


def make_purchase_partner(**kwargs):
	kwargs = frappe._dict(kwargs)
	partner = frappe.new_doc("Purchase Partner")
	partner.partner_name = kwargs.partner_name or "_Test Purchase Partner"
	partner.territory = kwargs.territory or "_Test Territory"
	partner.commission_rate = kwargs.commission_rate or 10.0
	if not frappe.db.exists("Purchase Partner", partner.partner_name):
		partner.insert(ignore_permissions=True)
	else:
		partner = frappe.get_doc("Purchase Partner", partner.partner_name)
	return partner
