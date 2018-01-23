// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

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
		frappe.query_reports["Balance Sheet"] = erpnext.financial_statements;

		frappe.query_reports["Balance Sheet"]["filters"].push({
			"fieldname": "accumulated_values",
			"label": __("Accumulated Values"),
			"fieldtype": "Check",
			"default": 1
		},
		{
			"fieldname": "presentation_currency",
			"label": __("Currency"),
			"fieldtype": "Select",
			"options": currency_list
		});
	});
});
