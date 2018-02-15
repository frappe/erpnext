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
	print(sig, frappe.get_request_header("X-Wc-Webhook-Signature"))
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
	print(frappe.request.headers)
	print(frappe.request.headers.get("X-Wc-Webhook-Event"))
	print(frappe.request.headers.get("X-Wc-Webhook-Resource"))
	verify_request()
	print("yay!")

@frappe.whitelist(allow_guest=True)
def delete_coupon():
	pass

@frappe.whitelist(allow_guest=True)
def restore_coupon():
	pass

@frappe.whitelist(allow_guest=True)
def customer():
	verify_request()
	print(frappe.local.form_dict)
	fd = frappe.local.form_dict
	event = frappe.get_request_header("X-Wc-Webhook-Event")

	if event == "created":
		new_customer = frappe.new_doc("Customer")
		new_customer.customer_name = fd.get("first_name")+" "+fd.get("last_name")
		new_customer.Customer-woocommerce_id = fd.get("id")


		make_address = frappe.new_doc("Address")
		make_address.address_line1 = "None" if (fd.get("address_1") == None) else fd.get("address_1")
		make_address.address_line2 = "None" if (fd.get("address_2") == None) else fd.get("address_2")
		make_address.city = "None" if (fd.get("city") == None) else fd.get("city")
		make_address.country = fd.get("country")
		make_address.state = fd.get("state")
		make_address.pincode = fd.get("postcode")
		make_address.phone = fd.get("phone")
		make_address.email = fd.get("email")

		make_address.append("links", {
			"link_doctype": "Customer",
			"link_name": customer.customer_name
		})

		new_customer.save()
		make_address.save()

	elif event == "updated":
		pass
	elif event == "deleted":
		pass

	frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def product():
	print("hello"*1000)
	verify_request()
	print(frappe.local.form_dict)
	fd = frappe.local.form_dict
	event = frappe.get_request_header("X-Wc-Webhook-Event")

	if event == "created":
		item = frappe.new_doc("Item")
		item.item_name = fd.get("name")
		item.tem_code = fd.get("id")
		item.item_group = "Products"
		item.opening_stock = 0 if (fd.get("stock_quantity") == None) else fd.get("stock_quantity")
		item.save()

	elif event == "updated":
		item = frappe.get_doc({"doctype":"Item", "item_code":fd.get("id")})

	elif event == "restored":
		pass
	elif event == "deleted":
		pass

@frappe.whitelist(allow_guest=True)
def order():
	verify_request()
	print(frappe.local.form_dict)
	fd = frappe.local.form_dict
	event = frappe.get_request_header("X-Wc-Webhook-Event")
	if event == "created":
		new_sales_order = frappe.new_doc("Sales Order")
		new_sales_order.customer = fd.get("first_name")+" "+fd.get("last_name")
		created_date = fd.get("date_created").split("T")
		new_sales_order.transaction_date = created_date[0]
		new_sales_order.po_no = fd.get("id")
		new_sales_order.Sales Order-woocommerce_id = fd.get("id")
		# new_sales_order.append("taxes",{
		# 				"charge_type":"Actual",
		# 				"account_head": "VAT 5% - Woo",
		# 				"tax_amount": charge_amount,
		# 				"description": charge_type
		# 				})
		ordered_items = vin.get("line_items")
		for item in ordered_items:
			# write from here

	elif event == "updated":
		pass
	elif event == "restored":
		pass
	elif event == "deleted":
	pass