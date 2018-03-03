
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
	print("verify_request", sig, frappe.get_request_header("X-Wc-Webhook-Signature"))
	if frappe.request.data and \
		frappe.get_request_header("X-Wc-Webhook-Signature") and \
		not sig == frappe.get_request_header("X-Wc-Webhook-Signature"):
			frappe.throw(_("Unverified Webhook Data"))
	frappe.set_user("Administrator")

@frappe.whitelist(allow_guest=True)
def order():

	verify_request()
	print(frappe.local.form_dict)
	# fd = frappe.local.form_dict

	if frappe.request.data:
		fd = json.loads(frappe.request.data)
	else:
		return "success"

	event = frappe.get_request_header("X-Wc-Webhook-Event")
	print(event*10)

	print("This is Actual Data: ")
	print(fd)

	if event == "created":
		print("Inside updated of order")

		raw_billing_data = fd.get("billing")
		customer_woo_com_email = raw_billing_data.get("email")

		try:
			search_customer = frappe.get_doc("Customer",{"woocommerce_email": customer_woo_com_email})
			# Edit
			link_customer_and_address(raw_billing_data,1)
		except frappe.DoesNotExistError as e:
			print("Error Found",e)
			# create
			link_customer_and_address(raw_billing_data,0)

		except Exception as e:
			print("THis is different Error",e)

		# if not search_customer:
		# 	# create
		# 	link_customer_and_address(raw_billing_data,0)
		# else:
		# 	#Edit existing
		# 	link_customer_and_address(raw_billing_data,1)


def link_customer_and_address(raw_billing_data,customer_status):

	if customer_status == 0:
		# create
		customer = frappe.new_doc("Customer")
		address = frappe.new_doc("Address")

	if customer_status == 1:
		# Edit
		customer_woo_com_email = raw_billing_data.get("email")
		customer = frappe.get_doc("Customer",{"woocommerce_email": customer_woo_com_email})
		old_name = customer.customer_name

	full_name = str(raw_billing_data.get("first_name"))+ " "+str(raw_billing_data.get("last_name"))
	customer.customer_name = full_name
	customer.woocommerce_email = str(raw_billing_data.get("email"))
	customer.save()
	frappe.db.commit()

	if customer_status == 1:
		frappe.rename_doc("Customer", old_name, full_name)
		address = frappe.get_doc("Address",{"woocommerce_email":customer_woo_com_email})
		customer = frappe.get_doc("Customer",{"woocommerce_email": customer_woo_com_email})

	address.address_line1 = raw_billing_data.get("address_1", "Not Provided")
	address.address_line2 = raw_billing_data.get("address_2", "Not Provided")
	address.city = raw_billing_data.get("city", "Not Provided")
	address.woocommerce_email = str(raw_billing_data.get("email"))
	address.address_type = "Shipping"
	address.country = frappe.get_value("Country", filters={"code":raw_billing_data.get("country", "IN").lower()})
	address.state =  raw_billing_data.get("state")
	address.pincode =  str(raw_billing_data.get("postcode"))
	address.phone = str(raw_billing_data.get("phone"))
	address.email_id = str(raw_billing_data.get("email"))

	address.append("links", {
		"link_doctype": "Customer",
		"link_name": customer.customer_name
	})

	address.save()
	frappe.db.commit()

	if customer_status == 1:

		address = frappe.get_doc("Address",{"woocommerce_email":customer_woo_com_email})
		old_address_title = address.name
		new_address_title = customer.customer_name+"-billing"
		address.address_title = customer.customer_name
		address.save()

		frappe.rename_doc("Address",old_address_title,new_address_title)

	frappe.db.commit()

