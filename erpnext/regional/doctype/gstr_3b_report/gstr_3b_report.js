// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('GSTR 3B Report', {
	refresh : function(frm){
		if(!frm.is_new()) {
			frm.add_custom_button(__('Download JSON'), function() {
				var w = window.open(
					frappe.urllib.get_full_url(
						"/api/method/erpnext.regional.doctype.gstr_3b_report.gstr_3b_report.make_json?"
						+"name="+encodeURIComponent(frm.doc.name)));

				if(!w) {
					frappe.msgprint(__("Please enable pop-ups")); return;
				}
			});
			frm.add_custom_button(__('View Form'), function() {
				frappe.call({
					"method" : "erpnext.regional.gstr_3b_report.gstr_3b_report.view_report",
					"args" : {
						name : frm.doc.name,
					},
					"callback" : function(r){

						let data = r.message

						frappe.ui.get_print_settings(false, print_settings => {

							frappe.render_grid({
								template: 'gstr_3b_report',
								title: __(this.doctype),
								print_settings: print_settings,
								data: data,
								columns:[]
							});
						});
					}
				});
			});
		}
	},

	setup: function(frm){
		frm.set_query('company_address', function(doc) {
			if(!doc.company) {
				frappe.throw(__('Please set Company'));
			}

			return {
				query: 'frappe.contacts.doctype.address.address.address_query',
				filters: {
					link_doctype: 'Company',
					link_name: doc.company
				}
			};
		});
	},
});
