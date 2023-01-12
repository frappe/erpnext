# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import copy
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.nestedset import NestedSet
from frappe.website.utils import clear_cache
from frappe.website.website_generator import WebsiteGenerator

from erpnext.e_commerce.doctype.e_commerce_settings.e_commerce_settings import ECommerceSettings
from erpnext.e_commerce.product_data_engine.filters import ProductFiltersBuilder


class ItemGroup(NestedSet, WebsiteGenerator):
	nsm_parent_field = "parent_item_group"
	website = frappe._dict(
		condition_field="show_in_website",
		template="templates/generators/item_group.html",
		no_cache=1,
		no_breadcrumbs=1,
	)

	def autoname(self):
		self.name = self.item_group_name

	def validate(self):
		super(ItemGroup, self).validate()

		if not self.parent_item_group and not frappe.flags.in_test:
			if frappe.db.exists("Item Group", _("All Item Groups")):
				self.parent_item_group = _("All Item Groups")

		self.make_route()
		self.validate_item_group_defaults()
		ECommerceSettings.validate_field_filters(self.filter_fields, enable_field_filters=True)

	def on_update(self):
		NestedSet.on_update(self)
		invalidate_cache_for(self)
		self.validate_one_root()
		self.delete_child_item_groups_key()

	def make_route(self):
		"""Make website route"""
		if not self.route:
			self.route = ""
			if self.parent_item_group:
				parent_item_group = frappe.get_doc("Item Group", self.parent_item_group)

				# make parent route only if not root
				if parent_item_group.parent_item_group and parent_item_group.route:
					self.route = parent_item_group.route + "/"

			self.route += self.scrub(self.item_group_name)

			return self.route

	def on_trash(self):
		NestedSet.on_trash(self)
		WebsiteGenerator.on_trash(self)
		self.delete_child_item_groups_key()

	def get_context(self, context):
		context.show_search = True
		context.body_class = "product-page"
		context.page_length = (
			cint(frappe.db.get_single_value("E Commerce Settings", "products_per_page")) or 6
		)
		context.search_link = "/product_search"

		filter_engine = ProductFiltersBuilder(self.name)

		context.field_filters = filter_engine.get_field_filters()
		context.attribute_filters = filter_engine.get_attribute_filters()

		context.update({"parents": get_parent_item_groups(self.parent_item_group), "title": self.name})

		if self.slideshow:
			values = {"show_indicators": 1, "show_controls": 0, "rounded": 1, "slider_name": self.slideshow}
			slideshow = frappe.get_doc("Website Slideshow", self.slideshow)
			slides = slideshow.get({"doctype": "Website Slideshow Item"})
			for index, slide in enumerate(slides):
				values[f"slide_{index + 1}_image"] = slide.image
				values[f"slide_{index + 1}_title"] = slide.heading
				values[f"slide_{index + 1}_subtitle"] = slide.description
				values[f"slide_{index + 1}_theme"] = slide.get("theme") or "Light"
				values[f"slide_{index + 1}_content_align"] = slide.get("content_align") or "Centre"
				values[f"slide_{index + 1}_primary_action"] = slide.url

			context.slideshow = values

		context.no_breadcrumbs = False
		context.title = self.website_title or self.name
		context.name = self.name
		context.item_group_name = self.item_group_name

		return context

	def delete_child_item_groups_key(self):
		frappe.cache().hdel("child_item_groups", self.name)

	def validate_item_group_defaults(self):
		from erpnext.stock.doctype.item.item import validate_item_default_company_links

		validate_item_default_company_links(self.item_group_defaults)


def get_child_groups_for_website(item_group_name, immediate=False, include_self=False):
	"""Returns child item groups *excluding* passed group."""
	item_group = frappe.get_cached_value("Item Group", item_group_name, ["lft", "rgt"], as_dict=1)
	filters = {"lft": [">", item_group.lft], "rgt": ["<", item_group.rgt], "show_in_website": 1}

	if immediate:
		filters["parent_item_group"] = item_group_name

	if include_self:
		filters.update({"lft": [">=", item_group.lft], "rgt": ["<=", item_group.rgt]})

	return frappe.get_all("Item Group", filters=filters, fields=["name", "route"], order_by="name")


def get_child_item_groups(item_group_name):
	item_group = frappe.get_cached_value("Item Group", item_group_name, ["lft", "rgt"], as_dict=1)

	child_item_groups = [
		d.name
		for d in frappe.get_all(
			"Item Group", filters={"lft": (">=", item_group.lft), "rgt": ("<=", item_group.rgt)}
		)
	]

	return child_item_groups or {}


def get_item_for_list_in_html(context):
	# add missing absolute link in files
	# user may forget it during upload
	if (context.get("website_image") or "").startswith("files/"):
		context["website_image"] = "/" + quote(context["website_image"])

	products_template = "templates/includes/products_as_list.html"

	return frappe.get_template(products_template).render(context)


def get_parent_item_groups(item_group_name, from_item=False):
	base_nav_page = {"name": _("Shop by Category"), "route": "/shop-by-category"}

	if from_item and frappe.request.environ.get("HTTP_REFERER"):
		# base page after 'Home' will vary on Item page
		last_page = frappe.request.environ["HTTP_REFERER"].split("/")[-1].split("?")[0]
		if last_page and last_page in ("shop-by-category", "all-products"):
			base_nav_page_title = " ".join(last_page.split("-")).title()
			base_nav_page = {"name": _(base_nav_page_title), "route": "/" + last_page}

	base_parents = [
		{"name": _("Home"), "route": "/"},
		base_nav_page,
	]

	if not item_group_name:
		return base_parents

	item_group = frappe.db.get_value("Item Group", item_group_name, ["lft", "rgt"], as_dict=1)
	parent_groups = frappe.db.sql(
		"""select name, route from `tabItem Group`
		where lft <= %s and rgt >= %s
		and show_in_website=1
		order by lft asc""",
		(item_group.lft, item_group.rgt),
		as_dict=True,
	)

	return base_parents + parent_groups


def invalidate_cache_for(doc, item_group=None):
	if not item_group:
		item_group = doc.name

	for d in get_parent_item_groups(item_group):
		item_group_name = frappe.db.get_value("Item Group", d.get("name"))
		if item_group_name:
			clear_cache(frappe.db.get_value("Item Group", item_group_name, "route"))


def get_item_group_defaults(item, company):
	item = frappe.get_cached_doc("Item", item)
	item_group = frappe.get_cached_doc("Item Group", item.item_group)

	for d in item_group.item_group_defaults or []:
		if d.company == company:
			row = copy.deepcopy(d.as_dict())
			row.pop("name")
			return row

	return frappe._dict()
