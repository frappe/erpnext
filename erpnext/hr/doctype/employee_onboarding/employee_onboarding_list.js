frappe.listview_settings['Employee Onboarding'] = {
	add_fields: ["boarding_status", "employee_name", "date_of_joining", "department"],
	filters:[["boarding_status","=", "Pending"]],
	get_indicator: function(doc) {
		return [__(doc.boarding_status), frappe.utils.guess_colour(doc.boarding_status), "status,=," + doc.boarding_status];
	}
};
