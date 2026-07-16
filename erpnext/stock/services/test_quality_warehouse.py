# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

"""Shared warehouse helpers for the quality test suites."""

import frappe

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


class TestQualityWarehouseConfiguration(ERPNextTestSuite):
	def test_quality_warehouse_target_must_be_quality_type(self):
		ensure_quality_warehouse_type()
		plain_target = make_warehouse("_Test QW Plain Target")  # no warehouse type
		store = frappe.get_doc("Warehouse", make_warehouse("_Test QW Config Store"))

		# pointing at an untyped warehouse would route stock into an unlocked
		# destination and break submission downstream — refused at config time
		store.quality_warehouse = plain_target
		self.assertRaises(frappe.ValidationError, store.save)

		store.reload()
		store.quality_warehouse = make_warehouse("_Test QW Typed Target", warehouse_type="Quality")
		store.save()


class TestWarehouseLinkQuery(ERPNextTestSuite):
	"""The default Warehouse link query (standard_queries) hides Quality
	warehouses unless the caller filters on warehouse types itself."""

	def run_query(self, filters=None, txt=""):
		from erpnext.controllers.queries import warehouse_link_query

		rows = warehouse_link_query("Warehouse", txt, "name", 0, 20, filters)
		return {row[0] for row in rows}

	def test_default_pick_hides_quality_warehouses(self):
		ensure_quality_warehouse_type()
		qc = make_warehouse("_Test WLQ Quality", warehouse_type="Quality")
		plain = make_warehouse("_Test WLQ Plain")

		names = self.run_query(txt="_Test WLQ")
		self.assertIn(plain, names)
		self.assertNotIn(qc, names)

	def test_explicit_type_filter_offers_quality_warehouses(self):
		ensure_quality_warehouse_type()
		qc = make_warehouse("_Test WLQ Quality", warehouse_type="Quality")

		# the routing-target field, release dispatch and quality reports all
		# ask for the type explicitly — the default exclusion yields to them
		names = self.run_query(filters={"warehouse_type": "Quality"}, txt="_Test WLQ")
		self.assertIn(qc, names)

	def test_list_form_filters_are_understood(self):
		ensure_quality_warehouse_type()
		qc = make_warehouse("_Test WLQ Quality", warehouse_type="Quality")
		plain = make_warehouse("_Test WLQ Plain")

		# erpnext.queries.* builders send ["Warehouse", field, op, value] rows
		names = self.run_query(filters=[["Warehouse", "company", "=", "_Test Company"]], txt="_Test WLQ")
		self.assertIn(plain, names)
		self.assertNotIn(qc, names)

		names = self.run_query(filters=[["Warehouse", "warehouse_type", "=", "Quality"]], txt="_Test WLQ")
		self.assertIn(qc, names)

	def test_not_in_type_filter_keeps_untyped_warehouses(self):
		ensure_quality_warehouse_type()
		qc = make_warehouse("_Test WLQ Quality", warehouse_type="Quality")
		plain = make_warehouse("_Test WLQ Plain")  # warehouse_type is NULL

		# the shared inbound picker sends this exact shape; NOT IN must not
		# swallow untyped warehouses through SQL NULL semantics
		names = self.run_query(
			filters=[["Warehouse", "warehouse_type", "not in", ["Quality", "Rejected"]]],
			txt="_Test WLQ",
		)
		self.assertIn(plain, names)
		self.assertNotIn(qc, names)

	def test_dict_operator_form_is_understood(self):
		ensure_quality_warehouse_type()
		qc = make_warehouse("_Test WLQ Quality", warehouse_type="Quality")
		plain = make_warehouse("_Test WLQ Plain")

		# the Quality Control Release target picker sends {"warehouse_type": ["!=", "Quality"]}
		names = self.run_query(filters={"warehouse_type": ["!=", "Quality"]}, txt="_Test WLQ")
		self.assertIn(plain, names)
		self.assertNotIn(qc, names)

	def test_in_filter_with_empty_matches_untyped_warehouses(self):
		ensure_quality_warehouse_type()
		if not frappe.db.exists("Warehouse Type", "Rejected"):
			frappe.get_doc({"doctype": "Warehouse Type", "name": "Rejected"}).insert(ignore_permissions=True)
		qc = make_warehouse("_Test WLQ Quality", warehouse_type="Quality")
		rejected = make_warehouse("_Test WLQ Rejected", warehouse_type="Rejected")
		plain = make_warehouse("_Test WLQ Plain")  # warehouse_type is NULL

		# the rejected_warehouse picker sends in ["Rejected", ""]: the empty
		# member must match untyped (NULL) warehouses through the IfNull wrap
		names = self.run_query(
			filters=[["Warehouse", "warehouse_type", "in", ["Rejected", ""]]], txt="_Test WLQ"
		)
		self.assertIn(rejected, names)
		self.assertIn(plain, names)
		self.assertNotIn(qc, names)
