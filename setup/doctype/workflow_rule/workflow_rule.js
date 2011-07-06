 

//--------- ONLOAD -------------
cur_frm.cscript.onload = function(doc, cdt, cdn) {
   
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
   
}

// Show Label name of fields for selected Doctype 
// ---------------------------

cur_frm.cscript.select_form = function(doc, cdt, cdn){
  var mydoc = doc
  
  var call_back_action = function(mydoc){
    $c('runserverobj', args={'method':'field_label_list', 'docs':compress_doclist (make_doclist (mydoc.doctype,mydoc.name))},
    function(r, rt) {
      var doc = locals[mydoc.doctype][mydoc.name];
      cur_frm.fields_dict.workflow_action_details.grid.get_field("action_field").df.options = r.message;
    }
    );
  }
  
  var call_back_rule = function(mydoc){
    $c('runserverobj', args={'method':'compare_field', 'docs':compress_doclist (make_doclist (mydoc.doctype,mydoc.name))},
    function(r, rt) {
      var doc = locals[mydoc.doctype][mydoc.name];
      cur_frm.fields_dict.workflow_rule_details.grid.get_field("comparing_field").df.options = r.message;
      call_back_action(mydoc)
    }
    );
  }
  
  $c('runserverobj', args={'method':'maindoc_field', 'docs':compress_doclist (make_doclist (doc.doctype,doc.name))},
    function(r, rt) {
     var doc = locals[mydoc.doctype][mydoc.name];
     cur_frm.fields_dict.workflow_rule_details.grid.get_field("rule_field").df.options = r.message;
     call_back_rule(mydoc)
    }
  );
}