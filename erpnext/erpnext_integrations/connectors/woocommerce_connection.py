
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
			"on-behalf": "On Behalf",
		}

		# link customer and address
		customer_code = ""
		pos_order_type = ""
		patient_name = ""
		for meta in meta_data:
			if meta["key"] == "user_practitioner":
				if "-" in meta["value"]:
					end_index = meta["value"].find('-')
					customer_code = meta["value"][0:end_index]
				else:
					customer_code = meta["value"]
			elif meta["key"] == "customer_code":
				customer_code = meta["value"]
			# elif meta["key"] == "practitioner_name":
			# 	practitioner_name = meta["value"]
			elif meta["key"] == "delivery_option":
				delivery_option = meta["value"]
			# elif meta["key"] == "_nab_reference_id":
			# 	nab_reference_id = meta["value"]
			elif meta["key"] == "pos_patient":
				patient_name = meta["value"]
			elif meta["key"] == "_pos_order_type":
				pos_order_type = meta["value"]
			else:
				pass

		if not patient_name:
			patient_name = billing.get('first_name') + ", " + billing.get('last_name')
		street = billing.get('address_1') + " " + billing.get('address_2')
		city_postcode_country = billing.get('city') + ", " + billing.get('state') + ", " + billing.get('postcode') + ", " + billing.get('country')
		phone = billing.get('phone')
		email = billing.get('email')

		# create temp_address dict for later use
		temp_address = {
			"temporary_address": 1,
			"temporary_delivery_address_line_1": patient_name,
			"temporary_delivery_address_line_2": street,
			"temporary_delivery_address_line_3": city_postcode_country,
			"temporary_delivery_address_line_4": phone,
			"temporary_delivery_address_line_5": email,
		}

		if not customer_code :
			frappe.throw("Check order id {} in WP, cannot find user_practitioner".format(order.get('id')))

		if frappe.db.exists("Customer", customer_code):
			customer_doc = frappe.get_doc("Customer", customer_code)
			payment_category = customer_doc.payment_category
			accepts_backorders = customer_doc.accepts_backorders
		else:
			frappe.throw("Customer {} not exits!".format(customer_code))

		test_order = 0
		if customer_id == 0: # this is guest login, a patient under a practitioner
			edited_line_items, create_backorder_doc_flag = backorder_validation(order.get("line_items"), customer_code, woocommerce_settings)
			if pos_order_type == "patient_test_order":
				# We don't need to use the backorder flag for test order
				test_order = 1
				new_invoice, customer_accepts_backorder = create_sales_invoice(edited_line_items, order, customer_code, "Pay before Dispatch", woocommerce_settings, order_type= "Patient Order", temp_address=temp_address, delivery_option=delivery_option, test_order=test_order)

			elif pos_order_type == "patient_product_order":
				if create_backorder_doc_flag == 1:
					# throw error if the customers don't accept backorders
					if not accepts_backorders:
						frappe.throw("Customer {} doesn't accept backorders!")
					frappe.throw("This need to be developed further, to create a backorder instead of invoice")

				new_invoice, customer_accepts_backorder = create_sales_invoice(edited_line_items, order, customer_code, "Pay before Dispatch", woocommerce_settings, order_type= "Patient Order", temp_address=temp_address, delivery_option=delivery_option)
			else:
				frappe.log_error(title="Error in guest order", message="Cannot recoginized pos_order_type: {}".format(pos_order_type))
		else: # customer_id != 0
			# this is a user login, a practitioner
			if woocommerce_settings.company == "RN Labs":
				order_type = order_type_mapping[pos_order_type]
				"""
					order_type_mapping = {
						"practitioner_order": "Practitioner Order",
						"self": "Self Test",
						"on-behalf": "On Behalf",
						"patient_order": "Patient Order",
					}
				"""
				if pos_order_type == "self":
					# apply 20% of the discount
					self_test_discount = 20
					edited_line_items, create_backorder_doc_flag = backorder_validation(order.get("line_items"), customer_code, woocommerce_settings, discount=self_test_discount)
					test_order = 1
					new_invoice, customer_accepts_backorder = create_sales_invoice(edited_line_items, order, customer_code, payment_category, woocommerce_settings, order_type=order_type, test_order=test_order)
					## maybe no shipping fee 

				elif pos_order_type == "practitioner_order":

					edited_line_items, create_backorder_doc_flag = backorder_validation(order.get("line_items"), customer_code, woocommerce_settings)
					if create_backorder_doc_flag == 1:
						# throw error if the customers don't accept backorders
						if not accepts_backorders:
							frappe.throw("Customer {} doesn't accept backorders!")
						frappe.throw("This need to be developed further, to create a backorder instead of invoice")
					else: # Create sales invoice
						new_invoice, customer_accepts_backorder = create_sales_invoice(edited_line_items, order, customer_code, payment_category, woocommerce_settings, order_type=order_type)

				elif pos_order_type == "on-behalf": # Test order for patient
					# we can ignore the create_backorder_doc_flag since this is a test order
					test_order = 1
					edited_line_items, create_backorder_doc_flag = backorder_validation(order.get("line_items"), customer_code, woocommerce_settings)

					new_invoice, customer_accepts_backorder = create_sales_invoice(edited_line_items, order, customer_code, payment_category, woocommerce_settings, order_type=order_type, temp_address=temp_address, delivery_option=delivery_option, test_order=test_order)

				else:
					frappe.log_error(title="Error in authorized order", message="Cannot recoginized pos_order_type: {}".format(pos_order_type))

		# Create a intergration request
		try:
			log_integration_request(order=order, invoice_doc=new_invoice, status="Completed", data=json.dumps(order), reference_docname=new_invoice.name, woocommerce_settings=woocommerce_settings, test_order=test_order, customer_accepts_backorder=customer_accepts_backorder)
			return "Sales invoice: {} created!".format(new_invoice.name)
		except UnboundLocalError:
			frappe.log_error(title="Error in Woocommerce Integration", message=frappe.get_traceback())
			return "failed"


def create_sales_invoice(edited_line_items, order, customer_code, payment_category,  woocommerce_settings, order_type=None, temp_address=None, delivery_option=None, test_order=0):
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

	# Add Items
	customer_accepts_backorder = set_items_in_sales_invoice(edited_line_items, customer_code, invoice_doc, woocommerce_settings, tax_rate)

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
		invoice_doc.append("items",{
			"item_code": "HAND-FEE",
			"item_name": "Handling Fee",
			"description": "Handling Fee",
			"uom": "Unit",
			"qty": 1,
			"rate": shipping_total,
			"warehouse": woocommerce_settings.warehouse
		})
		addTaxDetails("Actual", invoice_doc, shipping_tax, "Handling Fee tax", woocommerce_settings.tax_account)

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
						"rate": float(shipping_line["total"]),
						"warehouse": woocommerce_settings.warehouse
					})
		desc = "GST 10% @ 10.0"
		addTaxDetails("On Net Total", invoice_doc, 0, desc, woocommerce_settings.tax_account, rate=10, included_in_print_rate=included_in_print_rate)

	invoice_doc.save()

	DocTags("Sales Invoice").add(invoice_doc.name, "WooCommerce Order")

	return invoice_doc, customer_accepts_backorder
	

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

		else: # item["is_stock_item"] == 0 
			invoice_doc.append("items", item)
			if item["item_group"] != "Tests":
				item_tax = (item['rate'] * tax_rate) * item["qty"]



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



def backorder_validation(line_items, customer_code, woocommerce_settings, discount=None):
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
		# if frappe.db.get_value("Customer", customer_code, "default_price_list"):
		# 	price_list = frappe.db.get_value("Customer", customer_code, "default_price_list")
		# 	# consider we could have multiple item price for the same item 
		# 	rate_list = frappe.db.get_list('Item Price', 
		# 		filters=[
		# 			['selling', '=', 1],
		# 			['buying', '=', 0],
		# 			['price_list', '=', price_list],
		# 			['item_code', '=', sku],
		# 			['valid_upto', 'is', 'not set']
		# 		], fields=['price_list_rate']
		# 	)
		# 	if rate_list:
		# 		rate = rate_list[0]
		# 	else:
		# 		frappe.throw("Item Price for {} - {} is not found!".format(sku, price_list))
		# else:
		# 	frappe.throw("Default price list for customer: {} is not found!").format(customer_code)

		validated_item = {
			"item_code": found_item.item_code,
			"item_name": found_item.item_name,
			"description": found_item.item_name,
			"item_group": found_item.item_group,
			"uom": woocommerce_settings.uom or _("Unit"),
			"qty": item.get("quantity"),
			"rate": item.get("price"),
			"warehouse": woocommerce_settings.warehouse,
			"is_stock_item": found_item.is_stock_item
		}

		# add discount
		if discount: # unit is %, so discount would be 20, 30 insetad of 0.2, 0.3
			validated_item["discount_percentage"] = discount
			validated_item["discount_amount"] = discount/100 * validated_item["rate"]
			validated_item["rate"] = validated_item["rate"] - validated_item["discount_amount"]
			validated_item["ignore_pricing_rules"] = 1

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