// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Motor Assessment Scale', {
	refresh: function(frm) {
		if (!frm.doc.assessment_sheet) {
			let parameters = ['supine to side lying', 'supine to sitting over side of bed', 'balance sitting', 'sitting to standing', 'walking', 'upper arm function', 'hand movements', 'advanced hand activities'];
			$.each(parameters, function(i, v) {
				let entry = frappe.model.add_child(frm.doc, 'Motor Assessment Scale Sheet', 'assessment_sheet');
				entry.parameter = v;
			})
			refresh_field('assessment_sheet');
		}

		if (!frm.doc.__islocal) {
			frm.trigger('show_patient_progress');
		}
	},

	calculate_total_score: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		let total_score = 0;
		$.each(frm.doc.assessment_sheet || [], function(i, item){
			if (item.value) {
				total_score += parseInt(item.value);
			}
		});
		frm.set_value('total_score', total_score);
	},

	show_patient_progress: function(frm) {
		let bars = [];
		let message = '';
		let added_min = false;

		// completed sessions
		let title = __('{0} out of 56', [frm.doc.total_score]);

		bars.push({
			'title': title,
			'width': (frm.doc.total_score / 56 * 100) + '%',
			'progress_class': 'progress-bar-success'
		});
		if (bars[0].width == '0%') {
			bars[0].width = '0.5%';
			added_min = 0.5;
		}
		message = title;
		frm.dashboard.add_progress(__('Status'), bars, message);
	},
});

frappe.ui.form.on('Motor Assessment Scale Sheet', {
	value: function(frm, cdt, cdn) {
		frm.events.calculate_total_score(frm, cdt, cdn);
	}
});

