

report.customize_filters = function() {
  this.mytabs.items['Select Columns'].hide()
  this.hide_all_filters();
  this.add_filter({fieldname:'fiscal_year', label:'Fiscal Year', fieldtype:'Link', options:'Fiscal Year', report_default:sys_defaults.fiscal_year, ignore : 1, parent:'DocType'});
  this.add_filter({fieldname:'company', label:'Company', fieldtype:'Link', options:'Company', report_default:sys_defaults.company, ignore : 1, parent:'DocType'});
  this.add_filter({fieldname:'period', label:'Period', fieldtype:'Select', options:'Monthly'+NEWLINE+'Quarterly'+NEWLINE+'Half Yearly'+NEWLINE+'Annual',ignore : 1, parent:'DocType'});
}

report.aftertableprint = function(t) {
   $yt(t,'*',1,{NEWLINE:'<br>'});
}