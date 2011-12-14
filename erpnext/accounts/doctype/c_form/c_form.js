//c-form js file
// -----------------------------
cur_frm.fields_dict.invoice_details.grid.get_field("invoice_no").get_query = function(doc) {
	return 'SELECT `tabReceivable Voucher`.`name` FROM `tabReceivable Voucher` WHERE `tabReceivable Voucher`.`company` = "' +doc.company+'" AND `tabReceivable Voucher`.%(key)s LIKE "%s" AND `tabReceivable Voucher`.`customer` = "' + doc.customer + '" AND `tabReceivable Voucher`.`docstatus` = 1 and `tabReceivable Voucher`.`c_form_applicable` = "Yes" and ifnull(`tabReceivable Voucher`.c_form_no, "") = "" ORDER BY `tabReceivable Voucher`.`name` ASC LIMIT 50';
}

cur_frm.cscript.invoice_no = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	get_server_fields('get_invoice_details', d.invoice_no, 'invoice_details', doc, cdt, cdn, 1);
}
