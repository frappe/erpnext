# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.utilities.product import get_price


class TestProductUtil(ERPNextTestSuite):
	"""Cover the ``get_price`` sales-UOM conversion query (UOM Conversion Detail join Item).

	The converted query in ``erpnext.utilities.product.get_price`` resolves the
	item's sales UOM conversion factor and scales ``formatted_price_sales_uom``
	by it. We seed a sales UOM whose conversion factor differs from 1 so the join
	produces an observable, non-trivial result.
	"""

	ITEM_CODE = "_Test Item"
	PRICE_LIST = "_Test Selling Price List"
	SALES_UOM = "_Test UOM 1"
	SALES_UOM_FACTOR = 10.0
	PRICE_LIST_RATE = 200.0

	def setUp(self):
		# _Test Item bootstrap ships uoms [_Test UOM (1.0), _Test UOM 1 (10.0)].
		# Point its sales_uom at the 10x conversion so the joined query returns a
		# factor != 1; assert against the bootstrapped conversion_factor to keep
		# the check tied to real seeded state rather than a literal.
		uom_cf = frappe.db.get_value(
			"UOM Conversion Detail",
			{"parent": self.ITEM_CODE, "parenttype": "Item", "uom": self.SALES_UOM},
			"conversion_factor",
		)
		self.assertEqual(
			flt(uom_cf),
			self.SALES_UOM_FACTOR,
			msg=f"Expected bootstrap UOM Conversion Detail {self.SALES_UOM} = {self.SALES_UOM_FACTOR}",
		)

		frappe.db.set_value("Item", self.ITEM_CODE, "sales_uom", self.SALES_UOM)

		if not frappe.db.exists("Item Price", {"item_code": self.ITEM_CODE, "price_list": self.PRICE_LIST}):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": self.ITEM_CODE,
					"price_list": self.PRICE_LIST,
					"price_list_rate": self.PRICE_LIST_RATE,
				}
			).insert()

	def test_sales_uom_conversion_factor_applied(self):
		price = get_price(
			item_code=self.ITEM_CODE,
			price_list=self.PRICE_LIST,
			customer_group="_Test Customer Group",
			company="_Test Company",
		)

		self.assertIsNotNone(price, msg="get_price returned no price for seeded Item Price")

		rate = flt(price["price_list_rate"])
		self.assertTrue(rate, msg="seeded Item Price did not resolve a price_list_rate")

		# The converted query (UOM Conversion Detail join Item on uom == sales_uom)
		# multiplies the rate by the sales-UOM conversion factor for this field.
		expected_sales_uom_price = frappe.utils.fmt_money(
			rate * self.SALES_UOM_FACTOR, currency=price["currency"]
		)
		self.assertEqual(
			price["formatted_price_sales_uom"],
			expected_sales_uom_price,
			msg="sales-UOM conversion factor (10x) was not applied by the converted join query",
		)

		# Guard against a degenerate factor of 1 silently passing: the sales-UOM
		# price must differ from the plain formatted price.
		self.assertNotEqual(
			price["formatted_price_sales_uom"],
			price["formatted_price"],
			msg="formatted_price_sales_uom equals formatted_price; conversion factor was not picked up",
		)

	def test_factor_defaults_to_one_without_matching_sales_uom(self):
		# When sales_uom has no matching UOM Conversion Detail row, the join
		# returns nothing and the factor falls back to 1 (price unchanged).
		frappe.db.set_value("Item", self.ITEM_CODE, "sales_uom", None)

		price = get_price(
			item_code=self.ITEM_CODE,
			price_list=self.PRICE_LIST,
			customer_group="_Test Customer Group",
			company="_Test Company",
		)

		self.assertIsNotNone(price)
		self.assertEqual(
			price["formatted_price_sales_uom"],
			price["formatted_price"],
			msg="factor should default to 1 when no UOM Conversion Detail matches sales_uom",
		)
