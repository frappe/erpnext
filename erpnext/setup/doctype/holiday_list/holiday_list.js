// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

function update_total_holidays(frm) {
	let total_holidays = 0;
	for (const holiday of frm.doc.holidays || []) {
		total_holidays += holiday.is_half_day ? 0.5 : 1;
	}
	frm.doc.total_holidays = total_holidays;
	frm.refresh_field("total_holidays");
}

frappe.ui.form.on("Holiday List", {
	refresh: function (frm) {
		update_total_holidays(frm);

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
	// these buttons call a whitelisted doc method that mutates the `holidays`
	// table on the server and syncs the result back, instead of going through
	// the grid APIs — that sync never marks the form dirty on its own, so a
	// Save right after (on an already-saved doc) was a no-op ("No changes to
	// Save") even though rows were visibly added.
	get_weekly_off_dates: function (frm) {
		frm.call("get_weekly_off_dates").then(() => frm.dirty());
	},
	get_local_holidays: function (frm) {
		frm.call("get_local_holidays").then(() => frm.dirty());
	},
	clear_table: function (frm) {
		frm.call("clear_table").then(() => frm.dirty());
	},
});

frappe.ui.form.on("Holiday", {
	holidays_add: function (frm) {
		update_total_holidays(frm);
	},
	holidays_remove: function (frm) {
		update_total_holidays(frm);
	},
	is_half_day: function (frm) {
		update_total_holidays(frm);
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
