import frappe
from frappe.model.utils.rename_field import update_property_setters

def execute():
	if not frappe.db.exists("DocType", "Salary Structure Earning"):
		return
	
	frappe.reload_doc("hr", "doctype", "salary_detail")
	frappe.reload_doc("hr", "doctype", "salary_component")
	
	standard_cols = ["name", "creation", "modified", "owner", "modified_by", "parent", "parenttype", "parentfield", "idx"]
	
	dt_cols = {
		"Salary Structure Deduction": ["d_type", "d_modified_amt", "depend_on_lwp"],
		"Salary Structure Earning": ["e_type", "modified_value", "depend_on_lwp"],
		"Salary Slip Earning": ["e_type", "e_modified_amount", "e_depends_on_lwp", "e_amount"],
		"Salary Slip Deduction": ["d_type", "d_modified_amount", "d_depends_on_lwp", "d_amount"],
	}
	
	earning_type_exists = True if "earning_type" in frappe.db.get_table_columns("Salary Slip Earning") else False
	e_type_exists = True if "e_type" in frappe.db.get_table_columns("Salary Slip Earning") else False
	
	
	if e_type_exists and earning_type_exists:
		frappe.db.sql("""update `tabSalary Slip Earning` 
			set e_type = earning_type, e_modified_amount = earning_amount
			where e_type is null and earning_type is not null""")

		frappe.db.sql("""update `tabSalary Structure Earning` set e_type = earning_type 
			where e_type is null and earning_type is not null""")

		frappe.db.sql("""update `tabSalary Slip Deduction` set 
			d_type = deduction_type, d_modified_amount = deduction_amount
			where d_type is null and deduction_type is not null""")

		frappe.db.sql("""update `tabSalary Structure Deduction` set d_type = deduction_type 
			where d_type is null and deduction_type is not null""")
			
	if earning_type_exists and not e_type_exists:
		for val in dt_cols.values():
			if val[0] == "e_type":
				val[0] = "earning_type"
			
			if val[0] == "d_type":
				val[0] = "deduction_type"
				
			if val[1] == "e_modified_amount":
				val[1]  ="earning_amount"
				
			if val[1] == "d_modified_amount":
				val[1]  ="deduction_amount"
			

	
	target_cols = standard_cols + ["salary_component", "amount", "depends_on_lwp", "default_amount"]
	target_cols = "`" + "`, `".join(target_cols) + "`"		
	
	for doctype, cols in dt_cols.items():		
		source_cols = "`" + "`, `".join(standard_cols + cols) + "`"
		if len(cols) == 3:
			source_cols += ", 0"
		
		
		frappe.db.sql("""INSERT INTO `tabSalary Detail` ({0}) SELECT {1} FROM `tab{2}`"""
			.format(target_cols, source_cols, doctype))
			
	
	dt_cols_de = {
		"Deduction Type": ["deduction_name", "description"],
		"Earning Type": ["earning_name", "description"],
	}
	
	standard_cols_de = standard_cols
	

	target_cols = standard_cols_de + ["salary_component", "description"]
	target_cols = "`" + "`, `".join(target_cols) + "`"		
	
	for doctype, cols in dt_cols_de.items():		
		source_cols = "`" + "`, `".join(standard_cols_de + cols) + "`"
		try:
			frappe.db.sql("""INSERT INTO `tabSalary Component` ({0}) SELECT {1} FROM `tab{2}`"""
				.format(target_cols, source_cols, doctype))
		except Exception, e:
			if e.args[0]==1062:
				pass
			
	update_customizations()
			
	for doctype in ["Salary Structure Deduction", "Salary Structure Earning", "Salary Slip Earning", 
			"Salary Slip Deduction", "Deduction Type", "Earning Type"] :
		frappe.delete_doc("DocType", doctype)


def update_customizations():
	dt_cols = {
		"Salary Structure Deduction": {
			"d_type": "salary_component", 
			"deduction_type": "salary_component", 
			"d_modified_amt": "amount",
			"depend_on_lwp": "depends_on_lwp"
		},
		"Salary Structure Earning": {
			"e_type": "salary_component", 
			"earning_type": "salary_component", 
			"modified_value": "amount",
			"depend_on_lwp": "depends_on_lwp"
		},
		"Salary Slip Earning": {
			"e_type": "salary_component", 
			"earning_type": "salary_component", 
			"e_modified_amount": "amount",
			"e_amount" : "default_amount",
			"e_depends_on_lwp": "depends_on_lwp"
		},
		"Salary Slip Deduction": {
			"d_type": "salary_component", 
			"deduction_type": "salary_component", 
			"d_modified_amount": "amount",
			"d_amount" : "default_amount",
			"d_depends_on_lwp": "depends_on_lwp"
		}
	}
	
	update_property_setters_and_custom_fields("Salary Detail", dt_cols)
	
	dt_cols = {
		"Earning Type": {
			"earning_name": "salary_component"
		},
		"Deduction Type": {
			"deduction_name": "salary_component"
		}
	}
	
	update_property_setters_and_custom_fields("Salary Component", dt_cols)
	
	
	
	
def update_property_setters_and_custom_fields(new_dt, dt_cols):
	for doctype, cols in dt_cols.items():
		frappe.db.sql("update `tabProperty Setter` set doc_type = %s where doc_type=%s", (new_dt, doctype))
		frappe.db.sql("update `tabCustom Field` set dt = %s where dt=%s", (new_dt, doctype))
		
		
		for old_fieldname, new_fieldname in cols.items():
			update_property_setters(new_dt, old_fieldname, new_fieldname)
