from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.tests.utils import ERPNextTestSuite


class TestTaxesAndTotals(ERPNextTestSuite):
	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": 1})
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

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": 1})
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

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": 1})
	def test_distributed_discount_amount_with_rounding_adjustment(self):
		so = make_sales_order(do_not_save=1)
		so.apply_discount_on = "Net Total"
		so.discount_amount = 10
		so.items[0].qty = 1
		so.items[0].rate = 100
		so.append("items", so.items[0].as_dict())
		so.append("items", so.items[0].as_dict())
		so.save()

		calculate_taxes_and_totals(so)

		# the rounding adjustment lands on the second line
		self.assertAlmostEqual(so.items[1].net_amount, 96.66, places=2)
		self.assertAlmostEqual(so.items[1].distributed_discount_amount, 3.34, places=2)

		for item in so.items:
			self.assertAlmostEqual(item.amount - item.distributed_discount_amount, item.net_amount, places=2)
		self.assertAlmostEqual(
			sum(i.distributed_discount_amount for i in so.items), so.discount_amount, places=2
		)
		self.assertEqual(so.net_total, 290)

	def test_100_percent_discount_with_inclusive_tax(self):
		"""Test that 100% discount with inclusive taxes results in zero net_total"""
		so = make_sales_order(do_not_save=1)
		so.apply_discount_on = "Grand Total"
		so.items[0].qty = 2
		so.items[0].rate = 1300
		so.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account VAT - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Account VAT",
				"included_in_print_rate": True,
				"rate": 9,
			},
		)
		so.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account Service Tax - _TC",
				"cost_center": "_Test Cost Center - _TC",
				"description": "Account Service Tax",
				"included_in_print_rate": True,
				"rate": 9,
			},
		)
		so.save()

		# Apply 100% discount
		so.discount_amount = 2600
		calculate_taxes_and_totals(so)

		# net_total should be exactly 0, not 0.01
		self.assertEqual(so.net_total, 0)
		self.assertEqual(so.grand_total, 0)
