

import base64
import hashlib
import hmac
import json

import frappe
from frappe import _
from frappe.utils import cstr


import pdb
import requests
from datetime import datetime 

from frappe.utils.background_jobs import enqueue
from frappe.desk.doctype.tag.tag import DocTags
from erpnext.stock.get_item_details import get_bin_details
from fxnmrnth.integration_req_log import log_integration_request, log_exceptions
19820
from erpnext.exceptions import PartyFrozen, PartyDisabled
from frappe.exceptions import ValidationError

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
		not sig == frappe.get_request_header("X-Wc-Webhook-Signature", "").encode():
			frappe.throw(_("Unverified Webhook Data"))

def validate_event_and_status(order_id, event, status):
	if event == "woocommerce_payment_complete": # normal patient test order and on-behalf test order
		if status != "processing":
			frappe.log_error(message="Order ID: {} -- Status {}".format(order_id, status), 
				title="WooCommerce Event: {}".format(event))
			frappe.throw(f"Getting unexpect status: {status} from {event}!")

	elif event == "wholesale_order":
		if status not in ["pending", "on-hold"]:
			frappe.log_error(message="Order ID: {} -- Status {}".format(order_id, status), 
				title="WooCommerce Event: {}".format(event))
			frappe.throw(f"Getting unexpect status: {status} from {event}!")

def pre_process_payload(meta_data, billing):
	customer_code = ""
	pos_order_type = ""
	patient_name = ""
	delivery_option = ""
	invoice_sending_option = ""
	patient_dob = ""
	for meta in meta_data:
		if meta["key"] == "user_practitioner":
			customer_code = meta["value"]
		elif meta["key"] == "customer_code":
			customer_code = meta["value"]
		elif meta["key"] == "delivery_option":
			delivery_option = meta["value"]
		# elif meta["key"] == "_nab_reference_id":
		# 	nab_reference_id = meta["value"]
		elif meta["key"] == "pos_patient":
			patient_name = meta["value"]
		elif meta["key"] == "patient_dob":
			patient_dob = meta["value"]
		elif meta["key"] == "invoice_sending_option":
			invoice_sending_option = meta["value"]
		elif meta["key"] == "_pos_order_type":
			pos_order_type = meta["value"]
		else:
			pass

	# To reslove if customer code contains "-a" or "-b"
	if "-" in customer_code:
		end_index = customer_code.find('-')
		customer_code = customer_code[0:end_index]

	# create temp_address dict for later use
	temp_address = {
		"temporary_address": 1,
		"temporary_delivery_address_line_1": patient_name if patient_name else billing.get('first_name') + " " + billing.get('last_name'),
		"temporary_delivery_address_line_2": billing.get('address_1') + " " + billing.get('address_2'),
		"temporary_delivery_address_line_3": billing.get('city') + ", " + billing.get('state') + ", " + billing.get('postcode') + ", " + billing.get('country'),
		"temporary_delivery_address_line_4": billing.get('phone'),
		"temporary_delivery_address_line_5": billing.get('email')
	}

	# convert date format 03/07/1985
	if patient_dob:
		patient_dob = datetime.strptime(patient_dob, "%d/%m/%Y").strftime("%Y-%m-%d")

	return customer_code, pos_order_type, patient_name, invoice_sending_option, delivery_option, temp_address, patient_dob

def validate_customer_code_erpnext(customer_code):
	if not customer_code :
		frappe.throw("Check order id {} in WP, cannot find user_practitioner".format(order.get('id')))

	if frappe.db.exists("Customer", customer_code):
		customer_doc = frappe.get_doc("Customer", customer_code)
		payment_category = customer_doc.payment_category
		accepts_backorders = customer_doc.accepts_backorders
	else:
		frappe.throw("Customer {} not exits in ERPNext!".format(customer_code))
	return payment_category, accepts_backorders

@frappe.whitelist(allow_guest=True)
def order(*args, **kwargs):
	woocommerce_settings = frappe.get_doc("Woocommerce Settings")
	try:
		response = _order(woocommerce_settings, *args, **kwargs)
		return response
	except PartyFrozen as exc:
		order = json.loads(frappe.request.data)
		log_exceptions(order=order, status="Failed", internal_reason=str(exc))
		return str(exc)
	except PartyDisabled as exc:
		order = json.loads(frappe.request.data)
		log_exceptions(order=order, status="Failed", internal_reason=str(exc))
		return str(exc)
	except ValidationError as exc:
		order = json.loads(frappe.request.data)
		log_exceptions(order=order, status="Failed", internal_reason=str(exc))
		return str(exc)
	else:
		order = json.loads(frappe.request.data)
		webhook_delivery_id = frappe.get_request_header("X-WC-Webhook-Delivery-ID")
		log_integration_request(webhook_delivery_id=webhook_delivery_id, order=order, invoice_doc=None, status="Failed", data=json.dumps(order, indent=4), error=frappe.get_traceback(), woocommerce_settings=woocommerce_settings)
		return frappe.get_traceback()

def _order(woocommerce_settings, *args, **kwargs):
	frappe.set_user(woocommerce_settings.creation_user)
	if frappe.request and frappe.request.data:
		# verify_request()
		try:
			order = json.loads(frappe.request.data)
		except ValueError:
			#woocommerce returns 'webhook_id=value' for the first request which is not JSON
			order = frappe.request.data
		event = frappe.get_request_header("X-WC-Webhook-Event")
		webhook_delivery_id = frappe.get_request_header("X-WC-Webhook-Delivery-ID")
	else:
		return "success"

	# Validate if the event and status results are expecting
	validate_event_and_status(order.get("id"), event, order.get("status"))

	# Mapping of order type
	order_type_mapping = {
		"practitioner_order": "Practitioner Order",
		"self": "Self Test",
		"patient_order": "Patient Order",
		"on-behalf": "On Behalf",
	}

	# pre-process to parse payload (parameter: meta_data, billing)
	customer_code, pos_order_type, patient_name, invoice_sending_option, delivery_option, temp_address, patient_dob = pre_process_payload(order.get('meta_data'), order.get('billing'))

	if pos_order_type == "marketing_material":
		return "Marketing Material detected, we will ignore in ERPNext"

	# Validate customer code, output payment_category and accepts_backorders 
	payment_category, accepts_backorders = validate_customer_code_erpnext(customer_code)

	# categorized customer type and order type
	customer_id = order.get('customer_id')

	# input customer_id 
	test_order = 0
	if customer_id == 0: # this is guest login, a patient under a practitioner
		edited_line_items, create_backorder_doc_flag = backorder_validation(order.get("line_items"), customer_code, woocommerce_settings)
		if pos_order_type == "patient_test_order":

			#Check if Prac is Frozen and Patient Test Order
			temporaryUnfreeze = 0
			customer_doc = frappe.get_doc("Customer", customer_code)
			if customer_doc.is_frozen == 1:
				temporaryUnfreeze = 1
				customer_doc.is_frozen = 0
				customer_doc.save()

			# We don't need to use the backorder flag for test order
			test_order = 1
			invoice_sending_option = "send receipt to patient" # this need to be added so that test kit is added for this type of orders
			new_invoice, customer_accepts_backorder = create_sales_invoice(edited_line_items, order, customer_code, "Pay before Dispatch", woocommerce_settings, order_type= "Patient Order", temp_address=temp_address, delivery_option=delivery_option, invoice_sending_option=invoice_sending_option, test_order=test_order, patient_dob=patient_dob)

			#Check if Prac was Frozen and Patient Test Order
			if temporaryUnfreeze == 1:
				DocTags("Sales Invoice").add(new_invoice.name, "Temporary Unfreeze")
				customer_doc.is_frozen = 1
				customer_doc.save()

		elif pos_order_type == "patient_product_order":
			# Cannot handle that for now as we need to check if the patient account exist or not in ERPNext
			log_integration_request(webhook_delivery_id=webhook_delivery_id, order=order, invoice_doc=None, status="Cancelled", data=json.dumps(order, indent=4), error="Ignore patient product order for now", woocommerce_settings=woocommerce_settings)
			return "Ignore patient order type"
		else: # Throw error if the pos_order_type is something else
			frappe.log_error(title="Error in guest order", message="Cannot recoginized pos_order_type: {}".format(pos_order_type))
	else: # this is a user login, a practitioner
		if woocommerce_settings.company == "RN Labs":
			if pos_order_type not in order_type_mapping:
				log_integration_request(webhook_delivery_id=webhook_delivery_id, order=order, invoice_doc=None, status="Cancelled", data=json.dumps(order, indent=4), error="Order Type is not found on WooCommcerce Payload!", woocommerce_settings=woocommerce_settings)
				frappe.throw('Order Type is not found on WooCommcerce Payload!')
			order_type = order_type_mapping[pos_order_type]
			edited_line_items, create_backorder_doc_flag = backorder_validation(order.get("line_items"), customer_code, woocommerce_settings)

			if pos_order_type in  ["self", "on-behalf"]:
				# apply 20% of the discount
				test_order = 1
				if pos_order_type == "self":
					invoice_sending_option = "send receipt to patient" # this need to be added so that test kit is added for this type of orders
					new_invoice, customer_accepts_backorder = create_sales_invoice(edited_line_items, order, customer_code, payment_category, woocommerce_settings, order_type=order_type, invoice_sending_option=invoice_sending_option, test_order=test_order)
				else:
					new_invoice, patient_invoice_doc = create_sales_invoice(edited_line_items, order, customer_code, payment_category, woocommerce_settings, order_type=order_type, temp_address=temp_address, delivery_option=delivery_option, invoice_sending_option=invoice_sending_option, test_order=test_order, patient_dob=patient_dob)
					customer_accepts_backorder = 1

			elif pos_order_type == "practitioner_order":
				if create_backorder_doc_flag == 1:
					# throw error if the customers don't accept backorders
					if not accepts_backorders:
						frappe.throw("Customer {} doesn't accept backorders!")
					frappe.throw("This need to be developed further, to create a backorder instead of invoice")
				else: # Create sales invoice
					new_invoice, customer_accepts_backorder = create_sales_invoice(edited_line_items, order, customer_code, payment_category, woocommerce_settings, order_type=order_type)
			else:
				frappe.log_error(title="Error in authorized order", message="Cannot recoginized pos_order_type: {}".format(pos_order_type))

	# Create a intergration request
	try:
		if invoice_sending_option != "send receipt to clinic":
			patient_invoice_doc = None

		log_integration_request(webhook_delivery_id=webhook_delivery_id, order=order, invoice_doc=new_invoice, status="Completed", data=json.dumps(order, indent=4), reference_docname=new_invoice.name, woocommerce_settings=woocommerce_settings, test_order=test_order, customer_accepts_backorder=customer_accepts_backorder, patient_invoice_doc=patient_invoice_doc)

		# for postman display only
		if invoice_sending_option != "send receipt to clinic":
			return "Sales invoice: {} created!".format(new_invoice.name)
		else:
			return "Sales invoice: {} created! \n Patient invoice: {}".format(new_invoice.name, patient_invoice_doc.name)
	except UnboundLocalError:
		frappe.log_error(title="Error in Woocommerce Integration", message=frappe.get_traceback())
		frappe.throw(frappe.get_traceback())


def create_sales_invoice(edited_line_items, order, customer_code, payment_category,  woocommerce_settings, order_type=None, temp_address=None, delivery_option=None, invoice_sending_option=None, test_order=0, patient_dob=""):
	#Set Basic Info
	date_created = order.get("date_created").split("T")[0]
	customer_note = order.get('customer_note')
	tax_rate = frappe.db.get_value('Account', woocommerce_settings.tax_account, "tax_rate")/100

	default_warehouse = frappe.db.get_single_value('Stock Settings', 'default_warehouse')
	invoice_dict = {
		"doctype": "Sales Invoice",
		"customer": customer_code,
		"woocommerce_order": 1,
		"set_warehouse": default_warehouse,
		"po_no": str(order.get("id")),
		"naming_series": frappe.get_meta("Sales Invoice").get_field("naming_series").options or "",
		"transaction_date":date_created,
		"po_date":date_created,
		"company": woocommerce_settings.company,
		"payment_category": payment_category,
		"patient_dob": patient_dob
	}
	if order_type:
		if order_type == "Self Test":
			invoice_dict['campaign'] = order_type
		invoice_dict['order_type']= order_type

	if temp_address: # Adding tempopary address in invoice
		invoice_dict.update(temp_address)
	
	if delivery_option:
		invoice_dict['customer_shipping_instructions'] = delivery_option

	if customer_note:
		if 'customer_shipping_instructions' in invoice_dict: # in case the delivery option is not presented
			invoice_dict['customer_shipping_instructions'] += (" " + customer_note)
		else:
			invoice_dict['customer_shipping_instructions'] = customer_note


	if woocommerce_settings.company == "RN Labs":
		# set selling price list
		if order_type in ["Practitioner Order", "Self Test", "On Behalf"]:
			invoice_dict["selling_price_list"] = "Aus Wholesale"
			invoice_dict["taxes_and_charges"] = "Australia GST 10% Wholesale - RNLab"
			included_in_print_rate = 0
		else:
			invoice_dict["selling_price_list"] = "Aus Retail"
			invoice_dict["taxes_and_charges"] = "Australia GST 10% Retail - RNLab"
			included_in_print_rate = 1

	# create frappe doc for invoice
	invoice_doc = frappe.get_doc(invoice_dict)

	# Add Items, add test kit based on invoice sending option
	customer_accepts_backorder = set_items_in_sales_invoice(edited_line_items, customer_code, invoice_doc, woocommerce_settings, tax_rate, invoice_sending_option=invoice_sending_option)

	# Save 
	invoice_doc.flags.ignore_mandatory = True
	invoice_doc.insert()

	shipping_total = order.get('shipping_total')
	shipping_tax = order.get('shipping_tax')


	# adding handling fee
	if test_order == 1:
		# Hard code shipping tax
		if invoice_doc.order_type == "On Behalf":
			shipping_tax = 2
			shipping_total = 20

			# Depending on invoice sending option
			if invoice_sending_option == "send receipt to clinic":
				# create patient invoice with just test kit
				patient_invoice_doc = frappe.get_doc(invoice_dict)
				create_patient_invoice(edited_line_items, patient_invoice_doc)

				if hasattr(patient_invoice_doc, "items"):
					# Save 
					patient_invoice_doc.flags.ignore_mandatory = True
					patient_invoice_doc.insert()

					DocTags("Sales Invoice").add(patient_invoice_doc.name, "WC order on behalf of patient")

		invoice_doc.append("items",{
			"item_code": "HAND-FEE",
			"item_name": "Handling Fee",
			"description": "Handling Fee",
			"uom": "Unit",
			"qty": 1,
			"rate": str(float(shipping_total) + float(shipping_tax)),
			"warehouse": woocommerce_settings.warehouse
		})
		add_tax_on_net_total(invoice_doc, "Handling Fee tax", woocommerce_settings.tax_account, rate=10, included_in_print_rate=1)

	else: # test_order = 0
		# Add shipping fee according to the total 
		# if invoice_doc.total < 150:
			# use default $10 as shipping fee need to correct in the future
			# addTaxDetails("Actual", invoice_doc, 10, "Shipping Total", woocommerce_settings.f_n_f_account)
			# addTaxDetails("Actual", invoice_doc, 10 * tax_rate, "Shipping Tax", woocommerce_settings.tax_account)
		shipping_lines = order.get('shipping_lines')
		if shipping_lines:
			for shipping_line in shipping_lines:
				if float(shipping_line["total"]) > 0:
					invoice_doc.append("items",{
						"item_code": "SHIP1",
						"item_name": "Standard Shipping",
						"description": "Standard Shipping",
						"uom": "Unit",
						"qty": 1,
						"warehouse": woocommerce_settings.warehouse
					})
		desc = "GST 10% @ 10.0"
		addTaxDetails("On Net Total", invoice_doc, 0, desc, woocommerce_settings.tax_account, rate=10, included_in_print_rate=included_in_print_rate)

	invoice_doc.save()

	## put any message logs into the comments section
	msg_comments = ""
	messages = frappe.get_message_log()
	if messages:
		for message in messages:
			msg_comments += message.get("message") + "\n"

	invoice_doc.comments = msg_comments
	invoice_doc.save()

	DocTags("Sales Invoice").add(invoice_doc.name, "WooCommerce Order")

	# if send receipt to clinic, we need to have two invoices, one for practitioner, one for patient
	if invoice_sending_option == "send receipt to clinic":
		return invoice_doc, patient_invoice_doc
	else:
		return invoice_doc, customer_accepts_backorder


def set_items_in_sales_invoice(edited_line_items, customer_code, invoice_doc, woocommerce_settings, tax_rate, invoice_sending_option=None):
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
			"is_stock_item": found_item.is_stock_item,
			"is_paediatric": True or False,
			"is_swab": True of False,
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
					"item_name": item['item_name'], 
					"supplier": supplier,
					"qty": item["qty"],
					"actual_qty":item["actual_qty"]
				})
			else:
				invoice_doc.append("items", item)
				if item["item_group"] != "Tests":
					item_tax = (item['rate'] * tax_rate) * item["qty"]

			# We need to flag the update backorder if backorder_items has contents
			if invoice_doc.get("backorder_items"):
				invoice_doc.set("update_backorder", 1)

		else: # item["is_stock_item"] == 0 
			invoice_doc.append("items", item)
			if item["item_group"] != "Tests":
				item_tax = (item['rate'] * tax_rate) * item["qty"]

			if item["item_group"] == "Tests" and invoice_sending_option == "send receipt to patient":
				## need to check if is_paediatric
				if item["item_code"] == "OAT1" and item["is_paediatric"]:
					extra_test_kit = "GPPDBag"
					invoice_doc.append("items", {
						"item_code": extra_test_kit,
						"qty": 1,
					})

				## need to check if is_swab
				if item["item_code"].startswith("DNA") and item["is_swab"]:
					extra_test_kit = "DNAKIT"
					invoice_doc.append("items", {
						"item_code": extra_test_kit,
						"qty": 1,
					})	
				
				test_kit = frappe.db.get_value("Item", item['item_code'], "test_kit")
				
				# pdb.set_trace()
				## append it to sales invoice
				if test_kit:
					invoice_doc.append("items", {
						"item_code": test_kit,
						"qty": 1,
					})


	# check if customer accepts backorder
	customer_accepts_backorder = 1
	try:
		if invoice_doc.backorder_items:
			accepts_backorders = frappe.db.get_value("Customer", customer_code, "accepts_backorders")
			if not accepts_backorders:
				customer_accepts_backorder = 0
	except AttributeError:
		pass
	except:
  		frappe.log_error(title='Error in woocommerce integration', message=frappe.get_traceback())
	return customer_accepts_backorder

def create_patient_invoice(edited_line_items, patient_invoice_doc):
	# Proceed to invoice
	for item in edited_line_items:
		if item["item_group"] == "Tests":
			test_kit = frappe.db.get_value("Item", item['item_code'], "test_kit")
			if test_kit:
				patient_invoice_doc.append("items", {
					"item_code": test_kit,
					"qty": 1,
				})
			else:
				frappe.throw("Cannot find testkit for {}".format(item['item_code']))


def backorder_validation(line_items, customer_code, woocommerce_settings, discount=None):
	new_line_items = []
	backorder_item_num = 0
	for item in line_items:
		sku = item.get("sku")

		# check sku
		if not sku:
			frappe.throw(f"SKU is missing for {item.get('name', 'product')}")
		
		# if we detect the sku is "GPKITPD", we ignore it
		if sku == "GPKITPD":
			continue

		# check if the item with the sku exist
		if frappe.db.exists("Item", {"name": sku}):
			found_item = frappe.get_doc("Item", {"name": sku})
		else:
			frappe.log_error(title="WooCommerce Item Mismatch", message="Item: {} is not found!".format(sku))
			frappe.throw("Item: {} is not found!".format(sku))


		# hard code part:
		# 1. if detect the sku is "OAT1", then we need to change the item_code to "" postpond
		""" item.meta_data: 
		{
			Key :  'paediatric'
			Value : 'true'
		}
		"""
		is_paediatric = False
		if sku == "OAT1":
			item_meta_data = item.get('meta_data')
			for meta_data in item_meta_data:
				if meta_data.get('key') == "paediatric" and meta_data.get('value') == "true":
					is_paediatric = True

		# 2. For DNA swab
		is_swab = False
		if sku.startswith("DNA"):
			item_meta_data = item.get('meta_data')
			for meta_data in item_meta_data:
				if meta_data.get('key') == "swab" and meta_data.get('value') == "true":
					is_swab = True

		# we want to find the price list for that curreny and calculate the discount percentage
		default_price_list = frappe.db.get_value("Customer", customer_code, "default_price_list")
		from erpnext.stock.get_item_details import get_price_list_rate_for
		args = frappe._dict(
			customer=customer_code,
			price_list=default_price_list, 
			qty=item.get("quantity"),
			transaction_date=datetime.today().strftime('%Y-%m-%d')
		)
		price_list_rate = get_price_list_rate_for(
			args,
			found_item.item_code,
		)

		if item.get("price")> 0 and price_list_rate:
			discount = (price_list_rate - item.get("price")) / price_list_rate * 100
		else:
			discount = 0

		validated_item = {
			"item_code": found_item.item_code,
			"item_name": found_item.item_name,
			"description": found_item.item_name,
			"item_group": found_item.item_group,
			"uom": woocommerce_settings.uom or _("Unit"),
			"qty": item.get("quantity"),
			"discount_percentage": discount,
			# "rate": item.get("price"),
			"warehouse": woocommerce_settings.warehouse,
			"is_stock_item": found_item.is_stock_item,
			"is_paediatric": is_paediatric,
			"is_swab": is_swab,
		}

		if price_list_rate:
			validated_item['rate'] = price_list_rate
		else:
			validated_item['rate'] = item.get("price")

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

def add_tax_on_net_total(sales_invoice, desc, tax_account_head, rate=None, included_in_print_rate=0):
	tax_dict = {
		"charge_type":"On Net Total",
		"account_head": tax_account_head,
		"rate": rate,
		"description": desc
	}
	if included_in_print_rate:
		tax_dict['included_in_print_rate'] = included_in_print_rate
	sales_invoice.append("taxes", tax_dict)

def addTaxDetails(charge_type, sales_invoice, tax_amount, desc, tax_account_head, rate=None, included_in_print_rate=0):
	tax_dict = {
		"charge_type":charge_type,
		"account_head": tax_account_head,
		"tax_amount": tax_amount,
		"description": desc
	}
	if rate:
		tax_dict['rate'] = rate
	if included_in_print_rate:
		tax_dict['included_in_print_rate'] = included_in_print_rate
	sales_invoice.append("taxes", tax_dict)