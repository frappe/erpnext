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

pscript['onload_accounts-home'] = function(wrapper) {
	erpnext.module_page.setup_page('Accounts', wrapper);
	wrapper.appframe = new wn.ui.AppFrame($(wrapper).find('.appframe-area'), 'Accounts');
	
	if(wn.control_panel.country!='India') {
		$('.india-specific').toggle(false);
	}

	if(wn.boot.profile.roles.indexOf('Accounts Manager')==-1 && wn.boot.profile.roles.indexOf('Accounts User')==-1) {
		$('[href*="Accounts Browser"]').each(function() {
			var txt = $(this).text();
			$(this).parent().css('color', '#999').html(txt);
		});
	}

}
