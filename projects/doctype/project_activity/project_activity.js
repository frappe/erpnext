cur_frm.cscript.onload = function(doc, dt, dn) {
  // created?
  if(cur_frm.mylist) {
     cur_frm.mylist.run();
     return;
  } else {

    // create a new listing
    var lst = new Listing('Activities Updates');

    lst.colwidths = ['5%','30%','40%','25%'];
 
    // define options
    var opts = {};

    opts.head_main_style = {};
    opts.cell_style = { padding:'3px 2px', borderRight : '0px', borderBottom : '1px solid #AAA', verticalAlign: 'top'}
    opts.head_style = { padding:'3px 2px', borderBottom : '1px solid #AAA'}
    opts.alt_cell_style = {};
    opts.hide_print = 1;
    opts.no_border = 1;

    opts.hide_export = 1;
    opts.hide_print = 1;
    opts.hide_rec_label = 1;

    lst.opts = opts;
  
    // query
    lst.get_query = function() {
      var doc = cur_frm.doc;
      this.query = "select owner,creation,`update`, hours from `tabProject Activity Update` where parent = '"+doc.name+"'";
      this.query_max = "select count(*) from `tabProject Activity Update` where parent = '"+doc.name+"'";
    }

    lst.show_cell = function(cell,ri,ci,d){
 
      // owner and date
      if (ci==0){ 
        var d1 = $a(cell,'div');
        var img = $a(cell,'img','',{width:'40px'});
        set_user_img(img,d[ri][0])
        var d2 = $a(cell,'div');
        d2.innerHTML =  d[ri][0] + ' on: ' + date.str_to_user(d[ri][1]);
      }

      // update
      if(ci==1) {
        cell.innerHTML =  replace_newlines(d[ri][2]);
      }

      // Hours
      if (ci==2) { 
        cell.innerHTML = d[ri][3] + ' hrs';
      }
    }
  
    lst.make(cur_frm.fields_dict['Updates HTML'].wrapper);
    cur_frm.mylist = lst;
    lst.run();
  }
}

cur_frm.cscript.refresh = function(doc, dt, dn) {

  // show activities only after project is saved

  var fl = ['new_update','Add','hours','Updates HTML'];
  if(doc.__islocal) { 
    hide_field(fl);}
  else { 
    unhide_field(fl); }
}

cur_frm.cscript['Add'] = function(doc, dt, dn) {
  var callback = function(r,rt) {
    
    // refresh listing
    cur_frm.mylist.run();

  }
  $c_obj([doc],'add_update','',callback);
}