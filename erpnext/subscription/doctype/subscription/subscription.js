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
	}
});
