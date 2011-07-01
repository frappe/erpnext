pscript.onload_Messages = function() {
  var p = new PageHeader($i('message_header'),'Messages');
  pscript.msg_struct = new Message();
}

pscript.onshow_Messages = function() {
  pscript.msg_struct.show_inbox();
}

function Message(){
  if(!this.mytabs) this.make_body();
}

Message.prototype.make_body = function() {
  var me = this;
  this.mytabs = new TabbedPage($i('inbox_tabs'));
  $y(this.mytabs.body_area, {padding:'16px'})

  me.make_inbox();
  me.make_compose();
  me.make_sent();
  
  this.mytabs.tabs['Inbox'].show();
}

Message.prototype.make_inbox = function() {
  var me = this;
  
  //inbox tab
  me.mytabs.add_tab('Inbox', function() { 
    me.inbox_lst.generate_unread_lst();
    me.inbox_lst.msg_li.run(); 
    me.cur_inbox_list = me.inbox_lst.msg_li; // for refresh
  });
  
  if(!this.inbox_lst) this.inbox_lst = new MessageList(me.mytabs.tabs['Inbox'].tab_body, 'inbox msg');
  this.inbox_lst.msg_li.get_query = function() {
    //me.checked_msg_lst = [];
    me.all_msg = {};
    this.query = repl("select distinct t1.name, t1.last_updated_on, t1.last_updated_by, t1.subject, t3.first_name, t3.file_list, t1.message_date, t1.owner, t1.message, t1.previous_updated_by from `tabMail` t1, `tabMail Participant Details` t2, `tabProfile` t3 where t1.is_main_thread='Yes' and t2.participant_name='%(user)s' and (t2.delete_status is NULL or t2.delete_status = 'No') and t1.name = t2.parent and ((t1.last_updated_by = t3.name and t1.last_updated_by!='%(user)s') or (t1.previous_updated_by = t3.name and t1.previous_updated_by!='%(user)s')) order by t1.modified desc", {'user':user});
    
    this.query_max = repl("select distinct count(t1.name) from `tabMail` t1, `tabMail Participant Details` t2, `tabProfile` t3 where t1.is_main_thread='Yes' and t2.participant_name='%(user)s' and (t2.delete_status is NULL or t2.delete_status = 'No') and t1.name = t2.parent and ((t1.last_updated_by = t3.name and t1.last_updated_by!='%(user)s') or (t1.previous_updated_by = t3.name and t1.previous_updated_by!='%(user)s')) order by t1.modified desc", {'user':user});
  }
  
  this.inbox_lst.generate_unread_lst();  
  this.inbox_lst.msg_li.run();
  this.inbox_lst.msg_li.onrun = function(){ me.inbox_lst.show_if_no_msg(me.inbox_lst.msg_li); }
}

Message.prototype.make_compose = function() {
  var me = this;
  
  me.mytabs.add_tab('Compose', function() { 
    if(!pscript.compose_msg_obj){
      pscript.compose_msg_obj = new MessageThread(me.mytabs.tabs['Compose'].tab_body, me.mytabs.tabs['Inbox'], me.inbox_lst.lst_wrapper, 'My Inbox'); 
      //pscript.compose_msg_obj.show_msg(0, me.mytabs.tabs['Compose'].tab_body, me.mytabs.tabs['Inbox'], me.inbox_lst.lst_wrapper, 'My Inbox', me.mytabs.tabs['Sent'], me.sent_lst.lst_wrapper);
    }
    pscript.compose_msg_obj.show_msg(0, me.mytabs.tabs['Compose'].tab_body, me.mytabs.tabs['Inbox'], me.inbox_lst.lst_wrapper, 'My Inbox', me.mytabs.tabs['Sent'], me.sent_lst.lst_wrapper);
    
    this.cur_inbox_list = null;
  });
}

Message.prototype.make_sent = function() {
  var me = this;
  
  // sent msg tab
  me.mytabs.add_tab('Sent', function() { 
    me.sent_lst.msg_li.run(); 
    me.cur_inbox_list = me.sent_lst.msg_li; // for refresh
  });
  
  if(!this.sent_lst) this.sent_lst = new MessageList(me.mytabs.tabs['Sent'].tab_body, 'sent msg');
  this.sent_lst.msg_li.get_query = function() {
    //me.checked_msg_lst = [];
    me.all_msg = {};
    
    this.query = repl("select distinct t1.name, t1.last_updated_on, t1.last_updated_by, t1.subject, t3.first_name, t3.file_list, t1.message_date, t1.owner, t1.message from `tabMail` t1, `tabProfile` t3, `tabMail Participant Details` t2 where t1.is_main_thread='Yes' and t1.last_updated_by='%(user)s' and t1.last_updated_by = t3.name and t2.participant_name = '%(user)s' and (t2.delete_status is NULL or t2.delete_status = 'No') and t2.parent = t1.name order by t1.modified desc", {'user':user});
    this.query_max = repl("select distinct count(t1.name) from `tabMail` t1, `tabProfile` t3, `tabMail Participant Details` t2 where t1.is_main_thread='Yes' and t1.last_updated_by='%(user)s' and t1.last_updated_by = t3.name and t2.participant_name = '%(user)s' and (t2.delete_status is NULL or t2.delete_status = 'No') and t2.parent = t1.name order by t1.modified desc", {'user':user});
  }
  this.sent_lst.msg_li.run();
  this.sent_lst.msg_li.onrun = function(){ me.sent_lst.show_if_no_msg(me.sent_lst.msg_li); }
}

Message.prototype.show_inbox = function(){
  var me = this;
  if(me.inbox_lst){
    me.inbox_lst.msg_li.run();
  }
  me.mytabs.tabs['Inbox'].show();
}

MessageList = function(parent_tab, req_frm) {
  this.checked_msg_lst = [];
  this.unread_msg_lst = [];
  this.all_msg = {};
  this.parent_tab = parent_tab;
  this.req_frm = req_frm;
  this.make();
}

MessageList.prototype.make = function(){
  var me = this;
  
  this.lst_wrapper = $a(me.parent_tab, 'div');
  
  //toolbar
  this.toolbar_area = $a(this.lst_wrapper, 'div', '', {paddingTop:'12px'});
  this.create_toolbar();
  
  //no inbox msg div
  this.no_lst_wrapper = $a(me.parent_tab, 'div', '', {padding:'8px',backgroundColor:'#FFE4AA'});
  $dh(this.no_lst_wrapper);
  
  //view inbox msg div
  this.view_msg_wrapper = $a(me.parent_tab, 'div');
  
  this.msg_li = new Listing("Recent Messages",1);
  this.msg_li.colwidths = ['90%'];
  this.msg_li.opts.no_border = 1;
  this.msg_li.opts.show_empty_tab = 0;
  this.msg_li.opts.no_border = 1;
  
  this.msg_li.show_cell = function(cell,ri,ci,d) {
    if(ri % 2)$y(cell,{backgroundColor:'#E1E3DE'});
    if(ci ==0){
      this.msg_lst = new MessagePreview(cell, me.req_frm, d[ri][0], d[ri][1], d[ri][2], d[ri][3], d[ri][4], d[ri][5], d[ri][6], d[ri][7], d[ri][8], d[ri][9], me.lst_wrapper, me.view_msg_wrapper, me.unread_msg_lst, me.all_msg);
    }
  }
  this.msg_li.make(this.lst_wrapper);
  $dh(this.msg_li.btn_area);
}

MessageList.prototype.create_toolbar = function(){
  var me = this;
  
  this.toolbar_tbl = make_table(me.toolbar_area, 1, 2, '100%', ['85%', '15%']);
  
  this.select_all_lnk = $a($td(this.toolbar_tbl, 0, 0), 'span', 'link_type');
  this.select_all_lnk.innerHTML = 'Select All';
  $dh(this.select_all_lnk);
  
  this.unselect_all_lnk = $a($td(this.toolbar_tbl, 0, 0), 'span', 'link_type');
  this.unselect_all_lnk.innerHTML = 'Unselect All';
  $dh(this.unselect_all_lnk);
  
  this.select_all_lnk.onclick = function(){
    $ds(me.unselect_all_lnk);
    $dh(me.select_all_lnk);
    for(m in me.all_msg){
      me.all_msg[m].checked = true;
    }
  }
  
  this.unselect_all_lnk.onclick = function(){
    $ds(me.select_all_lnk);
    $dh(me.unselect_all_lnk);
    for(m in me.all_msg){
      me.all_msg[m].checked = false;
    }
  }
  
  this.delete_selected_btn = $a($td(this.toolbar_tbl, 0, 1), 'button', 'button', {align:'right'});
  this.delete_selected_btn.innerHTML = 'Delete Selected';
  $dh(this.delete_selected_btn);
  this.delete_selected_btn.onclick = function(){
    me.checked_msg_lst = [];    
    for(m in me.all_msg){
      if(me.all_msg[m].checked == true)
        me.checked_msg_lst.push(m);
    }
    me.delete_selected();
  }
}

MessageList.prototype.show_if_no_msg = function(lst_data){
  var me = this;
  $dh(me.view_msg_wrapper);
  
  if(!lst_data.has_data()){  
    $ds(me.no_lst_wrapper);
    $dh(me.lst_wrapper);
    if(me.req_frm == 'inbox msg'){
      me.no_lst_wrapper.innerHTML = "You have no messages in your Inbox.";      
    }
    else if(me.req_frm == 'sent msg'){
      me.no_lst_wrapper.innerHTML = "You have no messages in your Sent messages list.";
    }
  } else {    
    $dh(me.no_lst_wrapper); 
    $ds(me.lst_wrapper);
    $dh(me.no_lst_wrapper); 
    $ds(me.lst_wrapper);
    $dh(this.unselect_all_lnk);
    $ds(this.select_all_lnk);
    $ds(this.delete_selected_btn);
  }
}

MessageList.prototype.generate_unread_lst = function(){
  var me = this;
  
  var msg_callback = function(r, rt){
    if(r.message.ur_lst){
      me.unread_msg_lst = r.message.ur_lst;
    }
  }
  $c('runserverobj', {doctype:'Message Control',method:'get_unread_msg_lst',arg:user}, msg_callback);
}

MessageList.prototype.delete_selected = function(){
  var me = this;
  
  if(me.checked_msg_lst.length >= 1) me.msg_li.msg_lst.delete_msg(me.checked_msg_lst);
  else  msgprint("error:Please select the message to delete");
}

function MessagePreview(parent, req_frm, msg_id, last_updated_on, last_updated_by, subject, first_name, profile_pic, msg_date, msg_owner, message, previous_updated_by, lst_wrapper, view_msg_wrapper, unread_msg_lst, all_msg_dict) { 
  this.create_structure(parent);
  
  if(req_frm) this.req_frm = req_frm;
  this.msg_id = msg_id;
  this.subject = subject;
  this.message = message;
  this.msg_date = msg_date;
  this.msg_owner = msg_owner;
  this.first_name = first_name;
  this.lst_wrapper = lst_wrapper;
  this.view_msg_wrapper = view_msg_wrapper;
  if(profile_pic) this.profile_pic = profile_pic;
  if(last_updated_on) this.last_updated_on = last_updated_on;
  if(last_updated_by) this.last_updated_by = last_updated_by;
  if(previous_updated_by) this.previous_updated_by = previous_updated_by;
	this.unread_msg_lst = unread_msg_lst;
  this.all_msg = all_msg_dict;
  
  this.show_msg_sender();
  this.show_msg_subject();
  this.show_delete_lnk();
}

MessagePreview.prototype.create_structure = function(parent){
  this.wrapper = $a(parent,'div');
  this.t = make_table(this.wrapper, 1, 4, '100%', ['5%','10%','80%','5%']);
}

MessagePreview.prototype.show_msg_sender = function(){
  var me = this;
  
  // checkbox
  var chk_box = $a($td(this.t, 0, 0),'div');
  if(isIE) {
    chk_box.innerHTML = '<input type="checkbox" style="border: 0px">'; // IE fix
    this.inp = chk_box.childNodes[0];
  } else {
    this.inp = $a(chk_box, 'input');
    this.inp.type = 'checkbox';
  }
  
  this.inp.onclick = function() { 
    for(m in me.all_msg){
      if(m == me.msg_id)
        me.all_msg[m].checked = me.inp.checked;
    }
  }
  
  me.all_msg[me.msg_id] = this.inp;
  
  //sender or receiver
  // photo
  if(this.profile_pic) {
    var img = $a($td(this.t, 0, 1),'img');
    var img_src = this.profile_pic.split(NEWLINE)[0].split(',')[0]
    img.src = repl('cgi-bin/getfile.cgi?name=%(fn)s&thumbnail=32',{fn:img_src})
  }
  //name
  var div = $a($td(this.t, 0, 1),'div');
  div.innerHTML = this.first_name;
}

MessagePreview.prototype.show_msg_subject = function() {
  var me = this;
  // message
  var div1 = $a($td(this.t, 0, 2),'div', '', {paddingBottom:'4px'});
  var sp = $a(div1,'span','link_type', {fontSize:'12px'});
  sp.innerHTML = 'Sub : ' +me.subject;
  
  var div = $a($td(this.t, 0, 2),'div', 'comment',{paddingBottom:'8px'});
  div.innerHTML = 'created by: ' + me.msg_owner +' | created on: ' + dateutil.str_to_user(me.msg_date)+ ' | last updated on: ' + dateutil.str_to_user(me.last_updated_on);
  
  if (me.req_frm == 'inbox msg' && inList(me.unread_msg_lst, me.msg_id)) {
    $y(sp,{fontWeight:'bold',color:'Black'});
    $y(div,{fontWeight:'bold',color:'Black'});
  }
  
  sp.style.cursor = 'pointer';
  sp.msg_id = me.msg_id; sp.req_frm = me.req_frm;
  
  sp.onclick = function() {
    $dh(me.lst_wrapper);
    if(this.req_frm == 'inbox msg'){
      if(!pscript.inbox_msg_obj){
        pscript.inbox_msg_obj = new MessageThread(me.view_msg_wrapper, pscript.msg_struct.mytabs.tabs['Inbox'], me.lst_wrapper, 'My Inbox'); 
      }
      pscript.inbox_msg_obj.show_msg(this.msg_id, me.view_msg_wrapper, pscript.msg_struct.mytabs.tabs['Inbox'], me.lst_wrapper, 'My Inbox', pscript.msg_struct.mytabs.tabs['Sent'], me.lst_wrapper);
      
      //mark for already read
      if (this.req_frm == 'inbox msg' && inList(me.unread_msg_lst,this.msg_id)) {
        me.mark_as_read(this.msg_id);
      }
    }
    else if(this.req_frm == 'sent msg'){
      if(!pscript.sent_msg_obj){
        pscript.sent_msg_obj = new MessageThread(me.view_msg_wrapper, pscript.msg_struct.mytabs.tabs['Sent'], me.lst_wrapper, 'My Inbox'); 
      }
      pscript.sent_msg_obj.show_msg(this.msg_id, me.view_msg_wrapper, pscript.msg_struct.mytabs.tabs['Sent'], me.lst_wrapper, 'My Inbox', pscript.msg_struct.mytabs.tabs['Sent'], me.lst_wrapper); 
    }
  }
}

MessagePreview.prototype.mark_as_read = function(msg_id){
  this.msg_id = msg_id;
  var me = this;
  
  args = {'user' : user, 'msg':this.msg_id,'read':'Yes'}
  $c_obj('Message Control','read_unread_message',docstring(args),function(r,rt){
    me.remove_element(me.unread_msg_lst, me.msg_id);
  });
}

MessagePreview.prototype.delete_msg = function(msg_nm_lst){
  this.msg_nm_lst = msg_nm_lst;
  var me = this; 
  var delete_msg_dialog;
  
  set_delete_msg_dialog = function() {
    delete_msg_dialog = new Dialog(400, 200, 'Delete Message');
    delete_msg_dialog.make_body([
      ['HTML', 'Message', '<div class = "comment">Are you sure, you want to delete message(s) ?</div>'],
      ['HTML', 'Response', '<div class = "comment" id="delete_msg_dialog_response"></div>'],
      ['HTML', 'Delete Msg', '<div></div>']
    ]);
    
    var delete_msg_btn1 = $a($i(delete_msg_dialog.widgets['Delete Msg']), 'button', 'button');
    delete_msg_btn1.innerHTML = 'Yes';
    delete_msg_btn1.onclick = function(){ delete_msg_dialog.add(); }
    
    var delete_msg_btn2 = $a($i(delete_msg_dialog.widgets['Delete Msg']), 'button', 'button');
    delete_msg_btn2.innerHTML = 'No';
    $y(delete_msg_btn2,{marginLeft:'4px'});
    delete_msg_btn2.onclick = function(){ delete_msg_dialog.hide();}
    
    delete_msg_dialog.onshow = function() {
      $i('delete_msg_dialog_response').innerHTML = '';
    }
    
    delete_msg_dialog.add = function() {
      // sending...
      $i('delete_msg_dialog_response').innerHTML = 'Processing...';
      var m_arg = user+ '~~' + this.msg_nm_lst;
      
      var call_back = function(r,rt) { 
        if(r.message == 'true'){
          $i('delete_msg_dialog_response').innerHTML = 'Message Deleted';
          delete_msg_dialog.hide();
          
          for(m=0; m<me.msg_nm_lst.length; m++){
            if(inList(me.unread_msg_lst, me.msg_nm_lst[m]))
              me.remove_element(me.unread_msg_lst, me.msg_nm_lst[m]);
          }
          pscript.msg_struct.inbox_lst.msg_li.run();
          pscript.msg_struct.sent_lst.msg_li.run();
        }
      }
      $c('runserverobj', {doctype:'Message Control',method:'delete_message',arg:m_arg}, call_back); 
    }
  }  
  
  if(!delete_msg_dialog){
    set_delete_msg_dialog();
  }  
  delete_msg_dialog.msg_nm_lst = this.msg_nm_lst;
  delete_msg_dialog.show();
}

MessagePreview.prototype.remove_element = function(arrayName, arrayElement){
  for(var i=0; i<arrayName.length;i++ )
  { 
    if(arrayName[i]==arrayElement)
    arrayName.splice(i,1); 
  }
}

MessagePreview.prototype.show_delete_lnk = function() {
  var me = this;
  var div = $a($td(this.t, 0, 3), 'span', 'link_type');
  div.innerHTML = 'Delete';
  div.msg_id = me.msg_id;
  
  div.onclick = function() {
    me.delete_msg(me.msg_id);
  }
}

MessagePart = function(parent){
  var me = this;
  
  this.parent = parent;
  this.inputs = {};
  
  me.make_header();
  me.make_reply();
  me.make_post();
}

MessagePart.prototype.make = function(label, ele, comment){
  var me = this;
  
  var div = $a(this.parent,'div','',{marginBottom:'12px'});
  var t = make_table(div,2,1,'70%',['100%']);
  
  if( ele == 'button'){
    var element = $a($td(t,0,0), 'button');
    element.innerHTML = label;
  }
  else {
    var element = $a($td(t,1,0),ele);

    // large fonts for inputs
    if(in_list(['input','textarea'],ele.toLowerCase())) {
      $y(element,{fontSize:'14px', width:'100%'})
    }
    $td(t,0,0).innerHTML = label;
  }

  if(comment) {
    var div2 = $a(div,'div','',{fontSize:'11px', color:'#888', marginTop:'2px'});
    div2.innerHTML = comment;
  }
  
  element.wrapper = div;
  if(label) me.inputs[label] = element;
  return element;
}

MessagePart.prototype.make_header = function(){
  var me = this;
  
  this.back_link_div = $a(me.make('','div'),'span', 'link_type', {paddingTop:'12px'});
  this.back_link_div.innerHTML = 'Back to List';
  
  me.make('To','textarea','Enter Email Ids separated by commas (,)');
  $y(me.inputs['To'],{overflow :'auto', height : '50px'});
  me.make('Subject','input');
}

MessagePart.prototype.make_reply = function(){
  var me = this;
  this.inputs.Thread = $a(this.parent, 'div', '', {margin:'16px 0px'})
}

MessagePart.prototype.make_post = function(){
  var me = this;
  
  me.make('Message','textarea');
  $y(me.inputs['Message'],{height:'240px'});

  // send + cancel
  var d = $a(this.parent, 'div');
  me.inputs.Send = $btn(d, 'Send');
  me.inputs.Reply = $a(d, 'Reply')
}

MessagePart.prototype.add_header_values = function(to_list, subject){
  var me = this;
  
  //thread_participants
  me.inputs['To'].value = to_list.join(',');
  me.inputs['To'].disabled = true;
  
  // subject
  me.inputs['Subject'].value = subject;
  me.inputs['Subject'].disabled = true;
}

MessagePart.prototype.add_reply_thread = function(thread){
  var me = this;
  // prev messages
  var t = me.inputs['Thread'];
  t.innerHTML = ''; // clear previous threads
  
  var w = $a(t,'div','',{width:'70%'});
  var tab = make_table(w,thread.length,2,'100%',['20%','80%'], {padding:'8px 0px', borderBottom:'1px solid #AAA'});
  
  for(i=0;i<thread.length;i++) {
    // ---- photo ---- 
    if(thread[i][6]) {
      var img = $a($td(tab,i,0),'img');
      var img_src = thread[i][6].split(NEWLINE)[0].split(',')[0];
      img.src = repl('cgi-bin/getfile.cgi?name=%(fn)s&thumbnail=32',{fn:img_src});
    }
    
    // ---- sender name ---- 
    var d = $a($td(tab,i,0),'div','',{fontSize:'11px'});
    d.innerHTML = thread[i][5];
    
    //----- date ----
    var d = $a($td(tab,i,1),'div', 'comment', {marginLeft:'8px', color:'#888', fontSize:'11px'}); 
    d.innerHTML = dateutil.str_to_user(thread[i][3]);
    
    //------ message ------
    var d = $a($td(tab,i,1),'div', 'comment', {fontSize:'14px', marginLeft:'8px'}); 
    d.innerHTML = replace_newlines(thread[i][1]);
    $y($td(tab,i,1), {paddingBottom: '8px'});
  }
}

//++++++++++++++++++++++++ Message  ++++++++++++++++++++++++

MessageThread = function(parent, view_list_tab, view_list_div, req_frm) {
  var me = this;
  this.wrapper = $a(parent,'div');
  if(!this.msg_parts) this.make(view_list_tab, view_list_div, req_frm);
}

 
MessageThread.prototype.add_autosuggest = function() {
  var me = this;
  
  // ---- add auto suggest ---- 
  var opts = { script: '', json: true, maxresults: 10, timeout: 10000, delay:250, maxentries:500, cache:false};
  
  var as = new AutoSuggest(me.msg_parts.inputs['To'], opts);
  as.custom_select = function(txt, sel) {
    // ---- add to the last comma ---- 
    
    var r = '';
    var tl = txt.split(',');
    for(var i=0;i<tl.length-1;i++) r=r+tl[i]+',';
    r = r+(r?' ':'')+sel+',';
    if(r[r.length-1]==NEWLINE) { r=substr(0,r.length-1);}
    return r;
  }
  
  // ---- override server call ---- 
  as.doAjaxRequest = function(txt) {
    var pointer = as; var q = '';
    
    // ---- get last few letters typed ---- 
    var last_txt = txt.split(',');
    last_txt = last_txt[last_txt.length-1];
    
    // ---- show options ---- 
    var call_back = function(r,rt) {
      as.aSug = [];
      var jsondata = r.message;  
      for (var i=0;i<jsondata.results.length;i++) {
        as.aSug.push({'id':jsondata.results[i].id, 'value':jsondata.results[i].value, 'info':jsondata.results[i].info});
      }
      as.idAs = "as_for_to_message";
      
      //old create list
      as.createList(as.aSug);        
    }
    
    $c_obj('Message Control', 'get_to_list', (last_txt ? last_txt : '%'), call_back);
    return;
  }  
}
  
MessageThread.prototype.make = function(view_list_tab, view_list_div, req_frm) {
  var me = this;
  
  me.view_list_tab = view_list_tab;
  me.view_list_div = view_list_div;
  me.req_frm = req_frm;
  
  this.msg_parts = new MessagePart(me.wrapper);

  this.msg_parts.back_link_div.onclick = function() { 
    me.hide(); 
    
    if(me.in_compose) {
      if(me.req_frm == 'My Inbox') { me.view_list_tab.show(); $ds(me.view_list_div); }
    }
  }
  
  // autosuggest
  me.add_autosuggest();
}

MessageThread.prototype.set_inbox_editor = function(editor) { 
  pscript.inbox_text_editor_set = 1;
}

MessageThread.prototype.view_existing_msg = function(args){
  var me = this;
  
  $c_obj('Message Control', 'get_thread_details', docstring(args), 
    function(r, rt){
      var tl = r.message.tl;
      var to_list = r.message.to_list;
      
      //to and subject
      me.msg_parts.add_header_values(to_list, tl[0][0]);
      
      //reply thread
      me.msg_parts.add_reply_thread(tl);
      
      //post area
      if(me.inbox_editor && pscript.inbox_text_editor_set == 1){
        me.inbox_editor.editor.setContent('');
      }
      else{
        me.msg_parts.inputs['Message'].value = '';
      }
      me.show_as(true);
    }
  );
}

MessageThread.prototype.view_blank_form = function(){
  var me = this;
  
  $ds(me.msg_parts.inputs['To'].wrapper);
  
  me.msg_parts.inputs['To'].disabled = false;
  me.msg_parts.inputs['To'].value = '';    
  
  me.msg_parts.inputs['Subject'].disabled = false;    
  me.msg_parts.inputs['Subject'].value = '';
  
  me.msg_parts.inputs['Thread'].innerHTML = '';
  
  if(me.inbox_editor && pscript.inbox_text_editor_set == 1){
    me.inbox_editor.editor.setContent('');
  }
  else{
    me.msg_parts.inputs['Message'].value = '';
  }    
  me.show_as(false);
}
  
//  msg_id = mesage id, 
//  parent = div/tab from where msg will be shown, 
//  view_list_tab = name of tab in which list will be viewed, 
//  view_list_div = name of div in which list will be viewed, 
//  req_frm = my inbox / group / event, 
//  show_on_send_tab = tab to be viewed on sending/replying to msg, 
//  show_on_send_div = div to be viewed on sending/replying to msg, 
//  receiver_lst = list of msg receiver

MessageThread.prototype.show_msg = function(msg_id, parent, view_list_tab, view_list_div, req_frm, show_on_send_tab, show_on_send_div, receiver_lst) {
  var me = this;
  
  // set tinymce editor
  if(!me.inbox_editor) {
    pscript.inbox_text_editor_set = 0;
    var theme_adv_btn1 ="fontselect,fontsizeselect,formatselect,indicime,indicimehelp,emotions";
    var theme_adv_btn2 ="bold,italic,underline,|,undo,redo,|,code,forecolor,backcolor,link,unlink,hr,|,sub,sup,|,charmap";
    var theme_adv_btn3 = "";
    
    me.inbox_editor = new TextAreaEditor(me.msg_parts.inputs["Message"], null, me.set_inbox_editor, theme_adv_btn1, theme_adv_btn2, theme_adv_btn3, '300px');
  }
  
  me.req_frm = req_frm;
  me.receiver_lst = receiver_lst;
  me.parent = parent;
  me.view_list_tab = view_list_tab;
  me.view_list_div = view_list_div;
  me.show_on_send_tab = show_on_send_tab;
  me.show_on_send_div = show_on_send_div;
  me.msg_parts.inputs['Send'].btn_click = 0;
  me.msg_parts.inputs['Reply'].btn_click = 0;
  
  if(msg_id) {
    this.cur_message_id = msg_id;
    var args = {'user_name':user, 'cur_msg_id': this.cur_message_id};
    me.view_existing_msg(args);      
  } 
  else {
    this.cur_message_id = null;
    me.view_blank_form();
  }  
  $ds(me.parent);
  
  // reply or send btn
  me.msg_parts.inputs['Send'].onclick = function(){ 
    if(!this.btn_click){
      this.btn_click = 1;
      me.send(me.req_frm, me.receiver_lst, me.show_on_send_tab, me.show_on_send_div); 
    }
  }
  me.msg_parts.inputs['Reply'].onclick = me.msg_parts.inputs['Send'].onclick;
}

MessageThread.prototype.hide = function() {
  var me = this;
  
  $dh(me.wrapper);
  $ds(me.view_list_div);
  me.display = 0;
}

MessageThread.prototype.show_as = function(reply) {
  var me = this;
  
  if(!reply) {
    $dh(me.msg_parts.inputs['Thread'].wrapper);
    $dh(me.msg_parts.inputs['Reply']);
    $ds(me.msg_parts.inputs['Send']);
    me.in_compose = 1;
  }
  else {
    $ds(me.msg_parts.inputs['Thread'].wrapper);
    $ds(me.msg_parts.inputs['Reply']);
    $dh(me.msg_parts.inputs['Send']);
    $dh(me.view_list_div);
    me.in_compose = 1;
  } 
  $ds(me.wrapper);
  me.display = 1;
}

MessageThread.prototype.send_msg = function(arg){
  var me = this;
  var args = arg;
  
  var send_call_back = function(r, rt){
    //var me = this;
    if(r.message == 'true'){
      me.msg_parts.inputs['To'].value = '';
      me.msg_parts.inputs['Subject'].value = '';
      me.msg_parts.inputs['Thread'].innerHTML = '';
      
      if(me.inbox_editor && pscript.inbox_text_editor_set == 1){
        me.inbox_editor.editor.setContent('');
      }
      else{
        me.msg_parts.inputs['Message'].value = '';
      }
      
      if(me.req_frm == 'My Inbox'){
        pscript.msg_struct.sent_lst.msg_li.run();
        me.show_on_send_tab.show();
        $ds(me.show_on_send_div);
        $dh(me.parent);
      }
    }
  }
  
  if(me.cur_message_id==null){
    $c_obj('Message Control','send_message',docstring(args), send_call_back);
  }
  else{  
    $c_obj('Message Control','send_reply',docstring(args), send_call_back);
  }
}

MessageThread.prototype.send = function(req_frm, receiver_lst, show_on_send_tab, show_on_send_div) {
  var me = this;
  me.req_frm = req_frm;
  me.show_on_send_tab = show_on_send_tab;
  me.show_on_send_div = show_on_send_div;
  var args = {'user_name':user};
  
  if(me.inbox_editor && pscript.inbox_text_editor_set == 1){
    args.message = me.inbox_editor.editor.getContent();
  }
  else{
    args.message = me.msg_parts.inputs['Message'].value;
  }
  
  if(me.cur_message_id==null){
    args.subject = me.msg_parts.inputs['Subject'].value;
    args.to_list = me.msg_parts.inputs['To'].value;
    if(!args.to_list) {msgprint('error:Must enter "To:"'); }
    else if(!args.subject) {msgprint('error:Must enter "Subject"'); }
    else me.send_msg(args);
  }
  else{
    var subj = me.msg_parts.inputs['Subject'].value;
    if(!subj.substr(0,3).toLowerCase()=='re:')
      subj = 'Re: ' + subj;
    args.subject = subj;
    args.message_id = me.cur_message_id;
    
    me.send_msg(args);
  }
}

MessageThread.prototype.delete_msg = function(req_frm, parent, view_list_tab, view_list_div) {
  var me = this;
  
  var msg_lst = [];
  var delete_message_dialog;
  me.parent = parent;
  
  if(me.cur_message_id)
    msg_lst.push(me.cur_message_id);
  
  if(msg_lst.length >= 1){
    function set_delete_message_dialog() {
      delete_message_dialog = new Dialog(400, 400, 'Delete Message');
      delete_message_dialog.make_body([
        ['HTML', 'Message', '<div class = "comment">Are you sure, you want to delete this message ?</div>'],
        ['HTML', 'Response', '<div class = "comment" id="delete_message_dialog_response"></div>'],
        ['HTML', 'Delete Message', '<div id="delete_message_btn" style ="height:25px;"></div>']
      ]);
      
      var delete_message_btn1 = $a($i('delete_message_btn'), 'button', 'button');
      delete_message_btn1.innerHTML = 'Yes';
      delete_message_btn1.onclick = function(){ delete_message_dialog.add();}
      
      var delete_message_btn2 = $a($i('delete_message_btn'), 'button', 'button');
      delete_message_btn2.innerHTML = 'No';
      $y(delete_message_btn2,{marginLeft:'4px'});
      
      delete_message_btn2.onclick = function(){ delete_message_dialog.hide();}
      
      delete_message_dialog.onshow = function() {
        $i('delete_message_dialog_response').innerHTML = '';
      }
      
      delete_message_dialog.add = function() {
        if(this.req_frm == 'My Inbox'){
          var args = user + '~~' + this.msg_lst;
          $c_obj('Message Control', 'delete_message', args, function(r, rt){
            if(r.message == 'true'){
              me.hide();
              me.view_list_tab.show(); 
              $ds(me.view_list_div);
              delete_message_dialog.hide();
            }
          });  
        }
      }
    }  
    
    if(!delete_message_dialog)
      set_delete_message_dialog();
    delete_message_dialog.req_frm = req_frm;
    delete_message_dialog.msg_lst = msg_lst;
    delete_message_dialog.view_list_tab = view_list_tab;
    delete_message_dialog.view_list_div = view_list_div;
    delete_message_dialog.show();
  }
}

// ---------------- editor---------------------

var editor_count = 0;

function TextAreaEditor(txt, parent, callback, theme_advanced_btn1, theme_advanced_btn2, theme_advanced_btn3, editor_ht) {

  this.txt = txt;
  this.parent = parent;
  this.callback = callback;
  if(theme_advanced_btn1) this.theme_advanced_btn1 = theme_advanced_btn1;
  if(theme_advanced_btn2) this.theme_advanced_btn2 = theme_advanced_btn2;
  if(theme_advanced_btn3) this.theme_advanced_btn3 = theme_advanced_btn3;
  if(editor_ht) this.editor_ht = editor_ht;

  // load tinyMCE library
  this.load_tiny_mce_library();
}

TextAreaEditor.prototype.load_tiny_mce_library = function() {

  var me = this;
  
  if(!tinymce_loaded) {
    tinymce_loaded = 1;
    tinyMCE_GZ.init(
      {
        themes : "advanced",
        plugins : "style,table,inlinepopups,indicime,emotions",
        languages : "en",
        disk_cache : true
      }, function(){ me.setup_text_area() });
  }
  else {
    me.setup_text_area();
  }
}

TextAreaEditor.prototype.setup_text_area = function() {

  var me = this;
  if(!me.txt) {
    me.txt = $a(me.parent, 'textarea');
  }
  
  editor_count++;
  me.id = 'editor_text_' + editor_count;
  me.txt.setAttribute('id', me.id);
  
  tinyMCE.init({
    theme : "advanced",
    mode : "exact",
    elements: me.id,
    plugins:"table,style,inlinepopups,indicime,emotions",
    theme_advanced_toolbar_location : "top",
    theme_advanced_statusbar_location : "bottom",
    extended_valid_elements: "div[id|dir|class|align|style]",
    
    // w/h
    width: '100%',
    height: me.editor_ht?me.editor_ht:'50px',
    
    // buttons
    //theme_advanced_buttons1 :"bold,italic,underline,strikethrough,blockquote,forecolor,backcolor,bullist,numlist,|,undo,redo,|,image,code,indicime,indicimehelp,emotions",
    theme_advanced_buttons1 : me.theme_advanced_btn1?me.theme_advanced_btn1:"bold,italic,underline,forecolor,backcolor,|,undo,redo,|,link,unlink,indicime,indicimehelp,emotions",
    theme_advanced_buttons2 : me.theme_advanced_btn2?me.theme_advanced_btn2:"",
    theme_advanced_buttons3 : me.theme_advanced_btn3?me.theme_advanced_btn3:"",
    
    // callback function with editor instance.
    init_instance_callback : "editor_init_callback"
  });  

  editor_init_callback = function(inst) {
    me.editor = tinyMCE.get(me.id);
    me.editor.focus();
    
    if(me.callback){
      me.callback(me.editor);
    }
  }  
}