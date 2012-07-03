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
        img.src = wn.user_info(d[ri][0]).image;
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
  
    lst.make(cur_frm.fields_dict['updates_html'].wrapper);
    cur_frm.mylist = lst;
    lst.run();
  }
}

cur_frm.cscript.refresh = function(doc, dt, dn) {

  // show activities only after project is saved

  var fl = ['new_update','add','hours','updates_html'];
  if(doc.__islocal) { 
    hide_field(fl);}
  else { 
    unhide_field(fl); }
}

cur_frm.cscript.add = function(doc, dt, dn) {
  var callback = function(r,rt) {
    
    // refresh listing
    cur_frm.mylist.run();

  }
  $c_obj(make_doclist(doc.doctype, doc.name),'add_update','',callback);
}
