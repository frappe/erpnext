# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.utils import getdate, add_days, add_years
from datetime import timedelta

from frappe.model.document import Document

class FiscalYear(Document):

	def set_as_default(self):
		frappe.db.set_value("Global Defaults", None, "current_fiscal_year", self.name)
		frappe.get_doc("Global Defaults").on_update()

		# clear cache
		frappe.clear_cache()

		msgprint(_("{0} is now the default Fiscal Year. Please refresh your browser for the change to take effect.").format(self.name))

	def validate(self):
		year_start_end_dates = frappe.db.sql("""select year_start_date, year_end_date
			from `tabFiscal Year` where name=%s""", (self.name))

		if year_start_end_dates:
			if getdate(self.year_start_date) != year_start_end_dates[0][0] or getdate(self.year_end_date) != year_start_end_dates[0][1]:
				frappe.throw(_("Cannot change Fiscal Year Start Date and Fiscal Year End Date once the Fiscal Year is saved."))

	def on_update(self):
		# validate year start date and year end date
		if getdate(self.year_start_date) > getdate(self.year_end_date):
			frappe.throw(_("Fiscal Year Start Date should not be greater than Fiscal Year End Date"))

		if (getdate(self.year_end_date) - getdate(self.year_start_date)).days > 366:
			frappe.throw(_("Fiscal Year Start Date and Fiscal Year End Date cannot be more than a year apart."))

		check_duplicate_fiscal_year(self)

@frappe.whitelist()
def check_duplicate_fiscal_year(doc):
	year_start_end_dates = frappe.db.sql("""select name, year_start_date, year_end_date from `tabFiscal Year` where name!=%s""", (doc.name))
	for fiscal_year, ysd, yed in year_start_end_dates:
		if (getdate(doc.year_start_date) == ysd and getdate(doc.year_end_date) == yed) and (not frappe.flags.in_test):
					frappe.throw(_("Fiscal Year Start Date and Fiscal Year End Date are already set in Fiscal Year {0}").format(fiscal_year))


@frappe.whitelist()
def auto_create_fiscal_year():
	for d in frappe.db.sql("""select name from `tabFiscal Year` where year_end_date =(current_date + 3)"""):
		try:
			current_fy = frappe.get_doc("Fiscal Year", d[0])

			new_fy = frappe.copy_doc(current_fy)

			new_fy.year_start_date = add_days(current_fy.year_end_date, 1)
			new_fy.year_end_date = add_years(current_fy.year_end_date, 1)

			start_year = new_fy.year_start_date[:4]
			end_year = new_fy.year_end_date[:4]
			new_fy.year = start_year if start_year==end_year else (start_year + "-" + end_year)

			new_fy.insert()
		except frappe.NameError:
			pass
