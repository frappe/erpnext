from frappe.tests import IntegrationTestCase

from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order


class TestTaxesAndTotals(AccountsTestMixin, IntegrationTestCase):
	def test_distributed_discount_amount(self):
		so = make_sales_order(do_not_save=1)
		so.apply_discount_on = "Net Total"
		so.discount_amount = 100
		so.items[0].qty = 5
		so.items[0].rate = 100
		so.append("items", so.items[0].as_dict())
		so.items[1].qty = 5
		so.items[1].rate = 200
		so.save()

		calculate_taxes_and_totals(so)

		self.assertAlmostEqual(so.items[0].distributed_discount_amount, 33.33, places=2)
		self.assertAlmostEqual(so.items[1].distributed_discount_amount, 66.67, places=2)
		self.assertAlmostEqual(so.items[0].net_amount, 466.67, places=2)
		self.assertAlmostEqual(so.items[1].net_amount, 933.33, places=2)
		self.assertEqual(so.total, 1500)
		self.assertEqual(so.net_total, 1400)
		self.assertEqual(so.grand_total, 1400)

	def test_distributed_discount_amount_with_taxes(self):
		so = make_sales_order(do_not_save=1)
		so.apply_discount_on = "Grand Total"
		so.discount_amount = 100
		so.items[0].qty = 5
		so.items[0].rate = 100
		so.append("items", so.items[0].as_dict())
		so.items[1].qty = 5
		so.items[1].rate = 200
		so.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account VAT - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "VAT",
				"included_in_print_rate": True,
				"rate": 10,
			},
		)
		so.save()

		calculate_taxes_and_totals(so)

		# like in test_distributed_discount_amount, but reduced by the included tax
		self.assertAlmostEqual(so.items[0].distributed_discount_amount, 33.33 / 1.1, places=2)
		self.assertAlmostEqual(so.items[1].distributed_discount_amount, 66.67 / 1.1, places=2)
		self.assertAlmostEqual(so.items[0].net_amount, 466.67 / 1.1, places=2)
		self.assertAlmostEqual(so.items[1].net_amount, 933.33 / 1.1, places=2)
		self.assertEqual(so.total, 1500)
		self.assertAlmostEqual(so.net_total, 1272.73, places=2)
		self.assertEqual(so.grand_total, 1400)
