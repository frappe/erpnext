pscript['onload_File Browser'] = function(){
	
	// header and toolbar
	var h = new PageHeader('fb_header','File Management','Upload and share your file across users');
	//$dh(h.toolbar); $y(h.toolbar,{width:'0px', height:'0px'})
	
	if(!pscript.fb_tree)
		pscript.create_browser_tree();
	pscript.get_root_file_grps();
	
	pscript.create_action_widget();
	pscript.create_display_div();

	pscript.create_n_file_grp_obj();
	pscript.create_n_file_obj();
	pscript.create_attach_obj();
	
	pscript.get_all_roles();
	
	$ds(pscript.gen_div);
	$dh(pscript.grp_div);
	$dh(pscript.file_div);
	
	$ds($i('unselect'));
}

// Get all roles
pscript.get_all_roles = function(){
	if(!pscript.fg_all_roles){
		var callback = function(r,rt){
			pscript.fg_all_roles = r.message ? r.message : '';
			pscript.create_share_obj();
			pscript.fg_share.make(r.message);
		}
		$c_obj('File Browser Control','get_all_roles','',callback);
	}
}


// Creating File Browser tree.
pscript.create_browser_tree = function() {

	$i('fb_tree_div').innerHTML = '';
	var tree = new Tree($i('fb_tree_div'), '100%');
	pscript.fb_tree = tree;
	
	pscript.fb_tree.std_onclick = function(node) { /*pass*/ }		   // on click
	pscript.fb_tree.std_onexp = function(node) { /*PASS*/ }			 // on expand
	
	$ds(pscript.gen_div);
	$dh(pscript.grp_div);
	$dh(pscript.file_div);
	
	$dh(pscript.f_file_display);
}

// Creating a Share Privilege object.
pscript.create_share_obj = function(){
	
	var d = new Dialog(400,400,'Assign Privilege');
	var me = d;
	d.inputs = {};
	
	d.make_body([
		['HTML','Privilege','<div id="fg_share_div" style="overflow-y:auto; height:300px"></div>'],
		['Button','Update']
	]);
	
	
	d.make = function(all_roles){
		optn_header = make_table('fg_share_div',1,2,'100%',['60%','40%'],{padding:'4px'});

		for(var c=0;c<2;c++){
			if(c==1)
				$td(optn_header,0,c).innerHTML = '<b>Privilege</b>';
			else
				$td(optn_header,0,c).innerHTML = '<b>Role</b>';
		}
		
		optn_tbl = make_table('fg_share_div',all_roles.length,2,'100%',['60%','40%'],{padding:'4px'});
		
		for(var i=0;i<all_roles.length;i++){

			var v=$a($td(optn_tbl, i,0),'div');
			v.innerHTML=all_roles[i];

			// make select
			var sel = $a($td(optn_tbl, i,1),'select');
			add_sel_options(sel,['None','Edit','View'],'None');
			
			sel.r_nm = all_roles[i];
			d.inputs[sel.r_nm] = sel;
			
			sel.onchange = function(){}
		}
	}

	// Assigning roles in Share Privilege object.
	d.assign = function(all_roles,edit_roles,view_roles){

		if(all_roles == undefined) all_roles = '';		
		if(edit_roles == undefined) edit_roles = '';
		if(view_roles == undefined) view_roles = '';
		
		for(var i=0;i<all_roles.length;i++){
			var ele = all_roles[i];
			var sel = me.inputs[ele];
			
			if(in_list(edit_roles,ele))
				sel.value = 'Edit';
			else if(in_list(view_roles,ele))
				sel.value = 'View';
			else
				sel.value = 'None';
		}
	}
	
	//on update
	d.widgets['Update'].onclick = function(){
		var edit_roles = []; var view_roles = [];
		
		for(var i=0;i<pscript.fg_all_roles.length;i++){
			var ele = pscript.fg_all_roles[i]; var sel = me.inputs[ele];

			if(sel_val(sel) == 'Edit')
				edit_roles.push(ele)
			else if(sel_val(sel) == 'View')
				view_roles.push(ele)
		}

		var args = {}; args.name = pscript.f_cur_node_name; args.type = pscript.f_cur_node_type;
		args.edit_roles = edit_roles.join(','); args.view_roles = view_roles.join(',');
		
		$c_obj('File Browser Control','update_privileges',docstring(args),function(r,rt){me.hide();});
	}
	
	d.onshow = function(){}	
	d.onhide = function(){}
	pscript.fg_share = d;
}

// Action Widget
pscript.create_action_widget = function(){

	// General Actions.
	// new action widget
	pscript.gen_div = $i('fb_gen_action');
	
	//refresh tree
	f_refresh = $a(pscript.gen_div,'span','',{marginRight:'15px'});
	f_refresh.innerHTML = '<img src="images/icons/page_refresh.gif" style="margin-right:5px; vertical-align:middle"/><span class="link_type" style="vertical-align:middle">Refresh</span>';
	f_refresh.onclick = function(){
		pscript.fb_refresh(); 
		$dh(pscript.f_file_display);
	}

	// new group
	f_new_grp = $a(pscript.gen_div,'span','',{marginRight:'15px'});
	f_new_grp.innerHTML = '<img src="images/icons/folder.gif" style="margin-right: 5px; vertical-align:middle"><span class="link_type" style="vertical-align:middle">New</span>';
	f_new_grp.onclick = function(){ pscript.fb_show_grp(''); $ds(pscript.f_file_display); $dh($i('unselect')); }

	// Group actions.	
	pscript.grp_div = $i('fb_grp_action');
	
	// share group
	f_share_grp = $a(pscript.grp_div,'span','',{marginRight:'15px'});
	f_share_grp.innerHTML = '<img src="images/icons/user.png" style="margin-right: 5px; vertical-align:middle"><span class="link_type" style="vertical-align:middle">Share</span>';
	f_share_grp.onclick = function(){ pscript.fb_share(); }
	
	//Delete group.
	f_del_grp = $a(pscript.grp_div,'span','',{marginRight:'15px'});
	f_del_grp.innerHTML = '<img src="images/icons/cancel.gif" style="margin-right: 5px; vertical-align:middle"><span class="link_type" style="vertical-align:middle">Delete</span>';
	f_del_grp.onclick = function(){ pscript.fb_delete(); }
	
	// Add file to group.
	f_new_file = $a(pscript.grp_div,'span','',{marginRight:'15px'});
	f_new_file.innerHTML = '<img src="images/icons/page_add.gif" style="margin-right: 5px; vertical-align:middle"><span class="link_type" style="vertical-align:middle">Upload</span>';
	f_new_file.onclick = function(){ pscript.fb_create_new_file(); }
   // $dh(f_new_file);
	
	// file actions
	pscript.file_div = $i('fb_file_action');


	//share file
	f_share_file = $a(pscript.file_div,'span','',{marginRight:'15px'});
	f_share_file.innerHTML = '<img src="images/icons/user.png" style="margin-right: 5px; vertical-align:middle"><span class="link_type" style="vertical-align:middle">Share</span>';
	f_share_file.onclick = function(){ pscript.fb_share(); };
	
	// delete file
	f_del_file = $a(pscript.file_div,'span','',{marginRight:'15px'});
	f_del_file.innerHTML = '<img src="images/icons/cancel.gif" style="margin-right: 5px; vertical-align:middle"><span class="link_type" style="vertical-align:middle">Delete</span>';
	f_del_file.onclick = function(){ pscript.fb_delete(); };
	
		
	//edit file
	f_edit_file = $a(pscript.file_div,'span','',{marginRight:'15px'});
	f_edit_file.innerHTML = '<img src="images/icons/table_edit.png" style="margin-right: 5px; vertical-align:middle"><span class="link_type" style="vertical-align:middle">Edit</span>';
	f_edit_file.onclick = function(){ pscript.fb_edit_file(); };
}


// Refresh tree
pscript.fb_refresh = function(){
	pscript.create_browser_tree();
	pscript.get_root_file_grps();
	
	$ds(pscript.gen_div);
	$dh(pscript.grp_div);
	$dh(pscript.file_div);
	
	if(!pscript.f_cur_node_name){ $dh($i('unselect')); } else{ $ds($i('unselect')); }
}

// Show selected / create a new file group.
pscript.fb_show_grp = function(grp){
	var parent = pscript.f_file_display;

	if(!grp || grp == undefined){
		parent.f_file_title.innerHTML = 'New File Group';
		pscript.n_file_grp.show('');
	}
	else{
		var callback = function(r,rt){

			var grp_det = r.message ? r.message : '';

			parent.f_file_title.innerHTML = grp_det['Group Name']; 
			if(has_common(grp_det['Can Edit'].split(','),user_roles) || user==grp_det['Owner']){ $ds(pscript.grp_div); }
			else{ $dh(pscript.grp_div); }
			
			pscript.n_file_grp.show(grp_det);
		}
		$c_obj('File Browser Control','get_fg_details',grp,callback);
	}
	$ds(parent); $ds(parent.f_file_content);
}

//share privileges.
pscript.fb_share = function(){
	var callback = function(r,rt){
		pscript.fg_edit_roles = r.message[0][0] ? r.message[0][0].split(',') : '';
		pscript.fg_view_roles = r.message[0][1] ? r.message[0][1].split(',') : '';
		
		pscript.fg_share.assign(pscript.fg_all_roles,pscript.fg_edit_roles,pscript.fg_view_roles);
		pscript.fg_share.show();
	}
	var args = {};
	args.dt = pscript.f_cur_node_type;
	args.dn = pscript.f_cur_node_name;
	$c_obj('File Browser Control','get_privileges',docstring(args),callback);
}

// delete group
pscript.fb_delete = function(){
	pscript.delete_node('File Browser Control',pscript.f_cur_node_type,pscript.f_cur_node_name,'');
	$dh(pscript.f_file_display);
}

// Create a new file.
pscript.fb_create_new_file = function(){
	var parent = pscript.f_file_display;
	
	pscript.f_cur_parent = pscript.f_cur_node;
	
	parent.f_file_title.innerHTML = 'New File';
	pscript.n_file.show(0,'frm_node');
}

// If file other than image then download file.
pscript.fb_show_txt_file = function(){
	$i('file_link').href = repl('cgi-bin/getfile.cgi?ac=%(acc)s&name=%(f_nm)s',{acc:session.account_name, f_nm:pscript.f_cur_node_file});
	$i('file_link').target = "_blank";
}

// Area to display content.
pscript.create_display_div = function(){

	var d = $a($i('fb_display_div'),'div');
	
	d.f_file_title = $a(d,'div','',{fontSize:'14px',fontWeight:'bold'});
	$y($a(d,'div'),{margin:'5px 0px 5px 0px',borderBottom:'1px solid #333'});

	d.f_file_content = $a(d,'div','',{marginTop:'20px'});
	pscript.f_file_display = d;
	$dh(d);
}

// function to create a new File Group object.
pscript.create_n_file_grp_obj = function(){
	var n_file_grp = new pscript.n_file_grp_Obj();
	pscript.n_file_grp = n_file_grp;
}

// Create a new File object.
pscript.create_n_file_obj = function(){
	var n_file = new pscript.n_file_Obj();
	pscript.n_file = n_file;
}

// Create a new Attachement object.
pscript.create_attach_obj = function(){
	var attach_obj = new pscript.attach_Obj();
	pscript.attach_obj = attach_obj;
}

// File Group object.
pscript.n_file_grp_Obj = function() {
  
	this.inputs = {}; var me = this; this.fg_field_lst = [];
	
	this.make_section = function(label, tp, css) {

		var div = $a(this.wrapper,'div','',{marginBottom:'8px'});
		var t = make_table(div,1,2,'90%',['35%','65%']);

		if(tp=='button'){
			var element = $a($td(t,0,1), 'button', 'button');
			element.innerHTML = label;
		}
		else if(tp == 'link'){
			var element = make_field({fieldtype:'link', 'label':label, 'options':'File Group'}, '', $td(t,0,1), this, 0, 1);
			$y($td(t,0,1),{width:'100%'})
			element.in_filter = 1; element.refresh();
			
			$td(t,0,0).innerHTML = label;
			element.display_div = $a($td(t,0,1),'div', '', {width:'80%'});
			me.fg_field_lst.push(label);
		}
		else {
			var element = $a($td(t,0,1),tp, '', {width:'80%'});
			$td(t,0,0).innerHTML = label;
			
			element.display_div = $a($td(t,0,1),'div', '', {width:'80%'});
			$dh(element.display_div);
			me.fg_field_lst.push(label);
		}
		
		if(css){
			$y($td(t,0,0),css);
		}
		
		element.wrapper = div;
		
		if(label) me.inputs[label] = element;
		return element;
	}
  
	this.make = function() {

		this.wrapper = document.createElement('div');

		this.make_section('Group Name','input',{color:'red'});
		this.make_section('Parent Group','link');
		this.make_section('Description','textarea');
		$y(this.inputs['Description'],{height:'140px'});
		
		this.make_section('Save','button');

		// cancel
		this.inputs['Cancel'] = $a(this.inputs['Save'].parentNode, 'button', 'button');
		this.inputs['Cancel'].innerHTML = 'Cancel';
		$y(this.inputs['Cancel'], {marginLeft:'8px'});
	}
  
	this.show = function(grp_det){
		
		if(! me.wrapper) me.make();

		var field_lst = me.fg_field_lst;

		if(!grp_det || grp_det == undefined){
			pscript.fg_edit_roles = ''; pscript.fg_view_roles = ''; me.inputs['Save'].disabled = false;
		
			for(i in field_lst){
				var fld_nm = field_lst[i] ? field_lst[i] : '';
				var fld = me.inputs[fld_nm] ? me.inputs[fld_nm] : '';
				fld.display_div.innerHTML = '';
				
				if(fld_nm == 'Parent Group'){ fld.txt.value = ''; $ds(fld.input_area); }
				else{ fld.value = ''; $ds(fld); }
				
				$dh(fld.display_div); 
			}
			me.inputs['Save'].onclick = function(){ me.save(''); }
		}
		else{
			pscript.fg_edit_roles = grp_det['Can Edit'] ? grp_det['Can Edit'].split(',') : '';
			pscript.fg_view_roles = grp_det['Can View'] ? grp_det['Can View'].split(',') : '';		
			for(i in field_lst){
				var fld_nm = field_lst[i] ? field_lst[i] : '';
				var fld = me.inputs[fld_nm] ? me.inputs[fld_nm] : '';
				fld.display_div.innerHTML = grp_det[fld_nm] ? grp_det[fld_nm] : '';

				if(fld_nm == 'Parent Group') fld.txt.value = grp_det[fld_nm] ? grp_det[fld_nm] : '';
				else fld.value = grp_det[fld_nm] ? grp_det[fld_nm] : '';
									
				if(has_common(pscript.fg_edit_roles,user_roles) || user == grp_det['Owner']){
					if(fld_nm == 'Parent Group') $ds(fld.input_area); else $ds(fld); 
					$dh(fld.display_div); me.inputs['Save'].disabled = false;
				}
				else{
					if(fld_nm == 'Parent Group') $dh(fld.input_area); else $dh(fld);
					$ds(fld.display_div); me.inputs['Save'].disabled = true;
				}
			}
			me.inputs['Save'].onclick = function(){ me.save(grp_det['Name']); }
		}
		me.show_as();
		me.inputs['Cancel'].onclick = function() { me.cancel(); me.hide();}
	}
  
	this.save = function(name) {
		var grp_nm = me.inputs['Group Name'].value; grp_nm = strip(grp_nm," ");
		var parent_grp = me.inputs['Parent Group'].get_value(); parent_grp = strip(parent_grp," ");
		var desc = me.inputs['Description'].value; desc = strip(desc," ");
		
		if(grp_nm == '') msgprint('Please enter group name');
		else{ var args = {}; args.grp_nm = grp_nm; args.parent_grp = parent_grp; args.desc = desc; }
		
		if(!name || name == undefined){
			args.name = '';
			var callback = function(r,rt){
				pscript.f_cur_node_name = r.message ? r.message : '';
				pscript.fb_show_grp(pscript.f_cur_node_name);
				pscript.fb_refresh();
				//if(!pscript.f_cur_parent){ pscript.fb_refresh(); pscript.f_cur_node_name = }
				//else{ pscript.load_child_nodes(); }
			}
			$c_obj('File Browser Control','create_new_grp',docstring(args),callback);
		}
		else{
			args.name = name;
			var callback = function(r,rt){
				var grp = r.message ? r.message : '';
				pscript.fb_show_grp(grp);
				pscript.fb_refresh();
			}
			$c_obj('File Browser Control','update_grp',docstring(args),callback);
		}
		
	}
  
	this.cancel = function(){
		$dh(pscript.f_file_display);this.hide();
	}
  
	this.show_as = function() {
		if(me.wrapper.parentNode) me.wrapper.parentNode.removeChild(me.wrapper);
		
		var parent = pscript.f_file_display;
		pscript.remove_child_nodes(parent.f_file_content);

		parent.f_file_content.appendChild(me.wrapper);
		$ds(pscript.f_file_display); $ds(me.wrapper);
	}
  
	this.hide = function() {
		$dh(me.wrapper); me.display = 0;
	}
}

// File Object.
pscript.n_file_Obj = function() {

	this.inputs = {};
	var me = this;
	
	this.make_section = function(label, tp, css) {

		var div = $a(this.wrapper,'div','',{marginBottom:'8px'});
		var t = make_table(div,1,2,'90%',['38%','62%']);
		
		if(tp=='button'){
			var element = $a($td(t,0,1), 'button', 'button');
			element.innerHTML = label;
		}
		else if(tp=='Note'){
			var element = $a($td(t,0,1),'span','',{color:'red'});
			element.innerHTML = 'Fields in red are mandatory.'
		}
		else if(tp=='link'){
			var element = make_field({fieldtype:'link', 'label':label, 'options':'File Group'}, '', $td(t,0,1), this, 0, 1);
			$y($td(t,0,1),{width:'100%'})
			element.in_filter = 1; element.refresh();
			
			$td(t,0,0).innerHTML = label;
			element.display_div = $a($td(t,0,1),'div', '', {width:'80%'});
			element.txt.onchange = function(){ pscript.set_file_det_value(pscript.attach_obj,pscript.n_file); }
		}
		else {
			var element = $a($td(t,0,1),tp, '', {width:'95%'});
			$td(t,0,0).innerHTML = label;
			element.onchange = function(){ pscript.set_file_det_value(pscript.attach_obj,pscript.n_file); }
		}

		//---css to label---
		if(css){
			$y($td(t,0,0),css);
		}
	
		element.wrapper = div;
		
		if(label) me.inputs[label] = element;
		return element;
	}

	this.make = function() {

		this.wrapper = document.createElement('div');
		
		// note
		this.make_section('','Note');
		
		// upload area
		this.ul_area = $a(this.wrapper,'div','',{marginBottom:'8px'});
		$dh(this.ul_area);
		
		// file group and description
		this.make_section('File Group','link',{color:'red'});
		this.make_section('Description','textarea');
		$y(this.inputs['Description'],{height:'140px'});

		//save
		this.make_section('Save','button');$dh(this.inputs['Save']);

		// cancel
		this.inputs['Cancel'] = $a(this.inputs['Save'].parentNode, 'button', 'button');
		this.inputs['Cancel'].innerHTML = 'Cancel'; $dh(this.inputs['Cancel']);
		$y(this.inputs['Cancel'], {marginLeft:'8px'});
	}
  
	this.show = function(edit,frm){
		if(! me.wrapper) me.make();
		
		if(edit){
			var callback1 = function(r,rt){
				file_det = r.message;
			
				me.inputs['Description'].value = file_det['description'] ? file_det['description'] : '';
				me.inputs['File Group'].txt.value = file_det['file_group'] ? file_det['file_group'] : '';

				pscript.f_cur_node_file = file_det['file_list'] ? file_det['file_list'].split(NEWLINE)[0].split(',')[1] : '';

				me.inputs['Save'].file_id = file_det['name'] ? file_det['name'] : '';
				me.inputs['Save'].onclick = function(){ me.save(this.file_id);}
				pscript.attach_obj.show(me, me.ul_area, 1, file_det);
			}
			$ds(me.ul_area); $di(me.inputs['Save']); $di(me.inputs['Cancel']);
			$c_obj('File Browser Control','get_file_details',pscript.f_cur_node_name,callback1);
		}
		else{
			$ds(me.ul_area); $dh(me.inputs['Save']); $dh(me.inputs['Cancel']);

			me.inputs['Description'].value = '';
			if(frm == 'frm_node') me.inputs['File Group'].txt.value = pscript.f_cur_node_label;
			var parent = pscript.f_file_display;
			parent.f_file_title.innerHTML = 'New File';
			
			$ds(parent);
			me.inputs['Save'].onclick = function(){ me.save('');}
			pscript.attach_obj.show(me,me.ul_area,0,'');
		}
		me.inputs['Cancel'].onclick = function() { me.cancel(); me.hide(); }
	}
  
	this.save = function(name) {

		var desc = me.inputs['Description'].value; desc = strip(desc," ");
		file_grp = me.inputs['File Group'].txt.value; file_grp = strip(file_grp," ");
		
		if(file_grp == '') msgprint('Please select file group');

		var args = {}; args.desc = desc; args.file_grp = file_grp;
		
		if(name){
			args.name = name;
			var callback = function(){
				//pscript.fb_edit_file();
				
				//refreshing parent
				pscript.load_child_nodes();
			}
			$c_obj('File Browser Control','update_file',docstring(args),callback);
		}
		else{
			args.name = ''
			var callback = function(r,rt){
				var f = eval('var a='+r.message+';a');
				
				//refreshing node
				pscript.load_child_nodes();
				
				//pscript.f_cur_node_name = f.name; pscript.f_cur_node_label = f.label;
				//pscript.fb_edit_file();
			}
			$c_obj('File Browser Control','create_new_file',docstring(args),callback);
		}
	}
  
	this.cancel = function(){
		$dh(pscript.f_file_display); this.hide();
	}
  
	this.show_as = function(edit) {
	    if(me.wrapper.parentNode) me.wrapper.parentNode.removeChild(me.wrapper);
	
		var parent = pscript.f_file_display;
		pscript.remove_child_nodes(parent.f_file_content);

		parent.f_file_content.appendChild(me.wrapper);
		$ds(pscript.f_file_display); $ds(parent.f_file_content);
		$ds(me.wrapper);
	}
  
	this.hide = function() {
		$dh(me.wrapper);
		me.display = 0;
	}
}

// File Attachement object.
pscript.attach_Obj = function(){

	var me = this;
		
	this.show = function(obj,parent,edit,dict){
		var me = this;
		if(!me.wrapper) { me.make(); }

		me.show_as(obj,parent,edit,dict);
		obj.show_as(edit);
	}

	this.make = function(){
		var me = this;
		this.wrapper = document.createElement('div');
		
		var div = $a(this.wrapper,'div',{marginBottom:'8px', border:'1px solid #AAA'});
		
		var t1 = make_table(div,1,2,'90%',['38%','62%']);
		
		lbl_area = $a($td(t1,0,0),'div');
		lbl_area.innerHTML = '<img src="images/icons/paperclip.gif"><span style="margin-left4px; color:red;">File:</span><br>';
	
		main_area = $a($td(t1,0,1),'div');
		
		this.upload_div = $a(main_area,'div');
		this.download_div = $a(main_area,'div');
			
		me.make_ul_area();
		me.make_dl_area();
	}
	
	//image upload area
	this.make_ul_area = function(){
		var me = this;
		
		this.upload_div.innerHTML = '';

		var div = $a(this.upload_div,'div');
		div.innerHTML = '<iframe id="fb_iframe" name="fb_iframe" src="blank1.html" style="width:0px; height:0px; border:0px"></iframe>';

		var div = $a(this.upload_div,'div');
		div.innerHTML = '<form method="POST" enctype="multipart/form-data" action="'+outUrl+'" target="fb_iframe"></form>';

		var ul_form = div.childNodes[0];
		
		this.upload_div.ul_form = ul_form;
		
		var f_list = [];

		// file data
		var inp_fdata = $a_input($a(ul_form,'span'),'file',{name:'filedata'});

		var inp_btn = $a_input($a(ul_form,'span'),'hidden',{name:'cmd'}); inp_btn.value = 'upload_many';
		var inp = $a_input($a(ul_form,'span'),'hidden',{name:'form_name'}); inp.value = 'File Browser';
		var inp = $a_input($a(ul_form,'span'),'submit'); inp.value = 'Upload';
		
		this.inp_file = $a_input($a(ul_form,'span'),'hidden',{name:'file_id'});
		this.file_det = $a_input($a(ul_form,'span'),'hidden',{name:'file_det'});

		inp_btn.onclick = function(){
			pscript.set_file_det_value(pscript.attach_obj,pscript.n_file);
		}
	}
	
	//download link
	this.make_dl_area = function(){
		var me = this;
		var download_tbl = make_table(this.download_div,1,2,'100%',['70%','30%']);
		
		var download_link = $a($td(download_tbl,0,0),'a','link_type');
		
		this.download_div.download_link = download_link;
		
		var remove_link = $a($td(download_tbl,0,1),'span','link_type',{textAlign:'right',marginLeft:'20px'});
		remove_link.innerHTML = 'Remove';
		
		this.download_div.remove_link = remove_link;		
	}
	
	this.show_as = function(obj,parent,edit,dict){
		var me = this;
		
		// add to parent
		if(me.wrapper.parentNode) me.wrapper.parentNode.removeChild(me.wrapper);
		parent.appendChild(me.wrapper);
		$ds(me.wrapper);
		
		if(edit){
			pscript.set_file_det_value(pscript.attach_obj,pscript.n_file);
			me.inp_file.value = dict.name ? dict.name : '';
   
			if(dict.file_list){ $dh(me.upload_div); $ds(me.download_div); }
			else{ $ds(me.upload_div); $dh(me.download_div); }
			
			// download
			me.download_div.download_link.innerHTML = dict.file_list ? dict.file_list.split(',')[0] : '';
			me.download_div.download_link.onclick = function(){
				this.href = repl('cgi-bin/getfile.cgi?ac=%(acc)s&name=%(f_nm)s',{acc:session.account_name, f_nm:pscript.f_cur_node_file});
				this.target = "_blank";
			}
			
			// remove
			me.download_div.remove_link.onclick = function(){
				$c_obj('File Browser Control','remove_file',docstring(dict),function(r,rt){
					pscript.n_file.show(0,'frm_remove');
				});
				$ds(me.upload_div); $dh(me.download_div);
			}
		}
		else{
			$ds(me.upload_div); $dh(me.download_div);
			me.inp_file.value = '';
			pscript.set_file_det_value(pscript.attach_obj,pscript.n_file);
		}
	}
}

// Get all root file groups(where Parent Group is null).
pscript.get_root_file_grps = function(){

	if (pscript.fb_tree){
		pscript.fb_tree.body.innerHTML = '';
	}
  
	var callback1 = function(r,rt){
		var cl = r.message ? r.message : ''; var n = pscript.fb_tree.allnodes[cl]; var has_children = true;
		
		for(var i=0; i<cl.length;i++){
			if(!cl[i][2] || cl[i][2] == undefined) cl[i][2] = ''; if(!cl[i][3] || cl[i][3] == undefined) cl[i][3] = '';
			if(has_common(cl[i][2].split(','),user_roles) || has_common(cl[i][3].split(','),user_roles) || user == cl[i][4]){
				var r = pscript.fb_tree.addNode(null, cl[i][0],'', pscript.show_hide_link , has_children ? pscript.fb_get_children : null, null, cl[i][1]);
				r.rec = cl[i]; r.rec.name = cl[i][0]; r.rec.label = cl[i][1]; r.rec.parent_grp = ''; r.rec.file_list = ''; r.rec.type = 'File Group';
			}
		}
	}
	$c_obj('File Browser Control','get_root_file_grps','',callback1);
}

// Onclick of a tree node will show / hide corresponding actions from action widget.
pscript.show_hide_link = function(node){

	$dh($i('unselect'));
	$dh(pscript.f_file_display);
	
	pscript.f_cur_node = node;
	
	if(node.parent){
		pscript.f_cur_parent = node.parent;
	}
	else{ pscript.f_cur_parent = ''; }
	
	pscript.f_cur_node_name = node.rec.name;

	if(node.rec.label){ pscript.f_cur_node_label = node.rec.label; }
	else{ pscript.f_cur_node_label = ''; }
	
	if(node.rec.type){ pscript.f_cur_node_type = node.rec.type; }
	else{ pscript.f_cur_node_type = ''; }
	
	if(node.rec.file_list){ pscript.f_cur_node_file = node.rec.file_list.split(NEWLINE)[0].split(',')[1]; }
	else{ pscript.f_cur_node_file = ''; }

	img_extns = ['jpg','jpeg','gif','png','biff','cgm','dpof','exif','img','mng','pcx','pic','pict','raw','tga','wmf']
	extn = node.rec.file_list ? node.rec.file_list.split(NEWLINE)[0].split(',')[0].split('.')[1] : '';

	var dsp_div = pscript.f_file_display;
	dsp_div.f_file_title.innerHTML = pscript.f_cur_node_label;

	if(node.rec.type == 'File Group'){
		$dh(pscript.file_div);
		$ds(pscript.grp_div);
		pscript.fb_show_grp(pscript.f_cur_node_name);
	}
	else if(node.rec.type == 'File'){
		$dh(pscript.grp_div);
		$ds(pscript.file_div);
		if(pscript.f_cur_node_file){
			if(inList(img_extns,extn)){
				pscript.fb_show_img();
			}
			else{
				// IE FIX
				pscript.remove_child_nodes(dsp_div.f_file_content);
				
				var div = document.createElement('div');
				div.innerHTML = '<a class="link_type" onclick="pscript.fb_show_txt_file()" id="file_link">Click to Open/ Download file.</span>';				
				dsp_div.f_file_content.appendChild(div);
				$ds(dsp_div);
			}
		}
		else{
			dsp_div.f_file_content.innerHTML = 'No attachement found.';
			$ds(pscript.f_file_display);
			
			$ds(pscript.file_div);
			$dh(pscript.grp_div);			
		}
		pscript.show_edit_file_link(node.rec.name);
	}
	else{
		$dh(pscript.grp_div);
		$dh(pscript.file_div);
	}
}

// Onexpand of a tree node get all childrens(Files / File Groups).
pscript.fb_get_children = function(node){
	if(node.expanded_once) return;
	$ds(node.loading_div);
	
	var callback = function(r,rt){
		var p = pscript.fb_tree.allnodes[r.message.parent_grp];
		$dh(node.loading_div);

		var fl = r.message.fl ? r.message.fl : '';
		if(fl){
			for(var i=0; i<fl.length; i++){
				if(fl[i][3] == undefined) fl[i][3] = '';
				if(fl[i][4] == undefined) fl[i][4] = '';
				
				if(has_common(fl[i][3].split(','),user_roles) || has_common(fl[i][4].split(','),user_roles) || (user == fl[i][5])){
					var imgsrc = 'images/icons/page.gif'; var has_children = false; 
					if(fl[i][1]) var label = fl[i][1]; else var label = fl[i][0];

					var n = pscript.fb_tree.addNode(p,fl[i][0],imgsrc,pscript.show_hide_link,has_children ? pscript.fb_get_children:null,null,label);
					n.rec = fl[i]; n.rec.name = fl[i][0]; n.rec.parent_grp = r.message.parent_grp;
					n.rec.label = fl[i][1]; n.rec.file_list = fl[i][2]; n.rec.type = 'File';
				}
			}
		}
		
		var fl_grp = r.message.fl_grp ? r.message.fl_grp : '';
		if(fl_grp){
			for(var i=0;i<fl_grp.length;i++){
				if(fl_grp[i][2] == undefined) fl_grp[i][2] = '';
				if(fl_grp[i][3] == undefined) fl_grp[i][3] = '';

				if(has_common(fl_grp[i][2].split(','),user_roles) || has_common(fl_grp[i][3].split(','),user_roles) || (user == fl_grp[i][4])){
					var imgsrc = 'images/icons/folder.gif'; var has_children = true;
					var label = fl_grp[i][1] ? fl_grp[i][1] : fl_grp[i][0];

					var n = pscript.fb_tree.addNode(p,fl_grp[i][0],imgsrc,pscript.show_hide_link,has_children ? pscript.fb_get_children:null,null,label);
					n.rec = fl_grp[i]; n.rec.name = fl_grp[i][0]; n.rec.parent_grp = r.message.parent_grp;
					n.rec.label = fl_grp[i][1]; n.rec.file_list = ''; n.rec.type='File Group';
				}
			}
		}
	}
	$c_obj('File Browser Control','get_children',node.rec.name,callback);
}

// If image file then display image.
pscript.fb_show_img = function(){

	var parent = pscript.f_file_display;

	parent.f_file_title.innerHTML = pscript.f_cur_node_label;
	pscript.remove_child_nodes(parent.f_file_content);

	var a = $a(parent.f_file_content,'a');
	
	var img = $a(a,'img','',{textAlign:'center',cursor:'pointer'}); 
	img.src = repl('cgi-bin/getfile.cgi?ac=%(acc)s&name=%(f_nm)s&thumbnail=300',{acc:session.account_name, f_nm:pscript.f_cur_node_file});
	$ds(pscript.f_file_display);

	a.onclick = function(){
		this.href = repl('cgi-bin/getfile.cgi?ac=%(acc)s&name=%(f_nm)s',{acc:session.account_name, f_nm:pscript.f_cur_node_file});
		this.target = "_blank";
	}
}

// Enable/ disable Edit File action.
pscript.show_edit_file_link = function(){
	
	var callback = function(r,rt){
			pscript.f_edit_roles = r.message[0][0] ? r.message[0][0].split(',') : '';
			pscript.f_view_roles = r.message[0][1] ? r.message[0][1].split(',') : '';
			
			if(has_common(pscript.f_edit_roles,user_roles) || user == r.message[0][2]){
				$ds(pscript.file_div);
			}
			else{ $dh(pscript.file_div); }
	}
	
	var args = {};
	args.dt = pscript.f_cur_node_type;
	args.dn = pscript.f_cur_node_name;
	$c_obj('File Browser Control','get_privileges',docstring(args),callback);
}

// Set file detail in attachement object.
pscript.set_file_det_value = function(att,file){
	if(file.inputs['Description'].value) file_desc = file.inputs['Description'].value; else file_desc = 'NIL';
	if(file.inputs['File Group'].txt.value) file_grp = file.inputs['File Group'].txt.value; else file_grp = 'NIL';
	att.file_det.value = file_desc + '~~' + file_grp;
}

// Edit selected file.
pscript.fb_edit_file = function(){
	var parent = pscript.f_file_display;
	parent.f_file_title.innerHTML = pscript.f_cur_node_label;
	pscript.n_file.show(1,'frm_node');
}

//delete dialog structure

pscript.delete_node = function(sdt,dt,dn,callback){
	if(!pscript.delete_dialog){
		var delete_dialog = new Dialog(400,200);

		delete_dialog.make_body([
			['HTML','Message',''],
			['HTML','Response',''],
			['HTML','Delete Record','<div id="delete_record" style="height:25px"></div>']
		]);
		
		delete_dialog.y_btn = $a($i('delete_record'),'button','button');
		delete_dialog.y_btn.innerHTML = 'Ok';
		delete_dialog.y_btn.onclick = function(){
			delete_dialog.widgets['Response'].innerHTML = 'Deleting...';
			var args = {};
			args.dt = delete_dialog.dt; args.dn = delete_dialog.dn;
			
			var callback1 = function(r,rt){
				delete_dialog.onhide = delete_dialog.callback;
				delete_dialog.hide();
				
				//refreshing node
				pscript.load_child_nodes();
			}
			$c_obj(sdt,'delete',docstring(args),callback1);
		}
		
		delete_dialog.n_btn = $a($i('delete_record'),'button','button');
		delete_dialog.n_btn.innerHTML = 'Cancel';
		
		delete_dialog.n_btn.onclick = function(){
			delete_dialog.widgets['Response'].innerHTML = '';
			delete_dialog.onhide = '';
			delete_dialog.hide();
		}

		delete_dialog.widgets['Message'].innerHTML = 'Note: All data will be deleted permanantly. Do you want to continue?';
		pscript.delete_dialog = delete_dialog;
	}
	//if(!delete_dialog.display) delete_dialog.show();
	pscript.delete_dialog.show();
	pscript.delete_dialog.widgets['Response'].innerHTML = '';
	pscript.delete_dialog.sdt = sdt; pscript.delete_dialog.dt=dt; pscript.delete_dialog.dn=dn; pscript.delete_dialog.callback = callback;
}

pscript.remove_child_nodes = function(parent){
	var len = parent.childNodes.length;
	if(len){
		for(l=0; l<len; l++){
			var c = parent.childNodes[0];
			parent.removeChild(c);
		}
	}
}

pscript.load_child_nodes = function(){
	if(pscript.f_cur_parent){
		pscript.f_cur_parent.clear_child_nodes();
		pscript.f_cur_parent.expand();
		pscript.f_cur_parent.select();
	}
	else{ pscript.fb_refresh(); }
}