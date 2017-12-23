// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch('employee','department','department');

frappe.ui.form.on('Training Feedback', {
	onload: function(frm) {
		frm.add_fetch("training_event", "course", "course");
		frm.add_fetch("training_event", "event_name", "event_name");
		frm.add_fetch("training_event", "trainer_name", "trainer_name");
	},
	workflow_state: function(frm){
        cur_frm.refresh_fields(["workflow_state"]);
    },
    validate: function(frm){
        cur_frm.refresh_fields(["workflow_state"]);
    }
});