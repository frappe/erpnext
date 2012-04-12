cur_frm.cscript.refresh = function(doc, dt, dn) {
	if (doc.__islocal) {
		hide_field(['repost_account_balances', 'repost_voucher_outstanding']);
		set_multiple(dt, dn, {'is_fiscal_year_closed': 'No'});
	}
	else unhide_field(['repost_account_balances', 'repost_voucher_outstanding']);
}
