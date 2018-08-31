# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, requests, json, time

from frappe.model.document import Document
from frappe.utils import add_years, now, get_datetime, get_datetime_str
from frappe import _
from erpnext.utilities.product import get_price, get_qty_in_stock
from six import string_types

class MarketplaceSettings(Document):

	def validate(self):
		self.site_name = frappe.utils.get_url()

	def get_marketplace_url(self):
		return self.marketplace_url

	def register(self):
		""" Create a User on hub.erpnext.org and return username/password """

		if frappe.session.user == 'Administrator':
			frappe.throw(_('Please login as another user to register on Marketplace'))

		if 'System Manager' not in frappe.get_roles():
			frappe.throw(_('Only users with System Manager role can register on Marketplace'), frappe.PermissionError)

		self.site_name = frappe.utils.get_url()

		data = {
			'profile': self.as_json()
		}
		post_url = self.get_marketplace_url() + '/api/method/hub.hub.api.register'

		response = requests.post(post_url, data=data, headers = {'accept': 'application/json'})

		response.raise_for_status()

		if response.ok:
			message = response.json().get('message')
		else:
			frappe.throw(json.loads(response.text))

		if message.get('email'):
			self.update_session_user_password(message)
			self.registered = 1
			self.save()

		return message or None

	# def unregister(self):
	# 	""" Disable the User on hub.erpnext.org"""

	# 	hub_connector = frappe.get_doc(
	# 		'Data Migration Connector', 'Hub Connector')

	# 	connection = hub_connector.get_connection()
	# 	response_doc = connection.update('User', frappe._dict({'enabled': 0}), hub_connector.username)

	# 	if response_doc['enabled'] == 0:
	# 		self.enabled = 0
	# 		self.save()

	def update_session_user_password(self, message):
		# TODO: Update child table session user password
		pass

	def create_hub_connector(self, message):
		if frappe.db.exists('Data Migration Connector', 'Hub Connector'):
			hub_connector = frappe.get_doc('Data Migration Connector', 'Hub Connector')
			hub_connector.hostname = self.get_marketplace_url()
			hub_connector.username = message['email']
			hub_connector.password = message['password']
			hub_connector.save()
			return

		frappe.get_doc({
			'doctype': 'Data Migration Connector',
			'connector_type': 'Frappe',
			'connector_name': 'Hub Connector',
			'hostname': self.get_marketplace_url(),
			'username': message['email'],
			'password': message['password']
		}).insert()

def reset_hub_publishing_settings(last_sync_datetime = ""):
	doc = frappe.get_doc("Marketplace Settings", "Marketplace Settings")
	doc.reset_publishing_settings(last_sync_datetime)
	doc.in_callback = 1
	doc.save()

def reset_hub_settings(last_sync_datetime = ""):
	doc = frappe.get_doc("Marketplace Settings", "Marketplace Settings")
	doc.reset_publishing_settings(last_sync_datetime)
	doc.reset_enable()
	doc.in_callback = 1
	doc.save()
	frappe.msgprint(_("Successfully unregistered."))

@frappe.whitelist()
def register_seller(**kwargs):
	settings = frappe.get_doc('Marketplace Settings')
	user_emails = kwargs.get('users').strip()[:-1].split(', ')

	users = []

	for user_email in user_emails:
		users.append({
			"user": user_email
		})

	users.insert(0, {
		"user": frappe.session.user,
		"hub_username": kwargs.get('username')
	})

	kwargs['users'] = users
	settings.update(kwargs)

	settings.save()

	message = settings.register()
	return message.get('email')
