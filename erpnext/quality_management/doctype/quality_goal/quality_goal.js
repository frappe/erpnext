// Copyright (c) 2018, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Quality Goal', {
	onload: function(frm) {
		frm.doc.created_by = frappe.session.user;
	},
	refresh: function(frm) {
		if(!frm.doc.__islocal) {
			frm.add_custom_button(__("Review"), () => {
				const review = new frappe.ui.Dialog({
					title: __('Review'),
					fields: [
						{
							fieldtype: "Text",
							fieldname: "review",
							label: __("Review"),
							reqd: 1
						},
					],
					primary_action_label: __('Review'),
					primary_action: (values) => {
						review.disable_primary_action();
						review.hide();

						frappe.call({
							method: "erpnext.quality_management.doctype.quality_review.quality_review.create_review",
							args: {
								reference_doctype: frm.doc.doctype,
								reference_name: frm.doc.name,
								review: values.review
							}
						}).then(() =>{
							review.clear();
							review.enable_primary_action();
						});
					}
				});
				review.show();
			});
		}
	}
});