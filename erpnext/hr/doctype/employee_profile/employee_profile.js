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

cur_frm.cscript.onload = function(doc, cdt, cdn){
  $c('runserverobj', args={'method':'cal_tot_exp','docs':compress_doclist (make_doclist (doc.doctype,doc.name))},
function(r, rt) { refresh_many(['year','months']); });
}

//===========================================================

cur_frm.cscript.employee = function(doc, cdt, cdn){
  $c('runserverobj', args={'method':'get_doj','docs':compress_doclist (make_doclist (doc.doctype,doc.name))},
function(r, rt) { refresh_many(['employee_name','date_of_joining']); });
}

//===========================================================

cur_frm.cscript.country1 = function(doc, cdt, cdn) {
  var mydoc=doc;
  $c('runserverobj', args={'method':'check_state','arg':doc.country1, 'docs':compress_doclist([doc])},
    function(r,rt){

      if(r.message) {
        var doc = locals[mydoc.doctype][mydoc.name];
        doc.state1 = '';
        get_field(doc.doctype, 'state1' , doc.name).options = r.message;
        refresh_field('state1');
      }
    }  
  );
}

//===========================================================
cur_frm.cscript.country2 = function(doc, cdt, cdn) {
  var mydoc=doc;
  $c('runserverobj', args={'method':'check_state', 'arg':doc.country2,'docs':compress_doclist([doc])},
    function(r,rt){

      if(r.message) {
        var doc = locals[mydoc.doctype][mydoc.name];
        doc.state2 = '';
        get_field(doc.doctype, 'state2' , doc.name).options = r.message;
        refresh_field('state2');
      }
    }  
  );
}