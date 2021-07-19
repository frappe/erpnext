# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.e_commerce.doctype.website_item.website_item import make_website_item

class TestWebsiteItem(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		make_item("Test Web Item", {
			"has_variant": 1,
			"variant_based_on": "Item Attribute",
			"attributes": [
				{
					"attribute": "Test Size"
				}
			]
		})

	def test_index_creation(self):
		"Check if index is getting created in db."
		from erpnext.e_commerce.doctype.website_item.website_item import on_doctype_update
		on_doctype_update()

		indices = frappe.db.sql("show index from `tabWebsite Item`", as_dict=1)
		expected_columns = {"route", "item_group", "brand"}
		for index in indices:
			expected_columns.discard(index.get("Column_name"))

		if expected_columns:
			self.fail(f"Expected db index on these columns: {', '.join(expected_columns)}")

	def test_website_item_desk_item_sync(self):
		"Check creation/updation/deletion of Website Item and its impact on Item master."
		web_item = None
		item = make_item("Test Web Item")
		try:
			web_item = make_website_item(item, save=False)
			web_item.save()
		except Exception:
			self.fail(f"Error while creating website item for {item.item_code}")

		# check if website item was created
		self.assertTrue(bool(web_item))

		item.reload()
		# check if item was back updated
		self.assertEqual(web_item.published, 1)
		self.assertEqual(item.published_in_website, 1)
		self.assertEqual(web_item.item_group, item.item_group)

		# check if disabling item unpublished website item
		item.disabled = 1
		item.save()
		web_item.reload()
		self.assertEqual(web_item.published, 0)

		# check if website item deletion, unpublishes desk item
		web_item.delete()
		item.reload()
		self.assertEqual(item.published_in_website, 0)

		# tear down
		item.delete()