// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('PMS Calendar', {
	setup: function(frm) {
	// frm.set_value("fiscal_year",'');
	},
	onload: (frm)=>{
		if ( !frm.doc.target_end_date && frm.doc.fiscal_year)
			set_default_field_value(frm)
		if (frm.doc.title && frm.doc.fiscal_year){
			disable_fields(frm)
		}
	},
	refresh:function(frm){
		open_extension(frm)
	},
	after_save: function(frm){
		disable_fields(frm)
	},

});

//if need to extend open pms extension doc
function open_extension(frm){
	frm.add_custom_button('Extend', () => {
		frappe.model.open_mapped_doc({
			method: "erpnext.hr.doctype.pms_calendar.pms_calendar.create_pms_extension",	
			frm: cur_frm
		});
	})
}