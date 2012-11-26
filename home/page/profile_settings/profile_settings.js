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
		this.wrapper.appframe.add_button('Update', this.update_profile);
		this.wrapper.appframe.buttons["Update"].addClass("btn-info");
		this.wrapper.appframe.add_button('Change Password', this.change_password);
		
		$(this.wrapper).find('.layout-main').html("<h4>Personal</h4>\
			<div class='personal-settings' style='margin-left: 15px;'></div>\
			<hr>\
			<!--<h4>Email</h4>\
			<div class='email-settings' style='margin-left: 15px;'></div>\
			<hr>-->\
			<h4>Display</h4>\
			<div class='display-settings' style='margin-left: 15px;'>\
				<p>Change Background: <button class='btn btn-small change-background'>Upload</button></p>\
				<br><p>Change Theme: <select class='change-theme'></select></p>\
			</div>");
			
		this.make_display();
		this.make_personal();
	}
	
	this.make_display = function() {
		$(this.wrapper).find(".change-background")
			.click(me.change_background)
		
		$(this.wrapper).find(".change-theme")
			.add_options(keys(erpnext.themes).sort())
			.change(function() {
				erpnext.set_theme($(this).val());
			}).val(wn.boot.profile.defaults.theme ? 
				wn.boot.profile.defaults.theme[0] : "Default")
			.change(function() {
				wn.call({
					module: "home",
					page: "profile_settings",
					method: "set_user_theme",
					args: {theme: $(this).val() }
				})
			});
	}
	
	this.make_personal = function() {
		this.personal = $(this.wrapper).find('.personal-settings').html('<div \
			class="pull-left" style="width: 300px;">\
			<img style="max-width: 200px;" src='+wn.user_info(user).image+'><br><br>\
			<button class="btn btn-small">Change Image</button><br><br>\
			</div><div class="pull-left profile-form" style="width: 45%; margin-top: -11px;">\
			<div class="clear"></div>\
			</div>')
		
		this.personal.find("button").click(this.change_image);
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
		var div = this.personal.find(".profile-form").get(0);
		this.form = new wn.ui.FieldGroup({
			parent: div,
			fields: [
				{fieldname:'first_name', fieldtype:'Data',label:'First Name',reqd:1},
				{fieldname:'last_name', fieldtype:'Data',label:'Last Name'},
				{fieldname:'email_signature', fieldtype:'Small Text',label:'Email Signature',
					decription:'Will be appended to outgoing mail'},
			]
		});

	}
	
	this.update_profile = function() {
		var v = me.form.get_values();
		if(v) {
			$(this).set_working();
			var btn = this;
			$c_page('home','profile_settings','set_user_details',v,function(r, rt) {
				$(btn).done_working();
			})
		}		
	}

	this.change_password = function() {
		var d = new wn.ui.Dialog({
			title:'Change Password',
			width: 400,
			fields: [
				{fieldname:'old_password', fieldtype:'Password', label:'Old Password', reqd:1 },
				{fieldname:'new_password', fieldtype:'Password', label:'New Password', reqd:1 },
				{fieldname:'new_password1', fieldtype:'Password', label:'Re-type New Password', reqd:1 },
				{fieldname:'change', fieldtype:'Button', label:'Change'}
			]
		})
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
		var d = new wn.ui.Dialog({
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
					me.personal.find("img").attr("src", 'files/' + fid);
				}
			}
		});
		d.show();
	}
	
	this.change_background = function() {
		var d = new wn.ui.Dialog({
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