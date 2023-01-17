// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transporter Invoice Entry', {
	refresh: function(frm) {
		if(frm.doc.docstatus == 1 && frm.doc.invoice_created == 0){
			cur_frm.add_custom_button(__('Create Transporter Invoice'), function(doc) {
				frm.events.create_transporter_invoice(frm)
			},__("Create"))
		}
		if(frm.doc.docstatus == 1 && frm.doc.invoice_created == 1 && frm.doc.invoice_submitted == 0){
			cur_frm.add_custom_button(__('Submit Transporter Invoice'), function(doc) {
				frm.events.submit_transporter_invoice(frm)
			},__("Create"))
		}
		if(frm.doc.docstatus == 1 && frm.doc.invoice_created == 1 && frm.doc.invoice_submitted == 1 && frm.doc.posted_to_account == 0){
			cur_frm.add_custom_button(__('Cancel Transporter Invoice'), function(doc) {
				frm.events.cancel_transporter_invoice(frm)
			},__("Create"))
		}
		if(frm.doc.docstatus == 1 && frm.doc.invoice_submitted == 1 && frm.doc.posted_to_account == 0){
			cur_frm.add_custom_button(__('Post To Account'), function(doc) {
				frm.events.post_to_account(frm)
			},__("Create"))
		}
	},
	from_date:function(frm){
		frm.events.clear_child_table(frm)
	},
	to_date:function(frm){
		frm.events.clear_child_table(frm)
	},
	clear_child_table:function(frm){
		frm.clear_table("items");
		frm.refresh_field("items")
	},
	get_equipment:function(frm){
		if (frm.doc.branch && frm.doc.equipment_category && frm.doc.supplier_type){
			frappe.call({
				method:"get_equipment",
				doc:frm.doc,
				callback:function(r){
					frm.refresh_field("items")
					frm.dirty()
				},
				freeze: true,
				freeze_message: '<span style="color:white; background-color: red; padding: 10px 50px; border-radius: 5px;">Feching Equipment.....</span>'
			})
		}else{
			frappe.msgprint("Either Branch or Equipment Category missing")
		}
	},
	create_transporter_invoice:function(frm){
		frappe.call({
			method:"create_transporter_invoice",
			doc:frm.doc,
			callback:function(r){
				cur_frm.reload_doc();
			},
			freeze: true,
			freeze_message: '<span style="color:white; background-color: red; padding: 10px 50px; border-radius: 5px;">Creating Invoice.....</span>'
		})
	}, 
	submit_transporter_invoice:function(frm){
		frappe.call({
			method:"submit_transporter_invoice",
			doc:frm.doc,
			callback:function(r){
				cur_frm.reload_doc();
			},
			freeze: true,
			freeze_message: '<span style="color:white; background-color: red; padding: 10px 50px; border-radius: 5px;">Siubmitting Invoice.....</span>'
		})
	},
	cancel_transporter_invoice:function(frm){
		frappe.call({
			method:"cancel_transporter_invoice",
			doc:frm.doc,
			callback:function(r){
				cur_frm.reload_doc();
			},
			freeze: true,
			freeze_message: '<span style="color:white; background-color: red; padding: 10px 50px; border-radius: 5px;">Cancelling Invoice.....</span>'
		})
	},
	post_to_account:function(frm){
		frappe.call({
			method:"post_to_account",
			doc:frm.doc,
			callback:function(r){
				cur_frm.reload_doc();
			},
			freeze: true,
			freeze_message: '<span style="color:white; background-color: red; padding: 10px 50px; border-radius: 5px;">Posting Accounting Entry.....</span>'
		})
	}
});