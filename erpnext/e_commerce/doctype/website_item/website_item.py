# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.website.doctype.website_slideshow.website_slideshow import \
	get_slideshow

from frappe.website.render import clear_cache
from frappe.website.website_generator import WebsiteGenerator

from frappe.utils import cstr, random_string

class WebsiteItem(WebsiteGenerator):
	website = frappe._dict(
		page_title_field="web_item_name",
		condition_field="published",
		template="templates/generators/item/item.html",
		no_cache=1
	)

	def onload(self):
		super(WebsiteItem, self).onload()

	def validate(self):
		super(WebsiteItem, self).validate()

		if not self.item_code:
			frappe.throw(_("Item Code is required"), title=_("Mandatory"))

		self.validate_website_image()
		self.make_thumbnail()
		self.publish_unpublish_desk_item(publish=True)

	def on_trash(self):
		self.publish_unpublish_desk_item(publish=False)

	def publish_unpublish_desk_item(self, publish=True):
		if frappe.db.get_value("Item", self.item_code, "published_in_website") and publish:
			return # if already published don't publish again
		frappe.db.set_value("Item", self.item_code, "published_in_website", publish)

	def make_route(self):
		"""Called from set_route in WebsiteGenerator."""
		if not self.route:
			return cstr(frappe.db.get_value('Item Group', self.item_group,
					'route')) + '/' + self.scrub((self.item_name if self.item_name else self.item_code) + '-' + random_string(5))

	def validate_website_image(self):
		if frappe.flags.in_import:
			return

		"""Validate if the website image is a public file"""
		auto_set_website_image = False
		if not self.website_image and self.image:
			auto_set_website_image = True
			self.website_image = self.image

		if not self.website_image:
			return

		# find if website image url exists as public
		file_doc = frappe.get_all("File", filters={
			"file_url": self.website_image
		}, fields=["name", "is_private"], order_by="is_private asc", limit_page_length=1)

		if file_doc:
			file_doc = file_doc[0]

		if not file_doc:
			if not auto_set_website_image:
				frappe.msgprint(_("Website Image {0} attached to Item {1} cannot be found").format(self.website_image, self.name))

			self.website_image = None

		elif file_doc.is_private:
			if not auto_set_website_image:
				frappe.msgprint(_("Website Image should be a public file or website URL"))

			self.website_image = None

	def make_thumbnail(self):
		if frappe.flags.in_import:
			return

		"""Make a thumbnail of `website_image`"""
		import requests.exceptions

		if not self.is_new() and self.website_image != frappe.db.get_value(self.doctype, self.name, "website_image"):
			self.thumbnail = None

		if self.website_image and not self.thumbnail:
			file_doc = None

			try:
				file_doc = frappe.get_doc("File", {
					"file_url": self.website_image,
					"attached_to_doctype": "Item",
					"attached_to_name": self.name
				})
			except frappe.DoesNotExistError:
				pass
				# cleanup
				frappe.local.message_log.pop()

			except requests.exceptions.HTTPError:
				frappe.msgprint(_("Warning: Invalid attachment {0}").format(self.website_image))
				self.website_image = None

			except requests.exceptions.SSLError:
				frappe.msgprint(
					_("Warning: Invalid SSL certificate on attachment {0}").format(self.website_image))
				self.website_image = None

			# for CSV import
			if self.website_image and not file_doc:
				try:
					file_doc = frappe.get_doc({
						"doctype": "File",
						"file_url": self.website_image,
						"attached_to_doctype": "Item",
						"attached_to_name": self.name
					}).save()

				except IOError:
					self.website_image = None

			if file_doc:
				if not file_doc.thumbnail_url:
					file_doc.make_thumbnail()

				self.thumbnail = file_doc.thumbnail_url

@frappe.whitelist()
def make_website_item(doc):
	if not doc:
		return
	doc = json.loads(doc)

	if frappe.db.exists("Website Item", {"item_code": doc.get("item_code")}):
		message = _("Website Item already exists against {0}").format(frappe.bold(doc.get("item_code")))
		frappe.throw(message, title=_("Already Published"), indicator="blue")

	website_item = frappe.new_doc("Website Item")
	website_item.web_item_name = doc.get("item_name")

	fields_to_map = ["item_code", "item_name", "item_group", "stock_uom", "brand", "image",
		"has_variants", "variant_of"]
	for field in fields_to_map:
		website_item.update({field: doc.get(field)})

	website_item.save()
	return [website_item.name, website_item.web_item_name]
