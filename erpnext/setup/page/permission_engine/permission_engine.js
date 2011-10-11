pscript['onload_Permission Engine'] = function() {
  // header and toolbar
  var h = new PageHeader('pe_header','Permissions Manager','Set specific permissions for Roles')
  
  if(!pscript.perm_engine) pscript.perm_engine = new pscript.PermEngine();
}


pscript.PermEngine = function() {
  // create UI elements
  this.wrapper = $i('perm_engine_div');
  
  this.head = $a(this.wrapper, 'div');
  this.body = $a(this.wrapper, 'div');
  this.footer = $a(this.wrapper, 'div');

  var lab = $a(this.body,'div', '', {backgroundColor:'#FFD', padding:'8px', margin:'16px 0px'});
  lab.innerHTML = 'Please select the item for which you want to set permissions';
  
  this.make_head();
  this.load_options();
}


// Make Head
// -------------
pscript.PermEngine.prototype.make_head = function() {
  var me = this;
  
  var make_select = function(label) {
    var w = $a(me.head, 'div', '', {margin:'8px 0px'});
    var t = make_table(w,1,2,'300px',['50%','50%']);
    $td(t,0,0).innerHTML = label;
    var s = $a($td(t,0,1),'select','',{width:'140px'});
    s.wrapper = w;
    return s;
  }
  
  var make_button = function(label, parent, green) {
  	return $btn(parent, label, null, {margin:'8px 0px', display:'none'}, (green ? 'green' : null));
  }
  
  
  // Set Permissions for
  this.type_select = make_select('Set Permissions For');
  this.type_select.onchange = function() {
  	me.get_permissions();
  }
    
  // Update Button
  this.add_button = make_button('+ Add A New Rule', this.head, 0);
  this.add_button.onclick = function() {
    me.add_permission();
  }

  // Update Button
  this.update_button = make_button('Update', this.footer, 1);
  this.update_button.onclick = function() {
    me.update_permissions();
  }
}

// Add Permissions
// -----------------
pscript.PermEngine.prototype.add_permission = function() {
  var me = this;
  if(!this.add_permission_dialog) {
  	
  	// dialog
    var d = new Dialog(400,400,'Add Permission');
    d.make_body([['Select','Role'],['Select','Level'],['Button','Add']])

    add_sel_options(d.widgets['Role'], this.roles, '');
    add_sel_options(d.widgets['Level'], [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 0);

    // add
    d.widgets['Add'].onclick = function() {
      if(!sel_val(d.widgets['Role'])) {
        msgprint('Please select Role'); return;
      }
      var callback = function(r, rt) {
      	// reload
        me.get_permissions();
        d.hide();
      }
      $c_obj('Permission Control','add_permission',JSON.stringify([sel_val(me.type_select), sel_val(d.widgets['Role']), sel_val(d.widgets['Level'])]), callback);
    }

    this.add_permission_dialog = d;
  }
  this.add_permission_dialog.show();
}


// Hide Fields
// -----------------
pscript.PermEngine.prototype.hide_fields = function() {
  $dh(this.role_select.wrapper);
  this.type_select.disabled = false;
  this.body.innerHTML = '';
}


// Load Roles And Modules
// -----------------------
pscript.PermEngine.prototype.load_options = function() {
  var me = this;
  $dh(me.update_button);
  $dh(me.add_button);

  $c_obj('Permission Control','get_doctype_list','', function(r,rt) {    
    me.roles = r.message.roles;
    
    // Type
    empty_select(me.type_select);
    add_sel_options(me.type_select,add_lists([''], r.message.doctypes));
    
  });
}


// Get DocType and Permissions related to module
// --------------------------------------------------
pscript.PermEngine.prototype.get_permissions = function() {
  var me = this;
  
  if(!sel_val(me.type_select)) {
  	msgprint('Please select a type first!'); return;
  }
  
  $c_obj('Permission Control','get_permissions',sel_val(me.type_select), function(r,rt) {    
     // Get permissions
    if(r.message.perms.length)me.get_results(r.message);
    else me.body.innerHTML = '<div style = "color : red; margin:8px 0px;">No Records Found</div>'
  });
}

// Get Results
// ------------------
pscript.PermEngine.prototype.get_results = function(r){
  var perms = r.perms;
  var me = this;
  var doctype = sel_val(me.type_select);
  
  // show update button
  $ds(me.update_button);
  $ds(me.add_button);

  this.body.innerHTML = ''
  pscript.all_checkboxes = [];
  pscript.all_matches = [];
  
  var head = $a(this.body, 'h3'); head.innerHTML = 'Rules for ' + doctype;        
  var permt = make_table(me.body, perms.length+1,9,'80%',[],{border:'1px solid #AAA', padding:'3px', verticalAlign:'middle', height:'30px'});
    
  // Create Grid for particular DocType
  // ------------------------------------
    
  // Columns
  var col_labels = ['Role','Level','Read','Write','Create','Submit','Cancel','Amend','Restrict By']
  for(var n = 0; n < col_labels.length; n++){
  	$y($td(permt,0,n), {backgroundColor:'#DDD', width:(n==0?'30%':(n==8?'21%':'7%'))})
    $td(permt,0,n).innerHTML = col_labels[n];
    $td(permt,0,n).fieldname = col_labels[n].toLowerCase();
  }
    
  // Rows for Column Level / Role
  for(var j = 0; j < perms.length; j++){
    var plevel = $a($td(permt,j+1,1), 'span', 'link_type');
    plevel.innerHTML = perms[j].permlevel;
    plevel.doctype = doctype;
    plevel.value = perms[j].permlevel;
    plevel.onclick = function() {me.get_fields(this.doctype, this.value)}

    // role
    $td(permt,j+1,0).innerHTML = perms[j].role;

  }  
    
  // Get values
  for(var l = 0; l < perms.length; l++){
    for(var m = 0; m < 6; m++){                             // (read,write,create,submit,cancel,amend) 
      var chk = $a_input($td(permt,l+1,m+2), 'checkbox');
      var val = perms[l][$td(permt,0,m+2).fieldname];
      if(val == 1) chk.checked = 1;
      else chk.checked = 0;
      chk.doctype = doctype;
      chk.permlevel = perms[l].permlevel; chk.perm_type = col_labels[m+2].toLowerCase(); chk.role = perms[l].role;
      pscript.all_checkboxes.push(chk);
    }
  }
  
  // add selects for match
  me.add_match_select(r, perms, permt, doctype);
}

// render selects for match
// --------------------------------------------

pscript.PermEngine.prototype.add_match_select = function(r, perms, permt, doctype) {
  var me = this;
  
  // add select for match
  for(var i=0; i<perms.length; i++) {
    if(perms[i].permlevel==0) {
      // select
      var sel = $a($td(permt,i+1,8),'select','',{width:'100%'});
      add_sel_options(sel, r.fields);
      sel.details = perms[i]; sel.details.parent = doctype;
      sel.onchange = function() { 
      	if(sel_val(this) && sel_val(this)!='owner') $ds(this.div); 
      	else $dh(this.div); }
      
      // link
      var div = $a($td(permt,i+1,8),'div','link_type',{marginTop: '2px', fontSize:'10px', display:'none'});
      div.onclick = function() { this.details.match = sel_val(this.sel); me.show_match_dialog(this.details); }
      div.innerHTML = 'Set Users / Roles';
      div.details = perms[i];
      sel.div = div; div.sel = sel;

      // set the value
      if(perms[i].match) { sel.value = perms[i].match; $ds(div); }
      
      pscript.all_matches.push(sel);
    }
  }
}

// match users Dialog
// =======================================================

pscript.PermEngine.prototype.show_match_dialog=function(details) {
  if(!this.match_defaults_dialog) {
    var d = new Dialog(750, 500, 'Permission Applies To');
    d.make_body([['HTML','Body']]);
    var w = d.widgets['Body'];
    $y(w,{height:'350px', overflow:'auto'});
    this.match_defaults_dialog = d;
  }
  
  // dialog
  this.match_defaults_dialog.show();
  
  // render the rules
  var me = this;
  var callback = function(r,rt) {
  	me.render_match_dialog(r, details);
  }
  // load the rules
  $c_obj('Permission Control','get_defaults', details.match + '~~~' + (this.profiles ? 'No' : 'Yes'), callback); 
}

// --------------------------------------------

pscript.PermEngine.prototype.render_match_dialog=function(r, details) {
  var d = this.match_defaults_dialog;
  var w = d.widgets['Body'];
  w.innerHTML = '<div style="background-color:#FFD; padding: 4px; color: #440; margin-bottom:16px">Please Note: Any action will also affect other permissions with similar rules!</div>'
  
  // header
  var t=make_table($a(w,'div','',{borderBottom:'1px solid #AAA'}),1,3,'90%',['40%','40%','20%'],{fontWeight:'bold', padding:'3px', fontSize:'14px'});
  $td(t,0,0).innerHTML = 'Who?'; $td(t,0,1).innerHTML = 'Is allowed if '+details.match+' equals';
  
  // existing defaults
  var dl = r.message.dl; this.options = r.message.ol;
  if(!this.profiles) {
    this.profiles = r.message.pl;
  }
  
  for(var i=0; i<dl.length; i++) {
    new MatchDefaultValue(this, w, dl[i], details.match);
  }
  
  this.add_new_match_row(details.match);
}

pscript.PermEngine.prototype.add_new_match_row = function(fieldname) {
  // add new default
  new MatchDefaultValue(this, this.match_defaults_dialog.widgets['Body'], null, fieldname, 1);
}  
  
// --------------------------------------------

MatchDefaultValue = function(pe, parent, details, fieldname, editable) {
  this.pe = pe;
  this.wrapper = $a(parent, 'div', '', {margin:'4px'});
  this.clear();
  this.details = details;
  this.fieldname = fieldname;
  this.render(editable);
}


// --------------------------------------------

MatchDefaultValue.prototype.clear = function() {
  this.wrapper.innerHTML = '';
  this.tab = make_table(this.wrapper, 1, 3, '90%', ['40%','40%','20%'], {verticalAlign:'middle', padding:'3px'});
}

// --------------------------------------------

MatchDefaultValue.prototype.render = function(editable) {

  if(editable) {
  	this.render_editable();
  } else {
    this.render_static();
  }
}

// --------------------------------------------

MatchDefaultValue.prototype.render_editable = function() {
  var me = this;

  // profile or role
  this.profile_or_role = $a($td(this.tab,0,0), 'select', '', {width:'60px', marginRight:'8px'});
  add_sel_options(this.profile_or_role,['Profile', 'Role'], 'Profile');
  this.profile_or_role.onchange = function() {
    if(sel_val(this)=='Profile') { $di(me.profile_sel); $dh(me.role_sel); }
    else { $dh(me.profile_sel); $di(me.role_sel); }
  }

  // role sel
  this.role_sel = $a($td(this.tab,0,0), 'select', '', {width:'100px',display:'none'});
  add_sel_options(this.role_sel,this.pe.roles);
  
  // profile sel
  this.profile_sel = $a($td(this.tab,0,0), 'select', '', {width:'100px'});
  add_sel_options(this.profile_sel,this.pe.profiles);

  // options sel
  this.options_sel = $a($td(this.tab,0,1), 'select', '', {width:'120px'});
  add_sel_options(this.options_sel,this.pe.options);

   // add
  var span = $a($td(this.tab,0,2),'span','link_type',{marginLeft:'8px'});
  span.innerHTML = 'Add'
  span.onclick = function() { me.save(); }
}

// --------------------------------------------

MatchDefaultValue.prototype.render_static = function() {
  var me = this;
  
  $td(this.tab,0,0).innerHTML = this.details.parenttype;
  $td(this.tab,0,0).innerHTML += '&nbsp;' + this.details.parent;
  $td(this.tab,0,1).innerHTML = this.details.defvalue;

   // delete
  var span = $a($td(this.tab,0,2),'span','link_type',{marginLeft:'8px'});
  span.innerHTML = 'Cancel'
  span.onclick = function() { me.delete_def(); }
}

// --------------------------------------------

MatchDefaultValue.prototype.delete_def = function() {	
  var me = this;
  this.wrapper.innerHTML = '<div style="color: #888; padding: 3px;">Deleting...</div>';
  var callback = function(r,rt) {
  	$dh(me.wrapper);
    if(r.exc) msgprint('There were errors!')
  }
  $c_obj('Permission Control','delete_default'
    ,[this.details.parent, this.fieldname, this.details.defvalue].join('~~~')
    ,callback)
}

// --------------------------------------------

MatchDefaultValue.prototype.save = function() {
  var me= this;
  
  var callback = function(r,rt) {
    me.details = r.message;
    me.clear();
    me.render();
    me.pe.add_new_match_row(me.fieldname);
  }
  	
  // values
  if(sel_val(this.profile_or_role)=='Profile') { var parent = sel_val(this.profile_sel); var parenttype = 'Profile'; }
  else { var parent = sel_val(this.role_sel); var parenttype = 'Role'; }

  if(!sel_val(this.options_sel) || !parent) { msgprint("Please select all values"); return; }
  	
  $c_obj('Permission Control','add_default'
    ,[parent, parenttype, this.fieldname, sel_val(this.options_sel)].join('~~~')
    ,callback);
      
  this.wrapper.innerHTML = '<div style="color: #888; padding: 3px;">Adding...</div>';
}


// Make Dialog Box To Get Fields fro PermLevel
// =======================================================

pscript.PermEngine.prototype.make_fields_dialog=function(){
  if(!pscript.get_field_dialog) {
    pscript.get_field_dialog = new Dialog(750,500,'Fields');
    pscript.get_field_dialog.make_body([['HTML','Fields','<div id="perm_engine_get_fields"></div>'],['Button','OK']]);
  }
  else $i('perm_engine_get_fields').innerHTML = '';
}

// Get Fields
// --------------------
pscript.PermEngine.prototype.get_fields = function(dt, permlevel) {
  var me = this;
  var callback = function(r,rt){
    // Get Parent DocType Fields
    var parent_fields_dict = r.message.parent_fields_dict;
    
    // Get Child Table Fields if any
    var table_fields_dict = r.message.table_fields_dict;
    
    // Make Fields Dialog Box
    me.make_fields_dialog();
    
    me.make_fields_table(dt, parent_fields_dict, table_fields_dict, permlevel);
    
    pscript.get_field_dialog.show();
    pscript.get_field_dialog.widgets['OK'].onclick=function(){
      pscript.get_field_dialog.hide();
    }
  }
  var args = "{'dt':'"+dt+"','permlevel':"+permlevel+"}"
  $c_obj('Permission Control','get_fields', args, callback);
}



// Make Table of Fields for Dialog Box
// --------------------------------------
pscript.PermEngine.prototype.make_fields_table = function(dt, parent_fields_dict, table_fields_dict, permlevel) {
  
  var make_grid = function(table, fields_dict) {
    var col_labels = ['Label','Fieldtype','Fieldname','Options'];
    for(var n = 0; n < col_labels.length; n++){
      $a_input(($td(table,0,n)), 'data');
      $td(table,0,n).innerHTML = '<b>'+col_labels[n]+'</b>';
      $td(table,0,n).fieldname = col_labels[n].toLowerCase();
    }
    
    // Add values
    for(var i = 0; i < keys(fields_dict).length; i++){
      for(var j = 0; j < 4; j++){
        $a_input(($td(table,i+1,j)), 'data');
        $td(table,i+1,j).innerHTML = cstr(fields_dict[i][$td(table,0,j).fieldname])
      }
    }
  }

  
  $i('perm_engine_get_fields').innerHTML = '<b>'+ dt + ' Fields at Level '+ permlevel +':</b><br><br>';
  var parent_field_table = make_table('perm_engine_get_fields',keys(parent_fields_dict).length+1, 4,'100%',['25%','25%','25%','25%'],{border:'1px solid #AAA',padding:'2px'});
  make_grid(parent_field_table, parent_fields_dict);
  
  child_tables = keys(table_fields_dict)
  if(child_tables.length > 0){
    for(var k = 0; k < child_tables.length; k++){
      var tab_fields_det = table_fields_dict[child_tables[k]];
      if(keys(tab_fields_det).length > 0){
        $i('perm_engine_get_fields').innerHTML += '<br><b>'+ child_tables[k] + ' Fields at Level '+ permlevel +':</b><br><br>'
        var child_field_table = make_table('perm_engine_get_fields',keys(tab_fields_det).length+1, 4,'100%',['25%','25%','25%','25%'],{border:'1px solid #AAA',padding:'2px'});
        make_grid(child_field_table, tab_fields_det);
      }
    }
  }
}


// Update Permissions
// -----------------------
pscript.PermEngine.prototype.update_permissions = function() {
  var me = this;
  var out = {};

  var add_to_out = function(doctype, permlevel, role, key, value) {
    if(!out[doctype]) out[doctype] = {};
    if(!out[doctype][permlevel]) out[doctype][permlevel] = {};
    if(!out[doctype][permlevel][role]) out[doctype][permlevel][role] = {};
    out[doctype][permlevel][role][key] = value; 
  }

  // check boxes
  for(i in pscript.all_checkboxes) {
    c = pscript.all_checkboxes[i];
    add_to_out(c.doctype, c.permlevel, c.role, c.perm_type, c.checked ? 1 : 0);
  }

  // matches
  for(var i=0; i<pscript.all_matches.length; i++) {
  	var s = pscript.all_matches[i];
    if(sel_val(s))
      add_to_out(s.details.parent, s.details.permlevel, s.details.role, 'match', sel_val(s));
  }
  
  var args = "{'perm_dict': "+JSON.stringify(out)+"}"
  $c_obj('Permission Control','update_permissions', args, function(r,rt) {});
}


// Update Page Roles
// ----------------------
pscript.PermEngine.prototype.update_page_roles = function() {
  var me = this;
  var out = {};
  for(i in pscript.all_pg_checkboxes) {
    c = pscript.all_pg_checkboxes[i];
    out[c.page_name] = c.checked ? 1 : 0
  }
  var args = "{'page_role_dict': "+JSON.stringify(out)+", 'role': '"+sel_val(me.role_select)+"'}"
  $c_obj('Permission Control','update_page_role', args, function(r,rt) {});
}

// Reset Permission Engine
// -------------------------
pscript.PermEngine.prototype.reset_perm_engine = function(){
  this.type_select.selectedIndex = 0;
  this.load_options();
}
