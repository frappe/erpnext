cur_frm.cscript.select_transaction = function(doc, dt, dn) {
  if(doc.select_transaction) {
    var callback = function(r,rt) {
      var doc = locals[dt][dn];
      doc.custom_message = r.message;
      refresh_field('custom_message');
    }
    $c_obj('Notification Control','get_message',doc.select_transaction, callback)
  }
}