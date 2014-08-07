// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc, dt, dn) {
	doc = locals[dt][dn];
	var save_msg = __("You must Save the form before proceeding");
	var err_msg = __("There was an error. One probable reason could be that you haven't saved the form. Please contact support@erpnext.com if the problem persists.")

	cur_frm.add_custom_button(__('View Now'), function() {
		doc = locals[dt][dn];
		if(doc.__unsaved != 1) {
			return $c_obj(doc, 'get_digest_msg', '', function(r, rt) {
				if(r.exc) {
					msgprint(err_msg);
					console.log(r.exc);
				} else {
					//console.log(arguments);
					var d = new frappe.ui.Dialog({
						title: __('Email Digest: ') + dn,
						width: 800
					});

					$a(d.body, 'div', '', '', r['message']);

					d.show();
				}
			});
		} else {
			msgprint(save_msg);
		}
	}, "icon-eye-open", "btn-default");
	cur_frm.add_custom_button(__('Send Now'), function() {
		doc = locals[dt][dn];
		if(doc.__unsaved != 1) {
			return $c_obj(doc, 'send', '', function(r, rt) {
				if(r.exc) {
					msgprint(err_msg);
					console.log(r.exc);
				} else {
					//console.log(arguments);
					msgprint(__('Message Sent'));
				}
			});
		} else {
			msgprint(save_msg);
		}
	}, "icon-envelope", "btn-default");
}

cur_frm.cscript.addremove_recipients = function(doc, dt, dn) {
	// Get user list
	return $c_obj(doc, 'get_users', '', function(r, rt) {
		if(r.exc) {
			msgprint(r.exc);
		} else {
			// Open a dialog and display checkboxes against email addresses
			doc = locals[dt][dn];
			var d = new frappe.ui.Dialog({
				title: __('Add/Remove Recipients'),
				width: 400
			});
			var dialog_div = $a(d.body, 'div', 'dialog-div', '', '');
			var tab = make_table(dialog_div, r.user_list.length+2, 2, '', ['15%', '85%']);
			tab.className = 'user-list';
			var add_or_update = 'Add';
			$.each(r.user_list, function(i, v) {
				var check = $a_input($td(tab, i+1, 0), 'checkbox');
				check.value = v.name;
				if(v.checked==1) {
					check.checked = 1;
					add_or_update = 'Update';
				}
				var fullname = frappe.user.full_name(v.name);
				if(fullname !== v.name) v.name = fullname + " &lt;" + v.name + "&gt;";
				if(v.enabled==0) {
					v.name = repl("<span style='color: red'> %(name)s (disabled user)</span>", {name: v.name});
				}
				var user = $a($td(tab, i+1, 1), 'span', '', '', v.name);
				//user.onclick = function() { check.checked = !check.checked; }
			});

			// Display add recipients button
			if(r.user_list.length>15) {
				$btn($td(tab, 0, 1), add_or_update + ' Recipients', function() {
					cur_frm.cscript.add_to_rec_list(doc, tab, r.user_list.length);
				});
			}
			$btn($td(tab, r.user_list.length+1, 1), add_or_update + ' Recipients', function() {
				cur_frm.cscript.add_to_rec_list(doc, tab, r.user_list.length);
			});

			cur_frm.rec_dialog = d;
			d.show();
		}
	});
}

cur_frm.cscript.add_to_rec_list = function(doc, tab, length) {
	// add checked users to list of recipients
	var rec_list = [];
	for(var i = 1; i <= length; i++) {
		var input = $($td(tab, i, 0)).find('input');
		if(input.is(':checked')) {
			rec_list.push(input.attr('value'));
		}
	}
	doc.recipient_list = rec_list.join('\n');
	cur_frm.rec_dialog.hide();
	cur_frm.save();
	cur_frm.refresh_fields();
}
