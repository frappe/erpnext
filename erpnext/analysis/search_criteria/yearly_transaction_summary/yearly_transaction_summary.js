report.customize_filters = function() {
  this.mytabs.items['Select Columns'].hide()
  this.hide_all_filters();
  this.add_filter({fieldname:'company', label:'Company', fieldtype:'Link', options:'Company', report_default:sys_defaults.company, ignore : 1, parent:'Profile'});
  this.add_filter({fieldname:'from_fiscal_year', label:'From Fiscal Year', fieldtype:'Link', options:'Fiscal Year', report_default:sys_defaults.fiscal_year, ignore : 1, parent:'Profile'});
  this.add_filter({fieldname:'to_fiscal_year', label:'To Fiscal Year', fieldtype:'Link', options:'Fiscal Year', report_default:sys_defaults.fiscal_year, ignore : 1, parent:'Profile'});
  this.add_filter({fieldname:'date', label:'Date', fieldtype:'Date', options:'',ignore : 1, parent:'Profile'});
}

report.aftertableprint = function(t) {
   $yt(t,'*',1,{NEWLINE:'<br>'});
}