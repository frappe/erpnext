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

pscript.onload_contact = function(wrapper) {
	$('#content-contact-us .btn.primary').click(function() {
		var me = this;
		var args = {};
		args.name = $('#content-contact-us [name="contact-name"]').val();
		args.email = $('#content-contact-us [name="contact-email"]').val();
		args.message = $('#content-contact-us [name="contact-message"]').val();
		
		if(!validate_email(args.email)) {
			msgprint('Please enter a valid email id');
			return;
		}
		
		if(args.name && args.email && args.message) {
			$(this).set_working();
			$c_page('website', 'contact', 'send', args, function(r) {
				$('#content-contact-us [name*="contact"]').val('');
				$(me).done_working();
			});
		} else {
			msgprint("Please enter info in all the fields.")
		}
	});
	
	$('#content-contact-us :input').keyup(function(ev) {
		if(ev.which == 13) {
			$('#content-contact-us .btn.primary').click();
		}
	});
}