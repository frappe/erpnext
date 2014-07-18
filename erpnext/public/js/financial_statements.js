frappe.provide("erpnext.financial_statements");

erpnext.financial_statements = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("company"),
			"reqd": 1
		},
		{
			"fieldname":"fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.defaults.get_user_default("fiscal_year"),
			"reqd": 1
		},
		{
			"fieldname": "periodicity",
			"label": __("Periodicity"),
			"fieldtype": "Select",
			"options": "Yearly\nHalf-yearly\nQuarterly\nMonthly",
			"default": "Yearly",
			"reqd": 1
		},
		{
			"fieldname": "depth",
			"label": __("Depth"),
			"fieldtype": "Select",
			"options": "3\n4\n5",
			"default": "3"
		}
	],
	"formatter": function(row, cell, value, columnDef, dataContext) {
		if (columnDef.df.fieldname=="account") {
			var link = $("<a></a>")
				.text(dataContext.account_name)
				.attr("onclick", 'erpnext.financial_statements.open_general_ledger("' + dataContext.account + '")');

			var span = $("<span></span>")
				.css("padding-left", (cint(dataContext.indent) * 21) + "px")
				.append(link);

			value = span.wrap("<p></p>").parent().html();

		} else {
			value = erpnext.financial_statements.default_formatter(row, cell, value, columnDef, dataContext);
		}

		if (!dataContext.parent_account) {
			value = $(value).css("font-weight", "bold").wrap("<p></p>").parent().html();
		}

		return value;
	},
	"open_general_ledger": function(account) {
		if (!account) return;

		frappe.route_options = {
			"account": account,
			"company": frappe.query_report.filters_by_name.company.get_value()
		};
		frappe.set_route("query-report", "General Ledger");
	}
};
