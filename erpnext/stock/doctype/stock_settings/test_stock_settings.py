# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


from unittest.mock import patch

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestStockSettings(ERPNextTestSuite):
	def setUp(self):
		super().setUp()
		frappe.db.set_single_value("Stock Settings", "clean_description_html", 0)

	def test_settings(self):
		item = frappe.get_doc(
			doctype="Item",
			item_code="Item for description test",
			item_group="Products",
			description='<p><span style="font-size: 12px;">Drawing No. 07-xxx-PO132<br></span><span style="font-size: 12px;">1800 x 1685 x 750<br></span><span style="font-size: 12px;">All parts made of Marine Ply<br></span><span style="font-size: 12px;">Top w/ Corian dd<br></span><span style="font-size: 12px;">CO, CS, VIP Day Cabin</span></p>',
		).insert()

		settings = frappe.get_single("Stock Settings")
		settings.clean_description_html = 1
		settings.save()

		item.reload()

		self.assertEqual(
			item.description,
			"<p>Drawing No. 07-xxx-PO132<br>1800 x 1685 x 750<br>All parts made of Marine Ply<br>Top w/ Corian dd<br>CO, CS, VIP Day Cabin</p>",
		)

		item.delete()

	def test_clean_html(self):
		settings = frappe.get_single("Stock Settings")
		settings.clean_description_html = 1
		settings.save()

		item = frappe.get_doc(
			doctype="Item",
			item_code="Item for description test",
			item_group="Products",
			description='<p><span style="font-size: 12px;">Drawing No. 07-xxx-PO132<br></span><span style="font-size: 12px;">1800 x 1685 x 750<br></span><span style="font-size: 12px;">All parts made of Marine Ply<br></span><span style="font-size: 12px;">Top w/ Corian dd<br></span><span style="font-size: 12px;">CO, CS, VIP Day Cabin</span></p>',
		).insert()

		self.assertEqual(
			item.description,
			"<p>Drawing No. 07-xxx-PO132<br>1800 x 1685 x 750<br>All parts made of Marine Ply<br>Top w/ Corian dd<br>CO, CS, VIP Day Cabin</p>",
		)

		item.delete()

	def test_unrelated_change_does_not_update_item_metadata(self):
		settings = frappe.get_single("Stock Settings")
		settings.allow_partial_reservation = not settings.allow_partial_reservation

		with (
			patch("erpnext.utilities.naming.set_by_naming_series") as set_by_naming_series,
			patch("frappe.make_property_setter") as make_property_setter,
		):
			settings.save()

		set_by_naming_series.assert_not_called()
		make_property_setter.assert_not_called()

	def test_item_metadata_updates_when_related_settings_change(self):
		settings = frappe.get_single("Stock Settings")
		settings.item_naming_by = (
			"Item Code" if settings.item_naming_by == "Naming Series" else "Naming Series"
		)
		settings.show_barcode_field = not settings.show_barcode_field

		with (
			patch("erpnext.utilities.naming.set_by_naming_series") as set_by_naming_series,
			patch("frappe.make_property_setter") as make_property_setter,
		):
			settings.save()

		set_by_naming_series.assert_called_once()
		self.assertEqual(make_property_setter.call_count, 3)
