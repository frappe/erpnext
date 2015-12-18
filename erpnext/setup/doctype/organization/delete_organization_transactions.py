# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cint
from frappe import _
from frappe.desk.notifications import clear_notifications

@frappe.whitelist()
def delete_organization_transactions(organization_name):
	frappe.only_for("System Manager")
	doc = frappe.get_doc("Organization", organization_name)

	if frappe.session.user != doc.owner:
		frappe.throw(_("Transactions can only be deleted by the creator of the organization"), frappe.PermissionError)

	delete_bins(organization_name)
	delete_time_logs(organization_name)
	delete_lead_addresses(organization_name)

	for doctype in frappe.db.sql_list("""select parent from
		tabDocField where fieldtype='Link' and options='organization'"""):
		if doctype not in ("Account", "Cost Center", "Warehouse", "Budget Detail", 
			"Party Account", "Employee", "Sales Taxes and Charges Template", 
			"Purchase Taxes and Charges Template", "POS Profile"):
				delete_for_doctype(doctype, organization_name)
			
	# Clear notification counts
	clear_notifications()

def delete_for_doctype(doctype, organization_name):
	meta = frappe.get_meta(doctype)
	organization_fieldname = meta.get("fields", {"fieldtype": "Link",
		"options": "organization"})[0].fieldname

	if not meta.issingle:
		if not meta.istable:
			# delete children
			for df in meta.get_table_fields():
				frappe.db.sql("""delete from `tab{0}` where parent in
					(select name from `tab{1}` where `{2}`=%s)""".format(df.options,
						doctype, organization_fieldname), organization_name)

		# delete parent
		frappe.db.sql("""delete from `tab{0}`
			where {1}= %s """.format(doctype, organization_fieldname), organization_name)

		# reset series
		naming_series = meta.get_field("naming_series")
		if naming_series:
			prefixes = sorted(naming_series.options.split("\n"), lambda a, b: len(b) - len(a))

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


def delete_bins(organization_name):
	frappe.db.sql("""delete from tabBin where warehouse in
			(select name from tabWarehouse where organization=%s)""", organization_name)

def delete_time_logs(organization_name):
	# Delete Time Logs as it is linked to Production Order / Project / Task, which are linked to organization
	frappe.db.sql("""
		delete from `tabTime Log`
		where 
			(ifnull(project, '') != '' 
				and exists(select name from `tabProject` where name=`tabTime Log`.project and organization=%(organization)s))
			or (ifnull(task, '') != '' 
				and exists(select name from `tabTask` where name=`tabTime Log`.task and organization=%(organization)s))
			or (ifnull(production_order, '') != '' 
				and exists(select name from `tabProduction Order` 
					where name=`tabTime Log`.production_order and organization=%(organization)s))
			or (ifnull(sales_invoice, '') != '' 
				and exists(select name from `tabSales Invoice` 
					where name=`tabTime Log`.sales_invoice and organization=%(organization)s))
	""", {"organization": organization_name})

def delete_lead_addresses(organization_name):
	"""Delete addresses to which leads are linked"""
	for lead in frappe.get_all("Lead", filters={"organization": organization_name}):
		frappe.db.sql("""delete from `tabAddress`
			where lead=%s and (customer='' or customer is null) and (supplier='' or supplier is null)""", lead.name)

		frappe.db.sql("""update `tabAddress` set lead=null, lead_name=null where lead=%s""", lead.name)
