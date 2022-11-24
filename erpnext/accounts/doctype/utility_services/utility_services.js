// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
//add_fetch("link fieldname", "source fieldname", "target fieldname")
cur_frm.add_fetch("utility_service_type", "party","party");
cur_frm.add_fetch("utility_service_type", "service_id","service_id");
cur_frm.add_fetch("utility_service_type", "service_type","service_type");
cur_frm.add_fetch("utility_service_type", "unique_key_field","customer_identification");
cur_frm.add_fetch("branch","expense_bank_account","expense_account");
cur_frm.add_fetch("branch","cost_center","cost_center");

frappe.ui.form.on('Utility Services', {
	refresh: function(frm) {

	},
	"branch": function(frm){
	},
	"expense_account": function(frm){
		frappe.model.get_value('Account', {'name': frm.doc.expense_account}, 'bank_account_no',
		 function(d) {
			cur_frm.set_value("bank_account", d.bank_account_no);
		});
	}

});
