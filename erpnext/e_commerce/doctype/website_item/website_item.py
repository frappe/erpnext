# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
import itertools
from six import string_types
from frappe import _

from frappe.website.website_generator import WebsiteGenerator
from frappe.utils import cstr, random_string, cint, flt
from frappe.website.doctype.website_slideshow.website_slideshow import get_slideshow

from erpnext.setup.doctype.item_group.item_group import (get_parent_item_groups, invalidate_cache_for)

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

		self.validate_duplicate_website_item()
		self.validate_website_image()
		self.make_thumbnail()
		self.publish_unpublish_desk_item(publish=True)

		if not self.get("__islocal"):
			self.old_website_item_groups = frappe.db.sql_list("""select item_group
					from `tabWebsite Item Group`
					where parentfield='website_item_groups' and parenttype='Item' and parent=%s""", self.name)

	def on_update(self):
		invalidate_cache_for_web_item(self)
		self.update_template_item()

	def on_trash(self):
		self.publish_unpublish_desk_item(publish=False)

	def validate_duplicate_website_item(self):
		existing_web_item = frappe.db.exists("Website Item", {"item_code": self.item_code})
		if existing_web_item and existing_web_item != self.name:
			message = _("Website Item already exists against Item {0}").format(frappe.bold(self.item_code))
			frappe.throw(message, title=_("Already Published"))

	def publish_unpublish_desk_item(self, publish=True):
		if frappe.db.get_value("Item", self.item_code, "published_in_website") and publish:
			return # if already published don't publish again
		frappe.db.set_value("Item", self.item_code, "published_in_website", publish)

	def make_route(self):
		"""Called from set_route in WebsiteGenerator."""
		if not self.route:
			return cstr(frappe.db.get_value('Item Group', self.item_group,
					'route')) + '/' + self.scrub((self.item_name if self.item_name else self.item_code) + '-' + random_string(5))

	def update_template_item(self):
		"""Set Show in Website for Template Item if True for its Variant"""
		if self.variant_of:
			if self.published:
				# show template
				template_item = frappe.get_doc("Item", self.variant_of)

				if not template_item.published_in_website:
					template_item.flags.ignore_permissions = True
					make_website_item(template_item)

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

	def get_context(self, context):
		context.show_search = True
		context.search_link = '/search'

		context.parents = get_parent_item_groups(self.item_group, from_item=True)
		self.attributes = frappe.get_all("Item Variant Attribute",
					  fields=["attribute", "attribute_value"],
					  filters={"parent": self.item_code})
		self.set_variant_context(context)
		self.set_attribute_context(context)
		self.set_disabled_attributes(context)
		self.set_metatags(context)
		self.set_shopping_cart_data(context)
		self.get_product_details_section(context)

		context.wished = False
		if frappe.db.exists("Wishlist Items", {"item_code": self.item_code, "parent": frappe.session.user}):
				context.wished = True

		return context

	def set_variant_context(self, context):
		if self.has_variants:
			context.no_cache = True

			# load variants
			# also used in set_attribute_context
			context.variants = frappe.get_all("Item",
				 filters={"variant_of": self.name, "show_variant_in_website": 1},
				 order_by="name asc")

			variant = frappe.form_dict.variant
			if not variant and context.variants:
				# the case when the item is opened for the first time from its list
				variant = context.variants[0]

			if variant:
				context.variant = frappe.get_doc("Item", variant)

				for fieldname in ("website_image", "website_image_alt", "web_long_description", "description",
										"website_specifications"):
					if context.variant.get(fieldname):
						value = context.variant.get(fieldname)
						if isinstance(value, list):
							value = [d.as_dict() for d in value]

						context[fieldname] = value

		if self.slideshow:
			if context.variant and context.variant.slideshow:
				context.update(get_slideshow(context.variant))
			else:
				context.update(get_slideshow(self))

	def set_attribute_context(self, context):
		if self.has_variants:
			attribute_values_available = {}
			context.attribute_values = {}
			context.selected_attributes = {}

			# load attributes
			for v in context.variants:
				v.attributes = frappe.get_all("Item Variant Attribute",
					  fields=["attribute", "attribute_value"],
					  filters={"parent": v.name})
				# make a map for easier access in templates
				v.attribute_map = frappe._dict({})
				for attr in v.attributes:
					v.attribute_map[attr.attribute] = attr.attribute_value

				for attr in v.attributes:
					values = attribute_values_available.setdefault(attr.attribute, [])
					if attr.attribute_value not in values:
						values.append(attr.attribute_value)

					if v.name == context.variant.name:
						context.selected_attributes[attr.attribute] = attr.attribute_value

			# filter attributes, order based on attribute table
			for attr in self.attributes:
				values = context.attribute_values.setdefault(attr.attribute, [])

				if cint(frappe.db.get_value("Item Attribute", attr.attribute, "numeric_values")):
					for val in sorted(attribute_values_available.get(attr.attribute, []), key=flt):
						values.append(val)

				else:
					# get list of values defined (for sequence)
					for attr_value in frappe.db.get_all("Item Attribute Value",
						fields=["attribute_value"],
						filters={"parent": attr.attribute}, order_by="idx asc"):

						if attr_value.attribute_value in attribute_values_available.get(attr.attribute, []):
							values.append(attr_value.attribute_value)

			context.variant_info = json.dumps(context.variants)

	def set_disabled_attributes(self, context):
		"""Disable selection options of attribute combinations that do not result in a variant"""

		if not self.attributes or not self.has_variants:
			return

		context.disabled_attributes = {}
		attributes = [attr.attribute for attr in self.attributes]

		def find_variant(combination):
			for variant in context.variants:
				if len(variant.attributes) < len(attributes):
					continue

				if "combination" not in variant:
					ref_combination = []

					for attr in variant.attributes:
						idx = attributes.index(attr.attribute)
						ref_combination.insert(idx, attr.attribute_value)

					variant["combination"] = ref_combination

				if not (set(combination) - set(variant["combination"])):
					# check if the combination is a subset of a variant combination
					# eg. [Blue, 0.5] is a possible combination if exists [Blue, Large, 0.5]
					return True

		for i, attr in enumerate(self.attributes):
			if i == 0:
				continue

			combination_source = []

			# loop through previous attributes
			for prev_attr in self.attributes[:i]:
				combination_source.append([context.selected_attributes.get(prev_attr.attribute)])

			combination_source.append(context.attribute_values[attr.attribute])

			for combination in itertools.product(*combination_source):
				if not find_variant(combination):
					context.disabled_attributes.setdefault(attr.attribute, []).append(combination[-1])

	def set_metatags(self, context):
		context.metatags = frappe._dict({})

		safe_description = frappe.utils.to_markdown(self.description)

		context.metatags.url = frappe.utils.get_url() + '/' + context.route

		if context.website_image:
			if context.website_image.startswith('http'):
				url = context.website_image
			else:
				url = frappe.utils.get_url() + context.website_image
			context.metatags.image = url

		context.metatags.description = safe_description[:300]

		context.metatags.title = self.item_name or self.item_code

		context.metatags['og:type'] = 'product'
		context.metatags['og:site_name'] = 'ERPNext'

	def set_shopping_cart_data(self, context):
		from erpnext.e_commerce.shopping_cart.product_info import get_product_info_for_website
		context.shopping_cart = get_product_info_for_website(self.item_code, skip_quotation_creation=True)

	def copy_specification_from_item_group(self):
		self.set("website_specifications", [])
		if self.item_group:
			for label, desc in frappe.db.get_values("Item Website Specification",
				{"parent": self.item_group}, ["label", "description"]):
				row = self.append("website_specifications")
				row.label = label
				row.description = desc

	def get_product_details_section(self, context):
		""" Get section with tabs or website specifications. """
		context.show_tabs = self.show_tabbed_section
		if self.show_tabbed_section and self.tabs:
			context.tabs = self.get_tabs()
		else:
			context.website_specifications = self.website_specifications

	def get_tabs(self):
		tab_values = {}
		tab_values["tab_1_title"] = "Product Details"
		tab_values["tab_1_content"] = frappe.render_template(
			"templates/generators/item/item_specifications.html",
			{
				"website_specifications": self.website_specifications,
				"show_tabs": self.show_tabbed_section
			})

		for row in self.tabs:
			tab_values[f"tab_{row.idx + 1}_title"] = _(row.label)
			tab_values[f"tab_{row.idx + 1}_content"] = row.content

		return tab_values

def invalidate_cache_for_web_item(doc):
	"""Invalidate Website Item Group cache and rebuild ItemVariantsCacheManager."""
	from erpnext.stock.doctype.item.item import invalidate_item_variants_cache_for_website

	invalidate_cache_for(doc, doc.item_group)

	website_item_groups = list(set((doc.get("old_website_item_groups") or [])
		+ [d.item_group for d in doc.get({"doctype": "Website Item Group"}) if d.item_group]))

	for item_group in website_item_groups:
		invalidate_cache_for(doc, item_group)

	invalidate_item_variants_cache_for_website(doc)

@frappe.whitelist()
def make_website_item(doc, save=True):
	if not doc: return

	if isinstance(doc, string_types):
		doc = json.loads(doc)

	if frappe.db.exists("Website Item", {"item_code": doc.get("item_code")}):
		message = _("Website Item already exists against {0}").format(frappe.bold(doc.get("item_code")))
		frappe.throw(message, title=_("Already Published"))

	website_item = frappe.new_doc("Website Item")
	website_item.web_item_name = doc.get("item_name")

	fields_to_map = ["item_code", "item_name", "item_group", "stock_uom", "brand", "image",
		"has_variants", "variant_of", "description"]
	for field in fields_to_map:
		website_item.update({field: doc.get(field)})

	if not save:
		return website_item

	website_item.save()
	return [website_item.name, website_item.web_item_name]

def on_doctype_update():
	# since route is a Text column, it needs a length for indexing
	frappe.db.add_index("Website Item", ["route(500)"])