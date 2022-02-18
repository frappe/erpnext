// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Patient Assessment', {
	refresh: function(frm) {
		if (frm.doc.assessment_template) {
			frm.trigger('set_score_range');
		}

		if (!frm.doc.__islocal) {
			frm.trigger('show_patient_progress');
		}
	},

	assessment_template: function(frm) {
		if (frm.doc.assessment_template) {
			frappe.call({
				'method': 'frappe.client.get',
				args: {
					doctype: 'Patient Assessment Template',
					name: frm.doc.assessment_template
				},
				callback: function(data) {
					frm.doc.assessment_sheet = [];
					$.each(data.message.parameters, function(_i, e) {
						let entry = frm.add_child('assessment_sheet');
						entry.parameter = e.assessment_parameter;
					});

					frm.set_value('scale_min', data.message.scale_min);
					frm.set_value('scale_max', data.message.scale_max);
					frm.set_value('assessment_description', data.message.assessment_description);
					frm.set_value('total_score', data.message.scale_max * data.message.parameters.length);
					frm.trigger('set_score_range');
					refresh_field('assessment_sheet');
				}
			});
		}
	},

	set_score_range: function(frm) {
		let options = [''];
		for(let i = frm.doc.scale_min; i <= frm.doc.scale_max; i++) {
			options.push(i);
		}
		frm.fields_dict.assessment_sheet.grid.update_docfield_property(
			'score', 'options', options
		);
	},

	calculate_total_score: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		let total_score = 0;
		$.each(frm.doc.assessment_sheet || [], function(_i, item) {
			if (item.score) {
				total_score += parseInt(item.score);
			}
		});

		frm.set_value('total_score_obtained', total_score);
	},

	show_patient_progress: function(frm) {
		let bars = [];
		let message = '';
		let added_min = false;

		let title = __('{0} out of {1}', [frm.doc.total_score_obtained, frm.doc.total_score]);

		bars.push({
			'title': title,
			'width': (frm.doc.total_score_obtained / frm.doc.total_score * 100) + '%',
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

frappe.ui.form.on('Patient Assessment Sheet', {
	score: function(frm, cdt, cdn) {
		frm.events.calculate_total_score(frm, cdt, cdn);
	}
});
