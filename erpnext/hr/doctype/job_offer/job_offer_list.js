// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt

frappe.listview_settings['Job Offer'] = {
	add_fields: ["company", "designation", "job_applicant", "status"],
	get_indicator: function (doc) {
		if (doc.status == "Accepted") {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if (doc.status == "Awaiting Response") {
			return [__(doc.status), "orange", "status,=," + doc.status];
		} else if (doc.status == "Rejected") {
			return [__(doc.status), "red", "status,=," + doc.status];
		}
	}
};
