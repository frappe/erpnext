# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils.redis_wrapper import RedisWrapper
from redisearch import (Client, AutoCompleter, Suggestion, IndexDefinition, TextField, TagField)

WEBSITE_ITEM_INDEX = 'website_items_index'
WEBSITE_ITEM_KEY_PREFIX = 'website_item:'
WEBSITE_ITEM_NAME_AUTOCOMPLETE = 'website_items_name_dict'
WEBSITE_ITEM_CATEGORY_AUTOCOMPLETE = 'website_items_category_dict'

def get_indexable_web_fields():
	"Return valid fields from Website Item that can be searched for."
	web_item_meta = frappe.get_meta("Website Item", cached=True)
	valid_fields = filter(
		lambda df: df.fieldtype in ("Link", "Table MultiSelect", "Data", "Small Text", "Text Editor"),
		web_item_meta.fields)

	return [df.fieldname for df in valid_fields]

ALLOWED_INDEXABLE_FIELDS_SET = get_indexable_web_fields()


def is_search_module_loaded():
	cache = frappe.cache()
	out = cache.execute_command('MODULE LIST')

	parsed_output = " ".join(
		(" ".join([s.decode() for s in o if not isinstance(s, int)]) for o in out)
	)

	return "search" in parsed_output

def if_redisearch_loaded(function):
	"Decorator to check if Redisearch is loaded."
	def wrapper(*args, **kwargs):
		if is_search_module_loaded():
			func = function(*args, **kwargs)
			return func
		return

	return wrapper

def make_key(key):
	return "{0}|{1}".format(frappe.conf.db_name, key).encode('utf-8')

@if_redisearch_loaded
def create_website_items_index():
	"Creates Index Definition."

	# CREATE index
	client = Client(make_key(WEBSITE_ITEM_INDEX), conn=frappe.cache())

	# DROP if already exists
	try:
		client.drop_index()
	except Exception:
		pass

	idx_def = IndexDefinition([make_key(WEBSITE_ITEM_KEY_PREFIX)])

	# Based on e-commerce settings
	idx_fields = frappe.db.get_single_value(
		'E Commerce Settings',
		'search_index_fields'
	)
	idx_fields = idx_fields.split(',') if idx_fields else []

	if 'web_item_name' in idx_fields:
		idx_fields.remove('web_item_name')

	idx_fields = list(map(to_search_field, idx_fields))

	client.create_index(
		[TextField("web_item_name", sortable=True)] + idx_fields,
		definition=idx_def,
	)

	reindex_all_web_items()
	define_autocomplete_dictionary()

def to_search_field(field):
	if field == "tags":
		return TagField("tags", separator=",")

	return TextField(field)

@if_redisearch_loaded
def insert_item_to_index(website_item_doc):
	# Insert item to index
	key = get_cache_key(website_item_doc.name)
	cache = frappe.cache()
	web_item = create_web_item_map(website_item_doc)

	for k, v in web_item.items():
		super(RedisWrapper, cache).hset(make_key(key), k, v)

	insert_to_name_ac(website_item_doc.web_item_name, website_item_doc.name)

@if_redisearch_loaded
def insert_to_name_ac(web_name, doc_name):
	ac = AutoCompleter(make_key(WEBSITE_ITEM_NAME_AUTOCOMPLETE), conn=frappe.cache())
	ac.add_suggestions(Suggestion(web_name, payload=doc_name))

def create_web_item_map(website_item_doc):
	fields_to_index = get_fields_indexed()
	web_item = {}

	for f in fields_to_index:
		web_item[f] = website_item_doc.get(f) or ''

	return web_item

@if_redisearch_loaded
def update_index_for_item(website_item_doc):
	# Reinsert to Cache
	insert_item_to_index(website_item_doc)
	define_autocomplete_dictionary()

@if_redisearch_loaded
def delete_item_from_index(website_item_doc):
	cache = frappe.cache()
	key = get_cache_key(website_item_doc.name)

	try:
		cache.delete(key)
	except Exception:
		return False

	delete_from_ac_dict(website_item_doc)
	return True

@if_redisearch_loaded
def delete_from_ac_dict(website_item_doc):
	'''Removes this items's name from autocomplete dictionary'''
	cache = frappe.cache()
	name_ac = AutoCompleter(make_key(WEBSITE_ITEM_NAME_AUTOCOMPLETE), conn=cache)
	name_ac.delete(website_item_doc.web_item_name)

@if_redisearch_loaded
def define_autocomplete_dictionary():
	"""Creates an autocomplete search dictionary for `name`.
		Also creats autocomplete dictionary for `categories` if
		checked in E Commerce Settings"""

	cache = frappe.cache()
	name_ac = AutoCompleter(make_key(WEBSITE_ITEM_NAME_AUTOCOMPLETE), conn=cache)
	cat_ac = AutoCompleter(make_key(WEBSITE_ITEM_CATEGORY_AUTOCOMPLETE), conn=cache)

	ac_categories = frappe.db.get_single_value(
		'E Commerce Settings',
		'show_categories_in_search_autocomplete'
	)

	# Delete both autocomplete dicts
	try:
		cache.delete(make_key(WEBSITE_ITEM_NAME_AUTOCOMPLETE))
		cache.delete(make_key(WEBSITE_ITEM_CATEGORY_AUTOCOMPLETE))
	except Exception:
		return False

	items = frappe.get_all(
		'Website Item',
		fields=['web_item_name', 'item_group'],
		filters={"published": 1}
	)

	for item in items:
		name_ac.add_suggestions(Suggestion(item.web_item_name))
		if ac_categories and item.item_group:
			cat_ac.add_suggestions(Suggestion(item.item_group))

	return True

@if_redisearch_loaded
def reindex_all_web_items():
	items = frappe.get_all(
		'Website Item',
		fields=get_fields_indexed(),
		filters={"published": True}
	)

	cache = frappe.cache()
	for item in items:
		web_item = create_web_item_map(item)
		key = make_key(get_cache_key(item.name))

		for k, v in web_item.items():
			super(RedisWrapper, cache).hset(key, k, v)

def get_cache_key(name):
	name = frappe.scrub(name)
	return f"{WEBSITE_ITEM_KEY_PREFIX}{name}"

def get_fields_indexed():
	fields_to_index = frappe.db.get_single_value(
		'E Commerce Settings',
		'search_index_fields'
	)
	fields_to_index = fields_to_index.split(',') if fields_to_index else []

	mandatory_fields = ['name', 'web_item_name', 'route', 'thumbnail', 'ranking']
	fields_to_index = fields_to_index + mandatory_fields

	return fields_to_index

# TODO: Remove later
# # Figure out a way to run this at startup
define_autocomplete_dictionary()
create_website_items_index()
