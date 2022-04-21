// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["E-Invoice Summary"] = {
	"filters": [
		{
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"fieldname": "company",
			"label": __("Company"),
			"default": frappe.defaults.get_user_default("Company"),
		},
		{
			"fieldtype": "Link",
			"options": "Customer",
			"fieldname": "customer",
			"label": __("Customer")
		},
		{
			"fieldtype": "Date",
			"reqd": 1,
			"fieldname": "from_date",
			"label": __("From Date"),
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			"fieldtype": "Date",
			"reqd": 1,
			"fieldname": "to_date",
			"label": __("To Date"),
			"default": frappe.datetime.get_today(),
		},
		{
			"fieldtype": "Select",
			"fieldname": "status",
			"label": __("Status"),
			"options": "\nPending\nGenerated\nCancelled\nFailed"
		}
	],

	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname == "einvoice_status" && value) {
			if (value == 'Pending') value = `<span class="bold" style="color: var(--text-on-orange)">${value}</span>`;
			else if (value == 'Generated') value = `<span class="bold" style="color: var(--text-on-green)">${value}</span>`;
			else if (value == 'Cancelled') value = `<span class="bold" style="color: var(--text-on-red)">${value}</span>`;
			else if (value == 'Failed') value = `<span class="bold"  style="color: var(--text-on-red)">${value}</span>`;
		}

		return value;
	}
};
