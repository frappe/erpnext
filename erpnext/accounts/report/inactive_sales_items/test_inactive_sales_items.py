from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.report.inactive_sales_items import inactive_sales_items as report


class TestInactiveSalesItems(FrappeTestCase):
	def _mk_filters(self, **kw):
		base = dict(
			based_on="Sales Invoice",
			days=30,
			territory=None,
			item_group=None,
			item=None,
		)
		base.update(kw)
		return frappe._dict(base)

	# def test_no_sales_data_includes_basic_row_TC_ACC_412(self):
	# 	filters = self._mk_filters()

	# 	report.get_items = lambda f: [SimpleNamespace(item_group="IG", item_code="ITEM-1", item_name="Item One")]
	# 	report.get_territories = lambda f: [SimpleNamespace(name="India")]
	# 	report.get_sales_details = lambda f: {}
	# 	data = report.execute(filters)
	# 	data = report.get_data(filters)
	# 	self.assertEqual(len(data), 1)
	# 	row = data[0]
	# 	self.assertEqual(row["territory"], "India")
	# 	self.assertEqual(row["item"], "ITEM-1")
	# 	self.assertNotIn("customer", row)

	# def test_skip_recent_order_TC_ACC_413(self):
	# 	filters = self._mk_filters(days=30)

	# 	report.get_items = lambda f: [SimpleNamespace(item_group="IG", item_code="ITEM-2", item_name="Item Two")]
	# 	report.get_territories = lambda f: [SimpleNamespace(name="USA")]

	# 	report.get_sales_details = lambda f: {
	# 		("USA", "ITEM-2"): SimpleNamespace(
	# 			territory="USA",
	# 			customer="CUST-001",
	# 			last_order_date="2025-08-01",
	# 			qty=10,
	# 			days_since_last_order=10,  # below threshold
	# 		)
	# 	}

	# 	data = report.get_data(filters)
	# 	self.assertEqual(len(data), 0)

	# def test_include_old_order_TC_ACC_414(self):
	# 	filters = self._mk_filters(days=30)

	# 	report.get_items = lambda f: [SimpleNamespace(item_group="IG", item_code="ITEM-3", item_name="Item Three")]
	# 	report.get_territories = lambda f: [SimpleNamespace(name="Canada")]

	# 	report.get_sales_details = lambda f: {
	# 		("Canada", "ITEM-3"): SimpleNamespace(
	# 			territory="Canada",
	# 			customer="CUST-002",
	# 			last_order_date="2025-05-01",
	# 			qty=7,
	# 			days_since_last_order=90,  # above threshold
	# 		)
	# 	}

	# data = report.get_data(filters)
	# self.assertEqual(len(data), 1)
	# row = data[0]
	# self.assertEqual(row["territory"], "Canada")
	# self.assertEqual(row["customer"], "CUST-002")
	# self.assertEqual(row["qty"], 7)
	# self.assertEqual(row["days_since_last_order"], 90)

	# def test_get_sales_details_invoice_TC_ACC_415(self):
	# 	filters = self._mk_filters(based_on="Sales Invoice")
	# 	fake_result = [
	# 		SimpleNamespace(
	# 			territory="India",
	# 			customer="CUST-003",
	# 			item_group="IG",
	# 			item_code="ITEM-4",
	# 			qty=2,
	# 			last_order_date="2025-07-01",
	# 			days_since_last_order=50,
	# 		)
	# 	]
	# 	frappe.db.sql = lambda *a, **k: fake_result
	# 	result = report.get_sales_details(filters)
	# 	self.assertIn(("India", "ITEM-4"), result)
	# 	self.assertEqual(result[("India", "ITEM-4")].customer, "CUST-003")

	# def test_get_sales_details_order_TC_ACC_416(self):
	# 	filters = self._mk_filters(based_on="Sales Order")
	# 	fake_result = [
	# 		SimpleNamespace(
	# 			territory="USA",
	# 			customer="CUST-004",
	# 			item_group="IG",
	# 			item_code="ITEM-5",
	# 			qty=3,
	# 			last_order_date="2025-06-15",
	# 			days_since_last_order=75,
	# 		)
	# 	]
	# 	frappe.db.sql = lambda *a, **k: fake_result
	# 	result = report.get_sales_details(filters)
	# 	self.assertIn(("USA", "ITEM-5"), result)
	# 	self.assertEqual(result[("USA", "ITEM-5")].customer, "CUST-004")

	# def test_get_territories_with_and_without_filter_TC_ACC_417(self):
	# 	filters = self._mk_filters(territory="India")
	# 	frappe.get_all = lambda doctype, fields, filters: [SimpleNamespace(name="India")]
	# 	result = report.get_territories(filters)
	# 	self.assertEqual(result[0].name, "India")

	# 	filters = self._mk_filters()
	# 	frappe.get_all = lambda doctype, fields, filters: [SimpleNamespace(name="USA")]
	# 	result = report.get_territories(filters)
	# 	self.assertEqual(result[0].name, "USA")

	# def test_get_items_with_and_without_filters_TC_ACC_418(self):
	# 	filters = self._mk_filters(item_group="Electronics", item="ITEM-10")
	# 	frappe.get_all = lambda doctype, fields, filters, order_by: [
	# 	SimpleNamespace(name="ITEM-10", item_group="Electronics", item_name="Phone", item_code="ITEM-10")
	# 	]
	# 	result = report.get_items(filters)
	# 	self.assertEqual(result[0].item_group, "Electronics")
	# 	self.assertEqual(result[0].item_code, "ITEM-10")

	# 	filters = self._mk_filters()
	# 	frappe.get_all = lambda doctype, fields, filters, order_by: [
	# 	SimpleNamespace(name="ITEM-20", item_group="Hardware", item_name="Hammer", item_code="ITEM-20")
	# 	]
	# 	result = report.get_items(filters)
	# 	self.assertEqual(result[0].item_group, "Hardware")
