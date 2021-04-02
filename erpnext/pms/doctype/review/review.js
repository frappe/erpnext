// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
//  developed by Birendra on 15/02/2021

frappe.ui.form.on('Review', {
	refresh: (frm)=>{
		hide_child_table_field(frm)
	},
	onload: (frm) =>{
		apply_filter(frm)
		approver(frm)
	},
	get_competency: (frm) =>{
		get_competency(frm);
	},
	get_target: (frm)=>{
		get_target(frm);
	}
})

var hide_child_table_field = (frm)=>{
	frappe.meta.get_docfield("Review Target Item","appraisees_remarks",cur_frm.doc.name).read_only = frappe.session.user == frm.doc.approver
}

var approver = (frm)=>{
	cur_frm.set_query('approver',()=>{
		return {
			'filters':{
				'roles':'Approver'
			}
		}
	})
}

var apply_filter=(frm) =>{
	cur_frm.set_query('pms_calendar',  () =>{
		return {
			'filters': {
				'name': frappe.defaults.get_user_default('fiscal_year'),
				'docstatus': 1
			}
		};
	});
}

var get_target = (frm) =>{
	//get traget from py file
	if (frm.doc.required_to_set_target && frm.doc.pms_calendar) {
		frappe.call({
			method: 'get_target',
			doc: frm.doc,
			callback:  (r) =>{
				frm.refresh_field("review_target_item")
			}
		})
	}else{
		frappe.throw("Select PMS Calendar to get <b>Target</b>")
	}
}

var get_competency = (frm) =>{
	if (frm.doc.pms_calendar) {
		frappe.call({
			method: "get_competency",
			doc: frm.doc,
			callback:  (r) =>{
				cur_frm.refresh_field("review_competency_item")
			}
		})
	}else{
		frappe.throw("Select PMS Calendar to get <b>Competency</b>")
	}
}

