report.customize_filters = function() {
  this.hide_all_filters();
  this.mytabs.items['Select Columns'].hide();
  this.mytabs.items['More Filters'].hide();
  this.add_filter({fieldname:'based_on', label:'Based On', fieldtype:'Select', options:'Territory'+NEWLINE+'Item Group',ignore:1,parent:'Serial No',in_first_page:1, report_default:'Item Group'});
}

report.aftertableprint = function(t) {
   $yt(t,'*',1,{whiteSpace:'pre'});
}