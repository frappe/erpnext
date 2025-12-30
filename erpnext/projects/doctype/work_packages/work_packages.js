// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Work Packages", {
	onload(frm){
		calulate_progress(frm);
	},
	refresh(frm) {
		calulate_progress(frm);
    	fetch_tasks(frm);
	}

});

function calulate_progress(frm) {
	if(!frm.is_new()){
		frappe.call({
			method: "erpnext.projects.doctype.work_packages.work_packages.update_percent_complete",
			args: {wp_name: frm.doc.name},
			callback: function(r) {
				if (r.message){
					frm.set_value("progress",r.message);
					// frm.refresh_field("progress")
				}
			}
		});
	}
}

function fetch_tasks(frm) {
	frappe.call({
		method: "erpnext.projects.doctype.work_packages.work_packages.get_tasks",
		args: {wp_name:frm.doc.name},
		callback: function(r) {
			frm.clear_table("tasks")
			if( r.message && r.message.length > 0 ){
				r.message.forEach( task => {
					let row = frm.add_child("tasks");
					row.task = task.name;
					row.subject = task.subject;
					row.progress = task.progress;
				});
			}
			frm.refresh_field("tasks");
		}
	});
}
