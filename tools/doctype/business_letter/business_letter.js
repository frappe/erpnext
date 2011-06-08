$import(Tips Common)

cur_frm.fields_dict['template'].get_query=function(doc,cdt,cdn){
  return "SELECT `tabBusiness Letter Template`.name FROM `tabBusiness Letter Template` WHERE `tabBusiness Letter Template`.letter_type='"+doc.letter_type+"' AND `tabBusiness Letter Template`.name like '%s' LIMIT 50"
}

cur_frm.cscript.template = function(doc,cdt,cdn){
  //set title as like template
  doc.title = doc.template;
  refresh_field('title');

  //set print heading as title 
  cur_frm.pformat.print_heading=doc.title;
  cur_frm.pformat.print_subheading = ' ';

  //call set_content function to pull content as per template selected
  $c_obj([doc], 'set_content', '',function(r, rt) { refresh_field('content');});
}

cur_frm.cscript.title= function(doc,cdt,cdn){
  //set print heading on title change
  cur_frm.pformat.print_heading=doc.title;
  cur_frm.pformat.print_subheading = ' ';
}

cur_frm.cscript.refresh= function(doc,cdt,cdn){
  cur_frm.cscript.get_tips(doc, cdt, cdn);
  //set print heading on refresh
  cur_frm.pformat.print_heading=doc.title;
  cur_frm.pformat.print_subheading = ' ';
}

cur_frm.cscript.onload= function(doc,cdt,cdn){
  cur_frm.cscript.get_tips(doc, cdt, cdn);
  //set print heading
  cur_frm.pformat.print_heading=doc.title;
  cur_frm.pformat.print_subheading = ' ';
}
