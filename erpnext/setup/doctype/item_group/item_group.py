# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import urllib
import copy
from frappe.utils import nowdate, cint, cstr
from frappe.utils.nestedset import NestedSet
from frappe.website.website_generator import WebsiteGenerator
from frappe.website.render import clear_cache
from frappe.website.doctype.website_slideshow.website_slideshow import get_slideshow
from erpnext.shopping_cart.product_info import set_product_info_for_website
from erpnext.utilities.product import get_qty_in_stock
from frappe.utils.html_utils import clean_html

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
		self.description = clean_html(self.description)
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
				parent_item_group = frappe.get_doc('Item Group', self.parent_item_group)

				# make parent route only if not root
				if parent_item_group.parent_item_group and parent_item_group.route:
					self.route = parent_item_group.route + '/'

			self.route += self.scrub(self.item_group_name)

			return self.route

	def on_trash(self):
		NestedSet.on_trash(self)
		WebsiteGenerator.on_trash(self)

	def validate_name_with_item(self):
		if frappe.db.exists("Item", self.name):
			frappe.throw(frappe._("An item exists with same name ({0}), please change the item group name or rename the item").format(self.name), frappe.NameError)

	def get_context(self, context):
		context.show_search=True
		context.page_length = cint(frappe.db.get_single_value('Products Settings', 'products_per_page')) or 6
		context.search_link = '/product_search'

		start = int(frappe.form_dict.start or 0)
		if start < 0:
			start = 0
		context.update({
			"items": get_product_list_for_group(product_group = self.name, start=start,
				limit=context.page_length + 1, search=frappe.form_dict.get("search")),
			"parents": get_parent_item_groups(self.parent_item_group),
			"title": self.name,
			"products_as_list": cint(frappe.db.get_single_value('Website Settings', 'products_as_list'))
		})

		if self.slideshow:
			context.update(get_slideshow(self))

		return context

@frappe.whitelist(allow_guest=True)
def get_product_list_for_group(product_group=None, start=0, limit=10, search=None):
	if product_group:
		item_group = frappe.get_cached_doc('Item Group', product_group)
		if item_group.is_group:
			# return child item groups if the type is of "Is Group"
			return get_child_groups_for_list_in_html(item_group, start, limit, search)

	child_groups = ", ".join(['"' + frappe.db.escape(i[0]) + '"' for i in get_child_groups(product_group)])

	# base query
	query = """select I.name, I.item_name, I.item_code, I.route, I.image, I.website_image, I.thumbnail, I.item_group,
			I.description, I.web_long_description as website_description, I.is_stock_item,
			case when (S.actual_qty - S.reserved_qty) > 0 then 1 else 0 end as in_stock, I.website_warehouse,
			I.has_batch_no
		from `tabItem` I
		left join tabBin S on I.item_code = S.item_code and I.website_warehouse = S.warehouse
		where I.show_in_website = 1
			and I.disabled = 0
			and (I.end_of_life is null or I.end_of_life='0000-00-00' or I.end_of_life > %(today)s)
			and (I.variant_of = '' or I.variant_of is null)
			and (I.item_group in ({child_groups})
			or I.name in (select parent from `tabWebsite Item Group` where item_group in ({child_groups})))
			""".format(child_groups=child_groups)
	# search term condition
	if search:
		query += """ and (I.web_long_description like %(search)s
				or I.item_name like %(search)s
				or I.name like %(search)s)"""
		search = "%" + cstr(search) + "%"

	query += """order by I.weightage desc, in_stock desc, I.modified desc limit %s, %s""" % (start, limit)

	data = frappe.db.sql(query, {"product_group": product_group,"search": search, "today": nowdate()}, as_dict=1)
	data = adjust_qty_for_expired_items(data)

	for item in data:
		set_product_info_for_website(item)

	return [get_item_for_list_in_html(r) for r in data]

def get_child_groups_for_list_in_html(item_group, start, limit, search):
	search_filters = None
	if search_filters:
		search_filters = [
			dict(name = ('like', '%{}%'.format(search))),
			dict(description = ('like', '%{}%'.format(search)))
		]
	data = frappe.db.get_all('Item Group',
		fields = ['name', 'route', 'description', 'image'],
		filters = dict(
			show_in_website = 1,
			lft = ('>', item_group.lft),
			rgt = ('<', item_group.rgt),
		),
		or_filters = search_filters,
		order_by = 'weightage desc, name asc',
		start = start,
		limit = limit
	)

	return [get_item_for_list_in_html(r) for r in data]

def adjust_qty_for_expired_items(data):
	adjusted_data = []

	for item in data:
		if item.get('has_batch_no') and item.get('website_warehouse'):
			stock_qty_dict = get_qty_in_stock(
				item.get('name'), 'website_warehouse', item.get('website_warehouse'))
			qty = stock_qty_dict.stock_qty[0][0]
			item['in_stock'] = 1 if qty else 0
		adjusted_data.append(item)

	return adjusted_data


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

	context["show_availability_status"] = cint(frappe.db.get_single_value('Products Settings',
		'show_availability_status'))

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
	if not item_group_name:
		return [{"name": frappe._("Home"), "route":"/"}]
	item_group = frappe.get_doc("Item Group", item_group_name)
	parent_groups = frappe.db.sql("""select name, route from `tabItem Group`
		where lft <= %s and rgt >= %s
		and show_in_website=1
		order by lft asc""", (item_group.lft, item_group.rgt), as_dict=True)

	return 	[{"name": frappe._("Home"), "route":"/"}] + parent_groups

def invalidate_cache_for(doc, item_group=None):
	if not item_group:
		item_group = doc.name

	for d in get_parent_item_groups(item_group):
		item_group_name = frappe.db.get_value("Item Group", d.get('name'))
		if item_group_name:
			clear_cache(frappe.db.get_value('Item Group', item_group_name, 'route'))

def get_item_group_defaults(item, company):
	item = frappe.get_cached_doc("Item", item)
	item_group = frappe.get_cached_doc("Item Group", item.item_group)

	for d in item_group.item_group_defaults or []:
		if d.company == company:
			row = copy.deepcopy(d.as_dict())
			row.pop("name")
			return row

	return frappe._dict()