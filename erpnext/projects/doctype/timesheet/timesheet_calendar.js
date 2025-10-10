frappe.views.calendar["Timesheet"] = {
	field_map: {
		start: "start_date",
		end: "end_date",
		name: "parent",
		id: "name",
		allDay: "allDay",
		child_name: "name",
		title: "title",
	},
	style_map: {
		0: "info",
		1: "standard",
		2: "danger",
	},
	gantt: true,
	filters: [
		{
			fieldtype: "Link",
			fieldname: "project",
			options: "Project",
			label: __("Project"),
		},
		{
			fieldtype: "Link",
			fieldname: "employee",
			options: "Employee",
			label: __("Employee"),
		},
	],
	get_events_method: "erpnext.projects.doctype.timesheet.timesheet.get_events",
	// Small helpers for leap year calculations (Gregorian rules). These are
	// attached here so frontend code that renders timesheets can quickly
	// reference whether a year is a leap year and how many days it has.
	isLeapYear: function (year) {
		// Coerce to Number and ensure integerness
		year = Number(year);
		if (!Number.isInteger(year)) {
			throw new Error("year must be an integer");
		}
		if (year % 4 !== 0) return false;
		if (year % 100 !== 0) return true;
		return year % 400 === 0;
	},

	daysInYear: function (year) {
		return this.isLeapYear(year) ? 366 : 365;
	},

	// Example usage:
	// const isLeap = frappe.views.calendar['Timesheet'].isLeapYear(2024);
	// const days = frappe.views.calendar['Timesheet'].daysInYear(2024);
};
