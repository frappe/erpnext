// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Nepali Date', {


	refresh: function(frm) {
        frm.call({
			method:'check_date',
			doc:frm.doc,
			callback: function(r){
				if(r.message){
					console.log("-- - date --------- ", r.message)
				}
			}
		});
	}
});

frappe.ui.form.on('Nepali Date', {
	refresh(frm) {
		// your code here

		var cal = document.createElement("link");
        cal.rel = 'stylesheet';
        cal.type = "text/css";
        // cal.href = "https://unpkg.com/nepali-date-picker@latest/dist/nepaliDatePicker.min.css";
        cal.href = "http://nepalidatepicker.sajanmaharjan.com.np/nepali.datepicker/css/nepali.datepicker.v3.6.min.css";
        cal.onload = function(){
        console.log("jQuery Nepali Calender Loaded");
        };
            document.head.appendChild(cal);
                //   $.getScript("https://unpkg.com/nepali-date-picker@latest/dist/jquery.nepaliDatePicker.min.js", function () {
                    $.getScript("http://nepalidatepicker.sajanmaharjan.com.np/nepali.datepicker/js/nepali.datepicker.v3.6.min.js",
                     function () {  
                //   $(".example").nepaliDatePicker({
                //         dateFormat:"%D, %M %d, %y"
                //     });
                
                //    $(".example").nepaliDatePicker();
                    // new BS2AD(vdate: object): string;
                    var mainInput = document.getElementById("nepali-datepicker");
                     mainInput.nepaliDatePicker();
                    console.log("-------*********");
                                       
                   frm.doc.v_date = $(".example").nepaliDatePicker();
                   console.log(frm.doc.v_date)
                  }                                  
      );
      var data = document.getElementById("nepali-datepicker");
      console.log("this is date", data.get)
	}

    g_date
})
