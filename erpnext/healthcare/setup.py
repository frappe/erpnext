from __future__ import unicode_literals
import frappe

from frappe import _

def setup_healthcare():
	if frappe.db.exists('Medical Department', 'Cardiology'):
		# already setup
		return
	create_medical_departments()
	create_antibiotics()
	create_test_uom()
	create_duration()
	create_dosage()
	create_healthcare_item_groups()
	create_lab_test_items()
	create_lab_test_template()
	create_sensitivity()

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

def create_test_uom():
	records = [
		{"doctype": "Lab Test UOM", "name": "umol/L", "test_uom": "umol/L", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "mg/L", "test_uom": "mg/L", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "mg / dl", "test_uom": "mg / dl", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "pg / ml", "test_uom": "pg / ml", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "U/ml", "test_uom": "U/ml", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "/HPF", "test_uom": "/HPF", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "Million Cells / cumm", "test_uom": "Million Cells / cumm", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "Lakhs Cells / cumm", "test_uom": "Lakhs Cells / cumm", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "U / L", "test_uom": "U / L", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "g / L", "test_uom": "g / L", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "IU / ml", "test_uom": "IU / ml", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "gm %", "test_uom": "gm %", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "Microgram", "test_uom": "Microgram", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "Micron", "test_uom": "Micron", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "Cells / cumm", "test_uom": "Cells / cumm", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "%", "test_uom": "%", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "mm / dl", "test_uom": "mm / dl", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "mm / hr", "test_uom": "mm / hr", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "ulU / ml", "test_uom": "ulU / ml", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "ng / ml", "test_uom": "ng / ml", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "ng / dl", "test_uom": "ng / dl", "uom_description": None },
		{"doctype": "Lab Test UOM", "name": "ug / dl", "test_uom": "ug / dl", "uom_description": None }
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

def create_lab_test_items():
	records = [
		{"doctype": "Item", "item_code": "MCH", "item_name": "MCH", "item_group": _("Laboratory"),
			"stock_uom": _("Unit"), "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1},
		{"doctype": "Item", "item_code": "LDL", "item_name": "LDL", "item_group": _("Laboratory"),
			"stock_uom": _("Unit"), "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1},
		{"doctype": "Item", "item_code": "GTT", "item_name": "GTT", "item_group": _("Laboratory"),
			"stock_uom": _("Unit"), "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1},
		{"doctype": "Item", "item_code": "HDL", "item_name": "HDL", "item_group": _("Laboratory"),
			"stock_uom": _("Unit"), "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1},
		{"doctype": "Item", "item_code": "BILT", "item_name": "BILT", "item_group": _("Laboratory"),
			"stock_uom": _("Unit"), "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1},
		{"doctype": "Item", "item_code": "BILD", "item_name": "BILD", "item_group": _("Laboratory"),
			"stock_uom": _("Unit"), "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1},
		{"doctype": "Item", "item_code": "BP", "item_name": "BP", "item_group": _("Laboratory"),
			"stock_uom": _("Unit"), "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1},
		{"doctype": "Item", "item_code": "BS", "item_name": "BS", "item_group": _("Laboratory"),
			"stock_uom": _("Unit"), "is_stock_item": 0, "is_purchase_item": 0, "is_sales_item": 1}
	]
	insert_record(records)

def create_lab_test_template():
	records = [
		{"doctype": "Lab Test Template", "name": "MCH","test_name": "MCH","test_code": "MCH",
		"test_group": _("Laboratory"),"department": _("Haematology"),"item": "MCH",
		"test_template_type": "Single","is_billable": 1,"test_rate": 0.0,"test_uom": "Microgram",
		"test_normal_range": "27 - 32 Microgram",
		"sensitivity": 0,"test_description": "Mean Corpuscular Hemoglobin"},
		{"doctype": "Lab Test Template", "name": "LDL","test_name": "LDL (Serum)","test_code": "LDL",
		"test_group": _("Laboratory"),"department": _("Biochemistry"),
		"item": "LDL","test_template_type": "Single",
		"is_billable": 1,"test_rate": 0.0,"test_uom": "mg / dl","test_normal_range": "70 - 160 mg/dlLow-density Lipoprotein (LDL)",
		"sensitivity": 0,"test_description": "Low-density Lipoprotein (LDL)"},
		{"doctype": "Lab Test Template", "name": "GTT","test_name": "GTT","test_code": "GTT",
		"test_group": _("Laboratory"),"department": _("Haematology"),
		"item": "GTT","test_template_type": "Single",
		"is_billable": 1,"test_rate": 0.0,"test_uom": "mg / dl","test_normal_range": "Less than 85 mg/dl",
		"sensitivity": 0,"test_description": "Glucose Tolerance Test"},
		{"doctype": "Lab Test Template", "name": "HDL","test_name": "HDL (Serum)","test_code": "HDL",
		"test_group": _("Laboratory"),"department": _("Biochemistry"),
		"item": "HDL","test_template_type": "Single",
		"is_billable": 1,"test_rate": 0.0,"test_uom": "mg / dl","test_normal_range": "35 - 65 mg/dl",
		"sensitivity": 0,"test_description": "High-density Lipoprotein (HDL)"},
		{"doctype": "Lab Test Template", "name": "BILT","test_name": "Bilirubin Total","test_code": "BILT",
		"test_group": _("Laboratory"),"department": _("Biochemistry"),
		"item": "BILT","test_template_type": "Single",
		"is_billable": 1,"test_rate": 0.0,"test_uom": "mg / dl","test_normal_range": "0.2 - 1.2 mg / dl",
		"sensitivity": 0,"test_description": "Bilirubin Total"},
		{"doctype": "Lab Test Template", "name": "BILD","test_name": "Bilirubin Direct","test_code": "BILD",
		"test_group": _("Laboratory"),"department": _("Biochemistry"),
		"item": "BILD","test_template_type": "Single",
		"is_billable": 1,"test_rate": 0.0,"test_uom": "mg / dl","test_normal_range": "0.4 mg / dl",
		"sensitivity": 0,"test_description": "Bilirubin Direct"},

		{"doctype": "Lab Test Template", "name": "BP","test_name": "Bile Pigment","test_code": "BP",
		"test_group": _("Laboratory"),"department": _("Pathology"),
		"item": "BP","test_template_type": "Single",
		"is_billable": 1,"test_rate": 0.0,"test_uom": "","test_normal_range": "",
		"sensitivity": 0,"test_description": "Bile Pigment"},
		{"doctype": "Lab Test Template", "name": "BS","test_name": "Bile Salt","test_code": "BS",
		"test_group": _("Laboratory"),"department": _("Pathology"),
		"item": "BS","test_template_type": "Single",
		"is_billable": 1,"test_rate": 0.0,"test_uom": "","test_normal_range": "",
		"sensitivity": 0,"test_description": "Bile Salt"}
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

def insert_record(records):
	for r in records:
		doc = frappe.new_doc(r.get("doctype"))
		doc.update(r)
		try:
			doc.insert(ignore_permissions=True)
		except frappe.DuplicateEntryError, e:
			# pass DuplicateEntryError and continue
			if e.args and e.args[0]==doc.doctype and e.args[1]==doc.name:
				# make sure DuplicateEntryError is for the exact same doc and not a related doc
				pass
			else:
				raise
