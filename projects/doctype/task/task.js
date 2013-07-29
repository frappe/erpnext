// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

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

