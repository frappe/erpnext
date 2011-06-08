cur_frm.fields_dict['doctype_name'].get_query = function(doc){
  return 'SELECT tabDocType.name FROM tabDocType WHERE (tabDocType.istable != 1 OR tabDocType.istable is null) AND (tabDocType.issingle !=1 OR tabDocType.issingle is null) AND tabDocType.name LIKE "%s"';
}

cur_frm.fields_dict['report_filter_details'].grid.get_field("field_label_fr").get_query = function(doc){
  return 'SELECT tabDocField.label FROM tabDocField WHERE tabDocField.parent = "' + doc.doctype_name+ '" AND tabDocField.fieldname is not null AND tabDocField.fieldname != "'+''+'" AND tabDocField.fieldtype != "Table" AND tabDocField.label LIKE "%s"';
}

cur_frm.fields_dict['report_field_details'].grid.get_field("field_label_fd").get_query = function(doc){
  return 'SELECT tabDocField.label FROM tabDocField WHERE tabDocField.parent = "' + doc.doctype_name+ '" AND tabDocField.fieldname is not null AND tabDocField.fieldname != "'+''+'" AND tabDocField.fieldtype != "Table" AND tabDocField.label LIKE "%s"';
}

cur_frm.cscript.field_label_fr = function(doc,cdt,cdn){
  var d = locals[cdt][cdn];
  if(d.field_label_fr){
    get_server_fields('get_filter_details',d.field_label_fr,'report_filter_details',doc,cdt,cdn,1);
  }
}

cur_frm.cscript.field_label_fd = function(doc,cdt,cdn){
  var d = locals[cdt][cdn];
  if(d.field_label_fd){
    get_server_fields('get_field_details',d.field_label_fd,'report_field_details',doc,cdt,cdn,1);
  }
}