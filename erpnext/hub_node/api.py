from __future__ import unicode_literals

import frappe
import json
import io
import base64
import os
import requests

from frappe import _
from frappe.frappeclient import FrappeClient
from frappe.desk.form.load import get_attachments
from frappe.utils.file_manager import get_file_path
from six import string_types

@frappe.whitelist()
def register_seller(**kwargs):
	settings = frappe.get_single('Marketplace Settings')
	settings.update(kwargs)
	settings.users = []

	validate_registerer()
	message = settings.register()

	if message.get('email'):
		settings.registered = 1

		settings.append('users', {
			'user': frappe.session.user,
			'name': frappe.session.user,
			'username': kwargs.get('username'),
			'password': message.get('password')
		})

		user_emails = kwargs.get('users').strip()[:-1].split(', ')
		for email in user_emails:
			settings.append('users', {'user': email, 'name': email})

		settings.insert()

	return message

def validate_registerer():
	if frappe.session.user == 'Administrator':
		frappe.throw(_('Please login as another user to register on Marketplace'))

	if 'System Manager' not in frappe.get_roles():
		frappe.throw(_('Only users with System Manager role can register on Marketplace'), frappe.PermissionError)

@frappe.whitelist()
def call_hub_method(method, params=None):
	connection = get_hub_connection()

	if isinstance(params, string_types):
		params = json.loads(params)

	params.update({
		'cmd': 'hub.hub.api.' + method
	})

	response = connection.post_request(params)
	return response

def map_fields(items):
	field_mappings = get_field_mappings()
	table_fields = [d.fieldname for d in frappe.get_meta('Item').get_table_fields()]

	hub_seller = frappe.db.get_value('Marketplace Settings' , 'Marketplace Settings', 'company_email')

	for item in items:
		for fieldname in table_fields:
			item.pop(fieldname, None)

		for mapping in field_mappings:
			local_fieldname = mapping.get('local_fieldname')
			remote_fieldname = mapping.get('remote_fieldname')

			value = item.get(local_fieldname)
			item.pop(local_fieldname, None)
			item[remote_fieldname] = value

		item['doctype'] = 'Hub Item'
		item['hub_seller'] = hub_seller
		item.pop('attachments', None)

	return items

@frappe.whitelist()
def get_valid_items(search_value=''):
	items = frappe.get_list(
		'Item',
		fields=["*"],
		filters={
			'disabled': 0,
			'item_name': ['like', '%' + search_value + '%'],
			'publish_in_hub': 0
		},
		order_by="modified desc"
	)

	valid_items = filter(lambda x: x.image and x.description, items)

	def prepare_item(item):
		item.source_type = "local"
		item.attachments = get_attachments('Item', item.item_code)
		return item

	valid_items = map(prepare_item, valid_items)

	return valid_items

@frappe.whitelist()
def publish_selected_items(items_to_publish):
	items_to_publish = json.loads(items_to_publish)
	if not len(items_to_publish):
		frappe.throw('No items to publish')

	for item in items_to_publish:
		item_code = item.get('item_code')
		frappe.db.set_value('Item', item_code, 'publish_in_hub', 1)

		frappe.get_doc({
			'doctype': 'Hub Tracked Item',
			'item_code': item_code,
			'hub_category': item.get('hub_category'),
			'image_list': item.get('image_list')
		}).insert(ignore_if_duplicate=True)


	items = map_fields(items_to_publish)

	try:
		item_sync_preprocess(len(items))
		load_base64_image_from_items(items)

		# TODO: Publish Progress
		connection = get_hub_connection()
		connection.insert_many(items)

		item_sync_postprocess()
	except Exception as e:
		frappe.log_error(message=e, title='Hub Sync Error')

def item_sync_preprocess(intended_item_publish_count):
	response = call_hub_method('pre_items_publish', {
		'intended_item_publish_count': intended_item_publish_count
	})

	if response:
		frappe.db.set_value("Marketplace Settings", "Marketplace Settings", "sync_in_progress", 1)
		return response
	else:
		frappe.throw('Unable to update remote activity')

def item_sync_postprocess():
	response = call_hub_method('post_items_publish', {})
	if response:
		frappe.db.set_value('Marketplace Settings', 'Marketplace Settings', 'last_sync_datetime', frappe.utils.now())
	else:
		frappe.throw('Unable to update remote activity')

	frappe.db.set_value('Marketplace Settings', 'Marketplace Settings', 'sync_in_progress', 0)


def load_base64_image_from_items(items):
	for item in items:
		file_path = item['image']
		file_name = os.path.basename(file_path)
		base64content = None

		if file_path.startswith('http'):
			# fetch content and then base64 it
			url = file_path
			response = requests.get(url)
			base64content = base64.b64encode(response.content)
		else:
			# read file then base64 it
			file_path = os.path.abspath(get_file_path(file_path))
			with io.open(file_path, 'rb') as f:
				base64content = base64.b64encode(f.read())

		image_data = json.dumps({
			'file_name': file_name,
			'base64': base64content
		})

		item['image'] = image_data


def get_hub_connection():
	read_only = True

	if frappe.db.exists('Data Migration Connector', 'Hub Connector'):
		hub_connector = frappe.get_doc('Data Migration Connector', 'Hub Connector')

		# full rights to user who registered as hub_seller
		if hub_connector.username == frappe.session.user:
			read_only = False

		if not read_only:
			hub_connection = hub_connector.get_connection()
			return hub_connection.connection

	# read-only connection
	if read_only:
		marketplace_url = frappe.db.get_single_value('Marketplace Settings', 'marketplace_url')
		hub_connection = FrappeClient(marketplace_url)
		return hub_connection

def get_field_mappings():
	return []
