// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
// developed by Birendra on 01/02/2021
frappe.ui.form.on('Target Set Up', {
	pms_calendar: (frm)=>{
		get_competency(frm)
	},
	onload: (frm)=>{
		apply_filter(frm)
	},
	// date:(frm)=>{
	// 	today_date(frm)
	// },

	// employee: (frm)=>{
	// 	get_supervisor_user_id(frm)
	// }
});
// var get_supervisor_user_id = (frm)=>{
// 	if (frm.doc.employee) {
// 		frappe.call({
// 			method: "get_supervisor_user_id",
// 			doc: frm.doc,
// 			callback: ()=> {
// 				cur_frm.refresh_field("sup_user_id")				
// 			}
// 		})
// 	}
// }

// var today_date=(frm)=>{
// 	frm.set_value("date",frappe.datetime.get_today())
// }

var apply_filter=(frm)=> {
	cur_frm.set_query('pms_calendar', ()=> {
		return {
			'filters': {
				'name': frappe.defaults.get_user_default('fiscal_year'),
				'docstatus': 1
			}
		};
	});
}
var get_competency=(frm)=>{
	// get competency from py file
	if (frm.doc.designation) {
		return frappe.call({
			method: 'get_competency',
			doc: frm.doc,
			callback: ()=> {
				frm.refresh_field('competency');
				frm.refresh_fields()
			}
		})
	} else {
		frappe.msgprint('Your Designation is not defined under Employee Category')
	}
}