// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Insurance and Registration', {
	onload: function(frm) {
		if (!frm.doc.posting_date) {
			frm.set_value("posting_date", get_today());
		}	
	},
	refresh:function(frm){
		frm.add_custom_button(
			__("Journal Entry"),
			function () {
			  frappe.route_options = {
				"Journal Entry Account.reference_type": frm.doc.doctype,
				"Journal Entry Account.reference_name": frm.doc.name,
				company: frm.doc.company,
			  };
			  frappe.set_route("List", "Journal Entry");
			},
			__("View")
		  );
	}
});
frappe.ui.form.on("Bluebook Fitness and Emission Details", {	
	"amount": function(frm, cdt, cdn) {
		set_total_amount(frm, cdt, cdn);
	},
	"penalty_amount": function(frm, cdt, cdn){
		set_total_amount(frm, cdt, cdn);
	},
	"post_bank_entry":function(frm, cdt, cdn){
		let row = locals[cdt][cdn]
		frappe.call({
			method:"create_je",
			doc:frm.doc,
			args:row,
			callback:function(r){
				if (r.message){
					frappe.model.set_value(cdt, cdn, "journal_entry", r.message);
					frm.refresh_field("items")
					frm.dirty()
				}
			}
		})
	}
}); 
var set_total_amount = function(frm, cdt, cdn){
	var item = locals[cdt][cdn];
	if(flt(item.amount) > 0){
		if (flt(item.penalty_amount) > 0){
			var total = 0
			total = flt(item.amount)+flt(item.penalty_amount)
			frappe.model.set_value(cdt, cdn, "total_amount", total);
		}
		else{
			frappe.model.set_value(cdt, cdn, "total_amount", item.amount);
		}
	}else{
		frappe.throw("Amount Cannot be less than 0")
	}

}
