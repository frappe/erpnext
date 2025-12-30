// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sub Project", {
	onload(frm){
		calulate_progress(frm);
	},
	refresh(frm) {
		calulate_progress(frm);
    	fetch_work_packages(frm);
	}

});

function calulate_progress(frm) {
	if(!frm.is_new()){
		frappe.call({
			method: "erpnext.projects.doctype.sub_project.sub_project.update_percent_complete",
			args: {sp_name: frm.doc.name},
			callback: function(r) {
				if (r.message){
					frm.set_value("percent_complete",r.message);
					//frm.refresh_field("percent_complete")
				}
			}
		});
	}
}

function fetch_work_packages(frm) {
	frappe.call({
		method: "erpnext.projects.doctype.sub_project.sub_project.get_work_packages",
		args: {sub_project_name:frm.doc.name},
		callback: function(r) {
			frm.clear_table("work_packages")
			if( r.message && r.message.length > 0 ){
				r.message.forEach( wp => {
					let row = frm.add_child("work_packages");
					row.work_package_id = wp.name;
					row.work_package_name = wp.work_package_name;
					row.progress = wp.progress;
				});
			}
			frm.refresh_field("work_packages");
		}
	});
}
