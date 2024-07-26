# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase


class TestStockSettings(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.db.set_single_value("Stock Settings", "clean_description_html", 0)

	def test_settings(self):
		item = frappe.get_doc(
			dict(
				doctype="Item",
				item_code="Item for description test",
				item_group="Products",
				description='<p><span style="font-size: 12px;">Drawing No. 07-xxx-PO132<br></span><span style="font-size: 12px;">1800 x 1685 x 750<br></span><span style="font-size: 12px;">All parts made of Marine Ply<br></span><span style="font-size: 12px;">Top w/ Corian dd<br></span><span style="font-size: 12px;">CO, CS, VIP Day Cabin</span></p>',
			)
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
			dict(
				doctype="Item",
				item_code="Item for description test",
				item_group="Products",
				description='<p><span style="font-size: 12px;">Drawing No. 07-xxx-PO132<br></span><span style="font-size: 12px;">1800 x 1685 x 750<br></span><span style="font-size: 12px;">All parts made of Marine Ply<br></span><span style="font-size: 12px;">Top w/ Corian dd<br></span><span style="font-size: 12px;">CO, CS, VIP Day Cabin</span></p>',
			)
		).insert()

		self.assertEqual(
			item.description,
			"<p>Drawing No. 07-xxx-PO132<br>1800 x 1685 x 750<br>All parts made of Marine Ply<br>Top w/ Corian dd<br>CO, CS, VIP Day Cabin</p>",
		)

		item.delete()
