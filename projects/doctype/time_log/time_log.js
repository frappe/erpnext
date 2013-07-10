wn.provide("erpnext.projects");

erpnext.projects.TimeLog = wn.ui.form.Controller.extend({
	setup: function() {
		this.frm.set_query("task", function() {
			return { query: "projects.utils.query_task" }
		});

cur_frm.cscript = new erpnext.projects.TimeLog({frm: cur_frm});