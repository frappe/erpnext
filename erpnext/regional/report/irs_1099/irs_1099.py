# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import cstr, nowdate
from frappe.utils.data import fmt_money
from frappe.utils.jinja import render_template
from frappe.utils.pdf import get_pdf
from frappe.utils.print_format import read_multi_pdf
from pypdf import PdfWriter

from erpnext.accounts.utils import get_fiscal_year

IRS_1099_FORMS_FILE_EXTENSION = ".pdf"


def execute(filters=None):
	filters = filters if isinstance(filters, frappe._dict) else frappe._dict(filters)
	if not filters:
		filters.setdefault("fiscal_year", get_fiscal_year(nowdate())[0])
		filters.setdefault("company", frappe.db.get_default("company"))

	region = frappe.db.get_value("Company", filters={"name": filters.company}, fieldname=["country"])

	if region != "United States":
		return [], []

	columns = get_columns()
	conditions = ""
	if filters.supplier_group:
		conditions += "AND s.supplier_group = %s" % frappe.db.escape(filters.get("supplier_group"))

	data = frappe.db.sql(
		f"""
		SELECT
			s.supplier_group as "supplier_group",
			gl.party AS "supplier",
			s.tax_id as "tax_id",
			SUM(gl.debit_in_account_currency) AS "payments"
		FROM
			`tabGL Entry` gl
				INNER JOIN `tabSupplier` s
		WHERE
			s.name = gl.party
				AND s.irs_1099 = 1
				AND gl.fiscal_year = %(fiscal_year)s
				AND gl.party_type = 'Supplier'
				AND gl.company = %(company)s
				{conditions}

		GROUP BY
			gl.party

		ORDER BY
			gl.party DESC""",
		{"fiscal_year": filters.fiscal_year, "company": filters.company},
		as_dict=True,
	)

	return columns, data


def get_columns():
	return [
		{
			"fieldname": "supplier_group",
			"label": _("Supplier Group"),
			"fieldtype": "Link",
			"options": "Supplier Group",
			"width": 200,
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 200,
		},
		{"fieldname": "tax_id", "label": _("Tax ID"), "fieldtype": "Data", "width": 200},
		{"fieldname": "payments", "label": _("Total Payments"), "fieldtype": "Currency", "width": 200},
	]


@frappe.whitelist()
def irs_1099_print(filters):
	if not filters:
		frappe._dict(
			{
				"company": frappe.db.get_default("Company"),
				"fiscal_year": frappe.db.get_default("Fiscal Year"),
			}
		)
	else:
		filters = frappe._dict(json.loads(filters))

	fiscal_year_doc = get_fiscal_year(fiscal_year=filters.fiscal_year, as_dict=True)
	fiscal_year = cstr(fiscal_year_doc.year_start_date.year)

	company_address = get_payer_address_html(filters.company)
	company_tin = frappe.db.get_value("Company", filters.company, "tax_id")

	columns, data = execute(filters)
	template = frappe.get_doc("Print Format", "IRS 1099 Form").html
	output = PdfWriter()

	for row in data:
		row["fiscal_year"] = fiscal_year
		row["company"] = filters.company
		row["company_tin"] = company_tin
		row["payer_street_address"] = company_address
		row["recipient_street_address"], row["recipient_city_state"] = get_street_address_html(
			"Supplier", row.supplier
		)
		row["payments"] = fmt_money(row["payments"], precision=0, currency="USD")
		get_pdf(render_template(template, row), output=output if output else None)

	frappe.local.response.filename = (
		f"{filters.fiscal_year} {filters.company} IRS 1099 Forms{IRS_1099_FORMS_FILE_EXTENSION}"
	)
	frappe.local.response.filecontent = read_multi_pdf(output)
	frappe.local.response.type = "download"


def get_payer_address_html(company):
	address_list = frappe.db.sql(
		"""
		SELECT
			name
		FROM
			tabAddress
		WHERE
			is_your_company_address = 1
		ORDER BY
			address_type="Postal" DESC, address_type="Billing" DESC
		LIMIT 1
	""",
		{"company": company},
		as_dict=True,
	)

	address_display = ""
	if address_list:
		company_address = address_list[0]["name"]
		address_display = frappe.get_doc("Address", company_address).get_display()

	return address_display


def get_street_address_html(party_type, party):
	address_list = frappe.db.sql(
		"""
		SELECT
			link.parent
		FROM
			`tabDynamic Link` link,
			`tabAddress` address
		WHERE
			link.parenttype = "Address"
				AND link.link_name = %(party)s
		ORDER BY
			address.address_type="Postal" DESC,
			address.address_type="Billing" DESC
		LIMIT 1
	""",
		{"party": party},
		as_dict=True,
	)

	street_address = city_state = ""
	if address_list:
		supplier_address = address_list[0]["parent"]
		doc = frappe.get_doc("Address", supplier_address)

		if doc.address_line2:
			street_address = doc.address_line1 + "<br>\n" + doc.address_line2 + "<br>\n"
		else:
			street_address = doc.address_line1 + "<br>\n"

		city_state = doc.city + ", " if doc.city else ""
		city_state = city_state + doc.state + " " if doc.state else city_state
		city_state = city_state + doc.pincode if doc.pincode else city_state
		city_state += "<br>\n"

	return street_address, city_state
