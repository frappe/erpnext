import frappe
from frappe import _
import base64, hashlib, hmac
from six.moves.urllib.parse import urlparse

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

def get_webhook_address(connector_name, method, exclude_uri=False):
	endpoint = "erpnext.erpnext_integrations.connectors.{0}.{1}".format(connector_name, method)

	if exclude_uri:
		return endpoint

	try:
		url = frappe.request.url
	except RuntimeError:
		url = "http://localhost:8000"

	server_url = '{uri.scheme}://{uri.netloc}/api/method/{endpoint}'.format(uri=urlparse(url), endpoint=endpoint)

	return server_url