# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, json, erpnext
from frappe.utils.nestedset import get_root_of
from frappe.utils import nowdate

@frappe.whitelist()
def get_items(start, page_length, price_list, item_group, search_value=""):
	serial_no = ""
	batch_no = ""
	item_code = search_value
	if not frappe.db.exists('Item Group', item_group):
		item_group = get_root_of('Item Group')

	if search_value:
		# search serial no
		serial_no_data = frappe.db.get_value('Serial No', search_value, ['name', 'item_code'])
		if serial_no_data:
			serial_no, item_code = serial_no_data

		if not serial_no:
			batch_no_data = frappe.db.get_value('Batch', search_value, ['name', 'item'])
			if batch_no_data:
				batch_no, item_code = batch_no_data

	lft, rgt = frappe.db.get_value('Item Group', item_group, ['lft', 'rgt'])
	# locate function is used to sort by closest match from the beginning of the value
	res = frappe.db.sql("""select i.name as item_code, i.item_name, i.image as item_image,
		item_det.price_list_rate, item_det.currency
		from `tabItem` i LEFT JOIN
			(select item_code, price_list_rate, currency from
				`tabItem Price`	where price_list=%(price_list)s) item_det
		ON
			(item_det.item_code=i.name or item_det.item_code=i.variant_of)
		where
			i.disabled = 0 and i.has_variants = 0 and i.is_sales_item = 1
			and i.item_group in (select name from `tabItem Group` where lft >= {lft} and rgt <= {rgt})
			and (i.item_code like %(item_code)s
			or i.item_name like %(item_code)s or i.barcode like %(item_code)s)
		limit {start}, {page_length}""".format(start=start, page_length=page_length, lft=lft, rgt=rgt),
		{
			'item_code': '%%%s%%'%(frappe.db.escape(item_code)),
			'price_list': price_list
		} , as_dict=1)

	res = {
		'items': res
	}

	if serial_no:
		res.update({
			'serial_no': serial_no
		})

	if batch_no:
		res.update({
			'batch_no': batch_no
		})

	return res

@frappe.whitelist()
def get_master_data_for_offline_mode(pos_profile):
	if isinstance(pos_profile, basestring):
		pos_profile = json.loads(pos_profile)

	if not pos_profile.get('company'):
		pos_profile['company'] = erpnext.get_default_company()

	if not pos_profile.get('selling_price_list'):
		pos_profile['selling_price_list'] = frappe.db.get_single_value('Selling Settings',
			'selling_price_list')

	customers = get_customers_list(pos_profile)

	return {
		'Customer': customers,
		'Item Group': get_item_groups(pos_profile),
		'item': get_items_list(pos_profile),
		'address': get_customers_address(customers),
		'contact': get_contacts(customers),
		'serial_no_data': get_serial_no_data(pos_profile),
		'batch_no_data': get_batch_no_data(),
		'price_list_data': get_price_list_data(pos_profile),
		'pricing_rules': get_pricing_rule_data(pos_profile),
		'bin_data': get_bin_data(pos_profile),
		'tax_data': get_item_tax_data()
	}

def get_items_list(pos_profile):
	cond = "1=1"
	item_groups = []
	if pos_profile.get('item_groups'):
		# Get items based on the item groups defined in the POS profile
		for data in pos_profile.get('item_groups'):
			item_groups.extend([d.name for d in get_child_nodes('Item Group', data.item_group)])
		cond = "item_group in (%s)"%(', '.join(['%s']*len(item_groups)))

	return frappe.db.sql("""
		select
			name, item_code, item_name, description, item_group, expense_account, has_batch_no,
			has_serial_no, expense_account, selling_cost_center, stock_uom, image,
			default_warehouse, is_stock_item, barcode, brand,
			concat(item_name, ", ", description, ", ", item_group, ", ", barcode) as item_data
		from
			tabItem
		where
			disabled = 0 and has_variants = 0 and is_sales_item = 1 and {cond}
		""".format(cond=cond), tuple(item_groups), as_dict=1)

def get_item_groups(pos_profile):
	return frappe.db.sql(""" select name as label, name as value
		 from `tabItem Group`""", as_dict=1)

def get_customers_list(pos_profile):
	cond = "1=1"
	customer_groups = []
	if pos_profile.get('customer_groups'):
		# Get customers based on the customer groups defined in the POS profile
		for data in pos_profile.get('customer_groups'):
			customer_groups.extend([d.name for d in get_child_nodes('Customer Group', data.customer_group)])
		cond = "customer_group in (%s)"%(', '.join(['%s']*len(customer_groups)))

	return frappe.db.sql(""" select name as label, customer_name as value,
		CONCAT(customer_group, ", " , territory) as description,
		customer_pos_id, name as label, name as value from tabCustomer where disabled = 0
		and {cond}""".format(cond=cond), tuple(customer_groups), as_dict=1) or {}

def get_customers_address(customers):
	customer_address = {}
	if isinstance(customers, basestring):
		customers = [frappe._dict({'name': customers})]

	for data in customers:
		address = frappe.db.sql(""" select name, address_line1, address_line2, city, state,
			email_id, phone, fax, pincode from `tabAddress` where is_primary_address =1 and name in
			(select parent from `tabDynamic Link` where link_doctype = 'Customer' and link_name = %s
			and parenttype = 'Address')""", data.name, as_dict=1)
		address_data = {}
		if address: address_data = address[0]

		address_data.update({'full_name': data.customer_name, 'customer_pos_id': data.customer_pos_id})
		customer_address[data.name] = address_data

	return customer_address

def get_contacts(customers):
	customer_contact = {}
	if isinstance(customers, basestring):
		customers = [frappe._dict({'name': customers})]

	for data in customers:
		contact = frappe.db.sql(""" select email_id, phone, mobile_no from `tabContact`
			where is_primary_contact =1 and name in
			(select parent from `tabDynamic Link` where link_doctype = 'Customer' and link_name = %s
			and parenttype = 'Contact')""", data.name, as_dict=1)
		if contact:
			customer_contact[data.name] = contact[0]

	return customer_contact

def get_child_nodes(group_type, root):
	lft, rgt = frappe.db.get_value(group_type, root, ["lft", "rgt"])
	return frappe.db.sql(""" Select name, lft, rgt from `tab{tab}` where
			lft >= {lft} and rgt <= {rgt} order by lft""".format(tab=group_type, lft=lft, rgt=rgt), as_dict=1)

def get_serial_no_data(pos_profile):
	# get itemwise serial no data
	# example {'Nokia Lumia 1020': {'SN0001': 'Pune'}}
	# where Nokia Lumia 1020 is item code, SN0001 is serial no and Pune is warehouse

	cond = "1=1"
	if pos_profile.get('update_stock') and pos_profile.get('warehouse'):
		cond = "warehouse = '{0}'".format(pos_profile.get('warehouse'))

	serial_nos = frappe.db.sql("""select name, warehouse, item_code from `tabSerial No` where {0}
				and company = %(company)s """.format(cond), {'company': pos_profile.get('company')}, as_dict=1)

	itemwise_serial_no = {}
	for sn in serial_nos:
		if sn.item_code not in itemwise_serial_no:
			itemwise_serial_no.setdefault(sn.item_code, {})
		itemwise_serial_no[sn.item_code][sn.name] = sn.warehouse

	return itemwise_serial_no

def get_batch_no_data():
	# get itemwise batch no data
	# exmaple: {'LED-GRE': [Batch001, Batch002]}
	# where LED-GRE is item code, SN0001 is serial no and Pune is warehouse

	itemwise_batch = {}
	batches = frappe.db.sql("""select name, item from `tabBatch`
		where ifnull(expiry_date, '4000-10-10') >= curdate()""", as_dict=1)

	for batch in batches:
		if batch.item not in itemwise_batch:
			itemwise_batch.setdefault(batch.item, [])
		itemwise_batch[batch.item].append(batch.name)

	return itemwise_batch

def get_price_list_data(pos_profile):
	itemwise_price_list = {}
	price_lists = frappe.db.sql("""Select ifnull(price_list_rate, 0) as price_list_rate,
		item_code from `tabItem Price` ip where price_list = %(price_list)s""",
		{'price_list': pos_profile.get('selling_price_list')}, as_dict=1)

	for item in price_lists:
		itemwise_price_list[item.item_code] = item.price_list_rate

	return itemwise_price_list

def get_pricing_rule_data(pos_profile):
	pricing_rules = ""
	if not pos_profile.get("ignore_pricing_rule"):
		pricing_rules = frappe.db.sql(""" Select * from `tabPricing Rule` where docstatus < 2
						and ifnull(for_price_list, '') in (%(price_list)s, '') and selling = 1
						and ifnull(company, '') in (%(company)s, '') and disable = 0 and %(date)s
						between ifnull(valid_from, '2000-01-01') and ifnull(valid_upto, '2500-12-31')
						order by priority desc, name desc""",
		{'company': pos_profile.get('company'), 'price_list': pos_profile.get('selling_price_list'), 'date': nowdate()}, as_dict=1)
	return pricing_rules

def get_item_tax_data():
	# get default tax of an item
	# example: {'Consulting Services': {'Excise 12 - TS': '12.000'}}

	itemwise_tax = {}
	taxes = frappe.db.sql(""" select parent, tax_type, tax_rate from `tabItem Tax`""", as_dict=1)

	for tax in taxes:
		if tax.parent not in itemwise_tax:
			itemwise_tax.setdefault(tax.parent, {})
		itemwise_tax[tax.parent][tax.tax_type] = tax.tax_rate

	return itemwise_tax

def get_bin_data(pos_profile):
	itemwise_bin_data = {}
	cond = "1=1"
	if pos_profile.get('warehouse'):
		cond = "warehouse = '{0}'".format(pos_profile.get('warehouse'))

	bin_data = frappe.db.sql(""" select item_code, warehouse, actual_qty from `tabBin`
		where actual_qty > 0 and {cond}""".format(cond=cond), as_dict=1)

	for bins in bin_data:
		if bins.item_code not in itemwise_bin_data:
			itemwise_bin_data.setdefault(bins.item_code, {})
		itemwise_bin_data[bins.item_code][bins.warehouse] = bins.actual_qty

	return itemwise_bin_data

@frappe.whitelist()
def get_orders(company):
	return frappe.get_all('Sales Invoice', fields = ["posting_date", "name", "customer", "grand_total"],
		filters = {'docstatus': 0, 'company': company})

@frappe.whitelist()
def submit_invoice(doc, submitted=None):
	if isinstance(doc, basestring):
		args = json.loads(doc)

	if not frappe.db.exists('Sales Invoice', args.get('name')):
		doc = frappe.new_doc('Sales Invoice')
	else:
		doc = frappe.get_doc('Sales Invoice', args.get('name'))

	doc.update(args)
	doc.run_method("set_missing_values")
	doc.run_method("calculate_taxes_and_totals")
	if submitted:
		doc.submit()
	else:
		doc.save(ignore_permissions=True)

	return doc
