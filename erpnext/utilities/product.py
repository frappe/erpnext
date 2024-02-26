# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.query_builder.functions import IfNull
from frappe.utils import cint, flt, fmt_money, getdate, nowdate

from erpnext.accounts.doctype.pricing_rule.pricing_rule import get_pricing_rule_for_item
from erpnext.stock.doctype.batch.batch import get_batch_qty
from erpnext.stock.doctype.warehouse.warehouse import get_child_warehouses


def get_web_item_qty_in_stock(item_code, item_warehouse_field, warehouse=None):
	template_item_code, is_stock_item = frappe.db.get_value(
		"Item", item_code, ["variant_of", "is_stock_item"]
	)

	if not warehouse:
		warehouse = frappe.db.get_value("Website Item", {"item_code": item_code}, item_warehouse_field)

	if not warehouse and template_item_code and template_item_code != item_code:
		warehouse = frappe.db.get_value(
			"Website Item", {"item_code": template_item_code}, item_warehouse_field
		)

	if warehouse and frappe.get_cached_value("Warehouse", warehouse, "is_group") == 1:
		warehouses = get_child_warehouses(warehouse)
	else:
		warehouses = [warehouse] if warehouse else []

	total_stock = 0.0
	if warehouses:
		qty_field = (
			"actual_qty"
			if frappe.db.get_single_value("E Commerce Settings", "show_actual_qty")
			else "projected_qty"
		)

		BIN = frappe.qb.DocType("Bin")
		ITEM = frappe.qb.DocType("Item")
		UOM = frappe.qb.DocType("UOM Conversion Detail")

		for warehouse in warehouses:
			stock_qty = (
				frappe.qb.from_(BIN)
				.select(BIN[qty_field] / IfNull(UOM.conversion_factor, 1))
				.inner_join(ITEM)
				.on(BIN.item_code == ITEM.item_code)
				.left_join(UOM)
				.on((ITEM.sales_uom == UOM.uom) & (UOM.parent == ITEM.item_code))
				.where((BIN.item_code == item_code) & (BIN.warehouse == warehouse))
			).run()

			if stock_qty:
				stock_qty = flt(stock_qty[0][0])
				total_stock += adjust_qty_for_expired_items(item_code, stock_qty, warehouse)

	in_stock = int(total_stock > 0)

	return frappe._dict(
		{"in_stock": in_stock, "stock_qty": total_stock, "is_stock_item": is_stock_item}
	)


def adjust_qty_for_expired_items(item_code, stock_qty, warehouse):
	batches = frappe.get_all("Batch", filters={"item": item_code}, fields=["expiry_date", "name"])
	expired_batches = get_expired_batches(batches)

	for batch in expired_batches:
		if warehouse:
			stock_qty = max(0, stock_qty - get_batch_qty(batch, warehouse))
		else:
			stock_qty = max(0, stock_qty - qty_from_all_warehouses(get_batch_qty(batch)))

	return stock_qty


def get_expired_batches(batches):
	"""
	:param batches: A list of dict in the form [{'expiry_date': datetime.date(20XX, 1, 1), 'name': 'batch_id'}, ...]
	"""
	return [b.name for b in batches if b.expiry_date and b.expiry_date <= getdate(nowdate())]


def qty_from_all_warehouses(batch_info):
	"""
	:param batch_info: A list of dict in the form [{u'warehouse': u'Stores - I', u'qty': 0.8}, ...]
	"""
	qty = 0
	for batch in batch_info:
		qty = qty + batch.qty

	return qty


def get_price(item_code, price_list, customer_group, company, qty=1):
	from erpnext.e_commerce.shopping_cart.cart import get_party

	template_item_code = frappe.db.get_value("Item", item_code, "variant_of")

	if price_list:
		price = frappe.get_all(
			"Item Price",
			fields=["price_list_rate", "currency"],
			filters={"price_list": price_list, "item_code": item_code},
		)

		if template_item_code and not price:
			price = frappe.get_all(
				"Item Price",
				fields=["price_list_rate", "currency"],
				filters={"price_list": price_list, "item_code": template_item_code},
			)

		if price:
			party = get_party()
			pricing_rule_dict = frappe._dict(
				{
					"item_code": item_code,
					"qty": qty,
					"stock_qty": qty,
					"transaction_type": "selling",
					"price_list": price_list,
					"customer_group": customer_group,
					"company": company,
					"conversion_rate": 1,
					"for_shopping_cart": True,
					"currency": frappe.db.get_value("Price List", price_list, "currency"),
					"doctype": "Quotation",
				}
			)

			if party and party.doctype == "Customer":
				pricing_rule_dict.update({"customer": party.name})

			pricing_rule = get_pricing_rule_for_item(pricing_rule_dict)
			price_obj = price[0]

			if pricing_rule:
				# price without any rules applied
				mrp = price_obj.price_list_rate or 0

				if pricing_rule.pricing_rule_for == "Discount Percentage":
					price_obj.discount_percent = pricing_rule.discount_percentage
					price_obj.formatted_discount_percent = str(flt(pricing_rule.discount_percentage, 0)) + "%"
					price_obj.price_list_rate = flt(
						price_obj.price_list_rate * (1.0 - (flt(pricing_rule.discount_percentage) / 100.0))
					)

				if pricing_rule.pricing_rule_for == "Rate":
					rate_discount = flt(mrp) - flt(pricing_rule.price_list_rate)
					if rate_discount > 0:
						price_obj.formatted_discount_rate = fmt_money(rate_discount, currency=price_obj["currency"])
					price_obj.price_list_rate = pricing_rule.price_list_rate or 0

			if price_obj:
				price_obj["formatted_price"] = fmt_money(
					price_obj["price_list_rate"], currency=price_obj["currency"]
				)
				if mrp != price_obj["price_list_rate"]:
					price_obj["formatted_mrp"] = fmt_money(mrp, currency=price_obj["currency"])

				price_obj["currency_symbol"] = (
					not cint(frappe.db.get_default("hide_currency_symbol"))
					and (
						frappe.db.get_value("Currency", price_obj.currency, "symbol", cache=True)
						or price_obj.currency
					)
					or ""
				)

				uom_conversion_factor = frappe.db.sql(
					"""select	C.conversion_factor
					from `tabUOM Conversion Detail` C
					inner join `tabItem` I on C.parent = I.name and C.uom = I.sales_uom
					where I.name = %s""",
					item_code,
				)

				uom_conversion_factor = uom_conversion_factor[0][0] if uom_conversion_factor else 1
				price_obj["formatted_price_sales_uom"] = fmt_money(
					price_obj["price_list_rate"] * uom_conversion_factor, currency=price_obj["currency"]
				)

				if not price_obj["price_list_rate"]:
					price_obj["price_list_rate"] = 0

				if not price_obj["currency"]:
					price_obj["currency"] = ""

				if not price_obj["formatted_price"]:
					price_obj["formatted_price"], price_obj["formatted_mrp"] = "", ""

			return price_obj


def get_non_stock_item_status(item_code, item_warehouse_field):
	# if item is a product bundle, check if its bundle items are in stock
	if frappe.db.exists("Product Bundle", item_code):
		items = frappe.get_doc("Product Bundle", item_code).get_all_children()
		bundle_warehouse = frappe.db.get_value(
			"Website Item", {"item_code": item_code}, item_warehouse_field
		)
		return all(
			get_web_item_qty_in_stock(d.item_code, item_warehouse_field, bundle_warehouse).in_stock
			for d in items
		)
	else:
		return 1
