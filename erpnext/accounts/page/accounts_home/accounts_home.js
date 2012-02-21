pscript['onload_accounts-home'] = function(wrapper) {
	erpnext.module_page.setup_page('Accounts', wrapper);
	if(wn.control_panel.country!='India') {
		$('.india-specific').toggle(false);
	}
}