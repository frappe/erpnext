// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.select_transaction = function(doc, cdt, cdn) {
  if(doc.select_transaction) {
    var callback = function(r,rt) {
      var doc = locals[cdt][cdn];
      doc.custom_message = r.message;
      refresh_field('custom_message');
    }
    return $c_obj(make_doclist(cdt, cdn),'get_message',doc.select_transaction, callback)
  }
}
