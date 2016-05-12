// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.cheque_print");

frappe.ui.form.on('Cheque Print Template', {
	refresh: function(frm) {
		if(!frm.doc.__islocal) {
			frm.add_custom_button(__("Cheque Print Preview"), function() {
					erpnext.cheque_print.view_cheque_print(frm);
				});
				
			$(frm.fields_dict.cheque_print_preview.wrapper).empty()
			
			$("<div style='position: relative; overflow-x: scroll;'>\
				<div style='width:"+ frm.doc.cheque_width + "cm; \
					height: "+ frm.doc.cheque_height +"cm;\
					background-image: url("+frm.doc.scanned_cheque+");\
					background-repeat: no-repeat;\
					background-size: cover;'>\
					<span style='top: "+frm.doc.date_dist_from_top_edge+"cm;\
						left: "+ flt(frm.doc.date_dist_from_left_edge) +"cm;\
						position: absolute;'> "+ frappe.datetime.obj_to_user() +" </span>\
					<span style='top: "+frm.doc.acc_no_dist_from_top_edge+"cm;\
						left: "+ frm.doc.acc_no_dist_from_left_edge +"cm;\
						position: absolute;'> Acc. No. </span>\
					<span style='top:"+ frm.doc.payer_name_from_top_edge +"cm;\
						left: "+ flt(frm.doc.payer_name_from_left_edge) +"cm;\
						position: absolute;'> Payer Name </span>\
					<span style='top:"+ frm.doc.amt_in_words_from_top_edge +"cm;\
						left: "+ flt(frm.doc.amt_in_words_from_left_edge) +"cm;\
						position: absolute;\
						display: block;\
						width: "+frm.doc.amt_in_word_width+"cm;\
						line-height: "+frm.doc.amt_in_words_line_spacing+"cm;\
						word-wrap: break-word;'> Amount in Words </span>\
					<span style='top:"+ frm.doc.amt_in_figures_from_top_edge +"cm;\
						left: "+ flt(frm.doc.amt_in_figures_from_left_edge) +"cm;\
						position: absolute;'> 1000 </span>\
					<span style='top:"+ frm.doc.signatory_from_top_edge +"cm;\
						left: "+ flt(frm.doc.signatory_from_left_edge) +"cm;\
						position: absolute;'> Signatory Name </span>\
				</div>\
			</div>").appendTo(frm.fields_dict.cheque_print_preview.wrapper)
		}
	}
});


erpnext.cheque_print.view_cheque_print = function(frm) {
		var dialog = new frappe.ui.Dialog({
			title: 'Cheque Print Preview'
		});

		dialog.show();
		var body = dialog.body;
		console.log(frm.doc.cheque_width)
		dialog.$wrapper.find('.modal-dialog').css("width", "790px");

		$(body).html("<div style='width:"+ frm.doc.cheque_width + "cm; \
						height: "+ frm.doc.cheque_height +"cm;\
						background-image: url("+frm.doc.cheque_scan+");\
						background-repeat: no-repeat;\
						background-size: cover;\
						border: 1px solid black;'>\
							<span style='top: "+frm.doc.data_7+"cm;\
								left: "+ flt(frm.doc.data_8) +"cm;\
								position: absolute;'> "+ frappe.datetime.obj_to_user() +" </span>\
							<span style='top: "+frm.doc.acc_no_ps+"cm;\
								left: "+ frm.doc.str_loc_acc_no +"cm;\
								position: absolute;'> 1234567890 </span>\
							<span style='top:"+ frm.doc.data_9 +"cm;\
								left: "+ flt(frm.doc.data_10) +"cm;\
								position: absolute;'> Saurabh Palande </span>\
							<span style='top:"+ frm.doc.data_11 +"cm;\
								left: "+ flt(frm.doc.data_13) +"cm;\
								position: absolute;\
								display: block;\
								width: "+frm.doc.ln_width+"cm;\
								line-height: "+frm.doc.ln_spacing+"cm;\
								word-wrap: break-word;'>One Crore One Lakh Forty One Thousand Six hundred And Sixty Six Only </span>\
							<span style='top:"+ frm.doc.data_15 +"cm;\
								left: "+ flt(frm.doc.data_16) +"cm;\
								position: absolute;'> 1,01,41666.00 </span>\
							<span style='top:"+ frm.doc.data_17 +"cm;\
								left: "+ flt(frm.doc.data_18) +"cm;\
								position: absolute;'> Frappe Technologies Pvt Ltd </span>\
					</div>")
		
	}
