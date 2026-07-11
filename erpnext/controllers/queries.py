# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
from collections import OrderedDict, defaultdict

import frappe
from frappe import qb, scrub
from frappe.permissions import has_permission
from frappe.query_builder import Case, Criterion, DocType
from frappe.query_builder.functions import (
	Cast_,
	Concat,
	IfNull,
	Length,
	Locate,
	Lower,
	Round,
	Substring,
	Sum,
)
from frappe.utils import cint, nowdate, today, unique
from pypika import Order

import erpnext
from erpnext.accounts.utils import build_qb_match_conditions
from erpnext.stock.get_item_details import _get_item_tax_template
from erpnext.stock.utils import get_combine_datetime
from erpnext.utilities.query import get_filter_conditions_qb


# searches for active employees
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def employee_query(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict | str | None = None,
	reference_doctype: str | None = None,
	ignore_user_permissions: bool = False,
):
	doctype = "Employee"
	fields = get_fields(doctype, ["name", "employee_name"])
	ignore_permissions = False

	if reference_doctype and ignore_user_permissions:
		ignore_permissions = has_ignored_field(reference_doctype, doctype) and has_permission(
			doctype,
			ptype="select" if frappe.only_has_select_perm(doctype) else "read",
		)

	Employee = frappe.qb.DocType("Employee")
	search_str = f"%{txt}%"
	txt_no_percent = txt.replace("%", "")
	search_fields = list(dict.fromkeys([searchfield, *fields]))
	search_conditions = [Employee[field].like(search_str) for field in search_fields]

	query = frappe.qb.get_query(
		"Employee",
		fields=fields,
		filters=filters,
		ignore_permissions=ignore_permissions,
	)

	query = (
		query.where(Employee.status.isin(["Active", "Suspended"]))
		.where(Employee.docstatus < 2)
		.where(Criterion.any(search_conditions))
		.orderby(
			Case()
			.when(Locate(txt_no_percent, Employee.name) > 0, Locate(txt_no_percent, Employee.name))
			.else_(99999)
		)
		.orderby(
			Case()
			.when(
				Locate(txt_no_percent, Employee.employee_name) > 0,
				Locate(txt_no_percent, Employee.employee_name),
			)
			.else_(99999)
		)
		.orderby(Employee.idx, order=Order.desc)
		.orderby(Employee.name)
		.orderby(Employee.employee_name)
		.limit(page_len)
		.offset(start)
	)

	return query.run()


def has_ignored_field(reference_doctype, doctype):
	meta = frappe.get_meta(reference_doctype)
	for field in meta.fields:
		if not field.ignore_user_permissions:
			continue
		if field.fieldtype == "Link" and field.options == doctype:
			return True
		elif field.fieldtype == "Dynamic Link":
			options = meta.get_link_doctype(field.fieldname)
			if not options:
				continue
			if isinstance(options, str):
				options = options.split("\n")
			if doctype in options or "DocType" in options:
				return True

	return False


# searches for leads which are not converted
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def lead_query(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | None = None
):
	doctype = "Lead"
	fields = get_fields(doctype, ["name", "lead_name", "company_name"])

	Lead = frappe.qb.DocType("Lead")
	search_str = f"%{txt}%"
	txt_no_percent = txt.replace("%", "")

	searchfields = frappe.get_meta(doctype).get_search_fields()
	search_fields = list(dict.fromkeys([searchfield, "lead_name", "company_name", *searchfields]))
	search_conditions = [Lead[field].like(search_str) for field in search_fields]

	query = frappe.qb.get_query("Lead", fields=fields, filters=filters, ignore_permissions=False)

	query = (
		query.where(Lead.docstatus < 2)
		.where(Lead.status.isnull() | (Lead.status != "Converted"))
		.where(Criterion.any(search_conditions))
		.orderby(
			Case().when(Locate(txt_no_percent, Lead.name) > 0, Locate(txt_no_percent, Lead.name)).else_(99999)
		)
		.orderby(
			Case()
			.when(Locate(txt_no_percent, Lead.lead_name) > 0, Locate(txt_no_percent, Lead.lead_name))
			.else_(99999)
		)
		.orderby(
			Case()
			.when(Locate(txt_no_percent, Lead.company_name) > 0, Locate(txt_no_percent, Lead.company_name))
			.else_(99999)
		)
		.orderby(Lead.idx, order=Order.desc)
		.orderby(Lead.name)
		.orderby(Lead.lead_name)
		.limit(page_len)
		.offset(start)
	)

	return query.run()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def tax_account_query(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	company_currency = erpnext.get_company_currency(filters.get("company"))

	Account = frappe.qb.DocType("Account")

	def get_accounts(with_account_type_filter):
		query = frappe.qb.get_query("Account", fields=["name", "parent_account"], ignore_permissions=False)
		query = (
			query.where(Account.docstatus != 2)
			.where(Account.is_group == 0)
			.where(Account.company == filters.get("company"))
			.where(Account.disabled == filters.get("disabled", 0))
			.where(
				(Account.account_currency == company_currency)
				| Account.account_currency.isnull()
				| (Account.account_currency == "")
			)
			.where(Account[searchfield].like(f"%{txt}%"))
		)

		if with_account_type_filter:
			query = query.where(Account.account_type.isin(filters.get("account_type")))

		query = (
			query.orderby(Account.idx, order=Order.desc).orderby(Account.name).limit(page_len).offset(start)
		)

		return query.run()

	tax_accounts = get_accounts(True)

	if not tax_accounts:
		tax_accounts = get_accounts(False)

	return tax_accounts


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict | str | None = None,
	as_dict: bool = False,
):
	"""
	Fetch items for link fields
	"""
	doctype = "Item"

	filters = frappe.parse_json(filters)

	if filters and isinstance(filters, dict):
		if filters.get("customer") or filters.get("supplier"):
			party_type = "Customer" if filters.get("customer") else "Supplier"
			party = filters.get("customer") or filters.get("supplier")
			group = "Customer Group" if filters.get("customer") else "Supplier Group"
			item_rules_list = frappe.get_all(
				"Party Specific Item",
				filters={"party_type": party_type},
				fields=["party", "restrict_based_on", "based_on_value"],
			)

			party_group_rules_list = frappe.get_all(
				"Party Specific Item",
				filters={"party_type": group},
				fields=["party as party_group", "restrict_based_on", "based_on_value"],
			)
			current_party_group = frappe.get_value(party_type, party, frappe.scrub(group))

			restricted_items = defaultdict(set)
			allowed_items = defaultdict(set)

			for rule in item_rules_list:
				restrict_based_on = "name" if rule.restrict_based_on == "Item" else rule.restrict_based_on

				if rule.party == party:
					allowed_items[restrict_based_on].add(rule.based_on_value)
				else:
					restricted_items[restrict_based_on].add(rule.based_on_value)

			for rule in party_group_rules_list:
				restrict_based_on = "name" if rule.restrict_based_on == "Item" else rule.restrict_based_on

				if current_party_group == rule.party_group:
					allowed_items[restrict_based_on].add(rule.based_on_value)
				else:
					restricted_items[restrict_based_on].add(rule.based_on_value)

			for field, restricted_values in restricted_items.items():
				values_to_exclude = restricted_values - allowed_items[field]
				if values_to_exclude:
					filters[scrub(field)] = ["not in", list(values_to_exclude)]

			if filters.get("customer"):
				del filters["customer"]
			else:
				del filters["supplier"]
		else:
			filters.pop("customer", None)
			filters.pop("supplier", None)

	item = DocType(doctype)

	# Condition for the date
	eol = item.end_of_life
	date_conditions = [eol > nowdate(), eol.isnull()]
	#  Add the condition if the db can evaluate it
	if frappe.db.db_type not in ["postgres"]:
		date_conditions.append(eol == "0000-00-00")

	date_condition = Criterion.any(date_conditions)

	# Condition for the searchfields
	meta = frappe.get_meta("Item", cached=True)
	searchfields = meta.get_search_fields()
	query_select = []

	extra_searchfields = [field for field in searchfields if field not in ["name", "description"]]

	for field in extra_searchfields:
		query_select.append(item[field])

	if "description" in searchfields:
		description_col = (
			Case()
			.when(Length(item.description) > 40, Concat(Substring(item.description, 1, 40), "..."))
			.else_(item.description)
		).as_("description")

		query_select.append(description_col)

	fields_to_process = list(
		dict.fromkeys(
			searchfields
			+ [
				field
				for field in [
					searchfield or "name",
					"item_code",
					"item_group",
					"item_name",
				]
				if field not in searchfields
			]
		)
	)
	db_fields = [f.fieldname for f in meta.fields] + ["name"]
	search_str = f"%{txt}%"
	search_conditions = []
	for fieldname in fields_to_process:
		if fieldname in db_fields:
			search_conditions.append(item[fieldname].like(search_str))

	barcode_tbl = DocType("Item Barcode")
	barcode_subquery = (
		frappe.qb.from_(barcode_tbl).select(barcode_tbl.parent).where(barcode_tbl.barcode.like(search_str))
	)
	search_conditions.append(item.item_code.isin(barcode_subquery))

	# Condition for the description
	if frappe.db.estimate_count("Item") < 50000 and "description" not in fields_to_process:
		search_conditions.append(item.description.like(search_str))

	txt_no_percent = txt.replace("%", "")

	# Building the query
	query = (
		frappe.get_query(doctype, filters=filters, ignore_permissions=False)
		.select(*query_select)
		.where(item.docstatus < 2)
		.where(item.disabled == 0)
		.where(item.has_variants == 0)
		.where(date_condition)
		.where(Criterion.any(search_conditions))
		.orderby(
			Case()
			.when(
				Locate(Lower(txt_no_percent), Lower(item.name)) > 0,
				Locate(Lower(txt_no_percent), Lower(item.name)),
			)
			.else_(99999)
		)
		.orderby(
			Case()
			.when(
				Locate(Lower(txt_no_percent), Lower(item.item_name)) > 0,
				Locate(Lower(txt_no_percent), Lower(item.item_name)),
			)
			.else_(99999)
		)
		.orderby(item.idx, order=Order.desc)
		.orderby(item.name)
		.orderby(item.item_name)
		.limit(page_len)
		.offset(start)
	)

	return query.run(as_dict=as_dict)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def bom(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | str | None = None
):
	doctype = "BOM"
	fields = get_fields(doctype, ["name", "item"])

	BOM = frappe.qb.DocType("BOM")
	txt_no_percent = txt.replace("%", "")

	query = frappe.qb.get_query("BOM", fields=fields, filters=filters, ignore_permissions=False)

	query = (
		query.where(BOM.docstatus == 1)
		.where(BOM.is_active == 1)
		.where(BOM[searchfield].like(f"%{txt}%"))
		.orderby(
			Case().when(Locate(txt_no_percent, BOM.name) > 0, Locate(txt_no_percent, BOM.name)).else_(99999)
		)
		.orderby(BOM.idx, order=Order.desc)
		.orderby(BOM.name)
		.limit(page_len or 20)
		.offset(start or 0)
	)

	return query.run()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_project_name(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | None = None
):
	proj = qb.DocType("Project")
	qb_filter_and_conditions = []
	qb_filter_or_conditions = []

	if filters:
		if filters.get("customer"):
			qb_filter_and_conditions.append(
				(proj.customer == filters.get("customer")) | (proj.customer.isnull()) | (proj.customer == "")
			)

		if filters.get("company"):
			qb_filter_and_conditions.append(proj.company == filters.get("company"))

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
		q = q.orderby(
			Case()
			.when(
				Locate(Lower(txt), Lower(proj.project_name)) > 0,
				Locate(Lower(txt), Lower(proj.project_name)),
			)
			.else_(99999)
		)
	q = q.orderby(proj.idx, order=Order.desc).orderby(proj.name)

	if page_len:
		q = q.limit(page_len)

	if start:
		q = q.offset(start)
	return q.run()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_delivery_notes_to_be_billed(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict, as_dict: bool = False
):
	DeliveryNote = frappe.qb.DocType("Delivery Note")

	fields = get_fields(doctype, ["name", "customer", "posting_date"])

	original_dn = (
		frappe.qb.from_(DeliveryNote)
		.select(DeliveryNote.name)
		.where((DeliveryNote.docstatus == 1) & (DeliveryNote.is_return == 0) & (DeliveryNote.per_billed > 0))
	)

	query = frappe.qb.get_query(
		"Delivery Note",
		fields=fields,
		filters=filters,
		ignore_permissions=False,
	)

	query = (
		query.where(
			(DeliveryNote.docstatus == 1)
			& (DeliveryNote.status.notin(["Stopped", "Closed"]))
			& (DeliveryNote[searchfield].like(f"%{txt}%"))
			& (
				((DeliveryNote.is_return == 0) & (DeliveryNote.per_billed < 100))
				| ((DeliveryNote.grand_total == 0) & (DeliveryNote.per_billed < 100))
				| (
					(DeliveryNote.is_return == 1)
					& (DeliveryNote.per_billed < 100)
					& (DeliveryNote.return_against.isin(original_dn))
				)
			)
		)
		.orderby(DeliveryNote[searchfield], order=Order.asc)
		.limit(page_len)
		.offset(start)
	)

	return query.run(as_dict=as_dict)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_batch_no(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	doctype = "Batch"
	meta = frappe.get_meta(doctype, cached=True)
	searchfields = meta.get_search_fields()
	page_len = 300

	batches = get_batches_from_stock_ledger_entries(searchfields, txt, filters, start, page_len)
	batches.extend(get_batches_from_serial_and_batch_bundle(searchfields, txt, filters, start, page_len))

	filtered_batches = get_filterd_batches(batches)

	if filters.get("is_inward"):
		filtered_batches.extend(get_empty_batches(filters, start, page_len, filtered_batches, txt))

	return filtered_batches


def get_empty_batches(filters, start, page_len, filtered_batches=None, txt=None):
	query_filter = {"item": filters.get("item_code"), "disabled": 0}
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
		.where(stock_ledger_entry.is_cancelled == 0)
		.where(
			(stock_ledger_entry.item_code == filters.get("item_code"))
			& (batch_table.disabled == 0)
			& (stock_ledger_entry.batch_no.isnotnull())
		)
		.groupby(stock_ledger_entry.batch_no, stock_ledger_entry.warehouse, batch_table.name)
		.having(Sum(stock_ledger_entry.actual_qty) != 0)
		.offset(start)
		.limit(page_len)
	)

	if not filters.get("is_inward"):
		if filters.get("posting_date") and filters.get("posting_time"):
			query = query.where(
				stock_ledger_entry.posting_datetime
				<= get_combine_datetime(filters.get("posting_date"), filters.get("posting_time"))
			)

	if not filters.get("include_expired_batches"):
		query = query.where((batch_table.expiry_date >= expiry_date) | (batch_table.expiry_date.isnull()))

	query = query.select(
		Case()
		.when(batch_table.manufacturing_date.isnotnull(), Concat("MFG-", batch_table.manufacturing_date))
		.as_("manufacturing_date"),
		Case()
		.when(batch_table.expiry_date.isnotnull(), Concat("EXP-", batch_table.expiry_date))
		.as_("expiry_date"),
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
		.where(stock_ledger_entry.is_cancelled == 0)
		.where(
			(stock_ledger_entry.item_code == filters.get("item_code"))
			& (batch_table.disabled == 0)
			& (stock_ledger_entry.serial_and_batch_bundle.isnotnull())
		)
		.groupby(bundle.batch_no, bundle.warehouse, batch_table.name)
		.having(Sum(bundle.qty) != 0)
		.offset(start)
		.limit(page_len)
	)

	if not filters.get("is_inward"):
		if filters.get("posting_date") and filters.get("posting_time"):
			bundle_query = bundle_query.where(
				stock_ledger_entry.posting_datetime
				<= get_combine_datetime(filters.get("posting_date"), filters.get("posting_time"))
			)

	if not filters.get("include_expired_batches"):
		bundle_query = bundle_query.where(
			(batch_table.expiry_date >= expiry_date) | (batch_table.expiry_date.isnull())
		)

	bundle_query = bundle_query.select(
		Case()
		.when(batch_table.manufacturing_date.isnotnull(), Concat("MFG-", batch_table.manufacturing_date))
		.as_("manufacturing_date"),
		Case()
		.when(batch_table.expiry_date.isnotnull(), Concat("EXP-", batch_table.expiry_date))
		.as_("expiry_date"),
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
def get_account_list(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | list
):
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
def get_blanket_orders(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	bo = frappe.qb.DocType("Blanket Order")
	bo_item = frappe.qb.DocType("Blanket Order Item")

	blanket_orders = (
		frappe.qb.from_(bo)
		.from_(bo_item)
		.select(bo.name)
		.distinct()
		.select(bo.blanket_order_type, bo.to_date)
		.where(
			(bo_item.parent == bo.name)
			& (bo_item.item_code == filters.get("item"))
			& (bo.blanket_order_type == filters.get("blanket_order_type"))
			& (bo.company == filters.get("company"))
			& (bo.docstatus == 1)
		)
		.run()
	)

	return blanket_orders


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_income_account(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	# income account can be any Credit account,
	# but can also be a Asset account with account_type='Income Account' in special circumstances.
	# Hence the first condition is an "OR"

	if not filters:
		filters = {}

	dt = "Account"

	acc = qb.DocType(dt)
	condition = [
		(acc.report_type.eq("Profit and Loss") | acc.account_type.isin(["Income Account", "Temporary"])),
		acc.is_group.eq(0),
		acc.disabled.eq(0),
	]
	if txt:
		condition.append(acc.name.like(f"%{txt}%"))

	if filters.get("company"):
		condition.append(acc.company.eq(filters.get("company")))

	user_perms = build_qb_match_conditions(dt)
	condition.extend(user_perms)

	return (
		qb.from_(acc)
		.select(acc.name)
		.where(Criterion.all(condition))
		.orderby(acc.idx, order=Order.desc)
		.orderby(acc.name)
		.run()
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_filtered_dimensions(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters: dict,
	reference_doctype: str | None = None,
):
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
		df = meta.get_field(field)
		if df and df.fieldtype != "Check":
			or_filters.append([field, "LIKE", "%%%s%%" % txt])
		else:
			or_filters.append([field, "=", cint(txt)])
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
def get_expense_account(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	if not filters:
		filters = {}

	dt = "Account"

	acc = qb.DocType(dt)
	condition = [
		(
			acc.report_type.eq("Profit and Loss")
			| acc.account_type.isin(
				[
					"Expense Account",
					"Fixed Asset",
					"Temporary",
					"Asset Received But Not Billed",
					"Capital Work in Progress",
				]
			)
		),
		acc.is_group.eq(0),
		acc.disabled.eq(0),
	]
	if txt:
		condition.append(acc.name.like(f"%{txt}%"))

	if filters.get("company"):
		condition.append(acc.company.eq(filters.get("company")))

	user_perms = build_qb_match_conditions(dt)
	condition.extend(user_perms)

	return qb.from_(acc).select(acc.name).where(Criterion.all(condition)).run()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def warehouse_query(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: list):
	# Should be used when item code is passed in filters.
	filter_dict = get_doctype_wise_filters(filters)

	warehouse_field = "name"
	meta = frappe.get_meta("Warehouse")
	if meta.get("show_title_field_in_link") and meta.get("title_field"):
		searchfield = meta.get("title_field")
		warehouse_field = meta.get("title_field")

	wh = frappe.qb.DocType("Warehouse")
	bin_dt = frappe.qb.DocType("Bin")

	# Bin filters go on the LEFT JOIN so warehouses without a matching Bin row are still returned
	join_condition = bin_dt.warehouse == wh.name
	for condition in get_filter_conditions_qb("Bin", filter_dict.get("Bin")):
		join_condition &= condition

	# Base the query on Warehouse so get_query applies its user-permission match conditions;
	# Bin is left-joined (its filters on the JOIN) so warehouses without a Bin row still match.
	query = (
		frappe.qb.get_query("Warehouse", fields=[warehouse_field], ignore_permissions=False)
		.left_join(bin_dt)
		.on(join_condition)
		.select(
			Concat("Actual Qty", " : ", IfNull(Round(bin_dt.actual_qty, 2), 0)).as_("actual_qty"),
		)
		.where(wh[searchfield].like(f"%{txt}%"))
	)

	for condition in get_filter_conditions_qb("Warehouse", filter_dict.get("Warehouse")):
		query = query.where(condition)

	return (
		query.orderby(IfNull(bin_dt.actual_qty, 0), order=Order.desc)
		.orderby(wh[warehouse_field], order=Order.asc)
		.limit(page_len)
		.offset(start)
		.run()
	)


def get_doctype_wise_filters(filters):
	# Helper function to seperate filters doctype_wise
	filter_dict = defaultdict(list)
	for row in filters:
		filter_dict[row[0]].append(row)
	return filter_dict


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_batch_numbers(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	batch = frappe.qb.DocType("Batch")
	query = (
		frappe.qb.from_(batch)
		.select(batch.batch_id)
		.where(
			(batch.disabled == 0)
			& (batch.expiry_date.isnull() | (batch.expiry_date >= today()))
			& batch.name.like(f"%{txt}%")
		)
	)

	if filters and filters.get("item"):
		query = query.where(batch.item == filters.get("item"))

	return query.orderby(batch.batch_id).limit(page_len).offset(start).run()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_manufacturer_query(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict
):
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
def get_purchase_receipts(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	pr = frappe.qb.DocType("Purchase Receipt")
	pr_item = frappe.qb.DocType("Purchase Receipt Item")
	query = (
		frappe.qb.from_(pr)
		.inner_join(pr_item)
		.on(pr_item.parent == pr.name)
		.select(pr.name)
		.distinct()  # one row per receipt, not per matching item line
		.where((pr.docstatus == 1) & pr.name.like(f"%{txt}%"))
	)

	if filters and filters.get("item_code"):
		query = query.where(pr_item.item_code == filters.get("item_code"))

	return query.orderby(pr.name).limit(page_len).offset(start).run()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_purchase_invoices(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	pi = frappe.qb.DocType("Purchase Invoice")
	pi_item = frappe.qb.DocType("Purchase Invoice Item")
	query = (
		frappe.qb.from_(pi)
		.inner_join(pi_item)
		.on(pi_item.parent == pi.name)
		.select(pi.name)
		.distinct()  # one row per invoice, not per matching item line
		.where((pi.docstatus == 1) & pi.name.like(f"%{txt}%"))
	)

	if filters and filters.get("item_code"):
		query = query.where(pi_item.item_code == filters.get("item_code"))

	return query.orderby(pi.name).limit(page_len).offset(start).run()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_doctypes_for_closing(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict
):
	doctypes = frappe.get_hooks("period_closing_doctypes")
	if txt:
		doctypes = [d for d in doctypes if txt.lower() in d.lower()]
	return [(d,) for d in set(doctypes)]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_tax_template(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	item_doc = frappe.get_cached_doc("Item", filters.get("item_code"))
	item_group = filters.get("item_group")
	company = filters.get("company")
	taxes = item_doc.taxes or []

	while item_group:
		item_group_doc = frappe.get_cached_doc("Item Group", item_group)
		taxes += item_group_doc.taxes or []
		item_group = item_group_doc.parent_item_group

	if not taxes:
		or_filters = []
		if txt:
			search_fields = ["name"]

			tax_template_doc = frappe.get_meta("Item Tax Template")

			if title_field := tax_template_doc.title_field:
				search_fields.append(title_field)
			if tax_template_doc.search_fields:
				search_fields.extend(tax_template_doc.get_search_fields())

			for f in search_fields:
				or_filters.append([doctype, f.strip(), "like", f"%{txt}%"])

		return frappe.get_list(
			"Item Tax Template",
			filters={"disabled": 0, "company": company},
			or_filters=or_filters,
			as_list=True,
		)

	else:
		valid_from = filters.get("valid_from")
		valid_from = valid_from[1] if isinstance(valid_from, list) else valid_from

		ctx = frappe._dict(
			{
				"item_code": filters.get("item_code"),
				"posting_date": valid_from,
				"tax_category": filters.get("tax_category"),
				"company": company,
				"base_net_rate": filters.get("base_net_rate"),
			}
		)

		taxes = _get_item_tax_template(ctx, taxes, for_validate=True)
		txt = txt.lower()
		return [(d,) for d in set(taxes) if not txt or txt in d.lower()]


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
def get_payment_terms_for_references(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict
):
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
def get_filtered_child_rows(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict
):
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
			((Cast_(table.idx, "varchar").like(txt.replace("#", ""))) | (table.item_code.like(txt)))
			| (table.name.like(txt))
		)

	return query.run(as_dict=False)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_item_uom_query(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	if frappe.get_single_value("Stock Settings", "allow_uom_with_conversion_rate_defined_in_item"):
		query_filters = {"parent": filters.get("item_code")}

		if txt:
			query_filters["uom"] = ["like", f"%{txt}%"]

		return frappe.get_all(
			"UOM Conversion Detail",
			filters=query_filters,
			fields=["uom", "conversion_factor"],
			limit_start=start,
			limit_page_length=page_len,
			order_by="idx",
			as_list=1,
		)

	return frappe.get_all(
		"UOM",
		filters={"name": ["like", f"%{txt}%"], "enabled": 1},
		fields=["name"],
		limit_start=start,
		limit_page_length=page_len,
		as_list=1,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_warehouse_address(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	table = frappe.qb.DocType(doctype)
	child_table = frappe.qb.DocType("Dynamic Link")

	query = (
		frappe.qb.from_(table)
		.inner_join(child_table)
		.on((table.name == child_table.parent) & (child_table.parenttype == doctype))
		.select(table.name)
		.where(
			(child_table.link_name == filters.get("warehouse"))
			& (table.disabled == 0)
			& (child_table.link_doctype == "Warehouse")
			& (table.name.like(f"%{txt}%"))
		)
		.offset(start)
		.limit(page_len)
	)
	return query.run(as_list=1)
