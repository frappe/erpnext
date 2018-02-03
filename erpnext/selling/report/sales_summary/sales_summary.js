// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Summary"] = {
	"filters": [
		//{
		//	"fieldname":"company",
		//	"label": __("Company"),
		//	"fieldtype": "Link",
		//	"options": "Company",
		//	"default": frappe.defaults.get_user_default("Company")
		//},
		{
			"fieldname":"sales_type",
			"label":__("Sales Type"),
			"fieldtype":"Select",
			"options":"" + NEWLINE + "GROSS" + NEWLINE + "CREDIT NOTES"
		}
	],
	onload: function(report) {
		report.page.add_inner_button(__("Sales Summary"), function() {
			var filters = report.get_values();
			//frappe.set_route('query-report', 'Sales Summary', {company: filters.company});
			frappe.set_route('query-report','Sales Summary',{});
		});
	}
	// "formatter": function(row, cell, value, columnDef, dataContext, default_formatter) {
	// 	console.log('row:'+row)
	// 	console.log('cell:'+cell)
	// 	console.log('value:'+value)
	// 	console.log('columnDef:')
	// 	console.log(columnDef)
	// 	console.log('dataContext:'+dataContext)
	// 	console.log('default_formatter:'+default_formatter)
	// 	if(value=='Total'){
	// 		value = "<b>"+value+"</b>"
	// 		// value = value.wrap("<b></b>").parent().html();
	// 	}
	// 	// if (columnDef.df.fieldname=="account") {
	// 	// 	value = dataContext.account_name;

	// 	// 	columnDef.df.link_onclick =
	// 	// 		"erpnext.financial_statements.open_general_ledger(" + JSON.stringify(dataContext) + ")";
	// 	// 	columnDef.df.is_tree = true;
	// 	// }

	// 	// value = default_formatter(row, cell, value, columnDef, dataContext);

	// 	// if (!dataContext.parent_account) {
	// 	// 	var $value = $(value).css("font-weight", "bold");
	// 	// 	if (dataContext.warn_if_negative && dataContext[columnDef.df.fieldname] < 0) {
	// 	// 		$value.addClass("text-danger");
	// 	// 	}

	// 	// 	value = $value.wrap("<p></p>").parent().html();
	// 	// }

	// 	return value;
	// },
}

