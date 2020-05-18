
from __future__ import unicode_literals
import frappe, base64, hashlib, hmac, json
from frappe import _
import pdb

def verify_request():
	woocommerce_settings = frappe.get_doc("Woocommerce Settings")
	sig = base64.b64encode(
		hmac.new(
			woocommerce_settings.secret.encode('utf8'),
			frappe.request.data,
			hashlib.sha256
		).digest()
	)

	if frappe.request.data and \
		frappe.get_request_header("X-Wc-Webhook-Signature") and \
		not sig == bytes(frappe.get_request_header("X-Wc-Webhook-Signature").encode()):
			frappe.throw(_("Unverified Webhook Data"))
	frappe.set_user(woocommerce_settings.creation_user)

@frappe.whitelist(allow_guest=True)
def order(*args, **kwargs):
	try:
		response = _order(*args, **kwargs)
		return response
	except Exception:
		error_message = frappe.get_traceback()+"\n\n Request Data: \n"+json.loads(frappe.request.data).__str__()
		frappe.log_error(error_message, "WooCommerce Error")
		raise

def _order(*args, **kwargs):
	woocommerce_settings = frappe.get_doc("Woocommerce Settings")
	if frappe.flags.woocomm_test_order_data:
		order = frappe.flags.woocomm_test_order_data
		event = "created"
	elif frappe.request and frappe.request.data:
		verify_request()
		print('Second')
		try:
			order = json.loads(frappe.request.data)
		except ValueError:
			#woocommerce returns 'webhook_id=value' for the first request which is not JSON
			order = frappe.request.data
		event = frappe.get_request_header("X-Wc-Webhook-Event")
	else:
		return "success"

	if event == "created":
		raw_billing_data = order.get("billing")
		customer_name = raw_billing_data.get("first_name") + " " + raw_billing_data.get("last_name")

		metaDataList = order.get("meta_data")
		customerCode = ''
		for metaData in metaDataList:
			if metaData['key'] == "customer_code" or metaData['key'] == "user_practitioner":
				customerCode = metaData['value']

		if not customerCode:
			frappe.throw("Empty customer code. Data: " + json.loads(order).__str__())
		else:
			create_sales_invoice(order, customerCode, woocommerce_settings)
			return "Sales invoice created!"	

def create_sales_invoice(order, customerCode, woocommerce_settings):
	new_sales_invoice = frappe.new_doc("Sales Invoice")

	new_sales_invoice.customer = customerCode
	new_sales_invoice.woocommerce_order = 1
	new_sales_invoice.po_no = new_sales_invoice.woocommerce_id = order.get("id")
	new_sales_invoice.naming_series = "ACC-SINV-.YYYY.-"

	# For Now - Use Primary Shipping Address - Maybe this will auto fill?
	# addressSQL = frappe.db.sql("""SELECT 
	# 	a.name,
	# 	a.address_line1,
	# 	a.address_line2,
	# 	a.city,
	# 	a.county,
	# 	a.state,
	# 	a.pincode
	# FROM
	# 	`tabAddress` a
	# WHERE
	# 	a.name IN (
	# SELECT 
	# 	dl.parent
	# FROM
	# 	`tabDynamic Link` dl
	# INNER JOIN
	# 	`tabCustomer` c
	# ON
	# 	c.name = dl.link_name AND
	# 	c.name = '""" + customerCode + """' AND
	# 	dl.link_doctype = "Customer" AND
	# 	dl.parenttype = "Address")
	# AND
	# 	a.is_shipping_address = 1
	# AND 
	# 	a.disabled = 0""")
	# pdb.set_trace()
	# address = frappe.get_doc("Address", addressSQL[0][0])


	#Collect Shipping Information
	# shippingAddress = order.get("shipping")
	# shippingName = shippingAddress.get("first_name") + " " +  shippingAddress.get("last_name")
	# shippingLine1 = shippingAddress.get("address_1") + ", " + shippingAddress.get("address_2")
	# shippingLine2 = shippingAddress.get("city") + ", " + shippingAddress.get("state") + ", " + shippingAddress.get("postcode") + ", " + shippingAddress.get("country")
	# billingAddress = order.get("billing")
	# billingPhone = billingAddress.get("phone")
	# billingEmail = billingAddress.get("email")
	# new_sales_invoice.temporary_delivery_address_line_1 = shippingName
	# new_sales_invoice.temporary_delivery_address_line_2 = shippingLine1
	# new_sales_invoice.temporary_delivery_address_line_3 = shippingLine2
	# new_sales_invoice.temporary_delivery_address_line_4 = billingPhone
	# new_sales_invoice.temporary_delivery_address_line_5 = billingEmail
	
	date_created = order.get("date_created").split("T")[0]
	new_sales_invoice.transaction_date = date_created

	delivery_after = woocommerce_settings.delivery_after_days or 7
	new_sales_invoice.delivery_date = frappe.utils.add_days(date_created, delivery_after)

	new_sales_invoice.company = woocommerce_settings.company

	setItemsInSalesInvoice(customerCode, new_sales_invoice, woocommerce_settings, order)
	new_sales_invoice.flags.ignore_mandatory = True
	new_sales_invoice.insert()
	new_sales_invoice.save()

def setItemsInSalesInvoice(customerCode, new_sales_invoice, woocommerce_settings, order):
	company_abbr = frappe.db.get_value('Company', woocommerce_settings.company, 'abbr')

	SKU = ""
	for item in order.get("line_items"):
		SKU = item.get("sku")
		foundItem = frappe.get_doc("Item", {"name": SKU})
		price_list = frappe.get_doc('Customer', customerCode).default_price_list
		rate = frappe.get_list('Item Price', filters={'docstatus':0, 'selling': 1, 'buying': 0, 'price_list': price_list, 'item_code': SKU}, fields=['price_list_rate'])[0]

		pdb.set_trace()
		new_sales_invoice.append("items",{
			"item_code": foundItem.item_code,
			"item_name": foundItem.item_name,
			"description": foundItem.item_name,
			"delivery_date": new_sales_invoice.delivery_date,
			"uom": woocommerce_settings.uom or _("Nos"),
			"qty": item.get("quantity"),
			"rate": rate.price_list_rate,
			"warehouse": woocommerce_settings.warehouse or _("Stores - {0}").format(company_abbr)
			})

		addTaxDetails(new_sales_invoice, itemTax, "Ordered Item tax", woocommerce_settings.tax_account)

	# shipping_details = order.get("shipping_lines") # used for detailed order

	addTaxDetails(new_sales_invoice, order.get("shipping_tax"), "Shipping Tax", woocommerce_settings.f_n_f_account)
	addTaxDetails(new_sales_invoice, order.get("shipping_total"), "Shipping Total", woocommerce_settings.f_n_f_account)

def addTaxDetails(salesInvoice, price, desc, tax_account_head):
	salesInvoice.append("taxes", {
		"charge_type":"Actual",
		"account_head": tax_account_head,
		"tax_amount": price,
		"description": desc
	})