# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.utils import nowdate
from erpnext.setup.utils import get_exchange_rate
from erpnext.stock.get_item_details import get_pos_profile
from erpnext.accounts.party import get_party_account_currency
from erpnext.controllers.accounts_controller import get_taxes_and_charges

@frappe.whitelist()
def get_pos_data():
	doc = frappe.new_doc('Sales Invoice')
	doc.update_stock = 1;
	doc.is_pos = 1;
	pos_profile = get_pos_profile(doc.company) or {}

	if pos_profile.get('name'):
		pos_profile = frappe.get_doc('POS Profile', pos_profile.get('name'))
	else:
		frappe.msgprint('<a href="#List/POS Profile">'
			+ _("Welcome to POS: Create your POS Profile") + '</a>');

	update_pos_profile_data(doc, pos_profile)
	update_multi_mode_option(doc, pos_profile)
	default_print_format = pos_profile.get('print_format') or "Point of Sale"
	print_template = frappe.db.get_value('Print Format', default_print_format, 'html')

	return {
		'doc': doc,
		'default_customer': pos_profile.get('customer'),
		'items': get_items(doc, pos_profile),
		'customers': get_customers(pos_profile, doc),
		'pricing_rules': get_pricing_rules(doc),
		'print_template': print_template,
		'write_off_account': pos_profile.get('write_off_account'),
		'meta': {
			'invoice': frappe.get_meta('Sales Invoice'),
			'items': frappe.get_meta('Sales Invoice Item'),
			'taxes': frappe.get_meta('Sales Taxes and Charges')
		}
	}

def update_pos_profile_data(doc, pos_profile):
	company_data = frappe.db.get_value('Company', doc.company, '*', as_dict=1)

	doc.taxes_and_charges = pos_profile.get('taxes_and_charges')
	if doc.taxes_and_charges:
		update_tax_table(doc)

	doc.currency = pos_profile.get('currency') or company_data.default_currency
	doc.conversion_rate = 1.0
	if doc.currency != company_data.default_currency:
		doc.conversion_rate = get_exchange_rate(doc.currency, company_data.default_currency)
	doc.selling_price_list = pos_profile.get('selling_price_list') or frappe.db.get_value('Selling Settings', None, 'selling_price_list')
	doc.naming_series = pos_profile.get('naming_series') or 'SINV-'
	doc.letter_head = pos_profile.get('letter_head') or company_data.default_letter_head
	doc.ignore_pricing_rule = pos_profile.get('ignore_pricing_rule') or 0
	doc.apply_discount_on = pos_profile.get('apply_discount_on') or ''
	doc.customer_group = pos_profile.get('customer_group') or get_root('Customer Group')
	doc.territory = pos_profile.get('territory') or get_root('Territory')

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
		 `tabMode of Payment` mp where mpa.parent = mp.name and company = %(company)s""", {'company': doc.company}, as_dict=1)

def update_tax_table(doc):
	taxes = get_taxes_and_charges('Sales Taxes and Charges Template', doc.taxes_and_charges)
	for tax in taxes:
		doc.append('taxes', tax)

def get_items(doc, pos_profile):
	item_list = []
	for item in frappe.get_all("Item", fields=["*"], filters={'disabled': 0, 'has_variants': 0}):
		item_doc = frappe.get_doc('Item', item.name)
		if item_doc.taxes:
			item.taxes = json.dumps(dict(([d.tax_type, d.tax_rate] for d in
						item_doc.get("taxes"))))

		item.price_list_rate = frappe.db.get_value('Item Price', {'item_code': item.name,
									'price_list': doc.selling_price_list}, 'price_list_rate') or 0
		item.default_warehouse = pos_profile.get('warehouse') or item.default_warehouse or None
		item.expense_account = pos_profile.get('expense_account') or item.expense_account
		item.income_account = pos_profile.get('income_account') or item_doc.income_account
		item.cost_center = pos_profile.get('cost_center') or item_doc.selling_cost_center
		item.actual_qty = frappe.db.get_value('Bin', {'item_code': item.name,
								'warehouse': item.default_warehouse}, 'actual_qty') or 0
		item.serial_nos = get_serial_nos(item, pos_profile)
		item.batch_nos = frappe.db.sql_list("""select name from `tabBatch` where ifnull(expiry_date, '4000-10-10') > curdate()
			and item = %(item_code)s""", {'item_code': item.item_code})

		item_list.append(item)

	return item_list

def get_serial_nos(item, pos_profile):
	cond = "1=1"
	if pos_profile.get('update_stock') and pos_profile.get('warehouse'):
		cond = "warehouse = '{0}'".format(pos_profile.get('warehouse'))

	serial_nos = frappe.db.sql("""select name, warehouse from `tabSerial No` where {0}
				and item_code = %(item_code)s""".format(cond), {'item_code': item.item_code}, as_dict=1)

	serial_no_list = {}
	for serial_no in serial_nos:
		serial_no_list[serial_no.name] = serial_no.warehouse

	return serial_no_list

def get_customers(pos_profile, doc):
	filters = {'disabled': 0}
	customer_list = []
	customers = frappe.get_all("Customer", fields=["*"], filters = filters)

	for customer in customers:
		customer_currency = get_party_account_currency('Customer', customer.name, doc.company) or doc.currency
		if customer_currency == doc.currency:
			customer_list.append(customer)
	return customer_list

def get_pricing_rules(doc):
	pricing_rules = ""
	if doc.ignore_pricing_rule == 0:
		pricing_rules = frappe.db.sql(""" Select * from `tabPricing Rule` where docstatus < 2 and disable = 0
						and selling = 1 and ifnull(company, '') in (%(company)s, '') and
						ifnull(for_price_list, '') in (%(price_list)s, '')  and %(date)s between
						ifnull(valid_from, '2000-01-01') and ifnull(valid_upto, '2500-12-31') order by priority desc, name desc""",
						{'company': doc.company, 'price_list': doc.selling_price_list, 'date': nowdate()}, as_dict=1)
	return pricing_rules

@frappe.whitelist()
def make_invoice(doc_list):
	if isinstance(doc_list, basestring):
		doc_list = json.loads(doc_list)

	name_list = []

	for docs in doc_list:
		for name, doc in docs.items():
			if not frappe.db.exists('Sales Invoice', {'offline_pos_name': name}):
				validate_customer(doc)
				validate_item(doc)
				si_doc = frappe.new_doc('Sales Invoice')
				si_doc.offline_pos_name = name
				si_doc.update(doc)
				submit_invoice(si_doc, name)
				name_list.append(name)

	return name_list

def validate_customer(doc):
	if not frappe.db.exists('Customer', doc.get('customer')):
		customer_doc = frappe.new_doc('Customer')
		customer_doc.customer_name = doc.get('customer')
		customer_doc.customer_type = 'Company'
		customer_doc.customer_group = doc.get('customer_group')
		customer_doc.territory = doc.get('territory')
		customer_doc.save(ignore_permissions = True)
		frappe.db.commit()
		doc['customer'] = customer_doc.name

	return doc

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

def submit_invoice(si_doc, name):
	try:
		si_doc.insert()
		si_doc.submit()
	except Exception, e:
		if frappe.message_log: frappe.message_log.pop()
		frappe.db.rollback()
		save_invoice(e, si_doc, name)

def save_invoice(e, si_doc, name):
		si_doc.docstatus = 0
		si_doc.name = ''
		si_doc.save(ignore_permissions=True)
		make_scheduler_log(e, si_doc.name)

def make_scheduler_log(e, sales_invoice):
	scheduler_log = frappe.new_doc('Scheduler Log')
	scheduler_log.error = e
	scheduler_log.sales_invoice = sales_invoice
	scheduler_log.save(ignore_permissions=True)