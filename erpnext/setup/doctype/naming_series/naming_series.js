// Settings
cur_frm.cscript.onload = function(doc, cdt, cdn){
  var callback = function(r, rt){
    set_field_options('select_doc_for_series', r.message);
  }
  $c_obj([doc],'get_transactions','',callback);
  
  // add page head
  var ph = new PageHeader(cur_frm.fields_dict['Head HTML'].wrapper, 'Setup Series', 'Set prefix for numbering series on your transactions');
}

cur_frm.cscript.select_doc_for_series = function(doc, cdt, cdn) {
  var callback = function(r, rt){
    locals[cdt][cdn].set_options = r.message;
    refresh_field('set_options');
  }

  $c_obj([doc],'get_options','',callback)
}