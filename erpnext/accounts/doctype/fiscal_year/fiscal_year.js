// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on('Fiscal Year', {

	onload: function(frm) {
		if(frm.doc.__islocal) {
			frm.set_value("year_start_date",
				frappe.datetime.add_days(frappe.defaults.get_default("year_end_date"), 1));

				
		}

	},
	refresh: function (frm) {
		if (!frm.doc.__islocal && (frm.doc.name != frappe.sys_defaults.fiscal_year)) {
			frm.add_custom_button(__("Set as Default"), () => frm.events.set_as_default(frm));
			frm.set_intro(__("To set this Fiscal Year as Default, click on 'Set as Default'"));
		} else {
			frm.set_intro("");
		}
	},
	set_as_default: function(frm) {
		return frm.call('set_as_default');
	},
	year_start_date: function(frm) {
		// if (!frm.doc.is_short_year) {
		// 	let year_end_date =
		// 		frappe.datetime.add_days(frappe.datetime.add_months(frm.doc.year_start_date, 12), -1);
		// 	frm.set_value("year_end_date", year_end_date);
		// }

		// custom code for vikram calendar year start
		frm.call({
			method:'vikram_date',
			doc:frm.doc,
			callback: function(r){
				if(r.message){
					console.log("-- - date start--------- ", r.message)
					frm.doc.v_start_date = r.message
					frm.refresh_field("v_start_date")
				}
			}
		});
	},

	year_end_date: function(frm){
		// custom code for vikram calendar year start
		frm.call({
			method:'vikram_date_end',
			doc:frm.doc,
			callback: function(e){
				if(e.message){
					console.log("-- - date end--------- ", e.message)
					frm.doc.v_end_date = e.message
					frm.refresh_field("v_end_date")	
					
				}
			}
		});

	},


	onload(frm) {
				var cal = document.createElement("link");
				cal.rel = 'stylesheet';
				cal.type = "text/css";
				cal.href = "http://nepalidatepicker.sajanmaharjan.com.np/nepali.datepicker/css/nepali.datepicker.v3.6.min.css";
				cal.onload = function(){
				console.log("jQuery Nepali Calender Loaded");
				};
					document.head.appendChild(cal);
							$.getScript("http://nepalidatepicker.sajanmaharjan.com.np/nepali.datepicker/js/nepali.datepicker.v3.6.min.js",
							 function () {  
					
							var mainInput = document.querySelectorAll('[data-fieldname ="v_start_date"]')
							mainInput.nepaliDatePicker();

							var mainInput1 = document.querySelectorAll('[data-fieldname ="v_end_date"]')
							mainInput1.nepaliDatePicker();
						
							console.log("per defined",NepaliFunctions.GetCurrentBsDate());
							
							 });
			
			},

});
