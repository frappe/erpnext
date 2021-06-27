// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.query_reports["Monthly Attendance Sheet"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"year",
			"label": __("Year"),
			"fieldtype": "Select",
			"reqd": 1
		},
		{
			"fieldname":"month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": "Jan\nFeb\nMar\nApr\nMay\nJun\nJul\nAug\nSep\nOct\nNov\nDec",
			"default": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
				"Dec"][frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth()],
			"reqd": 1
		},
		{
			"fieldname":"employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee"
		}
	],

	onload: function() {
		return  frappe.call({
			method: "erpnext.hr.report.monthly_attendance_sheet.monthly_attendance_sheet.get_attendance_years",
			callback: function(r) {
				var year_filter = frappe.query_report.get_filter('year');
				year_filter.df.options = r.message;
				year_filter.df.default = r.message.split("\n")[0];
				year_filter.refresh();
				year_filter.set_input(year_filter.df.default);
			}
		});
	},

	formatter: function(value, row, column, data, default_formatter) {
		var style = {};
		var link;

		if (column.day) {
			var attendance_fieldname = "attendance_day_" + column.day;
			var status_fieldname = "status_day_" + column.day;
			var status = data[status_fieldname]

			if (data[attendance_fieldname]) {
				link = "desk#Form/Attendance/" + encodeURIComponent(data[attendance_fieldname]);
			}

			if (status == "Holiday") {
				style['font-weight'] = 'bold';
			}

			if (status == "Present") {
				style['color'] = 'green';
			}
			if (status == "Absent") {
				style['color'] = 'red';
			}
			if (status == "Half Day") {
				style['color'] = 'orange';
			}
			if (status == "On Leave") {
				style['color'] = 'blue';
			}
		}

		return default_formatter(value, row, column, data, {css: style, link_href: link, link_target: "_blank"});
	},
}
