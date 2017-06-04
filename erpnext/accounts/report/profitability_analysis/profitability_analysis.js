// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.require("assets/erpnext/js/financial_statements.js", function() {
	frappe.query_reports["Profitability Analysis"] = {
		"filters": [
			{
				"fieldname": "company",
				"label": __("Company"),
				"fieldtype": "Link",
				"options": "Company",
				"default": frappe.defaults.get_user_default("Company"),
				"reqd": 1
			},
			{
				"fieldname": "based_on",
				"label": __("Based On"),
				"fieldtype": "Select",
				"options": "Cost Center\nProject",
				"default": "Cost Center",
				"reqd": 1
			},
			{
				"fieldname": "fiscal_year",
				"label": __("Fiscal Year"),
				"fieldtype": "Link",
				"options": "Fiscal Year",
				"default": frappe.defaults.get_user_default("fiscal_year"),
				"reqd": 1,
				"on_change": function(query_report) {
					var fiscal_year = query_report.get_values().fiscal_year;
					if (!fiscal_year) {
						return;
					}
					frappe.model.with_doc("Fiscal Year", fiscal_year, function(r) {
						var fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
						frappe.query_report_filters_by_name.from_date.set_input(fy.year_start_date);
						frappe.query_report_filters_by_name.to_date.set_input(fy.year_end_date);
						query_report.trigger_refresh();
					});
				}
			},
			{
				"fieldname": "from_date",
				"label": __("From Date"),
				"fieldtype": "Date",
				"default": frappe.defaults.get_user_default("year_start_date"),
			},
			{
				"fieldname": "to_date",
				"label": __("To Date"),
				"fieldtype": "Date",
				"default": frappe.defaults.get_user_default("year_end_date"),
			},
			{
				"fieldname": "show_zero_values",
				"label": __("Show zero values"),
				"fieldtype": "Check"
			}
		],
		"formatter": function(row, cell, value, columnDef, dataContext, default_formatter) {
			if (columnDef.df.fieldname=="account") {
				value = dataContext.account_name;

				columnDef.df.link_onclick =
					"frappe.query_reports['Profitability Analysis'].open_profit_and_loss_statement(" + JSON.stringify(dataContext) + ")";
				columnDef.df.is_tree = true;
			}

			value = default_formatter(row, cell, value, columnDef, dataContext);

			if (!dataContext.parent_account && dataContext.based_on != 'project') {
				var $value = $(value).css("font-weight", "bold");
				if (dataContext.warn_if_negative && dataContext[columnDef.df.fieldname] < 0) {
					$value.addClass("text-danger");
				}

				value = $value.wrap("<p></p>").parent().html();
			}

			return value;
		},
		"open_profit_and_loss_statement": function(data) {
			if (!data.account) return;

			frappe.route_options = {
				"company": frappe.query_report_filters_by_name.company.get_value(),
				"from_fiscal_year": data.fiscal_year,
				"to_fiscal_year": data.fiscal_year
			};

			if(data.based_on == 'cost_center'){
				frappe.route_options["cost_center"] = data.account
			} else {
				frappe.route_options["project"] = data.account
			}

			frappe.set_route("query-report", "Profit and Loss Statement");
		},
		"tree": true,
		"name_field": "account",
		"parent_field": "parent_account",
		"initial_depth": 3
	}
});

