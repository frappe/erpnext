# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _, _dict
from frappe.utils import nowdate
from frappe.utils.data import fmt_money
from erpnext.accounts.utils import get_fiscal_year
from PyPDF2 import PdfFileWriter
from frappe.utils.pdf import get_pdf
from frappe.utils.print_format import read_multi_pdf
from frappe.utils.jinja import render_template


def execute(filters=None):
	filters = filters if isinstance(filters, _dict) else _dict(filters)
	if not filters:
		filters.setdefault('fiscal_year', get_fiscal_year(nowdate())[0])
		filters.setdefault('company', frappe.db.get_default("company"))
	data = []
	columns = get_columns()
	data = frappe.db.sql("""
		SELECT
			s.supplier_group as "supplier_group",
			gl.party AS "supplier",
			s.tax_id as "tax_id",
			SUM(gl.debit) AS "payments"
		FROM
			`tabGL Entry` gl INNER JOIN `tabSupplier` s
		WHERE
			s.name = gl.party
		AND	s.irs_1099 = 1
		AND gl.fiscal_year = %(fiscal_year)s
		AND gl.party_type = "Supplier"

		GROUP BY
			gl.party

		ORDER BY
			gl.party DESC""", {"fiscal_year": filters.fiscal_year,
		"supplier_group": filters.supplier_group,
		"company": filters.company}, as_dict=True)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "supplier_group",
			"label": _("Supplier Group"),
			"fieldtype": "Link",
			"options": "Supplier Group",
			"width": 200
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 200
		},
		{
			"fieldname": "tax_id",
			"label": _("Tax ID"),
			"fieldtype": "Data",
			"width": 120
		},
		{

			"fieldname": "payments",
			"label": _("Total Payments"),
			"fieldtype": "Currency",
			"width": 120
		}
	]


@frappe.whitelist()
def irs_1099_print(filters):
	if not filters:
		frappe._dict({
			"company": frappe.db.get_default("Company"),
			"fiscal_year": frappe.db.get_default("fiscal_year")})
	else:
		filters = frappe._dict(json.loads(filters))
	company_address = get_payer_address_html(filters.company)
	company_tin = frappe.db.get_value("Company", filters.company, "tax_id")
	columns, data = execute(filters)
	template = frappe.get_doc("Print Format", "IRS 1099 Form").html
	output = PdfFileWriter()
	for row in data:
		row["company"] = filters.company
		row["company_tin"] = company_tin
		row["payer_street_address"] = company_address
		row["recipient_street_address"], row["recipient_city_state"] = get_street_address_html("Supplier", row.supplier)
		row["payments"] = fmt_money(row["payments"], precision=0, currency="USD")
		frappe._dict(row)
		print(row)
		pdf = get_pdf(render_template(template, row), output=output if output else None)
		print(pdf)
	frappe.local.response.filename = filters.fiscal_year + " " + filters.company + " IRS 1099 Forms"
	frappe.local.response.filecontent = read_multi_pdf(output)
	frappe.local.response.type = "download"


def get_payer_address_html(company):
	address_list = frappe.db.sql("""
		SELECT
			name
		FROM
			tabAddress
		WHERE
			is_your_company_address = 1
		ORDER BY
			address_type="Postal" DESC, address_type="Billing" DESC
		LIMIT 1
		""", {"company": company}, as_dict=True)
	if address_list:
		company_address = address_list[0]["name"]
		return frappe.get_doc("Address", company_address).get_display()
	else:
		return ""


def get_street_address_html(party_type, party):
	address_list = frappe.db.sql("""
		SELECT
			link.parent
		FROM `tabDynamic Link` link, `tabAddress` address
		WHERE link.parenttype = "Address"
		AND link.link_name = %(party)s
		ORDER BY address.address_type="Postal" DESC,
			address.address_type="Billing" DESC
		LIMIT 1
		""", {"party": party}, as_dict=True)
	if address_list:
		supplier_address = address_list[0]["parent"]
		doc = frappe.get_doc("Address", supplier_address)
		if doc.address_line2:
			street = doc.address_line1 + "<br>\n" + doc.address_line2 + "<br>\n"
		else:
			street = doc.address_line1 + "<br>\n"
		city = doc.city + ", " if doc.city else ""
		city = city + doc.state + " " if doc.state else city
		city = city + doc.pincode if doc.pincode else city
		city += "<br>\n"
		return street, city
	else:
		return "", ""
