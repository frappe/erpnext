// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Crop Cycle', {
	onload: function(frm) {
	},
	crop: function(frm) {
		if (frm.doc.crop != undefined) {
			frappe.model.with_doc("Crop", frm.doc.crop, function() {
				let crop = frappe.model.get_doc("Crop", frm.doc.crop);
				$.each(crop.agriculture_task, function(index, row){
					frm.call("create_tasks", {
						subject: row.subject + frm.doc.name,
						day: row.day,
						holiday_management: row.holiday_management,
						priority: row.priority
					}, (r) => {
						let d = frm.add_child("crop_cycle_task");
						d.task = r.message;
						d.land_unit = frm.doc.land_unit;
						frm.refresh_field('crop_cycle_task');
					});
				});
			});
		}
	}
});

// Add crop name in title
// Add land unit as text in details
// Tree view when selecting the land unit
// how to handle Intercropping? both should be able to access the same land unit, 
	// with a validation warning (only on 2nd intercrop) if land unit is already in use, 
	// and denote the % of land being used, initially should be 100% for 1 crop


// On choosing the harvest date, ERPNext should be able to sugges the start date and crop cycle
// How to map the, Banana crop cycle? Should a convertion from mother plant to child plant be consifdered as a cycle?  