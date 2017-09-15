// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Subscription', {
	setup: function(frm) {
		if(frm.doc.__islocal) {
			var last_route = frappe.route_history.slice(-2, -1)[0];
			if(frappe.dynamic_link && frappe.dynamic_link.doc
					&& frappe.dynamic_link.doc.name==last_route[2]) {
				frm.set_value('reference_doctype', last_route[1]);
				frm.set_value('reference_document', last_route[2]);
			}
		}

		frm.fields_dict['reference_document'].get_query = function() {
			return {
				filters: {
					"docstatus": 1
				}
			};
		};

		frm.fields_dict['print_format'].get_query = function() {
			return {
				filters: {
					"doc_type": frm.doc.reference_doctype
				}
			};
		};
	},

	refresh: function(frm) {
		if(frm.doc.docstatus == 1) {
			let label = __('View {0}', [frm.doc.reference_doctype]);
			frm.add_custom_button(__(label),
				function() {
					frappe.route_options = {
						"subscription": frm.doc.name,
					};
					frappe.set_route("List", frm.doc.reference_doctype);
				}
			);

			if(frm.doc.status != 'Stopped') {
				frm.add_custom_button(__("Stop"),
					function() {
						frm.events.stop_resume_subscription(frm, "Stopped");
					}
				);
			}

			if(frm.doc.status == 'Stopped') {
				frm.add_custom_button(__("Resume"),
					function() {
						frm.events.stop_resume_subscription(frm, "Resumed");
					}
				);
			}
		}
	},

	stop_resume_subscription: function(frm, status) {
		frappe.call({
			method: "erpnext.accounts.doctype.subscription.subscription.stop_resume_subscription",
			args: {
				subscription: frm.doc.name,
				status: status
			},
			callback: function(r) {
				if(r.message) {
					frm.set_value("status", r.message);
					frm.reload_doc();
				}
			}
		});
	}
});