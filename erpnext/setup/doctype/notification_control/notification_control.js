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

cur_frm.cscript.select_transaction = function(doc, dt, dn) {
  if(doc.select_transaction) {
    var callback = function(r,rt) {
      var doc = locals[dt][dn];
      doc.custom_message = r.message;
      refresh_field('custom_message');
    }
    $c_obj('Notification Control','get_message',doc.select_transaction, callback)
}
}

cur_frm.cscript.notify = function(doc, args) {
	$c_obj('Notification Control', 'get_formatted_message', {
		type: args['type'],
		doctype: args['doctype'],
		contact_name: args['contact_name'] || doc.contact_display
	}, function(r, rt) {
		if(!r.exc) {
			var res = JSON.parse(r.message);
			var send_from = (function() {
				if(user!='Administrator') {
					return user;
				} else {
					return (wn.control_panel.auto_email_id || 'automail@erpnext.com');
				}
			})();
			if(res.send) {
				if(validate_email(args['send_to'] || doc.contact_email || '')) {
					var print_heading = (doc.select_print_heading || args['type'])
					sendmail(
						args['send_to'] || doc.contact_email,
						send_from,
						send_from,
						doc.company + " - " + print_heading + " - " + doc.name,
						res.message,
						res.print_format
					);
					msgprint('This ' + print_heading + ' is being sent to <b>'
						+ (args['send_to'] || doc.contact_email) + '</b><br />...');
				} else {
					msgprint('Invalid/Missing Email Address. ' + print_heading + ' not sent.');
				}
			}
		}
		//console.log(JSON.parse(r.message));
	});
}
