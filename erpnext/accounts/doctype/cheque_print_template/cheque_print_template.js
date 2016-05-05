// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.cheque_print");

frappe.ui.form.on('Cheque Print Template', {
	refresh: function(frm) {
		if(!frm.doc.__islocal) {
			frm.add_custom_button(__("Cheque Print Preview"), function() {
					erpnext.cheque_print.view_cheque_print(frm);
				});
		}
	}
});


erpnext.cheque_print.view_cheque_print = function(frm) {
		console.log("here")
		console.log(frm.doc)
		var dialog = new frappe.ui.Dialog({
			title: 'Cheque Print Preview'
		});

		dialog.show();
		var body = dialog.body;
		console.log(frm.doc.cheque_width)
		dialog.$wrapper.find('.modal-dialog').css("width", "790px");

		$(body).html("<div style='width:"+ frm.doc.cheque_width + "cm; \
						height: "+ frm.doc.cheque_height +"cm;\
						border: 1px solid black;'>\
							<span style='top: "+frm.doc.data_7+"cm;\
								right: "+ flt(frm.doc.cheque_width-frm.doc.data_8) +"cm;\
								position: absolute;'> "+ frappe.datetime.obj_to_user() +" </span>\
							<span style='top:"+ frm.doc.data_9 +"cm;\
								left: "+ flt(frm.doc.data_10) +"cm;\
								position: absolute;'> saurabh Palnde </span>\
							<span style='top:"+ frm.doc.data_11 +"cm;\
								left: "+ flt(frm.doc.data_13) +"cm;\
								position: absolute;'> Forty One Thousand Six hundred And Sixty Six Only </span>\
							<span style='top:"+ frm.doc.data_15 +"cm;\
								right: "+ flt(frm.doc.cheque_width-frm.doc.data_16) +"cm;\
								position: absolute;'> 41666.00 </span>\
							<span style='top:"+ frm.doc.data_17 +"cm;\
								right: "+ flt(frm.doc.cheque_width-frm.doc.data_18) +"cm;\
								position: absolute;'> Frappe Technologies Pvt Ltd </span>\
					</div>")
		
	}
