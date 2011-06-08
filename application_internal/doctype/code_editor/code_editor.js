
// get the script
loadscript("js/edit_area/edit_area_full.js", function() { });

// property div
cur_frm.fields_dict['Property HTML'].prop_div = $a(cur_frm.fields_dict['Property HTML'].wrapper,'div','',{margin:'8px 0px'});

// comment div
cur_frm.cscript.comment_div = $a(cur_frm.fields_dict['Code Toolbar'].wrapper,'div','',{display: 'none', marginBottom:'8px', width: '90%', backgroundColor: '#FFD', fontSize: '14px', padding:'4px'})

// field master
cur_frm.cscript.type_fields = {
  'DocType': 'doc_type'
  ,'Page': 'page_name'
  ,'Search Criteria': 'criteria_id'
  ,'Print Format': 'print_format'
}

// syntax master
// -------------
cur_frm.cscript.code_syntax = {
  // --- DocType   
   client_script:'js'
  ,client_script_core:'js'
  ,server_code:'python'
  ,server_code_core:'python'  

  // --- Page
  ,content:'html'
  ,script:'js'
  ,style:'css'

  // --- Search Criteria
  ,report_script:'js'
  ,server_script:'python'

  // --- Print Format
  ,code:'html'
}

// get field name of code
// ----------------------

cur_frm.cscript.get_field_name = function(doc) {
  // field names
  if(doc.script_from =='DocType') {
    var code_field = doc.code_type.toLowerCase().replace(/ /g,'_');
  } else if(doc.script_from =='Page') {
    var code_field = doc.code_type_page.toLowerCase().replace(/ /g,'_');
  } else if(doc.script_from =='Search Criteria') {
    var code_field = doc.code_type_criteria.toLowerCase().replace(/ /g,'_');
  } else if(doc.script_from =='Print Format') {
    var code_field = 'html';
  }
  return code_field;
}

// update comment
// --------------
cur_frm.cscript.update_comment = function() {
  var ce = cur_frm.cscript.cur_editor;
  if(!ce) return;
  var c = cur_frm.cscript.comment_div;
  c.innerHTML = "Currently Editing '<b>" + ce.fn + "</b>' from " + ce.dt + " <b>" + ce.dn + "</b><span style='color: #888'> (Last Modified: " + ce.code_modified + ")</span>";
  if(ce.saved)
    c.innerHTML += "<br><b style='color: GREEN'>Saved</b>"
  else
    c.innerHTML += "<br><b style='color: ORANGE'>Changes are not saved</b>"

  $ds(c);
}

// get code button
// ---------------
cur_frm.cscript.get_code = function() {
  var doc = locals[cur_frm.doctype][cur_frm.docname];

  if(!editAreaLoader) {
    msgprint('Waiting for the editor to load. Please try again');
    return;
  }

  if(cur_frm.cscript.cur_editor && (!cur_frm.cscript.cur_editor.saved)) {
    if(!confirm("Current script not saved. Do you want to continue?")) return;
  }

  // field names
  var code_field = cur_frm.cscript.get_field_name(doc);

  var callback = function(r, rt) {

    cur_frm.cscript.make_editor(cur_frm.cscript.code_syntax[code_field]);
    editAreaLoader.setValue(cur_frm.cscript.cur_editor.editor_id, r.message[0]);
    
    var ce = cur_frm.cscript.cur_editor;

    ce.code_modified = r.message[1];
    ce.dt = doc.script_from;
    ce.dn = doc[cur_frm.cscript.type_fields[doc.script_from]];
    ce.fn = code_field;
    ce.saved = 1;
    cur_frm.cscript.update_comment();
  }
  $c_obj([doc], 'get_code', [doc.script_from, doc[cur_frm.cscript.type_fields[doc.script_from]], code_field].join('~~~'), callback);
}

// make a new editor
// -----------------

cur_frm.cscript.make_editor = function(syntax) {

  // hide editor if exists
  if(cur_frm.cscript.cur_editor) {
  }

  // set id
  var myid = 'code_edit_1' //+ cur_frm.cscript.mycnt;

  editAreaLoader.init({id: myid, start_highlight: true, word_wrap: false, syntax: syntax
    ,change_callback : "cur_frm.cscript.editor_change_callback"
    ,EA_load_callback: "cur_frm.cscript.editor_load_callback"
  });
  editAreaLoader.window_loaded(); // make the editor

  if(!cur_frm.cscript.cur_editor) { 

    // parent
    var div = $a(cur_frm.fields_dict['Code HTML'].wrapper,'div');
    div.editor_id = myid;

    // make the form
    div.innerHTML = '<form method="POST"></form>';

    div.form = div.childNodes[0];

    // make the text area
    div.ta = $a(div.form,'textarea','',{height: '400px'}); div.ta.setAttribute('id',myid);

    cur_frm.cscript.cur_editor = div;
  }
}

cur_frm.cscript.editor_change_callback = function(id) {
  cur_frm.cscript.cur_editor.saved = 0; cur_frm.cscript.update_comment();
}

cur_frm.cscript.editor_load_callback = function(id) {
  cur_frm.cscript.cur_editor.saved = 1; cur_frm.cscript.update_comment();
}

// get properties 
// --------------
cur_frm.cscript.get_properties = function() {
  var callback = function(r,rt) {
    var div = cur_frm.fields_dict['Property HTML'].prop_div;
    div.innerHTML = '';
    
    var t = make_table(div, r.message.length, 4, '90%', ['25%','25%','25%','25%'], {padding: '3px'})
    var cl = r.message;
    for(var i=0; i<cl.length; i++) {
      $td(t,i,0).innerHTML = cl[i][0];
      $td(t,i,1).innerHTML = cl[i][1];
      $td(t,i,2).innerHTML = cl[i][2];
      $td(t,i,3).innerHTML = cl[i][3];
    }

  }

  $c_obj([locals[cur_frm.doctype][cur_frm.docname]], 'get_properties', '', callback);
}

// set code button
// ---------------

cur_frm.cscript.set_code = function() {
  ce = cur_frm.cscript.cur_editor;

  var doc = locals[cur_frm.doctype][cur_frm.docname];  
  
  if(doc.add_to_history) {
    var comment = prompt("Please enter comment before saving");
    if(!comment) { msgprint("Comment is necessary. Not saved"); return; }
  }

  doc.code = editAreaLoader.getValue(ce.editor_id);
  $c_obj([doc], 'set_code', [ce.dt, ce.dn, ce.fn, comment, ce.code_modified].join('~~~'), 
    function(r,rt) { 
      if(r.exc)return; 
      cur_frm.cscript.cur_editor.code_modified = r.message;
      cur_frm.cscript.cur_editor.saved = 1; 
      cur_frm.cscript.update_comment(); 
    }
  );
}

cur_frm.cscript.is_doctype = function(doc,dt,dn) { return doc.script_from == 'DocType' }
cur_frm.cscript.is_page    = function(doc,dt,dn) { return doc.script_from == 'Page' }
cur_frm.cscript.is_criteria = function(doc,dt,dn) { return doc.script_from == 'Search Criteria' }
cur_frm.cscript.is_print_format = function(doc,dt,dn) { return doc.script_from == 'Print Format' }
cur_frm.cscript.test = function(doc,dt,dn) { return false }

cur_frm.cscript.refresh = function(doc, dt, dn) {
  cur_frm.cscript.update_comment();
}