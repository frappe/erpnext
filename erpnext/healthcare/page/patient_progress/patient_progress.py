import frappe
from datetime import datetime
from frappe import _
from frappe.utils import getdate

@frappe.whitelist()
def get_therapy_sessions_count(patient):
	total = frappe.db.count('Therapy Session', filters={
		'docstatus': 1,
		'patient': patient
	})

	month_start = datetime.today().replace(day=1)
	this_month = frappe.db.count('Therapy Session', filters={
		'creation': ['>', month_start],
		'docstatus': 1,
		'patient': patient
	})

	return {
	'total_therapy_sessions': total,
	'therapy_sessions_this_month': this_month
	}


@frappe.whitelist()
def get_patient_heatmap_data(patient, date):
	return dict(frappe.db.sql('''
		SELECT
			unix_timestamp(communication_date), count(*)
		FROM
			`tabPatient Medical Record`
		WHERE
			communication_date > subdate('{date}', interval 1 year) and
			communication_date < subdate('{date}', interval -1 year) and
			patient = '{patient}'
		GROUP BY communication_date
		ORDER BY communication_date asc'''.format(patient=patient, date=date)))


@frappe.whitelist()
def get_therapy_sessions_distribution_data(patient, field):
	if field == 'therapy_type':
		result = frappe.db.get_all('Therapy Session',
			filters = {'patient': patient, 'docstatus': 1},
			group_by = field,
			order_by = field,
			fields = [field, 'count(*)'],
			as_list = True)

	elif field == 'exercise_type':
		data = frappe.db.get_all('Therapy Session',  filters={
			'docstatus': 1,
			'patient': patient
		}, as_list=True)
		therapy_sessions = [entry[0] for entry in data]

		result = frappe.db.get_all('Exercise',
			filters = {
				'parenttype': 'Therapy Session',
				'parent': ['in', therapy_sessions],
				'docstatus': 1
			},
			group_by = field,
			order_by = field,
			fields = [field, 'count(*)'],
			as_list = True)

	return {
		'labels': [r[0] for r in result if r[0] != None],
		'datasets': [{
			'values': [r[1] for r in result]
		}]
	}


@frappe.whitelist()
def get_therapy_progress_data(patient, therapy_type):
	result = frappe.db.get_all('Therapy Session', filters={
		'docstatus': 1,
		'patient': patient,
		'therapy_type': therapy_type
	},
	order_by='start_date asc',
	fields=['start_date', 'total_counts_targeted', 'total_counts_completed'],
	as_list=True)

	return {
		'labels': [r[0] for r in result if r[0] != None],
		'datasets': [
			{ 'name': _('Targetted'), 'values': [r[1] for r in result if r[0] != None] },
			{ 'name': _('Completed'), 'values': [r[2] for r in result if r[0] != None] }
		]
	}

@frappe.whitelist()
def get_patient_assessment_data(patient, assessment_template):
	result = frappe.db.get_all('Patient Assessment', filters={
		'docstatus': 1,
		'patient': patient,
		'assessment_template': assessment_template
	},
	order_by='assessment_datetime asc',
	fields=['assessment_datetime', 'total_score', 'total_score_obtained'],
	as_list=True)

	return {
		'labels': [getdate(r[0]) for r in result if r[0] != None],
		'datasets': [
			{ 'name': _('Maximum Score'), 'values': [r[1] for r in result if r[0] != None] },
			{ 'name': _('Score Obtained'), 'values': [r[2] for r in result if r[0] != None] }
		]
	}

@frappe.whitelist()
def get_therapy_assessment_correlation_data(patient, assessment_template):
	result = frappe.db.sql('''
		SELECT
			therapy.therapy_type, count(*), avg(assessment.total_score_obtained), total_score
		FROM
			`tabPatient Assessment` assessment INNER JOIN `tabTherapy Session` therapy
		ON
			assessment.therapy_session = therapy.name
		WHERE
			assessment.assessment_template = %(assessment)s
		GROUP BY
			therapy.therapy_type
	''', {'assessment': assessment_template}, as_list=True)

	return {
		'labels': [r[0] for r in result if r[0] != None],
		'datasets': [
			{ 'name': _('Sessions'), 'chartType': 'bar', 'values': [r[1] for r in result if r[0] != None] },
			{ 'name': _('Avg Score'), 'chartType': 'line', 'values': [round(r[2], 2) for r in result if r[0] != None] },
			{ 'name': _('Max Score'), 'chartType': 'line', 'values': [r[3] for r in result if r[0] != None] }
		]
	}

@frappe.whitelist()
def get_assessment_parameter_data(patient, parameter):
	results = frappe.db.sql('''
		SELECT
			assessment.assessment_datetime,
			sheet.score,
			template.scale_max
		FROM
			`tabPatient Assessment Sheet` sheet
		INNER JOIN `tabPatient Assessment` assessment
			ON sheet.parent = assessment.name
		INNER JOIN `tabPatient Assessment Template` template
			ON template.name = assessment.assessment_template
		WHERE
			sheet.parameter = %(parameter)s and
			assessment.patient = %(patient)s
		ORDER BY
			assessment.assessment_datetime asc
	''', {'parameter': parameter, 'patient': patient}, as_list=True)

	score_percentages = []
	for r in results:
		if r[2] != 0 and r[0] != None:
			score = round((int(r[1]) / int(r[2])) * 100, 2)
			score_percentages.append(score)

	return {
		'labels': [getdate(r[0]) for r in results if r[0] != None],
		'datasets': [
			{ 'values': score_percentages }
		]
	}

