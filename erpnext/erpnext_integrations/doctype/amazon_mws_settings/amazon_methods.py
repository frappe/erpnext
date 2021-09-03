# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import csv
import math
import time

import dateutil
import frappe
from frappe import _
from six import StringIO

import erpnext.erpnext_integrations.doctype.amazon_mws_settings.amazon_mws_api as mws


#Get and Create Products
def get_products_details():
	products = get_products_instance()
	reports = get_reports_instance()

	mws_settings = frappe.get_doc("Amazon MWS Settings")
	market_place_list = return_as_list(mws_settings.market_place_id)

	for marketplace in market_place_list:
		report_id = request_and_fetch_report_id("_GET_FLAT_FILE_OPEN_LISTINGS_DATA_", None, None, market_place_list)

		if report_id:
			listings_response = reports.get_report(report_id=report_id)

			#Get ASIN Codes
			string_io = StringIO(frappe.safe_decode(listings_response.original))
			csv_rows = list(csv.reader(string_io, delimiter=str('\t')))
			asin_list = list(set([row[1] for row in csv_rows[1:]]))
			#break into chunks of 10
			asin_chunked_list = list(chunks(asin_list, 10))

			#Map ASIN Codes to SKUs
			sku_asin = [{"asin":row[1],"sku":row[0]} for row in csv_rows[1:]]

			#Fetch Products List from ASIN
			for asin_list in asin_chunked_list:
				products_response = call_mws_method(products.get_matching_product,marketplaceid=marketplace,
					asins=asin_list)

				matching_products_list = products_response.parsed
				for product in matching_products_list:
					skus = [row["sku"] for row in sku_asin if row["asin"]==product.ASIN]
					for sku in skus:
						create_item_code(product, sku)

def get_products_instance():
	mws_settings = frappe.get_doc("Amazon MWS Settings")
	products = mws.Products(
			account_id = mws_settings.seller_id,
			access_key = mws_settings.aws_access_key_id,
			secret_key = mws_settings.secret_key,
			region = mws_settings.region,
			domain = mws_settings.domain
			)

	return products

def get_reports_instance():
	mws_settings = frappe.get_doc("Amazon MWS Settings")
	reports = mws.Reports(
			account_id = mws_settings.seller_id,
			access_key = mws_settings.aws_access_key_id,
			secret_key = mws_settings.secret_key,
			region = mws_settings.region,
			domain = mws_settings.domain
	)

	return reports

#returns list as expected by amazon API
def return_as_list(input_value):
	if isinstance(input_value, list):
		return input_value
	else:
		return [input_value]

#function to chunk product data
def chunks(l, n):
	for i in range(0, len(l), n):
		yield l[i:i+n]

def request_and_fetch_report_id(report_type, start_date=None, end_date=None, marketplaceids=None):
	reports = get_reports_instance()
	report_response = reports.request_report(report_type=report_type,
			start_date=start_date,
			end_date=end_date,
			marketplaceids=marketplaceids)

	report_request_id = report_response.parsed["ReportRequestInfo"]["ReportRequestId"]["value"]
	generated_report_id = None
	#poll to get generated report
	for x in range(1,10):
		report_request_list_response = reports.get_report_request_list(requestids=[report_request_id])
		report_status = report_request_list_response.parsed["ReportRequestInfo"]["ReportProcessingStatus"]["value"]

		if report_status == "_SUBMITTED_" or report_status == "_IN_PROGRESS_":
			#add time delay to wait for amazon to generate report
			time.sleep(15)
			continue
		elif report_status == "_CANCELLED_":
			break
		elif report_status == "_DONE_NO_DATA_":
			break
		elif report_status == "_DONE_":
			generated_report_id =  report_request_list_response.parsed["ReportRequestInfo"]["GeneratedReportId"]["value"]
			break
	return generated_report_id

def call_mws_method(mws_method, *args, **kwargs):

	mws_settings = frappe.get_doc("Amazon MWS Settings")
	max_retries = mws_settings.max_retry_limit

	for x in range(0, max_retries):
		try:
			response = mws_method(*args, **kwargs)
			return response
		except Exception as e:
			delay = math.pow(4, x) * 125
			frappe.log_error(message=e, title=f'Method "{mws_method.__name__}" failed')
			time.sleep(delay)
			continue

	mws_settings.enable_sync = 0
	mws_settings.save()

	frappe.throw(_("Sync has been temporarily disabled because maximum retries have been exceeded"))

def create_item_code(amazon_item_json, sku):
	if frappe.db.get_value("Item", sku):
		return

	item = frappe.new_doc("Item")

	new_manufacturer = create_manufacturer(amazon_item_json)
	new_brand = create_brand(amazon_item_json)

	mws_settings = frappe.get_doc("Amazon MWS Settings")

	item.item_code = sku
	item.amazon_item_code = amazon_item_json.ASIN
	item.item_group = mws_settings.item_group
	item.description = amazon_item_json.Product.AttributeSets.ItemAttributes.Title
	item.brand = new_brand
	item.manufacturer = new_manufacturer
	item.web_long_description = amazon_item_json.Product.AttributeSets.ItemAttributes.Title

	item.image = amazon_item_json.Product.AttributeSets.ItemAttributes.SmallImage.URL

	temp_item_group = amazon_item_json.Product.AttributeSets.ItemAttributes.ProductGroup

	item_group = frappe.db.get_value("Item Group",filters={"item_group_name": temp_item_group})

	if not item_group:
		igroup = frappe.new_doc("Item Group")
		igroup.item_group_name = temp_item_group
		igroup.parent_item_group =  mws_settings.item_group
		igroup.insert()

	item.append("item_defaults", {'company':mws_settings.company})

	item.insert(ignore_permissions=True)
	create_item_price(amazon_item_json, item.item_code)

	return item.name

def create_manufacturer(amazon_item_json):
	if not amazon_item_json.Product.AttributeSets.ItemAttributes.Manufacturer:
		return None

	existing_manufacturer = frappe.db.get_value("Manufacturer",
		filters={"short_name":amazon_item_json.Product.AttributeSets.ItemAttributes.Manufacturer})

	if not existing_manufacturer:
		manufacturer = frappe.new_doc("Manufacturer")
		manufacturer.short_name = amazon_item_json.Product.AttributeSets.ItemAttributes.Manufacturer
		manufacturer.insert()
		return manufacturer.short_name
	else:
		return existing_manufacturer

def create_brand(amazon_item_json):
	if not amazon_item_json.Product.AttributeSets.ItemAttributes.Brand:
		return None

	existing_brand = frappe.db.get_value("Brand",
		filters={"brand":amazon_item_json.Product.AttributeSets.ItemAttributes.Brand})
	if not existing_brand:
		brand = frappe.new_doc("Brand")
		brand.brand = amazon_item_json.Product.AttributeSets.ItemAttributes.Brand
		brand.insert()
		return brand.brand
	else:
		return existing_brand

def create_item_price(amazon_item_json, item_code):
	item_price = frappe.new_doc("Item Price")
	item_price.price_list = frappe.db.get_value("Amazon MWS Settings", "Amazon MWS Settings", "price_list")
	if not("ListPrice" in amazon_item_json.Product.AttributeSets.ItemAttributes):
		item_price.price_list_rate = 0
	else:
		item_price.price_list_rate = amazon_item_json.Product.AttributeSets.ItemAttributes.ListPrice.Amount

	item_price.item_code = item_code
	item_price.insert()

#Get and create Orders
def get_orders(after_date):
	try:
		orders = get_orders_instance()
		statuses = ["PartiallyShipped", "Unshipped", "Shipped", "Canceled"]
		mws_settings = frappe.get_doc("Amazon MWS Settings")
		market_place_list = return_as_list(mws_settings.market_place_id)

		orders_response = call_mws_method(orders.list_orders, marketplaceids=market_place_list,
			fulfillment_channels=["MFN", "AFN"],
			lastupdatedafter=after_date,
			orderstatus=statuses,
			max_results='50')

		while True:
			orders_list = []

			if "Order" in orders_response.parsed.Orders:
				orders_list = return_as_list(orders_response.parsed.Orders.Order)

			if len(orders_list) == 0:
				break

			for order in orders_list:
				create_sales_order(order, after_date)

			if not "NextToken" in orders_response.parsed:
				break

			next_token = orders_response.parsed.NextToken
			orders_response = call_mws_method(orders.list_orders_by_next_token, next_token)

	except Exception as e:
		frappe.log_error(title="get_orders", message=e)

def get_orders_instance():
	mws_settings = frappe.get_doc("Amazon MWS Settings")
	orders = mws.Orders(
			account_id = mws_settings.seller_id,
			access_key = mws_settings.aws_access_key_id,
			secret_key = mws_settings.secret_key,
			region= mws_settings.region,
			domain= mws_settings.domain,
			version="2013-09-01"
		)

	return orders

def create_sales_order(order_json,after_date):
	customer_name = create_customer(order_json)
	create_address(order_json, customer_name)

	market_place_order_id = order_json.AmazonOrderId

	so = frappe.db.get_value("Sales Order",
			filters={"amazon_order_id": market_place_order_id},
			fieldname="name")

	taxes_and_charges = frappe.db.get_value("Amazon MWS Settings", "Amazon MWS Settings", "taxes_charges")

	if so:
		return

	if not so:
		items = get_order_items(market_place_order_id)
		delivery_date = dateutil.parser.parse(order_json.LatestShipDate).strftime("%Y-%m-%d")
		transaction_date = dateutil.parser.parse(order_json.PurchaseDate).strftime("%Y-%m-%d")

		so = frappe.get_doc({
				"doctype": "Sales Order",
				"naming_series": "SO-",
				"amazon_order_id": market_place_order_id,
				"marketplace_id": order_json.MarketplaceId,
				"customer": customer_name,
				"delivery_date": delivery_date,
				"transaction_date": transaction_date,
				"items": items,
				"company": frappe.db.get_value("Amazon MWS Settings", "Amazon MWS Settings", "company")
			})

		try:
			if taxes_and_charges:
				charges_and_fees = get_charges_and_fees(market_place_order_id)
				for charge in charges_and_fees.get("charges"):
					so.append('taxes', charge)

				for fee in charges_and_fees.get("fees"):
					so.append('taxes', fee)

			so.insert(ignore_permissions=True)
			so.submit()

		except Exception as e:
			import traceback
			frappe.log_error(message=traceback.format_exc(), title="Create Sales Order")

def create_customer(order_json):
	order_customer_name = ""

	if not("BuyerName" in order_json):
		order_customer_name = "Buyer - " + order_json.AmazonOrderId
	else:
		order_customer_name = order_json.BuyerName

	existing_customer_name = frappe.db.get_value("Customer",
			filters={"name": order_customer_name}, fieldname="name")

	if existing_customer_name:
		filters = [
				["Dynamic Link", "link_doctype", "=", "Customer"],
				["Dynamic Link", "link_name", "=", existing_customer_name],
				["Dynamic Link", "parenttype", "=", "Contact"]
			]

		existing_contacts = frappe.get_list("Contact", filters)

		if existing_contacts:
			pass
		else:
			new_contact = frappe.new_doc("Contact")
			new_contact.first_name = order_customer_name
			new_contact.append('links', {
				"link_doctype": "Customer",
				"link_name": existing_customer_name
			})
			new_contact.insert()

		return existing_customer_name
	else:
		mws_customer_settings = frappe.get_doc("Amazon MWS Settings")
		new_customer = frappe.new_doc("Customer")
		new_customer.customer_name = order_customer_name
		new_customer.customer_group = mws_customer_settings.customer_group
		new_customer.territory = mws_customer_settings.territory
		new_customer.customer_type = mws_customer_settings.customer_type
		new_customer.save()

		new_contact = frappe.new_doc("Contact")
		new_contact.first_name = order_customer_name
		new_contact.append('links', {
			"link_doctype": "Customer",
			"link_name": new_customer.name
		})

		new_contact.insert()

		return new_customer.name

def create_address(amazon_order_item_json, customer_name):

	filters = [
			["Dynamic Link", "link_doctype", "=", "Customer"],
			["Dynamic Link", "link_name", "=", customer_name],
			["Dynamic Link", "parenttype", "=", "Address"]
		]

	existing_address = frappe.get_list("Address", filters)

	if not("ShippingAddress" in amazon_order_item_json):
		return None
	else:
		make_address = frappe.new_doc("Address")

		if "AddressLine1" in amazon_order_item_json.ShippingAddress:
			make_address.address_line1 = amazon_order_item_json.ShippingAddress.AddressLine1
		else:
			make_address.address_line1 = "Not Provided"

		if "City" in amazon_order_item_json.ShippingAddress:
			make_address.city = amazon_order_item_json.ShippingAddress.City
		else:
			make_address.city = "Not Provided"

		if "StateOrRegion" in amazon_order_item_json.ShippingAddress:
			make_address.state = amazon_order_item_json.ShippingAddress.StateOrRegion

		if "PostalCode" in amazon_order_item_json.ShippingAddress:
			make_address.pincode = amazon_order_item_json.ShippingAddress.PostalCode

		for address in existing_address:
			address_doc = frappe.get_doc("Address", address["name"])
			if (address_doc.address_line1 == make_address.address_line1 and
				address_doc.pincode == make_address.pincode):
				return address

		make_address.append("links", {
			"link_doctype": "Customer",
			"link_name": customer_name
		})
		make_address.address_type = "Shipping"
		make_address.insert()

def get_order_items(market_place_order_id):
	mws_orders = get_orders_instance()

	order_items_response = call_mws_method(mws_orders.list_order_items, amazon_order_id=market_place_order_id)
	final_order_items = []

	order_items_list = return_as_list(order_items_response.parsed.OrderItems.OrderItem)

	warehouse = frappe.db.get_value("Amazon MWS Settings", "Amazon MWS Settings", "warehouse")

	while True:
		for order_item in order_items_list:

			if not "ItemPrice" in order_item:
				price = 0
			else:
				price = order_item.ItemPrice.Amount

			final_order_items.append({
				"item_code": get_item_code(order_item),
				"item_name": order_item.SellerSKU,
				"description": order_item.Title,
				"rate": price,
				"qty": order_item.QuantityOrdered,
				"stock_uom": "Nos",
				"warehouse": warehouse,
				"conversion_factor": "1.0"
			})

		if not "NextToken" in order_items_response.parsed:
			break

		next_token = order_items_response.parsed.NextToken

		order_items_response = call_mws_method(mws_orders.list_order_items_by_next_token, next_token)
		order_items_list = return_as_list(order_items_response.parsed.OrderItems.OrderItem)

	return final_order_items

def get_item_code(order_item):
	sku = order_item.SellerSKU
	item_code = frappe.db.get_value("Item", {"item_code": sku}, "item_code")
	if item_code:
		return item_code

def get_charges_and_fees(market_place_order_id):
	finances = get_finances_instance()

	charges_fees = {"charges":[], "fees":[]}

	response = call_mws_method(finances.list_financial_events, amazon_order_id=market_place_order_id)

	shipment_event_list = return_as_list(response.parsed.FinancialEvents.ShipmentEventList)

	for shipment_event in shipment_event_list:
		if shipment_event:
			shipment_item_list = return_as_list(shipment_event.ShipmentEvent.ShipmentItemList.ShipmentItem)

			for shipment_item in shipment_item_list:
				charges, fees = [], []

				if 'ItemChargeList' in shipment_item.keys():
					charges = return_as_list(shipment_item.ItemChargeList.ChargeComponent)

				if 'ItemFeeList' in shipment_item.keys():
					fees = return_as_list(shipment_item.ItemFeeList.FeeComponent)

				for charge in charges:
					if(charge.ChargeType != "Principal") and float(charge.ChargeAmount.CurrencyAmount) != 0:
						charge_account = get_account(charge.ChargeType)
						charges_fees.get("charges").append({
							"charge_type":"Actual",
							"account_head": charge_account,
							"tax_amount": charge.ChargeAmount.CurrencyAmount,
							"description": charge.ChargeType + " for " + shipment_item.SellerSKU
							})

				for fee in fees:
					if float(fee.FeeAmount.CurrencyAmount) != 0:
						fee_account = get_account(fee.FeeType)
						charges_fees.get("fees").append({
							"charge_type":"Actual",
							"account_head": fee_account,
							"tax_amount": fee.FeeAmount.CurrencyAmount,
							"description": fee.FeeType + " for " + shipment_item.SellerSKU
							})

	return charges_fees

def get_finances_instance():

	mws_settings = frappe.get_doc("Amazon MWS Settings")

	finances = mws.Finances(
			account_id = mws_settings.seller_id,
			access_key = mws_settings.aws_access_key_id,
			secret_key = mws_settings.secret_key,
			region= mws_settings.region,
			domain= mws_settings.domain,
			version="2015-05-01"
		)

	return finances

def get_account(name):
	existing_account = frappe.db.get_value("Account", {"account_name": "Amazon {0}".format(name)})
	account_name = existing_account
	mws_settings = frappe.get_doc("Amazon MWS Settings")

	if not existing_account:
		try:
			new_account = frappe.new_doc("Account")
			new_account.account_name = "Amazon {0}".format(name)
			new_account.company = mws_settings.company
			new_account.parent_account = mws_settings.market_place_account_group
			new_account.insert(ignore_permissions=True)
			account_name = new_account.name
		except Exception as e:
			frappe.log_error(message=e, title="Create Account")

	return account_name
