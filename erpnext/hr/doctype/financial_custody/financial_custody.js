// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("expense_claim", "employee_name", "employee_name");
cur_frm.add_fetch("expense_claim", "exp_approver", "reported_by");
cur_frm.add_fetch("expense_claim", "employee", "employee");
cur_frm.add_fetch("expense_claim", "total_sanctioned_amount", "custody_value");
cur_frm.add_fetch("expense_claim", "posting_date", "date");

frappe.ui.form.on('Financial Custody', {
	refresh: function(frm) {
		//~ get_employee(frm);
		cur_frm.cscript.show_aprove_data(frm.doc);
		
	}
});
//~ cur_frm.set_query("expense_claim", function() {
			//~ return {
				//~ "filters": {
					//~ "customer": cur_frm.doc.customer
				//~ }
			//~ };
		//~ });
cur_frm.fields_dict.employee.get_query = function(doc) {
	return{
		query: "erpnext.hr.doctype.financial_custody.financial_custody.emp_query"
	};
};
var get_employee = function(frm) {
  frappe.call({
    doc: frm.doc,
    method: "get_employee_from_session",
    callback: function(r) {
      refresh_many(['reported_by', 'reported_by_name']);
      frm.refresh_fields(['reported_by', 'reported_by_name']);
    }
  });
};
cur_frm.set_query("reported_by", function() {
		return {
			query: "erpnext.hr.doctype.expense_claim.expense_claim.get_expense_approver"
		};
	});
cur_frm.cscript.custom_value =cur_frm.cscript.custom_custody_value= function(doc)
{
	if(!doc.__islocal){
		var total =0;
		li = doc.financial_custody_attachment;
		for (var i = 0; i < li.length; i++) {
			total += parseInt(li[i].value);
		}
		doc.paid = 0;
		doc.paid = total ;
		doc.remaining = flt(doc.custody_value) - total ;
		refresh_many(['paid','remaining']);
		cur_frm.refresh_fields(['paid','remaining']);
	}

};
cur_frm.cscript.show_aprove_data =function(doc)
{
	//~ if(in_list(user_roles, "Expense Approver") || in_list(user_roles, "Accounts User")||in_list(user_roles, "System Manager")) {
		 //~ cur_frm.set_df_property("date", "read_only",0);
		 //~ cur_frm.set_df_property("custody_value", "read_only",0);
	//~ }
	//~ else {
		//~ cur_frm.set_df_property("date", "read_only",1);
		//~ cur_frm.set_df_property("custody_value", "read_only",1);
	//~ }
	// refresh_many(["date","custody_value","reason","employee"]);
};
$(document).on("form-load", function(doc) {
  $(".form-attachments .attachment-row .close").remove();
  $('.form-assignments').remove();
  $('[data-fieldtype="Attach"] .control-value').html('<a class="attached-file" target="_blank" href="' + $('[data-fieldtype="Attach"] .control-value').text() + '">' + $('[data-fieldtype="Attach"] .control-value').text() + '</a>');
});
cur_frm.cscript.employee = function(doc, cdt, cd){
	if (!doc.employee) {
		cur_frm.set_value("employee_name", "");
	}
};
