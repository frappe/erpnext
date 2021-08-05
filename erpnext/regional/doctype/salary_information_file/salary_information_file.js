// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Salary Information File', {
	refresh: function(frm) {
		let error_log_wrapper = frm.get_field("error_log_html").$wrapper ;
		error_log_wrapper.empty();
		if (frm.doc.missing_fields) {
			let missing_fields_data = JSON.parse(frm.doc.missing_fields);

			let error_log_html = frappe.render_template("salary_information_file_error_log", {
				data: missing_fields_data
			});

			error_log_wrapper.append(error_log_html);
			console.log(missing_fields_data);
		}
	}
});
