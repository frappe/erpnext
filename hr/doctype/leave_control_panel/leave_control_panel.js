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

cur_frm.cscript.onload = function(doc,dt,dn){
  if(!doc.posting_date) set_multiple(dt,dn,{posting_date:get_today()});
  if(!doc.leave_transaction_type) set_multiple(dt,dn,{leave_transaction_type:'Allocation'});

}


// Validation For To Date
// ================================================================================================
cur_frm.cscript.to_date = function(doc, cdt, cdn) {
  return $c('runserverobj', args={'method':'to_date_validation','docs':wn.model.compress(make_doclist(doc.doctype, doc.name))},
    function(r, rt) {
    var doc = locals[cdt][cdn];
    if (r.message) {
      alert("To date cannot be before from date");
      doc.to_date = '';
      refresh_field('to_date');
    }
    }
  ); 
}

// Allocation Type
// ================================================================================================
cur_frm.cscript.allocation_type = function (doc, cdt, cdn){
  doc.no_of_days = '';
  refresh_field('no_of_days');
}
