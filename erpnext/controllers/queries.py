# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
from collections import OrderedDict, defaultdict

import frappe
from frappe import qb, scrub
from frappe.desk.reportview import get_filters_cond, get_match_cond
from frappe.query_builder import Criterion, CustomFunction
from frappe.query_builder.functions import Concat, Locate, Sum
from frappe.utils import nowdate, today, unique
from pypika import Order

import erpnext
from erpnext.stock.get_item_details import _get_item_tax_template


# searches for active employees
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def employee_query(doctype, txt, searchfield, start, page_len, filters):
	doctype = "Employee"
	conditions = []
	fields = get_fields(doctype, ["name", "employee_name"])

	return frappe.db.sql(
		"""select {fields} from `tabEmployee`
		where status in ('Active', 'Suspended')
			and docstatus < 2
			and ({key} like %(txt)s
				or employee_name like %(txt)s)
			{fcond} {mcond}
		order by
			(case when locate(%(_txt)s, name) > 0 then locate(%(_txt)s, name) else 99999 end),
			(case when locate(%(_txt)s, employee_name) > 0 then locate(%(_txt)s, employee_name) else 99999 end),
			idx desc,
			name, employee_name
		limit %(page_len)s offset %(start)s""".format(
			**{
				"fields": ", ".join(fields),
				"key": searchfield,
				"fcond": get_filters_cond(doctype, filters, conditions),
				"mcond": get_match_cond(doctype),
			}
		),
		{"txt": "%%%s%%" % txt, "_txt": txt.replace("%", ""), "start": start, "page_len": page_len},
	)


# searches for leads which are not converted
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def lead_query(doctype, txt, searchfield, start, page_len, filters):
	doctype = "Lead"
	fields = get_fields(doctype, ["name", "lead_name", "company_name"])

	searchfields = frappe.get_meta(doctype).get_search_fields()
	searchfields = " or ".join(field + " like %(txt)s" for field in searchfields)

	return frappe.db.sql(
		"""select {fields} from `tabLead`
		where docstatus < 2
			and ifnull(status, '') != 'Converted'
			and ({key} like %(txt)s
				or lead_name like %(txt)s
				or company_name like %(txt)s
				or {scond})
			{mcond}
		order by
			(case when locate(%(_txt)s, name) > 0 then locate(%(_txt)s, name) else 99999 end),
			(case when locate(%(_txt)s, lead_name) > 0 then locate(%(_txt)s, lead_name) else 99999 end),
			(case when locate(%(_txt)s, company_name) > 0 then locate(%(_txt)s, company_name) else 99999 end),
			idx desc,
			name, lead_name
		limit %(page_len)s offset %(start)s""".format(
			**{
				"fields": ", ".join(fields),
				"key": searchfield,
				"scond": searchfields,
				"mcond": get_match_cond(doctype),
			}
		),
		{"txt": "%%%s%%" % txt, "_txt": txt.replace("%", ""), "start": start, "page_len": page_len},
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def tax_account_query(doctype, txt, searchfield, start, page_len, filters):
	doctype = "Account"
	company_currency = erpnext.get_company_currency(filters.get("company"))

	def get_accounts(with_account_type_filter):
		account_type_condition = ""
		if with_account_type_filter:
			account_type_condition = "AND account_type in %(account_types)s"

		accounts = frappe.db.sql(
			f"""
			SELECT name, parent_account
			FROM `tabAccount`
			WHERE `tabAccount`.docstatus!=2
				{account_type_condition}
				AND is_group = 0
				AND company = %(company)s
				AND disabled = %(disabled)s
				AND (account_currency = %(currency)s or ifnull(account_currency, '') = '')
				AND `{searchfield}` LIKE %(txt)s
				{get_match_cond(doctype)}
			ORDER BY idx DESC, name
			LIMIT %(limit)s offset %(offset)s
		""",
			dict(
				account_types=filters.get("account_type"),
				company=filters.get("company"),
				disabled=filters.get("disabled", 0),
				currency=company_currency,
				txt=f"%{txt}%",
				offset=start,
				limit=page_len,
			),
		)

		return accounts

	tax_accounts = get_accounts(True)

	if not tax_accounts:
		tax_accounts = get_accounts(False)

	return tax_accounts


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	doctype = "Item"
	conditions = []

	if isinstance(filters, str):
		filters = json.loads(filters)

	# Get searchfields from meta and use in Item Link field query
	meta = frappe.get_meta(doctype, cached=True)
	searchfields = meta.get_search_fields()

	columns = ""
	extra_searchfields = [field for field in searchfields if field not in ["name", "description"]]

	if extra_searchfields:
		columns += ", " + ", ".join(extra_searchfields)

	if "description" in searchfields:
		columns += """, if(length(tabItem.description) > 40, \
			concat(substr(tabItem.description, 1, 40), "..."), description) as description"""

	searchfields = searchfields + [
		field
		for field in [searchfield or "name", "item_code", "item_group", "item_name"]
		if field not in searchfields
	]
	searchfields = " or ".join([field + " like %(txt)s" for field in searchfields])

	if filters and isinstance(filters, dict):
		if filters.get("customer") or filters.get("supplier"):
			party = filters.get("customer") or filters.get("supplier")
			item_rules_list = frappe.get_all(
				"Party Specific Item",
				filters={"party": party},
				fields=["restrict_based_on", "based_on_value"],
			)

			filters_dict = {}
			for rule in item_rules_list:
				if rule["restrict_based_on"] == "Item":
					rule["restrict_based_on"] = "name"
				filters_dict[rule.restrict_based_on] = []

			for rule in item_rules_list:
				filters_dict[rule.restrict_based_on].append(rule.based_on_value)

			for filter in filters_dict:
				filters[scrub(filter)] = ["in", filters_dict[filter]]

			if filters.get("customer"):
				del filters["customer"]
			else:
				del filters["supplier"]
		else:
			filters.pop("customer", None)
			filters.pop("supplier", None)

	description_cond = ""
	if frappe.db.count(doctype, cache=True) < 50000:
		# scan description only if items are less than 50000
		description_cond = "or tabItem.description LIKE %(txt)s"

	return frappe.db.sql(
		"""select
			tabItem.name {columns}
		from tabItem
		where tabItem.docstatus < 2
			and tabItem.disabled=0
			and tabItem.has_variants=0
			and (tabItem.end_of_life > %(today)s or ifnull(tabItem.end_of_life, '0000-00-00')='0000-00-00')
			and ({scond} or tabItem.item_code IN (select parent from `tabItem Barcode` where barcode LIKE %(txt)s)
				{description_cond})
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, item_name), locate(%(_txt)s, item_name), 99999),
			idx desc,
			name, item_name
		limit %(start)s, %(page_len)s """.format(
			columns=columns,
			scond=searchfields,
			fcond=get_filters_cond(doctype, filters, conditions).replace("%", "%%"),
			mcond=get_match_cond(doctype).replace("%", "%%"),
			description_cond=description_cond,
		),
		{
			"today": nowdate(),
			"txt": "%%%s%%" % txt,
			"_txt": txt.replace("%", ""),
			"start": start,
			"page_len": page_len,
		},
		as_dict=as_dict,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def bom(doctype, txt, searchfield, start, page_len, filters):
	doctype = "BOM"
	conditions = []
	fields = get_fields(doctype, ["name", "item"])

	return frappe.db.sql(
		"""select {fields}
		from `tabBOM`
		where `tabBOM`.docstatus=1
			and `tabBOM`.is_active=1
			and `tabBOM`.`{key}` like %(txt)s
			{fcond} {mcond}
		order by
			(case when locate(%(_txt)s, name) > 0 then locate(%(_txt)s, name) else 99999 end),
			idx desc, name
		limit %(page_len)s offset %(start)s""".format(
			fields=", ".join(fields),
			fcond=get_filters_cond(doctype, filters, conditions).replace("%", "%%"),
			mcond=get_match_cond(doctype).replace("%", "%%"),
			key=searchfield,
		),
		{
			"txt": "%" + txt + "%",
			"_txt": txt.replace("%", ""),
			"start": start or 0,
			"page_len": page_len or 20,
		},
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_project_name(doctype, txt, searchfield, start, page_len, filters):
	proj = qb.DocType("Project")
	qb_filter_and_conditions = []
	qb_filter_or_conditions = []
	ifelse = CustomFunction("IF", ["condition", "then", "else"])

	if filters and filters.get("customer"):
		qb_filter_and_conditions.append(
			(proj.customer == filters.get("customer")) | proj.customer.isnull() | proj.customer == ""
		)

	qb_filter_and_conditions.append(proj.status.notin(["Completed", "Cancelled"]))

	q = qb.from_(proj)

	fields = get_fields(doctype, ["name", "project_name"])
	for x in fields:
		q = q.select(proj[x])

	# don't consider 'customer' and 'status' fields for pattern search, as they must be exactly matched
	searchfields = [
		x for x in frappe.get_meta(doctype).get_search_fields() if x not in ["customer", "status"]
	]

	# pattern search
	if txt:
		for x in searchfields:
			qb_filter_or_conditions.append(proj[x].like(f"%{txt}%"))

	q = q.where(Criterion.all(qb_filter_and_conditions)).where(Criterion.any(qb_filter_or_conditions))

	# ordering
	if txt:
		# project_name containing search string 'txt' will be given higher precedence
		q = q.orderby(ifelse(Locate(txt, proj.project_name) > 0, Locate(txt, proj.project_name), 99999))
	q = q.orderby(proj.idx, order=Order.desc).orderby(proj.name)

	if page_len:
		q = q.limit(page_len)

	if start:
		q = q.offset(start)
	return q.run()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_delivery_notes_to_be_billed(doctype, txt, searchfield, start, page_len, filters, as_dict):
	doctype = "Delivery Note"
	fields = get_fields(doctype, ["name", "customer", "posting_date"])

	return frappe.db.sql(
		"""
		select {fields}
		from `tabDelivery Note`
		where `tabDelivery Note`.`{key}` like {txt} and
			`tabDelivery Note`.docstatus = 1
			and status not in ('Stopped', 'Closed') {fcond}
			and (
				(`tabDelivery Note`.is_return = 0 and `tabDelivery Note`.per_billed < 100)
				or (`tabDelivery Note`.grand_total = 0 and `tabDelivery Note`.per_billed < 100)
				or (
					`tabDelivery Note`.is_return = 1
					and return_against in (select name from `tabDelivery Note` where per_billed < 100)
				)
			)
			{mcond} order by `tabDelivery Note`.`{key}` asc limit {page_len} offset {start}
	""".format(
			fields=", ".join([f"`tabDelivery Note`.{f}" for f in fields]),
			key=searchfield,
			fcond=get_filters_cond(doctype, filters, []),
			mcond=get_match_cond(doctype),
			start=start,
			page_len=page_len,
			txt="%(txt)s",
		),
		{"txt": ("%%%s%%" % txt)},
		as_dict=as_dict,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_batch_no(doctype, txt, searchfield, start, page_len, filters):
	doctype = "Batch"
	meta = frappe.get_meta(doctype, cached=True)
	searchfields = meta.get_search_fields()
	page_len = 30

	batches = get_batches_from_stock_ledger_entries(searchfields, txt, filters, start, page_len)
	batches.extend(get_batches_from_serial_and_batch_bundle(searchfields, txt, filters, start, page_len))

	filtered_batches = get_filterd_batches(batches)

	if filters.get("is_inward"):
		filtered_batches.extend(get_empty_batches(filters, start, page_len, filtered_batches, txt))

	return filtered_batches


def get_empty_batches(filters, start, page_len, filtered_batches=None, txt=None):
	query_filter = {"item": filters.get("item_code")}
	if txt:
		query_filter["name"] = ("like", f"%{txt}%")

	exclude_batches = [batch[0] for batch in filtered_batches] if filtered_batches else []
	if exclude_batches:
		query_filter["name"] = ("not in", exclude_batches)

	return frappe.get_all(
		"Batch",
		fields=["name", "batch_qty"],
		filters=query_filter,
		limit_start=start,
		limit_page_length=page_len,
		as_list=1,
	)


def get_filterd_batches(data):
	batches = OrderedDict()

	for batch_data in data:
		if batch_data[0] not in batches:
			batches[batch_data[0]] = list(batch_data)
		else:
			batches[batch_data[0]][1] += batch_data[1]

	filterd_batch = []
	for _batch, batch_data in batches.items():
		if batch_data[1] > 0:
			filterd_batch.append(tuple(batch_data))

	return filterd_batch


def get_batches_from_stock_ledger_entries(searchfields, txt, filters, start=0, page_len=100):
	stock_ledger_entry = frappe.qb.DocType("Stock Ledger Entry")
	batch_table = frappe.qb.DocType("Batch")

	expiry_date = filters.get("posting_date") or today()

	query = (
		frappe.qb.from_(stock_ledger_entry)
		.inner_join(batch_table)
		.on(batch_table.name == stock_ledger_entry.batch_no)
		.select(
			stock_ledger_entry.batch_no,
			Sum(stock_ledger_entry.actual_qty).as_("qty"),
		)
		.where((batch_table.expiry_date >= expiry_date) | (batch_table.expiry_date.isnull()))
		.where(stock_ledger_entry.is_cancelled == 0)
		.where(
			(stock_ledger_entry.item_code == filters.get("item_code"))
			& (batch_table.disabled == 0)
			& (stock_ledger_entry.batch_no.isnotnull())
		)
		.groupby(stock_ledger_entry.batch_no, stock_ledger_entry.warehouse)
		.having(Sum(stock_ledger_entry.actual_qty) != 0)
		.offset(start)
		.limit(page_len)
	)

	query = query.select(
		Concat("MFG-", batch_table.manufacturing_date).as_("manufacturing_date"),
		Concat("EXP-", batch_table.expiry_date).as_("expiry_date"),
	)

	if filters.get("warehouse"):
		query = query.where(stock_ledger_entry.warehouse == filters.get("warehouse"))

	for field in searchfields:
		query = query.select(batch_table[field])

	if txt:
		txt_condition = batch_table.name.like(f"%{txt}%")
		for field in [*searchfields, "name"]:
			txt_condition |= batch_table[field].like(f"%{txt}%")

		query = query.where(txt_condition)

	return query.run(as_list=1) or []


def get_batches_from_serial_and_batch_bundle(searchfields, txt, filters, start=0, page_len=100):
	bundle = frappe.qb.DocType("Serial and Batch Entry")
	stock_ledger_entry = frappe.qb.DocType("Stock Ledger Entry")
	batch_table = frappe.qb.DocType("Batch")

	expiry_date = filters.get("posting_date") or today()

	bundle_query = (
		frappe.qb.from_(bundle)
		.inner_join(stock_ledger_entry)
		.on(bundle.parent == stock_ledger_entry.serial_and_batch_bundle)
		.inner_join(batch_table)
		.on(batch_table.name == bundle.batch_no)
		.select(
			bundle.batch_no,
			Sum(bundle.qty).as_("qty"),
		)
		.where((batch_table.expiry_date >= expiry_date) | (batch_table.expiry_date.isnull()))
		.where(stock_ledger_entry.is_cancelled == 0)
		.where(
			(stock_ledger_entry.item_code == filters.get("item_code"))
			& (batch_table.disabled == 0)
			& (stock_ledger_entry.serial_and_batch_bundle.isnotnull())
		)
		.groupby(bundle.batch_no, bundle.warehouse)
		.having(Sum(bundle.qty) != 0)
		.offset(start)
		.limit(page_len)
	)

	bundle_query = bundle_query.select(
		Concat("MFG-", batch_table.manufacturing_date),
		Concat("EXP-", batch_table.expiry_date),
	)

	if filters.get("warehouse"):
		bundle_query = bundle_query.where(stock_ledger_entry.warehouse == filters.get("warehouse"))

	for field in searchfields:
		bundle_query = bundle_query.select(batch_table[field])

	if txt:
		txt_condition = batch_table.name.like(f"%{txt}%")
		for field in [*searchfields, "name"]:
			txt_condition |= batch_table[field].like(f"%{txt}%")

		bundle_query = bundle_query.where(txt_condition)

	return bundle_query.run(as_list=1)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_account_list(doctype, txt, searchfield, start, page_len, filters):
	doctype = "Account"
	filter_list = []

	if isinstance(filters, dict):
		for key, val in filters.items():
			if isinstance(val, list | tuple):
				filter_list.append([doctype, key, val[0], val[1]])
			else:
				filter_list.append([doctype, key, "=", val])
	elif isinstance(filters, list):
		filter_list.extend(filters)

	if "is_group" not in [d[1] for d in filter_list]:
		filter_list.append(["Account", "is_group", "=", "0"])

	if searchfield and txt:
		filter_list.append([doctype, searchfield, "like", "%%%s%%" % txt])

	return frappe.desk.reportview.execute(
		doctype,
		filters=filter_list,
		fields=["name", "parent_account"],
		limit_start=start,
		limit_page_length=page_len,
		as_list=True,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_blanket_orders(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(
		"""select distinct bo.name, bo.blanket_order_type, bo.to_date
		from `tabBlanket Order` bo, `tabBlanket Order Item` boi
		where
			boi.parent = bo.name
			and boi.item_code = {item_code}
			and bo.blanket_order_type = '{blanket_order_type}'
			and bo.company = {company}
			and bo.docstatus = 1""".format(
			item_code=frappe.db.escape(filters.get("item")),
			blanket_order_type=filters.get("blanket_order_type"),
			company=frappe.db.escape(filters.get("company")),
		)
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_income_account(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	# income account can be any Credit account,
	# but can also be a Asset account with account_type='Income Account' in special circumstances.
	# Hence the first condition is an "OR"
	if not filters:
		filters = {}

	doctype = "Account"
	condition = ""
	if filters.get("company"):
		condition += "and tabAccount.company = %(company)s"

	condition += f"and tabAccount.disabled = {filters.get('disabled', 0)}"

	return frappe.db.sql(
		f"""select tabAccount.name from `tabAccount`
			where (tabAccount.report_type = "Profit and Loss"
					or tabAccount.account_type in ("Income Account", "Temporary"))
				and tabAccount.is_group=0
				and tabAccount.`{searchfield}` LIKE %(txt)s
				{condition} {get_match_cond(doctype)}
			order by idx desc, name""",
		{"txt": "%" + txt + "%", "company": filters.get("company", "")},
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_filtered_dimensions(doctype, txt, searchfield, start, page_len, filters, reference_doctype=None):
	from erpnext.accounts.doctype.accounting_dimension_filter.accounting_dimension_filter import (
		get_dimension_filter_map,
	)

	dimension_filters = get_dimension_filter_map()
	dimension_filters = dimension_filters.get((filters.get("dimension"), filters.get("account")))
	query_filters = []
	or_filters = []
	fields = ["name"]

	searchfields = frappe.get_meta(doctype).get_search_fields()

	meta = frappe.get_meta(doctype)
	if meta.is_tree and meta.has_field("is_group"):
		query_filters.append(["is_group", "=", 0])

	if meta.has_field("disabled"):
		query_filters.append(["disabled", "!=", 1])

	if meta.has_field("company"):
		query_filters.append(["company", "=", filters.get("company")])

	for field in searchfields:
		or_filters.append([field, "LIKE", "%%%s%%" % txt])
		fields.append(field)

	if dimension_filters:
		if dimension_filters["allow_or_restrict"] == "Allow":
			query_selector = "in"
		else:
			query_selector = "not in"

		if len(dimension_filters["allowed_dimensions"]) == 1:
			dimensions = tuple(dimension_filters["allowed_dimensions"] * 2)
		else:
			dimensions = tuple(dimension_filters["allowed_dimensions"])

		query_filters.append(["name", query_selector, dimensions])

	output = frappe.get_list(
		doctype,
		fields=fields,
		filters=query_filters,
		or_filters=or_filters,
		as_list=1,
		reference_doctype=reference_doctype,
	)

	return [tuple(d) for d in set(output)]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_expense_account(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	if not filters:
		filters = {}

	doctype = "Account"
	condition = ""
	if filters.get("company"):
		condition += "and tabAccount.company = %(company)s"

	return frappe.db.sql(
		f"""select tabAccount.name from `tabAccount`
		where (tabAccount.report_type = "Profit and Loss"
				or tabAccount.account_type in ("Expense Account", "Fixed Asset", "Temporary", "Asset Received But Not Billed", "Capital Work in Progress"))
			and tabAccount.is_group=0
			and tabAccount.docstatus!=2
			and tabAccount.{searchfield} LIKE %(txt)s
			{condition} {get_match_cond(doctype)}""",
		{"company": filters.get("company", ""), "txt": "%" + txt + "%"},
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def warehouse_query(doctype, txt, searchfield, start, page_len, filters):
	# Should be used when item code is passed in filters.
	doctype = "Warehouse"
	conditions, bin_conditions = [], []
	filter_dict = get_doctype_wise_filters(filters)

	warehouse_field = "name"
	meta = frappe.get_meta("Warehouse")
	if meta.get("show_title_field_in_link") and meta.get("title_field"):
		searchfield = meta.get("title_field")
		warehouse_field = meta.get("title_field")

	query = """select `tabWarehouse`.`{warehouse_field}`,
		CONCAT_WS(' : ', 'Actual Qty', ifnull(round(`tabBin`.actual_qty, 2), 0 )) actual_qty
		from `tabWarehouse` left join `tabBin`
		on `tabBin`.warehouse = `tabWarehouse`.name {bin_conditions}
		where
			`tabWarehouse`.`{key}` like {txt}
			{fcond} {mcond}
		order by ifnull(`tabBin`.actual_qty, 0) desc, `tabWarehouse`.`{warehouse_field}` asc
		limit
			{page_len} offset {start}
		""".format(
		warehouse_field=warehouse_field,
		bin_conditions=get_filters_cond(
			doctype, filter_dict.get("Bin"), bin_conditions, ignore_permissions=True
		),
		key=searchfield,
		fcond=get_filters_cond(doctype, filter_dict.get("Warehouse"), conditions),
		mcond=get_match_cond(doctype),
		start=start,
		page_len=page_len,
		txt=frappe.db.escape(f"%{txt}%"),
	)

	return frappe.db.sql(query)


def get_doctype_wise_filters(filters):
	# Helper function to seperate filters doctype_wise
	filter_dict = defaultdict(list)
	for row in filters:
		filter_dict[row[0]].append(row)
	return filter_dict


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_batch_numbers(doctype, txt, searchfield, start, page_len, filters):
	query = """select batch_id from `tabBatch`
			where disabled = 0
			and (expiry_date >= CURRENT_DATE or expiry_date IS NULL)
			and name like {txt}""".format(txt=frappe.db.escape(f"%{txt}%"))

	if filters and filters.get("item"):
		query += " and item = {item}".format(item=frappe.db.escape(filters.get("item")))

	return frappe.db.sql(query, filters)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_manufacturer_query(doctype, txt, searchfield, start, page_len, filters):
	item_filters = [
		["manufacturer", "like", "%" + txt + "%"],
		["item_code", "=", filters.get("item_code")],
	]

	item_manufacturers = frappe.get_all(
		"Item Manufacturer",
		fields=["manufacturer", "manufacturer_part_no"],
		filters=item_filters,
		limit_start=start,
		limit_page_length=page_len,
		as_list=1,
	)
	return item_manufacturers


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_purchase_receipts(doctype, txt, searchfield, start, page_len, filters):
	query = """
		select pr.name
		from `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pritem
		where pr.docstatus = 1 and pritem.parent = pr.name
		and pr.name like {txt}""".format(txt=frappe.db.escape(f"%{txt}%"))

	if filters and filters.get("item_code"):
		query += " and pritem.item_code = {item_code}".format(
			item_code=frappe.db.escape(filters.get("item_code"))
		)

	return frappe.db.sql(query, filters)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_purchase_invoices(doctype, txt, searchfield, start, page_len, filters):
	query = """
		select pi.name
		from `tabPurchase Invoice` pi, `tabPurchase Invoice Item` piitem
		where pi.docstatus = 1 and piitem.parent = pi.name
		and pi.name like {txt}""".format(txt=frappe.db.escape(f"%{txt}%"))

	if filters and filters.get("item_code"):
		query += " and piitem.item_code = {item_code}".format(
			item_code=frappe.db.escape(filters.get("item_code"))
		)

	return frappe.db.sql(query, filters)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_doctypes_for_closing(doctype, txt, searchfield, start, page_len, filters):
	doctypes = frappe.get_hooks("period_closing_doctypes")
	if txt:
		doctypes = [d for d in doctypes if txt.lower() in d.lower()]
	return [(d,) for d in set(doctypes)]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_tax_template(doctype, txt, searchfield, start, page_len, filters):
	item_doc = frappe.get_cached_doc("Item", filters.get("item_code"))
	item_group = filters.get("item_group")
	company = filters.get("company")
	taxes = item_doc.taxes or []

	while item_group:
		item_group_doc = frappe.get_cached_doc("Item Group", item_group)
		taxes += item_group_doc.taxes or []
		item_group = item_group_doc.parent_item_group

	if not taxes:
		return frappe.get_all("Item Tax Template", filters={"disabled": 0, "company": company}, as_list=True)
	else:
		valid_from = filters.get("valid_from")
		valid_from = valid_from[1] if isinstance(valid_from, list) else valid_from

		args = {
			"item_code": filters.get("item_code"),
			"posting_date": valid_from,
			"tax_category": filters.get("tax_category"),
			"company": company,
		}

		taxes = _get_item_tax_template(args, taxes, for_validate=True)
		return [(d,) for d in set(taxes)]


def get_fields(doctype, fields=None):
	if fields is None:
		fields = []
	meta = frappe.get_meta(doctype)
	fields.extend(meta.get_search_fields())

	if meta.title_field and meta.title_field.strip() not in fields:
		fields.insert(1, meta.title_field.strip())

	return unique(fields)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_payment_terms_for_references(doctype, txt, searchfield, start, page_len, filters) -> list:
	terms = []
	if filters:
		terms = frappe.db.get_all(
			"Payment Schedule",
			filters={"parent": filters.get("reference")},
			fields=["payment_term"],
			limit=page_len,
			as_list=1,
		)
	return terms


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_filtered_child_rows(doctype, txt, searchfield, start, page_len, filters) -> list:
	table = frappe.qb.DocType(doctype)
	query = (
		frappe.qb.from_(table)
		.select(
			table.name,
			Concat("#", table.idx, ", ", table.item_code),
		)
		.orderby(table.idx)
		.offset(start)
		.limit(page_len)
	)

	if filters:
		for field, value in filters.items():
			query = query.where(table[field] == value)

	if txt:
		txt += "%"
		query = query.where(
			((table.idx.like(txt.replace("#", ""))) | (table.item_code.like(txt))) | (table.name.like(txt))
		)

	return query.run(as_dict=False)
