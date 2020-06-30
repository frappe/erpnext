// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt

frappe.listview_settings['Job Applicant'] = {
	add_fields: ["company", "designation", "job_applicant", "status"],
	get_indicator: function (doc) {
		if (doc.status == "Accepted") {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if (["Open", "Replied"].includes(doc.status)) {
			return [__(doc.status), "orange", "status,=," + doc.status];
		} else if (["Hold", "Rejected"].includes(doc.status)) {
			return [__(doc.status), "red", "status,=," + doc.status];
		}
	}
};
