
//--------- ONLOAD -------------
cur_frm.cscript.onload = function(doc, cdt, cdn) {
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	if(!doc.file_list) {
		set_field_options('Upload Accounts Transactions Help', '<div class="help_box">To upload transactions, please attach a (.csv) file with 5 columns - <b>Date, Transaction Number, Account, Debit Amount, Credit Amount</b> (no headings necessary). See attachments box in the right column</div>')
	} else {
		set_field_options('Upload Accounts Transactions Help', '<div class="help_box">To update transactions from the attachment, please click on "Upload Accounts Transactions"</div>')
	}
}

cur_frm.cscript['Upload Accounts Transactions'] = function(doc, cdt, cdn) {
	if(confirm("This action will append all transactions and cannot be un-done. Are you sure you want to continue?")) {
		$c_obj([doc], 'upload_accounts_transactions', '', function(r, rt) { });
	}
}
