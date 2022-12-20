// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('DHI GCOA Mapper', {
	setup:(frm)=>{
		frm.get_docfield("items").allow_bulk_edit = 1;
	},
	account_code:(frm)=>{
		apply_filter(frm)
	}
});

frappe.ui.form.on('DHI Mapper Item',{
	account:(frm)=>{
		apply_filter(frm)
	}
})
var apply_filter = (frm)=>{
	if (frm.doc.account_type){
		frm.fields_dict['items'].grid.get_field('account').get_query = function(){
			return{
				filters: {
					'account_type': frm.doc.account_type,
					'is_group':0
				}
			}
		};
	}else{
		frm.fields_dict['items'].grid.get_field('account').get_query = function(){
			return{
				filters: {
					'is_group':0
				}
			}
		};
	}
}