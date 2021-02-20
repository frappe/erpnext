# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cint
from frappe import _
from frappe.desk.notifications import clear_notifications

import functools

@frappe.whitelist()
def delete_company_transactions(company_name):
	frappe.only_for("System Manager")
	doc = frappe.get_doc("Company", company_name)

	if frappe.session.user != doc.owner:
		frappe.throw(_("Transactions can only be deleted by the creator of the Company"),
			frappe.PermissionError)

	delete_bins(company_name)
	delete_lead_addresses(company_name)

	for doctype in frappe.db.sql_list("""select parent from
		tabDocField where fieldtype='Link' and options='Company'"""):
		if doctype not in ("Account", "Cost Center", "Warehouse", "Budget",
			"Party Account", "Employee", "Sales Taxes and Charges Template",
			"Purchase Taxes and Charges Template", "POS Profile", "BOM",
			"Company", "Bank Account", "Item Tax Template", "Mode Of Payment",
			"Item Default", "Customer", "Supplier", "GST Account"):
				delete_for_doctype(doctype, company_name)

	# reset company values
	doc.total_monthly_sales = 0
	doc.sales_monthly_history = None
	doc.save()
	# Clear notification counts
	clear_notifications()

def delete_for_doctype(doctype, company_name):
	meta = frappe.get_meta(doctype)
	company_fieldname = meta.get("fields", {"fieldtype": "Link",
		"options": "Company"})[0].fieldname

	if not meta.issingle:
		if not meta.istable:
			# delete communication
			delete_communications(doctype, company_name, company_fieldname)

			# delete children
			for df in meta.get_table_fields():
				frappe.db.sql("""delete from `tab{0}` where parent in
					(select name from `tab{1}` where `{2}`=%s)""".format(df.options,
						doctype, company_fieldname), company_name)

		#delete version log
		frappe.db.sql("""delete from `tabVersion` where ref_doctype=%s and docname in
			(select name from `tab{0}` where `{1}`=%s)""".format(doctype,
				company_fieldname), (doctype, company_name))

		# delete parent
		frappe.db.sql("""delete from `tab{0}`
			where {1}= %s """.format(doctype, company_fieldname), company_name)

		# reset series
		naming_series = meta.get_field("naming_series")
		if naming_series and naming_series.options:
			prefixes = sorted(naming_series.options.split("\n"),
				key=functools.cmp_to_key(lambda a, b: len(b) - len(a)))

			for prefix in prefixes:
				if prefix:
					last = frappe.db.sql("""select max(name) from `tab{0}`
						where name like %s""".format(doctype), prefix + "%")
					if last and last[0][0]:
						last = cint(last[0][0].replace(prefix, ""))
					else:
						last = 0

					frappe.db.sql("""update tabSeries set current = %s
						where name=%s""", (last, prefix))

def delete_bins(company_name):
	frappe.db.sql("""delete from tabBin where warehouse in
			(select name from tabWarehouse where company=%s)""", company_name)

def delete_lead_addresses(company_name):
	"""Delete addresses to which leads are linked"""
	leads = frappe.get_all("Lead", filters={"company": company_name})
	leads = [ "'%s'"%row.get("name") for row in leads ]
	addresses = []
	if leads:
		addresses = frappe.db.sql_list("""select parent from `tabDynamic Link` where link_name
			in ({leads})""".format(leads=",".join(leads)))

		if addresses:
			addresses = ["%s" % frappe.db.escape(addr) for addr in addresses]

			frappe.db.sql("""delete from tabAddress where name in ({addresses}) and
				name not in (select distinct dl1.parent from `tabDynamic Link` dl1
				inner join `tabDynamic Link` dl2 on dl1.parent=dl2.parent
				and dl1.link_doctype<>dl2.link_doctype)""".format(addresses=",".join(addresses)))

			frappe.db.sql("""delete from `tabDynamic Link` where link_doctype='Lead'
				and parenttype='Address' and link_name in ({leads})""".format(leads=",".join(leads)))

		frappe.db.sql("""update tabCustomer set lead_name=NULL where lead_name in ({leads})""".format(leads=",".join(leads)))

def delete_communications(doctype, company_name, company_fieldname):
		reference_docs = frappe.get_all(doctype, filters={company_fieldname:company_name})
		reference_doc_names = [r.name for r in reference_docs]

		communications = frappe.get_all("Communication", filters={"reference_doctype":doctype,"reference_name":["in", reference_doc_names]})
		communication_names = [c.name for c in communications]

		frappe.delete_doc("Communication", communication_names, ignore_permissions=True)
