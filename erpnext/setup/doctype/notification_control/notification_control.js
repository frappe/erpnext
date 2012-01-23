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
	if(validate_email(args['send_to'] || doc.contact_email || '')) {
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
						var cp = locals['Control Panel']['Control Panel'];
						return (cp.auto_email_id || 'automail@erpnext.com');
					}
				})();
				if(res.send) {
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
				}
			}
			//console.log(JSON.parse(r.message));
		});
	}
}
