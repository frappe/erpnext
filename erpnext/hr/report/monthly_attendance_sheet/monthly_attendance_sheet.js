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

				var previous_month = frappe.datetime.str_to_obj(frappe.datetime.add_months(frappe.datetime.get_today(), -1));
				year_filter.df.default = previous_month.getFullYear();

				year_filter.refresh();
				year_filter.set_input(year_filter.df.default);

				frappe.query_report.set_filter_value('month', moment(previous_month).format("MMM"));
			}
		});
	},

	formatter: function(value, row, column, data, default_formatter) {
		var style = {};
		var link;

		if (['total_present', 'total_absent', 'total_half_day', 'total_leave', 'total_late_entry', 'total_early_exit'].includes(column.fieldname) && data.employee) {
			link = `/app/query-report/Employee Checkin Sheet?employee=${encodeURIComponent(data.employee)}&from_date=${data.from_date}&to_date=${data.to_date}`;
		}

		if (column.fieldname == 'total_present' && flt(value)) {
			style['color'] = 'green';
		}
		if (['total_absent', 'total_late_deduction', 'total_deduction'].includes(column.fieldname) && flt(value)) {
			style['color'] = 'red';
		}
		if (column.fieldname == 'total_half_day' && flt(value)) {
			style['color'] = 'orange';
		}
		if ((column.fieldname == 'total_leave' || column.leave_type) && flt(value)) {
			if (column.is_lwp) {
				style['color'] = 'red';
			} else {
				style['color'] = 'blue';
			}
		}
		if (column.fieldname == 'total_late_entry' && flt(value)) {
			style['color'] = 'orange';
		}
		if (column.fieldname == 'total_early_exit' && flt(value)) {
			style['color'] = 'orange';
		}

		if (column.day) {
			var attendance_fieldname = "attendance_day_" + column.day;
			var status_fieldname = "status_day_" + column.day;
			var status = data[status_fieldname]

			if (data[attendance_fieldname]) {
				link = "/app/attendance/" + encodeURIComponent(data[attendance_fieldname]);
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
