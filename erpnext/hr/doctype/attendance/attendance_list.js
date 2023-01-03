frappe.listview_settings["Attendance"] = {
	add_fields: ["status", "attendance_date"],

	get_indicator: function (doc) {
		if (["Present", "Work From Home"].includes(doc.status)) {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if (["Absent", "On Leave"].includes(doc.status)) {
			return [__(doc.status), "red", "status,=," + doc.status];
		} else if (doc.status == "Half Day") {
			return [__(doc.status), "orange", "status,=," + doc.status];
		}
	},

	onload: function (list_view) {
		let me = this;

		list_view.page.add_inner_button(__("Mark Attendance"), function () {
			let first_day_of_month = moment().startOf('month');

			if (moment().toDate().getDate() === 1) {
				first_day_of_month = first_day_of_month.subtract(1, "month");
			}

			let dialog = new frappe.ui.Dialog({
				title: __("Mark Attendance"),
				fields: [
					{
						fieldname: "employee",
						label: __("For Employee"),
						fieldtype: "Link",
						options: "Employee",
						get_query: () => {
							return {
								query: "erpnext.controllers.queries.employee_query",
							};
						},
						reqd: 1,
						onchange: () => me.reset_dialog(dialog),
					},
					{
						fieldtype: "Section Break",
						fieldname: "time_period_section",
						hidden: 1,
					},
					{
						label: __("Start"),
						fieldtype: "Date",
						fieldname: "from_date",
						reqd: 1,
						default: first_day_of_month.toDate(),
						onchange: () => me.get_unmarked_days(dialog),
					},
					{
						fieldtype: "Column Break",
						fieldname: "time_period_column",
					},
					{
						label: __("End"),
						fieldtype: "Date",
						fieldname: "to_date",
						reqd: 1,
						default: moment().subtract(1, 'days').toDate(),
						onchange: () => me.get_unmarked_days(dialog),
					},
					{
						fieldtype: "Section Break",
						fieldname: "days_section",
						hidden: 1,
					},
					{
						label: __("Status"),
						fieldtype: "Select",
						fieldname: "status",
						options: ["Present", "Absent", "Half Day", "Work From Home"],
						reqd: 1,
					},
					{
						label: __("Exclude Holidays"),
						fieldtype: "Check",
						fieldname: "exclude_holidays",
						onchange: () => me.get_unmarked_days(dialog),
					},
					{
						label: __("Unmarked Attendance for days"),
						fieldname: "unmarked_days",
						fieldtype: "MultiCheck",
						options: [],
						columns: 2,
					},
				],
				primary_action(data) {
					if (cur_dialog.no_unmarked_days_left) {
						frappe.msgprint(
							__(
								"Attendance from {0} to {1} has already been marked for the Employee {2}",
								[data.from_date, data.to_date, data.employee]
							)
						);
					} else {
						frappe.confirm(
							__("Mark attendance as {0} for {1} on selected dates?", [
								data.status,
								data.employee,
							]),
							() => {
								frappe.call({
									method: "erpnext.hr.doctype.attendance.attendance.mark_bulk_attendance",
									args: {
										data: data,
									},
									callback: function (r) {
										if (r.message === 1) {
											frappe.show_alert({
												message: __("Attendance Marked"),
												indicator: "blue",
											});
											cur_dialog.hide();
										}
									},
								});
							}
						);
					}
					dialog.hide();
					list_view.refresh();
				},
				primary_action_label: __("Mark Attendance"),
			});
			dialog.show();
		});
	},

	reset_dialog: function (dialog) {
		let fields = dialog.fields_dict;

		dialog.set_df_property(
			"time_period_section",
			"hidden",
			fields.employee.value ? 0 : 1
		);

		dialog.set_df_property("days_section", "hidden", 1);
		dialog.set_df_property("unmarked_days", "options", []);
		dialog.no_unmarked_days_left = false;
		fields.exclude_holidays.value = false;

		fields.to_date.datepicker.update({
			maxDate: moment().subtract(1, 'days').toDate()
		});

		this.get_unmarked_days(dialog)
	},

	get_unmarked_days: function (dialog) {
		let fields = dialog.fields_dict;
		if (fields.employee.value && fields.from_date.value && fields.to_date.value) {
			dialog.set_df_property("days_section", "hidden", 0);
			dialog.set_df_property("status", "hidden", 0);
			dialog.set_df_property("exclude_holidays", "hidden", 0);
			dialog.no_unmarked_days_left = false;

			frappe
				.call({
					method: "erpnext.hr.doctype.attendance.attendance.get_unmarked_days",
					async: false,
					args: {
						employee: fields.employee.value,
						from_date: fields.from_date.value,
						to_date: fields.to_date.value,
						exclude_holidays: fields.exclude_holidays.value,
					},
				})
				.then((r) => {
					var options = [];

					for (var d in r.message) {
						var momentObj = moment(r.message[d], "YYYY-MM-DD");
						var date = momentObj.format("DD-MM-YYYY");
						options.push({
							label: date,
							value: r.message[d],
							checked: 1,
						});
					}

					dialog.set_df_property(
						"unmarked_days",
						"options",
						options.length > 0 ? options : []
					);
					dialog.no_unmarked_days_left = options.length === 0;
				});
		}
	},
};
