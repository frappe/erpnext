// complete my company registration
// --------------------------------
pscript.complete_registration = function(is_complete, profile) {
	if(is_complete == 'No'){
		var d = new Dialog(400, 200, "Setup your Account");
		if(user != 'Administrator'){
			d.no_cancel(); // Hide close image
			$('header').toggle(false);
		}

		d.make_body([
			['HTML', 'Your Profile Details', '<h4>Your Profile Details</h4>'],
			['Data', 'First Name'],
			['Data', 'Last Name'],
			['HTML', 'Company Details', '<h4>Create your first company</h4>'],
			['Data','Company Name','Example: Your Company LLC'],
	  		['Data','Company Abbreviation', 'Example: YC (all your acconts will have this as a suffix)'],
	  		['Select','Fiscal Year Start Date'],
	  		['Select','Default Currency'],
	  		['Button','Save'],
		]);

		// if company name is set, set the input value
		// and disable it
		if(wn.control_panel.company_name) {
			d.widgets['Company Name'].value = wn.control_panel.company_name;
			d.widgets['Company Name'].disabled = 1;
		}
		
		if(profile && profile.length>0) {
			if(profile[0].first_name && profile[0].first_name!='None') {
				d.widgets['First Name'].value = profile[0].first_name;
			}

			if(profile[0].last_name && profile[0].last_name!='None') {
				d.widgets['Last Name'].value = profile[0].last_name;
			}
		}


		//d.widgets['Save'].disabled = true;	  // disable Save button
		pscript.make_dialog_field(d);

		// submit details
		d.widgets['Save'].onclick = function()
		{
			d.widgets['Save'].set_working();
			
			flag = pscript.validate_fields(d);
			if(flag)
			{
				var args = [
					d.widgets['Company Name'].value,
					d.widgets['Company Abbreviation'].value,
					d.widgets['Fiscal Year Start Date'].value,
					d.widgets['Default Currency'].value,
					d.widgets['First Name'].value,
					d.widgets['Last Name'].value
				];
				
				$c_obj('Setup Control','setup_account',JSON.stringify(args),function(r, rt){
					sys_defaults = r.message;
					user_fullname = r.message.user_fullname;
					d.hide();
					$('header').toggle(true);
					page_body.wntoolbar.set_user_name();
				});
			} else {
				d.widgets['Save'].done_working();
			}
		}
		d.show();
	}
}

// make dialog fields
// ------------------
pscript.make_dialog_field = function(d)
{
	// fiscal year format 
	fisc_format = d.widgets['Fiscal Year Start Date'];
	add_sel_options(fisc_format, ['', '1st Jan', '1st Apr', '1st Jul', '1st Oct']);
  
	// default currency
	currency_list = ['', 'AED', 'AFN', 'ALL', 'AMD', 'ANG', 'AOA', 'ARS', 'AUD', 'AZN', 'BAM', 'BBD', 'BDT', 'BGN', 'BHD', 'BIF', 'BMD', 'BND', 'BOB', 'BRL', 'BSD', 'BTN', 'BYR', 'BZD', 'CAD', 'CDF', 'CFA', 'CFP', 'CHF', 'CLP', 'CNY', 'COP', 'CRC', 'CUC', 'CZK', 'DJF', 'DKK', 'DOP', 'DZD', 'EEK', 'EGP', 'ERN', 'ETB', 'EUR', 'EURO', 'FJD', 'FKP', 'FMG', 'GBP', 'GEL', 'GHS', 'GIP', 'GMD', 'GNF', 'GQE', 'GTQ', 'GYD', 'HKD', 'HNL', 'HRK', 'HTG', 'HUF', 'IDR', 'ILS', 'INR', 'IQD', 'IRR', 'ISK', 'JMD', 'JOD', 'JPY', 'KES', 'KGS', 'KHR', 'KMF', 'KPW', 'KRW', 'KWD', 'KYD', 'KZT', 'LAK', 'LBP', 'LKR', 'LRD', 'LSL', 'LTL', 'LVL', 'LYD', 'MAD', 'MDL', 'MGA', 'MKD', 'MMK', 'MNT', 'MOP', 'MRO', 'MUR', 'MVR', 'MWK', 'MXN', 'MYR', 'MZM', 'NAD', 'NGN', 'NIO', 'NOK', 'NPR', 'NRs', 'NZD', 'OMR', 'PAB', 'PEN', 'PGK', 'PHP', 'PKR', 'PLN', 'PYG', 'QAR', 'RMB', 'RON', 'RSD', 'RUB', 'RWF', 'SAR', 'SCR', 'SDG', 'SDR', 'SEK', 'SGD', 'SHP', 'SOS', 'SRD', 'STD', 'SYP', 'SZL', 'THB', 'TJS', 'TMT', 'TND', 'TRY', 'TTD', 'TWD', 'TZS', 'UAE', 'UAH', 'UGX', 'USD', 'USh', 'UYU', 'UZS', 'VEB', 'VND', 'VUV', 'WST', 'XAF', 'XCD', 'XDR', 'XOF', 'XPF', 'YEN', 'YER', 'YTL', 'ZAR', 'ZMK', 'ZWR'];
	currency = d.widgets['Default Currency'];
	add_sel_options(currency, currency_list);
}


// validate fields
// ---------------
pscript.validate_fields = function(d)
{
	var lst = ['First Name', 'Company Name', 'Company Abbreviation', 'Fiscal Year Start Date', 'Default Currency'];
	var msg = 'Please enter the following fields';
	var flag = 1;
	for(var i=0; i<lst.length; i++)
	{
		if(!d.widgets[lst[i]].value || d.widgets[lst[i]].value=='None'){
			flag = 0;
			msg = msg + NEWLINE + lst[i];
		}
	}

	if(!flag)  alert(msg);
	return flag;
}
