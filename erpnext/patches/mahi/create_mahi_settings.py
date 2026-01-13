import click
import frappe

from erpnext.manufacturing.doctype.quarantine_label.quarantine_label import QuarantineLabel
from erpnext.manufacturing.doctype.slab_quality_grade.slab_quality_grade import SlabQualityGrade
from erpnext.setup.doctype.mahi_granites_settings.mahi_granites_settings import MahiGranitesSettings


def execute():
	generate_mahi_granites_default_settings()


def generate_mahi_granites_default_settings():
	mahi_settings: MahiGranitesSettings = frappe.get_doc("Mahi Granites Settings")  # pyright: ignore[reportAssignmentType]
	mahi_settings = set_default_general_settings(mahi_settings)
	mahi_settings = set_default_mfg_settings(mahi_settings)
	click.secho("Created Mahi Granites Settings", fg="green")
	mahi_settings.save()
	frappe.db.commit()


def set_default_general_settings(mahi_settings: MahiGranitesSettings):
	mahi_settings.mfg_unit = get_company().name
	mahi_settings.max_pay_line_amount = 1000000
	return mahi_settings


def set_default_mfg_settings(mahi_settings: MahiGranitesSettings):
	mahi_settings.max_heating_minutes = 90
	mahi_settings.min_quarantine_hours = 24
	mahi_settings.quarantine_labels = get_default_quarantine_labels()
	mahi_settings.grades = get_default_quality_grades()
	return mahi_settings


def get_default_quarantine_labels():
	default_label_items = [
		"Paper Deep",
		"Light Paper Deep"
	]

	default_labels = []
	for item in default_label_items:
		default_label: QuarantineLabel = frappe.new_doc("Quarantine Label")  # pyright: ignore[reportAssignmentType]
		default_label.parameter = item
		default_labels.append(default_label)

	return default_labels


def get_default_quality_grades():
	default_grade_items = [
		{
			"grade_name": "Premium",
			"code": "PRE",
			"color": "#29CD42"
		},
		{
			"grade_name": "Standard",
			"code": "STD",
			"color": "#4F9DD9"
		},
		{
			"grade_name": "Reject",
			"code": "REJ",
			"color": "#CB2929"
		}
	]

	default_grades = []

	for item in default_grade_items:
		default_grade: SlabQualityGrade = frappe.new_doc("Slab Quality Grade")  # pyright: ignore[reportAssignmentType]
		default_grade.grade_name = item["grade_name"]
		default_grade.code = item["code"]
		default_grade.color = item["color"]
		default_grades.append(default_grade)

	return default_grades


def get_company():
	all_companies = frappe.get_all("Company", fields=["name", "abbr"])
	for company in all_companies:
		if company.name.lower() == "unit - 2" or company.name.lower() == "unit 2" or company.name.lower() == "unit-2" or company.name.lower() == "unit2":
			return company

	return all_companies[0]
