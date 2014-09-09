# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.utils import getdate

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

		year_start_end_dates = frappe.db.sql("""select name, year_start_date, year_end_date
			from `tabFiscal Year` where name!=%s""", (self.name))

		for fiscal_year, ysd, yed in year_start_end_dates:
			if (getdate(self.year_start_date) == ysd and getdate(self.year_end_date) == yed) \
				and (not frappe.flags.in_test):
					frappe.throw(_("Fiscal Year Start Date and Fiscal Year End Date are already set in Fiscal Year {0}").format(fiscal_year))
