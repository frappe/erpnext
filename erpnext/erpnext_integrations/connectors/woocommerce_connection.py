
from __future__ import unicode_literals
import frappe, base64, hashlib, hmac, json
from frappe import _
import pdb
import requests
import json
from frappe.utils.background_jobs import enqueue
from fxnmrnth import get_site_name


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
	print("Starting WooCommerce")
	try:
		response = _order(*args, **kwargs)
		return response
	except Exception:
		order = json.loads(frappe.request.data)
		orderID = order['id'];
		orderLink = order['_links']['self'][0]['href']
		order_link_url = orderLink[0:orderLink.find("wp-json")] + "wp-admin/post.php?post=" + orderLink[orderLink.find("orders/")+7:] + "&action=edit"

		# Compose error message
		error_message = """Hi there, \n\nThere was an error pushing Order ID: <a href='{order_link_url}'> {orderID} </a>\n\n Nerd Stuff:\n\n {traceback} \n\n Request Data: \n {data})""".format(
			order_link_url=order_link_url, orderID=str(orderID),
			traceback=frappe.get_traceback(),
			data=json.loads(frappe.request.data).__str__()
		)

		# Write an error log
		frappe.log_error(error_message, "WooCommerce Error")

		# Send error messages to admin
		enqueue(
			recipients=["Mitch@RNLabs.com.au", "andy@fxmed.co.nz"],
			subject="WooCommerce Order Error",
			sender="Support@RNLabs.com.au",
			content=error_message, method=frappe.sendmail,
			queue='short', timeout=300, is_async=True
		)
		raise

def _order(*args, **kwargs):
	woocommerce_settings = frappe.get_doc("Woocommerce Settings")
	if frappe.flags.woocomm_test_order_data:
		order = frappe.flags.woocomm_test_order_data
		event = "created"
	elif frappe.request and frappe.request.data:
		#RE-ENABLE THIS AFTER TESTING IS COMPLETE
		#verify_request()
		#Remove next 1 lines after finished testing
		frappe.set_user(woocommerce_settings.creation_user)
		try:
			order = json.loads(frappe.request.data)
		except ValueError:
			#woocommerce returns 'webhook_id=value' for the first request which is not JSON
			order = frappe.request.data
		event = frappe.get_request_header("X-Wc-Webhook-Event")
	else:
		return "No request or data received!"

	if event == "created":
		userLink = order.get("_links")["customer"][0]['href']
		customer_detail = getCustomerDetails(userLink)

		new_invoice = create_sales_invoice(
			order, 
			customer_detail['username'], 
			customer_detail['shippingAddress'], 
			woocommerce_settings
		)
		return "Sales invoice created!"

def getCustomerDetails(customerLink):
	user = 'mitch'
	ERPNextApp = 'gXmf sL4w wtGb QJUX kIXI CDt4'
	token = base64.b64encode((user + ':' + ERPNextApp).encode("utf-8"))
	headers = {'Authorization': 'Basic ' + token.decode("utf-8")}
	response = requests.get(customerLink, headers=headers)
	json = response.json()
	returnDict = dict();  
	returnDict['shippingAddress'] = json['shipping'];
	returnDict['username'] = json['username'];
	return returnDict

def create_sales_invoice(order, customer_code, shipping_address, woocommerce_settings):
	#Set Basic Info
	new_sales_invoice = frappe.new_doc("Sales Invoice")
	new_sales_invoice.customer = customer_code
	new_sales_invoice.woocommerce_order = 1
	new_sales_invoice.po_no = order.get("id")
	new_sales_invoice.naming_series = frappe.get_meta("Sales Invoice").get_field("naming_series").options or ""
	new_sales_invoice.transaction_date = order.get("date_created").split("T")[0]

	if woocommerce_settings.company:
		new_sales_invoice.company = woocommerce_settings.company
		if woocommerce_settings.company == "RN Labs":
			new_sales_invoice.temporary_address = 1
			new_sales_invoice.order_type = "Practitioner Order"
			# Need to tell if it's practitioner order or patient order


	#Collect Shipping Information
	shippingName = shipping_address["first_name"] + " " +  shipping_address["last_name"]
	shippingLine1 = shipping_address["address_1"] + ", " + shipping_address["address_2"]
	shippingLine2 = shipping_address["city"] + ", " + shipping_address["state"] + ", " + shipping_address["postcode"] + ", " + shipping_address["country"]

	billing_address = order.get("billing")
	new_sales_invoice.temporary_delivery_address_line_1 = shippingName
	new_sales_invoice.temporary_delivery_address_line_2 = shippingLine1
	new_sales_invoice.temporary_delivery_address_line_3 = shippingLine2
	new_sales_invoice.temporary_delivery_address_line_4 = billing_address.get("phone")
	new_sales_invoice.temporary_delivery_address_line_5 = billing_address.get("email")

	# Add Items
	setItemsInSalesInvoice(customer_code, new_sales_invoice, woocommerce_settings, order)

	# Save 
	new_sales_invoice.flags.ignore_mandatory = True
	new_sales_invoice.save()

	# Need send email to CS to confirm and submit?
	orderLink = order['_links']['self'][0]['href']
	order_link_url = orderLink[0:orderLink.find("wp-json")] + "wp-admin/post.php?post=" + orderLink[orderLink.find("orders/")+7:] + "&action=edit"

	site_name = get_site_name()
	erpnext_url = "https://{site_name}/desk#Form/Sales%20Invoice/{invoice_id}".format(site_name=site_name, invoice_id=new_sales_invoice.name)
	draft_message = """
		Hi *{name}*, \n
		There is an order captured in ERPNext from online website {company}.
		- Online order number: {order_number}
		- Order status: {status}
		- Created date: {created_date}
		- Total amount: {total}
		- Total tax: {total_tax}
		- Customer note: {customer_note}
		- order URL: {url}

		## ERPNext Sales Invoice brief 
		- Customer code : {customer_code}
		- Title : {title}
		- Grand total : {base_grand_total}
		- Taxes and charges : {total_taxes_and_charges}
		- Sales invoice ID : {sales_invoice_id}
		- Purchase order : {po_no}
		- Invoice URL: {erpnext_url}
	""".format(
		name="Administrator",
		company=woocommerce_settings.company,
		order_number=order.get("id"),
		status=order.get("status"),
		created_date=order.get("date_created"),
		total=order.get("total"),
		total_tax=order.get("total_tax"),
		customer_note=order.get("customer_note"),
		url=order_link_url,
		customer_code= new_sales_invoice.customer,
		title= new_sales_invoice.title,
		base_grand_total= new_sales_invoice.base_grand_total,
		total_taxes_and_charges= new_sales_invoice.total_taxes_and_charges,
		sales_invoice_id= new_sales_invoice.name,
		po_no= new_sales_invoice.po_no,
		erpnext_url= erpnext_url,
	)
	enqueue(
		recipients=["andy@fxmed.co.nz"],
		subject="WooCommerce Order Draft",
		sender="Support@RNLabs.com.au",
		content=draft_message, method=frappe.sendmail,
		queue='short', as_markdown=True
	)
	

def setItemsInSalesInvoice(customer_code, new_sales_invoice, woocommerce_settings, order):
	company_abbr = frappe.db.get_value('Company', woocommerce_settings.company, 'abbr')

	SKU = ""
	for item in order.get("line_items"):
		SKU = item.get("sku")
		foundItem = frappe.get_doc("Item", {"name": SKU})
		price_list = frappe.get_doc('Customer', customer_code).default_price_list
		rate = frappe.db.get_list('Item Price', filters={'docstatus':0, 'selling': 1, 'buying': 0, 'price_list': price_list, 'item_code': SKU}, fields=['price_list_rate'])[0]
		new_sales_invoice.append("items",{
			"item_code": foundItem.item_code,
			"item_name": foundItem.item_name,
			"description": foundItem.item_name,
			"uom": woocommerce_settings.uom or _("Nos"),
			"qty": item.get("quantity"),
			"rate": rate['price_list_rate'],
			"warehouse": woocommerce_settings.warehouse or _("Stores - {0}").format(company_abbr)
		})

		itemTax = (rate['price_list_rate']*0.1) * item.get("quantity")
		addTaxDetails(new_sales_invoice, itemTax, "Ordered Item tax", woocommerce_settings.tax_account)

	if float(order.get("shipping_total")) > 0:
		addTaxDetails(new_sales_invoice, order.get("shipping_total"), "Shipping Total", woocommerce_settings.f_n_f_account)
	if float(order.get("shipping_tax")) > 0:
		addTaxDetails(new_sales_invoice, order.get("shipping_tax"), "Shipping Tax", woocommerce_settings.f_n_f_account)


def addTaxDetails(salesInvoice, price, desc, tax_account_head):
	salesInvoice.append("taxes", {
		"charge_type":"Actual",
		"account_head": tax_account_head,
		"tax_amount": price,
		"description": desc
	})