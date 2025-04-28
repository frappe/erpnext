// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Purchase Order Analysis"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			width: "80",
			options: "Company",
			reqd: 1,
<<<<<<< HEAD
			default: frappe.defaults.get_user_default("Company"),
=======
			default: frappe.defaults.get_default("company"),
>>>>>>> 7c4cf3e834 (Favicon.svg)
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			width: "80",
			reqd: 1,
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
<<<<<<< HEAD
			on_change: (report) => {
				report.set_filter_value("name", []);
				report.refresh();
			},
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			width: "80",
			reqd: 1,
			default: frappe.datetime.get_today(),
<<<<<<< HEAD
			on_change: (report) => {
				report.set_filter_value("name", []);
				report.refresh();
			},
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			width: "80",
			options: "Project",
		},
		{
			fieldname: "name",
			label: __("Purchase Order"),
<<<<<<< HEAD
			fieldtype: "MultiSelectList",
			width: "80",
			options: "Purchase Order",
			get_data: function (txt) {
				let filters = { docstatus: 1 };

				const from_date = frappe.query_report.get_filter_value("from_date");
				const to_date = frappe.query_report.get_filter_value("to_date");
				if (from_date && to_date) filters["transaction_date"] = ["between", [from_date, to_date]];

				return frappe.db.get_link_options("Purchase Order", txt, filters);
=======
			fieldtype: "Link",
			width: "80",
			options: "Purchase Order",
			get_query: () => {
				return {
					filters: { docstatus: 1 },
				};
>>>>>>> 7c4cf3e834 (Favicon.svg)
			},
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "MultiSelectList",
			width: "80",
<<<<<<< HEAD
			options: ["To Pay", "To Bill", "To Receive", "To Receive and Bill", "Completed", "Closed"],
			get_data: function (txt) {
				let status = [
					"To Pay",
					"To Bill",
					"To Receive",
					"To Receive and Bill",
					"Completed",
					"Closed",
				];
=======
			get_data: function (txt) {
				let status = ["To Pay", "To Bill", "To Receive", "To Receive and Bill", "Completed"];
>>>>>>> 7c4cf3e834 (Favicon.svg)
				let options = [];
				for (let option of status) {
					options.push({
						value: option,
						label: __(option),
						description: "",
					});
				}
				return options;
			},
		},
		{
			fieldname: "group_by_po",
			label: __("Group by Purchase Order"),
			fieldtype: "Check",
			default: 0,
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		let format_fields = ["received_qty", "billed_amount"];

		if (in_list(format_fields, column.fieldname) && data && data[column.fieldname] > 0) {
			value = "<span style='color:green'>" + value + "</span>";
		}
		return value;
	},
};
