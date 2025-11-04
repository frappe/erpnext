# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
# coding=utf-8


import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.permissions import add_permission, update_permission_property

from erpnext.regional.italy import (
	fiscal_regimes,
	mode_of_payment_codes,
	tax_exemption_reasons,
	vat_collectability_options,
)


def setup(company=None, patch=True):
	make_custom_fields()
	setup_report()
	add_permissions()


def make_custom_fields(update=True):
	invoice_item_fields = [
		dict(
			fieldname="tax_rate",
			label="Tax Rate",
			fieldtype="Float",
			insert_after="description",
			print_hide=1,
			hidden=1,
			read_only=1,
		),
		dict(
			fieldname="tax_amount",
			label="Tax Amount",
			fieldtype="Currency",
			insert_after="tax_rate",
			print_hide=1,
			hidden=1,
			read_only=1,
			options="currency",
		),
		dict(
			fieldname="total_amount",
			label="Total Amount",
			fieldtype="Currency",
			insert_after="tax_amount",
			print_hide=1,
			hidden=1,
			read_only=1,
			options="currency",
		),
	]

	customer_po_fields = [
		dict(
			fieldname="customer_po_details",
			label="Customer PO",
			fieldtype="Section Break",
			insert_after="image",
		),
		dict(
			fieldname="customer_po_no",
			label="Customer PO No",
			fieldtype="Data",
			insert_after="customer_po_details",
			fetch_from="sales_order.po_no",
			print_hide=1,
			allow_on_submit=1,
			fetch_if_empty=1,
			read_only=1,
			no_copy=1,
		),
		dict(
			fieldname="customer_po_clm_brk",
			label="",
			fieldtype="Column Break",
			insert_after="customer_po_no",
			print_hide=1,
			read_only=1,
		),
		dict(
			fieldname="customer_po_date",
			label="Customer PO Date",
			fieldtype="Date",
			insert_after="customer_po_clm_brk",
			fetch_from="sales_order.po_date",
			print_hide=1,
			allow_on_submit=1,
			fetch_if_empty=1,
			read_only=1,
			no_copy=1,
		),
	]

	custom_fields = {
		"Company": [
			dict(
				fieldname="sb_e_invoicing",
				label="E-Invoicing",
				fieldtype="Section Break",
				insert_after="date_of_establishment",
				print_hide=1,
			),
			dict(
				fieldname="fiscal_regime",
				label="Fiscal Regime",
				fieldtype="Select",
				insert_after="sb_e_invoicing",
				print_hide=1,
				options="\n".join(map(lambda x: frappe.safe_decode(x, encoding="utf-8"), fiscal_regimes)),
			),
			dict(
				fieldname="fiscal_code",
				label="Fiscal Code",
				fieldtype="Data",
				insert_after="fiscal_regime",
				print_hide=1,
				description=_("Applicable if the company is an Individual or a Proprietorship"),
			),
			dict(
				fieldname="vat_collectability",
				label="VAT Collectability",
				fieldtype="Select",
				insert_after="fiscal_code",
				print_hide=1,
				options="\n".join(
					map(lambda x: frappe.safe_decode(x, encoding="utf-8"), vat_collectability_options)
				),
			),
			dict(
				fieldname="cb_e_invoicing1",
				fieldtype="Column Break",
				insert_after="vat_collectability",
				print_hide=1,
			),
			dict(
				fieldname="registrar_office_province",
				label="Province of the Registrar Office",
				fieldtype="Data",
				insert_after="cb_e_invoicing1",
				print_hide=1,
				length=2,
			),
			dict(
				fieldname="registration_number",
				label="Registration Number",
				fieldtype="Data",
				insert_after="registrar_office_province",
				print_hide=1,
				length=20,
			),
			dict(
				fieldname="share_capital_amount",
				label="Share Capital",
				fieldtype="Currency",
				insert_after="registration_number",
				print_hide=1,
				description=_("Applicable if the company is SpA, SApA or SRL"),
			),
			dict(
				fieldname="no_of_members",
				label="No of Members",
				fieldtype="Select",
				insert_after="share_capital_amount",
				print_hide=1,
				options="\nSU-Socio Unico\nSM-Piu Soci",
				description=_("Applicable if the company is a limited liability company"),
			),
			dict(
				fieldname="liquidation_state",
				label="Liquidation State",
				fieldtype="Select",
				insert_after="no_of_members",
				print_hide=1,
				options="\nLS-In Liquidazione\nLN-Non in Liquidazione",
			),
		],
		"Sales Taxes and Charges": [
			dict(
				fieldname="tax_exemption_reason",
				label="Tax Exemption Reason",
				fieldtype="Select",
				insert_after="included_in_print_rate",
				print_hide=1,
				depends_on='eval:doc.charge_type!="Actual" && doc.rate==0.0',
				options="\n"
				+ "\n".join(map(lambda x: frappe.safe_decode(x, encoding="utf-8"), tax_exemption_reasons)),
			),
			dict(
				fieldname="tax_exemption_law",
				label="Tax Exempt Under",
				fieldtype="Text",
				insert_after="tax_exemption_reason",
				print_hide=1,
				depends_on='eval:doc.charge_type!="Actual" && doc.rate==0.0',
			),
		],
		"Customer": [
			dict(
				fieldname="fiscal_code",
				label="Fiscal Code",
				fieldtype="Data",
				insert_after="tax_id",
				print_hide=1,
			),
			dict(
				fieldname="recipient_code",
				label="Recipient Code",
				fieldtype="Data",
				insert_after="fiscal_code",
				print_hide=1,
				default="0000000",
			),
			dict(
				fieldname="pec",
				label="Recipient PEC",
				fieldtype="Data",
				insert_after="fiscal_code",
				print_hide=1,
			),
			dict(
				fieldname="is_public_administration",
				label="Is Public Administration",
				fieldtype="Check",
				insert_after="is_internal_customer",
				print_hide=1,
				description=_("Set this if the customer is a Public Administration company."),
				depends_on='eval:doc.customer_type=="Company"',
			),
			dict(
				fieldname="first_name",
				label="First Name",
				fieldtype="Data",
				insert_after="salutation",
				print_hide=1,
				depends_on='eval:doc.customer_type!="Company"',
			),
			dict(
				fieldname="last_name",
				label="Last Name",
				fieldtype="Data",
				insert_after="first_name",
				print_hide=1,
				depends_on='eval:doc.customer_type!="Company"',
			),
		],
		"Mode of Payment": [
			dict(
				fieldname="mode_of_payment_code",
				label="Code",
				fieldtype="Select",
				insert_after="included_in_print_rate",
				print_hide=1,
				options="\n".join(
					map(lambda x: frappe.safe_decode(x, encoding="utf-8"), mode_of_payment_codes)
				),
			)
		],
		"Payment Schedule": [
			dict(
				fieldname="mode_of_payment_code",
				label="Code",
				fieldtype="Select",
				insert_after="mode_of_payment",
				print_hide=1,
				options="\n".join(
					map(lambda x: frappe.safe_decode(x, encoding="utf-8"), mode_of_payment_codes)
				),
				fetch_from="mode_of_payment.mode_of_payment_code",
				read_only=1,
			),
			dict(
				fieldname="bank_account",
				label="Bank Account",
				fieldtype="Link",
				insert_after="mode_of_payment_code",
				print_hide=1,
				options="Bank Account",
			),
			dict(
				fieldname="bank_account_name",
				label="Bank Name",
				fieldtype="Data",
				insert_after="bank_account",
				print_hide=1,
				fetch_from="bank_account.bank",
				read_only=1,
			),
			dict(
				fieldname="bank_account_no",
				label="Bank Account No",
				fieldtype="Data",
				insert_after="bank_account_name",
				print_hide=1,
				fetch_from="bank_account.bank_account_no",
				read_only=1,
			),
			dict(
				fieldname="bank_account_iban",
				label="IBAN",
				fieldtype="Data",
				insert_after="bank_account_name",
				print_hide=1,
				fetch_from="bank_account.iban",
				read_only=1,
			),
			dict(
				fieldname="bank_account_swift_number",
				label="Swift Code (BIC)",
				fieldtype="Data",
				insert_after="bank_account_iban",
				print_hide=1,
				fetch_from="bank_account.swift_number",
				read_only=1,
			),
		],
		"Sales Invoice": [
			dict(
				fieldname="vat_collectability",
				label="VAT Collectability",
				fieldtype="Select",
				insert_after="taxes_and_charges",
				print_hide=1,
				options="\n".join(
					map(lambda x: frappe.safe_decode(x, encoding="utf-8"), vat_collectability_options)
				),
				fetch_from="company.vat_collectability",
			),
			dict(
				fieldname="sb_e_invoicing_reference",
				label="E-Invoicing",
				fieldtype="Section Break",
				insert_after="against_income_account",
				print_hide=1,
			),
			dict(
				fieldname="company_fiscal_code",
				label="Company Fiscal Code",
				fieldtype="Data",
				insert_after="sb_e_invoicing_reference",
				print_hide=1,
				read_only=1,
				fetch_from="company.fiscal_code",
			),
			dict(
				fieldname="company_fiscal_regime",
				label="Company Fiscal Regime",
				fieldtype="Data",
				insert_after="company_fiscal_code",
				print_hide=1,
				read_only=1,
				fetch_from="company.fiscal_regime",
			),
			dict(
				fieldname="cb_e_invoicing_reference",
				fieldtype="Column Break",
				insert_after="company_fiscal_regime",
				print_hide=1,
			),
			dict(
				fieldname="customer_fiscal_code",
				label="Customer Fiscal Code",
				fieldtype="Data",
				insert_after="cb_e_invoicing_reference",
				read_only=1,
				fetch_from="customer.fiscal_code",
			),
			dict(
				fieldname="type_of_document",
				label="Type of Document",
				fieldtype="Select",
				insert_after="customer_fiscal_code",
				options="\nTD01\nTD02\nTD03\nTD04\nTD05\nTD06\nTD16\nTD17\nTD18\nTD19\nTD20\nTD21\nTD22\nTD23\nTD24\nTD25\nTD26\nTD27",
			),
		],
		"Purchase Invoice Item": invoice_item_fields,
		"POS Invoice Item": invoice_item_fields,
		"Sales Order Item": invoice_item_fields,
		"Delivery Note Item": invoice_item_fields,
		"Sales Invoice Item": invoice_item_fields + customer_po_fields,
		"Quotation Item": invoice_item_fields,
		"Purchase Order Item": invoice_item_fields,
		"Purchase Receipt Item": invoice_item_fields,
		"Supplier Quotation Item": invoice_item_fields,
		"Address": [
			dict(
				fieldname="country_code",
				label="Country Code",
				fieldtype="Data",
				insert_after="country",
				print_hide=1,
				read_only=0,
				fetch_from="country.code",
			),
			dict(
				fieldname="state_code",
				label="State Code",
				fieldtype="Data",
				insert_after="state",
				print_hide=1,
			),
		],
		"Purchase Invoice": [
			dict(
				fieldname="document_type",
				label="Document Type",
				fieldtype="Data",
				insert_after="company",
				print_hide=1,
				read_only=1,
			),
			dict(
				fieldname="destination_code",
				label="Destination Code",
				fieldtype="Data",
				insert_after="company",
				print_hide=1,
				read_only=1,
			),
			dict(
				fieldname="imported_grand_total",
				label="Imported Grand Total",
				fieldtype="Data",
				insert_after="update_auto_repeat_reference",
				print_hide=1,
				read_only=1,
			),
		],
		"Purchase Taxes and Charges": [
			dict(
				fieldname="tax_rate",
				label="Tax Rate",
				fieldtype="Data",
				insert_after="parenttype",
				print_hide=1,
				read_only=0,
			)
		],
		"Supplier": [
			dict(
				fieldname="fiscal_code",
				label="Fiscal Code",
				fieldtype="Data",
				insert_after="tax_id",
				print_hide=1,
				read_only=1,
			),
			dict(
				fieldname="fiscal_regime",
				label="Fiscal Regime",
				fieldtype="Select",
				insert_after="fiscal_code",
				print_hide=1,
				read_only=1,
				options="\nRF01\nRF02\nRF04\nRF05\nRF06\nRF07\nRF08\nRF09\nRF10\nRF11\nRF12\nRF13\nRF14\nRF15\nRF16\nRF17\nRF18\nRF19",
			),
		],
	}

	create_custom_fields(custom_fields, ignore_validate=frappe.flags.in_patch, update=update)


def setup_report():
	report_name = "Electronic Invoice Register"
	frappe.db.set_value("Report", report_name, "disabled", 0)

	if not frappe.db.get_value("Custom Role", dict(report=report_name)):
		frappe.get_doc(
			dict(
				doctype="Custom Role",
				report=report_name,
				roles=[dict(role="Accounts User"), dict(role="Accounts Manager")],
			)
		).insert()


def add_permissions():
	doctype = "Import Supplier Invoice"
	add_permission(doctype, "All", 0)

	for role in ("Accounts Manager", "Accounts User", "Purchase User", "Auditor"):
		add_permission(doctype, role, 0)
		update_permission_property(doctype, role, 0, "print", 1)
		update_permission_property(doctype, role, 0, "report", 1)

		if role in ("Accounts Manager", "Accounts User"):
			update_permission_property(doctype, role, 0, "write", 1)
			update_permission_property(doctype, role, 0, "create", 1)

	update_permission_property(doctype, "Accounts Manager", 0, "delete", 1)
	add_permission(doctype, "Accounts Manager", 1)
	update_permission_property(doctype, "Accounts Manager", 1, "write", 1)
	update_permission_property(doctype, "Accounts Manager", 1, "create", 1)
