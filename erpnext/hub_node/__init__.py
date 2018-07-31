# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json
from frappe.utils import now, nowdate, cint
from frappe.utils.nestedset import get_root_of
from frappe.frappeclient import FrappeClient
from frappe.contacts.doctype.contact.contact import get_default_contact

@frappe.whitelist()
def enable_hub():
	hub_settings = frappe.get_doc('Hub Settings')
	hub_settings.register()
	frappe.db.commit()
	return hub_settings

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


#### LOCAL ITEMS
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

	def attach_source_type(item):
		item.source_type = "local"
		return item

	valid_items = map(lambda x: attach_source_type(x), valid_items)
	return valid_items

@frappe.whitelist()
def publish_selected_items(items_to_publish):
	items_to_publish = json.loads(items_to_publish)
	if not len(items_to_publish):
		return

	for item_code in items_to_publish:
		frappe.db.set_value('Item', item_code, 'publish_in_hub', 1)

	try:
		hub_settings = frappe.get_doc('Hub Settings')
		item_sync_preprocess()
		hub_settings.sync()
	except Exception as e:
		frappe.db.set_value("Hub Settings", "Hub Settings", "sync_in_progress", 0)
		frappe.throw(e)

def item_sync_preprocess():
	# Call Hub to make a new activity
	# and return an activity ID
	# that will be used as the remote ID for the Migration Run

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

@frappe.whitelist()
def get_item_favourites(start=0, limit=20, fields=["*"], order_by=None):
	doctype = 'Hub Item'
	hub_settings = frappe.get_doc('Hub Settings')
	item_names_str = hub_settings.get('custom_data') or '[]'
	item_names = json.loads(item_names_str)
	filters = json.dumps({
		'hub_item_code': ['in', item_names]
	})
	return get_list(doctype, start, limit, fields, filters, order_by)

@frappe.whitelist()
def update_wishlist_item(item_name, remove=0):
	remove = int(remove)
	hub_settings = frappe.get_doc('Hub Settings')
	data = hub_settings.get('custom_data')
	if not data or not json.loads(data):
		data = '[]'
		hub_settings.custom_data = data
		hub_settings.save()

	item_names_str = data
	item_names = json.loads(item_names_str)
	if not remove and item_name not in item_names:
		item_names.append(item_name)
	if remove and item_name in item_names:
		item_names.remove(item_name)

	item_names_str = json.dumps(item_names)

	hub_settings.custom_data = item_names_str
	hub_settings.save()


@frappe.whitelist()
def update_category(hub_item_code, category):
	connection = get_hub_connection()

	# args = frappe._dict(dict(
	# 	doctype='Hub Category',
	# 	hub_category_name=category
	# ))
	# response = connection.insert('Hub Category', args)

	response = connection.update('Hub Item', frappe._dict(dict(
		doctype='Hub Item',
		hub_category = category
	)), hub_item_code)

	return response

def get_hub_connection():
	if frappe.db.exists('Data Migration Connector', 'Hub Connector'):
		hub_connector = frappe.get_doc('Data Migration Connector', 'Hub Connector')
		hub_connection = hub_connector.get_connection()
		return hub_connection.connection

	# read-only connection
	hub_connection = FrappeClient(frappe.conf.hub_url)
	return hub_connection

def make_opportunity(buyer_name, email_id):
	buyer_name = "HUB-" + buyer_name

	if not frappe.db.exists('Lead', {'email_id': email_id}):
		lead = frappe.new_doc("Lead")
		lead.lead_name = buyer_name
		lead.email_id = email_id
		lead.save(ignore_permissions=True)

	o = frappe.new_doc("Opportunity")
	o.enquiry_from = "Lead"
	o.lead = frappe.get_all("Lead", filters={"email_id": email_id}, fields = ["name"])[0]["name"]
	o.save(ignore_permissions=True)

@frappe.whitelist()
def make_rfq_and_send_opportunity(item, supplier):
	supplier = make_supplier(supplier)
	contact = make_contact(supplier)
	item = make_item(item)
	rfq = make_rfq(item, supplier, contact)
	status = send_opportunity(contact)

	return {
		'rfq': rfq,
		'hub_document_created': status
	}

def make_supplier(supplier):
	# make supplier if not already exists
	supplier = frappe._dict(json.loads(supplier))

	if not frappe.db.exists('Supplier', {'supplier_name': supplier.supplier_name}):
		supplier_doc = frappe.get_doc({
			'doctype': 'Supplier',
			'supplier_name': supplier.supplier_name,
			'supplier_group': supplier.supplier_group,
			'supplier_email': supplier.supplier_email
		}).insert()
	else:
		supplier_doc = frappe.get_doc('Supplier', supplier.supplier_name)

	return supplier_doc

def make_contact(supplier):
	contact_name = get_default_contact('Supplier', supplier.supplier_name)
	# make contact if not already exists
	if not contact_name:
		contact = frappe.get_doc({
			'doctype': 'Contact',
			'first_name': supplier.supplier_name,
			'email_id': supplier.supplier_email,
			'is_primary_contact': 1,
			'links': [
				{'link_doctype': 'Supplier', 'link_name': supplier.supplier_name}
			]
		}).insert()
	else:
		contact = frappe.get_doc('Contact', contact_name)

	return contact

def make_item(item):
	# make item if not already exists
	item = frappe._dict(json.loads(item))

	if not frappe.db.exists('Item', {'item_code': item.item_code}):
		item_doc = frappe.get_doc({
			'doctype': 'Item',
			'item_code': item.item_code,
			'item_group': item.item_group,
			'is_item_from_hub': 1
		}).insert()
	else:
		item_doc = frappe.get_doc('Item', item.item_code)

	return item_doc

def make_rfq(item, supplier, contact):
	# make rfq
	rfq = frappe.get_doc({
		'doctype': 'Request for Quotation',
		'transaction_date': nowdate(),
		'status': 'Draft',
		'company': frappe.db.get_single_value('Hub Settings', 'company'),
		'message_for_supplier': 'Please supply the specified items at the best possible rates',
		'suppliers': [
			{ 'supplier': supplier.name, 'contact': contact.name }
		],
		'items': [
			{
				'item_code': item.item_code,
				'qty': 1,
				'schedule_date': nowdate(),
				'warehouse': item.default_warehouse or get_root_of("Warehouse"),
				'description': item.description,
				'uom': item.stock_uom
			}
		]
	}).insert()

	rfq.save()
	rfq.submit()
	return rfq

def send_opportunity(contact):
	# Make Hub Message on Hub with lead data
	doc = {
		'doctype': 'Lead',
		'lead_name': frappe.db.get_single_value('Hub Settings', 'company'),
		'email_id': frappe.db.get_single_value('Hub Settings', 'user')
	}

	args = frappe._dict(dict(
		doctype='Hub Message',
		reference_doctype='Lead',
		data=json.dumps(doc),
		user=contact.email_id
	))

	connection = get_hub_connection()
	response = connection.insert('Hub Message', args)

	return response.ok
