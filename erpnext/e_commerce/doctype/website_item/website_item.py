# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
from typing import TYPE_CHECKING, List, Union

if TYPE_CHECKING:
	from erpnext.stock.doctype.item.item import Item

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, random_string
from frappe.website.doctype.website_slideshow.website_slideshow import get_slideshow
from frappe.website.website_generator import WebsiteGenerator

from erpnext.e_commerce.doctype.item_review.item_review import get_item_reviews
from erpnext.e_commerce.redisearch_utils import (
	delete_item_from_index,
	insert_item_to_index,
	update_index_for_item,
)
from erpnext.e_commerce.shopping_cart.cart import _set_price_list
from erpnext.setup.doctype.item_group.item_group import (
	get_parent_item_groups,
	invalidate_cache_for,
)
from erpnext.utilities.product import get_price


class WebsiteItem(WebsiteGenerator):
	website = frappe._dict(
		page_title_field="web_item_name",
		condition_field="published",
		template="templates/generators/item/item.html",
		no_cache=1,
	)

	def autoname(self):
		# use naming series to accomodate items with same name (different item code)
		from frappe.model.naming import get_default_naming_series, make_autoname

		naming_series = get_default_naming_series("Website Item")
		if not self.name and naming_series:
			self.name = make_autoname(naming_series, doc=self)

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
			wig = frappe.qb.DocType("Website Item Group")
			query = (
				frappe.qb.from_(wig)
				.select(wig.item_group)
				.where(
					(wig.parentfield == "website_item_groups")
					& (wig.parenttype == "Website Item")
					& (wig.parent == self.name)
				)
			)
			result = query.run(as_list=True)

			self.old_website_item_groups = [x[0] for x in result]

	def on_update(self):
		invalidate_cache_for_web_item(self)
		self.update_template_item()

	def on_trash(self):
		super(WebsiteItem, self).on_trash()
		delete_item_from_index(self)
		self.publish_unpublish_desk_item(publish=False)

	def validate_duplicate_website_item(self):
		existing_web_item = frappe.db.exists("Website Item", {"item_code": self.item_code})
		if existing_web_item and existing_web_item != self.name:
			message = _("Website Item already exists against Item {0}").format(frappe.bold(self.item_code))
			frappe.throw(message, title=_("Already Published"))

	def publish_unpublish_desk_item(self, publish=True):
		if frappe.db.get_value("Item", self.item_code, "published_in_website") and publish:
			return  # if already published don't publish again
		frappe.db.set_value("Item", self.item_code, "published_in_website", publish)

	def make_route(self):
		"""Called from set_route in WebsiteGenerator."""
		if not self.route:
			return (
				cstr(frappe.db.get_value("Item Group", self.item_group, "route"))
				+ "/"
				+ self.scrub((self.item_name if self.item_name else self.item_code) + "-" + random_string(5))
			)

	def update_template_item(self):
		"""Publish Template Item if Variant is published."""
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
		if not self.website_image:
			return

		# find if website image url exists as public
		file_doc = frappe.get_all(
			"File",
			filters={"file_url": self.website_image},
			fields=["name", "is_private"],
			order_by="is_private asc",
			limit_page_length=1,
		)

		if file_doc:
			file_doc = file_doc[0]

		if not file_doc:
			frappe.msgprint(
				_("Website Image {0} attached to Item {1} cannot be found").format(
					self.website_image, self.name
				)
			)

			self.website_image = None

		elif file_doc.is_private:
			frappe.msgprint(_("Website Image should be a public file or website URL"))

			self.website_image = None

	def make_thumbnail(self):
		"""Make a thumbnail of `website_image`"""
		if frappe.flags.in_import or frappe.flags.in_migrate:
			return

		import requests.exceptions

		db_website_image = frappe.db.get_value(self.doctype, self.name, "website_image")
		if not self.is_new() and self.website_image != db_website_image:
			self.thumbnail = None

		if self.website_image and not self.thumbnail:
			file_doc = None

			try:
				file_doc = frappe.get_doc(
					"File",
					{
						"file_url": self.website_image,
						"attached_to_doctype": "Website Item",
						"attached_to_name": self.name,
					},
				)
			except frappe.DoesNotExistError:
				pass
				# cleanup
				frappe.local.message_log.pop()

			except requests.exceptions.HTTPError:
				frappe.msgprint(_("Warning: Invalid attachment {0}").format(self.website_image))
				self.website_image = None

			except requests.exceptions.SSLError:
				frappe.msgprint(
					_("Warning: Invalid SSL certificate on attachment {0}").format(self.website_image)
				)
				self.website_image = None

			# for CSV import
			if self.website_image and not file_doc:
				try:
					file_doc = frappe.get_doc(
						{
							"doctype": "File",
							"file_url": self.website_image,
							"attached_to_doctype": "Website Item",
							"attached_to_name": self.name,
						}
					).save()

				except IOError:
					self.website_image = None

			if file_doc:
				if not file_doc.thumbnail_url:
					file_doc.make_thumbnail()

				self.thumbnail = file_doc.thumbnail_url

	def get_context(self, context):
		context.show_search = True
		context.search_link = "/search"
		context.body_class = "product-page"

		context.parents = get_parent_item_groups(self.item_group, from_item=True)  # breadcumbs
		self.attributes = frappe.get_all(
			"Item Variant Attribute",
			fields=["attribute", "attribute_value"],
			filters={"parent": self.item_code},
		)

		if self.slideshow:
			context.update(get_slideshow(self))

		self.set_metatags(context)
		self.set_shopping_cart_data(context)

		settings = context.shopping_cart.cart_settings

		self.get_product_details_section(context)

		if settings.get("enable_reviews"):
			reviews_data = get_item_reviews(self.name)
			context.update(reviews_data)
			context.reviews = context.reviews[:4]

		context.wished = False
		if frappe.db.exists(
			"Wishlist Item", {"item_code": self.item_code, "parent": frappe.session.user}
		):
			context.wished = True

		context.user_is_customer = check_if_user_is_customer()

		context.recommended_items = None
		if settings and settings.enable_recommendations:
			context.recommended_items = self.get_recommended_items(settings)

		return context

	def set_selected_attributes(self, variants, context, attribute_values_available):
		for variant in variants:
			variant.attributes = frappe.get_all(
				"Item Variant Attribute",
				filters={"parent": variant.name},
				fields=["attribute", "attribute_value as value"],
			)

			# make an attribute-value map for easier access in templates
			variant.attribute_map = frappe._dict(
				{attr.attribute: attr.value for attr in variant.attributes}
			)

			for attr in variant.attributes:
				values = attribute_values_available.setdefault(attr.attribute, [])
				if attr.value not in values:
					values.append(attr.value)

				if variant.name == context.variant.name:
					context.selected_attributes[attr.attribute] = attr.value

	def set_attribute_values(self, attributes, context, attribute_values_available):
		for attr in attributes:
			values = context.attribute_values.setdefault(attr.attribute, [])

			if cint(frappe.db.get_value("Item Attribute", attr.attribute, "numeric_values")):
				for val in sorted(attribute_values_available.get(attr.attribute, []), key=flt):
					values.append(val)
			else:
				# get list of values defined (for sequence)
				for attr_value in frappe.db.get_all(
					"Item Attribute Value",
					fields=["attribute_value"],
					filters={"parent": attr.attribute},
					order_by="idx asc",
				):

					if attr_value.attribute_value in attribute_values_available.get(attr.attribute, []):
						values.append(attr_value.attribute_value)

	def set_metatags(self, context):
		context.metatags = frappe._dict({})

		safe_description = frappe.utils.to_markdown(self.description)

		context.metatags.url = frappe.utils.get_url() + "/" + context.route

		if context.website_image:
			if context.website_image.startswith("http"):
				url = context.website_image
			else:
				url = frappe.utils.get_url() + context.website_image
			context.metatags.image = url

		context.metatags.description = safe_description[:300]

		context.metatags.title = self.web_item_name or self.item_name or self.item_code

		context.metatags["og:type"] = "product"
		context.metatags["og:site_name"] = "ERPNext"

	def set_shopping_cart_data(self, context):
		from erpnext.e_commerce.shopping_cart.product_info import get_product_info_for_website

		context.shopping_cart = get_product_info_for_website(
			self.item_code, skip_quotation_creation=True
		)

	def copy_specification_from_item_group(self):
		self.set("website_specifications", [])
		if self.item_group:
			for label, desc in frappe.db.get_values(
				"Item Website Specification", {"parent": self.item_group}, ["label", "description"]
			):
				row = self.append("website_specifications")
				row.label = label
				row.description = desc

	def get_product_details_section(self, context):
		"""Get section with tabs or website specifications."""
		context.show_tabs = self.show_tabbed_section
		if self.show_tabbed_section and (self.tabs or self.website_specifications):
			context.tabs = self.get_tabs()
		else:
			context.website_specifications = self.website_specifications

	def get_tabs(self):
		tab_values = {}
		tab_values["tab_1_title"] = "Product Details"
		tab_values["tab_1_content"] = frappe.render_template(
			"templates/generators/item/item_specifications.html",
			{"website_specifications": self.website_specifications, "show_tabs": self.show_tabbed_section},
		)

		for row in self.tabs:
			tab_values[f"tab_{row.idx + 1}_title"] = _(row.label)
			tab_values[f"tab_{row.idx + 1}_content"] = row.content

		return tab_values

	def get_recommended_items(self, settings):
		ri = frappe.qb.DocType("Recommended Items")
		wi = frappe.qb.DocType("Website Item")

		query = (
			frappe.qb.from_(ri)
			.join(wi)
			.on(ri.item_code == wi.item_code)
			.select(ri.item_code, ri.route, ri.website_item_name, ri.website_item_thumbnail)
			.where((ri.parent == self.name) & (wi.published == 1))
			.orderby(ri.idx)
		)
		items = query.run(as_dict=True)

		if settings.show_price:
			is_guest = frappe.session.user == "Guest"
			# Show Price if logged in.
			# If not logged in and price is hidden for guest, skip price fetch.
			if is_guest and settings.hide_price_for_guest:
				return items

			selling_price_list = _set_price_list(settings, None)
			for item in items:
				item.price_info = get_price(
					item.item_code, selling_price_list, settings.default_customer_group, settings.company
				)

		return items


def invalidate_cache_for_web_item(doc):
	"""Invalidate Website Item Group cache and rebuild ItemVariantsCacheManager."""
	from erpnext.stock.doctype.item.item import invalidate_item_variants_cache_for_website

	invalidate_cache_for(doc, doc.item_group)

	website_item_groups = list(
		set(
			(doc.get("old_website_item_groups") or [])
			+ [d.item_group for d in doc.get({"doctype": "Website Item Group"}) if d.item_group]
		)
	)

	for item_group in website_item_groups:
		invalidate_cache_for(doc, item_group)

	# Update Search Cache
	update_index_for_item(doc)

	invalidate_item_variants_cache_for_website(doc)


def on_doctype_update():
	# since route is a Text column, it needs a length for indexing
	frappe.db.add_index("Website Item", ["route(500)"])


def check_if_user_is_customer(user=None):
	from frappe.contacts.doctype.contact.contact import get_contact_name

	if not user:
		user = frappe.session.user

	contact_name = get_contact_name(user)
	customer = None

	if contact_name:
		contact = frappe.get_doc("Contact", contact_name)
		for link in contact.links:
			if link.link_doctype == "Customer":
				customer = link.link_name
				break

	return True if customer else False


@frappe.whitelist()
def make_website_item(doc: "Item", save: bool = True) -> Union["WebsiteItem", List[str]]:
	"Make Website Item from Item. Used via Form UI or patch."

	if not doc:
		return

	if isinstance(doc, str):
		doc = json.loads(doc)

	if frappe.db.exists("Website Item", {"item_code": doc.get("item_code")}):
		message = _("Website Item already exists against {0}").format(frappe.bold(doc.get("item_code")))
		frappe.throw(message, title=_("Already Published"))

	website_item = frappe.new_doc("Website Item")
	website_item.web_item_name = doc.get("item_name")

	fields_to_map = [
		"item_code",
		"item_name",
		"item_group",
		"stock_uom",
		"brand",
		"has_variants",
		"variant_of",
		"description",
	]
	for field in fields_to_map:
		website_item.update({field: doc.get(field)})

	# Needed for publishing/mapping via Form UI only
	if not frappe.flags.in_migrate and (doc.get("image") and not website_item.website_image):
		website_item.website_image = doc.get("image")

	if not save:
		return website_item

	website_item.save()

	# Add to search cache
	insert_item_to_index(website_item)

	return [website_item.name, website_item.web_item_name]
