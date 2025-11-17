import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.report.item_price_stock import item_price_stock
from erpnext.stock.utils import get_or_create_fiscal_year


class TestItemPriceReport(FrappeTestCase):
	def setUp(self):
		self.buying_pl = get_or_create_price_list("Test Buying PL", buying=1, selling=0)
		self.selling_pl = get_or_create_price_list("Test Selling PL", buying=0, selling=1)
		self.company = create_company("_Test Company")
		self.warehouse = create_warehouse(warehouse_name="Stores - W - _TC", company="_Test Company")
		self.item = create_item(
			item_code="TEST-ITEM-100",
			valuation_rate=100,
			warehouse="Stores - W - _TC",
			company="_Test Company",
		)

		self.buying_price = get_or_create_item_price(
			item_code=self.item, price_list=self.buying_pl.name, price_list_rate=50, buying=1, selling=0
		)

		self.selling_price = get_or_create_item_price(
			item_code=self.item, price_list=self.selling_pl.name, price_list_rate=80, buying=0, selling=1
		)

		get_or_create_fiscal_year("_Test Company")

		self.stock_entry_name = create_stock_entry(
			item_code=self.item, warehouse="Stores - W - _TC", qty=15, company="_Test Company"
		)

	def tearDown(self):
		frappe.delete_doc("Item Price", self.buying_price.name, force=1)
		frappe.delete_doc("Item Price", self.selling_price.name, force=1)
		frappe.delete_doc("Item", self.item.name, force=1)
		frappe.delete_doc("Price List", self.buying_pl.name, force=1)
		frappe.delete_doc("Price List", self.selling_pl.name, force=1)

	def test_item_price_stock_execute_TC_SCK_510(self):
		filters = {"item_code": self.item.name}
		columns, data = item_price_stock.execute(filters)

		# Test 1: Columns structure
		self.assertIsInstance(columns, list)
		self.assertTrue(any(col["fieldname"] == "item_code" for col in columns))

		# Test 2 and 3: Price map values (Buying and Selling)
		buying_col = next((col for col in columns if "Buying Rate" in col.get("label", "")), None)
		selling_col = next((col for col in columns if "Selling Rate" in col.get("label", "")), None)
		self.assertIsNotNone(buying_col)
		self.assertIsNotNone(selling_col)
		rates = [row for row in data if row.get("item_code") == self.item.name]
		self.assertTrue(any(row.get("buying_rate", row.get("Buying Rate", 0)) == 50 for row in rates))
		self.assertTrue(any(row.get("selling_rate", row.get("Selling Rate", 0)) == 80 for row in rates))

		# Test 4: Data contains correct item_code
		self.assertTrue(any(row["item_code"] == self.item.name for row in data))

		# Test 5: Data length (should be 2: one for buying, one for selling)
		self.assertEqual(len(data), 2)


def get_or_create_price_list(price_list_name, buying=0, selling=0):
	if frappe.db.exists("Price List", price_list_name):
		return frappe.get_doc("Price List", price_list_name)
	return frappe.get_doc(
		{"doctype": "Price List", "price_list_name": price_list_name, "buying": buying, "selling": selling}
	).insert(ignore_permissions=True)


def get_or_create_item(item_code):
	brand = "TestBrand"
	hsn_code = "10010010"

	if not frappe.db.exists("GST HSN Code", hsn_code):
		frappe.get_doc(
			{"doctype": "GST HSN Code", "hsn_code": hsn_code, "description": "Test HSN Code for automation"}
		).insert()

	if not frappe.db.exists("Brand", brand):
		frappe.get_doc({"doctype": "Brand", "brand": brand}).insert()

	if frappe.db.exists("Item", item_code):
		return frappe.get_doc("Item", item_code)
	return frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": f"Test Item {item_code}",
			"brand": "TestBrand",
			"is_stock_item": 1,
			"item_group": "All Item Groups",
			"stock_uom": "Nos",
			"gst_hsn_code": hsn_code,
		}
	).insert(ignore_permissions=True)


def get_or_create_item_price(item_code, price_list, price_list_rate, buying=0, selling=0):
	filters = {
		"item_code": item_code,
		"price_list": price_list,
		"buying": buying,
		"selling": selling,
	}
	existing = frappe.get_all("Item Price", filters=filters, limit=1)
	if existing:
		ip = frappe.get_doc("Item Price", existing[0].name)
		if ip.price_list_rate != price_list_rate:
			ip.price_list_rate = price_list_rate
			ip.save(ignore_permissions=True)
		return ip
	else:
		ip = frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": item_code,
				"price_list": price_list,
				"price_list_rate": price_list_rate,
				"buying": buying,
				"selling": selling,
			}
		).insert(ignore_permissions=True)
		return ip


def create_stock_entry(item_code, warehouse, qty, company):
	se = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": company,
			"items": [
				{"item_code": item_code, "qty": qty, "uom": "Nos", "t_warehouse": warehouse, "rate": 100}
			],
		}
	)
	se.insert(ignore_permissions=True)
	se.submit()
	return se.name
