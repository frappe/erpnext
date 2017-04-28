// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Physician', {
  setup: function(frm) {
		frm.set_query('account', 'accounts', function(doc, cdt, cdn) {
			var d  = locals[cdt][cdn];
			return {
				filters: {
					'root_type': 'Income',
					'company': d.company,
				}
			}
		});
	},
  validate: function (frm) {
    schedules = frm.doc.schedule
    for(j=0; j<schedules.length; j++){
      if (validate_schedule(schedules, schedules[j]) == false) return false;
    }
  }
});

frappe.ui.form.on("Physician", "user_id",function(frm) {
	if(frm.doc.user_id){
    frappe.call({
      "method": "frappe.client.get",
      args: {
        doctype: "User",
        name: frm.doc.user_id
      },
      callback: function (data) {
        if(!frm.doc.employee){
          frappe.model.get_value('Employee', {'user_id': frm.doc.user_id}, 'name',
            function(data) {
              if(data)
                frappe.model.set_value(frm.doctype,frm.docname, "employee", data.name)
            })
        }
        if(!frm.doc.first_name)
          frappe.model.set_value(frm.doctype,frm.docname, "first_name", data.message.first_name)
        if(!frm.doc.middle_name)
          frappe.model.set_value(frm.doctype,frm.docname, "middle_name", data.message.middle_name)
        if(!frm.doc.last_name)
          frappe.model.set_value(frm.doctype,frm.docname, "last_name", data.message.last_name)
        if(!frm.doc.mobile_phone)
          frappe.model.set_value(frm.doctype,frm.docname, "mobile_phone", data.message.phone)
      }
    })
  }
});

frappe.ui.form.on("Physician", "employee",
    function(frm) {
	if(frm.doc.employee){
		frappe.call({
		    "method": "frappe.client.get",
		    args: {
		        doctype: "Employee",
		        name: frm.doc.employee
		    },
		    callback: function (data) {
				if(!frm.doc.designation)
					frappe.model.set_value(frm.doctype,frm.docname, "designation", data.message.designation)
				if(!frm.doc.first_name)
					frappe.model.set_value(frm.doctype,frm.docname, "first_name", data.message.employee_name)
				if(!frm.doc.mobile_phone)
					frappe.model.set_value(frm.doctype,frm.docname, "mobile_phone", data.message.cell_number)
				if(!frm.doc.address)
					frappe.model.set_value(frm.doctype,frm.docname, "address", data.message.current_address)
		    }
		})
	}
});

var get_average = function (start, end, limit) {
  if(limit){
    duration = moment.utc(moment(end,"HH:mm:ss").diff(moment(start,"HH:mm:ss"))).format("HH:mm:ss")

    //I am combining the snippets I found in multiple pages.
    //Conversion of hh:mm:ss to seconds, divided by the limit and then again convert to hh:mm:ss.
    var hms =  duration  // your input string
    var a = hms.split(':'); // split it at the colons

    // minutes are worth 60 seconds. Hours are worth 60 minutes.
    var seconds = (+a[0]) * 60 * 60 + (+a[1]) * 60 + (+a[2]);
    var newSeconds= seconds/limit;

    // multiply by 1000 because Date() requires miliseconds
    var date = new Date(newSeconds * 1000);
    var hh = date.getUTCHours();
    var mm = date.getUTCMinutes();
    var ss = date.getSeconds();
    // If you were building a timestamp instead of a duration, you would uncomment the following line to get 12-hour (not 24) time
    // if (hh > 12) {hh = hh % 12;}
    // These lines ensure you have two-digits
    if (hh < 10) {hh = "0"+hh;}
    if (mm < 10) {mm = "0"+mm;}
    //if (ss < 10) {ss = "0"+ss;}
    // This formats your string to HH:MM:SS
    var t = hh+":"+mm+":00";
    return t
  };
};

var validate_schedule = function (schedules, child) {
  start = new Date(new Date().toDateString() + ' ' + child.start)
  end = new Date(new Date().toDateString() + ' '+ child.end)
  if(start >= end){
    frappe.msgprint(__("From and To times are not valid in line {0}", [child.idx]));
    return false
  };
  for(i=0; i<schedules.length; i++){
    if(schedules[i].day === child.day && schedules[i].name !== child.name){
      sch_start = new Date(new Date().toDateString() + ' ' + schedules[i].start)
      sch_end = new Date(new Date().toDateString() + ' '+ schedules[i].end)
      if ((start > sch_start   && start < sch_end) || (end > sch_start  && end < sch_end) || (start >= sch_start  && end <= sch_end)){
        frappe.msgprint(__("Schedule for {0}  {1} - {2} and {3} - {4} overlap", [child.day, sch_start.toTimeString(), sch_end.toTimeString(), start.toTimeString(), end.toTimeString()]))
        return false;
      }
    };
  };
  return true;
};

frappe.ui.form.on("Work Schedule", {
  limit: function(frm, cdt, cdn) {
  	var child = locals[cdt][cdn]
    avg = get_average(child.start, child.end, child.limit)
    frappe.model.set_value(cdt, cdn, 'average', avg)
    if(child.start && child.end && child.day){
      if (validate_schedule(frm.doc.schedule, child) !== true ){
        frappe.msgprint("Schedules overlap")
        return
      }
    }
  },
});
