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

cur_frm.cscript.refresh = function(doc, dt, dn) {
	doc = locals[dt][dn];
	var save_msg = "You must <b>Save</b> the form before proceeding";
	var err_msg = "There was an error. One probable reason could be that you haven't saved the form. Please contact support@erpnext.com if the problem persists."
	
	cur_frm.add_custom_button('View Now', function() {
		doc = locals[dt][dn];
		if(doc.__unsaved != 1) {
			$c_obj(make_doclist(dt, dn), 'get_digest_msg', '', function(r, rt) {
				if(r.exc) {
					msgprint(err_msg);
					console.log(r.exc);
				} else {
					//console.log(arguments);
					var d = new wn.ui.Dialog({
						title: 'Email Digest: ' + dn,
						width: 800
					});

					$a(d.body, 'div', '', '', r['message']);

					d.show();
				}
			});
		} else {
			msgprint(save_msg);
		}	
	}, 1);
	cur_frm.add_custom_button('Send Now', function() {
		doc = locals[dt][dn];
		if(doc.__unsaved != 1) {
			$c_obj(make_doclist(dt, dn), 'send', '', function(r, rt) {
				if(r.exc) {
					msgprint(err_msg);
					console.log(r.exc);
				} else {
					//console.log(arguments);
					msgprint('Message Sent');
				}
			});
		} else {
			msgprint(save_msg);
		}
	}, 1);
}

cur_frm.cscript.addremove_recipients = function(doc, dt, dn) {
	// Get profile list
	$c_obj(make_doclist(dt, dn), 'get_profiles', '', function(r, rt) {
		if(r.exc) {
			msgprint(r.exc);
		} else {
			// Open a dialog and display checkboxes against email addresses
			doc = locals[dt][dn];
			var d = new wn.ui.Dialog({
				title: 'Add/Remove Recipients',
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
	cur_frm.rec_dialog.hide();
	cur_frm.save();
	cur_frm.refresh_fields();
}
