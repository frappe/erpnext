# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from dateutil.relativedelta import relativedelta
from frappe import _, cint
from frappe.model.document import Document
from frappe.utils import add_days, add_years, cstr, getdate


class FiscalYear(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.fiscal_year_company.fiscal_year_company import FiscalYearCompany

		auto_created: DF.Check
		companies: DF.Table[FiscalYearCompany]
		disabled: DF.Check
		is_short_year: DF.Check
		year: DF.Data
		year_end_date: DF.Date
		year_start_date: DF.Date
	# end: auto-generated types

	def validate(self):
		self.validate_dates()
		self.validate_overlap()

	def on_update(self):
		frappe.cache().delete_key("fiscal_years")

	def on_trash(self):
		frappe.cache().delete_key("fiscal_years")

	def validate_dates(self):
		self.validate_from_to_dates("year_start_date", "year_end_date")
		if self.is_short_year:
			# Fiscal Year can be shorter than one year, in some jurisdictions
			# under certain circumstances. For example, in the USA and Germany.
			return

		date = getdate(self.year_start_date) + relativedelta(years=1) - relativedelta(days=1)

		if getdate(self.year_end_date) != date:
			frappe.throw(
				_("Fiscal Year End Date should be one year after Fiscal Year Start Date"),
				frappe.exceptions.InvalidDates,
			)

	def validate_overlap(self):
		fy = frappe.qb.DocType("Fiscal Year")

		name = self.name or self.year

		existing_fiscal_years = (
			frappe.qb.from_(fy)
			.select(fy.name)
			.where(
				(fy.year_start_date <= self.year_end_date)
				& (fy.year_end_date >= self.year_start_date)
				& (fy.name != name)
			)
			.run(as_dict=True)
		)

		if existing_fiscal_years:
			for existing in existing_fiscal_years:
				company_for_existing = frappe.db.sql_list(
					"""select company from `tabFiscal Year Company`
					where parent=%s""",
					existing.name,
				)

				overlap = False
				if not self.get("companies") and not company_for_existing:
					overlap = True

				for d in self.get("companies"):
					if d.company in company_for_existing:
						overlap = True

				if overlap:
					frappe.throw(
						_(
							"Year start date or end date is overlapping with {0}. To avoid please set company"
						).format(frappe.get_desk_link("Fiscal Year", existing.name, open_in_new_tab=True)),
						frappe.NameError,
					)


def auto_create_fiscal_year():
	fy = frappe.qb.DocType("Fiscal Year")

	# Skipped auto-creating Short Year, as it has very rare use case.
	# Reference: https://www.irs.gov/businesses/small-businesses-self-employed/tax-years (US)
	follow_up_date = add_days(getdate(), days=3)
	fiscal_year = (
		frappe.qb.from_(fy)
		.select(fy.name, fy.year_end_date)
		.where((fy.year_end_date <= follow_up_date) & (fy.is_short_year == 0))
		.run(as_dict=True)
	)

	if not fiscal_year:
		return

	existing_years = set(frappe.get_all("Fiscal Year", pluck="name"))
	for d in fiscal_year:
		year_start_date = add_days(d.year_end_date, 1)
		year_end_date = add_days(add_years(year_start_date, 1), -1)
		start_year = cstr(year_start_date.year)
		end_year = cstr(year_end_date.year)
		year = start_year if start_year == end_year else (start_year + "-" + end_year)
		if year in existing_years:
			continue

		# savepoint so a duplicate-year INSERT (Fiscal Year autoname=field:year) that aborts the
		# statement doesn't poison the whole scheduler transaction on Postgres and kill the next iteration
		frappe.db.savepoint("auto_create_fiscal_year")
		try:
			current_fy = frappe.get_doc("Fiscal Year", d.name)

			new_fy = frappe.new_doc("Fiscal Year")
			new_fy.disabled = cint(current_fy.disabled)

			new_fy.year_start_date = year_start_date
			new_fy.year_end_date = year_end_date
			new_fy.year = year

			for row in current_fy.companies:
				new_fy.append("companies", {"company": row.company})

			new_fy.auto_created = 1

			new_fy.insert(ignore_permissions=True)
			existing_years.add(year)
		except frappe.NameError:
			frappe.db.rollback(save_point="auto_create_fiscal_year")


def get_from_and_to_date(fiscal_year):
	fields = ["year_start_date", "year_end_date"]
	cached_results = frappe.get_cached_value("Fiscal Year", fiscal_year, fields, as_dict=1)
	return dict(from_date=cached_results.year_start_date, to_date=cached_results.year_end_date)
