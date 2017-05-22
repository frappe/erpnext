// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Attendance Hours', {
	refresh: function(frm) {

	}
});
$('[data-fieldname="attendance_hours"]').on('keypress', numbersonly);

function numbersonly(e) {
  var unicode = e.charCode ? e.charCode : e.keyCode;
  if (unicode != 8) { //if the key isn't the backspace key (which we should allow)
    if (unicode < 46 || unicode > 57) //if not a number
      return false; //disable key press
  }
}

cur_frm.cscript.custom_start_time = function(doc, cdt, cd, cdn) {
    // alert('');
    if( doc.attendance_hours ){
        var end_time = moment(doc.start_time, 'hh:mm:ss').add(doc.attendance_hours, 'hours');
        var allow_start_time = moment(doc.start_time, 'hh:mm:ss').add("15", 'minutes');
        var absent_time = moment(doc.start_time, 'hh:mm:ss').add("2", 'hours');
        var allow_end_time = moment(doc.start_time, 'hh:mm:ss').add(doc.attendance_hours, 'hours').add("-15", 'minutes');
        // debugger;
        // cu
        cur_frm.set_value('end_time',  end_time.format('HH:mm:ss'));
        cur_frm.set_value('allow_start_time',  allow_start_time.format('HH:mm:ss'));
        cur_frm.set_value('absent_time',  absent_time.format('HH:mm:ss'));
        cur_frm.set_value('allow_end_time',  allow_end_time.format('HH:mm:ss'));

    }
}
