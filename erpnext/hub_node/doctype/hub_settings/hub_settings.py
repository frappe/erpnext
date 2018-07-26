# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json

from frappe.model.document import Document
from frappe.utils import add_years, now, get_datetime, get_datetime_str
from frappe import _
from erpnext.utilities.product import get_price, get_qty_in_stock
from six import string_types

# hub_url = "https://hubmarket.org"
# hub_url = "http://159.89.175.122"
# hub_url = "http://erpnext.hub:8001"
hub_url = "http://hub.market:8000"

class OAuth2Session():
	def __init__(self, headers):
		self.headers = headers
	def get(self, url, params, headers, verify):
		res = requests.get(url, params=params, headers=self.headers, verify=verify)
		return res
	def post(self, url, data, verify):
		res = requests.post(url, data=data, headers=self.headers, verify=verify)
		return res
	def put(self, url, data, verify):
		res = requests.put(url, data=data, headers=self.headers, verify=verify)
		return res

class HubSetupError(frappe.ValidationError): pass

class HubSettings(Document):

	def validate(self):
		if self.publish_pricing and not self.selling_price_list:
			frappe.throw(_("Please select a Price List to publish pricing"))

	def get_hub_url(self):
		return hub_url

	def sync(self):
		"""Create and execute Data Migration Run for Hub Sync plan"""
		frappe.has_permission('Hub Settings', throw=True)

		doc = frappe.get_doc({
			'doctype': 'Data Migration Run',
			'data_migration_plan': 'Hub Sync',
			'data_migration_connector': 'Hub Connector',
		}).insert()

		self.sync_in_progress = 1
		doc.run()
		# self.sync_in_progress = 0

	def pre_reg(self):
		site_name = frappe.local.site + ':' + str(frappe.conf.webserver_port)
		protocol = 'http://'
		route = '/token'
		data = {
			'site_name': site_name,
			'protocol': protocol,
			'route': route
		}

		redirect_url = protocol + site_name + route
		post_url = hub_url + '/api/method/hub.hub.api.pre_reg'

		response = requests.post(post_url, data=data)
		response.raise_for_status()
		message = response.json().get('message')

		if message and message.get('client_id'):
			print("======CLIENT_ID======")
			print(message.get('client_id'))

			return {
				'client_id': message.get('client_id'),
				'redirect_uri': redirect_url
			}


	def register(self):
		""" Create a User on hub.erpnext.org and return username/password """
		data = {
			'profile': self.as_json()
		}
		post_url = hub_url + '/api/method/hub.hub.api.register'

		response = requests.post(post_url, data=data, headers = {'accept': 'application/json'})

		response.raise_for_status()

		if response.ok:
			message = response.json().get('message')
		else:
			frappe.throw(json.loads(response.text))

		return message.get('password') if message else None

	def unregister(self):
		""" Disable the User on hub.erpnext.org"""

		hub_connector = frappe.get_doc(
			'Data Migration Connector', 'Hub Connector')

		connection = hub_connector.get_connection()
		response_doc = connection.update('User', frappe._dict({'enabled': 0}), hub_connector.username)

		if response_doc['enabled'] == 0:
			self.enabled = 0
			self.save()

	def create_hub_connector(self, message):
		if frappe.db.exists('Data Migration Connector', 'Hub Connector'):
			hub_connector = frappe.get_doc('Data Migration Connector', 'Hub Connector')
			hub_connector.username = message['email']
			hub_connector.password = message['password']
			hub_connector.save()
			return

		frappe.get_doc({
			'doctype': 'Data Migration Connector',
			'connector_type': 'Frappe',
			'connector_name': 'Hub Connector',
			'hostname': hub_url,
			'username': message['email'],
			'password': message['password']
		}).insert()

def reset_hub_publishing_settings(last_sync_datetime = ""):
	doc = frappe.get_doc("Hub Settings", "Hub Settings")
	doc.reset_publishing_settings(last_sync_datetime)
	doc.in_callback = 1
	doc.save()

def reset_hub_settings(last_sync_datetime = ""):
	doc = frappe.get_doc("Hub Settings", "Hub Settings")
	doc.reset_publishing_settings(last_sync_datetime)
	doc.reset_enable()
	doc.in_callback = 1
	doc.save()
	frappe.msgprint(_("Successfully unregistered."))

@frappe.whitelist()
def sync():
	hub_settings = frappe.get_doc('Hub Settings')
	hub_settings.sync()

@frappe.whitelist()
def register_seller(**kwargs):
	settings = frappe.get_doc('Hub Settings')
	settings.update(kwargs)
	password = settings.register()

	print(password)

	# if password:
	# 	self.create_hub_connector(message)
	# 	self.registered = 1
	# 	self.save()
