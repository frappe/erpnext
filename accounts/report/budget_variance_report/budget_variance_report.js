wn.query_reports["Budget Variance Report"] = {
	"filters": [
		{
			fieldname: "fiscal_year",
			label: "Fiscal Year",
			fieldtype: "Link",
			options: "Fiscal Year",
			default: sys_defaults.fiscal_year
		},
		{
			fieldname: "period",
			label: "Period",
			fieldtype: "Select",
			options: "Monthly\nQuarterly\nHalf-Yearly\nYearly",
			default: "Monthly"
		},
		{
			fieldname: "company",
			label: "Company",
			fieldtype: "Link",
			options: "Company",
			default: sys_defaults.company
		},
	]
}