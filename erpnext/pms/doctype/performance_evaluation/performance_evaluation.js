// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
//  developed by Birendra on 01/03/2021

frappe.ui.form.on('Performance Evaluation', {
	refresh: (frm)=>{
		hide_child_table_field(frm)
	},
	pms_calendar: (frm)=>{
		hide_child_table_field(frm)
		get_achievement(frm)
	},
	onload:(frm)=> {
		apply_filter(frm)
	},
	get_competency:(frm)=> {
		get_competency(frm);
	},
	get_target:(frm)=>{
		get_target(frm);
	}
});

var hide_child_table_field = (frm)=>{
	// frm.fields_dict.evaluate_target_item.grid.toggle_display("supervisor_rating", frappe.session.user == frm.doc.sup_user_id );
	cur_frm.fields_dict.evaluate_target_item.grid.set_column_disp("supervisor_rating",frappe.session.user == frm.doc.approver);
	cur_frm.fields_dict.evaluate_competency_item.grid.set_column_disp("supervisor_rating",frappe.session.user == frm.doc.approver);
	cur_frm.fields_dict.achievements_items.grid.set_column_disp("supervisor_rating",frappe.session.user == frm.doc.approver);
	frappe.meta.get_docfield("Evaluate Target Item","self_rating",cur_frm.doc.name).read_only = frappe.session.user == frm.doc.approver
	frappe.meta.get_docfield("Evaluate Competency Item","self_rating",cur_frm.doc.name).read_only = frappe.session.user == frm.doc.approver
	frappe.meta.get_docfield("Evaluate Additional Achievements","self_rating",cur_frm.doc.name).read_only = frappe.session.user == frm.doc.approver
	frm.set_df_property('a_sup_rating_total', 'hidden', frappe.session.user != frm.doc.approver)
	frm.set_df_property('b_sup_rating_total', 'hidden', frappe.session.user != frm.doc.approver)
}
var apply_filter=(frm)=> {
	cur_frm.set_query('pms_calendar', function () {
		return {
			'filters': {
				'name': frappe.defaults.get_user_default('fiscal_year'),
				'docstatus': 1
			}
		};
	});
}

var get_target = (frm)=>{
	//get traget from py file
	if (frm.doc.required_to_set_target && frm.doc.pms_calendar) {
		frappe.call({
			method: 'get_target',
			doc: frm.doc,
			callback: (r)=> {
				frm.refresh_field("evaluate_target_item")
				// hide_child_table_field(frm)
			}
		})
	}else{
		frappe.throw("Select PMS Calendar to get <b>Target</b>")
	}
}

var get_competency = (frm)=>{
	if (frm.doc.pms_calendar) {
		frappe.call({
			method: "get_competency",
			doc: frm.doc,
			callback: (r)=> {
				cur_frm.refresh_field("evaluate_competency_item")
			}
		})
	}else{
		frappe.throw("Select PMS Calendar to get <b>Competency</b>")
	}
}
var get_achievement = (frm)=>{
	if (frm.doc.pms_calendar) {
		frappe.call({
			method: "get_additional_achievements",
			doc: frm.doc,
			callback: (r)=> {
				cur_frm.refresh_field("achievements_items")
			}
		})
	}else{
		frappe.throw("Select PMS Calendar to get <b>Achievements</b>")
	}
}
