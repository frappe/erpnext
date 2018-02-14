# see license.txt

from __future__ import unicode_literals
import frappe, base64, hashlib, hmac, json
from frappe import _

def verify_request():
	woocommerce_settings = frappe.get_doc("Woocommerce Settings")
	sig = base64.b64encode(
		hmac.new(
			woocommerce_settings.secret.encode(),
			str(frappe.request.data),
			hashlib.sha256
		).digest()
	)
	if frappe.request.data and \
		frappe.get_request_header("X-Wc-Webhook-Signature") and \
		not sig == frappe.get_request_header("X-Wc-Webhook-Signature"):
			frappe.throw(_("Unverified Webhook Data"))

@frappe.whitelist(allow_guest=True)
def create_coupon():
	verify_request()
	print("yay!")

@frappe.whitelist(allow_guest=True)
def update_coupon():
	pass

@frappe.whitelist(allow_guest=True)
def delete_coupon():
	pass

@frappe.whitelist(allow_guest=True)
def restore_coupon():
	pass

@frappe.whitelist(allow_guest=True)
def create_customer():
	pass

@frappe.whitelist(allow_guest=True)
def update_customer():
	pass

@frappe.whitelist(allow_guest=True)
def delete_customer():
	pass

@frappe.whitelist(allow_guest=True)
def create_product():
	pass

@frappe.whitelist(allow_guest=True)
def update_product():
	pass

@frappe.whitelist(allow_guest=True)
def delete_product():
	pass

@frappe.whitelist(allow_guest=True)
def restore_product():
	pass

@frappe.whitelist(allow_guest=True)
def create_order():
	pass

@frappe.whitelist(allow_guest=True)
def update_order():
	pass

@frappe.whitelist(allow_guest=True)
def delete_order():
	pass

@frappe.whitelist(allow_guest=True)
def restore_order():
	pass
