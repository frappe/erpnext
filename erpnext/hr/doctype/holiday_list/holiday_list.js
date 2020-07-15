// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Holiday List', {
	refresh: function(frm) {
		if (frm.doc.holidays) {
			frm.set_value('total_holidays', frm.doc.holidays.length);
		}
	},
	from_date: function(frm) {
		if (frm.doc.from_date && !frm.doc.to_date) {
			var a_year_from_start = frappe.datetime.add_months(frm.doc.from_date, 12);
			frm.set_value("to_date", frappe.datetime.add_days(a_year_from_start, -1));
		}
	}
});


frappe.tour['Holiday List'] = [
	{
		fieldname: "holiday_list_name",
		title: "Enter Name",
		description: __("Name your Holiday List"),
	},
	{
		fieldname: "from_date",
		title: "From Date",
		description: __("Enter the date from which the Holiday List will be applicable.")
	},
	{
		fieldname: "to_date",
		title: "To Date",
		description: __("Enter the date till which the Holiday List will be applicable.")
	},
	{
		fieldname: "weekly_off",
		title: "Weekly Off",
		description: __("Select day for Weekly Off")
	},
	{
		fieldname: "get_weekly_off_dates",
		title: "Add to holidays",
		description: __("On click, it will add Weekly off for a mentioned period in the Holidays List.")
	},
	{
		fieldname: "holidays",
		title: "Holidays",
		description: __("You can also add different dates in Holiday List")
	},
];
