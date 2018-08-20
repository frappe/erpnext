from __future__ import unicode_literals
import frappe, requests, json
from frappe.utils import now
from frappe.frappeclient import FrappeClient
from frappe.desk.form.load import get_attachments

@frappe.whitelist()
def call_hub_method(method, params=None):
	connection = get_hub_connection()

	if type(params) == unicode:
		params = json.loads(params)

	params.update({
		'cmd': 'hub.hub.api.' + method
	})

	response = connection.post_request(params)
	return response

@frappe.whitelist()
def get_valid_items(search_value=''):
	items = frappe.get_list(
		'Item',
		fields=["*"],
		filters={
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

	valid_items = map(lambda x: prepare_item(x), valid_items)

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
		}).insert()

	try:
		hub_settings = frappe.get_doc('Hub Settings')
		item_sync_preprocess()
		hub_settings.sync()
	except Exception as e:
		frappe.db.set_value("Hub Settings", "Hub Settings", "sync_in_progress", 0)
		frappe.throw(e)

def item_sync_preprocess():
	hub_seller = frappe.db.get_value("Hub Settings", "Hub Settings", "company_email")

	response = call_hub_method('add_hub_seller_activity', {
		'hub_seller': hub_seller,
		'activity_details': json.dumps({
			'subject': 'Publishing items',
			'status': 'Success'
		})
	})

	if response:
		frappe.db.set_value("Hub Settings", "Hub Settings", "sync_in_progress", 1)
		return response
	else:
		frappe.throw('Unable to update remote activity')

def item_sync_postprocess(sync_details):
	hub_seller = frappe.db.get_value("Hub Settings", "Hub Settings", "company_email")

	response = call_hub_method('add_hub_seller_activity', {
		'hub_seller': hub_seller,
		'activity_details': json.dumps({
			'subject': 'Publishing items:' + sync_details['status'],
			'content': json.dumps(sync_details['stats'])
		})
	})

	if response:
		frappe.db.set_value('Hub Settings', 'Hub Settings', 'sync_in_progress', 0)
		frappe.db.set_value('Hub Settings', 'Hub Settings', 'last_sync_datetime', frappe.utils.now())
	else:
		frappe.throw('Unable to update remote activity')

def get_hub_connection():
	if frappe.db.exists('Data Migration Connector', 'Hub Connector'):
		hub_connector = frappe.get_doc('Data Migration Connector', 'Hub Connector')
		hub_connection = hub_connector.get_connection()
		return hub_connection.connection

	# read-only connection
	hub_connection = FrappeClient(frappe.conf.hub_url)
	return hub_connection
