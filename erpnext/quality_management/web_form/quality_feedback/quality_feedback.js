frappe.ready(function() {
	// bind events here
	setTimeout(() => {
		var form = frappe.web_form.field_group.fields_dict;
		form.email.set_input(frappe.session.user_email);
	}, 1000);
});