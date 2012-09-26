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

$.extend(wn.pages.users, {
	onload: function(wrapper) {
		var w = wn.pages.users;
		wn.ui.make_app_page({
			parent: w,
			title: "Users",
			single_column: true
		});
		w.profiles = {};
		w.refresh();
		w.setup();
		w.role_editor = new erpnext.RoleEditor();
	},
	setup: function() {
		wn.pages.users.appframe.add_button('+ Add User', function() {
			wn.pages.users.add_user();
		});
		
		// set roles
		var w = wn.pages.users;
		$(w).on('click', '.btn.user-roles', function() {
			var uid = $(this).parent().parent().attr('data-name');
			wn.pages.users.role_editor.show(uid);
		});

		// settings
		$(w).on('click', '.btn.user-settings', function() {
			var uid = $(this).parent().parent().attr('data-name');
			wn.pages.users.show_settings(uid);
		});
		
		// delete
		$(w).on('click', 'a.close', function() {
			$card = $(this).parent();
			var uid = $card.attr('data-name');
			$card.css('opacity', 0.6);
			wn.call({
				method: 'utilities.page.users.users.delete',
				args: {'uid': uid},
				callback: function(r,rt) {
					if(!r.exc)
						$card.fadeOut()
				}
			});
		})
		
	},
	refresh: function() {
		// make the list
		wn.call({
			method:'utilities.page.users.users.get',
			callback: function(r, rt) {
				$(wn.pages.users).find('.layout-main').empty();
				for(var i in r.message) {
					var p = r.message[i];
					wn.pages.users.profiles[p.name] = p;
					wn.pages.users.render(p);
				}
			}
		});
		if(!$('.subscription-info').length && (wn.boot.max_users || wn.boot.expires_on)) {
			var $sub_info = $('<div class="subscription-info-box"><div>')
					.insertAfter($(wn.pages.users).find('.help'));
			if(wn.boot.max_users) {
				$sub_info.append(repl('\
				<span class="subscription-info"> \
					Max Users: <b>%(max_users)s</b> \
				</span>', { max_users: wn.boot.max_users }));
			}
			if(wn.boot.expires_on) {
				$sub_info.append(repl('\
				<span class="subscription-info"> \
				Expires On: <b>%(expires_on)s</b> \
				</span>', { expires_on: dateutil.str_to_user(wn.boot.expires_on) }));
			}
		}
	},
	render: function(data) {
		if(data.file_list) {
			data.imgsrc = 'files/' + data.file_list.split('\n')[0].split(',')[1];
		} else {
			data.imgsrc = 'lib/images/ui/no_img_' + (data.gender=='Female' ? 'f' : 'm') + '.gif';
		}
		data.fullname = wn.user_info(data.name).fullname;
		data.delete_html = '';
		if(!data.enabled) 
			data.delete_html = '<a class="close" title="delete">&times;</a>';
		
		$(wn.pages.users).find('.layout-main').append(repl('<div class="user-card" data-name="%(name)s">\
			%(delete_html)s\
			<img src="%(imgsrc)s">\
			<div class="user-info">\
				<b class="user-fullname">%(fullname)s</b><br>\
				%(name)s<br>\
				<button class="btn btn-small user-roles"><i class="icon-user"></i> Roles</button>\
				<button class="btn btn-small user-settings"><i class="icon-cog"></i> Settings</button>\
			</div>\
		</div>', data));
		
		if(!data.enabled) {
			$(wn.pages.users).find('.layout-main .user-card:last')
				.addClass('disabled')
				.find('.user-fullname').html('Disabled');
		}
	},
	show_settings: function(uid) {
		var me = wn.pages.users;
		if(!me.settings_dialog)
			me.make_settings_dialog();
		
		var p = me.profiles[uid];
		me.uid = uid;
		
		me.settings_dialog.set_values({
			restrict_ip: p.restrict_ip || '',
			login_before: p.login_before || '',
			login_after: p.login_after || '',
			enabled: p.enabled || 0,
			new_password: ''
		});
		
		me.settings_dialog.show();

	},
	make_settings_dialog: function() {
		var me = wn.pages.users;
		me.settings_dialog = new wn.widgets.Dialog({
			title: 'Set User Security',
			width: 500,
			fields: [
				{
					label:'Enabled',
					description: 'Uncheck to disable',
					fieldtype: 'Check', fieldname: 'enabled'
				},
				{
					label:'IP Address', 
					description: 'Restrict user login by IP address, partial ips (111.111.111), \
					multiple addresses (separated by commas) allowed', 
					fieldname:'restrict_ip', fieldtype:'Data'
				},
				{
					label:'Login After',
					description: 'User can only login after this hour (0-24)',
					fieldtype: 'Int', fieldname: 'login_after'
				},
				{
					label:'Login Before',
					description: 'User can only login before this hour (0-24)',
					fieldtype: 'Int', fieldname: 'login_before'
				},
				{
					label:'New Password',
					description: 'Update the current user password',
					fieldtype: 'Data', fieldname: 'new_password'
				},
				{
					label:'Update', fieldtype:'Button', fieldname:'update'
				}
			]
		});

		this.settings_dialog.fields_dict.update.input.onclick = function() {
			var btn = this;
			var args = me.settings_dialog.get_values();
			args.user = me.uid;

			if (args.new_password) {
				me.get_password(btn, args);
			} else {
				me.update_security(btn, args);
			}
		};
		
	},
	update_security: function(btn, args) {
		var me = wn.pages.users;
		$(btn).set_working();
		$c_page('utilities', 'users', 'update_security', JSON.stringify(args), function(r,rt) {
			$(btn).done_working();
			if(r.exc) {
				msgprint(r.exc);				
				return;
			}
			me.settings_dialog.hide();
			$.extend(me.profiles[me.uid], me.settings_dialog.get_values());
			me.refresh();
		});
	},
	get_password: function(btn, args) {
		var me = wn.pages.users;
		var pass_d = new wn.widgets.Dialog({
			title: 'Your Password',
			width: 300,
			fields: [
				{
					label: 'Please Enter <b style="color: black">Your Password</b>',
					description: "Your password is required to update the user's password",
					fieldtype: 'Password', fieldname: 'sys_admin_pwd', reqd: 1		
				},
				{
					label: 'Continue', fieldtype: 'Button', fieldname: 'continue'
				}
			]
		});

		pass_d.fields_dict.continue.input.onclick = function() {
			btn.pwd_dialog.hide();					
			args.sys_admin_pwd = btn.pwd_dialog.get_values().sys_admin_pwd;					
			btn.set_working();					
			me.update_security(btn, args);
			btn.done_working();
		}

		pass_d.show();
		btn.pwd_dialog = pass_d;
		btn.done_working();	
	},
	add_user: function() {
		var me = wn.pages.users;
		var active_users = $('.user-card:not(.disabled)');
		if(wn.boot.max_users && (active_users.length >= wn.boot.max_users)) {
			msgprint(repl("You already have <b>%(active_users)s</b> active users, \
			which is the maximum number that you are currently allowed to add. <br /><br /> \
			So, to add more users, you can:<br /> \
			1. <b>Upgrade to the unlimited users plan</b>, or<br /> \
			2. <b>Disable one or more of your existing users and try again</b>",
				{active_users: active_users.length}));
			return;
		}
		var d = new wn.widgets.Dialog({
			title: 'Add User',
			width: 400,
			fields: [{
					fieldtype: 'Data', fieldname: 'user', reqd: 1, 
					label: 'Email Id of the user to add'
				}, {
					fieldtype: 'Data', fieldname: 'first_name', reqd: 1, label: 'First Name'
				}, {
					fieldtype: 'Data', fieldname: 'last_name', label: 'Last Name'
				}, {
					fieldtype: 'Data', fieldname: 'password', reqd: 1, label: 'Password'
				}, {
					fieldtype: 'Button', label: 'Add', fieldname: 'add'
				}]
		});
		
		d.make();
		d.fields_dict.add.input.onclick = function() {
			v = d.get_values();
			if(v) {
				d.fields_dict.add.input.set_working();
				$c_page('utilities', 'users', 'add_user', v, function(r,rt) {
					if(r.exc) { msgprint(r.exc); return; }
					else {
						wn.boot.user_info[v.user] = {fullname:v.first_name + ' ' + (v.last_name || '')};
						d.hide();
						me.refresh();
					}
				})
			}
		}
		d.show();		
	}
});

erpnext.RoleEditor = Class.extend({
	init: function() {
		this.dialog = new wn.widgets.Dialog({
			title: 'Set Roles'
		});
		var me = this;
		$(this.dialog.body).html('<div class="help">Loading...</div>')
		wn.call({
			method:'utilities.page.users.users.get_roles',
			callback: function(r) {
				me.roles = r.message;
				me.show_roles();
			}
		});
	},
	show_roles: function() {
		var me = this;
		$(this.dialog.body).empty();
		for(var i in this.roles) {
			$(this.dialog.body).append(repl('<div class="user-role" \
				data-user-role="%(role)s">\
				<input type="checkbox"> \
				<a href="#"><i class="icon-question-sign"></i></a> %(role)s\
			</div>', {role: this.roles[i]}));
		}
		$(this.dialog.body).append('<div style="clear: both">\
			<button class="btn btn-small btn-info">Save</button></div>');
		$(this.dialog.body).find('button.btn-info').click(function() {
			me.save();
		});
		$(this.dialog.body).find('.user-role a').click(function() {
			me.show_permissions($(this).parent().attr('data-user-role'))
			return false;
		})
	},
	show: function(uid) {
		var me = this;
		this.uid = uid;
		this.dialog.show();
		// set user roles
		wn.call({
			method:'utilities.page.users.users.get_user_roles',
			args: {uid:uid},
			callback: function(r, rt) {
				$(me.dialog.body).find('input[type="checkbox"]').attr('checked', false);
				for(var i in r.message) {
					$(me.dialog.body)
						.find('[data-user-role="'+r.message[i]
							+'"] input[type="checkbox"]').attr('checked',true);
				}
			}
		})
	},
	save: function() {
		var set_roles = [];
		var unset_roles = [];
		$(this.dialog.body).find('[data-user-role]').each(function() {
			var $check = $(this).find('input[type="checkbox"]');
			if($check.attr('checked')) {
				set_roles.push($(this).attr('data-user-role'));
			} else {
				unset_roles.push($(this).attr('data-user-role'));
			}
		})
		wn.call({
			method:'utilities.page.users.users.update_roles',
			args: {
				set_roles: JSON.stringify(set_roles),
				unset_roles: JSON.stringify(unset_roles),
				uid: this.uid
			},
			btn: $(this.dialog.body).find('.btn-info').get(0),
			callback: function() {
				
			}
		})
	},
	show_permissions: function(role) {
		// show permissions for a role
		var me = this;
		if(!this.perm_dialog)
			this.make_perm_dialog()
		$(this.perm_dialog.body).empty();
		wn.call({
			method:'utilities.page.users.users.get_perm_info',
			args: {role: role},
			callback: function(r) {
				var $body = $(me.perm_dialog.body);
				$body.append('<table class="user-perm"><tbody><tr>\
					<th style="text-align: left">Document Type</th>\
					<th>Level</th>\
					<th>Read</th>\
					<th>Write</th>\
					<th>Submit</th>\
					<th>Cancel</th>\
					<th>Amend</th></tr></tbody></table>');
				for(var i in r.message) {
					var perm = r.message[i];
					
					// if permission -> icon
					for(key in perm) {
						if(key!='parent' && key!='permlevel') {
							if(perm[key]) {
								perm[key] = '<i class="icon-ok"></i>';
							} else {
								perm[key] = '';
							}							
						}
					}
					
					$body.find('tbody').append(repl('<tr>\
						<td style="text-align: left">%(parent)s</td>\
						<td>%(permlevel)s</td>\
						<td>%(read)s</td>\
						<td>%(write)s</td>\
						<td>%(submit)s</td>\
						<td>%(cancel)s</td>\
						<td>%(amend)s</td>\
						</tr>', perm))
				}
				
				me.perm_dialog.show();
			}
		});
		
	},
	make_perm_dialog: function() {
		this.perm_dialog = new wn.widgets.Dialog({
			title:'Role Permissions',
			width: 500
		});
	}
})
