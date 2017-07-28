# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.utils import nowdate
from erpnext.setup.utils import get_exchange_rate
from frappe.core.doctype.communication.email import make
from erpnext.stock.get_item_details import get_pos_profile
from erpnext.accounts.party import get_party_account_currency
from erpnext.controllers.accounts_controller import get_taxes_and_charges

@frappe.whitelist()
def get_pos_data():
	doc = frappe.new_doc('Sales Invoice')
	doc.is_pos = 1;
	pos_profile = get_pos_profile(doc.company) or {}
	if not doc.company: doc.company = pos_profile.get('company')
	doc.update_stock = pos_profile.get('update_stock')

	if pos_profile.get('name'):
		pos_profile = frappe.get_doc('POS Profile', pos_profile.get('name'))

	company_data = get_company_data(doc.company)
	update_pos_profile_data(doc, pos_profile, company_data)
	update_multi_mode_option(doc, pos_profile)
	default_print_format = pos_profile.get('print_format') or "Point of Sale"
	print_template = frappe.db.get_value('Print Format', default_print_format, 'html')
	customers = get_customers_list(pos_profile)

	return {
		'doc': doc,
		'default_customer': pos_profile.get('customer'),
		'items': get_items_list(pos_profile),
		'item_groups': get_item_groups(pos_profile),
		'customers': customers,
		'address': get_customers_address(customers),
		'contacts': get_contacts(customers),
		'serial_no_data': get_serial_no_data(pos_profile, doc.company),
		'batch_no_data': get_batch_no_data(),
		'tax_data': get_item_tax_data(),
		'price_list_data': get_price_list_data(doc.selling_price_list),
		'bin_data': get_bin_data(pos_profile),
		'pricing_rules': get_pricing_rule_data(doc),
		'print_template': print_template,
		'pos_profile': pos_profile,
		'meta': get_meta()
	}

def get_meta():
	doctype_meta = {
		'customer': frappe.get_meta('Customer'),
		'invoice': frappe.get_meta('Sales Invoice')
	}

	for row in frappe.get_all('DocField', fields = ['fieldname', 'options'],
		filters = {'parent': 'Sales Invoice', 'fieldtype': 'Table'}):
		doctype_meta[row.fieldname] = frappe.get_meta(row.options)

	return doctype_meta

def get_company_data(company):
	return frappe.get_all('Company', fields = ["*"], filters= {'name': company})[0]

def update_pos_profile_data(doc, pos_profile, company_data):
	doc.campaign = pos_profile.get('campaign')
	if pos_profile and not pos_profile.get('country'):
		pos_profile.country = company_data.country

	doc.write_off_account = pos_profile.get('write_off_account') or \
		company_data.write_off_account
	doc.change_amount_account = pos_profile.get('change_amount_account') or \
		company_data.default_cash_account
	doc.taxes_and_charges = pos_profile.get('taxes_and_charges')
	if doc.taxes_and_charges:
		update_tax_table(doc)

	doc.currency = pos_profile.get('currency') or company_data.default_currency
	doc.conversion_rate = 1.0

	if doc.currency != company_data.default_currency:
		doc.conversion_rate = get_exchange_rate(doc.currency, company_data.default_currency, doc.posting_date)

	doc.selling_price_list = pos_profile.get('selling_price_list') or \
		frappe.db.get_value('Selling Settings', None, 'selling_price_list')
	doc.naming_series = pos_profile.get('naming_series') or 'SINV-'
	doc.letter_head = pos_profile.get('letter_head') or company_data.default_letter_head
	doc.ignore_pricing_rule = pos_profile.get('ignore_pricing_rule') or 0
	doc.apply_discount_on = pos_profile.get('apply_discount_on') if pos_profile.get('apply_discount') else ''
	doc.customer_group = pos_profile.get('customer_group') or get_root('Customer Group')
	doc.territory = pos_profile.get('territory') or get_root('Territory')
	doc.terms = frappe.db.get_value('Terms and Conditions', pos_profile.get('tc_name'), 'terms') or doc.terms or ''

def get_root(table):
	root = frappe.db.sql(""" select name from `tab%(table)s` having
		min(lft)"""%{'table': table}, as_dict=1)

	return root[0].name

def update_multi_mode_option(doc, pos_profile):
	from frappe.model import default_fields

	if not pos_profile or not pos_profile.get('payments'):
		for payment in get_mode_of_payment(doc):
			payments = doc.append('payments', {})
			payments.mode_of_payment = payment.parent
			payments.account = payment.default_account
			payments.type = payment.type

		return

	for payment_mode in pos_profile.payments:
		payment_mode = payment_mode.as_dict()

		for fieldname in default_fields:
			if fieldname in payment_mode:
				del payment_mode[fieldname]

		doc.append('payments', payment_mode)

def get_mode_of_payment(doc):
	return frappe.db.sql(""" select mpa.default_account, mpa.parent, mp.type as type from `tabMode of Payment Account` mpa,
		 `tabMode of Payment` mp where mpa.parent = mp.name and mpa.company = %(company)s""", {'company': doc.company}, as_dict=1)

def update_tax_table(doc):
	taxes = get_taxes_and_charges('Sales Taxes and Charges Template', doc.taxes_and_charges)
	for tax in taxes:
		doc.append('taxes', tax)

def get_items_list(pos_profile):
	cond = "1=1"
	item_groups = []
	if pos_profile.get('item_groups'):
		# Get items based on the item groups defined in the POS profile
		for d in pos_profile.get('item_groups'):
			item_groups.extend([d.name for d in get_child_nodes('Item Group', d.item_group)])
		cond = "item_group in (%s)"%(', '.join(['%s']*len(item_groups)))

	return frappe.db.sql(""" 
		select
			name, item_code, item_name, description, item_group, expense_account, has_batch_no,
			has_serial_no, expense_account, selling_cost_center, stock_uom, image, 
			default_warehouse, is_stock_item, barcode, brand
		from
			tabItem
		where
			disabled = 0 and has_variants = 0 and is_sales_item = 1 and {cond}
		""".format(cond=cond), tuple(item_groups), as_dict=1)

def get_item_groups(pos_profile):
	item_group_dict = {}
	if pos_profile.get('item_groups'):
		item_groups = []
		for d in pos_profile.get('item_groups'):
			item_groups.extend(get_child_nodes('Item Group', d.item_group))
	else:
		item_groups = frappe.db.sql("""Select name,
			lft, rgt from `tabItem Group` order by lft""", as_dict=1)

	for data in item_groups:
		item_group_dict[data.name] = [data.lft, data.rgt]
	return item_group_dict

def get_customers_list(pos_profile={}):
	cond = "1=1"
	customer_groups = []
	if pos_profile.get('customer_groups'):
		# Get customers based on the customer groups defined in the POS profile
		for d in pos_profile.get('customer_groups'):
			customer_groups.extend([d.name for d in get_child_nodes('Customer Group', d.customer_group)])
		cond = "customer_group in (%s)"%(', '.join(['%s']*len(customer_groups)))

	return frappe.db.sql(""" select name, customer_name, customer_group,
		territory, customer_pos_id from tabCustomer where disabled = 0
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

def get_serial_no_data(pos_profile, company):
	# get itemwise serial no data
	# example {'Nokia Lumia 1020': {'SN0001': 'Pune'}}
	# where Nokia Lumia 1020 is item code, SN0001 is serial no and Pune is warehouse

	cond = "1=1"
	if pos_profile.get('update_stock') and pos_profile.get('warehouse'):
		cond = "warehouse = '{0}'".format(pos_profile.get('warehouse'))

	serial_nos = frappe.db.sql("""select name, warehouse, item_code from `tabSerial No` where {0}
				and company = %(company)s """.format(cond), {'company': company}, as_dict=1)

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

def get_price_list_data(selling_price_list):
	itemwise_price_list = {}
	price_lists = frappe.db.sql("""Select ifnull(price_list_rate, 0) as price_list_rate,
		item_code from `tabItem Price` ip where price_list = %(price_list)s""",
		{'price_list': selling_price_list}, as_dict=1)

	for item in price_lists:
		itemwise_price_list[item.item_code] = item.price_list_rate

	return itemwise_price_list

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

def get_pricing_rule_data(doc):
	pricing_rules = ""
	if doc.ignore_pricing_rule == 0:
		pricing_rules = frappe.db.sql(""" Select * from `tabPricing Rule` where docstatus < 2
						and ifnull(for_price_list, '') in (%(price_list)s, '') and selling = 1
						and ifnull(company, '') in (%(company)s, '') and disable = 0 and %(date)s
						between ifnull(valid_from, '2000-01-01') and ifnull(valid_upto, '2500-12-31')
						order by priority desc, name desc""",
						{'company': doc.company, 'price_list': doc.selling_price_list, 'date': nowdate()}, as_dict=1)
	return pricing_rules

@frappe.whitelist()
def make_invoice(doc_list={}, email_queue_list={}, customers_list={}):
	if isinstance(doc_list, basestring):
		doc_list = json.loads(doc_list)

	if isinstance(email_queue_list, basestring):
		email_queue_list = json.loads(email_queue_list)

	if isinstance(customers_list, basestring):
		customers_list = json.loads(customers_list)

	customers_list = make_customer_and_address(customers_list)
	name_list = []
	for docs in doc_list:
		for name, doc in docs.items():
			if not frappe.db.exists('Sales Invoice', {'offline_pos_name': name}):
				validate_records(doc)
				si_doc = frappe.new_doc('Sales Invoice')
				si_doc.offline_pos_name = name
				si_doc.update(doc)
				si_doc.set_posting_time = 1
				si_doc.customer = get_customer_id(doc)
				si_doc.due_date = doc.get('posting_date')
				submit_invoice(si_doc, name, doc)
				name_list.append(name)
			else:
				name_list.append(name)

	email_queue = make_email_queue(email_queue_list)
	customers = get_customers_list()
	return {
		'invoice': name_list,
		'email_queue': email_queue,
		'customers': customers_list,
		'synced_customers_list': customers,
		'synced_address': get_customers_address(customers),
		'synced_contacts': get_contacts(customers)
	}

def validate_records(doc):
	validate_item(doc)

def get_customer_id(doc, customer=None):
	cust_id = None
	if doc.get('customer_pos_id'):
		cust_id = frappe.db.get_value('Customer',
			{'customer_pos_id': doc.get('customer_pos_id')}, 'name')

	if not cust_id:
		customer = customer or doc.get('customer')
		if frappe.db.exists('Customer', customer):
			cust_id = customer
		else:
			cust_id = add_customer(doc)

	return cust_id

def make_customer_and_address(customers):
	customers_list = []
	for customer, data in customers.items():
		data = json.loads(data)
		cust_id = get_customer_id(data, customer)
		if not cust_id:
			cust_id = add_customer(data)
		else:
			frappe.db.set_value("Customer", cust_id, "customer_name", data.get('full_name'))

		make_contact(data, cust_id)
		make_address(data, cust_id)
		customers_list.append(customer)
	frappe.db.commit()
	return customers_list

def add_customer(data):
	customer_doc = frappe.new_doc('Customer')
	customer_doc.customer_name = data.get('full_name') or data.get('customer')
	customer_doc.customer_pos_id = data.get('customer_pos_id')
	customer_doc.customer_type = 'Company'
	customer_doc.customer_group = frappe.db.get_single_value('Selling Settings', 'customer_group')
	customer_doc.territory = frappe.db.get_single_value('Selling Settings', 'territory')
	customer_doc.flags.ignore_mandatory = True
	customer_doc.save(ignore_permissions = True)
	frappe.db.commit()
	return customer_doc.name

def make_contact(args,customer):
	if args.get('email_id') or args.get('phone'):
		name = frappe.db.get_value('Dynamic Link',
			{'link_doctype': 'Customer', 'link_name': customer, 'parenttype': 'Contact'}, 'parent')

		args = {
			'first_name': args.get('full_name'),
			'email_id': args.get('email_id'),
			'phone': args.get('phone')
		}

		doc = frappe.new_doc('Contact')
		if name:
			doc = frappe.get_doc('Contact', name)

		doc.update(args)
		doc.is_primary_contact = 1
		if not name:
			doc.append('links',{
				'link_doctype': 'Customer',
				'link_name': customer
			})
		doc.save(ignore_permissions=True)

def make_address(args, customer):
	if not args.get('address_line1'): return
	
	name = args.get('name')

	if not name:
		data = get_customers_address(customer)
		name = data[customer].get('name') if data else None

	if name:
		address = frappe.get_doc('Address', name)
	else:
		address = frappe.new_doc('Address')
		address.country = frappe.db.get_value('Company', args.get('company'), 'country')
		address.append('links',{
			'link_doctype': 'Customer',
			'link_name': customer
		})

	address.is_primary_address = 1
	address.is_shipping_address = 1
	address.update(args)
	address.save(ignore_permissions = True)

def make_email_queue(email_queue):
	name_list = []
	for key, data in email_queue.items():
		name = frappe.db.get_value('Sales Invoice', {'offline_pos_name': key}, 'name')
		data = json.loads(data)
		sender = frappe.session.user
		print_format = "POS Invoice"
		attachments = [frappe.attach_print('Sales Invoice', name, print_format= print_format)]

		make(subject = data.get('subject'), content = data.get('content'), recipients = data.get('recipients'),
			sender=sender,attachments = attachments, send_email=True,
			doctype='Sales Invoice', name=name)
		name_list.append(key)

	return name_list

def validate_item(doc):
	for item in doc.get('items'):
		if not frappe.db.exists('Item', item.get('item_code')):
			item_doc = frappe.new_doc('Item')
			item_doc.name = item.get('item_code')
			item_doc.item_code = item.get('item_code')
			item_doc.item_name = item.get('item_name')
			item_doc.description = item.get('description')
			item_doc.default_warehouse = item.get('warehouse')
			item_doc.stock_uom = item.get('stock_uom')
			item_doc.item_group = item.get('item_group')
			item_doc.save(ignore_permissions=True)
			frappe.db.commit()


def submit_invoice(si_doc, name, doc):
	try:
		si_doc.insert()
		si_doc.submit()
		frappe.db.commit()
	except Exception, e:
		if frappe.message_log: frappe.message_log.pop()
		frappe.db.rollback()
		save_invoice(e, si_doc, name)

def save_invoice(e, si_doc, name):
	if not frappe.db.exists('Sales Invoice', {'offline_pos_name': name}):
		si_doc.docstatus = 0
		si_doc.flags.ignore_mandatory = True
		si_doc.due_date = si_doc.posting_date
		si_doc.insert()
