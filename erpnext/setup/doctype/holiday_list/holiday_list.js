// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Holiday List", {
	refresh: function (frm) {
		if (frm.doc.holidays) {
			frm.set_value("total_holidays", frm.doc.holidays.length);
		}

		if (!frm.doc.__islocal) {
			frm.add_custom_button(__("Bulk Holiday Assignment"), () => {
				frm.events.show_bulk_holiday_assignment_dialog(frm);
			});
		}

		frm.call("get_supported_countries").then((r) => {
			frm.subdivisions_by_country = r.message.subdivisions_by_country;
			frm.fields_dict.country.set_data(
				r.message.countries.sort((a, b) => a.label.localeCompare(b.label))
			);

			if (frm.doc.country) {
				frm.trigger("set_subdivisions");
			}
		});
	},
	from_date: function (frm) {
		if (frm.doc.from_date && !frm.doc.to_date) {
			var a_year_from_start = frappe.datetime.add_months(frm.doc.from_date, 12);
			frm.set_value("to_date", frappe.datetime.add_days(a_year_from_start, -1));
		}
	},
	country: function (frm) {
		frm.set_value("subdivision", "");

		if (frm.doc.country) {
			frm.trigger("set_subdivisions");
		}
	},
	set_subdivisions: function (frm) {
		const subdivisions = [...frm.subdivisions_by_country[frm.doc.country]];
		if (subdivisions && subdivisions.length > 0) {
			frm.fields_dict.subdivision.set_data(subdivisions);
			frm.set_df_property("subdivision", "hidden", 0);
		} else {
			frm.fields_dict.subdivision.set_data([]);
			frm.set_df_property("subdivision", "hidden", 1);
		}
	},

	show_bulk_holiday_assignment_dialog: function (frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Bulk Holiday Assignment"),
			fields: [
				{
					fieldname: "holiday_list",
					fieldtype: "Data",
					label: __("Holiday List"),
					default: frm.doc.name,
					read_only: 1,
				},
				{
					fieldname: "from_date",
					fieldtype: "Date",
					label: __("Assignment Starts From"),
					default: frm.doc.from_date,
					reqd: 1,
					description: __("Must be within the holiday list period"),
				},
				{
					fieldname: "col_break_top",
					fieldtype: "Column Break",
				},
				{
					fieldname: "company",
					fieldtype: "Link",
					label: __("Company"),
					options: "Company",
					reqd: 1,
					default: frappe.defaults.get_default("company"),
				},
				{
					fieldname: "sec_from_date",
					fieldtype: "Section Break",
				},
				{
					fieldname: "quick_filters_section",
					fieldtype: "Section Break",
					label: __("Quick Filters"),
					collapsible: 0,
				},
				{
					fieldname: "branch",
					fieldtype: "Link",
					label: __("Branch"),
					options: "Branch",
					placeholder: __("Branch"),
				},
				{
					fieldname: "department",
					fieldtype: "Link",
					label: __("Department"),
					options: "Department",
					placeholder: __("Department"),
					get_query: () => ({ filters: { company: dialog.get_value("company") } }),
				},
				{
					fieldname: "col_break_1",
					fieldtype: "Column Break",
				},
				{
					fieldname: "employment_type",
					fieldtype: "Link",
					label: __("Employment Type"),
					options: "Employment Type",
					placeholder: __("Employment Type"),
				},
				{
					fieldname: "designation",
					fieldtype: "Link",
					label: __("Designation"),
					options: "Designation",
					placeholder: __("Designation"),
				},
				{
					fieldname: "employees_section",
					fieldtype: "Section Break",
					label: __("Employees"),
					hidden: 1,
				},
				{
					fieldname: "employees_multicheck",
					fieldtype: "MultiCheck",
					label: "",
					select_all: true,
					columns: 2,
					hidden: 1,
					get_data: () => [],
				},
			],
		});

		const filter_fields = ["branch", "department", "employment_type", "designation"];

		const fetch_and_render = frappe.utils.debounce(() => {
			const company = dialog.get_value("company");
			if (!company) return;
			const values = {
				holiday_list: frm.doc.name,
				from_date: dialog.get_value("from_date"),
				company,
				branch: dialog.get_value("branch") || "",
				department: dialog.get_value("department") || "",
				employment_type: dialog.get_value("employment_type") || "",
				designation: dialog.get_value("designation") || "",
			};
			frm.events.fetch_employees_into_dialog(frm, dialog, values);
		}, 300);

		dialog.set_primary_action(__("Assign Holiday List"), () => {
			const selected = dialog.fields_dict.employees_multicheck.get_checked_options();
			if (!selected.length) {
				frappe.throw({
					message: __("Please select at least one employee."),
					title: __("No Employees Selected"),
				});
				return;
			}
			const filters = {
				holiday_list: frm.doc.name,
				from_date: dialog.get_value("from_date"),
				company: dialog.get_value("company"),
			};
			const all_employees = dialog._loaded_employees || [];
			const selected_employees = all_employees.filter((e) => selected.includes(e.employee));
			frappe.call({
				method: "hrms.hr.doctype.holiday_list_assignment.holiday_list_assignment.bulk_assign_holiday_list",
				args: { filters, employees: selected_employees },
				freeze: true,
				freeze_message: __("Assigning Holiday List..."),
				callback(r) {
					if (r.exc) return;
					dialog.hide();
					if (r.message) {
						frm.events.show_assignment_summary(frm, r.message, selected_employees.length);
					} else {
						frm.events.listen_for_bulk_assignment_completion(frm, selected_employees.length);
					}
				},
			});
		});

		// Wire onchange before show so Frappe picks them up on render
		dialog.fields_dict.company.df.onchange = () => {
			filter_fields.forEach((f) => dialog.set_value(f, ""));
			dialog._employees_section_visible = false;
			dialog.set_df_property("employees_section", "hidden", 1);
			dialog.set_df_property("employees_multicheck", "hidden", 1);
			dialog.get_primary_btn().hide();
			fetch_and_render();
		};
		filter_fields.forEach((f) => {
			dialog.fields_dict[f].df.onchange = () => {
				if (dialog.get_value("company")) fetch_and_render();
			};
		});

		dialog._employees_section_visible = false;
		dialog.show();
		dialog.fields_dict.employees_multicheck.$wrapper.css({ "max-height": "300px", "overflow-y": "auto" });
		filter_fields.forEach((f) => {
			dialog.fields_dict[f].$wrapper.find(".control-label").hide();
		});
		dialog.set_df_property("employees_section", "hidden", 1);
		dialog.set_df_property("employees_multicheck", "hidden", 1);
		dialog.get_primary_btn().hide();

		if (frappe.defaults.get_default("company")) {
			fetch_and_render();
		}
	},

	fetch_employees_into_dialog: function (frm, dialog, filters) {
		const is_first_load = !dialog._employees_section_visible;

		frappe.call({
			method: "hrms.hr.doctype.holiday_list_assignment.holiday_list_assignment.get_employees_for_bulk_assignment",
			args: { filters },
			freeze: is_first_load,
			freeze_message: __("Fetching Employees..."),
			callback(r) {
				if (r.exc) return;

				const employees = r.message || [];
				dialog._loaded_employees = employees;

				const multicheck = dialog.fields_dict.employees_multicheck;
				multicheck.df.get_data = () =>
					employees.map((e) => ({
						label: `${e.employee}: ${e.employee_name}`,
						value: e.employee,
						checked: 1,
					}));

				if (!dialog._employees_section_visible) {
					dialog.set_df_property("employees_section", "hidden", 0);
					dialog.set_df_property("employees_multicheck", "hidden", 0);
					dialog._employees_section_visible = true;
					dialog.get_primary_btn().show();
				}

				const count_label = __("Employees ({0} found)", [employees.length]);
				const section = dialog.fields_dict["employees_section"];
				if (section) section.set_label(count_label);
				multicheck.set_options();

				if (!employees.length) {
					frappe.show_alert({
						message: __("No employees found for the selected filters."),
						indicator: "orange",
					});
				}
			},
		});
	},

	listen_for_bulk_assignment_completion: function (frm, total_selected) {
		frappe.realtime.on("completed_bulk_holiday_list_assignment", (data) => {
			frappe.realtime.off("completed_bulk_holiday_list_assignment");
			frm.events.show_assignment_summary(frm, data, total_selected);
		});
	},

	show_assignment_summary: function (frm, data, total_selected) {
		const success_count = (data.success || []).length;
		const failure_count = (data.failure || []).length;

		if (failure_count > 0) {
			frappe.show_alert({
				message: __("{0} assigned, {1} failed", [success_count, failure_count]),
				indicator: "orange",
			});
		} else {
			frappe.show_alert({
				message: __("{0} employee(s) assigned successfully", [success_count]),
				indicator: "green",
			});
		}
	},
});

frappe.tour["Holiday List"] = [
	{
		fieldname: "holiday_list_name",
		title: "Holiday List Name",
		description: __("Enter a name for this Holiday List."),
	},
	{
		fieldname: "from_date",
		title: "From Date",
		description: __("Based on your HR Policy, select your leave allocation period's start date"),
	},
	{
		fieldname: "to_date",
		title: "To Date",
		description: __("Based on your HR Policy, select your leave allocation period's end date"),
	},
	{
		fieldname: "weekly_off",
		title: "Weekly Off",
		description: __("Select your weekly off day"),
	},
	{
		fieldname: "get_weekly_off_dates",
		title: "Add Holidays",
		description: __(
			"Click on Add to Holidays. This will populate the holidays table with all the dates that fall on the selected weekly off. Repeat the process for populating the dates for all your weekly holidays"
		),
	},
	{
		fieldname: "holidays",
		title: "Holidays",
		description: __(
			"Here, your weekly offs are pre-populated based on the previous selections. You can add more rows to also add public and national holidays individually."
		),
	},
];
