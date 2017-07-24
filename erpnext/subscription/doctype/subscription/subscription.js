// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Subscription', {
	setup: function(frm) {
		frm.fields_dict['base_docname'].get_query = function() {
			return {
				filters: {
					"docstatus": 1
				}
			}
		}

		frm.fields_dict['print_format'].get_query = function() {
			return {
				filters: {
					"doc_type": frm.doc.base_doctype
				}
			}
		}
	},

	refresh: function(frm) {
		if(frm.doc.docstatus == 1) {
			label = 'View ' + frm.doc.base_doctype
			frm.add_custom_button(__(label),
				function() {
					frm.trigger("view_subscription_document")
			})
		}
	},

	view_subscription_document: function(frm) {
		frappe.route_options = {
			"subscription": frm.doc.name,
		};
		frappe.set_route("List", frm.doc.base_doctype);
	}
});
