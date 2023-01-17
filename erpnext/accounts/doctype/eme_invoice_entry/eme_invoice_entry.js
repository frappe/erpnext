// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('EME Invoice Entry', {
	refresh:(frm)=>{
		if(frm.doc.docstatus == 1 && frm.doc.invoice_created == 0){
			cur_frm.add_custom_button(__('Create EME Invoice'), function(doc) {
				frm.events.create_eme_invoice(frm)
			},__("Create"))
		}
		if(frm.doc.docstatus == 1 && frm.doc.successful > 0 && frm.doc.invoice_created == 1 && frm.doc.posted_to_account == 0){
			cur_frm.add_custom_button(__('Apply EME Invoice'), function(doc) {
				frm.events.apply_eme_invice(frm)
			},__("Create"))
			cur_frm.add_custom_button(__('Post To Account'), function(doc) {
				frm.events.post_to_account(frm)
			},__("Create"))
		}
	},
	setup: (frm) => {
		if( frm.doc.__islocal===1 ){
			frm.set_value('from_date', frappe.datetime.month_start());
			frm.set_value('to_date', frappe.datetime.month_end());
		}
		frm.fields_dict['deductions'].grid.get_field('supplier').get_query = function(){
			return {
				filters: {
					supplier_group:"Transporter",
					disabled:0
				}
			}
		}
	},
	post_to_account: function(frm){
		frappe.call({
			method: "post_to_account",
			doc:frm.doc,
			callback: function(r) {
				
			}
		});
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
	apply_eme_invice:function(frm){
		frappe.call({
			method:"apply_eme_invice",
			doc: frm.doc,
			callback: function (){},
			freeze: true,
			freeze_message: "Applying EME Invoice....."
		});
	},
	create_eme_invoice:function(frm){
		frappe.call({
			method:"create_eme_invoice",
			doc: frm.doc,
			callback: function (){},
			freeze: true,
			freeze_message: "Creating EME Invoice....."
		});
	}
});
function fetch_supplier(frm){
	if (frm.doc.docstatus != 1){
		frappe.call({
			method:"get_supplier_with_equipment",
			doc: frm.doc,
			callback: function (){
				frm.refresh_field("items")
				frm.dirty()
			}
		});
	}
}

frappe.ui.form.on('EME Invoice Success', {
	view_transaction:function(frm, cdt, cdn){
		let row = locals[cdt][cdn]
		frappe.set_route("Form", "EME Invoice", row.eme_invoice);	
	}
})