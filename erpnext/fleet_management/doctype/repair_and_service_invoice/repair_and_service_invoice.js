// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.ui.form.on('Repair And Service Invoice', {
	refresh: function(frm) {
		if (frm.doc.docstatus == 1){
			cur_frm.add_custom_button(__('Ledger'), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: frm.doc.posting_date,
					company: frm.doc.company,
					group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			})
			if (self.status != "Paid"){
				cur_frm.add_custom_button(__('Make Journal Entry'), function(doc) {
					frm.events.make_journal_entry(frm)
				})
			}			
		}
	},
	make_journal_entry:function(frm){
		frappe.call({
			method:
			"post_journal_entry",
			doc:frm.doc,
			callback: function (r) {},
		});
	},
	party_type:function(frm){
		frm.set_value("party","")
		frm.refresh_field("party")
	},
	party:function(frm){
		if (frm.doc.party){
			frappe.call({
				method: "erpnext.accounts.party.get_party_account",
				args: {
					party_type:frm.doc.party_type,
					party:frm.doc.party,
					company: frm.doc.company,
				},
				callback: function(r) {
					if(r.message) {
						frm.set_value("credit_account",r.message)
						frm.refresh_fields("credit_account")
					}
				}
			});
		}
	},
});
frappe.ui.form.on('Repair And Services Invoice Item', {
	rate:function(frm, cdt, cdn){
		calculate_amount(frm, cdt, cdn)
	},
	qty:function( frm, cdt, cdn){
		calculate_amount(frm, cdt, cdn)
	}
})
var calculate_amount = (frm,cdt,cdn)=>{
	var item = locals[cdt][cdn]
	if (item.qty && item.rate){
		item.charge_amount = item.qty * item.rate 
		cur_frm.refresh_field('items')
	}
}