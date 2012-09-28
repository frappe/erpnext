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

pscript['onload_profile-settings'] = function() {
	var wrapper = wn.pages['profile-settings'];
	pscript.myprofile = new MyProfile(wrapper)
}

MyProfile = function(wrapper) {
	this.wrapper = wrapper;
	var me = this;
	
	this.make = function() {
		this.wrapper.appframe = new wn.ui.AppFrame($(this.wrapper).find('.layout-appframe'), 'Profile Settings');
		this.wrapper.appframe.add_button('Change Password', this.change_password);
		this.wrapper.appframe.add_button('Change Background', this.change_background);
		this.wrapper.appframe.add_label("Set Theme:");
		this.wrapper.appframe.add_select("Theme", 
			["Default", "Desert", "Sky", "Tropic", "Snow", "Sun"]).change(function() {
				erpnext.set_theme($(this).val().toLowerCase());
			}).change(function() {
				wn.call({
					module: "home",
					page: "profile_settings",
					method: "set_user_theme",
					args: {theme: $(this).val() }
				})
			});
		this.tab = make_table($a($(this.wrapper).find('.layout-main').get(0), 'div', '', {marginTop:'19px'}), 
			1, 2, '90%', ['50%', '50%'], {padding:'11px'})
		this.img = $a($td(this.tab, 0, 0), 'img', '', {width: '120px', maxHeight:'200px'});
		this.img.src = wn.user_info(user).image;

		$btn($a($td(this.tab, 0, 0), 'div', '', {marginTop:'11px'}), 'Change Image', this.change_image);

		this.make_form();
		this.load_details();
	}
	
	this.load_details = function() {
		$c_page('home','profile_settings','get_user_details','',function(r, rt) {
			me.form.set_values(r.message);
		})
	}
	
	//
	// form
	//
	this.make_form = function() {
		var div = $a($td(this.tab, 0, 1), 'div');
		this.form = new wn.widgets.FieldGroup()
		this.form.make_fields(div, [
			{fieldname:'first_name', fieldtype:'Data',label:'First Name',reqd:1},
			{fieldname:'last_name', fieldtype:'Data',label:'Last Name'},
			{fieldname:'bio', fieldtype:'Text',label:'Bio'},
			{fieldname:'update', fieldtype:'Button',label:'Update'}
		]);
		
		this.form.fields_dict.update.input.onclick = function() {
			var v = me.form.get_values();
			if(v) {
				this.set_working();
				var btn = this;
				$c_page('home','profile_settings','set_user_details',v,function(r, rt) {
					btn.done_working();
				})
			}
		}
	}
	
	//
	// change password
	//
	this.change_password = function() {
		var d = new wn.widgets.Dialog({
			title:'Change Password',
			width: 400,
			fields: [
				{fieldname:'old_password', fieldtype:'Password', label:'Old Password', reqd:1 },
				{fieldname:'new_password', fieldtype:'Password', label:'New Password', reqd:1 },
				{fieldname:'new_password1', fieldtype:'Password', label:'Re-type New Password', reqd:1 },
				{fieldname:'change', fieldtype:'Button', label:'Change'}
			]
		})
		d.make();
		d.fields_dict.change.input.onclick = function() {
			var v = d.get_values();
			if(v) {
				if(v.new_password != v.new_password1) {
					msgprint('Passwords must match'); return;
				}
				this.set_working();
				$c_page('home','profile_settings','change_password',v,function(r,rt) {
					if(!r.message && r.exc) { msgprint(r.exc); return; }
					d.hide();
				})
			}
		}
		d.show();
	}
	
	//
	// change image
	//
	
	this.change_image = function() {
		var d = new wn.widgets.Dialog({
			title: 'Set your Profile'
		});
		
		wn.upload.make({
			parent: d.body,
			args: {
				method: 'home.page.profile_settings.profile_settings.set_user_image'
			},
			callback: function(fid) {
				if(fid) {
					d.hide();
					wn.boot.user_info[user].image = 'files/' + fid;
					pscript.myprofile.img.src = 'files/' + fid;
				}
			}
		});
		d.show();
	}
	
	this.change_background = function() {
		var d = new wn.widgets.Dialog({
			title: 'Set Background Image'
		})

		wn.upload.make({
			parent: d.body,
			args: {
				method: 'home.page.profile_settings.profile_settings.set_user_background'
			},
			callback: function(fid) {
				if(fid) {
					d.hide();
					erpnext.set_user_background(fid);		
				}				
			}
		});				
		d.show();
	}
	this.make();
}