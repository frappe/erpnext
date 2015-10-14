# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import urllib
from frappe.utils.nestedset import NestedSet
from frappe.website.website_generator import WebsiteGenerator
from frappe.website.render import clear_cache
from frappe.website.doctype.website_slideshow.website_slideshow import get_slideshow


class ItemGroup(NestedSet, WebsiteGenerator):
	nsm_parent_field = 'parent_item_group'
	website = frappe._dict(
		condition_field = "show_in_website",
		template = "templates/generators/item_group.html",
		parent_website_route_field = "parent_item_group"
	)

	def autoname(self):
		self.name = self.item_group_name

	def on_update(self):
		NestedSet.on_update(self)
		WebsiteGenerator.on_update(self)
		invalidate_cache_for(self)
		self.validate_name_with_item()
		self.validate_one_root()

	def after_rename(self, olddn, newdn, merge=False):
		NestedSet.after_rename(self, olddn, newdn, merge)
		WebsiteGenerator.after_rename(self, olddn, newdn, merge)

	def on_trash(self):
		NestedSet.on_trash(self)
		WebsiteGenerator.on_trash(self)

	def set_parent_website_route(self):
		"""Overwrite `parent_website_route` from `WebsiteGenerator`.
			Only set `parent_website_route` if parent is visble.

			e.g. If `show_in_website` is set for Products then url should be `/products`"""
		if self.parent_item_group and frappe.db.get_value("Item Group", self.parent_item_group, "show_in_website"):
			WebsiteGenerator.set_parent_website_route(self)
		else:
			self.parent_website_route = ""

	def validate_name_with_item(self):
		if frappe.db.exists("Item", self.name):
			frappe.throw(frappe._("An item exists with same name ({0}), please change the item group name or rename the item").format(self.name))

	def get_context(self, context):
		context.update({
			"items": get_product_list_for_group(product_group = self.name, limit=100),
			"parent_groups": get_parent_item_groups(self.name),
			"title": self.name
		})

		if self.slideshow:
			context.update(get_slideshow(self))

		return context

def get_product_list_for_group(product_group=None, start=0, limit=10):
	child_groups = ", ".join(['"' + i[0] + '"' for i in get_child_groups(product_group)])

	# base query
	query = """select name, item_name, page_name, website_image, thumbnail, item_group,
			web_long_description as website_description,
			concat(parent_website_route, "/", page_name) as route
		from `tabItem`
		where show_in_website = 1
			and (variant_of = '' or variant_of is null)
			and (item_group in (%s)
			or name in (select parent from `tabWebsite Item Group` where item_group in (%s)))
			""" % (child_groups, child_groups)

	query += """order by weightage desc, modified desc limit %s, %s""" % (start, limit)

	data = frappe.db.sql(query, {"product_group": product_group}, as_dict=1)

	return [get_item_for_list_in_html(r) for r in data]

def get_child_groups(item_group_name):
	item_group = frappe.get_doc("Item Group", item_group_name)
	return frappe.db.sql("""select name
		from `tabItem Group` where lft>=%(lft)s and rgt<=%(rgt)s
			and show_in_website = 1""", {"lft": item_group.lft, "rgt": item_group.rgt})

def get_item_for_list_in_html(context):
	# add missing absolute link in files
	# user may forget it during upload
	if (context.get("website_image") or "").startswith("files/"):
		context["website_image"] = "/" + urllib.quote(context["website_image"])
	return frappe.get_template("templates/includes/product_in_grid.html").render(context)

def get_group_item_count(item_group):
	child_groups = ", ".join(['"' + i[0] + '"' for i in get_child_groups(item_group)])
	return frappe.db.sql("""select count(*) from `tabItem`
		where docstatus = 0 and show_in_website = 1
		and (item_group in (%s)
			or name in (select parent from `tabWebsite Item Group`
				where item_group in (%s))) """ % (child_groups, child_groups))[0][0]


def get_parent_item_groups(item_group_name):
	item_group = frappe.get_doc("Item Group", item_group_name)
	return frappe.db.sql("""select name, page_name from `tabItem Group`
		where lft <= %s and rgt >= %s
		and ifnull(show_in_website,0)=1
		order by lft asc""", (item_group.lft, item_group.rgt), as_dict=True)

def invalidate_cache_for(doc, item_group=None):
	if not item_group:
		item_group = doc.name

	for d in get_parent_item_groups(item_group):
		d = frappe.get_doc("Item Group", d.name)
		route = d.get_route()
		if route:
			clear_cache(route)
