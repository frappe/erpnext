cur_frm.cscript.onload = function(doc,cdt,cdn){
  cur_frm.log_div = $a(cur_frm.fields_dict['Import Log1'].wrapper,'div','',{border:'1px solid #CCC', backgroundColor:'#DDD',width : '100%', height : '300px', overflow : 'auto'});
  hide_field('Import Log1')
  doc.att_fr_date = get_today();
  doc.file_list = '';
  doc.overwrite = 0;
  refresh_many(['att_fr_date','file_list','overwrite']);


}

//download attendance template - csv file
cur_frm.cscript['Get Template'] = function(doc,cdt,cdn){

  if(doc.att_to_date && !doc.att_fr_date)
    alert("Please enter 'Attendance To Date'");
  else if(doc.att_to_date && doc.att_fr_date && doc.att_to_date < doc.att_fr_date)
    alert("Attendance to date cannot be less than from date.");
  else
    $c_obj_csv(make_doclist(cdt,cdn),'get_att_list','');
}

//---------------------------------------------------------
cur_frm.cscript['Import'] = function(doc,cdt,cdn){
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
    hide_field('Import Log1');
  else
    unhide_field('Import Log1');
  refresh_field('Import Log1');

}