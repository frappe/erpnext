// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.


wn.require("public/app/js/utils.js");
wn.provide("erpnext.hr");

erpnext.hr.AttendanceControlPanel = erpnext.utils.Controller.extend({
	onload: function() {
		this.frm.set_value("att_fr_date", get_today());
		this.frm.set_value("att_to_date", get_today());
	},
	
	refresh: function() {
		this.show_upload();
	},
	
	get_template:function() {
		if(!this.frm.doc.att_fr_date || !this.frm.doc.att_to_date) {
			msgprint("Attendance From Date and Attendance To Date is mandatory");
			return;
		}
		window.location.href = repl(wn.request.url + 
			'?cmd=%(cmd)s&from_date=%(from_date)s&to_date=%(to_date)s', {
				cmd: "hr.doctype.upload_attendance.upload_attendance.get_template",
				from_date: this.frm.doc.att_fr_date,
				to_date: this.frm.doc.att_to_date,
			});
	},
	
	show_upload: function() {
		var me = this;
		var $wrapper = $(cur_frm.fields_dict.upload_html.wrapper).empty();
		var upload_area = $('<div id="dit-upload-area"></div>').appendTo($wrapper);
		
		// upload
		wn.upload.make({
			parent: $('#dit-upload-area'),
			args: {
				method: 'hr.doctype.upload_attendance.upload_attendance.upload'
			},
			sample_url: "e.g. http://example.com/somefile.csv",
			callback: function(r) {
				var $log_wrapper = $(cur_frm.fields_dict.import_log.wrapper).empty();
				var log_area = $('<div id="dit-output"></div>').appendTo($log_wrapper);
				
				$wrapper.find(".dit-progress-area").toggle(false);
				if(!r.messages) r.messages = [];
				// replace links if error has occured
				if(r.exc || r.error) {
					r.messages = $.map(r.messages, function(v) {
						var msg = v.replace("Inserted", "Valid")
							.replace("Updated", "Valid").split("<");
						if (msg.length > 1) {
							v = msg[0] + (msg[1].split(">").slice(-1)[0]);
						} else {
							v = msg[0];
						}
						return v;
					});

					r.messages = ["<h4 style='color:red'>Import Failed!</h4>"]
						.concat(r.messages)
				} else {
					r.messages = ["<h4 style='color:green'>Import Successful!</h4>"].
						concat(r.messages)
				}
				console.log(r.messages);
				
				$.each(r.messages, function(i, v) {
					var $p = $('<p>').html(v).appendTo('#dit-output');
					if(v.substr(0,5)=='Error') {
						$p.css('color', 'red');
					} else if(v.substr(0,8)=='Inserted') {
						$p.css('color', 'green');
					} else if(v.substr(0,7)=='Updated') {
						$p.css('color', 'green');
					} else if(v.substr(0,5)=='Valid') {
						$p.css('color', '#777');
					}
				});
			}
		});
		
		// rename button
		$('#dit-upload-area form input[type="submit"]')
			.attr('value', 'Upload and Import')
			.click(function() {
				$wrapper.find(".dit-progress-area").toggle(true);
			});
	}
})

cur_frm.cscript = new erpnext.hr.AttendanceControlPanel({frm: cur_frm});