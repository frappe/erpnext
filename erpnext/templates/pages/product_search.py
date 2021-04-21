# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, nowdate, cint
from erpnext.setup.doctype.item_group.item_group import get_item_for_list_in_html
from erpnext.e_commerce.shopping_cart.product_info import set_product_info_for_website

# For SEARCH -------
import redis
from redisearch import Client, AutoCompleter, Suggestion, IndexDefinition, TextField, TagField

WEBSITE_ITEM_INDEX = 'website_items_index'
WEBSITE_ITEM_KEY_PREFIX = 'website_item:'
WEBSITE_ITEM_NAME_AUTOCOMPLETE = 'website_items_name_dict'
# -----------------

no_cache = 1


def get_context(context):
	context.show_search = True

@frappe.whitelist(allow_guest=True)
def get_product_list(search=None, start=0, limit=12):
	# limit = 12 because we show 12 items in the grid view

	# base query
	query = """select I.name, I.item_name, I.item_code, I.route, I.image, I.website_image, I.thumbnail, I.item_group,
			I.description, I.web_long_description as website_description, I.is_stock_item,
			case when (S.actual_qty - S.reserved_qty) > 0 then 1 else 0 end as in_stock, I.website_warehouse,
			I.has_batch_no
		from `tabItem` I
		left join tabBin S on I.item_code = S.item_code and I.website_warehouse = S.warehouse
		where (I.show_in_website = 1)
			and I.disabled = 0
			and (I.end_of_life is null or I.end_of_life='0000-00-00' or I.end_of_life > %(today)s)"""

	# search term condition
	if search:
		query += """ and (I.web_long_description like %(search)s
				or I.description like %(search)s
				or I.item_name like %(search)s
				or I.name like %(search)s)"""
		search = "%" + cstr(search) + "%"

	# order by
	query += """ order by I.weightage desc, in_stock desc, I.modified desc limit %s, %s""" % (cint(start), cint(limit))

	data = frappe.db.sql(query, {
		"search": search,
		"today": nowdate()
	}, as_dict=1)

	for item in data:
		set_product_info_for_website(item)

	return [get_item_for_list_in_html(r) for r in data]

@frappe.whitelist(allow_guest=True)
def search(query):
	ac = AutoCompleter(WEBSITE_ITEM_NAME_AUTOCOMPLETE, port=13000)
	suggestions = ac.get_suggestions(query, num=10)
	print(suggestions)
	return list([s.string for s in suggestions])

def create_website_items_index():
	'''Creates Index Definition'''
	# DROP if already exists
	try:
		client.drop_index()
	except:
		pass

	# CREATE index
	client = Client(WEBSITE_ITEM_INDEX, port=13000)
	idx_def = IndexDefinition([WEBSITE_ITEM_KEY_PREFIX])

	client.create_index(
		[TextField("web_item_name", sortable=True), TagField("tags")],
		definition=idx_def
	)

	reindex_all_web_items()

def insert_item_to_index(website_item_doc):
	# Insert item to index
	key = get_cache_key(website_item_doc.name)
	r = redis.Redis("localhost", 13000)
	web_item = create_web_item_map(website_item_doc)
	r.hset(key, mapping=web_item)
	insert_to_name_ac(website_item_doc.name)

def insert_to_name_ac(name):
	ac = AutoCompleter(WEBSITE_ITEM_NAME_AUTOCOMPLETE, port=13000)
	ac.add_suggestions(Suggestion(name))

def create_web_item_map(website_item_doc):
	web_item = {}
	web_item["web_item_name"] = website_item_doc.web_item_name
	web_item["route"] = website_item_doc.route
	web_item["thumbnail"] = website_item_doc.thumbnail or ''
	web_item["description"] = website_item_doc.description or ''

	return web_item
	
def update_index_for_item(website_item_doc):
	# Reinsert to Cache
	insert_item_to_index(website_item_doc)
	define_autocomplete_dictionary()
	# TODO: Only reindex updated items
	create_website_items_index()

def delete_item_from_index(website_item_doc):
	r = redis.Redis("localhost", 13000)
	key = get_cache_key(website_item_doc.name)
	
	try:
		r.delete(key)
	except:
		return False

	# TODO: Also delete autocomplete suggestion
	return True

def define_autocomplete_dictionary():
	# AC for name
	# TODO: AC for category

	r = redis.Redis("localhost", 13000)
	ac = AutoCompleter(WEBSITE_ITEM_NAME_AUTOCOMPLETE, port=13000)

	try:
		r.delete(WEBSITE_ITEM_NAME_AUTOCOMPLETE)
	except:
		return False
	
	items = frappe.get_all(
		'Website Item', 
		fields=['web_item_name'], 
		filters={"published": True}
	)

	for item in items:
		print("adding suggestion: " + item.web_item_name)
		ac.add_suggestions(Suggestion(item.web_item_name))

	return True

def reindex_all_web_items():
	items = frappe.get_all(
		'Website Item', 
		fields=['web_item_name', 'name', 'route', 'thumbnail', 'description'], 
		filters={"published": True}
	)

	r = redis.Redis("localhost", 13000)
	for item in items:
		web_item = create_web_item_map(item)
		key = get_cache_key(item.name)
		print(key, web_item)
		r.hset(key, mapping=web_item)

def get_cache_key(name):
	name = frappe.scrub(name)
	return f"{WEBSITE_ITEM_KEY_PREFIX}{name}"

# TODO: Remove later
define_autocomplete_dictionary()
create_website_items_index()
