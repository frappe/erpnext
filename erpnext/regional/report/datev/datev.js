// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Fichier des Ecritures Comptables [FEC]"] = {
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
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.defaults.get_user_default("fiscal_year"),
			"reqd": 1
		}
	],
	onload: function (query_report) {
		query_report.export_report = function () {
			downloadify(query_report);
		};
	}
};

let downloadify = function (query_report) {
	const fiscal_year = query_report.get_values().fiscal_year;
	const company = query_report.get_values().company;
	const title = company + "_" + fiscal_year;
	const column_row = query_report.columns.map(col => col.label);
	const column_data = query_report.get_data_for_csv(false);
	const result = [column_row].concat(column_data);

	frappe.call({
		method: 'frappe.utils.csvutils.send_csv_to_client',
		args: {
			data: result,
			filename: title
		}
	});
};
