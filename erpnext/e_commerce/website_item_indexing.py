# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
import redis

from redisearch import (
        Client, AutoCompleter, Query,
        Suggestion, IndexDefinition, 
        TextField, TagField,
        Document
	)

# GLOBAL CONSTANTS
WEBSITE_ITEM_INDEX = 'website_items_index'
WEBSITE_ITEM_KEY_PREFIX = 'website_item:'
WEBSITE_ITEM_NAME_AUTOCOMPLETE = 'website_items_name_dict'
WEBSITE_ITEM_CATEGORY_AUTOCOMPLETE = 'website_items_category_dict'

ALLOWED_INDEXABLE_FIELDS_SET = {
	'item_code',
	'item_name',
	'item_group',
	'brand',
	'description',
	'web_long_description'
}

def create_website_items_index():
	'''Creates Index Definition'''
	# CREATE index
	client = Client(WEBSITE_ITEM_INDEX, port=13000)

	# DROP if already exists
	try:
		client.drop_index()
	except:
		pass

	
	idx_def = IndexDefinition([WEBSITE_ITEM_KEY_PREFIX])

	# Based on e-commerce settings
	idx_fields = frappe.db.get_single_value(
		'E Commerce Settings', 
		'search_index_fields'
	).split(',')

	if 'web_item_name' in idx_fields:
		idx_fields.remove('web_item_name')
	
	idx_fields = list(map(to_search_field, idx_fields))

	client.create_index(
		[TextField("web_item_name", sortable=True)] + idx_fields,
		definition=idx_def
	)

	reindex_all_web_items()
	define_autocomplete_dictionary()

def to_search_field(field):
	if field == "tags":
		return TagField("tags", separator=",")

	return TextField(field)

def insert_item_to_index(website_item_doc):
	# Insert item to index
	key = get_cache_key(website_item_doc.name)
	r = redis.Redis("localhost", 13000)
	web_item = create_web_item_map(website_item_doc)
	r.hset(key, mapping=web_item)
	insert_to_name_ac(website_item_doc.web_item_name, website_item_doc.name)

def insert_to_name_ac(web_name, doc_name):
	ac = AutoCompleter(WEBSITE_ITEM_NAME_AUTOCOMPLETE, port=13000)
	ac.add_suggestions(Suggestion(web_name, payload=doc_name))

def create_web_item_map(website_item_doc):
	fields_to_index = get_fields_indexed()

	web_item = {}

	for f in fields_to_index:
		web_item[f] = website_item_doc.get(f) or ''

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
	"""Creates an autocomplete search dictionary for `name`.
	   Also creats autocomplete dictionary for `categories` if 
	   checked in E Commerce Settings"""

	r = redis.Redis("localhost", 13000)
	name_ac = AutoCompleter(WEBSITE_ITEM_NAME_AUTOCOMPLETE, port=13000)
	cat_ac = AutoCompleter(WEBSITE_ITEM_CATEGORY_AUTOCOMPLETE, port=13000)

	ac_categories = frappe.db.get_single_value(
		'E Commerce Settings', 
		'show_categories_in_search_autocomplete'
	)
	
	# Delete both autocomplete dicts
	try:
		r.delete(WEBSITE_ITEM_NAME_AUTOCOMPLETE)
		r.delete(WEBSITE_ITEM_CATEGORY_AUTOCOMPLETE)
	except:
		return False
	
	items = frappe.get_all(
		'Website Item', 
		fields=['web_item_name', 'item_group'], 
		filters={"published": True}
	)

	for item in items:
		name_ac.add_suggestions(Suggestion(item.web_item_name))
		if ac_categories and item.item_group:
			cat_ac.add_suggestions(Suggestion(item.item_group))

	return True

def reindex_all_web_items():
	items = frappe.get_all(
		'Website Item', 
		fields=get_fields_indexed(), 
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

def get_fields_indexed():
	fields_to_index = frappe.db.get_single_value(
		'E Commerce Settings', 
		'search_index_fields'
	).split(',')

	mandatory_fields = ['name', 'web_item_name', 'route', 'thumbnail']
	fields_to_index = fields_to_index + mandatory_fields

	return fields_to_index

# TODO: Remove later
# # Figure out a way to run this at startup
define_autocomplete_dictionary()
create_website_items_index()
