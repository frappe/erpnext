import frappe
from frappe import _

from erpnext.accounts.report.tax_withholding_details.tax_withholding_details import (
	TaxWithholdingDetailsReport,
)
from erpnext.accounts.utils import get_fiscal_year


class TDSComputationSummaryReport(TaxWithholdingDetailsReport):
	GROUP_BY_FIELDS = ("party_type", "party", "tax_withholding_category")
	CARRY_OVER_FIELDS = (
		"tax_id",
		"party",
		"party_type",
		"party_name",
		"tax_withholding_category",
		"party_entity_type",
		"rate",
	)
	AGGREGATE_FIELDS = ("total_amount", "tax_amount")

	def validate_filters(self):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date must be before To Date"))

		from_year = get_fiscal_year(self.filters.from_date)[0]
		to_year = get_fiscal_year(self.filters.to_date)[0]
		if from_year != to_year:
			frappe.throw(_("From Date and To Date lie in different Fiscal Year"))

		self.filters.fiscal_year = from_year

	def get_data(self):
		return self.group_rows(super().get_data())

	def group_rows(self, data):
		grouped = {}
		for row in data:
			key = tuple(row.get(f) for f in self.GROUP_BY_FIELDS)
			bucket = grouped.setdefault(
				key,
				{
					**{f: row.get(f) for f in self.CARRY_OVER_FIELDS},
					**{f: 0.0 for f in self.AGGREGATE_FIELDS},
				},
			)

			for f in self.AGGREGATE_FIELDS:
				bucket[f] += row.get(f) or 0.0

		return list(grouped.values())

	def get_columns(self):
		party_type = self.filters.get("party_type", "Party")
		return [
			{"label": _("Tax Id"), "fieldname": "tax_id", "fieldtype": "Data", "width": 90},
			{
				"label": _(party_type),
				"fieldname": "party",
				"fieldtype": "Dynamic Link",
				"options": "party_type",
				"width": 180,
			},
			{
				"label": _(f"{party_type} Name"),
				"fieldname": "party_name",
				"fieldtype": "Data",
				"width": 180,
			},
			{
				"label": _("Tax Withholding Category"),
				"options": "Tax Withholding Category",
				"fieldname": "tax_withholding_category",
				"fieldtype": "Link",
				"width": 180,
			},
			{
				"label": _(f"{party_type} Type"),
				"fieldname": "party_entity_type",
				"fieldtype": "Data",
				"width": 180,
			},
			{"label": _("Tax Rate %"), "fieldname": "rate", "fieldtype": "Percent", "width": 120},
			{
				"label": _("Total Taxable Amount"),
				"fieldname": "total_amount",
				"fieldtype": "Float",
				"width": 120,
			},
			{"label": _("Tax Amount"), "fieldname": "tax_amount", "fieldtype": "Float", "width": 120},
		]


execute = TDSComputationSummaryReport.execute
