# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import urllib
from frappe.utils import nowdate, cint, cstr
from frappe.utils.nestedset import NestedSet
from frappe.website.website_generator import WebsiteGenerator
from frappe.website.render import clear_cache
from frappe.website.doctype.website_slideshow.website_slideshow import get_slideshow


class ItemGroup(NestedSet, WebsiteGenerator):
	nsm_parent_field = 'parent_item_group'
	website = frappe._dict(
		condition_field = "show_in_website",
		template = "templates/generators/item_group.html",
		no_cache = 1
	)

	def autoname(self):
		self.name = self.item_group_name

	def validate(self):
		super(ItemGroup, self).validate()
		self.make_route()

	def on_update(self):
		NestedSet.on_update(self)
		invalidate_cache_for(self)
		self.validate_name_with_item()
		self.validate_one_root()

	def make_route(self):
		'''Make website route'''
		if not self.route:
			self.route = ''
			if self.parent_item_group:
				parent_route = frappe.get_doc('Item Group', self.parent_item_group).route

				if parent_route:
					self.route = parent_route + '/'

			self.route += self.scrub(self.item_group_name)

			return self.route

	def after_rename(self, olddn, newdn, merge=False):
		NestedSet.after_rename(self, olddn, newdn, merge)

	def on_trash(self):
		NestedSet.on_trash(self)
		WebsiteGenerator.on_trash(self)

	def validate_name_with_item(self):
		if frappe.db.exists("Item", self.name):
			frappe.throw(frappe._("An item exists with same name ({0}), please change the item group name or rename the item").format(self.name))

	def get_context(self, context):
		context.show_search=True
		context.page_length = 6
		context.search_link = '/product_search'

		start = int(frappe.form_dict.start or 0)
		if start < 0:
			start = 0
		context.update({
			"items": get_product_list_for_group(product_group = self.name, start=start,
				limit=context.page_length + 1, search=frappe.form_dict.get("search")),
			"parent_groups": get_parent_item_groups(self.name),
			"title": self.name,
			"products_as_list": cint(frappe.db.get_single_value('Website Settings', 'products_as_list'))
		})

		if self.slideshow:
			context.update(get_slideshow(self))

		return context

@frappe.whitelist(allow_guest=True)
def get_product_list_for_group(product_group=None, start=0, limit=10, search=None):
	child_groups = ", ".join(['"' + i[0] + '"' for i in get_child_groups(product_group)])

	# base query
	query = """select name, item_name, item_code, route, image, website_image, thumbnail, item_group,
			description, web_long_description as website_description
		from `tabItem`
		where show_in_website = 1
			and disabled=0
			and (end_of_life is null or end_of_life='0000-00-00' or end_of_life > %(today)s)
			and (variant_of = '' or variant_of is null)
			and (item_group in ({child_groups})
			or name in (select parent from `tabWebsite Item Group` where item_group in ({child_groups})))
			""".format(child_groups=child_groups)
	# search term condition
	if search:
		query += """ and (web_long_description like %(search)s
				or item_name like %(search)s
				or name like %(search)s)"""
		search = "%" + cstr(search) + "%"

	query += """order by weightage desc, modified desc limit %s, %s""" % (start, limit)

	data = frappe.db.sql(query, {"product_group": product_group,"search": search, "today": nowdate()}, as_dict=1)

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

	products_template = 'templates/includes/products_as_grid.html'
	if cint(frappe.db.get_single_value('Products Settings', 'products_as_list')):
		products_template = 'templates/includes/products_as_list.html'

	return frappe.get_template(products_template).render(context)

def get_group_item_count(item_group):
	child_groups = ", ".join(['"' + i[0] + '"' for i in get_child_groups(item_group)])
	return frappe.db.sql("""select count(*) from `tabItem`
		where docstatus = 0 and show_in_website = 1
		and (item_group in (%s)
			or name in (select parent from `tabWebsite Item Group`
				where item_group in (%s))) """ % (child_groups, child_groups))[0][0]


def get_parent_item_groups(item_group_name):
	item_group = frappe.get_doc("Item Group", item_group_name)
	return frappe.db.sql("""select name, route from `tabItem Group`
		where lft <= %s and rgt >= %s
		and show_in_website=1
		order by lft asc""", (item_group.lft, item_group.rgt), as_dict=True)

def invalidate_cache_for(doc, item_group=None):
	if not item_group:
		item_group = doc.name

	for d in get_parent_item_groups(item_group):
		d = frappe.get_doc("Item Group", d.name)
		if d.route:
			clear_cache(d.route)
