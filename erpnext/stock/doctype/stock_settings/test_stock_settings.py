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

	def test_cannot_disable_serial_and_batch_with_tracked_items(self):
		from erpnext.stock.doctype.item.test_item import make_item

		make_item("_Test Serial Deactivation Item", {"has_serial_no": 1})

		settings = frappe.get_single("Stock Settings")
		settings.enable_serial_and_batch_no_for_item = 0

		exists = frappe.db.exists

		def exists_without_bundles(doctype, *args, **kwargs):
			# test data has submitted bundles, which would throw before the item check
			return doctype != "Serial and Batch Bundle" and exists(doctype, *args, **kwargs)

		with (
			patch.object(frappe.db, "exists", side_effect=exists_without_bundles),
			self.assertRaisesRegex(frappe.ValidationError, "items with serial / batch enabled"),
		):
			settings.save()
