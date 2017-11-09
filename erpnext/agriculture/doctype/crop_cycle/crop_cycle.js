// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Crop Cycle', {
	onload: function(frm) {
	},
	onsubmit: (frm) => {
	},
	validate: (frm) => {
		if (frm.doc.__islocal){
			frappe.model.with_doc("Crop", frm.doc.crop, function() {
				let crop = frappe.model.get_doc("Crop", frm.doc.crop);
				frappe.run_serially([
					() => frm.call("create_project", {
						period: crop.period,
						crop_tasks: crop.agriculture_task
					}, (r) => {
						frm.doc.project = r.message;
						frm.refresh_field("project");
						frm.save();
					})
				]);
			});
		}
	}
});