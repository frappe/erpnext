// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Job Card', {
	refresh: function(frm) {
		if (frm.doc.items && frm.doc.docstatus==1) {
			if (frm.doc.for_quantity != frm.doc.transferred_qty) {
				frm.add_custom_button(__("Material Request"), () => {
					frm.trigger("make_material_request");
				});
			}

			if (frm.doc.for_quantity != frm.doc.transferred_qty) {
				frm.add_custom_button(__("Material Transfer"), () => {
					frm.trigger("make_stock_entry");
				});
			}
		}

		if (frm.doc.docstatus == 0) {
			if (!frm.doc.actual_start_date || !frm.doc.actual_end_date) {
				frm.trigger("make_dashboard");
			}

			if (!frm.doc.actual_start_date) {
				frm.add_custom_button(__("Start Job"), () => {
					frm.set_value('actual_start_date', frappe.datetime.now_datetime());
					frm.save();
				});
			} else if (!frm.doc.actual_end_date) {
				frm.add_custom_button(__("Complete Job"), () => {
					frm.set_value('actual_end_date', frappe.datetime.now_datetime());
					frm.save();
				});
			}
		}
	},

	make_dashboard: function(frm) {
		if(frm.doc.__islocal)
			return;

		frm.dashboard.refresh();
		const timer = `
			<div class="stopwatch" style="font-weight:bold">
				<span class="hours">00</span>
				<span class="colon">:</span>
				<span class="minutes">00</span>
				<span class="colon">:</span>
				<span class="seconds">00</span>
			</div>`;

		var section = frm.dashboard.add_section(timer);

		if (frm.doc.actual_start_date) {
			let currentIncrement = moment(frappe.datetime.now_datetime()).diff(moment(frm.doc.actual_start_date),"seconds");
			initialiseTimer();

			function initialiseTimer() {
				const interval = setInterval(function() {
					var current = setCurrentIncrement();
					updateStopwatch(current);
				}, 1000);
			}

			function updateStopwatch(increment) {
				var hours = Math.floor(increment / 3600);
				var minutes = Math.floor((increment - (hours * 3600)) / 60);
				var seconds = increment - (hours * 3600) - (minutes * 60);

				$(section).find(".hours").text(hours < 10 ? ("0" + hours.toString()) : hours.toString());
				$(section).find(".minutes").text(minutes < 10 ? ("0" + minutes.toString()) : minutes.toString());
				$(section).find(".seconds").text(seconds < 10 ? ("0" + seconds.toString()) : seconds.toString());
			}

			function setCurrentIncrement() {
				currentIncrement += 1;
				return currentIncrement;
			}
		}
	},

	for_quantity: function(frm) {
		frm.doc.items = [];
		frm.call({
			method: "get_required_items",
			doc: frm.doc,
			callback: function() {
				refresh_field("items");
			}
		})
	},

	make_material_request: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.manufacturing.doctype.job_card.job_card.make_material_request",
			frm: frm,
			run_link_triggers: true
		});
	},

	make_stock_entry: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.manufacturing.doctype.job_card.job_card.make_stock_entry",
			frm: frm,
			run_link_triggers: true
		});
	},

	timer: function(frm) {
		return `<button> Start </button>`
	}
});