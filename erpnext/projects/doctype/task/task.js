// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.projects");

frappe.ui.form.on("Task", {
	setup: function (frm) {
		frm.make_methods = {
			Timesheet: () =>
				frappe.model.open_mapped_doc({
					method: "erpnext.projects.doctype.task.task.make_timesheet",
					frm: frm,
				}),
		};
	},

	onload: function (frm) {
		calulate_progress(frm);
		frm.set_query("task", "depends_on", function () {
			let filters = {
				name: ["!=", frm.doc.name],
			};
			if (frm.doc.project) filters["project"] = frm.doc.project;
			return {
				filters: filters,
			};
		});

		frm.set_query("parent_task", function () {
			let filters = {
				is_group: 1,
				name: ["!=", frm.doc.name],
			};
			if (frm.doc.project) filters["project"] = frm.doc.project;
			return {
				filters: filters,
			};
		});
	},

	refresh: function (frm) {
		calulate_progress(frm);
    	fetch_sub_tasks(frm);
	},

	is_group: function (frm) {
		frappe.call({
			method: "erpnext.projects.doctype.task.task.check_if_child_exists",
			args: {
				name: frm.doc.name,
			},
			callback: function (r) {
				if (r.message.length > 0) {
					let message = __(
						"Cannot convert Task to non-group because the following child Tasks exist: {0}.",
						[r.message.join(", ")]
					);
					frappe.msgprint(message);
					frm.reload_doc();
				}
			},
		});
	},

	validate: function (frm) {
		frm.doc.project && frappe.model.remove_from_locals("Project", frm.doc.project);
	},
	
});

function calulate_progress(frm) {
	if(!frm.is_new()){
		frappe.call({
			method: "erpnext.projects.doctype.task.task.update_percent_complete",
			args: {task_name: frm.doc.name},
			callback: function(r) {
				if (r.message){
					frm.set_value("progress",r.message);
					//frm.refresh_field("progress")
				}
			}
		});
	}
}

function fetch_sub_tasks(frm) {
	frappe.call({
		method: "erpnext.projects.doctype.task.task.get_sub_tasks",
		args: {task_name:frm.doc.name},
		callback: function(r) {
			frm.clear_table("sub_tasks")
			if( r.message && r.message.length > 0 ){
				r.message.forEach( st => {
					let row = frm.add_child("sub_tasks");
					row.task_name = st.name;
					row.subject = st.sub_task_name;
					row.progress = st.progress;
				});
			}
			frm.refresh_field("sub_tasks");
		}
	});
}