import frappe
from datetime import datetime
from frappe import _
from frappe.utils import getdate, get_timespan_date_range
import json

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
	return dict(frappe.db.sql("""
		SELECT
			unix_timestamp(communication_date), count(*)
		FROM
			`tabPatient Medical Record`
		WHERE
			communication_date > subdate(%(date)s, interval 1 year) and
			communication_date < subdate(%(date)s, interval -1 year) and
			patient = %(patient)s
		GROUP BY communication_date
		ORDER BY communication_date asc""", {'date': date, 'patient': patient}))


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
def get_therapy_progress_data(patient, therapy_type, time_span):
	date_range = get_date_range(time_span)
	query_values = {'from_date': date_range[0], 'to_date': date_range[1], 'therapy_type': therapy_type, 'patient': patient}
	result = frappe.db.sql("""
		SELECT
			start_date, total_counts_targeted, total_counts_completed
		FROM
			`tabTherapy Session`
		WHERE
			start_date BETWEEN %(from_date)s AND %(to_date)s and
			docstatus = 1 and
			therapy_type = %(therapy_type)s and
			patient = %(patient)s
		ORDER BY start_date""", query_values, as_list=1)

	return {
		'labels': [r[0] for r in result if r[0] != None],
		'datasets': [
			{ 'name': _('Targetted'), 'values': [r[1] for r in result if r[0] != None] },
			{ 'name': _('Completed'), 'values': [r[2] for r in result if r[0] != None] }
		]
	}

@frappe.whitelist()
def get_patient_assessment_data(patient, assessment_template, time_span):
	date_range = get_date_range(time_span)
	query_values = {'from_date': date_range[0], 'to_date': date_range[1], 'assessment_template': assessment_template, 'patient': patient}
	result = frappe.db.sql("""
		SELECT
			assessment_datetime, total_score, total_score_obtained
		FROM
			`tabPatient Assessment`
		WHERE
			DATE(assessment_datetime) BETWEEN %(from_date)s AND %(to_date)s and
			docstatus = 1 and
			assessment_template = %(assessment_template)s and
			patient = %(patient)s
		ORDER BY assessment_datetime""", query_values, as_list=1)

	return {
		'labels': [getdate(r[0]) for r in result if r[0] != None],
		'datasets': [
			{ 'name': _('Score Obtained'), 'values': [r[2] for r in result if r[0] != None] }
		],
		'max_score': result[0][1] if result else None
	}

@frappe.whitelist()
def get_therapy_assessment_correlation_data(patient, assessment_template, time_span):
	date_range = get_date_range(time_span)
	query_values = {'from_date': date_range[0], 'to_date': date_range[1], 'assessment': assessment_template, 'patient': patient}
	result = frappe.db.sql("""
		SELECT
			therapy.therapy_type, count(*), avg(assessment.total_score_obtained), total_score
		FROM
			`tabPatient Assessment` assessment INNER JOIN `tabTherapy Session` therapy
		ON
			assessment.therapy_session = therapy.name
		WHERE
			DATE(assessment.assessment_datetime) BETWEEN %(from_date)s AND %(to_date)s and
			assessment.docstatus = 1 and
			assessment.patient = %(patient)s and
			assessment.assessment_template = %(assessment)s
		GROUP BY therapy.therapy_type
	""", query_values, as_list=1)

	return {
		'labels': [r[0] for r in result if r[0] != None],
		'datasets': [
			{ 'name': _('Sessions'), 'chartType': 'bar', 'values': [r[1] for r in result if r[0] != None] },
			{ 'name': _('Average Score'), 'chartType': 'line', 'values': [round(r[2], 2) for r in result if r[0] != None] }
		],
		'max_score': result[0][1] if result else None
	}

@frappe.whitelist()
def get_assessment_parameter_data(patient, parameter, time_span):
	date_range = get_date_range(time_span)
	query_values = {'from_date': date_range[0], 'to_date': date_range[1], 'parameter': parameter, 'patient': patient}
	results = frappe.db.sql("""
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
			DATE(assessment.assessment_datetime) BETWEEN %(from_date)s AND %(to_date)s and
			assessment.docstatus = 1 and
			sheet.parameter = %(parameter)s and
			assessment.patient = %(patient)s
		ORDER BY
			assessment.assessment_datetime asc
	""", query_values, as_list=1)

	score_percentages = []
	for r in results:
		if r[2] != 0 and r[0] != None:
			score = round((int(r[1]) / int(r[2])) * 100, 2)
			score_percentages.append(score)

	return {
		'labels': [getdate(r[0]) for r in results if r[0] != None],
		'datasets': [
			{ 'name': _('Score'), 'values': score_percentages }
		]
	}

def get_date_range(time_span):
	try:
		time_span = json.loads(time_span)
		return time_span
	except json.decoder.JSONDecodeError:
		return get_timespan_date_range(time_span.lower())

