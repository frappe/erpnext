# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.desk.reportview import get_match_cond, get_filters_cond
from frappe.utils import nowdate
from collections import defaultdict


 # searches for active employees
def employee_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	return frappe.db.sql("""select name, employee_name from `tabEmployee`
		where status = 'Active'
			and docstatus < 2
			and ({key} like %(txt)s
				or employee_name like %(txt)s)
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, employee_name), locate(%(_txt)s, employee_name), 99999),
			idx desc,
			name, employee_name
		limit %(start)s, %(page_len)s""".format(**{
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
def lead_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select name, lead_name, company_name from `tabLead`
		where docstatus < 2
			and ifnull(status, '') != 'Converted'
			and ({key} like %(txt)s
				or lead_name like %(txt)s
				or company_name like %(txt)s)
			{mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, lead_name), locate(%(_txt)s, lead_name), 99999),
			if(locate(%(_txt)s, company_name), locate(%(_txt)s, company_name), 99999),
			idx desc,
			name, lead_name
		limit %(start)s, %(page_len)s""".format(**{
			'key': searchfield,
			'mcond':get_match_cond(doctype)
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len
		})

 # searches for customer
def customer_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	cust_master_name = frappe.defaults.get_user_default("cust_master_name")

	if cust_master_name == "Customer Name":
		fields = ["name", "customer_group", "territory"]
	else:
		fields = ["name", "customer_name", "customer_group", "territory"]

	meta = frappe.get_meta("Customer")
	searchfields = meta.get_search_fields()
	searchfields = searchfields + [f for f in [searchfield or "name", "customer_name"] \
			if not f in searchfields]
	fields = fields + [f for f in searchfields if not f in fields]

	fields = ", ".join(fields)
	searchfields = " or ".join([field + " like %(txt)s" for field in searchfields])

	return frappe.db.sql("""select {fields} from `tabCustomer`
		where docstatus < 2
			and ({scond}) and disabled=0
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, customer_name), locate(%(_txt)s, customer_name), 99999),
			idx desc,
			name, customer_name
		limit %(start)s, %(page_len)s""".format(**{
			"fields": fields,
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
def supplier_query(doctype, txt, searchfield, start, page_len, filters):
	supp_master_name = frappe.defaults.get_user_default("supp_master_name")
	if supp_master_name == "Supplier Name":
		fields = ["name", "supplier_type"]
	else:
		fields = ["name", "supplier_name", "supplier_type"]
	fields = ", ".join(fields)

	return frappe.db.sql("""select {field} from `tabSupplier`
		where docstatus < 2
			and ({key} like %(txt)s
				or supplier_name like %(txt)s) and disabled=0
			{mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, supplier_name), locate(%(_txt)s, supplier_name), 99999),
			idx desc,
			name, supplier_name
		limit %(start)s, %(page_len)s """.format(**{
			'field': fields,
			'key': searchfield,
			'mcond':get_match_cond(doctype)
		}), {
			'txt': "%%%s%%" % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len
		})

def tax_account_query(doctype, txt, searchfield, start, page_len, filters):
	tax_accounts = frappe.db.sql("""select name, parent_account	from tabAccount
		where tabAccount.docstatus!=2
			and account_type in (%s)
			and is_group = 0
			and company = %s
			and `%s` LIKE %s
		order by idx desc, name
		limit %s, %s""" %
		(", ".join(['%s']*len(filters.get("account_type"))), "%s", searchfield, "%s", "%s", "%s"),
		tuple(filters.get("account_type") + [filters.get("company"), "%%%s%%" % txt,
			start, page_len]))
	if not tax_accounts:
		tax_accounts = frappe.db.sql("""select name, parent_account	from tabAccount
			where tabAccount.docstatus!=2 and is_group = 0
				and company = %s and `%s` LIKE %s limit %s, %s"""
			% ("%s", searchfield, "%s", "%s", "%s"),
			(filters.get("company"), "%%%s%%" % txt, start, page_len))

	return tax_accounts

def item_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	conditions = []

	return frappe.db.sql("""select tabItem.name, tabItem.item_group, tabItem.image,
		if(length(tabItem.item_name) > 40,
			concat(substr(tabItem.item_name, 1, 40), "..."), item_name) as item_name,
		if(length(tabItem.description) > 40, \
			concat(substr(tabItem.description, 1, 40), "..."), description) as decription
		from tabItem
		where tabItem.docstatus < 2
			and tabItem.has_variants=0
			and tabItem.disabled=0
			and (tabItem.end_of_life > %(today)s or ifnull(tabItem.end_of_life, '0000-00-00')='0000-00-00')
			and (tabItem.`{key}` LIKE %(txt)s
				or tabItem.item_group LIKE %(txt)s
				or tabItem.item_name LIKE %(txt)s
				or tabItem.description LIKE %(txt)s)
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, item_name), locate(%(_txt)s, item_name), 99999),
			idx desc,
			name, item_name
		limit %(start)s, %(page_len)s """.format(key=searchfield,
			fcond=get_filters_cond(doctype, filters, conditions).replace('%', '%%'),
			mcond=get_match_cond(doctype).replace('%', '%%')),
			{
				"today": nowdate(),
				"txt": "%%%s%%" % txt,
				"_txt": txt.replace("%", ""),
				"start": start,
				"page_len": page_len
			}, as_dict=as_dict)

def bom(doctype, txt, searchfield, start, page_len, filters):
	conditions = []

	return frappe.db.sql("""select tabBOM.name, tabBOM.item
		from tabBOM
		where tabBOM.docstatus=1
			and tabBOM.is_active=1
			and tabBOM.`{key}` like %(txt)s
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			idx desc, name
		limit %(start)s, %(page_len)s """.format(
			fcond=get_filters_cond(doctype, filters, conditions),
			mcond=get_match_cond(doctype),
			key=frappe.db.escape(searchfield)),
		{
			'txt': "%%%s%%" % frappe.db.escape(txt),
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len
		})

def get_project_name(doctype, txt, searchfield, start, page_len, filters):
	cond = ''
	if filters.get('customer'):
		cond = '(`tabProject`.customer = "' + filters['customer'] + '" or ifnull(`tabProject`.customer,"")="") and'

	return frappe.db.sql("""select `tabProject`.name from `tabProject`
		where `tabProject`.status not in ("Completed", "Cancelled")
			and {cond} `tabProject`.name like %(txt)s {match_cond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			idx desc,
			`tabProject`.name asc
		limit {start}, {page_len}""".format(
			cond=cond,
			match_cond=get_match_cond(doctype),
			start=start,
			page_len=page_len), {
				"txt": "%{0}%".format(txt),
				"_txt": txt.replace('%', '')
			})

def get_delivery_notes_to_be_billed(doctype, txt, searchfield, start, page_len, filters, as_dict):
	return frappe.db.sql("""
		select `tabDelivery Note`.name, `tabDelivery Note`.customer, `tabDelivery Note`.posting_date
		from `tabDelivery Note`
		where `tabDelivery Note`.`%(key)s` like %(txt)s and
			`tabDelivery Note`.docstatus = 1 and `tabDelivery Note`.is_return = 0
			and status not in ("Stopped", "Closed") %(fcond)s
			and (`tabDelivery Note`.per_billed < 100 or `tabDelivery Note`.grand_total = 0)
			%(mcond)s order by `tabDelivery Note`.`%(key)s` asc
	""" % {
		"key": searchfield,
		"fcond": get_filters_cond(doctype, filters, []),
		"mcond": get_match_cond(doctype),
		"txt": "%(txt)s"
	}, { "txt": ("%%%s%%" % txt) }, as_dict=as_dict)

def get_batch_no(doctype, txt, searchfield, start, page_len, filters):
	cond = ""
	if filters.get("posting_date"):
		cond = "and (ifnull(batch.expiry_date, '')='' or batch.expiry_date >= %(posting_date)s)"

	batch_nos = None
	args = {
		'item_code': filters.get("item_code"),
		'warehouse': filters.get("warehouse"),
		'posting_date': filters.get('posting_date'),
		'txt': "%{0}%".format(txt),
		"start": start,
		"page_len": page_len
	}

	if args.get('warehouse'):
		batch_nos = frappe.db.sql("""select sle.batch_no, round(sum(sle.actual_qty),2), sle.stock_uom, batch.expiry_date
				from `tabStock Ledger Entry` sle
				    INNER JOIN `tabBatch` batch on sle.batch_no = batch.name
				where
					sle.item_code = %(item_code)s
					and sle.warehouse = %(warehouse)s
					and sle.batch_no like %(txt)s
					and batch.docstatus < 2
					{0}
					{match_conditions}
				group by batch_no having sum(sle.actual_qty) > 0
				order by batch.expiry_date, sle.batch_no desc
				limit %(start)s, %(page_len)s""".format(cond, match_conditions=get_match_cond(doctype)), args)

	if batch_nos:
		return batch_nos
	else:
		return frappe.db.sql("""select name, expiry_date from `tabBatch` batch
			where item = %(item_code)s
			and name like %(txt)s
			and docstatus < 2
			{0}
			{match_conditions}
			order by expiry_date, name desc
			limit %(start)s, %(page_len)s""".format(cond, match_conditions=get_match_cond(doctype)), args)

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
				'txt': "%%%s%%" % frappe.db.escape(txt),
				'company': filters.get("company", "")
			})


@frappe.whitelist()
def get_expense_account(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	if not filters: filters = {}

	condition = ""
	if filters.get("company"):
		condition += "and tabAccount.company = %(company)s"

	return frappe.db.sql("""select tabAccount.name from `tabAccount`
		where (tabAccount.report_type = "Profit and Loss"
				or tabAccount.account_type in ("Expense Account", "Fixed Asset", "Temporary"))
			and tabAccount.is_group=0
			and tabAccount.docstatus!=2
			and tabAccount.{key} LIKE %(txt)s
			{condition} {match_condition}"""
		.format(condition=condition, key=frappe.db.escape(searchfield),
			match_condition=get_match_cond(doctype)), {
			'company': filters.get("company", ""),
			'txt': "%%%s%%" % frappe.db.escape(txt)
		})


@frappe.whitelist()
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
		   `tabWarehouse`.`{key}` like '{txt}'
			{fcond} {mcond}
		order by
			`tabWarehouse`.name desc
		limit
			{start}, {page_len}
		""".format(
			sub_query=sub_query,
			key=frappe.db.escape(searchfield),
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
