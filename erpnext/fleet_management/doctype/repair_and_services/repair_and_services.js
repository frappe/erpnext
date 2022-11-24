// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Repair And Services', {
	refresh: function(frm) {
		if(frm.doc.docstatus == 1) {
			cur_frm.add_custom_button(__("Stock Ledger"), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: frm.doc.posting_date,
					company: frm.doc.company
				};
				frappe.set_route("query-report", "Stock Ledger");
			}, __("View"));

			cur_frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: frm.doc.posting_date,
					company: frm.doc.company,
					group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
			if (cint(frm.doc.out_source) == 1 && frm.doc.total_amount > 0 && cint(frm.doc.paid) == 0) {
				frm.add_custom_button("Create Invoice", function () {
					frappe.model.open_mapped_doc({
						method: "erpnext.fleet_management.doctype.repair_and_services.repair_and_services.make_repair_and_services_invoice",
						frm: cur_frm
					})
				});
			}
		}
	}
});
frappe.ui.form.on('Repair And Services Item', {
	// refresh: function(frm) {

	// }
	rate:function(frm,cdt,cdn){
		calculate_amount(frm,cdt,cdn)
	},
	qty:function(frm,cdt,cdn){
		calculate_amount(frm,cdt,cdn)
	},
});

var calculate_amount = (frm,cdt,cdn)=>{
	var item = locals[cdt][cdn]
	if (item.qty && item.rate){
		item.charge_amount = item.qty * item.rate 
		cur_frm.refresh_field('items')
	}
}