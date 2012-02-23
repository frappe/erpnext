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

//omload function to set values in select field
cur_frm.cscript.onload = function(doc, cdt, cdn){
  var mydoc = doc
  doc.select_master = 'Salary Structure';
  refresh_field('select_master');

  var call_back_master2 = function(mydoc){
    $c('runserverobj', args={'method':'get_masters', 'docs':compress_doclist (make_doclist (doc.doctype,doc.name))},
    function(r, rt) {
    var doc = locals[mydoc.doctype][mydoc.name];
     get_field(doc.doctype, 'select_master2' , doc.name).options = r.message;
     refresh_field('select_master2');
   
    }
  );
  }
  $c('runserverobj', args={'method':'maindoc_field', 'arg':doc.select_master,'docs':compress_doclist (make_doclist (doc.doctype,doc.name))},
    function(r, rt) {
     var doc = locals[mydoc.doctype][mydoc.name];
     get_field(doc.doctype, 'select_field' , doc.name).options = r.message;
     refresh_field('select_field');
     call_back_master2(mydoc);
    }
  );
}

//select_master2 onchanged event function: it will add values to select_field2 based on select_master2 field 
cur_frm.cscript.select_master2 = function(doc, cdt, cdn){
  var mydoc = doc
  doc.select_field2 ='';
  refresh_field('select_field2');
  doc.select_value='';
  refresh_field('select_value');
  $c('runserverobj', args={'method':'maindoc_field', 'arg':doc.select_master2, 'docs':compress_doclist (make_doclist (doc.doctype,doc.name))},
    function(r, rt) {
     var doc = locals[mydoc.doctype][mydoc.name];
     get_field(doc.doctype, 'select_field2' , doc.name).options = r.message;
     refresh_field('select_field2');
     get_field(doc.doctype, 'select_value' , doc.name).options = '';
     refresh_field('select_value'); 
        
    }
  );
}

//select_field2 onchanged event function: used to add records values of selected master & their field_name
cur_frm.cscript.select_field2 = function(doc, cdt, cdn){
  var mydoc = doc
  doc.select_value='';
  refresh_field('select_value');
  $c('runserverobj', args={'method':'get_values','docs':compress_doclist (make_doclist (doc.doctype,doc.name))},
    function(r, rt) {
     var doc = locals[mydoc.doctype][mydoc.name];
     get_field(doc.doctype, 'select_value' , doc.name).options = r.message;
     refresh_field('select_value');
     
    }
  );
}

//transaction onchanged event function: used to add transaction terms to transaction term field
cur_frm.cscript.transaction = function(doc, cdt, cdn){
  var mydoc = doc
  doc.transaction_term='';
  refresh_field('transaction_term');
  if(doc.transaction){
    $c('runserverobj', args={'method':'add_transaction_terms','docs':compress_doclist (make_doclist (doc.doctype,doc.name))},
      function(r, rt) {
       var doc = locals[mydoc.doctype][mydoc.name];
       get_field(doc.doctype, 'transaction_term' , doc.name).options = r.message;
       refresh_field('transaction_term');
     }
    );
  }
}


//right operand of condition :hide or unhide 
cur_frm.cscript.right_operand = function(doc, cdt, cdn){
  doc.select_master2 = "";
  doc.select_field2 = "";
  doc.select_value = "";
  if(doc.right_operand =='Automatic'){
    unhide_field('select_master2');
    unhide_field('select_field2');
    unhide_field('select_value');
  }
  else {
   hide_field('select_master2');
   hide_field('select_field2');
   hide_field('select_value');
  
  }
}

