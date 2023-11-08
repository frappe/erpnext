// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Holiday List", {
	refresh: function(frm) {
		if (frm.doc.holidays) {
			frm.set_value("total_holidays", frm.doc.holidays.length);
		}
	},
	from_date: function(frm) {
		if (frm.doc.from_date && !frm.doc.to_date) {
			var a_year_from_start = frappe.datetime.add_months(frm.doc.from_date, 12);
			frm.set_value("to_date", frappe.datetime.add_days(a_year_from_start, -1));
		}
	}
});
frappe.ui.form.on("Holiday List", {
    refresh: function(frm) {
        frm.fields_dict.holidays.grid.get_field("holiday_date").get_query = function(doc, cdt, cdn) {
            return {
                filters: [
                    ["Holiday", "parent", "=", frm.docname]
                ]
            };
        };
    }
});

frappe.ui.form.on('Holiday', {
    holiday_date: function(frm, cdt, cdn) {
        var child = locals[cdt][cdn];
        var selectedDate = child.holiday_date;
        
        // Parse the date string to a JavaScript Date object
        var dateObj = new Date(selectedDate);
        
        // Get the day of the week (0 = Sunday, 1 = Monday, ..., 6 = Saturday)
        var dayOfWeekIndex = dateObj.getDay();
        
        // Define an array of day names
        var dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        
        // Get the day name based on the index
        var dayOfWeek = dayNames[dayOfWeekIndex];
        
        // Set the day of the week in the description field
        frappe.model.set_value(cdt, cdn, 'description', dayOfWeek);
    }
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
		description: __("Click on Add to Holidays. This will populate the holidays table with all the dates that fall on the selected weekly off. Repeat the process for populating the dates for all your weekly holidays"),
	},
	{
		fieldname: "holidays",
		title: "Holidays",
		description: __("Here, your weekly offs are pre-populated based on the previous selections. You can add more rows to also add public and national holidays individually.")
	},
];
