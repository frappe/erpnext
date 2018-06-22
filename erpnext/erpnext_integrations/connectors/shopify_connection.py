from __future__ import unicode_literals
import frappe
from frappe import _
import json
from frappe.utils import cstr, cint, nowdate, flt
from erpnext.erpnext_integrations.utils import validate_webhooks_request
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note, make_sales_invoice
from erpnext.erpnext_integrations.doctype.shopify_settings.sync_product import sync_item_from_shopify
from erpnext.erpnext_integrations.doctype.shopify_settings.sync_customer import create_customer
from erpnext.erpnext_integrations.doctype.shopify_log.shopify_log import make_shopify_log, dump_request_data

@frappe.whitelist(allow_guest=True)
@validate_webhooks_request("Shopify Settings", 'X-Shopify-Hmac-Sha256', secret_key='shared_secret')
def store_request_data(order=None, event=None):
	if frappe.request:
		order = json.loads(frappe.request.data)
		event = frappe.request.headers.get('X-Shopify-Topic')

	dump_request_data(order, event)

def sync_sales_order(order, request_id=None):
	shopify_settings = frappe.get_doc("Shopify Settings")
	frappe.flags.request_id = request_id

	if not frappe.db.get_value("Sales Order", filters={"shopify_order_id": cstr(order['id'])}):
		try:
			validate_customer(order, shopify_settings)
			validate_item(order, shopify_settings)
			create_order(order, shopify_settings)
		except Exception as e:
			make_shopify_log(status="Error", message=e.message, exception=False)
		else:
			make_shopify_log(status="Success")

def prepare_sales_invoice(order, request_id=None):
	shopify_settings = frappe.get_doc("Shopify Settings")
	frappe.flags.request_id = request_id

	try:
		sales_order = get_sales_order(cstr(order['id']))
		if sales_order:
			create_sales_invoice(order, shopify_settings, sales_order)
		make_shopify_log(status="Success")
	except Exception:
		make_shopify_log(status="Error", exception=True)

def prepare_delivery_note(order, request_id=None):
	shopify_settings = frappe.get_doc("Shopify Settings")
	frappe.flags.request_id = request_id

	try:
		sales_order = get_sales_order(cstr(order['id']))
		if sales_order:
			create_delivery_note(order, shopify_settings, sales_order)
		make_shopify_log(status="Success")
	except Exception:
		make_shopify_log(status="Error", exception=True)

def get_sales_order(shopify_order_id):
	sales_order = frappe.db.get_value("Sales Order", filters={"shopify_order_id": shopify_order_id})
	if sales_order:
		so = frappe.get_doc("Sales Order", sales_order)
		return so

def validate_customer(order, shopify_settings):
	customer_id = order.get("customer", {}).get("id")
	if customer_id:
		if not frappe.db.get_value("Customer", {"shopify_customer_id": customer_id}, "name"):
			create_customer(order.get("customer"), shopify_settings)

def validate_item(order, shopify_settings):
	for item in order.get("line_items"):
		if item.get("product_id") and not frappe.db.get_value("Item", {"shopify_product_id": item.get("product_id")}, "name"):
			sync_item_from_shopify(shopify_settings, item)

def create_order(order, shopify_settings, company=None):
	so = create_sales_order(order, shopify_settings, company)
	if so:
		if order.get("financial_status") == "paid":
			create_sales_invoice(order, shopify_settings, so)

		if order.get("fulfillments"):
			create_delivery_note(order, shopify_settings, so)

def create_sales_order(shopify_order, shopify_settings, company=None):
	product_not_exists = []
	customer = frappe.db.get_value("Customer", {"shopify_customer_id": shopify_order.get("customer", {}).get("id")}, "name")
	so = frappe.db.get_value("Sales Order", {"shopify_order_id": shopify_order.get("id")}, "name")

	if not so:
		items = get_order_items(shopify_order.get("line_items"), shopify_settings)

		if not items:
			message = 'Following items are exists in order but relevant record not found in Product master'
			message += "\n" + ", ".join(product_not_exists)

			make_shopify_log(status="Error", message=message, exception=True)

			return ''

		so = frappe.get_doc({
			"doctype": "Sales Order",
			"naming_series": shopify_settings.sales_order_series or "SO-Shopify-",
			"shopify_order_id": shopify_order.get("id"),
			"customer": customer or shopify_settings.default_customer,
			"delivery_date": nowdate(),
			"company": shopify_settings.company,
			"selling_price_list": shopify_settings.price_list,
			"ignore_pricing_rule": 1,
			"items": items,
			"taxes": get_order_taxes(shopify_order, shopify_settings),
			"apply_discount_on": "Grand Total",
			"discount_amount": get_discounted_amount(shopify_order),
		})

		if company:
			so.update({
				"company": company,
				"status": "Draft"
			})
		so.flags.ignore_mandatory = True
		so.save(ignore_permissions=True)
		so.submit()

	else:
		so = frappe.get_doc("Sales Order", so)
	
	frappe.db.commit()
	return so

def create_sales_invoice(shopify_order, shopify_settings, so):
	if not frappe.db.get_value("Sales Invoice", {"shopify_order_id": shopify_order.get("id")}, "name")\
		and so.docstatus==1 and not so.per_billed and cint(shopify_settings.sync_sales_invoice):

		si = make_sales_invoice(so.name, ignore_permissions=True)
		si.shopify_order_id = shopify_order.get("id")
		si.naming_series = shopify_settings.sales_invoice_series or "SI-Shopify-"
		si.flags.ignore_mandatory = True
		set_cost_center(si.items, shopify_settings.cost_center)
		si.submit()
		make_payament_entry_against_sales_invoice(si, shopify_settings)
		frappe.db.commit()

def set_cost_center(items, cost_center):
	for item in items:
		item.cost_center = cost_center

def make_payament_entry_against_sales_invoice(doc, shopify_settings):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
	payemnt_entry = get_payment_entry(doc.doctype, doc.name, bank_account=shopify_settings.cash_bank_account)
	payemnt_entry.flags.ignore_mandatory = True
	payemnt_entry.reference_no = doc.name
	payemnt_entry.reference_date = nowdate()
	payemnt_entry.submit()

def create_delivery_note(shopify_order, shopify_settings, so):
	if not cint(shopify_settings.sync_delivery_note):
		return

	for fulfillment in shopify_order.get("fulfillments"):
		if not frappe.db.get_value("Delivery Note", {"shopify_fulfillment_id": fulfillment.get("id")}, "name")\
			and so.docstatus==1:

			dn = make_delivery_note(so.name)
			dn.shopify_order_id = fulfillment.get("order_id")
			dn.shopify_fulfillment_id = fulfillment.get("id")
			dn.naming_series = shopify_settings.delivery_note_series or "DN-Shopify-"
			dn.items = get_fulfillment_items(dn.items, fulfillment.get("line_items"), shopify_settings)
			dn.flags.ignore_mandatory = True
			dn.save()
			frappe.db.commit()

def get_fulfillment_items(dn_items, fulfillment_items, shopify_settings):
	return [dn_item.update({"qty": item.get("quantity")}) for item in fulfillment_items for dn_item in dn_items\
			if get_item_code(item) == dn_item.item_code]

def get_discounted_amount(order):
	discounted_amount = 0.0
	for discount in order.get("discount_codes"):
		discounted_amount += flt(discount.get("amount"))
	return discounted_amount

def get_order_items(order_items, shopify_settings):
	items = []
	all_product_exists = True
	product_not_exists = []

	for shopify_item in order_items:
		if not shopify_item.get('product_exists'):
			all_product_exists = False
			product_not_exists.append({'title':shopify_item.get('title'),
				'shopify_order_id': shopify_item.get('id')})
			continue

		if all_product_exists:
			item_code = get_item_code(shopify_item)
			items.append({
				"item_code": item_code,
				"item_name": shopify_item.get("name"),
				"rate": shopify_item.get("price"),
				"delivery_date": nowdate(),
				"qty": shopify_item.get("quantity"),
				"stock_uom": shopify_item.get("sku"),
				"warehouse": shopify_settings.warehouse
			})
		else:
			items = []

	return items

def get_item_code(shopify_item):
	item_code = frappe.db.get_value("Item", {"shopify_variant_id": shopify_item.get("variant_id")}, "item_code")
	if not item_code:
		item_code = frappe.db.get_value("Item", {"shopify_product_id": shopify_item.get("product_id")}, "item_code")
	if not item_code:
		item_code = frappe.db.get_value("Item", {"item_name": shopify_item.get("title")}, "item_code")

	return item_code

def get_order_taxes(shopify_order, shopify_settings):
	taxes = []
	for tax in shopify_order.get("tax_lines"):
		taxes.append({
			"charge_type": _("On Net Total"),
			"account_head": get_tax_account_head(tax),
			"description": "{0} - {1}%".format(tax.get("title"), tax.get("rate") * 100.0),
			"rate": tax.get("rate") * 100.00,
			"included_in_print_rate": 1 if shopify_order.get("taxes_included") else 0,
			"cost_center": shopify_settings.cost_center
		})

	taxes = update_taxes_with_shipping_lines(taxes, shopify_order.get("shipping_lines"), shopify_settings)

	return taxes

def update_taxes_with_shipping_lines(taxes, shipping_lines, shopify_settings):
	for shipping_charge in shipping_lines:
		taxes.append({
			"charge_type": _("Actual"),
			"account_head": get_tax_account_head(shipping_charge),
			"description": shipping_charge["title"],
			"tax_amount": shipping_charge["price"],
			"cost_center": shopify_settings.cost_center
		})

	return taxes

def get_tax_account_head(tax):
	tax_title = tax.get("title").encode("utf-8")

	tax_account =  frappe.db.get_value("Shopify Tax Account", \
		{"parent": "Shopify Settings", "shopify_tax": tax_title}, "tax_account")

	if not tax_account:
		frappe.throw("Tax Account not specified for Shopify Tax {0}".format(tax.get("title")))

	return tax_account
