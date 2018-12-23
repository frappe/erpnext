# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, random, erpnext
from frappe.utils import flt
from frappe.utils.make_random import add_random_children, get_random
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounting.party import get_party_account_currency
from erpnext.accounting.doctype.payment_request.payment_request import make_payment_request, make_payment_entry

def work(domain="Manufacturing"):
	frappe.set_user(frappe.db.get_global('demo_sales_user_2'))

	for i in range(random.randint(1,7)):
		if random.random() < 0.5:
			make_opportunity(domain)

	for i in range(random.randint(1,3)):
		if random.random() < 0.5:
			make_quotation(domain)

	# lost quotations / inquiries
	if random.random() < 0.3:
		for i in range(random.randint(1,3)):
			quotation = get_random('Quotation', doc=True)
			if quotation and quotation.status == 'Submitted':
				quotation.declare_order_lost('Did not ask')

		for i in range(random.randint(1,3)):
			opportunity = get_random('Opportunity', doc=True)
			if opportunity and opportunity.status in ('Open', 'Replied'):
				opportunity.declare_enquiry_lost('Did not ask')

	for i in range(random.randint(1,3)):
		if random.random() < 0.6:
			make_sales_order()

	if random.random() < 0.5:
		#make payment request against Sales Order
		sales_order_name = get_random("Sales Order", filters={"docstatus": 1})
		try:
			if sales_order_name:
				so = frappe.get_doc("Sales Order", sales_order_name)
				if flt(so.per_billed) != 100:
					payment_request = make_payment_request(dt="Sales Order", dn=so.name, recipient_id=so.contact_email,
						submit_doc=True, mute_email=True, use_dummy_message=True)

					payment_entry = frappe.get_doc(make_payment_entry(payment_request.name))
					payment_entry.posting_date = frappe.flags.current_date
					payment_entry.submit()
		except Exception:
			pass

def make_opportunity(domain):
	b = frappe.get_doc({
		"doctype": "Opportunity",
		"enquiry_from": "Customer",
		"customer": get_random("Customer"),
		"opportunity_type": "Sales",
		"with_items": 1,
		"transaction_date": frappe.flags.current_date,
	})

	add_random_children(b, "items", rows=4, randomize = {
		"qty": (1, 5),
		"item_code": ("Item", {"has_variants": 0, "is_fixed_asset": 0, "domain": domain})
	}, unique="item_code")

	b.insert()
	frappe.db.commit()

def make_quotation(domain):
	# get open opportunites
	opportunity = get_random("Opportunity", {"status": "Open", "with_items": 1})

	if opportunity:
		from erpnext.crm.doctype.opportunity.opportunity import make_quotation
		qtn = frappe.get_doc(make_quotation(opportunity))
		qtn.insert()
		frappe.db.commit()
		qtn.submit()
		frappe.db.commit()
	else:
		# make new directly

		# get customer, currency and exchange_rate
		customer = get_random("Customer")

		company_currency = frappe.get_cached_value('Company',  erpnext.get_default_company(),  "default_currency")
		party_account_currency = get_party_account_currency("Customer", customer, erpnext.get_default_company())
		if company_currency == party_account_currency:
			exchange_rate = 1
		else:
			exchange_rate = get_exchange_rate(party_account_currency, company_currency, args="for_selling")

		qtn = frappe.get_doc({
			"creation": frappe.flags.current_date,
			"doctype": "Quotation",
			"quotation_to": "Customer",
			"customer": customer,
			"currency": party_account_currency or company_currency,
			"conversion_rate": exchange_rate,
			"order_type": "Sales",
			"transaction_date": frappe.flags.current_date,
		})

		add_random_children(qtn, "items", rows=3, randomize = {
			"qty": (1, 5),
			"item_code": ("Item", {"has_variants": "0", "is_fixed_asset": 0, "domain": domain})
		}, unique="item_code")

		qtn.insert()
		frappe.db.commit()
		qtn.submit()
		frappe.db.commit()

def make_sales_order():
	q = get_random("Quotation", {"status": "Submitted"})
	if q:
		from erpnext.selling.doctype.quotation.quotation import make_sales_order as mso
		so = frappe.get_doc(mso(q))
		so.transaction_date = frappe.flags.current_date
		so.delivery_date = frappe.utils.add_days(frappe.flags.current_date, 10)
		so.insert()
		frappe.db.commit()
		so.submit()
		frappe.db.commit()
