# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.tests.utils import ERPNextTestSuite


def test_create_test_data():
	frappe.set_user("Administrator")
	# create test item
	if not frappe.db.exists("Item", "_Test Tesla Car"):
		item = frappe.get_doc(
			{
				"description": "_Test Tesla Car",
				"doctype": "Item",
				"has_batch_no": 0,
				"has_serial_no": 0,
				"inspection_required": 0,
				"is_stock_item": 1,
				"opening_stock": 100,
				"is_sub_contracted_item": 0,
				"item_code": "_Test Tesla Car",
				"item_group": "_Test Item Group",
				"item_name": "_Test Tesla Car",
				"apply_warehouse_wise_reorder_level": 0,
				"warehouse": "Stores - _TC",
				"valuation_rate": 5000,
				"standard_rate": 5000,
				"item_defaults": [
					{
						"company": "_Test Company",
						"default_warehouse": "Stores - _TC",
						"default_price_list": "_Test Price List",
						"expense_account": "Cost of Goods Sold - _TC",
						"buying_cost_center": "Main - _TC",
						"selling_cost_center": "Main - _TC",
						"income_account": "Sales - _TC",
					}
				],
			}
		)
		item.insert()
	# create test item price
	item_price = frappe.get_list(
		"Item Price",
		filters={"item_code": "_Test Tesla Car", "price_list": "_Test Price List"},
		fields=["name"],
	)
	if len(item_price) == 0:
		item_price = frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": "_Test Tesla Car",
				"price_list": "_Test Price List",
				"price_list_rate": 5000,
			}
		)
		item_price.insert()
	# create test item pricing rule
	if not frappe.db.exists("Pricing Rule", {"title": "_Test Pricing Rule for _Test Item"}):
		item_pricing_rule = frappe.get_doc(
			{
				"doctype": "Pricing Rule",
				"title": "_Test Pricing Rule for _Test Item",
				"apply_on": "Item Code",
				"items": [{"item_code": "_Test Tesla Car"}],
				"warehouse": "Stores - _TC",
				"coupon_code_based": 1,
				"selling": 1,
				"rate_or_discount": "Discount Percentage",
				"discount_percentage": 30,
				"company": "_Test Company",
				"currency": "INR",
				"for_price_list": "_Test Price List",
			}
		)
		item_pricing_rule.insert()
	# create test item sales partner
	if not frappe.db.exists("Sales Partner", "_Test Coupon Partner"):
		sales_partner = frappe.get_doc(
			{
				"doctype": "Sales Partner",
				"partner_name": "_Test Coupon Partner",
				"commission_rate": 2,
				"referral_code": "COPART",
				"territory": "All Territories",
			}
		)
		sales_partner.insert()
	# create test item coupon code
	if not frappe.db.exists("Coupon Code", "SAVE30"):
		pricing_rule = frappe.db.get_value(
			"Pricing Rule", {"title": "_Test Pricing Rule for _Test Item"}, ["name"]
		)
		coupon_code = frappe.get_doc(
			{
				"doctype": "Coupon Code",
				"coupon_name": "SAVE30",
				"coupon_code": "SAVE30",
				"pricing_rule": pricing_rule,
				"valid_from": "2014-01-01",
				"maximum_use": 1,
				"used": 0,
			}
		)
		coupon_code.insert()


class TestCouponCode(ERPNextTestSuite):
	def setUp(self):
		test_create_test_data()

	def make_coupon_order(self, coupon_name="SAVE30"):
		order = make_sales_order(
			company="_Test Company",
			warehouse="Stores - _TC",
			customer="_Test Customer",
			selling_price_list="_Test Price List",
			item_code="_Test Tesla Car",
			rate=5000,
			qty=1,
			do_not_save=True,
		)
		order.coupon_code = coupon_name
		return order

	def test_multiple_coupons_for_one_pricing_rule(self):
		coupon = frappe.get_doc("Coupon Code", "SAVE30")
		second_coupon = frappe.copy_doc(coupon)
		second_coupon.coupon_name = "_Test Second Coupon"
		second_coupon.coupon_code = "SECOND30"
		second_coupon.insert()

		for name in (coupon.name, second_coupon.name):
			with self.subTest(coupon=name):
				order = self.make_coupon_order(name).insert()
				self.assertEqual(order.items[0].rate, 3500)
				self.assertEqual(frappe.parse_json(order.items[0].pricing_rules), [coupon.pricing_rule])
				order.submit()
				self.assertEqual(frappe.db.get_value("Coupon Code", name, "used"), 1)

	def test_change_coupon_on_server_save(self):
		from erpnext.accounts.doctype.pricing_rule.pricing_rule import remove_pricing_rule_for_item

		frappe.db.set_single_value("Selling Settings", "allow_multiple_items", 1)
		coupon = frappe.get_doc("Coupon Code", "SAVE30")
		for discount_type, expected_rate in (
			("Discount Percentage", 4250),
			("Discount Amount", 4250),
			("Product", 5000),
		):
			with self.subTest(discount_type=discount_type):
				order = self.make_coupon_order().insert()
				self.assertEqual(order.items[0].rate, 3500)
				rule = frappe.copy_doc(frappe.get_doc("Pricing Rule", coupon.pricing_rule))
				if discount_type == "Product":
					rule.price_or_product_discount = "Product"
					rule.same_item = 1
					rule.free_qty = 1
				else:
					rule.rate_or_discount = discount_type
					rule.discount_percentage = 15
					rule.discount_amount = 750
				rule.insert()
				replacement = frappe.copy_doc(coupon)
				replacement.coupon_name = f"_Test Replacement {discount_type}"
				replacement.coupon_code = f"REPLACE-{discount_type}"
				replacement.pricing_rule = rule.name
				replacement.insert()
				order.coupon_code = replacement.name
				order.save()
				self.assertEqual(order.items[0].rate, expected_rate)
				self.assertEqual(frappe.parse_json(order.items[0].pricing_rules), [rule.name])
				self.assertEqual(sum(row.is_free_item for row in order.items), discount_type == "Product")
				if discount_type == "Discount Amount":
					reset_item = remove_pricing_rule_for_item(
						order.items[0].pricing_rules, order.items[0].as_dict(), rate=5000
					)
					self.assertEqual(reset_item.rate, 5000)
					self.assertEqual(reset_item.discount_percentage, 0)
				if discount_type == "Product":
					next_rule = frappe.copy_doc(rule)
					next_rule.same_item = 0
					next_rule.free_item = "_Test Item"
					next_rule.insert()
					next_coupon = frappe.copy_doc(replacement)
					next_coupon.coupon_name = "_Test Next Product Coupon"
					next_coupon.coupon_code = "NEXT-PRODUCT"
					next_coupon.pricing_rule = next_rule.name
					next_coupon.insert()
					for active_coupon in (next_coupon, replacement, next_coupon):
						order.coupon_code = active_coupon.name
						order.save()
						self.assertEqual(
							[row.pricing_rules for row in order.items if row.is_free_item],
							[active_coupon.pricing_rule],
						)
				order.coupon_code = None
				order.save()
				self.assertEqual(order.items[0].rate, 5000)
				self.assertEqual(order.items[0].discount_percentage, 0)
				self.assertFalse(order.items[0].pricing_rules)
				self.assertFalse(any(row.is_free_item for row in order.items))
				order.submit()
				self.assertEqual(frappe.db.get_value("Coupon Code", "SAVE30", "used"), 0)
				self.assertEqual(frappe.db.get_value("Coupon Code", replacement.name, "used"), 0)

	def test_gift_card_customer(self):
		from erpnext.selling.doctype.quotation import mapper
		from erpnext.selling.doctype.quotation.test_quotation import make_quotation

		coupon = frappe.get_doc("Coupon Code", "SAVE30")
		coupon.coupon_type = "Gift Card"
		coupon.customer = "_Test Customer"
		coupon.save()

		order = self.make_coupon_order()
		order.customer = "_Test Customer 1"
		with self.assertRaisesRegex(frappe.ValidationError, "Gift Card.*customer"):
			order.insert()
		self.make_coupon_order().insert()

		for party_type, customer_field, values in (
			("Lead", "lead_name", {"first_name": "Gift Card Lead"}),
			("Prospect", "prospect_name", {"company_name": "Gift Card Prospect", "company": "_Test Company"}),
		):
			with self.subTest(party_type=party_type):
				party = frappe.get_doc({"doctype": party_type, **values}).insert()
				for customer in (None, coupon.customer, "_Test Customer 1"):
					frappe.db.set_value("Customer", coupon.customer, customer_field, None)
					if customer:
						frappe.db.set_value("Customer", customer, customer_field, party.name)
					quotation = make_quotation(do_not_save=True)
					quotation.quotation_to = party_type
					quotation.party_name = party.name
					quotation.coupon_code = coupon.name
					if customer == coupon.customer:
						quotation.insert()
						quotation.submit()
						self.assertEqual(mapper.make_sales_order(quotation.name).customer, customer)
					else:
						with self.assertRaisesRegex(frappe.ValidationError, "Gift Card.*customer"):
							quotation.insert()

	def test_quotation_coupon_validity(self):
		from frappe.utils import add_days, today

		from erpnext.selling.doctype.quotation.test_quotation import make_quotation

		coupon = frappe.get_doc("Coupon Code", "SAVE30")
		for values, message in (
			({"valid_from": add_days(today(), 1)}, "validity has not started"),
			({"valid_upto": add_days(today(), -1)}, "validity has expired"),
			({"used": 1}, "no longer valid"),
		):
			with self.subTest(values=values):
				coupon.update({"valid_from": None, "valid_upto": None, "used": 0})
				coupon.update(values)
				coupon.save()
				quotation = make_quotation(do_not_save=True)
				quotation.coupon_code = coupon.name
				with self.assertRaisesRegex(frappe.ValidationError, message):
					quotation.insert()

		coupon.used = 0
		coupon.save()
		quotation = make_quotation(do_not_save=True)
		quotation.coupon_code = coupon.name
		quotation.insert()
		quotation.submit()
		self.assertEqual(frappe.db.get_value("Coupon Code", coupon.name, "used"), 0)

	def test_generated_coupon_codes_do_not_collide(self):
		coupons = []
		for name in ("Summer Savings 2026", "Summer Savings 2027"):
			coupon = frappe.copy_doc(frappe.get_doc("Coupon Code", "SAVE30"))
			coupon.coupon_type = "Promotional"
			coupon.coupon_name = name
			coupon.coupon_code = None
			coupon.insert()
			coupons.append(coupon)

		self.assertEqual(coupons[0].coupon_code, "SUMMER S")
		self.assertTrue(coupons[1].coupon_code.startswith("SUMMER S"))
		self.assertNotEqual(coupons[0].coupon_code, coupons[1].coupon_code)

	def test_disabled_pricing_rule_validation(self):
		coupon = frappe.get_doc("Coupon Code", "SAVE30")
		rule = frappe.get_doc("Pricing Rule", coupon.pricing_rule)
		rule.disable = 1
		rule.save()

		with self.subTest("new coupon cannot select a disabled rule"):
			new_coupon = frappe.copy_doc(coupon)
			new_coupon.coupon_name = "Festival Savings"
			new_coupon.coupon_code = "FESTSAVE"
			with self.assertRaisesRegex(frappe.ValidationError, "is disabled"):
				new_coupon.insert()

		with self.subTest("existing coupon can retain a disabled rule"):
			coupon.description = "Offer paused"
			coupon.save()
			coupon.reload()
			self.assertEqual(coupon.description, "Offer paused")
			self.assertEqual(coupon.pricing_rule, rule.name)

		with self.subTest("existing coupon cannot switch to a disabled rule"):
			disabled_rule = frappe.copy_doc(rule)
			disabled_rule.insert()
			coupon.reload()
			coupon.pricing_rule = disabled_rule.name
			with self.assertRaisesRegex(frappe.ValidationError, "is disabled"):
				coupon.save()
			coupon.reload()
			self.assertEqual(coupon.pricing_rule, rule.name)

	def test_cannot_save_coupon_with_reversed_validity_dates(self):
		coupon = frappe.get_doc("Coupon Code", "SAVE30")
		coupon.valid_from = "2026-09-17"
		coupon.valid_upto = "2026-09-02"
		with self.assertRaises(frappe.exceptions.InvalidDates):
			coupon.save()

	def test_sales_order_with_coupon_code(self):
		frappe.db.set_value("Coupon Code", "SAVE30", "used", 0)

		so = make_sales_order(
			company="_Test Company",
			warehouse="Stores - _TC",
			customer="_Test Customer",
			selling_price_list="_Test Price List",
			item_code="_Test Tesla Car",
			rate=5000,
			qty=1,
			do_not_save=True,
		)

		self.assertEqual(so.items[0].rate, 5000)

		so.coupon_code = "SAVE30"
		so.sales_partner = "_Test Coupon Partner"
		so.save()

		# check item price after coupon code is applied
		self.assertEqual(so.items[0].rate, 3500)

		so.submit()
		self.assertEqual(frappe.db.get_value("Coupon Code", "SAVE30", "used"), 1)

	def test_coupon_without_max_use(self):
		from erpnext.accounts.doctype.pricing_rule.utils import (
			update_coupon_code_count,
			validate_coupon_code,
		)

		coupon = frappe.get_doc(
			{
				"doctype": "Coupon Code",
				"coupon_name": "_Test Coupon Without Max Use",
				"coupon_code": "TESTUNLIMITED",
				"from_external_ecomm_platform": 1,  # avoids requirement for pricing rule
				"valid_from": frappe.utils.nowdate(),
				"maximum_use": 0,
				"used": 0,
			}
		)
		coupon.insert(ignore_permissions=True)

		# Validate initial state
		self.assertEqual(coupon.used, 0)
		self.assertEqual(coupon.maximum_use, 0)

		# Use coupon multiple times
		for _ in range(5):
			validate_coupon_code(coupon.name)
			update_coupon_code_count(coupon.name, "used")
			coupon.reload()

		# Check that the coupon is still valid and usage count increased
		self.assertEqual(coupon.used, 5)
		validate_coupon_code(coupon.name)  # This should not raise an error

		# Clean up
		coupon.delete()

	def test_validate_coupon_code_rejections(self):
		from frappe.utils import add_days, nowdate

		from erpnext.accounts.doctype.pricing_rule.utils import validate_coupon_code

		pricing_rule = frappe.db.get_value("Pricing Rule", {"title": "_Test Pricing Rule for _Test Item"})

		def make_coupon(name, **kwargs):
			frappe.delete_doc_if_exists("Coupon Code", name)
			return frappe.get_doc(
				{
					"doctype": "Coupon Code",
					"coupon_name": name,
					"coupon_code": name,
					"coupon_type": "Promotional",
					"pricing_rule": pricing_rule,
					**kwargs,
				}
			).insert(ignore_permissions=True)

		with self.subTest("validity not yet started"):
			make_coupon("_Test Coupon Future", valid_from=add_days(nowdate(), 5))
			self.assertRaises(frappe.ValidationError, validate_coupon_code, "_Test Coupon Future")

		with self.subTest("validity expired"):
			make_coupon("_Test Coupon Expired", valid_upto=add_days(nowdate(), -5))
			self.assertRaises(frappe.ValidationError, validate_coupon_code, "_Test Coupon Expired")

		with self.subTest("maximum use exhausted"):
			make_coupon("_Test Coupon Exhausted", maximum_use=2, used=2)
			self.assertRaises(frappe.ValidationError, validate_coupon_code, "_Test Coupon Exhausted")

		with self.subTest("valid coupon passes"):
			make_coupon("_Test Coupon Valid", maximum_use=5, used=1, valid_upto=add_days(nowdate(), 5))
			validate_coupon_code("_Test Coupon Valid")  # no raise

	def test_update_coupon_code_count_cancel_and_exhaust(self):
		from erpnext.accounts.doctype.pricing_rule.utils import update_coupon_code_count

		pricing_rule = frappe.db.get_value("Pricing Rule", {"title": "_Test Pricing Rule for _Test Item"})
		frappe.delete_doc_if_exists("Coupon Code", "_Test Coupon Count")
		frappe.get_doc(
			{
				"doctype": "Coupon Code",
				"coupon_name": "_Test Coupon Count",
				"coupon_code": "_Test Coupon Count",
				"coupon_type": "Promotional",
				"pricing_rule": pricing_rule,
				"maximum_use": 2,
				"used": 1,
			}
		).insert(ignore_permissions=True)

		# cancelling a transaction releases one use
		update_coupon_code_count("_Test Coupon Count", "cancelled")
		self.assertEqual(frappe.db.get_value("Coupon Code", "_Test Coupon Count", "used"), 0)

		# using up to the maximum is allowed, beyond it is rejected
		update_coupon_code_count("_Test Coupon Count", "used")
		update_coupon_code_count("_Test Coupon Count", "used")
		self.assertEqual(frappe.db.get_value("Coupon Code", "_Test Coupon Count", "used"), 2)
		self.assertRaises(frappe.ValidationError, update_coupon_code_count, "_Test Coupon Count", "used")
