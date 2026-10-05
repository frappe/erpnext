# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_link_to_form, getdate

from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import get_tax_id_for_party
from erpnext.accounts.utils import get_fiscal_year


class LowerDeductionCertificate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		certificate_limit: DF.Currency
		certificate_no: DF.Data
		company: DF.Link
		fiscal_year: DF.Link
		pan_no: DF.Data
		rate: DF.Percent
		supplier: DF.Link
		tax_withholding_category: DF.Link
		valid_from: DF.Date
		valid_upto: DF.Date
	# end: auto-generated types

	def validate(self):
		self.set_pan_from_supplier()
		self.validate_dates()
		self.validate_rate_and_limit()
		self.validate_supplier_against_tax_category()

	def set_pan_from_supplier(self):
		"""Certificates are matched to invoices by the supplier's tax id, so keep the PAN in line with it."""
		if tax_id := get_tax_id_for_party("Supplier", self.supplier):
			self.pan_no = tax_id

	def validate_dates(self):
		if getdate(self.valid_upto) < getdate(self.valid_from):
			frappe.throw(_("Valid Up To date cannot be before Valid From date"))

		fiscal_year = get_fiscal_year(fiscal_year=self.fiscal_year, as_dict=True)

		if not (fiscal_year.year_start_date <= getdate(self.valid_from) <= fiscal_year.year_end_date):
			frappe.throw(_("Valid From date not in Fiscal Year {0}").format(frappe.bold(self.fiscal_year)))

		if not (fiscal_year.year_start_date <= getdate(self.valid_upto) <= fiscal_year.year_end_date):
			frappe.throw(_("Valid Up To date not in Fiscal Year {0}").format(frappe.bold(self.fiscal_year)))

	def validate_rate_and_limit(self):
		if not 0 <= flt(self.rate) < 100:
			frappe.throw(_("Rate must be at least 0 and less than 100"))
		if flt(self.certificate_limit) <= 0:
			frappe.throw(_("Certificate Limit must be greater than 0"))

	def validate_supplier_against_tax_category(self):
		duplicate_certificate = frappe.db.get_value(
			"Lower Deduction Certificate",
			{
				"supplier": self.supplier,
				"tax_withholding_category": self.tax_withholding_category,
				"name": ("!=", self.name),
				"company": self.company,
			},
			["name", "valid_from", "valid_upto"],
			as_dict=True,
		)
		if duplicate_certificate and self.are_dates_overlapping(duplicate_certificate):
			certificate_link = get_link_to_form("Lower Deduction Certificate", duplicate_certificate.name)
			frappe.throw(
				_(
					"There is already a valid Lower Deduction Certificate {0} for Supplier {1} against category {2} for this time period."
				).format(
					certificate_link, frappe.bold(self.supplier), frappe.bold(self.tax_withholding_category)
				)
			)

	def are_dates_overlapping(self, duplicate_certificate):
		valid_from = duplicate_certificate.valid_from
		valid_upto = duplicate_certificate.valid_upto
		if valid_from <= getdate(self.valid_from) <= valid_upto:
			return True
		elif valid_from <= getdate(self.valid_upto) <= valid_upto:
			return True
		elif getdate(self.valid_from) <= valid_from and valid_upto <= getdate(self.valid_upto):
			return True
		return False
