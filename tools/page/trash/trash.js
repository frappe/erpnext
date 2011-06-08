pscript['onload_Trash'] = function() {

  // header and toolbar
  var h = new PageHeader('trash_header','Trash Bin','Restore the documents that you have trashed')
  
  if(!pscript.trash_bin) pscript.trash_bin = new pscript.Trash();
}

pscript.Trash = function() {
  // create UI elements
  this.wrapper = $i('trash_div');
  
  this.head = $a(this.wrapper, 'div');
  this.body = $a(this.wrapper, 'div');
  $y(this.body, {margin:'8px'})

  this.make_head();
  this.load_masters();
}

// Make Button
// ------------
pscript.Trash.prototype.make_button = function(label, area){
  var me = this;
  var w = $a(area, 'div', '', {margin:'8px'});
  var t = make_table(w,1,1,'400px',['50%','50%']);
  var s = $a($td(t,0,0),'button');
  s.innerHTML = label;
  s.wrapper = w;
  return s;
}


// Make Head
// -------------
pscript.Trash.prototype.make_head = function() {
  var me = this;
  
  var make_select = function(label) {
    var w = $a(me.head, 'div', '', {margin:'8px'});
    var t = make_table(w,1,2,'400px',['50%','50%']);
    $td(t,0,0).innerHTML = label;
    var s = $a($td(t,0,1),'select','',{width:'140px'});
    s.wrapper = w;
    return s;
  }
  
  // Select Master Name
  this.master_select = make_select('Select Master');
    
  var me = this;
  // Get Records
  this.get_records_button = me.make_button('Get Records', me.head);
  this.get_records_button.onclick = function() {
    me.get_records();
  }
}


// Load Masters
// -------------
pscript.Trash.prototype.load_masters = function(){
  var me = this;
  var callback = function(r, rt){
    // Masters
    empty_select(me.master_select);
    add_sel_options(me.master_select,add_lists(['All'], r.message), 'All');
  }
  $c_obj('Trash Control','get_masters','',callback);
}


// Get Records
// -----------
pscript.Trash.prototype.get_records = function(){
  var me = this;
  me.body.innerHTML = '';
  var callback = function(r, rt){
    if(r.message) me.generate_trash_records(r.message);
    else msgprint("No Records Found");
  }
  $c_obj('Trash Control','get_trash_records',sel_val(me.master_select),callback);
}


// Generate Trash Records
// -----------------------
pscript.Trash.prototype.generate_trash_records = function(rec_dict){
  var me = this;
  pscript.all_checkboxes = [];
  mnames = keys(rec_dict).sort();
  for(var i = 0; i < mnames.length; i ++){
    var head = $a(me.body, 'h3'); head.innerHTML = mnames[i];
    var rec_table = make_table(me.body,rec_dict[mnames[i]].length,2,'375px',['350px','25px'],{border:'1px solid #AAA',padding:'2px'});
    for(var j = 0; j < rec_dict[mnames[i]].length; j++){
      $a_input($td(rec_table,j,0), 'data');
      $td(rec_table,j,0).innerHTML = rec_dict[mnames[i]][j];
      var chk = $a_input($td(rec_table,j,1), 'checkbox');
      chk.master = mnames[i];
      chk.record = rec_dict[mnames[i]][j];
      pscript.all_checkboxes.push(chk);
    }
  }
  this.restore_button = me.make_button('Restore Selected', me.body);
  this.restore_button.onclick = function() {
    me.restore_records(0);
  }
  this.restore_all_button = me.make_button('Restore All', me.body);
  this.restore_all_button.onclick = function() {
    me.restore_records(1);
  }
}


// Restore Records
// ---------------
pscript.Trash.prototype.restore_records = function(restore_all){
  var me = this;
  var out = {};
  for(i in pscript.all_checkboxes) {
    c = pscript.all_checkboxes[i];
    if (restore_all || (!restore_all && c.checked)) {
      if(!out[c.master]) out[c.master] = [c.record];
      else {out[c.master].push(c.record);}
    }
  }
  $c_obj('Trash Control','restore_records',JSON.stringify(out),function(r, rt){me.get_records();})
}