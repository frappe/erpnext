from __future__ import unicode_literals
import frappe

from frappe import _
from erpnext.setup.utils import insert_record

def setup_healthcare():
	if frappe.db.exists('Medical Department', 'Cardiology'):
		# already setup
		return
	create_medical_departments()
	create_antibiotics()
	create_lab_test_uom()
	create_duration()
	create_dosage()
	create_healthcare_item_groups()
	create_sensitivity()
	add_healthcare_service_unit_tree_root()
	setup_patient_history_settings()

def create_medical_departments():
	departments = [
		"Accident And Emergency Care" ,"Anaesthetics", "Biochemistry", "Cardiology", "Dermatology",
		"Diagnostic Imaging", "ENT", "Gastroenterology", "General Surgery", "Gynaecology",
		"Haematology", "Maternity", "Microbiology", "Nephrology", "Neurology", "Oncology",
		"Orthopaedics", "Pathology", "Physiotherapy", "Rheumatology", "Serology", "Urology"
	]
	for department in departments:
		mediacal_department = frappe.new_doc("Medical Department")
		mediacal_department.department = _(department)
		try:
			mediacal_department.save()
		except frappe.DuplicateEntryError:
			pass

def create_antibiotics():
	abt = [
		"Amoxicillin", "Ampicillin", "Bacampicillin", "Carbenicillin", "Cloxacillin", "Dicloxacillin",
		"Flucloxacillin", "Mezlocillin", "Nafcillin", "Oxacillin", "Penicillin G", "Penicillin V",
		"Piperacillin", "Pivampicillin", "Pivmecillinam", "Ticarcillin", "Cefacetrile (cephacetrile)",
		"Cefadroxil (cefadroxyl)", "Cefalexin (cephalexin)", "Cefaloglycin (cephaloglycin)",
		"Cefalonium (cephalonium)", "Cefaloridine (cephaloradine)", "Cefalotin (cephalothin)",
		"Cefapirin (cephapirin)", "Cefatrizine", "Cefazaflur", "Cefazedone", "Cefazolin (cephazolin)",
		"Cefradine (cephradine)", "Cefroxadine", "Ceftezole", "Cefaclor", "Cefamandole", "Cefmetazole",
		"Cefonicid", "Cefotetan", "Cefoxitin", "Cefprozil (cefproxil)", "Cefuroxime", "Cefuzonam",
		"Cefcapene", "Cefdaloxime", "Cefdinir", "Cefditoren", "Cefetamet", "Cefixime", "Cefmenoxime",
		"Cefodizime", "Cefotaxime", "Cefpimizole", "Cefpodoxime", "Cefteram", "Ceftibuten", "Ceftiofur",
		"Ceftiolene", "Ceftizoxime", "Ceftriaxone", "Cefoperazone", "Ceftazidime", "Cefclidine", "Cefepime",
		"Cefluprenam", "Cefoselis", "Cefozopran", "Cefpirome", "Cefquinome", "Ceftobiprole", "Ceftaroline",
		"Cefaclomezine","Cefaloram", "Cefaparole", "Cefcanel", "Cefedrolor", "Cefempidone", "Cefetrizole",
		"Cefivitril", "Cefmatilen", "Cefmepidium", "Cefovecin", "Cefoxazole", "Cefrotil", "Cefsumide",
		"Cefuracetime", "Ceftioxide", "Ceftazidime/Avibactam", "Ceftolozane/Tazobactam", "Aztreonam",
		"Imipenem", "Imipenem/cilastatin", "Doripenem", "Meropenem", "Ertapenem", "Azithromycin",
		"Erythromycin", "Clarithromycin", "Dirithromycin", "Roxithromycin", "Telithromycin", "Clindamycin",
		"Lincomycin", "Pristinamycin", "Quinupristin/dalfopristin", "Amikacin", "Gentamicin", "Kanamycin",
		"Neomycin", "Netilmicin", "Paromomycin", "Streptomycin", "Tobramycin", "Flumequine", "Nalidixic acid",
		"Oxolinic acid", "Piromidic acid", "Pipemidic acid", "Rosoxacin", "Ciprofloxacin", "Enoxacin",
		"Lomefloxacin", "Nadifloxacin", "Norfloxacin", "Ofloxacin", "Pefloxacin", "Rufloxacin", "Balofloxacin",
		"Gatifloxacin", "Grepafloxacin", "Levofloxacin", "Moxifloxacin", "Pazufloxacin", "Sparfloxacin",
		"Temafloxacin", "Tosufloxacin", "Besifloxacin", "Clinafloxacin", "Gemifloxacin",
		"Sitafloxacin", "Trovafloxacin", "Prulifloxacin", "Sulfamethizole", "Sulfamethoxazole",
		"Sulfisoxazole", "Trimethoprim-Sulfamethoxazole", "Demeclocycline", "Doxycycline", "Minocycline",
		"Oxytetracycline", "Tetracycline", "Tigecycline", "Chloramphenicol", "Metronidazole",
		"Tinidazole", "Nitrofurantoin", "Vancomycin", "Teicoplanin", "Telavancin", "Linezolid",
		"Cycloserine 2", "Rifampin", "Rifabutin", "Rifapentine", "Rifalazil", "Bacitracin", "Polymyxin B",
		"Viomycin", "Capreomycin"
	]

	for a in abt:
		antibiotic = frappe.new_doc("Antibiotic")
		antibiotic.antibiotic_name = a
		try:
			antibiotic.save()
		except frappe.DuplicateEntryError:
			pass

def create_lab_test_uom():
	records = [
		{"doctype": "Lab Test UOM", "name": "umol/L", "lab_test_uom": "umol/L", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "mg/L", "lab_test_uom": "mg/L", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "mg / dl", "lab_test_uom": "mg / dl", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "pg / ml", "lab_test_uom": "pg / ml", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "U/ml", "lab_test_uom": "U/ml", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "/HPF", "lab_test_uom": "/HPF", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "Million Cells / cumm", "lab_test_uom": "Million Cells / cumm", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "Lakhs Cells / cumm", "lab_test_uom": "Lakhs Cells / cumm", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "U / L", "lab_test_uom": "U / L", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "g / L", "lab_test_uom": "g / L", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "IU / ml", "lab_test_uom": "IU / ml", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "gm %", "lab_test_uom": "gm %", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "Microgram", "lab_test_uom": "Microgram", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "Micron", "lab_test_uom": "Micron", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "Cells / cumm", "lab_test_uom": "Cells / cumm", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "%", "lab_test_uom": "%", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "mm / dl", "lab_test_uom": "mm / dl", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "mm / hr", "lab_test_uom": "mm / hr", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "ulU / ml", "lab_test_uom": "ulU / ml", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "ng / ml", "lab_test_uom": "ng / ml", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "ng / dl", "lab_test_uom": "ng / dl", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "ug / dl", "lab_test_uom": "ug / dl", "uom_description": None }
	]

	insert_record(records)

def create_duration():
	records = [
		{"doctype": "Prescription Duration", "name": "3 Month", "number": "3", "period": "Month" },
		{"doctype": "Prescription Duration", "name": "2 Month", "number": "2", "period": "Month" },
		{"doctype": "Prescription Duration", "name": "1 Month", "number": "1", "period": "Month" },
		{"doctype": "Prescription Duration", "name": "12 Hour", "number": "12", "period": "Hour" },
		{"doctype": "Prescription Duration", "name": "11 Hour", "number": "11", "period": "Hour" },
		{"doctype": "Prescription Duration", "name": "10 Hour", "number": "10", "period": "Hour" },
		{"doctype": "Prescription Duration", "name": "9 Hour", "number": "9", "period": "Hour" },
		{"doctype": "Prescription Duration", "name": "8 Hour", "number": "8", "period": "Hour" },
		{"doctype": "Prescription Duration", "name": "7 Hour", "number": "7", "period": "Hour" },
		{"doctype": "Prescription Duration", "name": "6 Hour", "number": "6", "period": "Hour" },
		{"doctype": "Prescription Duration", "name": "5 Hour", "number": "5", "period": "Hour" },
		{"doctype": "Prescription Duration", "name": "4 Hour", "number": "4", "period": "Hour" },
		{"doctype": "Prescription Duration", "name": "3 Hour", "number": "3", "period": "Hour" },
		{"doctype": "Prescription Duration", "name": "2 Hour", "number": "2", "period": "Hour" },
		{"doctype": "Prescription Duration", "name": "1 Hour", "number": "1", "period": "Hour" },
		{"doctype": "Prescription Duration", "name": "5 Week", "number": "5", "period": "Week" },
		{"doctype": "Prescription Duration", "name": "4 Week", "number": "4", "period": "Week" },
		{"doctype": "Prescription Duration", "name": "3 Week", "number": "3", "period": "Week" },
		{"doctype": "Prescription Duration", "name": "2 Week", "number": "2", "period": "Week" },
		{"doctype": "Prescription Duration", "name": "1 Week", "number": "1", "period": "Week" },
		{"doctype": "Prescription Duration", "name": "6 Day", "number": "6", "period": "Day" },
		{"doctype": "Prescription Duration", "name": "5 Day", "number": "5", "period": "Day" },
		{"doctype": "Prescription Duration", "name": "4 Day", "number": "4", "period": "Day" },
		{"doctype": "Prescription Duration", "name": "3 Day", "number": "3", "period": "Day" },
		{"doctype": "Prescription Duration", "name": "2 Day", "number": "2", "period": "Day" },
		{"doctype": "Prescription Duration", "name": "1 Day", "number": "1", "period": "Day" }
	]
	insert_record(records)

def create_dosage():
	records = [
		{"doctype": "Prescription Dosage", "name": "1-1-1-1", "dosage": "1-1-1-1","dosage_strength":
		[{"strength": "1.0","strength_time": "9:00:00"}, {"strength": "1.0","strength_time": "13:00:00"},{"strength": "1.0","strength_time": "17:00:00"},{"strength": "1.0","strength_time": "21:00:00"}]
		},
		{"doctype": "Prescription Dosage", "name": "0-0-1", "dosage": "0-0-1","dosage_strength":
		[{"strength": "1.0","strength_time": "21:00:00"}]
		},
		{"doctype": "Prescription Dosage", "name": "1-0-0", "dosage": "1-0-0","dosage_strength":
		[{"strength": "1.0","strength_time": "9:00:00"}]
		},
		{"doctype": "Prescription Dosage", "name": "0-1-0", "dosage": "0-1-0","dosage_strength":
		[{"strength": "1.0","strength_time": "14:00:00"}]
		},
		{"doctype": "Prescription Dosage", "name": "1-1-1", "dosage": "1-1-1","dosage_strength":
		[{"strength": "1.0","strength_time": "9:00:00"}, {"strength": "1.0","strength_time": "14:00:00"},{"strength": "1.0","strength_time": "21:00:00"}]
		},
		{"doctype": "Prescription Dosage", "name": "1-0-1", "dosage": "1-0-1","dosage_strength":
		[{"strength": "1.0","strength_time": "9:00:00"}, {"strength": "1.0","strength_time": "21:00:00"}]
		},
		{"doctype": "Prescription Dosage", "name": "Once Bedtime", "dosage": "Once Bedtime","dosage_strength":
		[{"strength": "1.0","strength_time": "21:00:00"}]
		},
		{"doctype": "Prescription Dosage", "name": "5 times a day", "dosage": "5 times a day","dosage_strength":
		[{"strength": "1.0","strength_time": "5:00:00"}, {"strength": "1.0","strength_time": "9:00:00"}, {"strength": "1.0","strength_time": "13:00:00"},{"strength": "1.0","strength_time": "17:00:00"},{"strength": "1.0","strength_time": "21:00:00"}]
		},
		{"doctype": "Prescription Dosage", "name": "QID", "dosage": "QID","dosage_strength":
		[{"strength": "1.0","strength_time": "9:00:00"}, {"strength": "1.0","strength_time": "13:00:00"},{"strength": "1.0","strength_time": "17:00:00"},{"strength": "1.0","strength_time": "21:00:00"}]
		},
		{"doctype": "Prescription Dosage", "name": "TID", "dosage": "TID","dosage_strength":
		[{"strength": "1.0","strength_time": "9:00:00"}, {"strength": "1.0","strength_time": "14:00:00"},{"strength": "1.0","strength_time": "21:00:00"}]
		},
		{"doctype": "Prescription Dosage", "name": "BID", "dosage": "BID","dosage_strength":
		[{"strength": "1.0","strength_time": "9:00:00"}, {"strength": "1.0","strength_time": "21:00:00"}]
		},
		{"doctype": "Prescription Dosage", "name": "Once Daily", "dosage": "Once Daily","dosage_strength":
		[{"strength": "1.0","strength_time": "9:00:00"}]
		}
	]
	insert_record(records)

def create_healthcare_item_groups():
	records = [
		{'doctype': 'Item Group', 'item_group_name': _('Laboratory'),
			'is_group': 0, 'parent_item_group': _('All Item Groups') },
		{'doctype': 'Item Group', 'item_group_name': _('Drug'),
			'is_group': 0, 'parent_item_group': _('All Item Groups') }
	]
	insert_record(records)

def create_sensitivity():
	records = [
		{"doctype": "Sensitivity", "sensitivity": _("Low Sensitivity")},
		{"doctype": "Sensitivity", "sensitivity": _("High Sensitivity")},
		{"doctype": "Sensitivity", "sensitivity": _("Moderate Sensitivity")},
		{"doctype": "Sensitivity", "sensitivity": _("Susceptible")},
		{"doctype": "Sensitivity", "sensitivity": _("Resistant")},
		{"doctype": "Sensitivity", "sensitivity": _("Intermediate")}
	]
	insert_record(records)

def add_healthcare_service_unit_tree_root():
	record = [
		{
			"doctype": "Healthcare Service Unit",
			"healthcare_service_unit_name": "All Healthcare Service Units",
			"is_group": 1,
			"company": get_company()
	 	}
	]
	insert_record(record)

def get_company():
	company = frappe.defaults.get_defaults().company
	if company:
		return company
	else:
		company = frappe.get_list("Company", limit=1)
		if company:
			return company[0].name
	return None

def setup_patient_history_settings():
	import json

	settings = frappe.get_single('Patient History Settings')
	configuration = get_patient_history_config()
	for dt, config in configuration.items():
		settings.append("standard_doctypes", {
			"document_type": dt,
			"date_fieldname": config[0],
			"selected_fields": json.dumps(config[1])
		})
	settings.save()

def get_patient_history_config():
	return {
		"Patient Encounter": ("encounter_date", [
			{"label": "Healthcare Practitioner", "fieldname": "practitioner", "fieldtype": "Link"},
			{"label": "Symptoms", "fieldname": "symptoms", "fieldtype": "Table Multiselect"},
			{"label": "Diagnosis", "fieldname": "diagnosis", "fieldtype": "Table Multiselect"},
			{"label": "Drug Prescription", "fieldname": "drug_prescription", "fieldtype": "Table"},
			{"label": "Lab Tests", "fieldname": "lab_test_prescription", "fieldtype": "Table"},
			{"label": "Clinical Procedures", "fieldname": "procedure_prescription", "fieldtype": "Table"},
			{"label": "Therapies", "fieldname": "therapies", "fieldtype": "Table"},
			{"label": "Review Details", "fieldname": "encounter_comment", "fieldtype": "Small Text"}
		]),
		"Clinical Procedure": ("start_date", [
			{"label": "Procedure Template", "fieldname": "procedure_template", "fieldtype": "Link"},
			{"label": "Healthcare Practitioner", "fieldname": "practitioner", "fieldtype": "Link"},
			{"label": "Notes", "fieldname": "notes", "fieldtype": "Small Text"},
			{"label": "Service Unit", "fieldname": "service_unit", "fieldtype": "Healthcare Service Unit"},
			{"label": "Start Time", "fieldname": "start_time", "fieldtype": "Time"},
			{"label": "Sample", "fieldname": "sample", "fieldtype": "Link"}
		]),
		"Lab Test": ("result_date", [
			{"label": "Test Template", "fieldname": "template", "fieldtype": "Link"},
			{"label": "Healthcare Practitioner", "fieldname": "practitioner", "fieldtype": "Link"},
			{"label": "Test Name", "fieldname": "lab_test_name", "fieldtype": "Data"},
			{"label": "Lab Technician Name", "fieldname": "employee_name", "fieldtype": "Data"},
			{"label": "Sample ID", "fieldname": "sample", "fieldtype": "Link"},
			{"label": "Normal Test Result", "fieldname": "normal_test_items", "fieldtype": "Table"},
			{"label": "Descriptive Test Result", "fieldname": "descriptive_test_items", "fieldtype": "Table"},
			{"label": "Organism Test Result", "fieldname": "organism_test_items", "fieldtype": "Table"},
			{"label": "Sensitivity Test Result", "fieldname": "sensitivity_test_items", "fieldtype": "Table"},
			{"label": "Comments", "fieldname": "lab_test_comment", "fieldtype": "Table"}
		]),
		"Therapy Session": ("start_date", [
			{"label": "Therapy Type", "fieldname": "therapy_type", "fieldtype": "Link"},
			{"label": "Healthcare Practitioner", "fieldname": "practitioner", "fieldtype": "Link"},
			{"label": "Therapy Plan", "fieldname": "therapy_plan", "fieldtype": "Link"},
			{"label": "Duration", "fieldname": "duration", "fieldtype": "Int"},
			{"label": "Location", "fieldname": "location", "fieldtype": "Link"},
			{"label": "Healthcare Service Unit", "fieldname": "service_unit", "fieldtype": "Link"},
			{"label": "Start Time", "fieldname": "start_time", "fieldtype": "Time"},
			{"label": "Exercises", "fieldname": "exercises", "fieldtype": "Table"},
			{"label": "Total Counts Targeted", "fieldname": "total_counts_targeted", "fieldtype": "Int"},
			{"label": "Total Counts Completed", "fieldname": "total_counts_completed", "fieldtype": "Int"}
		]),
		"Vital Signs": ("signs_date", [
			{"label": "Body Temperature", "fieldname": "temperature", "fieldtype": "Data"},
			{"label": "Heart Rate / Pulse", "fieldname": "pulse", "fieldtype": "Data"},
			{"label": "Respiratory rate", "fieldname": "respiratory_rate", "fieldtype": "Data"},
			{"label": "Tongue", "fieldname": "tongue", "fieldtype": "Select"},
			{"label": "Abdomen", "fieldname": "abdomen", "fieldtype": "Select"},
			{"label": "Reflexes", "fieldname": "reflexes", "fieldtype": "Select"},
			{"label": "Blood Pressure", "fieldname": "bp", "fieldtype": "Data"},
			{"label": "Notes", "fieldname": "vital_signs_note", "fieldtype": "Small Text"},
			{"label": "Height (In Meter)", "fieldname": "height", "fieldtype": "Float"},
			{"label": "Weight (In Kilogram)", "fieldname": "weight", "fieldtype": "Float"},
			{"label": "BMI", "fieldname": "bmi", "fieldtype": "Float"}
		]),
		"Inpatient Medication Order": ("start_date", [
			{"label": "Healthcare Practitioner", "fieldname": "practitioner", "fieldtype": "Link"},
			{"label": "Start Date", "fieldname": "start_date", "fieldtype": "Date"},
			{"label": "End Date", "fieldname": "end_date", "fieldtype": "Date"},
			{"label": "Medication Orders", "fieldname": "medication_orders", "fieldtype": "Table"},
			{"label": "Total Orders", "fieldname": "total_orders", "fieldtype": "Float"}
		])
	}