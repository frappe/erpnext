# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, flt


class MonthlyDistribution(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.monthly_distribution_percentage.monthly_distribution_percentage import (
			MonthlyDistributionPercentage,
		)

		distribution_id: DF.Data
		fiscal_year: DF.Link | None
		percentages: DF.Table[MonthlyDistributionPercentage]
	# end: auto-generated types

	@frappe.whitelist()
	def get_months(self):
		month_list = [
			"January",
			"February",
			"March",
			"April",
			"May",
			"June",
			"July",
			"August",
			"September",
			"October",
			"November",
			"December",
		]
		idx = 1
		for m in month_list:
			mnth = self.append("percentages")
			mnth.month = m
			mnth.percentage_allocation = 100.0 / 12
			mnth.idx = idx
			idx += 1

	def validate(self):
		total = sum(flt(d.percentage_allocation) for d in self.get("percentages"))

		if flt(total, 2) != 100.0:
			frappe.throw(_("Percentage Allocation should be equal to 100%") + f" ({flt(total, 2)!s}%)")


def get_periodwise_distribution_data(distribution_id, period_list, periodicity):
	doc = frappe.get_doc("Monthly Distribution", distribution_id)

	months_to_add = {"Yearly": 12, "Half-Yearly": 6, "Quarterly": 3, "Monthly": 1}[periodicity]

	period_dict = {}

	for d in period_list:
		period_dict[d.key] = get_percentage(doc, d.from_date, months_to_add)

	return period_dict


def get_percentage(doc, start_date, period):
	percentage = 0
	months = [start_date.strftime("%B").title()]

	for r in range(1, period):
		months.append(add_months(start_date, r).strftime("%B").title())

	for d in doc.percentages:
		if d.month in months:
			percentage += d.percentage_allocation

	return percentage
