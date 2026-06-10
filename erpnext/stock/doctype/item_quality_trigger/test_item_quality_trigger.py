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

	def test_party_transaction_type_only_on_party_documents(self):
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
		self.assertRaises(frappe.ValidationError, item.save)

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

	def test_job_card_inspection_point_only_on_job_card(self):
		item = make_item(properties={"is_stock_item": 1})
		# Purchase Receipt row carrying a Job Card-only option must be rejected
		item.append("quality_triggers", trigger_row(job_card_inspection_point="Every Job Card"))
		self.assertRaises(frappe.ValidationError, item.save)
