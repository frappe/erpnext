cur_frm.cscript.refresh = function(doc, dt, dn) {
	if (doc.__islocal) {
		hide_field(['Repost Account Balances', 'Repost Voucher Outstanding']);
		set_multiple(dt, dn, {'is_fiscal_year_closed': 'No'});
	}
	else unhide_field(['Repost Account Balances', 'Repost Voucher Outstanding']);
}
