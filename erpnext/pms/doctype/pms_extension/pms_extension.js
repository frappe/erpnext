// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('PMS Extension', {
	refresh:function(frm){
		disable_fields(frm)
	},
});

function disable_fields(frm){
//disable fields after save
	if (frm.doc.docstatus === 1){
		open_extension(frm)
		cur_frm.set_df_property("target_start_date", "read_only", 1);
		cur_frm.set_df_property("target_end_date", "read_only", 1);
		cur_frm.set_df_property("review_start_date", "read_only", 1);
		cur_frm.set_df_property("review_end_date", "read_only", 1);
		cur_frm.set_df_property("evaluation_start_date", "read_only", 1);
		cur_frm.set_df_property("evaluation_end_date", "read_only", 1);
	}
}
