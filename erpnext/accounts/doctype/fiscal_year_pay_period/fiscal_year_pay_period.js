// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fiscal Year Pay Period', {
	onload: function(frm) {
		remove_rows(frm, 'dates');
	},

	refresh: function(frm) {
		var pay_period_start_date = frm.doc.pay_period_start_date;
		var pay_period_end_date = frm.doc.pay_period_end_date;
		var payment_frequency = frm.doc.payment_frequency;
		if(frm.doc.__islocal){
			if(pay_period_start_date && pay_period_end_date && payment_frequency){
				remove_rows(frm, 'dates');
				get_pay_period_dates(frm);
			}
		}
	},

	pay_period_start_date: function(frm) {
		if (frm.doc.pay_period_start_date){
			frm.refresh();
		}
	},

	pay_period_end_date: function(frm) {
		if (frm.doc.pay_period_end_date){
			frm.refresh();
		}
	},

	payment_frequency: function(frm) {
		if (frm.doc.payment_frequency){
			frm.refresh();
		}
	}
});

get_pay_period_dates = function(frm){
	return frappe.call({
				type: "GET",
				method: "erpnext.accounts.doctype.fiscal_year_pay_period.fiscal_year_pay_period.get_pay_period_dates",
				args: {
					"payroll_start": frm.doc.pay_period_start_date,
					"payroll_end": frm.doc.pay_period_end_date,
					"payroll_frequency": frm.doc.payment_frequency
				},
				callback: function(r) {
					if(r.message) {
						auto_populate_date_table(frm, r.message);
					}
				}
			})
};

auto_populate_date_table = function(frm, dates_array){
	var proceed = 0;
	var date_table;

	if(dates_array){
		for(i=0; i < dates_array.length; i++){
			var child = frm.add_child("dates");
			date_obj = dates_array[i];
			frappe.model.set_value(child.doctype, child.name, "start_date", date_obj.start_date);
			frappe.model.set_value(child.doctype, child.name, "end_date", date_obj.end_date);
		}
		frm.refresh_field("dates");
	}
};

remove_rows = function(frm, child_table_name) {
	date_table = frm.doc.dates || [];
	$.each(date_table, function(){
		frm.get_field(child_table_name).grid.grid_rows[0].remove();
	});
}
