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
		"qc_mode": "Quarantine",
		"inspection_template": create_test_template(),
		"inspection_basis": "Sample",
	}
	row.update(overrides)
	return row


class TestItemQualityTrigger(ERPNextTestSuite):
	def test_item_holds_quality_triggers(self):
		item = make_item(properties={"is_stock_item": 1})
		item.append("quality_triggers", trigger_row())
		item.save()

		reloaded = frappe.get_doc("Item", item.name)
		self.assertEqual(len(reloaded.quality_triggers), 1)

		trigger = reloaded.quality_triggers[0]
		self.assertEqual(trigger.document_type, "Purchase Receipt")
		self.assertEqual(trigger.warehouse_role, "Inbound")
		self.assertEqual(trigger.qc_mode, "Quarantine")
		self.assertEqual(trigger.inspection_template, TEST_TEMPLATE)
		self.assertEqual(trigger.inspection_basis, "Sample")

	def test_item_supports_multiple_triggers(self):
		item = make_item(properties={"is_stock_item": 1})
		item.append("quality_triggers", trigger_row())
		item.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				transaction_sub_type="Material Transfer",
				warehouse_role="Outbound",
				qc_mode="Block",
			),
		)
		item.save()

		reloaded = frappe.get_doc("Item", item.name)
		self.assertEqual(len(reloaded.quality_triggers), 2)
		sub_types = {t.transaction_sub_type for t in reloaded.quality_triggers}
		self.assertIn("Material Transfer", sub_types)

	def test_item_group_holds_quality_triggers(self):
		group_name = create_test_item_group(is_group=1)
		group = frappe.get_doc("Item Group", group_name)
		group.set("quality_triggers", [])
		group.append(
			"quality_triggers",
			trigger_row(
				document_type="Stock Entry",
				transaction_sub_type="Material Transfer",
				warehouse_role="Outbound",
				qc_mode="Block",
			),
		)
		group.save()

		reloaded = frappe.get_doc("Item Group", group_name)
		self.assertTrue(any(t.document_type == "Stock Entry" for t in reloaded.quality_triggers))

	def test_legacy_item_qc_fields_removed(self):
		meta = frappe.get_meta("Item")
		self.assertIsNone(meta.get_field("inspection_required_before_purchase"))
		self.assertIsNone(meta.get_field("inspection_required_before_delivery"))
		self.assertIsNone(meta.get_field("quality_inspection_template"))
		self.assertIsNotNone(meta.get_field("quality_triggers"))

	def test_document_type_scoped_to_supported_doctypes(self):
		options = frappe.get_meta("Item Quality Trigger").get_field("document_type").options.split("\n")
		for doctype in (
			"Stock Entry",
			"Purchase Receipt",
			"Delivery Note",
			"Subcontracting Receipt",
			"Sales Invoice",
			"Purchase Invoice",
			"Job Card",
		):
			self.assertIn(doctype, options)

	def test_stock_settings_quality_fields_removed(self):
		meta = frappe.get_meta("Stock Settings")
		self.assertIsNone(meta.get_field("allow_to_make_quality_inspection_after_purchase_or_delivery"))
		self.assertIsNone(meta.get_field("action_if_quality_inspection_is_rejected"))
		self.assertIsNone(meta.get_field("action_if_quality_inspection_is_not_submitted"))

	def test_allowed_warehouse_roles_matrix(self):
		self.assertEqual(allowed_warehouse_roles("Purchase Receipt"), {"Inbound"})
		self.assertEqual(allowed_warehouse_roles("Delivery Note"), {"Outbound"})
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
				transaction_sub_type="Material Receipt",
				warehouse_role=None,
				party_transaction_type="Internal Transfer",
			),
		)
		self.assertRaises(frappe.ValidationError, item.save)

	def test_job_card_inspection_point_only_on_job_card(self):
		item = make_item(properties={"is_stock_item": 1})
		# Purchase Receipt row carrying a Job Card-only option must be rejected
		item.append("quality_triggers", trigger_row(job_card_inspection_point="Every Job Card"))
		self.assertRaises(frappe.ValidationError, item.save)
