# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from distutils.log import debug
import frappe
import erpnext
from frappe import _
from frappe.desk.reportview import get_match_cond, get_filters_cond
from frappe.utils import nowdate, getdate, flt, cstr, cint
from collections import defaultdict
from erpnext.stock.get_item_details import _get_item_tax_template
from frappe.utils import unique

# searches for active employees
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def employee_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	fields = get_fields("Employee", ["name", "employee_name"])

	searchfields = frappe.get_meta("Employee").get_search_fields()
	searchfields = " or ".join([field + " like %(txt)s" for field in searchfields])

	return frappe.db.sql("""select {fields} from `tabEmployee`
		where status = 'Active'
			and docstatus < 2
			and ({scond})
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, employee_name), locate(%(_txt)s, employee_name), 99999),
			modified desc,
			name, employee_name
		limit %(start)s, %(page_len)s""".format(**{
			'fields': ", ".join(fields),
			"scond": searchfields,
			'key': searchfield,
			'fcond': get_filters_cond(doctype, filters, conditions),
			'mcond': get_match_cond(doctype)
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len
		})


# searches for leads which are not converted
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def lead_query(doctype, txt, searchfield, start, page_len, filters):
	fields = get_fields("Lead", ["name", "lead_name", "company_name"])

	searchfields = frappe.get_meta("Lead").get_search_fields()
	searchfields = " or ".join([field + " like %(txt)s" for field in searchfields])

	return frappe.db.sql("""select {fields} from `tabLead`
		where docstatus < 2
			and ifnull(status, '') != 'Converted'
			and ({scond})
			{mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, lead_name), locate(%(_txt)s, lead_name), 99999),
			if(locate(%(_txt)s, company_name), locate(%(_txt)s, company_name), 99999),
			modified desc,
			name, lead_name
		limit %(start)s, %(page_len)s""".format(**{
			'fields': ", ".join(fields),
			"scond": searchfields,
			'key': searchfield,
			'mcond': get_match_cond(doctype)
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len
		})


# searches for customer
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def customer_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	cust_master_name = frappe.defaults.get_user_default("cust_master_name")

	if cust_master_name == "Customer Name":
		fields = ["name", "customer_group", "territory"]
	else:
		fields = ["name", "customer_name", "customer_group", "territory"]

	fields = get_fields("Customer", fields)

	searchfields = frappe.get_meta("Customer").get_search_fields()
	searchfields = " or ".join([field + " like %(txt)s" for field in searchfields])

	return frappe.db.sql("""select {fields} from `tabCustomer`
		where docstatus < 2
			and ({scond}) and disabled=0
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, customer_name), locate(%(_txt)s, customer_name), 99999),
			modified desc,
			name, customer_name
		limit %(start)s, %(page_len)s""".format(**{
			"fields": ", ".join(fields),
			"scond": searchfields,
			"mcond": get_match_cond(doctype),
			"fcond": get_filters_cond(doctype, filters, conditions).replace('%', '%%'),
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len
		})


# searches for supplier
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def supplier_query(doctype, txt, searchfield, start, page_len, filters):
	supp_master_name = frappe.defaults.get_user_default("supp_master_name")

	if supp_master_name == "Supplier Name":
		fields = ["name", "supplier_group"]
	else:
		fields = ["name", "supplier_name", "supplier_group"]

	fields = get_fields("Supplier", fields)

	return frappe.db.sql("""select {field} from `tabSupplier`
		where docstatus < 2
			and ({key} like %(txt)s
				or supplier_name like %(txt)s) and disabled=0
			{mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, supplier_name), locate(%(_txt)s, supplier_name), 99999),
			modified desc,
			name, supplier_name
		limit %(start)s, %(page_len)s """.format(**{
			'field': ', '.join(fields),
			'key': searchfield,
			'mcond':get_match_cond(doctype)
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len
		})


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def tax_account_query(doctype, txt, searchfield, start, page_len, filters):
	company_currency = erpnext.get_company_currency(filters.get('company'))

	def get_accounts(with_account_type_filter):
		account_type_condition = ''
		if with_account_type_filter:
			account_type_condition = "AND account_type in %(account_types)s"

		accounts = frappe.db.sql("""
			SELECT name, parent_account
			FROM `tabAccount`
			WHERE `tabAccount`.docstatus!=2
				{account_type_condition}
				AND is_group = 0
				AND company = %(company)s
				AND account_currency = %(currency)s
				AND `{searchfield}` LIKE %(txt)s
			ORDER BY idx DESC, name
			LIMIT %(offset)s, %(limit)s
		""".format(account_type_condition=account_type_condition, searchfield=searchfield),
			dict(
				account_types=filters.get("account_type"),
				company=filters.get("company"),
				currency=company_currency,
				txt="%{}%".format(txt),
				offset=start,
				limit=page_len
			)
		)

		return accounts

	tax_accounts = get_accounts(True)

	if not tax_accounts:
		tax_accounts = get_accounts(False)

	return tax_accounts


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	conditions = []

	# Get searchfields from meta and use in Item Link field query
	meta = frappe.get_meta("Item", cached=True)
	searchfields = meta.get_search_fields()
	if "description" in searchfields:
		searchfields.remove("description")

	# Columns
	columns = ''
	extra_searchfields = [field for field in searchfields
		if not field in ["name", "item_name", "item_group", "brand"]]

	if extra_searchfields:
		columns = ", " + ", ".join(extra_searchfields)

	searchfields = searchfields + [field for field in [searchfield or "name", "item_code", "item_group", "item_name"]
		if not field in searchfields]
	searchfields = " or ".join([field + " like %(txt)s" for field in searchfields])

	# Description Conditions
	description_cond = ''
	if frappe.db.count('Item', cache=True) < 50000:
		# scan description only if items are less than 50000
		description_cond = 'or tabItem.description LIKE %(txt)s'

	# Item applicability conditions
	has_applicable_items_cond = ""
	if filters and isinstance(filters, dict) and filters.get('has_applicable_items'):
		filters.pop('has_applicable_items')
		has_applicable_items_cond = """ and exists(select iai.name
			from `tabItem Applicable Item` iai
			where tabItem.name = iai.parent or tabItem.variant_of = iai.parent)
		"""

	# Default Conditions
	default_conditions = []
	default_disabled_condition = "tabItem.disabled = 0"
	default_variant_condition = "tabItem.has_variants = 0"
	default_eol_condition = "(tabItem.end_of_life > %(today)s or ifnull(tabItem.end_of_life, '0000-00-00')='0000-00-00')"

	if filters and isinstance(filters, dict):
		if filters.get('include_disabled'):
			filters.pop('include_disabled')
		else:
			if not filters.get('disabled'):
				default_conditions.append(default_disabled_condition)
			if not filters.get('end_of_life'):
				default_conditions.append(default_eol_condition)

		if filters.get('include_templates'):
			filters.pop('include_templates')
		elif not filters.get('has_variants'):
			default_conditions.append(default_variant_condition)
	else:
		default_conditions = [default_disabled_condition, default_variant_condition, default_eol_condition]

	default_conditions = "and {0}".format(" and ".join(default_conditions)) if default_conditions else ""

	return frappe.db.sql("""select tabItem.name,
		if(length(tabItem.item_name) > 40,
			concat(substr(tabItem.item_name, 1, 40), "..."), item_name) as item_name,
		tabItem.item_group, tabItem.brand
		{columns}
		from tabItem
		where tabItem.docstatus < 2
			{default_conditions}
			and (
				{scond}
				or tabItem.name IN (select parent from `tabItem Barcode` where barcode LIKE %(txt)s)
				{description_cond}
			)
			{fcond}
			{mcond}
			{has_applicable_items_cond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, item_name), locate(%(_txt)s, item_name), 99999),
			idx desc,
			name, item_name
		limit %(start)s, %(page_len)s """.format(
			columns=columns,
			default_conditions=default_conditions,
			scond=searchfields,
			fcond=get_filters_cond(doctype, filters, conditions).replace('%', '%%'),
			mcond=get_match_cond(doctype).replace('%', '%%'),
			description_cond=description_cond,
			has_applicable_items_cond=has_applicable_items_cond),
			{
				"today": nowdate(),
				"txt": "%%%s%%" % txt,
				"_txt": txt.replace("%", ""),
				"start": start,
				"page_len": page_len
			}, as_dict=as_dict)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def project_template_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	fields = get_fields("Project Template", ["name", "project_template_name"])

	searchfields = frappe.get_meta("Project Template").get_search_fields()
	searchfields = " or ".join([field + " like %(txt)s" for field in searchfields])

	applies_to_item_cond = ""
	if filters and isinstance(filters, dict) and filters.get('applies_to_item'):
		applies_to_item = filters.get('applies_to_item')
		del filters['applies_to_item']

		variant_of = frappe.get_cached_value("Item", applies_to_item, "variant_of")
		if variant_of:
			applies_to_item_match_cond = "`tabProject Template`.applies_to_item in ({0}, {1})"\
				.format(frappe.db.escape(applies_to_item), frappe.db.escape(variant_of))
		else:
			applies_to_item_match_cond = "`tabProject Template`.applies_to_item = {0}".format(frappe.db.escape(applies_to_item))

		applies_to_item_cond = "and (ifnull(`tabProject Template`.applies_to_item, '') = '' or {0})".format(applies_to_item_match_cond)

	return frappe.db.sql("""
			select {fields}
			from `tabProject Template`
			where ({scond}) and disabled = 0
				{applies_to_item_cond}
				{fcond}
				{mcond}
			order by
				if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
				idx desc, name
			limit %(start)s, %(page_len)s
		""".format(
		fields=", ".join(fields),
		scond=searchfields,
		fcond=get_filters_cond(doctype, filters, conditions).replace('%', '%%'),
		mcond=get_match_cond(doctype).replace('%', '%%'),
		key=searchfield,
		applies_to_item_cond=applies_to_item_cond,
	), {
		'txt': '%' + txt + '%',
		'_txt': txt.replace("%", ""),
		'start': start or 0,
		'page_len': page_len or 20
	})


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def applicable_item_group(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	fields = get_fields("Item Group", ["name"])

	return frappe.db.sql("""
		select {fields}
		from `tabItem Group`
		where `tabItem Group`.`{key}` like %(txt)s
			and exists(select iai.name
				from `tabItem Applicable Item` iai
				inner join `tabItem` iaim on iaim.name = iai.applicable_item_code
				where iaim.item_group = `tabItem Group`.name)
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			idx desc, name
		limit %(start)s, %(page_len)s
	""".format(
			fields=", ".join(fields),
			fcond=get_filters_cond(doctype, filters, conditions).replace('%', '%%'),
			mcond=get_match_cond(doctype).replace('%', '%%'),
			key=searchfield
		), {
			'txt': '%' + txt + '%',
			'_txt': txt.replace("%", ""),
			'start': start or 0,
			'page_len': page_len or 20
		})


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def bom(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	fields = get_fields("BOM", ["name", "item"])

	return frappe.db.sql("""select {fields}
		from tabBOM
		where tabBOM.docstatus=1
			and tabBOM.is_active=1
			and tabBOM.`{key}` like %(txt)s
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			modified desc, name
		limit %(start)s, %(page_len)s """.format(
			fields=", ".join(fields),
			fcond=get_filters_cond(doctype, filters, conditions).replace('%', '%%'),
			mcond=get_match_cond(doctype).replace('%', '%%'),
			key=searchfield),
		{
			'txt': '%' + txt + '%',
			'_txt': txt.replace("%", ""),
			'start': start or 0,
			'page_len': page_len or 20
		})


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_project_name(doctype, txt, searchfield, start, page_len, filters):
	cond = ''
	if filters.get('customer'):
		cond = """(`tabProject`.customer = %s or
			ifnull(`tabProject`.customer,"")="") and""" %(frappe.db.escape(filters.get("customer")))

	fields = get_fields("Project", ["name"])

	return frappe.db.sql("""select {fields} from `tabProject`
		where `tabProject`.status not in ("Completed", "Cancelled")
			and {cond} `tabProject`.name like %(txt)s {match_cond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			modified desc,
			`tabProject`.name asc
		limit {start}, {page_len}""".format(
			fields=", ".join(['`tabProject`.{0}'.format(f) for f in fields]),
			cond=cond,
			match_cond=get_match_cond(doctype),
			start=start,
			page_len=page_len), {
				"txt": "%{0}%".format(txt),
				"_txt": txt.replace('%', '')
			})


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_delivery_notes_to_be_billed(doctype, txt, searchfield, start, page_len, filters, as_dict):
	return _get_delivery_notes_to_be_billed(doctype, txt, searchfield, start, page_len, filters, as_dict)

def _get_delivery_notes_to_be_billed(doctype="Delivery Note", txt="", searchfield="name", start=0, page_len=0,
		filters=None, as_dict=True, ignore_permissions=False):
	fields = get_fields("Delivery Note", ["name", "customer", "customer_name", "posting_date", "project"])
	select_fields = ", ".join(["`tabDelivery Note`.{0}".format(f) for f in fields])
	limit = "limit {0}, {1}".format(start, page_len) if page_len else ""

	bill_only_to_cond = ""
	if cint(filters.get('bill_multiple_projects')):
		if filters.get('customer'):
			bill_only_operation = "dni.bill_only_to_customer = {0}".format(frappe.db.escape(filters.get('customer')))
			filters.pop("customer")
		else:
			bill_only_operation = "ifnull(dni.bill_only_to_customer, '') != ''"

		bill_only_to_cond = """ and exists(select dni.name from `tabDelivery Note Item` dni
			where dni.parent = `tabDelivery Note`.name and {0})""".format(bill_only_operation)

	filters.pop("bill_multiple_projects")

	return frappe.db.sql("""
		select {fields}
		from `tabDelivery Note`
		left join `tabDelivery Note` dr on `tabDelivery Note`.is_return = 1 and dr.name = `tabDelivery Note`.return_against
		where `tabDelivery Note`.docstatus = 1
			and `tabDelivery Note`.`{key}` like {txt}
			and `tabDelivery Note`.`status` not in ('Stopped', 'Closed')
			and `tabDelivery Note`.per_completed < 100
			and (`tabDelivery Note`.is_return = 0 or dr.per_completed < 100)
			{bill_only_to_cond} {fcond} {mcond}
			order by `tabDelivery Note`.posting_date, `tabDelivery Note`.posting_time, `tabDelivery Note`.creation
			{limit}
	""".format(
		fields=select_fields,
		key=searchfield,
		fcond=get_filters_cond(doctype, filters, [], ignore_permissions=ignore_permissions),
		mcond="" if ignore_permissions else get_match_cond(doctype),
		bill_only_to_cond=bill_only_to_cond,
		limit=limit,
		txt="%(txt)s",
	), {"txt": ("%%%s%%" % txt)}, as_dict=as_dict)


@frappe.whitelist()
def get_sales_order_to_be_billed(doctype="Sales Order", txt="", searchfield="name", start=0, page_len=0,
		filters=None, as_dict=True, ignore_permissions=False):
	fields = get_fields(doctype, ["name", "customer_name", "project", "transaction_date"])
	select_fields = ", ".join(["`tabSales Order`.{0}".format(f) for f in fields])
	limit = "limit {0}, {1}".format(start, page_len) if page_len else ""

	bill_only_to_cond = ""
	if cint(filters.get('bill_multiple_projects')):
		if filters.get('customer'):
			bill_only_operation = "soi.bill_only_to_customer = {0}".format(frappe.db.escape(filters.get('customer')))
			filters.pop("customer")
		else:
			bill_only_operation = "ifnull(soi.bill_only_to_customer, '') != ''"

		bill_only_to_cond = """ and exists(select soi.name from `tabSales Order Item` soi
			where soi.parent = `tabSales Order`.name and {0})""".format(bill_only_operation)

	filters.pop("bill_multiple_projects")

	return frappe.db.sql("""
		select {fields}
		from `tabSales Order`
		where `tabSales Order`.docstatus = 1
			and `tabSales Order`.`{key}` like {txt}
			and `tabSales Order`.`status` not in ('Stopped', 'Closed')
			and `tabSales Order`.per_completed < 100
			{bill_only_to_cond} {fcond} {mcond}
			order by `tabSales Order`.transaction_date, `tabSales Order`.creation
			{limit}
	""".format(
		fields=select_fields,
		key=searchfield,
		fcond=get_filters_cond(doctype, filters, [], ignore_permissions=ignore_permissions),
		mcond="" if ignore_permissions else get_match_cond(doctype),
		bill_only_to_cond=bill_only_to_cond,
		limit=limit,
		txt="%(txt)s",
	), {"txt": ("%%%s%%" % txt)}, as_dict=as_dict)



@frappe.whitelist()
def get_sales_order_for_project(doctype="Project", txt="", searchfield="name", start=0, page_len=0,
		filters=None, as_dict=True, ignore_permissions=False):
	limit = "limit {0}, {1}".format(start, page_len) if page_len else ""

	f_sales_order_cond, bill_only_to_sales_order_cond = get_extra_info(filters, "Sales Order", ignore_permissions)
	f_delivery_note_cond, bill_only_to_delivery_note_cond = get_extra_info(filters, "Delivery Note", ignore_permissions)
	
	filters.pop("join_filters")
	filters.update(filters.get("filters"))
	if filters.get("filters"):
		filters.pop("filters")
	sql_query = """
		SELECT 
			tabProject.name, tabProject.project_type, tabProject.customer as 'customer_name', tabProject.expected_delivery_date as Date,
			so.name as 'Sales Order',
			dn.name as 'Delivery Note'
		FROM `tabProject` tabProject

		LEFT JOIN `tabSales Order` so
				ON tabProject.name=so.project
		LEFT JOIN `tabDelivery Note` dn
			ON tabProject.name=dn.project

		Where 
			tabProject.docstatus <3 
			
			{fcond} {mcond}

			{bill_only_to_sales_order_cond} {f_sales_order_cond} {m_sales_order_cond}
			{bill_only_to_delivery_note_cond} {f_delivery_note_cond} {m_delivery_note_cond}
		ORDER BY 
			tabProject.expected_delivery_date, tabProject.creation
		{limit}
	""".format(
		fcond=get_filters_cond(doctype, filters, [], ignore_permissions=ignore_permissions),
		mcond="" if ignore_permissions else get_match_cond(doctype),
		limit=limit,
		
		bill_only_to_sales_order_cond=bill_only_to_sales_order_cond,
		f_sales_order_cond=f_sales_order_cond,
		m_sales_order_cond= "" if ignore_permissions else get_match_cond("Sales Order"),

		bill_only_to_delivery_note_cond = bill_only_to_delivery_note_cond,
		f_delivery_note_cond = f_delivery_note_cond,
		m_delivery_note_cond= "" if ignore_permissions else get_match_cond("Delivery Note"),
		
	)
	result = frappe.db.sql(sql_query, as_dict=as_dict)
	return result
	
def get_extra_info(filters, doctype, ignore_permissions):
	f_cond = ""
	bill_only_to_cond = ""

	if filters.get("join_filters"):
		for k, v in filters.get("join_filters").items():
			if type(v) != list:
				value_cond, value = v[0], v[1]
				if type(value) != str:
					f_cond += " and {0} {1} {2}".format(f"so.{k}",value_cond ,value if type(value) != list else tuple(value))
				else:
					f_cond += " and {0} {1} '{2}'".format(f"`tab{doctype}`.{k}",value_cond ,value)
		
		if cint(filters.get("join_filters").get('bill_multiple_projects')):
			if filters.get('customer'):
				bill_only_operation = "current_table.bill_only_to_customer = {0}".format(frappe.db.escape(filters.get('customer')))
			else:
				bill_only_operation = "ifnull(current_table.bill_only_to_customer, '') != ''"

			bill_only_to_cond = """ and exists(select current_table.name from `tab{1} Item` current_table
				where current_table.parent = `tab{1}`.name and {0})""".format(bill_only_operation, doctype)

	return f_cond, bill_only_to_cond

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_batch_no(doctype, txt, searchfield, start, page_len, filters):
	cond = ""
	if filters.get("posting_date"):
		cond += " and (batch.expiry_date is null or batch.expiry_date >= %(posting_date)s)"

	if filters.get("warehouse"):
		cond += " and sle.warehouse = %(warehouse)s"

	batch_nos = None
	args = {
		'item_code': filters.get("item_code"),
		'warehouse': filters.get("warehouse"),
		'posting_date': filters.get('posting_date'),
		'txt': "%{0}%".format(txt),
		"start": start,
		"page_len": page_len
	}

	having_clause = "having sum(sle.actual_qty) > 0"
	if filters.get("is_return") or filters.get('is_receipt'):
		having_clause = ""

	batch_nos = frappe.db.sql("""
		select sle.batch_no, round(sum(sle.actual_qty),2), sle.stock_uom,
			min(timestamp(sle.posting_date, sle.posting_time)), batch.manufacturing_date, batch.expiry_date
		from `tabStock Ledger Entry` sle
			INNER JOIN `tabBatch` batch on sle.batch_no = batch.name
		where
			batch.disabled = 0
			and sle.item_code = %(item_code)s
			and (sle.batch_no like %(txt)s
			or batch.expiry_date like %(txt)s
			or batch.manufacturing_date like %(txt)s)
			and batch.docstatus < 2
			{cond}
			{match_conditions}
		group by batch_no {having_clause}
		order by batch.expiry_date, sle.batch_no desc
		limit %(start)s, %(page_len)s""".format(
			cond=cond,
			match_conditions=get_match_cond(doctype),
			having_clause = having_clause
		), args, as_list=1)

	for d in batch_nos:
		d[1] = cstr(flt(d[1])) # Actual Qty
		d[3] = "Received: {0}".format(frappe.format(getdate(d[3]))) if d[3] else None  # Received Date
		d[4] = "Manufactured: {0}".format(frappe.format(getdate(d[4]))) if d[4] else None  # Manufactured Date
		d[5] = "Expiry: {0}".format(frappe.format(getdate(d[5]))) if d[5] else None  # Expiry Date

	return batch_nos


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_account_list(doctype, txt, searchfield, start, page_len, filters):
	filter_list = []

	if isinstance(filters, dict):
		for key, val in filters.items():
			if isinstance(val, (list, tuple)):
				filter_list.append([doctype, key, val[0], val[1]])
			else:
				filter_list.append([doctype, key, "=", val])
	elif isinstance(filters, list):
		filter_list.extend(filters)

	if "is_group" not in [d[1] for d in filter_list]:
		filter_list.append(["Account", "is_group", "=", "0"])

	if searchfield and txt:
		filter_list.append([doctype, searchfield, "like", "%%%s%%" % txt])

	return frappe.desk.reportview.execute("Account", filters = filter_list,
		fields = ["name", "parent_account"],
		limit_start=start, limit_page_length=page_len, as_list=True)

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_blanket_orders(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select distinct bo.name, bo.blanket_order_type, bo.to_date
		from `tabBlanket Order` bo, `tabBlanket Order Item` boi
		where
			boi.parent = bo.name
			and boi.item_code = {item_code}
			and bo.blanket_order_type = '{blanket_order_type}'
			and bo.company = {company}
			and bo.docstatus = 1"""
		.format(item_code = frappe.db.escape(filters.get("item")),
			blanket_order_type = filters.get("blanket_order_type"),
			company = frappe.db.escape(filters.get("company"))
		))


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_income_account(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	# income account can be any Credit account,
	# but can also be a Asset account with account_type='Income Account' in special circumstances.
	# Hence the first condition is an "OR"
	if not filters: filters = {}

	condition = ""
	if filters.get("company"):
		condition += "and tabAccount.company = %(company)s"

	return frappe.db.sql("""select tabAccount.name from `tabAccount`
			where (tabAccount.report_type = "Profit and Loss"
					or tabAccount.account_type in ("Income Account", "Temporary"))
				and tabAccount.is_group=0
				and tabAccount.`{key}` LIKE %(txt)s
				{condition} {match_condition}
			order by idx desc, name"""
			.format(condition=condition, match_condition=get_match_cond(doctype), key=searchfield), {
				'txt': '%' + txt + '%',
				'company': filters.get("company", "")
			})


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_expense_account(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	if not filters: filters = {}

	condition = ""
	if filters.get("company"):
		condition += "and tabAccount.company = %(company)s"

	return frappe.db.sql("""select tabAccount.name from `tabAccount`
		where (tabAccount.report_type = "Profit and Loss"
				or tabAccount.account_type in ("Expense Account", "Fixed Asset", "Temporary", "Asset Received But Not Billed", "Capital Work in Progress"))
			and tabAccount.is_group=0
			and tabAccount.docstatus!=2
			and tabAccount.{key} LIKE %(txt)s
			{condition} {match_condition}"""
		.format(condition=condition, key=searchfield,
			match_condition=get_match_cond(doctype)), {
			'company': filters.get("company", ""),
			'txt': '%' + txt + '%'
		})


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def warehouse_query(doctype, txt, searchfield, start, page_len, filters):
	# Should be used when item code is passed in filters.
	conditions, bin_conditions = [], []
	filter_dict = get_doctype_wise_filters(filters)

	sub_query = """ select round(`tabBin`.actual_qty, 2) from `tabBin`
		where `tabBin`.warehouse = `tabWarehouse`.name
		{bin_conditions} """.format(
		bin_conditions=get_filters_cond(doctype, filter_dict.get("Bin"),
			bin_conditions, ignore_permissions=True))

	query = """select `tabWarehouse`.name,
		CONCAT_WS(" : ", "Actual Qty", ifnull( ({sub_query}), 0) ) as actual_qty
		from `tabWarehouse`
		where
		   `tabWarehouse`.`{key}` like {txt}
			{fcond} {mcond}
		order by
			`tabWarehouse`.name desc
		limit
			{start}, {page_len}
		""".format(
			sub_query=sub_query,
			key=searchfield,
			fcond=get_filters_cond(doctype, filter_dict.get("Warehouse"), conditions),
			mcond=get_match_cond(doctype),
			start=start,
			page_len=page_len,
			txt=frappe.db.escape('%{0}%'.format(txt))
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
			and (expiry_date >= CURDATE() or expiry_date IS NULL)
			and name like {txt}""".format(txt = frappe.db.escape('%{0}%'.format(txt)))

	if filters and filters.get('item'):
		query += " and item = {item}".format(item = frappe.db.escape(filters.get('item')))

	return frappe.db.sql(query, filters)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_uom_query(doctype, txt, searchfield, start, page_len, filters):
	if filters and filters.get('item_code'):
		return frappe.db.sql("""
			select distinct uom
			from `tabUOM Conversion Detail`
				where parenttype = 'Item' and parent = %(item_code)s
					and (uom like %(txt)s)
					{mcond}
				order by
					if(locate(%(_txt)s, uom), locate(%(_txt)s, uom), 99999),
					idx desc,
					uom
				limit %(start)s, %(page_len)s
		""".format(**{
			'key': searchfield,
			'mcond': get_match_cond(doctype)
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'item_code': filters.get('item_code')
		})
	else:
		return frappe.db.sql("""
			select name
			from `tabUOM`
			where name like %(txt)s
			order by
				if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
				idx desc,
				name
			limit %(start)s, %(page_len)s
		""", {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'item_code': filters.get('item_code')
		})


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_manufacturer_query(doctype, txt, searchfield, start, page_len, filters):
	item_filters = [
		['manufacturer', 'like', '%' + txt + '%'],
		['item_code', '=', filters.get("item_code")]
	]

	item_manufacturers = frappe.get_all(
		"Item Manufacturer",
		fields=["manufacturer", "manufacturer_part_no"],
		filters=item_filters,
		limit_start=start,
		limit_page_length=page_len,
		as_list=1
	)
	return item_manufacturers


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_purchase_receipts(doctype, txt, searchfield, start, page_len, filters):
	query = """
		select pr.name
		from `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pritem
		where pr.docstatus = 1 and pritem.parent = pr.name
		and pr.name like {txt}""".format(txt = frappe.db.escape('%{0}%'.format(txt)))

	if filters and filters.get('item_code'):
		query += " and pritem.item_code = {item_code}".format(item_code = frappe.db.escape(filters.get('item_code')))

	return frappe.db.sql(query, filters)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_purchase_invoices(doctype, txt, searchfield, start, page_len, filters):
	query = """
		select pi.name
		from `tabPurchase Invoice` pi, `tabPurchase Invoice Item` piitem
		where pi.docstatus = 1 and piitem.parent = pi.name
		and pi.name like {txt}""".format(txt = frappe.db.escape('%{0}%'.format(txt)))

	if filters and filters.get('item_code'):
		query += " and piitem.item_code = {item_code}".format(item_code = frappe.db.escape(filters.get('item_code')))

	return frappe.db.sql(query, filters)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def vehicle_allocation_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = []

	fields = get_fields("Vehicle Allocation", ['name', 'title', 'vehicle_color'])
	fields[1] = "CONCAT('<b>', title, '</b>')"
	searchfields = frappe.get_meta("Vehicle Allocation").get_search_fields()
	searchfields = " or ".join([field + " like %(txt)s" for field in searchfields])

	if isinstance(filters, dict) and 'vehicle_color' in filters:
		color = filters.pop('vehicle_color')
		if color:
			conditions.append("ifnull(vehicle_color, '') in ('', {0})".format(frappe.db.escape(color)))

	return frappe.db.sql("""
		select {fields}
		from `tabVehicle Allocation`
		where docstatus = 1 and is_expired = 0 and is_cancelled = 0
			and ({scond}) {fcond} {mcond}
		order by
			if(locate(%(_txt)s, title), locate(%(_txt)s, title), 99999),
			is_additional, sr_no
		limit %(start)s, %(page_len)s
	""".format(**{
		'fields': ", ".join(fields),
		'key': searchfield,
		'scond': searchfields,
		'fcond': get_filters_cond("Vehicle Allocation", filters, conditions).replace('%', '%%'),
		'mcond': get_match_cond(doctype)
	}), {
		'txt': "%%%s%%" % txt,
		'_txt': txt.replace("%", ""),
		'start': start,
		'page_len': page_len
	})


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def vehicle_allocation_period_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = []

	transaction_date = None
	if isinstance(filters, dict) and filters.get('transaction_date'):
		transaction_date = getdate(filters.get('transaction_date'))
		del filters['transaction_date']

	if isinstance(filters, dict) and 'vehicle_color' in filters:
		color = filters.pop('vehicle_color')
		if color:
			conditions.append("ifnull(vehicle_color, '') in ('', {0})".format(frappe.db.escape(color)))

	date_cond = ""
	if transaction_date:
		date_cond = "and `tabVehicle Allocation Period`.to_date >= {0}".format(frappe.db.escape(transaction_date))

	having_cond = ""
	if searchfield == 'allocation_period':
		having_cond = "having allocations > 0"

	subquery = """
		select ifnull(count(`tabVehicle Allocation`.name), 0)
		from `tabVehicle Allocation`
		where `tabVehicle Allocation`.`{searchfield}` = `tabVehicle Allocation Period`.name
			and `tabVehicle Allocation`.docstatus = 1
			and `tabVehicle Allocation`.is_booked = 0
			and `tabVehicle Allocation`.is_cancelled = 0
			and `tabVehicle Allocation`.is_expired = 0
			{fcond}
	""".format(
		searchfield=searchfield,
		fcond=get_filters_cond("Vehicle Allocation", filters, conditions, ignore_permissions=True).replace('%', '%%')
	)

	query = """select `tabVehicle Allocation Period`.name, ({subquery}) as allocations
		from `tabVehicle Allocation Period`
		where `tabVehicle Allocation Period`.name like {txt} {mcond} {date_cond}
		{having_cond}
		order by `tabVehicle Allocation Period`.from_date asc
		limit {start}, {page_len}
		""".format(
			subquery=subquery,
			mcond=get_match_cond(doctype),
			date_cond=date_cond,
			having_cond=having_cond,
			start=start,
			page_len=page_len,
			txt=frappe.db.escape('%{0}%'.format(txt))
		)

	res = frappe.db.sql(query)

	out = []
	for row in res:
		out.append((row[0], _("Available Allocations: {0}").format(frappe.bold(row[1]))))

	return out


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def vehicle_color_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = []

	fields = get_fields("Vehicle Color", ['name', 'color_code'])
	searchfields = frappe.get_meta("Vehicle Color").get_search_fields()
	searchfields = " or ".join([field + " like %(txt)s" for field in searchfields])

	item_condition = ""
	def add_vehicle_color_condition(item_doc):
		colors = [frappe.db.escape(d.vehicle_color) for d in item_doc.vehicle_colors]
		return " and name in ({0})".format(", ".join(colors))

	if isinstance(filters, dict) and 'item_code' in filters:
		item_code = filters.pop('item_code')
		if item_code:
			item = frappe.get_cached_doc("Item", item_code)
			if item:
				if item.vehicle_colors:
					item_condition = add_vehicle_color_condition(item)
				elif item.variant_of:
					variant_item = frappe.get_cached_doc("Item", item.variant_of)
					if variant_item and variant_item.vehicle_colors:
						item_condition = add_vehicle_color_condition(variant_item)

	return frappe.db.sql("""
		select {fields}
		from `tabVehicle Color`
		where ({scond}) {fcond} {mcond} {item_condition}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			idx desc
		limit %(start)s, %(page_len)s
	""".format(**{
		'fields': ", ".join(fields),
		'key': searchfield,
		'scond': searchfields,
		'fcond': get_filters_cond("Vehicle Color", filters, conditions).replace('%', '%%'),
		'mcond': get_match_cond(doctype),
		'item_condition': item_condition
	}), {
		'txt': "%%%s%%" % txt,
		'_txt': txt.replace("%", ""),
		'start': start,
		'page_len': page_len
	})


def get_fields(doctype, fields=[]):
	meta = frappe.get_meta(doctype)
	fields.extend(meta.get_search_fields())

	if meta.title_field and not meta.title_field.strip() in fields:
		fields.insert(1, meta.title_field.strip())

	return unique(fields)
