cur_frm.cscript.refresh = function(doc, dt, dn) {
	cur_frm.add_custom_button('View Now', function() {
		$c_obj(make_doclist(dt, dn), 'get', '', function(r, rt) {
			if(r.exc) {
				msgprint(r.exc);
			} else {
				//console.log(arguments);
				var d = new wn.widgets.Dialog({
					title: 'Email Digest: ' + dn,
					width: 800
				});

				$a(d.body, 'div', '', '', r['message'][1]);

				d.show();
			}
		});	
	}, 1);
	cur_frm.add_custom_button('Send Now', function() {
		$c_obj(make_doclist(dt, dn), 'send', '', function(r, rt) {
			if(r.exc) {
				msgprint(r.exc);
			} else {
				//console.log(arguments);
				msgprint('Message Sent');
			}
		});	
	}, 1);
}

cur_frm.cscript['Add Recipients'] = function(doc, dt, dn) {
	// Get profile list
	$c_obj(make_doclist(dt, dn), 'get_profiles', '', function(r, rt) {
		if(r.exc) {
			msgprint(r.exc);
		} else {
			// Open a dialog and display checkboxes against email addresses
			doc = locals[dt][dn];
			var d = new wn.widgets.Dialog({
				title: 'Add Recipients',
				width: 400
			});
			var dialog_div = $a(d.body, 'div', 'dialog-div', '', '');
			var tab = make_table(dialog_div, r.profile_list.length+2, 2, '', ['15%', '85%']);
			tab.className = 'profile-list';
			var add_or_update = 'Add';
			$.each(r.profile_list, function(i, v) {
				var check = $a_input($td(tab, i+1, 0), 'checkbox');
				check.value = v.name;
				if(v.checked==1) {
					check.checked = 1;
					add_or_update = 'Update';
				}
				if(v.enabled==0) {
					v.name = "<span style='color: red'>" + v.name + " (disabled user)</span>"
				}
				var profile = $a($td(tab, i+1, 1), 'span', '', '', v.name);
				//profile.onclick = function() { check.checked = !check.checked; }
			});

			// Display add recipients button
			if(r.profile_list.length>15) {
				$btn($td(tab, 0, 1), add_or_update + ' Recipients', function() {
					cur_frm.cscript.add_to_rec_list(doc, tab, r.profile_list.length);
				});
			}
			$btn($td(tab, r.profile_list.length+1, 1), add_or_update + ' Recipients', function() {
				cur_frm.cscript.add_to_rec_list(doc, tab, r.profile_list.length);
			});

			cur_frm.rec_dialog = d;	
			d.show();
		}
	});
}

cur_frm.cscript.add_to_rec_list = function(doc, tab, length) {
	// add checked profiles to list of recipients
	var rec_list = [];
	for(var i = 1; i <= length; i++) {
		var input = $($td(tab, i, 0)).find('input');
		if(input.is(':checked')) {
			rec_list.push(input.attr('value'));
		}
	}
	doc.recipient_list = rec_list.join('\n');
	//console.log(doc.recipient_list);
	cur_frm.rec_dialog.hide();
	cur_frm.refresh_fields();
}
