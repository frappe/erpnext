// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// let arc = "<h1>Hello</h1>"

frappe.ui.form.on('Crop', {
	refresh: (frm) => {
		frappe.require([
			"assets/frappe/js/lib/snap.svg-min.js",
			"assets/frappe/js/lib/frappe-gantt/frappe-gantt.js"
		], init_gantt);
		function init_gantt() {
			let cycles = [];
			frm.doc.crop_cycle.forEach( (crop_cycle, index) => {
				let cycle = {
					id: `${index}`,
					name: `${frm.docname}`,
					scientific_name: `${frm.doc.scientific_name}`,
					start: `${crop_cycle.start_date}`,
					end: `${crop_cycle.end_date}`,
					progress: `${crop_cycle.progress}`
				};
				cycles.push(cycle);
			});
			frm.fields_dict.crop_gantt.$wrapper.append('<svg id="crop_gantt" width="100" height="100">');
			frm.fields_dict.crop_gantt.$wrapper.prevObject.css("overflow", "auto");
			frm.gantt = new Gantt('#crop_gantt', cycles, {
				on_date_change: function(task) {
					edit_crop_cycle(task);
				},
				on_progress_change: function(task) {
					edit_crop_cycle(task);
				},
				custom_popup_html: function(task) {
					const end_date = task._end.format('MMM D');
					return `
						<div class="details-container">
							<h5>${task.name}</h5>
							<p><b>Scientific name:</b> ${task.scientific_name}</p>
							<p><b>Progress:</b> ${task.progress}% completed!</p>
							<p>Expected to finish by ${end_date}</p>
						</div>
					`;
				}
			});

			frm.gantt.change_view_mode('Month');
		}
		function edit_crop_cycle(task) {
			let old_crop_cycle = cur_frm.doc.crop_cycle;
			frm.set_value("crop_cycle");
			let new_crop_cycle = {};
			old_crop_cycle.forEach((cycle, index) => {
				let crop_cycle = {};
				if (index == task.id){
					crop_cycle["start_date"] = task._start.format('YYYY-MM-DD');
					crop_cycle["end_date"] = task._end.format('YYYY-MM-DD');
					crop_cycle["progress"] =  task.progress;
				} else {
					crop_cycle["start_date"] = old_crop_cycle[index]["start_date"];
					crop_cycle["end_date"] = old_crop_cycle[index]["end_date"];
					crop_cycle["progress"] =  old_crop_cycle[index]["progress"];			
				}
				frm.add_child("crop_cycle", crop_cycle);
			});
		}
	}
});