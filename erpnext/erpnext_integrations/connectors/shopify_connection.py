from __future__ import unicode_literals
import frappe, json
from frappe import _
import base64, hashlib, hmac

def validate_webhooks_request():
	def innerfn(fn):
		shopify_settings = frappe.get_doc("Shopify Settings")

		sig = base64.b64encode(
			hmac.new(
				'8a5b96e2f29d409380fe9148bdb92b01'.encode('utf8'),
				frappe.request.data,
				hashlib.sha256
			).digest()
		)

		if frappe.request.data and \
			frappe.get_request_header("X-Shopify-Hmac-Sha256") and \
			not sig == bytes(frappe.get_request_header("X-Shopify-Hmac-Sha256").encode()):
				frappe.throw(_("Unverified Webhook Data"))
		
		return fn

	return innerfn

@frappe.whitelist(allow_guest=True)
@validate_webhooks_request()
def order():
	print(json.loads(frappe.request.data))
