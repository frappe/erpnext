// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Reserved Stock"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			get_query: () => ({
				filters: {
					is_stock_item: 1,
				},
			}),
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: () => ({
				filters: {
					is_group: 0,
					company: frappe.query_report.get_filter_value("company"),
				},
			}),
		},
		{
			fieldname: "stock_reservation_entry",
			label: __("Stock Reservation Entry"),
			fieldtype: "Link",
			options: "Stock Reservation Entry",
			get_query: () => ({
				filters: {
					docstatus: 1,
					company: frappe.query_report.get_filter_value("company"),
				},
			}),
		},
		{
			fieldname: "voucher_type",
			label: __("Voucher Type"),
			fieldtype: "Link",
			options: "DocType",
			default: "Sales Order",
			get_query: () => ({
				filters: {
					name: ["in", ["Sales Order", "Work Order", "Production Plan"]],
				},
			}),
		},
		{
			fieldname: "voucher_no",
			label: __("Voucher No"),
			fieldtype: "Dynamic Link",
			options: "voucher_type",
			get_query: () => ({
				filters: {
					docstatus: 1,
					company: frappe.query_report.get_filter_value("company"),
				},
			}),
			get_options: function () {
				return frappe.query_report.get_filter_value("voucher_type");
			},
		},
		{
			fieldname: "from_voucher_type",
			label: __("From Voucher Type"),
			fieldtype: "Link",
			options: "DocType",
			get_query: () => ({
				filters: {
					name: ["in", ["Pick List", "Purchase Receipt"]],
				},
			}),
		},
		{
			fieldname: "from_voucher_no",
			label: __("From Voucher No"),
			fieldtype: "Dynamic Link",
			options: "from_voucher_type",
			get_query: () => ({
				filters: {
					docstatus: 1,
					company: frappe.query_report.get_filter_value("company"),
				},
			}),
			get_options: function () {
				return frappe.query_report.get_filter_value("from_voucher_type");
			},
		},
		{
			fieldname: "reservation_based_on",
			label: __("Reservation Based On"),
			fieldtype: "Select",
			options: ["", "Qty", "Serial and Batch"],
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "Partially Reserved", "Reserved", "Partially Delivered", "Delivered"],
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "Project",
			get_query: () => ({
				filters: {
					company: frappe.query_report.get_filter_value("company"),
				},
			}),
		},
	],
	formatter: (value, row, column, data, default_formatter) => {
		value = default_formatter(value, row, column, data);

		if (data) {
			if (column.fieldname == "status") {
				switch (data.status) {
					case "Partially Reserved":
						value = "<span style='color:orange'>" + value + "</span>";
						break;
					case "Reserved":
						value = "<span style='color:blue'>" + value + "</span>";
						break;
					case "Partially Delivered":
						value = "<span style='color:purple'>" + value + "</span>";
						break;
					case "Delivered":
						value = "<span style='color:green'>" + value + "</span>";
						break;
				}
			} else if (column.fieldname == "delivered_qty") {
				if (data.delivered_qty > 0) {
					if (data.reserved_qty > data.delivered_qty) {
						value = "<span style='color:blue'>" + value + "</span>";
					} else {
						value = "<span style='color:green'>" + value + "</span>";
					}
				} else {
					value = "<span style='color:red'>" + value + "</span>";
				}
			}
		}

		return value;
	},
};
