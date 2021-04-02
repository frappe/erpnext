// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('PMS Calendar', {
	onload: function(frm){
		set_default_field_value(frm)
	},
	refresh:function(frm){
		disable_fields(frm)
	},
	fiscal_year: function(frm){
		set_default_field_value(frm)
	}
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

function open_extension(frm){
//if need to extend open pms extension doc
	frm.add_custom_button('Extend', () => {
		frappe.model.open_mapped_doc({
			method: "erpnext.pms.doctype.pms_calendar.pms_calendar.create_pms_extension",	
			frm: cur_frm
		});
	})
}

function set_default_field_value(frm){
//set default field base on fiscal year
	if ( frm.doc.fiscal_year && frm.doc.docstatus !== 1){
		frm.set_value("target_start_date",frm.doc.fiscal_year);
		frm.set_value("target_end_date",frappe.datetime.add_days(frm.doc.fiscal_year,30));
		frm.set_value("review_start_date",frappe.datetime.add_months(frm.doc.fiscal_year,5));
		frm.set_value("review_end_date",frappe.datetime.add_days(frm.doc.review_start_date,29));
		frm.set_value("evaluation_start_date",frappe.datetime.add_months(frm.doc.fiscal_year,11));
		frm.set_value("evaluation_end_date",frappe.datetime.add_days(frm.doc.evaluation_start_date,30));
	}
}