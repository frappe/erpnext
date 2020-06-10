from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('shopping_cart', 'doctype', 'Shopping Cart Settings')
	frappe.reload_doc('accounts', 'doctype', 'Payment Gateway Account')
	frappe.reload_doc('shopping_cart', 'doctype', 'Shopping Cart Payment Gateway')

	cart_settings = frappe.get_single("Shopping Cart Settings")

	if cart_settings.get("payment_gateway_account"):
		payment_gateway = frappe.db.get_value("Payment Gateway Account", cart_settings.get("payment_gateway_account"), "payment_gateway")

		default_gateway = {
			"payment_gateway_account": cart_settings.payment_gateway_account,
			"payment_gateway": payment_gateway,
			"label": payment_gateway,
			"is_default": 1
		}

		cart_settings.append("gateways", default_gateway)
		cart_settings.save()
