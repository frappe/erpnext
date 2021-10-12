from __future__ import unicode_literals

import base64
import hashlib
import hmac

import frappe
from frappe import _
from six.moves.urllib.parse import urlparse

from erpnext import get_default_company


def validate_webhooks_request(doctype,  hmac_key, secret_key='secret'):
	def innerfn(fn):
		settings = frappe.get_doc(doctype)

		if frappe.request and settings and settings.get(secret_key) and not frappe.flags.in_test:
			sig = base64.b64encode(
				hmac.new(
					settings.get(secret_key).encode('utf8'),
					frappe.request.data,
					hashlib.sha256
				).digest()
			)

			if frappe.request.data and \
				frappe.get_request_header(hmac_key) and \
				not sig == bytes(frappe.get_request_header(hmac_key).encode()):
					frappe.throw(_("Unverified Webhook Data"))
			frappe.set_user(settings.modified_by)

		return fn

	return innerfn

def get_webhook_address(connector_name, method, exclude_uri=False, force_https=False):
	endpoint = "erpnext.erpnext_integrations.connectors.{0}.{1}".format(connector_name, method)

	if exclude_uri:
		return endpoint

	try:
		url = frappe.request.url
	except RuntimeError:
		url = "http://localhost:8000"

	url_data = urlparse(url)
	scheme = "https" if force_https else url_data.scheme
	netloc = url_data.netloc

	server_url = f"{scheme}://{netloc}/api/method/{endpoint}"

	return server_url

def create_mode_of_payment(gateway, payment_type="General"):
	payment_gateway_account = frappe.db.get_value("Payment Gateway Account", {
			"payment_gateway": gateway
		}, ['payment_account'])

	mode_of_payment = frappe.db.exists("Mode of Payment", gateway)
	if not mode_of_payment and payment_gateway_account:
		mode_of_payment = frappe.get_doc({
			"doctype": "Mode of Payment",
			"mode_of_payment": gateway,
			"enabled": 1,
			"type": payment_type,
			"accounts": [{
				"doctype": "Mode of Payment Account",
				"company": get_default_company(),
				"default_account": payment_gateway_account
			}]
		})
		mode_of_payment.insert(ignore_permissions=True)

		return mode_of_payment
	elif mode_of_payment:
		return frappe.get_doc("Mode of Payment", mode_of_payment)

def get_tracking_url(carrier, tracking_number):
	# Return the formatted Tracking URL.
	tracking_url = ''
	url_reference = frappe.get_value('Parcel Service', carrier, 'url_reference')
	if url_reference:
		tracking_url = frappe.render_template(url_reference, {'tracking_number': tracking_number})
	return tracking_url
