// Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const get_currencies = () => {
	// frappe.db.get_list returns a Promise
	return frappe.db.get_list('GL Entry',
		{
			distinct: true,
			fields:['account_currency'],
			as_list: true
		}
	);
}

const flatten = (array) => {
	return [].concat.apply([], array);
}

get_currencies().then(currency_list => flatten(currency_list)).then(currency_list => {
	frappe.require("assets/erpnext/js/financial_statements.js", function() {
		frappe.query_reports["Cash Flow"] = $.extend({},
			erpnext.financial_statements);

		frappe.query_reports["Cash Flow"]["filters"].push({
			"fieldname": "accumulated_values",
			"label": __("Accumulated Values"),
			"fieldtype": "Check"
		},
		{
			"fieldname": "presentation_currency",
			"label": __("Currency"),
			"fieldtype": "Select",
			"options": currency_list
		});
	});
});