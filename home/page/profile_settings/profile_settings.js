pscript['onload_profile-settings'] = function() {
	var wrapper = page_body.pages['profile-settings'];
	wrapper.className = 'layout_wrapper';
	pscript.myprofile = new MyProfile(wrapper)
}

MyProfile = function(wrapper) {
	this.wrapper = wrapper;
	var me = this;
	
	this.make = function() {
		this.head = new PageHeader(this.wrapper, 'My Profile Settings');
		this.head.add_button('Change Password', this.change_password)
		this.tab = make_table($a(this.wrapper, 'div', '', {marginTop:'19px'}), 
			1, 2, '90%', ['50%', '50%'], {padding:'11px'})
		this.img = $a($td(this.tab, 0, 0), 'img');
		set_user_img(this.img, user);

		$btn($a($td(this.tab, 0, 0), 'div', '', {marginTop:'11px'}), 'Change Image', this.change_image)

		this.make_form();
		this.load_details();
	}
	
	this.load_details = function() {
		$c_page('event_updates','profile_settings','get_user_details','',function(r, rt) {
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
			{fieldname:'last_name', fieldtype:'Data',label:'Last Name',reqd:1},
			{fieldname:'bio', fieldtype:'Text',label:'Bio'},
			{fieldname:'update', fieldtype:'Button',label:'Update'}
		]);
		
		this.form.fields_dict.update.input.onclick = function() {
			var v = me.form.get_values();
			if(v) {
				this.set_working();
				var btn = this;
				$c_page('event_updates','profile_settings','set_user_details',v,function(r, rt) {
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
				$c_page('event_updates','profile_settings','change_password',v,function(r,rt) {
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
		if(!me.change_dialog) {

			var d = new Dialog(400,200,'Set Your Profile Image');
			d.make_body([
				['HTML','wrapper']
			]);	

			var w = d.widgets['wrapper'];
			me.uploader = new Uploader(w, {thumbnail:'80px', server_obj:'Company Control', method:'update_profile_image'}, pscript.user_image_upload)
			me.change_dialog = d;
		}
		me.change_dialog.show();
	}
	this.make();
}

pscript.user_image_upload = function(fid) {
	msgprint('File Uploaded');
	
	if(fid) {
		pscript.myprofile.change_dialog.hide();
		set_user_img(pscript.myprofile.img, user, null, fid);
	}
}