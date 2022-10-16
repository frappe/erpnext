// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('TDS Receipt Update', {
	refresh:function(frm){
		if (frm.doc.docstatus == 0 && in_list(["Other Invoice","Leave Encashment","Overtime"], frm.doc.purpose)){
			frm.add_custom_button(__('Get Invoices'),(doc)=>{
				get_invoices(frm);
			}).addClass("btn-primary")
		}

		frm.set_query("pbva", function() {
			return {
				query: "erpnext.accounts.doctype.tds_receipt_update.tds_receipt_update.apply_pbva_filter",
			};
		});
	},

	purpose:function(frm){
		if (frm.doc.docstatus == 0 && in_list(["Other Invoice","Leave Encashment","Overtime"], frm.doc.purpose)){
			frm.add_custom_button(__('Get Invoices'),(doc)=>{
				get_invoices(frm);
			}).addClass("btn-primary")
		}

		frm.clear_table("items");
		frm.refresh_field("items");
		frm.set_value('total_bill_amount', 0);
		frm.set_value('total_tax_amount', 0);
	}
});

frappe.ui.form.on('TDS Remittance Item', {
	items_remove: (frm,cdt,cdn) => {
		let tds_amount 	= 0
		let bill_amount = 0
		frm.doc.items.map(v=>{
			tds_amount 	+= flt(v.tds_amount)
			bill_amount += flt(v.bill_amount)
		})
		frm.set_value('total_bill_amount',bill_amount)
		frm.set_value('total_tax_amount',tds_amount)
	}
})

var get_invoices = function(frm){
	if(in_list(["Other Invoice","Leave Encashment","Overtime"], frm.doc.purpose)){
		frm.clear_table("items");
		frm.refresh_field("items");
		frm.set_value('total_bill_amount', 0);
		frm.set_value('total_tax_amount', 0);

		frappe.call({
			method: "get_invoices",
			doc: frm.doc,
			callback: function(r, rt) {
				frm.set_value('total_bill_amount',r.message[0]);
				frm.set_value('total_tax_amount',r.message[1]);
				frm.refresh_field("items");
				frm.refresh_fields();
			},
			freeze: true,
			freeze_message: "Loading Payment Invoices..... Please Wait"
		});
	}
}