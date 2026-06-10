# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.item_quality_trigger.item_quality_trigger import allowed_warehouse_roles
from erpnext.tests.utils import ERPNextTestSuite

TEST_TEMPLATE = "_Test QC Trigger Template"


def create_test_template(name=TEST_TEMPLATE):
	if not frappe.db.exists("Quality Inspection Template", name):
		doc = frappe.get_doc(
			{
				"doctype": "Quality Inspection Template",
				"quality_inspection_template_name": name,
			}
		)
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
	return name


def create_test_item_group(name="_Test QC Item Group", is_group=0):
	if not frappe.db.exists("Item Group", name):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": name,
				"parent_item_group": "All Item Groups",
				"is_group": is_group,
			}
		).insert(ignore_permissions=True)
	return name


def trigger_row(**overrides):
	row = {
		"document_type": "Purchase Receipt",
		"warehouse_role": "Inbound",
		"quality_control_mode": "Quarantine",
		"inspection_template": create_test_template(),
		"inspection_basis": "Sample",
	}
	row.update(overrides)
	return row


class TestItemQualityTrigger(ERPNextTestSuite):
	def test_allowed_warehouse_roles_matrix(self):
		self.assertEqual(allowed_warehouse_roles("Purchase Receipt"), {"Inbound"})
		# Outbound inspects the delivery, Inbound inspects the customer return
		self.assertEqual(allowed_warehouse_roles("Delivery Note"), {"Inbound", "Outbound"})
		self.assertEqual(allowed_warehouse_roles("Stock Entry", "Material Receipt"), {"Inbound"})
		self.assertEqual(allowed_warehouse_roles("Stock Entry", "Material Issue"), {"Outbound"})
		self.assertEqual(allowed_warehouse_roles("Stock Entry", "Material Transfer"), {"Inbound", "Outbound"})
		self.assertEqual(allowed_warehouse_roles("Job Card"), {"Inbound"})

	def test_single_direction_role_is_autoset(self):
		item = make_item(properties={"is_stock_item": 1})
		item.append("quality_triggers", trigger_row(warehouse_role=None))  # Purchase Receipt
		item.save()
		self.assertEqual(item.quality_triggers[0].warehouse_role, "Inbound")

	def test_invalid_direction_is_rejected(self):
		item = make_item(properties={"is_stock_item": 1})
		# Purchase Receipt is inbound-only; Outbound must be rejected
		item.append("quality_triggers", trigger_row(warehouse_role="Outbound"))
		self.assertRaises(frappe.ValidationError, item.save)

	def test_party_transaction_type_cleared_on_non_party_documents(self):
		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				stock_entry_type="Material Receipt",
				warehouse_role=None,
				party_transaction_type="Internal Transfer",
			),
		)
		# the field defaults to External on every row, so non-party document
		# types silently clear it instead of rejecting the row
		item.save()
		self.assertFalse(item.quality_triggers[0].party_transaction_type)

	def test_quality_control_release_cannot_be_a_trigger(self):
		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				stock_entry_type="Quality Control Release",
				warehouse_role="Inbound",
				quality_control_mode="Block",
			),
		)
		self.assertRaises(frappe.ValidationError, item.save)

	def test_template_optional_except_for_each_quantity(self):
		# a sample trigger without a template is a verdict-style inspection
		item = make_item(properties={"is_stock_item": 1})
		item.append("quality_triggers", trigger_row(inspection_template=None))
		item.save()

		# Each Quantity generates per-unit readings from the template — required
		other = make_item(properties={"is_stock_item": 1})
		other.append(
			"quality_triggers",
			trigger_row(inspection_template=None, inspection_basis="Each Quantity"),
		)
		self.assertRaises(frappe.ValidationError, other.save)

	def test_overlapping_triggers_are_rejected(self):
		item = make_item(properties={"is_stock_item": 1})
		# two Purchase Receipt rows that can match the same receipt — whichever
		# sat first would silently win (e.g. Sample over Each Quantity)
		item.append("quality_triggers", trigger_row(inspection_basis="Sample"))
		item.append("quality_triggers", trigger_row(inspection_basis="Each Quantity"))
		self.assertRaises(frappe.ValidationError, item.save)

		# rows scoped to different warehouses cannot match the same movement
		item.reload()
		item.append("quality_triggers", trigger_row(applicable_warehouse="_Test Warehouse - _TC"))
		item.append("quality_triggers", trigger_row(applicable_warehouse="_Test Warehouse 1 - _TC"))
		item.save()

	def test_quarantine_rejected_on_outbound_rows(self):
		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Delivery Note",
				warehouse_role="Outbound",
				quality_control_mode="Quarantine",
			),
		)
		self.assertRaises(frappe.ValidationError, item.save)

	def test_periodic_retest_row_needs_interval_and_forces_quarantine(self):
		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				trigger_type="Periodic Re-test",
				document_type=None,
				warehouse_role=None,
				quality_control_mode=None,
			),
		)
		# missing interval is rejected
		self.assertRaises(frappe.ValidationError, item.save)

		item.reload()
		item.append(
			"quality_triggers",
			trigger_row(
				trigger_type="Periodic Re-test",
				document_type=None,
				warehouse_role=None,
				quality_control_mode=None,
				retest_interval_days=90,
			),
		)
		item.save()
		self.assertEqual(item.quality_triggers[0].quality_control_mode, "Quarantine")

	def test_job_card_cannot_quarantine(self):
		item = make_item(properties={"is_stock_item": 1})
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Job Card",
				warehouse_role=None,
				quality_control_mode="Quarantine",
				job_card_inspection_point="Every Job Card",
			),
		)
		self.assertRaises(frappe.ValidationError, item.save)

	def test_job_card_inspection_point_only_on_job_card(self):
		item = make_item(properties={"is_stock_item": 1})
		# Purchase Receipt row carrying a Job Card-only option must be rejected
		item.append("quality_triggers", trigger_row(job_card_inspection_point="Every Job Card"))
		self.assertRaises(frappe.ValidationError, item.save)
