$(document).ready(function() {
	var redirect_flow_id = "{{ redirect_flow_id }}";
	var doctype = "{{ reference_doctype }}";
	var docname = "{{ reference_docname }}";

	frappe.call({
		method: "erpnext.templates.pages.integrations.gocardless_confirmation.confirm_payment",
		freeze: true,
		headers: {
			"X-Requested-With": "XMLHttpRequest"
		},
		args: {
			"redirect_flow_id": redirect_flow_id,
			"reference_doctype": doctype,
			"reference_docname": docname
		},
		callback: function(r) {
			if (r.message) {
				window.location.href = r.message.redirect_to;
			}
		}
	});

});
