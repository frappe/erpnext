# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestSellingSettings(ERPNextTestSuite):
	def test_defaults_populated(self):
		# Setup default values are not populated on migrate, this test checks
		# if setup was completed correctly
		default = frappe.db.get_single_value("Selling Settings", "maintain_same_rate_action")
		self.assertEqual("Stop", default)

	def test_unrelated_change_does_not_update_customer_metadata(self):
		settings = frappe.get_single("Selling Settings")
		settings.allow_multiple_items = not settings.allow_multiple_items

		with patch("erpnext.utilities.naming.set_by_naming_series") as set_by_naming_series:
			settings.save()

		set_by_naming_series.assert_not_called()

	def test_customer_metadata_updates_when_related_settings_change(self):
		settings = frappe.get_single("Selling Settings")
		settings.cust_master_name = (
			"Customer Name" if settings.cust_master_name == "Naming Series" else "Naming Series"
		)

		with patch("erpnext.utilities.naming.set_by_naming_series") as set_by_naming_series:
			settings.save()

		set_by_naming_series.assert_called_once()

	def test_unrelated_change_does_not_rewrite_toggle_setters(self):
		settings = frappe.get_single("Selling Settings")
		settings.allow_multiple_items = not settings.allow_multiple_items

		with patch(
			"erpnext.selling.doctype.selling_settings.selling_settings.make_property_setter"
		) as make_property_setter:
			settings.save()

		make_property_setter.assert_not_called()

	def test_toggle_setters_rewritten_when_related_settings_change(self):
		settings = frappe.get_single("Selling Settings")
		settings.hide_tax_id = not settings.hide_tax_id
		settings.editable_bundle_item_rates = not settings.editable_bundle_item_rates
		settings.enable_discount_accounting = not settings.enable_discount_accounting

		with patch(
			"erpnext.selling.doctype.selling_settings.selling_settings.make_property_setter"
		) as make_property_setter:
			settings.save()

		self.assertEqual(make_property_setter.call_count, 11)
