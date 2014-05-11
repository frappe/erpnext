// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.provide("erpnext.projects");

cur_frm.add_fetch("project", "company", "company");

erpnext.projects.Task = wn.ui.form.Controller.extend({
	setup: function() {
		this.frm.fields_dict.project.get_query = function() {
			return {
				query: "projects.doctype.task.task.get_project"
			}
		};
	},

	project: function() {
		if(this.frm.doc.project) {
			return get_server_fields('get_project_details', '','', this.frm.doc, this.frm.doc.doctype, 
				this.frm.doc.name, 1);
		}
	},

	validate: function() {
		this.frm.doc.project && wn.model.remove_from_locals("Project",
			this.frm.doc.project);
	},
});


cur_frm.cscript = new erpnext.projects.Task({frm: cur_frm});

