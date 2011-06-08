cur_frm.cscript.refresh = function(doc,cdt,cdn){
  if(!doc.outgoing_mail_server || !doc.mail_login || !doc.mail_password || !doc.auto_email_id || !doc.mail_port || !doc.use_ssl){
    get_server_fields('set_vals','','',doc, cdt, cdn, 1);
  }
}