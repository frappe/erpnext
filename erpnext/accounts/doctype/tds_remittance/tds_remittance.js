// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
{% include "erpnext/public/js/controllers/cheque_details.js" %};
frappe.ui.form.on('TDS Remittance', {
	onload_post_render: function(frm){
		if (frm.doc.docstatus === 1){
			$(".grid-footer").attr('style','');
		}
		$(".grid-upload").addClass('hidden');
	},

	refresh: function (frm) {
		if (frm.doc.docstatus == 1) {
			show_custom_buttons(frm);
		}

		if (frm.doc.docstatus == 0){
			frm.add_custom_button(__('Get Details'),(doc)=>{
				get_details(frm);
			}).addClass("btn-primary")
		}
	},

	base_on_region: function(frm){
		frm.set_value('region','')
		frm.set_df_property('region','reqd',frm.doc.based_on_region)
	},

	tax_withholding_category: function(frm){
		cur_frm.clear_table("items");
		cur_frm.refresh_field("items");
	}
});

frappe.ui.form.on('TDS Remittance Item', {
	items_remove:(frm,cdt,cdn)=>{
		let tds_amount 	= 0;
		let bill_amount = 0;
		frm.doc.items.forEach(v=>{
			tds_amount 	+= flt(v.tds_amount);
			bill_amount += flt(v.bill_amount);
		})
		frm.set_value('total_amount',bill_amount);
		frm.set_value('total_tds',tds_amount);
	}
})

var show_custom_buttons = function(frm){
	// show TDS Receipt Update
	frappe.call({
		method: "erpnext.accounts.doctype.tds_remittance.tds_remittance.get_tds_receipt_update",
		args: {
			tds_remittance: frm.docname
		},
		callback: function(r){
			if(r.message){
				frm.add_custom_button(__("View Receipt Details"), function() {
					frappe.set_route('Form', 'TDS Receipt Update', {name: r.message.tds_receipt_update});
				}, __('View'));
			} else {
				frm.add_custom_button(__('Update TDS Receipt Details'), ()=>{
					frappe.model.open_mapped_doc({
						method: "erpnext.accounts.doctype.tds_remittance.tds_remittance.create_tds_receipt_update",	
						frm: cur_frm,
						callback:(r)=>{
						}
					});
				},__("Create"))
				cur_frm.page.set_inner_btn_group_as_primary(__('Create'))
			}
		}
	});

	// show General Ledger
	frm.add_custom_button(__('Accounting Ledger'), function () {
		frappe.route_options = {
			voucher_no: frm.doc.name,
			from_date: frm.doc.posting_date,
			to_date: frm.doc.posting_date,
			company: frm.doc.company,
			group_by_voucher: false
		};
		frappe.set_route("query-report", "General Ledger");
	}, __("View"));
	cur_frm.page.set_inner_btn_group_as_primary(__('View'));
}

var get_details = function(frm){
	frm.clear_table("items");
	frm.refresh_field("items");
	frm.set_value('total_amount', 0);
	frm.set_value('total_tds', 0);
	frappe.call({
		method: "get_details",
		doc: frm.doc,
		callback: function (r, rt) {
			if ( r.message){
				frm.refresh_field("items");
				frm.set_value('total_amount',r.message[1]);
				frm.set_value('total_tds',r.message[0]);
				frm.refresh_fields();
			}
		},
	});
}