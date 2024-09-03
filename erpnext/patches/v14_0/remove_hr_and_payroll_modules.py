from sqlalchemy.orm import Session
from Goldfish.config import get_db
from Goldfish.models.doctype import DocType, DocField

def execute(db: Session = next(get_db())):
	# Check if HRMS is installed (you'll need to implement this check)
	if is_hrms_installed():
		return

	# Delete Module Def
	db.query(DocType).filter(DocType.name.in_(["HR", "Payroll"])).delete(synchronize_session=False)

	# Delete Workspace
	db.query(DocType).filter(DocType.name.in_(["HR", "Payroll"])).delete(synchronize_session=False)

	# Delete Print Formats
	db.query(DocType).filter(
		DocType.module.in_(["HR", "Payroll"]),
		DocType.name.like("Print Format%"),
		DocType.custom == False
	).delete(synchronize_session=False)

	# Delete Reports
	db.query(DocType).filter(
		DocType.module.in_(["HR", "Payroll"]),
		DocType.name.like("Report%"),
		DocType.custom == False
	).delete(synchronize_session=False)

	# Delete specific reports
	specific_reports = [
		"Project Profitability",
		"Employee Hours Utilization Based On Timesheet",
		"Unpaid Expense Claim",
		"Professional Tax Deductions",
		"Provident Fund Deductions",
	]
	db.query(DocType).filter(DocType.name.in_(specific_reports)).delete(synchronize_session=False)

	# Delete DocTypes
	db.query(DocType).filter(
		DocType.module.in_(["HR", "Payroll"]),
		DocType.custom == False
	).delete(synchronize_session=False)

	# Delete specific DocTypes
	db.query(DocType).filter(DocType.name.in_(["Salary Slip Loan", "Salary Component Account"])).delete(synchronize_session=False)

	# Delete Notifications
	db.query(DocType).filter(
		DocType.module.in_(["HR", "Payroll"]),
		DocType.name.like("Notification%"),
		DocType.custom == False
	).delete(synchronize_session=False)

	# Delete User Type
	db.query(DocType).filter(DocType.name == "Employee Self Service").delete(synchronize_session=False)

	# Delete other records (Web Form, Dashboard, etc.)
	for dt in ["Web Form", "Dashboard", "Dashboard Chart", "Number Card"]:
		db.query(DocType).filter(
			DocType.module.in_(["HR", "Payroll"]),
			DocType.name.like(f"{dt}%"),
			DocType.custom == False
		).delete(synchronize_session=False)

	# Delete Custom Fields
	custom_fields = {
		"Salary Component": ["component_type"],
		"Employee": ["ifsc_code", "pan_number", "micr_code", "provident_fund_account"],
		"Company": [
			"hra_section",
			"basic_component",
			"hra_component",
			"hra_column_break",
			"arrear_component",
		],
		"Employee Tax Exemption Declaration": [
			"hra_section",
			"monthly_house_rent",
			"rented_in_metro_city",
			"salary_structure_hra",
			"hra_column_break",
			"annual_hra_exemption",
			"monthly_hra_exemption",
		],
		"Employee Tax Exemption Proof Submission": [
			"hra_section",
			"house_rent_payment_amount",
			"rented_in_metro_city",
			"rented_from_date",
			"rented_to_date",
			"hra_column_break",
			"monthly_house_rent",
			"monthly_hra_exemption",
			"total_eligible_hra_exemption",
		],
	}

	for doc, fields in custom_fields.items():
		db.query(DocField).filter(
			DocField.parent == doc,
			DocField.fieldname.in_(fields)
		).delete(synchronize_session=False)

	db.commit()

# You'll need to implement this function
def is_hrms_installed():
	# Check if HRMS is in installed apps (implement this using SQLAlchemy or environment variables)
	pass
