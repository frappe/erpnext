// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

// complete my company registration
// --------------------------------

erpnext.complete_setup = function() {
	var currency_list = ['', 'AED', 'AFN', 'ALL', 'AMD', 'ANG', 'AOA', 'ARS', 'AUD', 'AZN', 
	'BAM', 'BBD', 'BDT', 'BGN', 'BHD', 'BIF', 'BMD', 'BND', 'BOB', 'BRL', 'BSD', 'BTN', 'BYR', 
	'BZD', 'CAD', 'CDF', 'CFA', 'CFP', 'CHF', 'CLP', 'CNY', 'COP', 'CRC', 'CUC', 'CZK', 'DJF', 
	'DKK', 'DOP', 'DZD', 'EEK', 'EGP', 'ERN', 'ETB', 'EUR', 'EURO', 'FJD', 'FKP', 'FMG', 'GBP', 
	'GEL', 'GHS', 'GIP', 'GMD', 'GNF', 'GQE', 'GTQ', 'GYD', 'HKD', 'HNL', 'HRK', 'HTG', 'HUF', 
	'IDR', 'ILS', 'INR', 'IQD', 'IRR', 'ISK', 'JMD', 'JOD', 'JPY', 'KES', 'KGS', 'KHR', 'KMF', 
	'KPW', 'KRW', 'KWD', 'KYD', 'KZT', 'LAK', 'LBP', 'LKR', 'LRD', 'LSL', 'LTL', 'LVL', 'LYD', 
	'MAD', 'MDL', 'MGA', 'MKD', 'MMK', 'MNT', 'MOP', 'MRO', 'MUR', 'MVR', 'MWK', 'MXN', 'MYR', 
	'MZM', 'NAD', 'NGN', 'NIO', 'NOK', 'NPR', 'NRs', 'NZD', 'OMR', 'PAB', 'PEN', 'PGK', 'PHP', 
	'PKR', 'PLN', 'PYG', 'QAR', 'RMB', 'RON', 'RSD', 'RUB', 'RWF', 'SAR', 'SCR', 'SDG', 'SDR', 
	'SEK', 'SGD', 'SHP', 'SOS', 'SRD', 'STD', 'SYP', 'SZL', 'THB', 'TJS', 'TMT', 'TND', 'TRY', 
	'TTD', 'TWD', 'TZS', 'UAE', 'UAH', 'UGX', 'USD', 'USh', 'UYU', 'UZS', 'VEB', 'VND', 'VUV', 
	'WST', 'XAF', 'XCD', 'XDR', 'XOF', 'XPF', 'YEN', 'YER', 'YTL', 'ZAR', 'ZMK', 'ZWR'];
	
	var d = new wn.widgets.Dialog({
		title: "Setup",
		fields: [
			{fieldname:'first_name', label:'Your First Name', fieldtype:'Data', reqd: 1},
			{fieldname:'last_name', label:'Your Last Name', fieldtype:'Data'},
			{fieldname:'company_name', label:'Company Name', fieldtype:'Data', reqd:1,
				description: 'e.g. "My Company LLC"'},
			{fieldname:'company_abbr', label:'Company Abbreviation', fieldtype:'Data',
				description:'e.g. "MC"',reqd:1},
			{fieldname:'fy_start', label:'Financial Year Start Date', fieldtype:'Select',
				description:'Your financial year begins on"', reqd:1,
				options: ['', '1st Jan', '1st Apr', '1st Jul', '1st Oct'].join('\n')},
			{fieldname:'currency', label: 'Default Currency', reqd:1,
				options: currency_list.join('\n'), fieldtype: 'Select'},
			{fieldname:'update', label:'Setup',fieldtype:'Button'}
		]
	})
	
	// prepare
	if(user != 'Administrator'){
		d.no_cancel(); // Hide close image
		$('header').toggle(false); // hide toolbar
	}
	
	// company name already set
	if(wn.control_panel.company_name) {
		var inp = d.fields_dict.company_name.input;
		inp.value = wn.control_panel.company_name;
		inp.disabled = true;
	}
	
	// set first name, last name
	if(user_fullname) {
		u = user_fullname.split(' ');
		if(u[0]) {
			d.fields_dict.first_name.input.value = u[0];
		}
		if(u[1]) {
			d.fields_dict.last_name.input.value = u[1];			
		}
	}
	
	// setup
	d.fields_dict.update.input.onclick = function() {
		var data = d.get_values();
		if(!data) return;
		$(this).set_working();
		$c_obj('Setup Control','setup_account',data,function(r, rt){
			sys_defaults = r.message;
			user_fullname = r.message.user_fullname;
			wn.boot.user_fullnames[user] = user_fullname;
			d.hide();
			$('header').toggle(true);
			page_body.wntoolbar.set_user_name();
		});
	}
	
	d.show();
}
