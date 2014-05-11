// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.provide("erpnext.projects");

erpnext.projects.TimeLog = wn.ui.form.Controller.extend({
	onload: function() {
		this.frm.set_query("task", erpnext.queries.task);
	}
});

cur_frm.cscript = new erpnext.projects.TimeLog({frm: cur_frm});

cur_frm.add_fetch('task','project','project');