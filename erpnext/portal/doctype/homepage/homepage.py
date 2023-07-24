# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.website.utils import delete_page_cache


class Homepage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.portal.doctype.homepage_featured_product.homepage_featured_product import (
			HomepageFeaturedProduct,
		)

		company: DF.Link
		description: DF.Text
		hero_image: DF.AttachImage | None
		hero_section: DF.Link | None
		hero_section_based_on: DF.Literal["Default", "Slideshow", "Homepage Section"]
		products: DF.Table[HomepageFeaturedProduct]
		products_url: DF.Data | None
		slideshow: DF.Link | None
		tag_line: DF.Data
		title: DF.Data | None
	# end: auto-generated types
	def validate(self):
		if not self.description:
			self.description = frappe._("This is an example website auto-generated from ERPNext")
		delete_page_cache("home")

	def setup_items(self):
		for d in frappe.get_all(
			"Website Item",
			fields=["name", "item_name", "description", "website_image", "route"],
			filters={"published": 1},
			limit=3,
		):

			doc = frappe.get_doc("Website Item", d.name)
			if not doc.route:
				# set missing route
				doc.save()
			self.append(
				"products",
				dict(
					item_code=d.name,
					item_name=d.item_name,
					description=d.description,
					image=d.website_image,
					route=d.route,
				),
			)
