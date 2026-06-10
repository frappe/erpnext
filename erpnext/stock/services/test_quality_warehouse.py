# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.stock.services.quality_warehouse import get_quality_warehouse, is_quality_warehouse
from erpnext.tests.utils import ERPNextTestSuite


def ensure_quality_warehouse_type():
	if not frappe.db.exists("Warehouse Type", "Quality"):
		frappe.get_doc({"doctype": "Warehouse Type", "name": "Quality"}).insert(ignore_permissions=True)


def make_warehouse(name, warehouse_type=None, quality_warehouse=None):
	full = f"{name} - _TC"
	if not frappe.db.exists("Warehouse", full):
		frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": name,
				"company": "_Test Company",
				"warehouse_type": warehouse_type,
				"quality_warehouse": quality_warehouse,
			}
		).insert(ignore_permissions=True)
	return full


class TestQualityWarehouse(ERPNextTestSuite):
	def test_quality_warehouse_helpers(self):
		ensure_quality_warehouse_type()
		qc = make_warehouse("_Test QC Hold", warehouse_type="Quality")
		store = make_warehouse("_Test QC Store", quality_warehouse=qc)

		self.assertTrue(is_quality_warehouse(qc))
		self.assertFalse(is_quality_warehouse(store))
		self.assertFalse(is_quality_warehouse(None))

		self.assertEqual(get_quality_warehouse(store), qc)
		self.assertIsNone(get_quality_warehouse(qc))
