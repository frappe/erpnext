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

cur_frm.cscript.onload = function(doc,cdt,cdn){
  cur_frm.log_div = $a(cur_frm.fields_dict['import_log1'].wrapper,'div','',{border:'1px solid #CCC', backgroundColor:'#DDD',width : '100%', height : '300px', overflow : 'auto'});
  hide_field('import_log1')
  doc.att_fr_date = get_today();
  doc.file_list = '';
  doc.overwrite = 0;
  refresh_many(['att_fr_date','file_list','overwrite']);


}

//download attendance template - csv file
cur_frm.cscript.get_template = function(doc,cdt,cdn){

  if(doc.att_to_date && !doc.att_fr_date)
    alert("Please enter 'Attendance To Date'");
  else if(doc.att_to_date && doc.att_fr_date && doc.att_to_date < doc.att_fr_date)
    alert("Attendance to date cannot be less than from date.");
  else
    $c_obj_csv(make_doclist(cdt,cdn),'get_att_list','');
}

//---------------------------------------------------------
cur_frm.cscript.import = function(doc,cdt,cdn){
  if(!doc.file_list){
    alert("Please upload attendance data CSV file");
  }
  else{
    var call_back = function(r,rt){
      cur_frm.log_div.innerHTML = '';
      if(r.message)
        cur_frm.log_div.innerHTML = r.message;
         
      cur_frm.cscript.refresh(doc,cdt,cdn);
    }

    $c_obj(make_doclist(cdt,cdn),'import_att_data','',call_back);
  }
  cur_frm.cscript.refresh(doc,cdt,cdn);
}

//====================================================
cur_frm.cscript.refresh = function(doc,cdt,cdn){
  if(cur_frm.log_div.innerHTML == '')
    hide_field('import_log1');
  else
    unhide_field('import_log1');
  refresh_field('import_log1');

}
