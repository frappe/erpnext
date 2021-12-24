# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import copy

import frappe
from frappe import _
from frappe.utils import cint, cstr, nowdate
from frappe.utils.nestedset import NestedSet
from frappe.website.utils import clear_cache
from frappe.website.website_generator import WebsiteGenerator
from six.moves.urllib.parse import quote

from erpnext.shopping_cart.filters import ProductFiltersBuilder
from erpnext.shopping_cart.product_info import set_product_info_for_website
from erpnext.shopping_cart.product_query import ProductQuery
from erpnext.utilities.product import get_qty_in_stock


class ItemGroup(NestedSet, WebsiteGenerator):
	nsm_parent_field = 'parent_item_group'
	website = frappe._dict(
		condition_field = "show_in_website",
		template = "templates/generators/item_group.html",
		no_cache = 1,
		no_breadcrumbs = 1
	)

	def autoname(self):
		self.name = self.item_group_name

	def validate(self):
		super(ItemGroup, self).validate()

		if not self.parent_item_group and not frappe.flags.in_test:
			if frappe.db.exists("Item Group", _('All Item Groups')):
				self.parent_item_group = _('All Item Groups')

		self.make_route()
		self.validate_item_group_defaults()

	def on_update(self):
		NestedSet.on_update(self)
		invalidate_cache_for(self)
		self.validate_name_with_item()
		self.validate_one_root()
		self.delete_child_item_groups_key()

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
		self.delete_child_item_groups_key()

	def validate_name_with_item(self):
		if frappe.db.exists("Item", self.name):
			frappe.throw(frappe._("An item exists with same name ({0}), please change the item group name or rename the item").format(self.name), frappe.NameError)

	def get_context(self, context):
		context.show_search=True
		context.page_length = cint(frappe.db.get_single_value('Products Settings', 'products_per_page')) or 6
		context.search_link = '/product_search'

		if frappe.form_dict:
			search = frappe.form_dict.search
			field_filters = frappe.parse_json(frappe.form_dict.field_filters)
			attribute_filters = frappe.parse_json(frappe.form_dict.attribute_filters)
			start = frappe.parse_json(frappe.form_dict.start)
		else:
			search = None
			attribute_filters = None
			field_filters = {}
			start = 0

		if not field_filters:
			field_filters = {}

		# Ensure the query remains within current item group & sub group
		field_filters['item_group'] = [ig[0] for ig in get_child_groups(self.name)]

		engine = ProductQuery()
		context.items = engine.query(attribute_filters, field_filters, search, start, item_group=self.name)

		filter_engine = ProductFiltersBuilder(self.name)

		context.field_filters = filter_engine.get_field_filters()
		context.attribute_filters = filter_engine.get_attribute_filters()

		context.update({
			"parents": get_parent_item_groups(self.parent_item_group),
			"title": self.name
		})

		if self.slideshow:
			values = {
				'show_indicators': 1,
				'show_controls': 0,
				'rounded': 1,
				'slider_name': self.slideshow
			}
			slideshow = frappe.get_doc("Website Slideshow", self.slideshow)
			slides = slideshow.get({"doctype":"Website Slideshow Item"})
			for index, slide in enumerate(slides):
				values[f"slide_{index + 1}_image"] = slide.image
				values[f"slide_{index + 1}_title"] = slide.heading
				values[f"slide_{index + 1}_subtitle"] = slide.description
				values[f"slide_{index + 1}_theme"] = slide.theme or "Light"
				values[f"slide_{index + 1}_content_align"] = slide.content_align or "Centre"
				values[f"slide_{index + 1}_primary_action_label"] = slide.label
				values[f"slide_{index + 1}_primary_action"] = slide.url

			context.slideshow = values

		context.breadcrumbs = 0
		context.title = self.website_title or self.name

		return context

	def delete_child_item_groups_key(self):
		frappe.cache().hdel("child_item_groups", self.name)

	def validate_item_group_defaults(self):
		from erpnext.stock.doctype.item.item import validate_item_default_company_links
		validate_item_default_company_links(self.item_group_defaults)

@frappe.whitelist(allow_guest=True)
def get_product_list_for_group(product_group=None, start=0, limit=10, search=None):
	if product_group:
		item_group = frappe.get_cached_doc('Item Group', product_group)
		if item_group.is_group:
			# return child item groups if the type is of "Is Group"
			return get_child_groups_for_list_in_html(item_group, start, limit, search)

	child_groups = ", ".join(frappe.db.escape(i[0]) for i in get_child_groups(product_group))

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

	query += """order by I.weightage desc, in_stock desc, I.modified desc limit %s, %s""" % (cint(start), cint(limit))

	data = frappe.db.sql(query, {"product_group": product_group,"search": search, "today": nowdate()}, as_dict=1)
	data = adjust_qty_for_expired_items(data)

	if cint(frappe.db.get_single_value("Shopping Cart Settings", "enabled")):
		for item in data:
			set_product_info_for_website(item)

	return data

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
			parent_item_group = item_group.name,
			lft = ('>', item_group.lft),
			rgt = ('<', item_group.rgt),
		),
		or_filters = search_filters,
		order_by = 'weightage desc, name asc',
		start = start,
		limit = limit
	)

	return data

def adjust_qty_for_expired_items(data):
	adjusted_data = []

	for item in data:
		if item.get('has_batch_no') and item.get('website_warehouse'):
			stock_qty_dict = get_qty_in_stock(
				item.get('name'), 'website_warehouse', item.get('website_warehouse'))
			qty = stock_qty_dict.stock_qty[0][0] if stock_qty_dict.stock_qty else 0
			item['in_stock'] = 1 if qty else 0
		adjusted_data.append(item)

	return adjusted_data


def get_child_groups(item_group_name):
	item_group = frappe.get_doc("Item Group", item_group_name)
	return frappe.db.sql("""select name
		from `tabItem Group` where lft>=%(lft)s and rgt<=%(rgt)s
			and show_in_website = 1""", {"lft": item_group.lft, "rgt": item_group.rgt})

def get_child_item_groups(item_group_name):
	item_group = frappe.get_cached_value("Item Group",
		item_group_name, ["lft", "rgt"], as_dict=1)

	child_item_groups = [d.name for d in frappe.get_all('Item Group',
		filters= {'lft': ('>=', item_group.lft),'rgt': ('<=', item_group.rgt)})]

	return child_item_groups or {}

def get_item_for_list_in_html(context):
	# add missing absolute link in files
	# user may forget it during upload
	if (context.get("website_image") or "").startswith("files/"):
		context["website_image"] = "/" + quote(context["website_image"])

	context["show_availability_status"] = cint(frappe.db.get_single_value('Products Settings',
		'show_availability_status'))

	products_template = 'templates/includes/products_as_list.html'

	return frappe.get_template(products_template).render(context)

def get_group_item_count(item_group):
	child_groups = ", ".join('"' + i[0] + '"' for i in get_child_groups(item_group))
	return frappe.db.sql("""select count(*) from `tabItem`
		where docstatus = 0 and show_in_website = 1
		and (item_group in (%s)
			or name in (select parent from `tabWebsite Item Group`
				where item_group in (%s))) """ % (child_groups, child_groups))[0][0]


def get_parent_item_groups(item_group_name):
	base_parents = [
		{"name": frappe._("Home"), "route":"/"},
		{"name": frappe._("All Products"), "route":"/all-products"},
	]
	if not item_group_name:
		return base_parents

	item_group = frappe.get_doc("Item Group", item_group_name)
	parent_groups = frappe.db.sql("""select name, route from `tabItem Group`
		where lft <= %s and rgt >= %s
		and show_in_website=1
		order by lft asc""", (item_group.lft, item_group.rgt), as_dict=True)

	return base_parents + parent_groups

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
