pscript['onload_My Company'] = function() {
	var wrapper = page_body.pages['My Company'];
	
	// body
	wrapper.head = new PageHeader(wrapper, 'People');
	wrapper.body = $a(wrapper, 'div', '', {marginRight:'11px', marginTop:'11px'});
	
	wrapper.message = $a(wrapper.body, 'div');
	wrapper.tab = make_table(wrapper.body, 1, 2, '100%', ['25%','75%']);
	
	$y(wrapper.tab, {tableLayout:'fixed'})
	
	pscript.myc_make_toolbar(wrapper);
	pscript.myc_make_list(wrapper);
	
	if(pscript.is_erpnext_saas) {
		pscript.myc_show_erpnext_message();
	}
}

pscript.myc_make_toolbar = function(wrapper) {
	if(has_common(user_roles, ['System Manager', 'Administrator'])) {
		wrapper.head.add_button('Add User', pscript.myc_add_user)	
	}
}

//
// Only for erpnext product - show max users allowed
//
pscript.myc_show_erpnext_message = function() {
	var callback = function(r, rt) {
		if(r.exc) {msgprint(r.exc); return;}
		$a(wrapper.message, 'div', 'help_box', '', 'You have ' + r.message.enabled 
		+ ' users enabled out of ' + r.message.max_user 
		+ '. Go to <a href="javascript:pscript.go_to_account_settings()">Account Settings</a> to increase the number of users');
	}
	$c_page('my_company', 'my_company', 'get_max_users', '', callback)
}

//
// Add user dialog and server call
//
pscript.myc_add_user = function() {
	var d = new wn.widgets.Dialog({
		title: 'Add User',
		width: 400,
		fields: [
			{fieldtype:'Data', fieldname:'user',reqd:1,label:'Email Id of the user to add'},
			{fieldtype:'Button', label:'Add', fieldname:'add'}
		]
	});
	d.make();
	d.fields_dict.add.input.onclick = function() {
		v = d.get_values();
		if(v) {
			d.fields_dict.add.input.set_working();
			$c_page('my_company', 'my_company', 'add_user', v, function(r,rt) {
				if(r.exc) { msgprint(r.exc); return; }
				else {
					d.hide();
					pscript.myc_refresh();
				}
			})
		}
	}
	d.show();
}

pscript.myc_refresh = function() {
	page_body.pages['My Company'].member_list.lst.run();	
}

pscript.myc_make_list= function(wrapper) {
	wrapper.member_list = new MemberList(wrapper)
}

pscript.get_fullname=function(uid) {
	if(uid=='Administrator') return uid;
	return page_body.pages['My Company'].member_list.member_items[uid].fullname;		
}



//=============================================

MemberList = function(parent) {
	var me = this;
	this.profiles = {};
	this.member_items = {};
	this.role_objects = {};
	this.cur_profile = null;
	
	this.list_wrapper = $a($td(parent.tab,0,0), 'div', '', {marginLeft:'11px'});
	this.profile_wrapper = $a($td(parent.tab,0,1), 'div', 'layout_wrapper', {marginLeft:'0px', height:'100%'});
	
	this.no_user_selected = $a(this.profile_wrapper, 'div', 'help_box', null, 'Please select a user to view profile');
	
	this.make_search();
	if(pscript.online_users) {
		this.make_list();		
	} else {
		$c_page('event_updates', 'event_updates', 'get_online_users', '', function(r,rt) {
			pscript.online_users = r.message;
			me.make_list();
		})
	}
}

// ----------------------

MemberList.prototype.make_search = function() {
	var me = this;
	this.search_area = $a(this.list_wrapper, 'div', '', {textAlign:'center', padding:'8px'});
	this.search_inp = $a(this.search_area, 'input', '', {fontSize:'14px', width:'80%'});
	this.search_inp.set_empty = function() {
		this.value = 'Search'; $fg(this,'#888');
	}
	this.search_inp.onfocus = function() {
		$fg(this,'#000');
		if(this.value=='Search')this.value = '';
	}
	this.search_inp.onchange = function() {
		if(!this.value) this.set_empty();
	}
	this.search_inp.set_empty();
}

// ----------------------

MemberList.prototype.make_list = function() {
	var me = this;
	this.lst_area = $a(this.list_wrapper, 'div');
	this.lst = new Listing('Profiles',1);
	this.lst.colwidths = ['100%'];
	this.lst.opts.cell_style = {padding:'0px'}
	this.lst.get_query = function() {
		var c1 = '';
		if(me.search_inp.value && me.search_inp.value != 'Search') {
			var c1 = repl(' AND (first_name LIKE "%(txt)s" OR last_name LIKE "%(txt)s" OR name LIKE "%(txt)s")', {txt:'%' + me.search_inp.value + '%'});
		}
		
		this.query = repl("SELECT distinct ifnull(name,''), ifnull(concat_ws(' ', first_name, last_name),''), ifnull(messanger_status,''), ifnull(gender,''), ifnull(file_list,''), 0, enabled from tabProfile where docstatus != 2 AND name not in ('Guest','Administrator') %(cond)s ORDER BY name asc",{cond:c1});
	}
	this.lst.make(this.lst_area);
	this.lst.show_cell= function(cell, ri, ci, d) {
		me.member_items[d[ri][0]] = new MemberItem(cell, d[ri], me);
	}
	this.lst.run();
}


/*
Create / show profile
*/
MemberList.prototype.show_profile = function(uid, member_item) {
	$dh(this.no_user_selected);

	// if not exists, create
	if(!this.profiles[uid]) {
		if(!member_item) member_item = this.member_items[uid];
		this.profiles[uid] = new MemberProfile(this.profile_wrapper, uid, member_item);		
	}

	// hide current
	if(this.cur_profile)
		this.cur_profile.hide();
	
	// show this
	this.profiles[uid].show();
	this.cur_profile = this.profiles[uid];
}


// Member Item
// List item of all profiles
// on the left hand sidebar of the page

MemberItem = function(parent, det, mlist) {
	var me = this;
	this.det = det;
	this.wrapper = $a(parent, 'div');
	this.enabled = det[6];
	
	this.tab = make_table(this.wrapper, 1,2,'100%', ['20%', '70%'], {padding:'4px', overflow:'hidden'});
	$y(this.tab, {tableLayout:'fixed', borderCollapse:'collapse'})
	
	this.is_online = function() {
		for(var i=0;i<pscript.online_users.length;i++) {
			if(det[0]==pscript.online_users[i][0]) return true;
		}
	}
	
	this.refresh_name_link = function() {
		// online / offline
		$fg(this.name_link,'#00B'); 
		if(!this.is_online())
			$fg(this.name_link,'#444');
		if(!this.enabled)
			$fg(this.name_link,'#777'); 

	}
	
	this.set_image = function() {
		// image
		this.img = $a($td(this.tab,0,0),'img','',{width:'41px'});
		set_user_img(this.img, det[0], null, 
			(det[4] ? det[4].split(NEWLINE)[0].split(',')[1] : ('no_img_' + (det[3]=='Female' ? 'f' : 'm'))));		
	}
	
	// set other details like email id, name etc
	this.set_details = function() {
		// name
		this.fullname = det[1] ? det[1] : det[0];
		var div = $a($td(this.tab, 0, 1), 'div', '', {fontWeight: 'bold',padding:'2px 0px'});
		this.name_link = $a(div,'span','link_type');
		this.name_link.innerHTML = this.fullname;
		this.name_link.onclick = function() {
			mlist.show_profile(me.det[0], me);
		}

		// "you" tag
		if(user==det[0]) {
			var span = $a(div,'span','',{padding:'2px' ,marginLeft:'3px'});
			span.innerHTML = '(You)'
		}

		// email id
		var div = $a($td(this.tab, 0, 1), 'div', '', {color: '#777', fontSize:'11px'});
		div.innerHTML = det[0];

		// working img
		var div = $a($td(this.tab, 0, 1), 'div');
		this.working_img = $a(div,'img','',{display:'none'}); 
		this.working_img.src = 'images/ui/button-load.gif';
		
		this.refresh_name_link();
		
	}
	
	this.select = function() {
		$(this.wrapper).addClass('my-company-member-item-selected');
	}

	this.deselect = function() {
		$(this.wrapper).removeClass('my-company-member-item-selected');		
	}
	
	this.set_image();
	this.set_details();
	
	// show initial
	if(user==det[0]) me.name_link.onclick();
}


//
// Member Profile
// shows profile with Photo and conversation
//
MemberProfile = function(parent, uid, member_item) {
	this.parent = parent;
	this.uid = uid;
	this.member_item = member_item;
	var me = this;

	// make the UI 
	this.make = function() {
		this.wrapper = $a(this.parent, 'div', '', {display:'none'});
		this.tab = make_table(this.wrapper, 3, 2,'100%',['120px',null],{padding:'3px'});
		$y(this.tab, {tableLayout: 'fixed'});
		
		this.make_image_and_bio();
		this.make_toolbar();
		this.make_message_list();
	}
	
	// create elements
	this.make_image_and_bio = function() {
		var rh = $td(this.tab, 0, 1);
		
		// image
		this.img = $a($td(this.tab, 0, 0), 'img','',{width:'80px', marginLeft:'10px'});
		set_user_img(this.img, this.uid);

		// details
		this.name_area = $a(rh, 'div' , 'my-company-name-head');
		var div = $a(rh, 'div', 'my-company-email');
		this.email_area = $a(div, 'span');
		this.online_status_area = $a(div, 'span', 'my-company-online-status');
		this.bio_area = $a(rh, 'div', 'my-company-bio');	
		this.toolbar_area = $a(rh, 'div', 'my-company-toolbar');	
		this.status_span = $a(this.toolbar_area, 'span', '', {marginRight:'7px'});
		
	}
	
	// the toolbar
	this.make_toolbar = function() {
		if(has_common(['Administrator','System Manager'],user_roles)) {
			var roles_btn = $btn(this.toolbar_area, 'Set Roles', function() { me.show_roles() },{marginRight:'3px'});
			var delete_btn = $btn(this.toolbar_area, 'Delete User', function() { me.delete_user(); },{marginRight:'3px'});
		}
	}
	
	// create the role object
	this.show_roles = function() {
		if(!this.role_object)
			this.role_object = new RoleObj(this.uid);
		this.role_object.dialog.show();
	}
	
	// delete user
	// create a confirm dialog and call server method
	this.delete_user = function() {
		var cp = locals['Control Panel']['Control Panel'];

		var d = new Dialog(400,200,'Delete User');
		d.make_body([
			['HTML','','Do you really want to remove '+this.uid+' from system?'],['Button','Delete']
		]);
		d.onshow = function() {
			this.clear_inputs();
		}

		d.widgets['Delete'].onclick = function() {
			this.set_working();

			var callback = function(r,rt) {
				d.hide();
				if(r.exc) {
					msgprint(r.exc);
					return;
				}
				pscript.myc_refresh()
				msgprint("User Deleted Successfully");
			}
			$c_page('my_company', 'my_company', 'delete_user', {'user': me.uid}, callback);
		}
		d.show();
	}

	// set enabled
	this.set_enable_button = function() {
		var me = this;
		var act = this.profile.enabled ? 'Disable' : 'Enable';

		if(this.status_button) {
			this.status_button.innerHTML = act;	
		} else {	
			// make the button
			this.status_button = $btn(this.toolbar_area, act, function() {
				var callback = function(r,rt) {
					locals['Profile'][me.profile.name].enabled = cint(r.message);
					me.status_button.done_working();
					me.refresh_enable_disable();
				}
				this.set_working();
				$c_page('my_company','my_company', this.innerHTML.toLowerCase()+'_profile',me.profile.name, callback);
			}, null, null, 1);
		}
		if(this.uid==user) $dh(this.status_button); else $di(this.status_button);
	}
	
	// render the details of the user from Profile
	this.render = function() {
		this.profile = locals['Profile'][uid];
		scroll(0, 0);

		// name
		if(cstr(this.profile.first_name) || cstr(this.profile.last_name)) {
			this.fullname = cstr(this.profile.first_name) + ' ' + cstr(this.profile.last_name);
		} else {
			this.fullname = this.profile.name;
		}
		this.name_area.innerHTML = this.fullname;
		
		// email
		this.email_area.innerHTML = this.profile.name;

		// online / offline
		this.online_status_area.innerHTML = (this.member_item.is_online() ? '(Online)' : '(Offline)')
		if(this.member_item.is_online()) {
			$y(this.online_status_area, {color:'green'});
		}

		// refresh enable / disabled
		this.refresh_enable_disable();

		// designation
		this.bio_area.innerHTML = this.profile.designation ? ('Designation: ' + cstr(this.profile.designation) + '<br>') : '';
		this.bio_area.innerHTML += this.profile.bio ? this.profile.bio : 'No bio';
		
		new MemberConversation(this.wrapper, this.profile.name, this.fullname);
	}
	
	// refresh enable / disable
	this.refresh_enable_disable = function() {
		this.profile = locals['Profile'][this.uid]

		if(!this.profile.enabled) {
			$fg(this.name_area,'#999');
		} else {
			$fg(this.name_area,'#000');
		}

		this.member_item.enabled = this.profile.enabled;
		this.member_item.refresh_name_link();
		
		this.status_span.innerHTML = this.profile.enabled ? 'Enabled' : 'Disabled';

		// set styles and buttons
		if(has_common(['Administrator','System Manager'],user_roles)) {
			this.set_enable_button();
		}		
	}
	
	// Load user profile (if not loaded)
	this.load = function() {
		if(locals['Profile'] && locals['Profile'][uid]) {
			this.render();
			return;
		}
		var callback = function(r,rt) {
			$dh(me.member_item.working_img);
			$ds(me.wrapper);
			me.loading = 0;
			me.render();
		}
		$ds(this.member_item.working_img);
		$dh(this.wrapper);
		this.loading = 1;
		$c('webnotes.widgets.form.getdoc', {'name':this.uid, 'doctype':'Profile', 'user':user}, callback);	// onload		
	}
	
	// show / hide
	this.show = function() {
		if(!this.loading)$ds(this.wrapper);

		// select profile
		this.member_item.select();
	}
	this.hide = function() {
		$dh(this.wrapper);

		// select profile
		this.member_item.deselect();
	}
	
	this.make_message_list = function() {
		
	}
	
	this.make();
	this.load();
}




// Member conversation
// Between the current user and the displayed profile
// or if same, then the conversation with all other
// profiles
MemberConversation = function(parent, uid, fullname) {
	var me = this;
	this.wrapper = $a(parent, 'div', 'my-company-conversation');
	this.fullname = fullname;
	this.make = function() {
		if(user!=uid) {
			this.make_input();			
		}
		this.make_list();
		
		// set all messages
		// as "read" (docstatus = 0)
		if(user==uid) {
			$c_page('my_company', 'my_company', 'set_read_all_messages', '', function(r,rt) { });	
		}
	}
	
	this.make_input = function() {
		this.input_wrapper = $a(this.wrapper, 'div', 'my-company-input-wrapper');
		var tab = make_table(this.input_wrapper, 1, 2, '100%', ['64%','36%'], {padding: '3px'})
		this.input = $a($td(tab,0,0), 'textarea');
		$(this.input).add_default_text( 'Send a message to ' + fullname);

		// button
		var div = $a(this.input_wrapper, 'div');
		this.post = $btn(div, 'Post'.bold(), function() { me.post_message(); }, {margin:'0px 13px 0px 3px'})
		this.post.set_disabled();
		this.input.onkeyup = this.input.onchange = function() {
			if(this.value) {
				me.post.set_enabled();
			} else {
				me.post.set_disabled();
			}
		}

		// notification check
		this.notify_check = $a_input(div, 'checkbox', null);
		$a(div, 'span', '', {marginLeft:'3px'}, 'Notify ' + fullname + ' by email')
	}
	
	this.post_message = function() {
		if(me.input.value==$(me.input).attr('default_text')) {
			msgprint('Please write a message first!'); return;
		}
		this.post.set_working();
		$c_page('my_company', 'my_company', 'post_comment', {
			uid: uid,
			comment: $(me.input).val(),
			notify: me.notify_check.checked ? 1 : 0
		}, function(r,rt) {
			$(me.input).val("").blur();
			me.post.done_working();
			if(r.exc) { msgprint(r.exc); return; }
			me.notify_check.checked = false;
			me.refresh();
		})
	}
	
	this.make_list = function() {
		this.lst_area = $a(this.wrapper, 'div', 'my-company-conversation', {padding:'7px 13px'});

		if(user==uid) {
			this.my_messages_box = $a(this.lst_area, 'div', 'my-company-conversation-head', {marginBottom:'7px'}, 'Messages by everyone to me<br>To send a message, click on the user on the left')
		}
		
		this.lst = new wn.widgets.Listing({
			parent: this.lst_area,
			no_result_message: (user==uid 
				? 'No messages by anyone yet' 
				: 'No messages yet. To start a conversation post a new message'),

			get_query: function() {
				if(uid==user) {
					return repl("SELECT comment, owner, comment_docname, creation, docstatus " +
					"FROM `tabComment Widget Record` "+
					"WHERE comment_doctype='My Company' " +
					"AND comment_docname='%(user)s' " +
					"ORDER BY creation DESC ", {user:user});

				} else {
					return repl("SELECT comment, owner, comment_docname, creation, docstatus " +
					"FROM `tabComment Widget Record` "+
					"WHERE comment_doctype='My Company' " +
					"AND ((owner='%(user)s' AND comment_docname='%(uid)s') " +
					"OR (owner='%(uid)s' AND comment_docname='%(user)s')) " +
					"ORDER BY creation DESC ", {uid:uid, user:user});

				}
			},
			render_row: function(parent, data) {
				new MemberCoversationComment(parent, data, me);
			},
			
		})
		this.refresh();
	}
	
	this.refresh = function() {
		me.lst.run()
	}
	
	this.make();
}

MemberCoversationComment = function(cell, det, conv) {
	var me = this;
	this.det = det;
	this.wrapper = $a(cell, 'div', 'my-company-comment-wrapper');
	this.comment = $a(this.wrapper, 'div', 'my-company-comment');

	this.user = $a(this.comment, 'span', 'link_type', {fontWeight:'bold'}, pscript.get_fullname(det[1]));
	this.user.onclick = function() {
		page_body.pages['My Company'].member_list.show_profile(me.det[1]);
	}

	var st = (!det[4] ? {fontWeight: 'bold'} : null);
	this.msg = $a(this.comment, 'span', 'social', st, ': ' + det[0]);

	if(det[1]==user) {
		$y(this.wrapper, {backgroundColor: '#D9D9F3'});
	}
	this.timestamp = $a(this.wrapper, 'div', 'my-company-timestamp', '', comment_when(det[3]));
}







// ========================== Role object =====================================

pscript.all_roles = null;

RoleObj = function(profile_id){
	this.roles_dict = {};
	this.profile_id = profile_id;
	this.setup_done = 0;

	var d = new Dialog(500,500,'Assign Roles');
	d.make_body([
		['HTML','roles']
	]);
	
	this.dialog = d;
	this.make_role_body(profile_id);
	this.make_help_body();
	
	this.body.innerHTML = '<span style="color:#888">Loading...</span> <img src="images/ui/button-load.gif">'
	var me=this;

	d.onshow = function() {
		if(!me.setup_done)
			me.get_all_roles(me.profile_id);
	}
}

// make role body
RoleObj.prototype.make_role_body = function(id){
	var me = this;
	var d = this.dialog;
	this.role_div = $a(d.widgets['roles'],'div');
	
	this.head = $a(this.role_div,'div','',{marginLeft:'4px', marginBottom:'4px',fontWeight:'bold'});
	this.body = $a(this.role_div,'div');
	this.footer = $a(this.role_div,'div');
	
	this.update_btn = $btn(this.footer,'Update',function() { me.update_roles(me.profile_id); },{marginRight:'4px'},'',1);	
}

// make help body
RoleObj.prototype.make_help_body = function(){
	var me = this;
	
	var d = this.dialog;
	this.help_div = $a(d.widgets['roles'],'div');
	
	var head = $a(this.help_div,'div');	this.help_div.head = head;
	var body = $a(this.help_div,'div');	this.help_div.body = body;
	var tail = $a(this.help_div,'div');	this.help_div.tail = tail;
	
	var back_btn = $btn(tail,'Back', function() {
		// back to assign roles
		$(me.role_div).slideToggle('medium');
		$(me.help_div).slideToggle('medium');
	});
	this.help_div.back_btn = back_btn;
	$dh(this.help_div);
}

// get all roles
RoleObj.prototype.get_all_roles = function(id){
	if(pscript.all_roles) {
		this.make_roles(id);
		return;
	}

	var me = this;
	var callback = function(r,rt){
		pscript.all_roles = r.message;
		me.make_roles(id);
	}
	$c_obj('Company Control','get_all_roles','',callback);
}

// make roles
RoleObj.prototype.make_roles = function(id){
	var me = this;
	var list = pscript.all_roles;
	me.setup_done = 1;
	me.body.innerHTML = '';
		
	var tbl = make_table( me.body, cint(list.length / 2) + 1,4,'100%',['5%','45%','5%','45%'],{padding:'4px'});
	var in_right = 0; var ridx = 0;

	for(i=0;i<list.length;i++){
		var cidx = in_right * 2;
		
		me.make_checkbox(tbl, ridx, cidx, list[i]);
		me.make_label(tbl, ridx, cidx + 1, list[i]);

		// change column
		if(in_right) {in_right = 0; ridx++ } else in_right = 1;
	}
	me.get_user_roles(id);
}

// make checkbox
RoleObj.prototype.make_checkbox = function(tbl,ridx,cidx, role){
	var me = this;
	
	var a = $a_input($a($td(tbl, ridx, cidx),'div'),'checkbox');
	a.role = role;
	me.roles_dict[role] = a;
	
	$y(a,{width:'20px'});
	$y($td(tbl, ridx, cidx),{textAlign:'right'});
}


// make label
RoleObj.prototype.make_label = function(tbl, ridx, cidx, role){
	var me = this;
	
	var t = make_table($td(tbl, ridx, cidx),1,2,null,['16px', null],{marginRight:'5px'});
	var ic = $a($td(t,0,0), 'img','',{cursor:'pointer', marginRight:'5px'});
	ic.src= 'images/icons/help.gif';
	ic.role = role;
		
	ic.onclick = function(){
		me.get_permissions(this.role);
	}
	$td(t,0,1).innerHTML= role;
	
}

// get user roles
RoleObj.prototype.get_user_roles = function(id){
	var me = this;
	me.head.innerHTML = 'Roles for ' + id;
	
	$ds(me.role_div);
	$dh(me.help_div);
	
	var callback = function(r,rt){
			me.set_user_roles(r.message);
	}
	$c_obj('Company Control','get_user_roles', id,callback);
}


// set user roles
RoleObj.prototype.set_user_roles = function(list){
	var me = this;
	for(d in me.roles_dict){
		me.roles_dict[d].checked = 0;
	}
	for(l=0; l<list.length; l++){
		me.roles_dict[list[l]].checked = 1;
	}
}


// update roles
RoleObj.prototype.update_roles = function(id){
	var me = this;
	
	
	if(id == user && has_common(['System Manager'], user_roles) && !me.roles_dict['System Manager'].checked){
		var callback = function(r,rt){
			if(r.message){
				if(r.message > 1){
					var c = confirm("You have unchecked the System Manager role.\nYou will lose administrative rights and will not be able to set roles.\n\nDo you want to continue anyway?");
					if(!c) return;
				}
				else{
					var c = "There should be atleast one user with System Manager role.";
					me.roles_dict['System Manager'].checked = 1;
				}
			}
			me.set_roles(id);
		}
		$c_obj('Company Control','get_sm_count','',callback);
	}
	else{
		me.set_roles(id);
	}
}

// set roles
RoleObj.prototype.set_roles = function(id){

	var me = this;
	var role_list = [];
	
	for(d in me.roles_dict){
		if(me.roles_dict[d].checked){
			role_list.push(d);
		}
	}

	var callback = function(r,rt){
		me.update_btn.done_working();
		me.dialog.hide();
	}
	var arg = {'usr':id, 'role_list':role_list};
	me.update_btn.set_working();
	$c_obj('Company Control','update_roles',docstring(arg), callback);

}

// get permission
RoleObj.prototype.get_permissions = function(role){
	var me = this;
	
	var callback = function(r,rt){
		$(me.help_div).slideToggle('medium');
		$(me.role_div).slideToggle('medium');
		me.set_permissions(r.message, role);
	}
	$c_obj('Company Control','get_permission',role,callback);
}


// set permission
RoleObj.prototype.set_permissions = function(perm, role){
	var me = this;
	me.help_div.body.innerHTML ='';
	
	if(perm){
		me.help_div.head.innerHTML = 'Permissions for ' + role + ':<br><br>';
		
		perm_tbl = make_table(me.help_div.body,cint(perm.length)+2,7,'100%',['30%','10%','10%','10%','10%','10%','10%'],{padding:'4px'});
		
		var head_lst = ['Document','Read','Write','Create','Submit','Cancel','Amend'];

		for(var i=0; i<(head_lst.length-1);i++){
			$td(perm_tbl,0,i).innerHTML= "<b>"+head_lst[i]+"</b>";
		}
		var accept_img1 = 'images/icons/accept.gif';
		var cancel_img1 =	'images/icons/cancel.gif';

		for(i=1; i<perm.length+1; i++){
			$td(perm_tbl,i,0).innerHTML= get_doctype_label(perm[i-1][0]);
			
			for(var j=1;j<(head_lst.length-1);j++){
				
				if(perm[i-1][j]){
					var accept_img = $a($td(perm_tbl,i,j), 'img');	accept_img.src= accept_img1;
				}
				else { 
					var cancel_img = $a($td(perm_tbl,i,j), 'img'); cancel_img.src= cancel_img1;
				}
				$y($td(perm_tbl,i,j),{textAlign:'center'});
			}
		}
	}
	else
		me.help_div.head.innerHTML = 'No Permission set for ' + role + '.<br><br>';
}
