// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Process Payroll", {
	refresh: function(frm) {
		frm.disable_save();
		frm.trigger("toggle_fields");
		frm.trigger("set_month_dates");
	},
	
	month: function(frm) {
		frm.trigger("set_month_dates");
	},
	
	fiscal_year: function(frm) {
		frm.trigger("set_month_dates");
	},
	
	salary_slip_based_on_timesheet: function(frm) {
		frm.trigger("toggle_fields")
	},

	toggle_fields: function(frm) {
		frm.toggle_display(['from_date','to_date'],
			cint(frm.doc.salary_slip_based_on_timesheet)==1);
		frm.toggle_display(['fiscal_year', 'month'],
			cint(frm.doc.salary_slip_based_on_timesheet)==0);
	},
	
	set_month_dates: function(frm) {
		if (!frm.doc.salary_slip_based_on_timesheet){
			frappe.call({
				method:'erpnext.hr.doctype.process_payroll.process_payroll.get_month_details',
				args:{
					year: frm.doc.fiscal_year, 
					month: frm.doc.month
				},
				callback: function(r){
					if (r.message){
						frm.set_value('from_date', r.message.month_start_date);
						frm.set_value('to_date', r.message.month_end_date);			
					}
				}
			})
		}
	}
})

cur_frm.cscript.onload = function(doc,cdt,cdn){
		if(!doc.month) {
			var today=new Date();
			month = (today.getMonth()+01).toString();
			if(month.length>1) doc.month = month;
			else doc.month = '0'+month;
		}
		if(!doc.fiscal_year) doc.fiscal_year = sys_defaults['fiscal_year'];
		refresh_many(['month', 'fiscal_year']);
}

cur_frm.cscript.display_activity_log = function(msg) {
	if(!cur_frm.ss_html)
		cur_frm.ss_html = $a(cur_frm.fields_dict['activity_log'].wrapper,'div');
	if(msg) {
		cur_frm.ss_html.innerHTML =
			'<div class="padding"><h4>'+__("Activity Log:")+'</h4>'+msg+'</div>';
	} else {
		cur_frm.ss_html.innerHTML = "";
	}
}

//Create salary slip
//-----------------------
cur_frm.cscript.create_salary_slip = function(doc, cdt, cdn) {
	cur_frm.cscript.display_activity_log("");
	var callback = function(r, rt){
		if (r.message)
			cur_frm.cscript.display_activity_log(r.message);
	}
	return $c('runserverobj', args={'method':'create_sal_slip','docs':doc},callback);
}

cur_frm.cscript.submit_salary_slip = function(doc, cdt, cdn) {
	cur_frm.cscript.display_activity_log("");

	frappe.confirm(__("Do you really want to Submit all Salary Slip from {0} to {1}", [doc.from_date, doc.to_date]), function() {
		// clear all in locals
		if(locals["Salary Slip"]) {
			$.each(locals["Salary Slip"], function(name, d) {
				frappe.model.remove_from_locals("Salary Slip", name);
			});
		}

		var callback = function(r, rt){
			if (r.message)
				cur_frm.cscript.display_activity_log(r.message);
		}

		return $c('runserverobj', args={'method':'submit_salary_slip','docs':doc},callback);
	});
}

cur_frm.cscript.make_bank_entry = function(doc,cdt,cdn){
    if(doc.company && doc.from_date && doc.to_date){
		return cur_frm.cscript.reference_entry(doc,cdt,cdn);
    } else {
  	  msgprint(__("Company, From Date and To Date is mandatory"));
    }
}

cur_frm.cscript.reference_entry = function(doc,cdt,cdn){
	var dialog = new frappe.ui.Dialog({
		title: __("Bank Transaction Reference"),
		fields: [
			{
				"label": __("Reference Number"), 
				"fieldname": "reference_number",
				"fieldtype": "Data", 
				"reqd": 1
			},
			{
				"label": __("Reference Date"), 
				"fieldname": "reference_date",
				"fieldtype": "Date", 
				"reqd": 1,
				"default": get_today()
			}
		]
	});
	dialog.set_primary_action(__("Make"), function() {
		args = dialog.get_values();
		if(!args) return;
		dialog.hide();
		return frappe.call({
			doc: cur_frm.doc,
			method: "make_journal_entry",
			args: {"reference_number": args.reference_number, "reference_date":args.reference_date},
			callback: function(r) {
				if (r.message)
					cur_frm.cscript.display_activity_log(r.message);
			}
		});
	});
	dialog.show();
}