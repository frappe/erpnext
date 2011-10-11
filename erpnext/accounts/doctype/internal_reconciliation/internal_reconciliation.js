// Booking Entry Id
// --------------------

cur_frm.fields_dict.voucher_no.get_query = function(doc) {

	if (!doc.account) msgprint("Please select Account first");
	else {
		return repl("select voucher_no, posting_date \
			from `tabGL Entry` where ifnull(is_cancelled, 'No') = 'No'\
			and account = '%(acc)s' \
			and voucher_type = '%(dt)s' \
			and voucher_no LIKE '%s' \
			ORDER BY posting_date DESC, voucher_no DESC LIMIT 50 \
		", {dt:session.rev_dt_labels[doc.voucher_type] || doc.voucher_type, acc:doc.account});
	}
}

cur_frm.cscript.voucher_no  =function(doc, cdt, cdn) {
	get_server_fields('get_voucher_details', '', '', doc, cdt, cdn, 1)
}

