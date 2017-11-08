// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Crop Cycle', {
	onload: function(frm) {
	},
	validate: (frm) => {
		if (frm.doc.__islocal){
			frappe.model.with_doc("Crop", frm.doc.crop, function() {
				let crop = frappe.model.get_doc("Crop", frm.doc.crop);
				console.log(crop);
				frappe.run_serially([
					() => frm.call("create_project", {
						period: crop.period, 
						crop_tasks: crop.agriculture_task
					}, (r) => {
						frm.doc.project = r.message;
						frm.refresh_field("project");
					}),
					// () => $.each(crop.agriculture_task, function(index, row){
					// 	frm.call("create_task", {
					// 		subject: `${row.subject} ${frm.doc.crop}`,
					// 		day: row.day,
					// 		project: frm.doc.project,
					// 		holiday_management: row.holiday_management,
					// 		priority: row.priority
					// 	});
					// })
				]);
			});
		}
	}
	// crop: function(frm) {
	// 	if (frm.doc.crop != undefined) {
	// 		frappe.model.with_doc("Crop", frm.doc.crop, function() {

	// 			$.each(crop.agriculture_task, function(index, row){
	// 				frm.call("create_tasks", {
	// 					subject: row.subject + frm.doc.name,
	// 					day: row.day,
	// 					holiday_management: row.holiday_management,
	// 					priority: row.priority
	// 				}, (r) => {
	// 					let d = frm.add_child("crop_cycle_task");
	// 					d.task = r.message;
	// 					d.land_unit = frm.doc.land_unit;
	// 					frm.refresh_field('crop_cycle_task');
	// 				});
	// 			});
	// 		});
	// 	}
	// }
});