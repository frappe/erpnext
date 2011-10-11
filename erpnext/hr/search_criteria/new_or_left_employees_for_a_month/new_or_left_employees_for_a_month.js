report.customize_filters = function() {
  var d = new Date();
  
  var month=["January","February","March","April","May","June","July","August","September","October","November","December"]
  
  this.add_filter({fieldname:'month', label:'Month',fieldtype:'Select', options:"January"+NEWLINE+"February"+NEWLINE+"March"+NEWLINE+"April"+NEWLINE+"May"+NEWLINE+"June"+NEWLINE+"July"+NEWLINE+"August"+NEWLINE+"September"+NEWLINE+"October"+NEWLINE+"November"+NEWLINE+"December",report_default : month[d.getMonth()],ignore : 1, parent:'Employee'});
  
  this.filter_fields_dict['Employee'+FILTER_SEP +'Month'].df.in_first_page = 1;
  this.filter_fields_dict['Employee'+FILTER_SEP +'Status'].df.in_first_page = 1;
  this.filter_fields_dict['Employee'+FILTER_SEP +'Status'].df.report_default = 'Active';
  
  this.add_filter({fieldname:'year', label:'Year',fieldtype:'Select', options:"2000"+NEWLINE+"2001"+NEWLINE+"2002"+NEWLINE+"2003"+NEWLINE+"2004"+NEWLINE+"2005"+NEWLINE+"2006"+NEWLINE+"2007"+NEWLINE+"2008"+NEWLINE+"2009"+NEWLINE+"2010"+NEWLINE+"2011",report_default : d.getFullYear(),ignore : 1, parent:'Employee'});
  
  this.filter_fields_dict['Employee'+FILTER_SEP +'Year'].df.in_first_page = 1;
}

report.get_query = function() {

  emp_month = this.filter_fields_dict['Employee'+FILTER_SEP+'Month'].get_value();
  emp_year = this.filter_fields_dict['Employee'+FILTER_SEP+'Year'].get_value();
  emp_status = this.filter_fields_dict['Employee'+FILTER_SEP+'Status'].get_value();

  // month and year mandatory
  if ((emp_month == '') || (emp_year == '')) {
    alert("Please enter Month and Year");
    return;
  }

  month={"January":"1", "February":"2", "March":"3", "April":"4","May":"5", "June":"6", "July":"7","August":"8", "September":"9", "October":"10", "November":"11", "December":"12"}
  
  mnt = ''
  for(m=0; m<emp_month.length;m++){
    if(mnt== '') mnt = "("+month[emp_month[m]];
    else mnt +=", "+month[emp_month[m]]; 
  }
  mnt +=")"
  c1 = '(MONTH(t1.date_of_joining) in '+mnt+' AND YEAR(t1.date_of_joining) = "'+emp_year+'")';
  c2 = '(MONTH(t1.relieving_date) in '+mnt+' AND YEAR(t1.relieving_date) = "'+emp_year+'")';

  if(emp_status == 'Active')
    cond = c1;  
  else if (emp_status == 'Left')
    cond = c2;
  else
    cond = c1 + ' OR '+c2;
  
  var q = 'SELECT t1.name AS "ID", t1.employee_name AS "Employee Name", t1.employee_number AS "Employee Number" FROM `tabEmployee` t1 WHERE '+cond;

  return q;
}
