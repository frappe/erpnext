// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Crop Cycle', {
	refresh: function(frm) {
	},
	crop: function(frm) {
		// frappe.call({
		// 	method: 'erpnext.agriculture.doctype.crop_cycle.crop_cycle.create_site'
		// });
		frappe.model.with_doc("Crop", frm.doc.crop, function() {
			let tabletransfer = frappe.model.get_doc("Crop", frm.doc.crop);
			$.each(tabletransfer.agriculture_task, function(index, row){
				let d = frm.add_child("agriculture_task");
				d.title = row.title;
				d.date = row.date;
				d.holiday_management = row.holiday_management;
				frm.refresh_field("agriculture_task");
			});
		});
	}
});
