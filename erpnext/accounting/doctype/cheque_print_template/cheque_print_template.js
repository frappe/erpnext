// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.cheque_print");

frappe.ui.form.on('Cheque Print Template', {
	refresh: function(frm) {
		if(!frm.doc.__islocal) {
			frm.add_custom_button(frm.doc.has_print_format?__("Update Print Format"):__("Create Print Format"),
				function() {
					erpnext.cheque_print.view_cheque_print(frm);
				}).addClass("btn-primary");

			$(frm.fields_dict.cheque_print_preview.wrapper).empty()


			var template = '<div style="position: relative; overflow-x: scroll;">\
				<div id="cheque_preview" style="width: {{ cheque_width }}cm; \
					height: {{ cheque_height }}cm;\
					background-repeat: no-repeat;\
					background-size: cover;">\
					<span style="top: {{ acc_pay_dist_from_top_edge }}cm;\
						left: {{ acc_pay_dist_from_left_edge }}cm;\
						border-bottom: solid 1px;border-top:solid 1px;\
						position: absolute;"> {{ message_to_show || __("Account Pay Only") }} </span>\
					<span style="top: {{ date_dist_from_top_edge }}cm;\
						left: {{ date_dist_from_left_edge }}cm;\
						position: absolute;"> {{ frappe.datetime.obj_to_user() }} </span>\
					<span style="top: {{ acc_no_dist_from_top_edge }}cm;\
						left: {{ acc_no_dist_from_left_edge }}cm;\
						position: absolute;"> Acc. No. </span>\
					<span style="top: {{ payer_name_from_top_edge }}cm;\
						left: {{ payer_name_from_left_edge }}cm;\
						position: absolute;"> Payer Name </span>\
					<span style="top:{{ amt_in_words_from_top_edge }}cm;\
						left: {{ amt_in_words_from_left_edge }}cm;\
						position: absolute;\
						display: block;\
						width: {{ amt_in_word_width }}cm;\
						line-height: {{ amt_in_words_line_spacing }}cm;\
						word-wrap: break-word;"> Amount in Words </span>\
					<span style="top: {{ amt_in_figures_from_top_edge }}cm;\
						left: {{ amt_in_figures_from_left_edge }}cm;\
						position: absolute;"> 1000 </span>\
					<span style="top: {{ signatory_from_top_edge }}cm;\
						left: {{ signatory_from_left_edge }}cm;\
						position: absolute;"> Signatory Name </span>\
				</div>\
			</div>';

			$(frappe.render(template, frm.doc)).appendTo(frm.fields_dict.cheque_print_preview.wrapper)

			if (frm.doc.scanned_cheque) {
				$(frm.fields_dict.cheque_print_preview.wrapper).find("#cheque_preview").css('background-image', 'url(' + frm.doc.scanned_cheque + ')');
			}
		}
	}
});


erpnext.cheque_print.view_cheque_print = function(frm) {
	frappe.call({
		method: "erpnext.accounting.doctype.cheque_print_template.cheque_print_template.create_or_update_cheque_print_format",
		args:{
			"template_name": frm.doc.name
		},
		callback: function(r) {
			if (!r.exe && !frm.doc.has_print_format) {
				var doc = frappe.model.sync(r.message);
				frappe.set_route("Form", r.message.doctype, r.message.name);
			}
			else {
				frappe.msgprint(__("Print settings updated in respective print format"))
			}
		}
	})
}
