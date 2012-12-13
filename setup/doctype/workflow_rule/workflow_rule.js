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
    $c('runserverobj', args={'method':'field_label_list', 'docs':wn.model.compress (make_doclist (mydoc.doctype,mydoc.name))},
    function(r, rt) {
      var doc = locals[mydoc.doctype][mydoc.name];
      cur_frm.fields_dict.workflow_action_details.grid.get_field("action_field").df.options = r.message;
    }
    );
  }
  
  var call_back_rule = function(mydoc){
    $c('runserverobj', args={'method':'compare_field', 'docs':wn.model.compress (make_doclist (mydoc.doctype,mydoc.name))},
    function(r, rt) {
      var doc = locals[mydoc.doctype][mydoc.name];
      cur_frm.fields_dict.workflow_rule_details.grid.get_field("comparing_field").df.options = r.message;
      call_back_action(mydoc)
    }
    );
  }
  
  $c('runserverobj', args={'method':'maindoc_field', 'docs':wn.model.compress (make_doclist (doc.doctype,doc.name))},
    function(r, rt) {
     var doc = locals[mydoc.doctype][mydoc.name];
     cur_frm.fields_dict.workflow_rule_details.grid.get_field("rule_field").df.options = r.message;
     call_back_rule(mydoc)
    }
  );
}
