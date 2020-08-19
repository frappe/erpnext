
from __future__ import unicode_literals
import frappe, base64, hashlib, hmac, json
from frappe import _
import pdb
import requests
from frappe.utils.background_jobs import enqueue
from fxnmrnth import get_site_name
from frappe.desk.doctype.tag.tag import DocTags


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
			# print("sig" + sig.decode("utf-8"))
			frappe.throw(_("Unverified Webhook Data"))

def log_integration_request(order=None, invoice_doc=None, status=None, data=None, output=None, error=None, reference_doctype=None, reference_docname=None, woocommerce_settings=None):
	doc_dict = frappe._dict(
		doctype="Integration Request",
		integration_type="Remote",
		integration_request_service="WooCommerce",
		status=status,
		data=data,
		output=output,
		error=error,
		reference_id_=reference_docname
	)
	integration_request_doc = frappe.get_doc(doc_dict)
	integration_request_doc.insert(ignore_permissions=True)
	frappe.db.commit()

	if invoice_doc:
		# send email as well to 4 people
		order_link = order['_links']['self'][0]['href']
		order_edit_link = order_link[0:order_link.find("wp-json")] + "wp-admin/post.php?post=" + order_link[order_link.find("orders/")+7:] + "&action=edit"

		site_name = get_site_name()
		erpnext_url = "https://{site_name}/desk#Form/Sales%20Invoice/{invoice_id}".format(site_name=site_name, invoice_id=invoice_doc.name)
		draft_message = """
			Hi *{name}*, \n
			There is an order captured in ERPNext from online website - {company}.

			## WooCommerce Order detail
			- Online order number: {order_number}
			- Order status: {status}
			- Created date: {created_date}
			- Total amount: ${total}
			- Total tax: ${total_tax}
			- Customer note: {customer_note}
			- order URL: {url}

			## ERPNext Sales Invoice brief 
			- Purchase order : {po_no}
			- Customer code : {customer_code}
			- Title : {title}
			- Total amount : ${base_grand_total} (Included taxes and charges: ${total_taxes_and_charges})
			- Invoice URL: {erpnext_url}
		""".format(
			name="All",
			company=woocommerce_settings.company,
			order_number=order.get("id"),
			status=order.get("status"),
			created_date=order.get("date_created"),
			total=order.get("total"),
			total_tax=order.get("total_tax"),
			customer_note=order.get("customer_note"),
			url=order_edit_link,
			customer_code= invoice_doc.customer,
			title= invoice_doc.title,
			base_grand_total= invoice_doc.base_grand_total,
			total_taxes_and_charges= invoice_doc.total_taxes_and_charges,
			sales_invoice_id= invoice_doc.name,
			po_no= invoice_doc.po_no,
			erpnext_url= erpnext_url,
		)

		cc = []
		if site_name == "erpnext.rnlabs.com.au" or site_name == "erpnext.therahealth.com.au":
			cc = ["Tiana@rnlabs.com.au", "testkits@rnlabs.com.au", "andy@fxmed.co.nz"]

		enqueue(
			recipients=["Mitch@RNLabs.com.au"],
			subject="WooCommerce Order Draft",
			sender="Support@RNLabs.com.au",
			content=draft_message, method=frappe.sendmail,
			queue='short', as_markdown=True,
			expose_recipients="footer",
			cc=cc
		)


@frappe.whitelist(allow_guest=True)
def order(*args, **kwargs):
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
			traceback="<pre>" + frappe.get_traceback() + "</pre>",
			data=json.dumps(order, indent=4)
		)

		woocommerce_settings = frappe.get_doc("Woocommerce Settings")
		# Create a intergration request
		log_integration_request(order=order, invoice_doc=None,status="Failed", data=json.dumps(order, indent=4), output=order_link_url, error="<pre>" + frappe.get_traceback() + "</pre>", woocommerce_settings=woocommerce_settings)


		# Write an error log
		frappe.log_error(error_message, "WooCommerce Error")

		# Send error messages to admins
		enqueue(
			recipients=["Mitch@RNLabs.com.au", "andy@fxmed.co.nz"],
			subject="WooCommerce Order Error",
			sender="Support@RNLabs.com.au",
			content=error_message, method=frappe.sendmail,
			queue='short', is_async=True, as_markdown=True,
			expose_recipients="footer"
		)
		raise

def _order(*args, **kwargs):
	woocommerce_settings = frappe.get_doc("Woocommerce Settings")
	frappe.set_user(woocommerce_settings.creation_user)
	if frappe.request and frappe.request.data:
		# verify_request()
		try:
			order = json.loads(frappe.request.data)
		except ValueError:
			#woocommerce returns 'webhook_id=value' for the first request which is not JSON
			order = frappe.request.data
		event = frappe.get_request_header("X-Wc-Webhook-Event")
	else:
		return "success"

	if event == "created":
		# Get basic data from order
		customer_id = order.get('customer_id')
		meta_data = order.get('meta_data')
		billing = order.get('billing')


		# link customer and address
		patient_name = ""
		if customer_id == 0: # this is guest login, a patient under a practitioner
			for meta in meta_data:
				if meta["key"] == "user_practitioner":
					if "-" in meta["value"]:
						end_index = meta["value"].find('-')
						customer_code = meta["value"][0:end_index]
					else:
						customer_code = meta["value"]
				elif meta["key"] == "practitioner_name":
					practitioner_name = meta["value"]
				elif meta["key"] == "delivery_option":
					delivery_option = meta["value"]
				elif meta["key"] == "_nab_reference_id":
					nab_reference_id = meta["value"]
				elif meta["key"] == "pos_practitioner":
					customer_id = meta["value"]
				elif meta["key"] == "pos_patient":
					patient_name = meta["value"]
				else:
					pass

			if not customer_code :
				frappe.throw("Check order id {} in WP, cannot find user_practitioner".format(order.get('id')))
			# For patient order, we need to get shipping address in the order itself
			if frappe.db.exists("Customer", customer_code):
				customer_doc = frappe.get_doc("Customer", customer_code)
				if not patient_name:
					patient_name = billing.get('first_name') + ", " + billing.get('last_name')
				street = billing.get('address_1') + " " + billing.get('address_2')
				city_postcode_country = billing.get('city') + ", " + billing.get('state') + ", " + billing.get('postcode') + ", " + billing.get('country')
				phone = billing.get('phone')
				email = billing.get('email')

				# create sales invoice
				temp_address = {
					"temporary_address": 1,
					"temporary_delivery_address_line_1": patient_name,
					"temporary_delivery_address_line_2": street,
					"temporary_delivery_address_line_3": city_postcode_country,
					"temporary_delivery_address_line_4": phone,
					"temporary_delivery_address_line_5": email,
				}
				new_invoice = create_sales_invoice(order, customer_code, "Pay before Dispatch", woocommerce_settings, order_type= "Patient Order", temp_address=temp_address, delivery_option=delivery_option)
			else:
				frappe.throw("Customer {} not exits!".format(customer_code))

		else: # customer_id != 0
			# this is a user login, a practitioner
			customer_code = ""
			for meta in meta_data:
				if meta["key"] == "user_practitioner":
					customer_code = meta["value"]
					break

			if not customer_code:
				frappe.throw("WP Customer id {} don't have a customer code in ERPNext!".format(customer_id))
			# For practitioner order, we just need to get the primary address as shipping address
			if frappe.db.exists("Customer", customer_code):
				customer_doc = frappe.get_doc("Customer", customer_code)
				payment_category = customer_doc.payment_category
				if woocommerce_settings.company == "RN Labs":
					order_type = "Practitioner Order"
				# we don't need to find the primary address as it will auto load when you open the draft invoice

				# Create sales invoice
				new_invoice = create_sales_invoice(order, customer_code, payment_category, woocommerce_settings, order_type=order_type, temp_address=None, delivery_option=None)

			else:
				frappe.throw("Customer {} not exits!".format(customer_code))

		# Create a intergration request
		log_integration_request(order=order, invoice_doc=new_invoice, status="Completed", data=json.dumps(order), reference_doctype="Sales Invoice", reference_docname=new_invoice.name, woocommerce_settings=woocommerce_settings)


		return "Sales invoice: {} created!".format(new_invoice.name)

def create_sales_invoice(order, customer_code, payment_category,  woocommerce_settings, order_type=None, temp_address=None, delivery_option=None):
	#Set Basic Info
	date_created = order.get("date_created").split("T")[0]
	customer_note = order.get('customer_note')
	invoice_dict = {
		"doctype": "Sales Invoice",
		"customer": customer_code,
		"woocommerce_order": 1,
		"po_no": order.get("id"),
		"naming_series": frappe.get_meta("Sales Invoice").get_field("naming_series").options or "",
		"transaction_date":date_created,
		"po_date":date_created,
		"company": woocommerce_settings.company,
		"payment_category": payment_category,
		"comments": customer_note
	}
	if order_type:
		invoice_dict['order_type']= order_type

	if temp_address: # Adding tempopary address in invoice
		invoice_dict.update(temp_address)
	
	if delivery_option:
		invoice_dict['customer_shipping_instructions'] = delivery_option
	invoice_doc = frappe.get_doc(invoice_dict)

	# Add Items
	set_items_in_sales_invoice(order, customer_code, invoice_doc, woocommerce_settings)

	# Save 
	invoice_doc.flags.ignore_mandatory = True
	invoice_doc.insert()
	DocTags("Sales Invoice").add(invoice_doc.name, "WooCommerce Order")

	return invoice_doc
	

def set_items_in_sales_invoice(order, customer_code, invoice_doc, woocommerce_settings):
	company_abbr = frappe.db.get_value('Company', woocommerce_settings.company, 'abbr')
	sku = ""
	for item in order.get("line_items"):
		sku = item.get("sku")
		if frappe.db.exists("Item", {"name": sku}):
			foundItem = frappe.get_doc("Item", {"name": sku})
		else:
			frappe.throw("Item: {} is not found!").format(sku)
		if frappe.db.get_value("Customer", customer_code, "default_price_list"):
			price_list = frappe.db.get_value("Customer", customer_code, "default_price_list")
		else:
			frappe.throw("Default price list for customer: {} is not found!").format(customer_code)

		# consider we could have multiple item price for the same item 
		rate_list = frappe.db.get_list('Item Price', 
			filters=[
				['selling', '=', 1],
				['buying', '=', 0],
				['price_list', '=', price_list],
				['item_code', '=', sku],
				['valid_upto', 'is', 'not set']
			], fields=['price_list_rate']
		)
		if rate_list:
			rate = rate_list[0]
		else:
			frappe.throw("Item Price for {} - {} is not found!".format(sku, price_list))
		invoice_doc.append("items",{
			"item_code": foundItem.item_code,
			"item_name": foundItem.item_name,
			"description": foundItem.item_name,
			"uom": woocommerce_settings.uom or _("Unit"),
			"qty": item.get("quantity"),
			"rate": rate['price_list_rate'],
			"warehouse": woocommerce_settings.warehouse or _("Stores - {0}").format(company_abbr)
		})

		if foundItem.item_group != "Tests":
			itemTax = (rate['price_list_rate']*0.1) * item.get("quantity")
			addTaxDetails(invoice_doc, itemTax, "Ordered Item tax", woocommerce_settings.tax_account)

	# adding handling fee
	if invoice_doc.order_type == "Patient Order":
		invoice_doc.append("items",{
			"item_code": "HAND-FEE",
			"item_name": "Handling Fee",
			"description": "Handling Fee",
			"uom": "Unit",
			"qty": 1,
			"rate": 20,
			"warehouse": woocommerce_settings.warehouse
		})
		addTaxDetails(invoice_doc, 2, "Handling Fee tax", woocommerce_settings.tax_account)

	if float(order.get("shipping_total")) > 0:
		addTaxDetails(invoice_doc, order.get("shipping_total"), "Shipping Total", woocommerce_settings.f_n_f_account)
	if float(order.get("shipping_tax")) > 0:
		addTaxDetails(invoice_doc, order.get("shipping_tax"), "Shipping Tax", woocommerce_settings.tax_account)


def addTaxDetails(salesInvoice, price, desc, tax_account_head):
	salesInvoice.append("taxes", {
		"charge_type":"Actual",
		"account_head": tax_account_head,
		"tax_amount": price,
		"description": desc
	})