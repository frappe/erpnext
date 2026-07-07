# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe.query_builder import Criterion, DocType, Order
from frappe.utils import cint, get_datetime
from frappe.utils.nestedset import get_root_of

from erpnext.accounts.doctype.pos_invoice.pos_invoice import get_item_group, get_stock_availability
from erpnext.accounts.doctype.pos_profile.pos_profile import get_child_nodes, get_item_groups
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.stock.utils import scan_barcode


def search_by_term(search_term, warehouse, price_list):
	result = search_for_serial_or_batch_or_barcode_number(search_term) or {}

	item_code = result.get("item_code", search_term)
	serial_no = result.get("serial_no", "")
	batch_no = result.get("batch_no", "")
	barcode = result.get("barcode", "")

	if not result:
		return

	item_doc = frappe.get_doc("Item", item_code)

	if not item_doc:
		return

	item = {
		"barcode": barcode,
		"batch_no": batch_no,
		"description": item_doc.description,
		"is_stock_item": item_doc.is_stock_item,
		"item_code": item_doc.name,
		"item_group": item_doc.item_group,
		"item_image": item_doc.image,
		"item_name": item_doc.item_name,
		"serial_no": serial_no,
		"stock_uom": item_doc.stock_uom,
		"uom": item_doc.stock_uom,
	}

	if barcode:
		barcode_info = next(filter(lambda x: x.barcode == barcode, item_doc.get("barcodes", [])), None)
		if barcode_info and barcode_info.uom:
			uom = next(filter(lambda x: x.uom == barcode_info.uom, item_doc.uoms), {})
			item.update(
				{
					"uom": barcode_info.uom,
					"conversion_factor": uom.get("conversion_factor", 1),
				}
			)

	item_stock_qty, is_stock_item, is_negative_stock_allowed = get_stock_availability(item_code, warehouse)
	item_stock_qty = item_stock_qty // item.get("conversion_factor", 1)
	item.update({"actual_qty": item_stock_qty})

	price_filters = {
		"price_list": price_list,
		"item_code": item_code,
	}

	if batch_no:
		price_filters["batch_no"] = ["in", [batch_no, ""]]

	if serial_no:
		price_filters["uom"] = item_doc.stock_uom

	price = frappe.get_list(
		doctype="Item Price",
		filters=price_filters,
		fields=["uom", "currency", "price_list_rate", "batch_no"],
	)

	def __sort(p):
		p_uom = p.get("uom")
		p_batch = p.get("batch_no")
		batch_no = item.get("batch_no")

		if batch_no and p_batch and p_batch == batch_no:
			if p_uom == item.get("uom"):
				return 0
			elif p_uom == item.get("stock_uom"):
				return 1
			else:
				return 2

		if p_uom == item.get("uom"):
			return 3
		elif p_uom == item.get("stock_uom"):
			return 4
		else:
			return 5

	# sort by fallback preference. always pick exact uom and batch number match if available
	price = sorted(price, key=__sort)

	if len(price) > 0:
		p = price.pop(0)
		item.update(
			{
				"currency": p.get("currency"),
				"price_list_rate": p.get("price_list_rate"),
			}
		)

	return {"items": [item]}


def filter_result_items(result, pos_profile):
	if result and result.get("items"):
		pos_profile_doc = frappe.get_cached_doc("POS Profile", pos_profile)
		pos_item_groups = get_item_group(pos_profile_doc)
		if not pos_item_groups:
			return
		result["items"] = [item for item in result.get("items") if item.get("item_group") in pos_item_groups]


@frappe.whitelist()
def get_parent_item_group(pos_profile: str):
	item_groups = get_item_groups(pos_profile)

	if not item_groups:
		item_groups = frappe.get_all("Item Group", {"lft": 1, "is_group": 1}, pluck="name")

	return item_groups[0] if item_groups else None


@frappe.whitelist()
def get_items(
	start: str | int,
	page_length: str | int,
	price_list: str | None,
	item_group: str,
	pos_profile: str,
	search_term: str = "",
):
	warehouse, hide_unavailable_items = frappe.db.get_value(
		"POS Profile", pos_profile, ["warehouse", "hide_unavailable_items"]
	)

	result = []

	if search_term:
		result = search_by_term(search_term, warehouse, price_list) or []
		filter_result_items(result, pos_profile)
		if result:
			return result

	if not frappe.db.exists("Item Group", item_group):
		item_group = get_root_of("Item Group")

	lft, rgt = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"])

	item = frappe.qb.DocType("Item")
	item_group_dt = frappe.qb.DocType("Item Group")

	item_group_subquery = (
		frappe.qb.from_(item_group_dt)
		.select(item_group_dt.name)
		.where((item_group_dt.lft >= lft) & (item_group_dt.rgt <= rgt))
	)

	query = (
		frappe.qb.from_(item)
		.select(
			item.name.as_("item_code"),
			item.item_name,
			item.description,
			item.stock_uom,
			item.image.as_("item_image"),
			item.is_stock_item,
			item.sales_uom,
		)
		.where(
			(item.disabled == 0)
			& (item.has_variants == 0)
			& (item.is_sales_item == 1)
			& (item.is_fixed_asset == 0)
			& (item.item_group.isin(item_group_subquery))
			& get_conditions(search_term, item)
		)
	)

	item_group_condition = get_item_group_condition(pos_profile, item)
	if item_group_condition is not None:
		query = query.where(item_group_condition)

	if hide_unavailable_items:
		bin_dt = frappe.qb.DocType("Bin")
		query = (
			query.left_join(bin_dt)
			.on(bin_dt.item_code == item.name)
			.where(
				(item.is_stock_item == 0)
				| ((item.is_stock_item == 1) & (bin_dt.warehouse == warehouse) & (bin_dt.actual_qty > 0))
			)
		)

	items_data = (
		query.orderby(item.name, order=Order.asc).limit(cint(page_length)).offset(cint(start)).run(as_dict=1)
	)

	# return (empty) list if there are no results
	if not items_data:
		return result

	current_date = frappe.utils.today()

	for item in items_data:
		item.actual_qty, _, is_negative_stock_allowed = get_stock_availability(item.item_code, warehouse)

		ItemPrice = DocType("Item Price")
		item_prices = (
			frappe.qb.from_(ItemPrice)
			.select(
				ItemPrice.price_list_rate,
				ItemPrice.currency,
				ItemPrice.uom,
				ItemPrice.batch_no,
				ItemPrice.valid_from,
				ItemPrice.valid_upto,
			)
			.where(ItemPrice.price_list == price_list)
			.where(ItemPrice.item_code == item.item_code)
			.where(ItemPrice.selling == 1)
			.where((ItemPrice.valid_from <= current_date) | (ItemPrice.valid_from.isnull()))
			.where((ItemPrice.valid_upto >= current_date) | (ItemPrice.valid_upto.isnull()))
			.orderby(ItemPrice.valid_from.isnull(), order=Order.asc)
			.orderby(ItemPrice.valid_from, order=Order.desc)
		).run(as_dict=True)

		stock_uom_price = next((d for d in item_prices if d.get("uom") == item.stock_uom), {})
		item_uom = item.stock_uom
		item_uom_price = stock_uom_price

		if item.sales_uom and item.sales_uom != item.stock_uom:
			item_uom = item.sales_uom
			sales_uom_price = next((d for d in item_prices if d.get("uom") == item.sales_uom), {})
			if sales_uom_price:
				item_uom_price = sales_uom_price

		if item_prices and not item_uom_price:
			item_uom = item_prices[0].get("uom")
			item_uom_price = item_prices[0]

		item_conversion_factor = get_conversion_factor(item.item_code, item_uom).get("conversion_factor")

		if item.stock_uom != item_uom:
			item.actual_qty = item.actual_qty // item_conversion_factor

		if item_uom_price and item_uom != item_uom_price.get("uom"):
			item_uom_price.price_list_rate = item_uom_price.price_list_rate * item_conversion_factor

		result.append(
			{
				**item,
				"price_list_rate": item_uom_price.get("price_list_rate"),
				"currency": item_uom_price.get("currency"),
				"uom": item_uom,
				"batch_no": item_uom_price.get("batch_no"),
			}
		)

	return {"items": result}


@frappe.whitelist()
def search_for_serial_or_batch_or_barcode_number(search_value: str) -> dict[str, str | None]:
	return scan_barcode(search_value)


def get_conditions(search_term, item=None):
	if item is None:
		item = frappe.qb.DocType("Item")

	pattern = f"%{search_term}%"
	conditions = [item.name.like(pattern), item.item_name.like(pattern)]
	conditions += add_search_fields_condition(search_term, item)

	return Criterion.any(conditions)


def add_search_fields_condition(search_term, item=None):
	if item is None:
		item = frappe.qb.DocType("Item")

	pattern = f"%{search_term}%"
	conditions = []
	search_fields = frappe.get_all("POS Search Fields", fields=["fieldname"])
	for field in search_fields:
		if not field.get("fieldname"):
			continue
		conditions.append(item[field["fieldname"]].like(pattern))

	return conditions


def get_item_group_condition(pos_profile, item=None):
	if item is None:
		item = frappe.qb.DocType("Item")

	item_groups = get_item_groups(pos_profile)
	if item_groups:
		return item.item_group.isin(item_groups)

	return None


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_group_query(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	pos_profile = filters.get("pos_profile")

	item_filters = [["name", "like", f"%{txt}%"]]
	if pos_profile:
		item_groups = get_item_groups(pos_profile)
		if item_groups:
			item_filters.append(["name", "in", item_groups])

	return frappe.get_all(
		"Item Group",
		filters=item_filters,
		fields=["name"],
		distinct=True,
		order_by="",  # original raw SQL had no ORDER BY; suppress the injected default (creation desc on MariaDB)
		limit_start=start,
		limit_page_length=page_len,
		as_list=True,
	)


@frappe.whitelist()
def check_opening_entry(user: str):
	open_vouchers = frappe.db.get_all(
		"POS Opening Entry",
		filters={"user": user, "pos_closing_entry": ["in", ["", None]], "docstatus": 1},
		fields=["name", "company", "pos_profile", "period_start_date"],
		order_by="period_start_date desc",
	)

	return open_vouchers


@frappe.whitelist(methods=["POST"])
def create_opening_voucher(pos_profile: str, company: str, balance_details: str | list):
	balance_details = frappe.parse_json(balance_details)

	new_pos_opening = frappe.get_doc(
		{
			"doctype": "POS Opening Entry",
			"period_start_date": frappe.utils.get_datetime(),
			"posting_date": frappe.utils.getdate(),
			"user": frappe.session.user,
			"pos_profile": pos_profile,
			"company": company,
		}
	)
	new_pos_opening.set("balance_details", balance_details)
	new_pos_opening.submit()

	return new_pos_opening.as_dict()


@frappe.whitelist()
def get_past_order_list(search_term: str, status: str, limit: int = 20):
	fields = ["name", "grand_total", "currency", "customer", "customer_name", "posting_time", "posting_date"]
	invoice_list = []

	if search_term and status:
		pos_invoices_by_customer = frappe.db.get_list(
			"POS Invoice",
			filters=get_invoice_filters("POS Invoice", status),
			or_filters={
				"customer_name": ["like", f"%{search_term}%"],
				"customer": ["like", f"%{search_term}%"],
			},
			fields=fields,
			page_length=limit,
		)

		pos_invoices_by_name = frappe.db.get_list(
			"POS Invoice",
			filters=get_invoice_filters("POS Invoice", status, name=search_term),
			fields=fields,
			page_length=limit,
		)

		pos_invoice_list = add_doctype_to_results(
			"POS Invoice", pos_invoices_by_customer + pos_invoices_by_name
		)

		sales_invoices_by_customer = frappe.db.get_list(
			"Sales Invoice",
			filters=get_invoice_filters("Sales Invoice", status),
			or_filters={
				"customer_name": ["like", f"%{search_term}%"],
				"customer": ["like", f"%{search_term}%"],
			},
			fields=fields,
			page_length=limit,
		)
		sales_invoices_by_name = frappe.db.get_list(
			"Sales Invoice",
			filters=get_invoice_filters("Sales Invoice", status, name=search_term),
			fields=fields,
			page_length=limit,
		)

		sales_invoice_list = add_doctype_to_results(
			"Sales Invoice", sales_invoices_by_customer + sales_invoices_by_name
		)

	elif status:
		pos_invoice_list = frappe.db.get_list(
			"POS Invoice",
			filters=get_invoice_filters("POS Invoice", status),
			fields=fields,
			page_length=limit,
		)
		pos_invoice_list = add_doctype_to_results("POS Invoice", pos_invoice_list)

		sales_invoice_list = frappe.db.get_list(
			"Sales Invoice",
			filters=get_invoice_filters("Sales Invoice", status),
			fields=fields,
			page_length=limit,
		)
		sales_invoice_list = add_doctype_to_results("Sales Invoice", sales_invoice_list)

	invoice_list = order_results_by_posting_date([*pos_invoice_list, *sales_invoice_list])

	return invoice_list


@frappe.whitelist(methods=["POST"])
def set_customer_info(fieldname: str, customer: str, value: str = ""):
	customer_doc = frappe.get_doc("Customer", customer)
	customer_doc.check_permission("write")

	if fieldname == "loyalty_program":
		customer_doc.loyalty_program = value
	else:
		contact = customer_doc.get("customer_primary_contact")
		if not contact:
			Contact = DocType("Contact")
			DynamicLink = DocType("Dynamic Link")

			# Inner join with Contact DocType, to priorities records that have is_primary_contact set.
			query = (
				frappe.qb.from_(DynamicLink)
				.join(Contact)
				.on(DynamicLink.parent == Contact.name)
				.select(DynamicLink.parent)
				.where(
					(DynamicLink.link_name == customer)
					& (DynamicLink.parentfield == "links")
					& (DynamicLink.parenttype == "Contact")
					& (DynamicLink.link_doctype == "Customer")
				)
				.orderby(Contact.is_primary_contact, order=Order.desc)
				# tiebreaker: contacts tie on is_primary_contact (the common no-primary case) ->
				# pick the same one on MariaDB and Postgres
				.orderby(DynamicLink.parent, order=Order.asc)
			)

			contacts = query.run(pluck=DynamicLink.parent)

			contact = contacts[0] if contacts else None

		if not contact:
			new_contact = frappe.new_doc("Contact")
			new_contact.is_primary_contact = 1
			new_contact.first_name = customer
			new_contact.set("links", [{"link_doctype": "Customer", "link_name": customer}])
			new_contact.save()
			contact = new_contact.name

		def set_primary_phone_no_email(field, value):
			# Create new record instead deleting existing email or phone_no and setting the new row as primary.
			field_mapper = {
				"email_ids": {"field": "email_id", "primary": "is_primary"},
				"phone_nos": {"field": "phone", "primary": "is_primary_mobile_no"},
			}

			value_already_exists = False
			for d in contact_doc.get(field):
				if d.get(field_mapper[field].get("field")) == value and not value_already_exists:
					d.set(field_mapper[field]["primary"], 1)
					value_already_exists = True
					continue
				d.set(field_mapper[field]["primary"], 0)

			if not value_already_exists:
				contact_doc.append(
					field, {field_mapper[field]["field"]: value, field_mapper[field]["primary"]: 1}
				)

		contact_doc = frappe.get_doc("Contact", contact)
		# setting is_primary_contact = 1 on Contact to refetch the same contact incase it's removed from Customer records.
		contact_doc.set("is_primary_contact", 1)
		if fieldname == "email_id":
			set_primary_phone_no_email("email_ids", value)
		elif fieldname == "mobile_no":
			set_primary_phone_no_email("phone_nos", value)
		# Saving contact_doc to set mobile_no and email.
		contact_doc.save()

		# Auto-fetches from Contact DocType, no need to set values separately.
		customer_doc.customer_primary_contact = contact

	# using save method instead db.set_value which bypasses the validation for loyalty program
	# and auto sets the mobile_no and email field on customer records.
	customer_doc.save()


@frappe.whitelist()
def get_pos_profile_data(pos_profile: str):
	pos_profile = frappe.get_doc("POS Profile", pos_profile)
	pos_profile = pos_profile.as_dict()

	_customer_groups_with_children = []
	for row in pos_profile.customer_groups:
		children = get_child_nodes("Customer Group", row.customer_group)
		_customer_groups_with_children.extend(children)

	pos_profile.customer_groups = _customer_groups_with_children
	return pos_profile


def add_doctype_to_results(doctype, results):
	for result in results:
		result["doctype"] = doctype

	return results


def order_results_by_posting_date(results):
	return sorted(
		results,
		key=lambda x: get_datetime(f"{x.get('posting_date')} {x.get('posting_time')}"),
		reverse=True,
	)


def get_invoice_filters(doctype, status, name=None):
	filters = {}

	if name:
		filters["name"] = ["like", f"%{name}%"]
	if doctype == "POS Invoice":
		filters["status"] = status
		if status == "Partly Paid":
			filters["status"] = ["in", ["Partly Paid", "Overdue", "Unpaid"]]
		return filters

	if doctype == "Sales Invoice":
		filters["is_created_using_pos"] = 1
		filters["is_consolidated"] = 0

		if status == "Consolidated":
			filters["pos_closing_entry"] = ["is", "set"]
		else:
			filters["pos_closing_entry"] = ["is", "not set"]
			if status == "Draft":
				filters["docstatus"] = 0
			elif status == "Partly Paid":
				filters["status"] = ["in", ["Partly Paid", "Overdue", "Unpaid"]]
			else:
				filters["docstatus"] = 1
				if status == "Paid":
					filters["is_return"] = 0
				if status == "Return":
					filters["is_return"] = 1

	return filters


@frappe.whitelist()
def get_customer_recent_transactions(customer: str):
	sales_invoices = frappe.db.get_list(
		"Sales Invoice",
		filters={
			"customer": customer,
			"docstatus": 1,
			"is_pos": 1,
			"is_consolidated": 0,
			"is_created_using_pos": 1,
		},
		fields=["name", "grand_total", "status", "posting_date", "posting_time", "currency"],
		page_length=20,
	)

	pos_invoices = frappe.db.get_list(
		"POS Invoice",
		filters={"customer": customer, "docstatus": 1},
		fields=["name", "grand_total", "status", "posting_date", "posting_time", "currency"],
		page_length=20,
	)

	invoices = order_results_by_posting_date(sales_invoices + pos_invoices)
	return invoices
