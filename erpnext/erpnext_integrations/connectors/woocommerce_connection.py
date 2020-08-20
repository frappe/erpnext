
from __future__ import unicode_literals
import frappe, base64, hashlib, hmac, json
from frappe import _

import pdb
import requests

from frappe.utils.background_jobs import enqueue
from frappe.desk.doctype.tag.tag import DocTags
from erpnext.stock.get_item_details import get_bin_details
from fxnmrnth.integration_req_log import log_integration_request


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


@frappe.whitelist(allow_guest=True)
def order(*args, **kwargs):
	woocommerce_settings = frappe.get_doc("Woocommerce Settings")
	try:
		response = _order(woocommerce_settings, *args, **kwargs)
		return response
	except Exception:
		order = json.loads(frappe.request.data)
		log_integration_request(order=order, invoice_doc=None, status="Failed", data=json.dumps(order, indent=4), error=frappe.get_traceback(), woocommerce_settings=woocommerce_settings)

def _order(woocommerce_settings, *args, **kwargs):
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
		status = order.get("status")
		if status == "failed":
			frappe.log_error("order {} status {}".format(order.get("id"), order.get('status')), "WooCommerce order status filter")

		# Get basic data from order
		customer_id = order.get('customer_id')
		meta_data = order.get('meta_data')
		billing = order.get('billing')

		# Mapping of order type
		order_type_mapping = {
			"practitioner_order": "Practitioner Order",
			"self": "Self Test",
			"patient_order": "Patient Order",
			"on-behalf": "Patient Order",
		}

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
			pos_order_type = ""
			for meta in meta_data:
				if meta["key"] == "customer_code":
					customer_code = meta["value"]
				elif meta["key"] == "user_practitioner":
					customer_code = meta["value"]
				elif meta["key"] == "_pos_order_type":
					pos_order_type = meta["value"]

			if not customer_code:
				frappe.throw("WP Customer id {} don't have a customer code in ERPNext!".format(customer_id))
			# For practitioner order, we just need to get the primary address as shipping address
			if frappe.db.exists("Customer", customer_code):
				customer_doc = frappe.get_doc("Customer", customer_code)
				payment_category = customer_doc.payment_category
				accepts_backorders = customer_doc.accepts_backorders


				if woocommerce_settings.company == "RN Labs":
					# use pos_order_type to check if it's practitioner order or self test
					order_type = order_type_mapping[pos_order_type]
				
					# we need to find the primary address


					# branch off by different order type
					if order_type == "Self Test":
						# apply 20% of the discount

						## maybe no shipping fee 
						pass
					elif order_type == "Practitioner Order":
						# Item backorder validation
						edited_line_items, create_backorder_doc_flag = backorder_validation(order.get("line_items"), customer_code, woocommerce_settings)

						if create_backorder_doc_flag == 1:
							# throw error if the customer don't accept backorders
							if not accepts_backorders:
								frappe.throw("Customer {} doesn't accepts backorders!")
							frappe.throw("This need to be developed further, to create a backorder instead of invoice")
						else: # Create sales invoice
							new_invoice = create_sales_invoice(edited_line_items, order, customer_code, payment_category, woocommerce_settings, order_type=order_type, temp_address=None, delivery_option=None)

			else:
				frappe.throw("Customer {} not exits!".format(customer_code))

		# Create a intergration request
		log_integration_request(order=order, invoice_doc=new_invoice, status="Completed", data=json.dumps(order), reference_docname=new_invoice.name, woocommerce_settings=woocommerce_settings)


		return "Sales invoice: {} created!".format(new_invoice.name)

def create_sales_invoice(edited_line_items, order, customer_code, payment_category,  woocommerce_settings, order_type=None, temp_address=None, delivery_option=None):
	#Set Basic Info
	date_created = order.get("date_created").split("T")[0]
	customer_note = order.get('customer_note')
	tax_rate = frappe.db.get_value('Account', woocommerce_settings.tax_account, "tax_rate")/100

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

	# create frappe doc for invoice
	invoice_doc = frappe.get_doc(invoice_dict)

	# Add Items
	set_items_in_sales_invoice(edited_line_items, customer_code, invoice_doc, woocommerce_settings, tax_rate)

	# Save 
	invoice_doc.flags.ignore_mandatory = True
	invoice_doc.insert()

	# Add shipping fee according to the total 
	if invoice_doc.total < 150:
		# use default $10 as shipping fee need to correct in the future
		addTaxDetails(invoice_doc, 10, "Shipping Total", woocommerce_settings.f_n_f_account)
		addTaxDetails(invoice_doc, 10 * tax_rate, "Shipping Tax", woocommerce_settings.tax_account)


	if woocommerce_settings.company == "RN Labs":
		# adding handling fee
		if invoice_doc.order_type == "Patient Order" or invoice_doc.order_type == "Self Test":
			invoice_doc.append("items",{
				"item_code": "HAND-FEE",
				"item_name": "Handling Fee",
				"description": "Handling Fee",
				"uom": "Unit",
				"qty": 1,
				"rate": 20,
				"warehouse": woocommerce_settings.warehouse
			})
			addTaxDetails(invoice_doc, 20*tax_rate, "Handling Fee tax", woocommerce_settings.tax_account)

	invoice_doc.save()

	DocTags("Sales Invoice").add(invoice_doc.name, "WooCommerce Order")

	return invoice_doc
	

def set_items_in_sales_invoice(edited_line_items, customer_code, invoice_doc, woocommerce_settings, tax_rate):
	"""
		validated_item = {
			"item_code": found_item.item_code,
			"item_name": found_item.item_name,
			"description": found_item.item_name,
			"item_group": found_item.item_group,
			"uom": woocommerce_settings.uom or _("Unit"),
			"qty": item.get("quantity"),
			"rate": rate['price_list_rate'],
			"warehouse": woocommerce_settings.warehouse,
			"is_stock_item": found_item.is_stock_item
		}
	"""
	# Proceed to invoice
	for item in edited_line_items:
		if item["is_stock_item"] == 1: # only check if it maintains stock
			if item["qty"] > item["actual_qty"]:
				supplier = frappe.db.get_value("Item Default",{
					"parent": item['item_code'], 
					"company": woocommerce_settings.company}, "default_supplier")
				invoice_doc.append("backorder_items", {
					"item_code": item['item_code'], 
					"supplier": supplier,
					"qty": item["qty"],
					"actual_qty":item["actual_qty"]
				})
			else:
				invoice_doc.append("items", item)
				if item["item_group"] != "Tests":
					item_tax = (item['rate'] * tax_rate) * item["qty"]
					desc = "{} tax".format(item["item_code"])
					addTaxDetails(invoice_doc, item_tax, desc, woocommerce_settings.tax_account)
		else: # item["is_stock_item"] == 0 
			invoice_doc.append("items", item)
			if item["item_group"] != "Tests":
				item_tax = (item['rate'] * tax_rate) * item["qty"]
				desc = "{} tax".format(item["item_code"])
				addTaxDetails(invoice_doc, item_tax, desc, woocommerce_settings.tax_account)


def backorder_validation(line_items, customer_code, woocommerce_settings):
	new_line_items = []
	backorder_item_num = 0
	for item in line_items:
		sku = item.get("sku")

		# check sku
		if not sku:
			frappe.throw("SKU is missing!")
		
		# check if the item with the sku exist
		if frappe.db.exists("Item", {"name": sku}):
			found_item = frappe.get_doc("Item", {"name": sku})
		else:
			frappe.throw("Item: {} is not found!").format(sku)

		# check if the customer has the default_price_list
		if frappe.db.get_value("Customer", customer_code, "default_price_list"):
			price_list = frappe.db.get_value("Customer", customer_code, "default_price_list")
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
		else:
			frappe.throw("Default price list for customer: {} is not found!").format(customer_code)

		validated_item = {
			"item_code": found_item.item_code,
			"item_name": found_item.item_name,
			"description": found_item.item_name,
			"item_group": found_item.item_group,
			"uom": woocommerce_settings.uom or _("Unit"),
			"qty": item.get("quantity"),
			"rate": rate['price_list_rate'],
			"warehouse": woocommerce_settings.warehouse,
			"is_stock_item": found_item.is_stock_item
		}

		# check if item is out of stock
		if found_item.is_stock_item == 1:
			validated_item['actual_qty'] = get_bin_details(found_item.item_code, woocommerce_settings.warehouse)['actual_qty']
			if validated_item['actual_qty'] < validated_item["qty"]:
				backorder_item_num += 1

		new_line_items.append(validated_item)

	# check if all the items need to be on back order
	create_backorder_doc_flag = 0
	if backorder_item_num == len(new_line_items):
		create_backorder_doc_flag = 1
	return new_line_items, create_backorder_doc_flag


def addTaxDetails(sales_invoice, price, desc, tax_account_head):
	sales_invoice.append("taxes", {
		"charge_type":"Actual",
		"account_head": tax_account_head,
		"tax_amount": price,
		"description": desc
	})