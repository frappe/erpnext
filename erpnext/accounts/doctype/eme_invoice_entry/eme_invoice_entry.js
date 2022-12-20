// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('EME Invoice Entry', {
	refresh:(frm)=>{
		if(frm.doc.docstatus == 1){
			cur_frm.add_custom_button(__('Create EME Invoice'), function(doc) {
				frm.events.create_eme_invoice(frm)
			},__("Create"))
		}
	},
	setup: (frm) => {
		frm.set_value('from_date', frappe.datetime.month_start());
		frm.set_value('to_date', frappe.datetime.month_end());
	},
	get_supplier: function(frm) {
		fetch_supplier(frm)
	},
	from_date:function(frm){
		frm.events.clear_child_table(frm)
	},
	to_date:function(frm){
		frm.events.clear_child_table(frm)
	},
	clear_child_table:function(frm){
		frm.clear_table("items");
		frm.refresh_fields();
	},
	tds_percent:function(frm){
		if (frm.doc.tds_percent){
			frappe.call({
				method: "erpnext.accounts.utils.get_tds_account",
				args: {
					percent:frm.doc.tds_percent,
					company:frm.doc.company
				},
				callback: function(r) {
					if(r.message) {
						frm.set_value("tds_account",r.message)
						frm.refresh_fields("tds_account")
					}
				}
			});
		}
	},
	create_eme_invoice:function(frm){
		frappe.call({
			method:"create_eme_invoice",
			doc: frm.doc,
			callback: function (){
				// frm.refresh_field("items")
	
			}
		});
	}
});
function fetch_supplier(frm){
	frappe.call({
		method:"get_supplier_with_equipment",
		doc: frm.doc,
		callback: function (){
			frm.refresh_field("items")

		}
	});
}
