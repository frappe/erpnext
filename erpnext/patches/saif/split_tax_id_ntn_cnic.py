import frappe
from six import iteritems
from frappe.utils import cstr
import re

cnic_regex = re.compile(r'^.....-.......-.$')
ntn_regex = re.compile(r'^.......-.$')
strn_regex = re.compile(r'^..-..-....-...-..$')

def execute():
	tax_info = frappe._dict()

	for d in frappe.db.sql("select name, tax_id, tax_ntn_cnic from tabCustomer", as_dict=1):
		tax_info[("Customer", d.name)] = d
	for d in frappe.db.sql("select name, tax_id, tax_ntn_cnic from tabSupplier", as_dict=1):
		tax_info[("Supplier", d.name)] = d

	frappe.reload_doc("selling", "doctype", "customer")
	frappe.reload_doc("buying", "doctype", "supplier")
	frappe.reload_doc("selling", "doctype", "sales_order")
	frappe.reload_doc("stock", "doctype", "delivery_note")
	frappe.reload_doc("accounts", "doctype", "sales_invoice")
	frappe.reload_doc("accounts", "doctype", "purchase_invoice")

	for (party_type, party), d in iteritems(tax_info):
		ntn = cnic = strn = ""

		old_tax_id, old_tax_ntn_cnic = "".join(cstr(d.tax_id).split()), "".join(cstr(d.tax_ntn_cnic).split())

		for old_value in (old_tax_id, old_tax_ntn_cnic):
			if old_value:
				if cnic_regex.match(old_value):
					cnic = old_value
				elif strn_regex.match(old_value):
					strn = old_value
				elif ntn_regex.match(old_value):
					ntn = old_value

		if not ntn and not cnic and not strn:
			v = [old_tax_id, old_tax_ntn_cnic]
			v = filter(lambda d: d, v)
			ntn = " // ".join(v)

		frappe.db.set_value(party_type, party, {
			"tax_id": ntn, "tax_cnic": cnic, "tax_strn": strn
		}, None)

	for dt in ['Sales Order', 'Delivery Note', 'Sales Invoice']:
		frappe.db.sql("""
			update `tab{0}` t
			inner join `tabCustomer` p on p.name=t.customer
			set t.tax_id=p.tax_id, t.tax_cnic=p.tax_cnic, t.tax_strn=p.tax_strn
		""".format(dt))

	for dt in ['Purchase Invoice']:
		frappe.db.sql("""
			update `tab{0}` t
			inner join `tabSupplier` p on p.name=t.supplier
			set t.tax_id=p.tax_id, t.tax_cnic=p.tax_cnic, t.tax_strn=p.tax_strn
		""".format(dt))
