import frappe
import os, time
from frappe.utils import nowdate, cstr, cint, flt, add_days
from six import iteritems

# header = ['pfno', 'pname', 'levman', 'pemp', 'deptname', 'pdesc', 'Basic Fixed', 'grade_pay1', 
#    'Attendance', 'pml', 'perl', 'plwp', '1 - Basic Pay', '2 - Grade Pay', 'Pay20', '4 - DA', '6 - CLA', 
#    '3 - HRA', '35 - Handicap', '12 - N.P.All', '34 - 24 HOURS DUTY ALLOWANCE', '15 - WASHING ALLOWANCE', 
#    '10 - CASH HANDLING ALLOWANCE', '38 - CONVEYANCE ALLOWANCE', '23 - UNIFORM ALLOWANCE', '55 - Other Benefit', 
#    'Gross Pay', '19 - HRR', 'PCNBPF', '5 - P.Tax', 'Postal Stamp Charge', 'Recurring Deposit', '6 - INCOME TAX', 
#    '30 - P.F.LOAN', '16 - SOCIETY', '33 - FESC.ADV.', '25 - LIC', 'Additional PF', 'Recovery Charges', 
#    '13 - Other Adv', 'Gross deduction', 'Netpay', 'bank_ac', 'bank_micr', 'ic', 'bank_name']

company = 'Thane Municipal Corporation'
zones = {
    'D': 'Diva',
    'H': 'CSM Hospital',
    'L': 'Lokmanya Nagar',
    'V': 'Vartak Nagar',
    '1': 'Uthalsar',
    '3': 'Mumbra',
    '4': 'Kalwa',
    '5': 'Manpada',
    '7': 'Wagale',
    '8': 'Head Office',
    '9': 'Naupada'
}

emp_filename = "employee.xlsx"
allowance_filename = 'allowance.xlsx'
deduction_filename = 'deduction.xlsx'
allowance_component_filename = 'earning_component.xlsx'
ded_component_filename = 'deduction_component.xlsx'
salary_slip_filename = 'salary_slip.xlsx'



def execute():
    t1 = time.time()
    # delete_existing_records()
    # create_zone()
    # import_employee()
    # import_earning_component()
    # import_deduction_component()
    import_salary_structure()
    print(time.time() - t1)
    # create_banks()

def delete_existing_records():
    for dt in ("Salary Component", "Salary Component Account", "Payroll Entry", "Leave Application", 
        "Salary Structure", "Salary Structure Assignment", "Salary Detail", "Salary Slip", "Additional Salary"):
            frappe.db.sql("delete from `tab{0}`".format(dt))
    # "Employee", "Branch", "Designation", 
    # frappe.db.sql("delete from `tabDepartment` where name != 'All Departments - TMC'")

def create_zone():    
    for code, name in iteritems(zones):
        z = frappe.new_doc("Branch")
        z.branch = code + " - " + name
        z.branch_code = code
        z.save()

def import_employee():
    frappe.db.set_value("HR Settings", None, "emp_created_by", "Employee Number")

    header, data = load_xlsx(emp_filename)

    col_map = {
        "desg_code": "CODE",
        "desg": "DESIGN",
        "dept_code": "DPTCODE",
        "dept": "DEPT",
        "first_name": "FNAME",
        "middle_name": "MNAME",
        "last_name": "SNAME",
        "employee_name": "NAME",
        "zone_code": "ZONE",
        "employee_number": "EMPCODE",
        "zender": "SEX"
    }

    col_idx = frappe._dict()
    for d in col_map:
        col_idx[d] = header.index(col_map[d])
    i = 1
    for row in data:
        if row[col_idx.desg]:
            designation = create_designation(row[col_idx.desg_code], row[col_idx.desg])
        if row[col_idx.dept]:
            department = create_department(row[col_idx.dept_code], row[col_idx.dept])

        create_employee(row, department, designation, col_idx)
        if i % 100==0:
            frappe.db.commit()
        print(i)
        i += 1

def create_designation(code, name):
    desg = code + " - " + name if code else name
    try:
        d = frappe.new_doc("Designation")
        d.designation_name = desg
        d.insert()
    except frappe.DuplicateEntryError:
        pass
    return desg

def create_department(code, name):
    dept = code + " - " + name if code else name
    try:
        d = frappe.new_doc("Department")
        d.department_name = dept
        d.company = company
        d.parent_department = "All Departments - TMC"
        d.insert()
    except frappe.DuplicateEntryError:
        pass
    
    return dept + " - TMC"

def create_employee(row, dept, desg, col_idx):
    if frappe.db.exists("Employee", row[col_idx["employee_number"]]):
        return

    emp = frappe.new_doc("Employee")

    for f in ["first_name", "middle_name", "last_name", "employee_name", "employee_number"]:
        emp.set(f, row[col_idx[f]])
    if not emp.first_name:
        emp.first_name = emp.employee_name
    emp.designation = desg
    emp.department = dept
    emp.date_of_birth = "1990-01-01"
    emp.date_of_joining = "2010-01-01"
    emp.gender = "Female" if row[col_idx.zender]=="F" else "Male"
    emp.status = "Active"
    emp.company = company
    if col_idx.zone_code and row[col_idx.zone_code] and zones.get(row[col_idx.zone_code]):
        emp.branch = row[col_idx.zone_code] + " - " + zones[row[col_idx.zone_code]]
    emp.save()

def import_earning_component():
    standard_components = [
        {
            "component_code": "1",
            "description": "Basic",
            "salary_component": "1 - Basic",
            "salary_component_abbr": "BA"
        },
        {
            "component_code": "2",
            "description": "Grade pay",
            "salary_component": "2 - Grade Pay",
            "salary_component_abbr": "GP"
        },
        {
            "component_code": "3",
            "description": "HRA",
            "salary_component": "3 - HRA",
            "salary_component_abbr": "HRA",
            "amount_based_on_formula": 1,
            "formula": ".3*(BA+GP)"
        },
        {
            "component_code": "4",
            "description": "Dearness Allowance",
            "salary_component": "4 - Dearness Allowance",
            "salary_component_abbr": "DA",
            "amount_based_on_formula": 1,
            "formula": "1.39*(BA+GP)"

        },
        {
            "component_code": "12",
            "description": "Non Practicing Allowance",
            "salary_component": "12 - Non Practicing Allowance",
            "salary_component_abbr": "NONPA",
            "amount_based_on_formula": 1,
            "formula": ".25*BA",
            "prorated_based_on_attendance": 1

        },
        {
            "component_code": "6",
            "description": "City Allowance",
            "salary_component": "6 - City Allowance",
            "salary_component_abbr": "CLA",
            "amount": 300
        },
        {
            "component_code": "35",
            "description": "Handicap Allowance",
            "salary_component": "35 - Handicap Allowance",
            "salary_component_abbr": "HANDICAP",
            "amount": 2000,
            "prorated_based_on_attendance": 1

        },
    ]

    for d in standard_components:
        d.update({
            "type": "Earning",
            "is_payable": 1,
            "depends_on_lwp": 1
        })
        create_salary_component(d)

    # allowance
    header, data = load_xlsx(allowance_component_filename)

    for row in data:
        # row = [miscode, amount, desc]
        if row[1] and row[2]:
            create_salary_component({
                "salary_component": row[0] + " - " + row[2],
                "component_code": row[0],
                "description": row[2],
                "type": "Earning",
                "amount": row[1],
                "is_payable": 1,
                "prorated_based_on_attendance": 1,
                "salary_component_abbr": frappe.scrub(row[2])[:10]
            })
    
    # Deduction Component
def import_deduction_component():
    standard_components = [
        {
            "component_code": "5",
            "description": "Professional Tax",
            "salary_component": "5 - Professional Tax",
            "salary_component_abbr": "PPT",
            "amount": "200"
        },
        {
            "description": "Provident Fund Deducted from Salary",
            "salary_component": "Provident Fund Deducted from Salary",
            "salary_component_abbr": "PNCBPF",
            "amount_based_on_formula": 1,
            "formula": "0.0833*(BA+GP)",
            "depends_on_lwp": 1
        },
        {
            "description": "Postal Stamp Charge",
            "salary_component": "Postal Stamp Charge",
            "salary_component_abbr": "PST",
            "amount": 1
        }
    ]

    for d in standard_components:
        d["type"] = "Deduction"
        create_salary_component(d)

    header, data = load_xlsx(ded_component_filename)

    for row in data:
        # row = [msscode, desc]
        if row[1]:
            create_salary_component({
                "salary_component": row[0] + " - " + row[1],
                "description": row[1],
                "type": "Deduction",
                "salary_component_abbr": frappe.scrub(row[1])[:10],
                "component_code": row[0]
            })

def create_salary_component(args):
    try:
        c = frappe.new_doc("Salary Component")
        c.is_additional_component = 1
        c.append("accounts", {
            "company": company,
            "account": "Salary - TMC"
        })
        c.update(args)
        c.save()
    except frappe.DuplicateEntryError:
        pass

def import_salary_structure():
    allowance_map, half_hra = get_allowance_map()
    deduction_map = get_deduction_component_map()

    header, data = load_xlsx(salary_slip_filename)
    basic_idx, gp_idx, emp_code_idx, emp_name_idx, lwp_idx, pother_idx = \
        header.index("abas"), header.index("grade_pay1"), header.index("pemp"), \
        header.index("pname"), header.index("plwp"), header.index("pother")

    employee_list = [d.name for d in frappe.get_all("Employee")]

    # empl = frappe.db.sql_list("""
    #     select name from tabEmployee
    #     where department in ('20001 - COMPUTER DEPT - TMC', '20001 - COMPUTER STAFF - TMC')
    # """)
    # print(empl)
    i=1
    for row in data[6001:]:
        emp = row[emp_code_idx]
        if emp and emp in employee_list:
            emp_name = row[emp_name_idx]
            allowances = allowance_map.get(row[emp_code_idx], [])
            deductions = deduction_map.get(row[emp_code_idx], [])
            ss = create_salary_structure(emp, emp_name, row[basic_idx], row[gp_idx], allowances, deductions, half_hra)
            assignment = create_salary_structure_assignment(ss, row[emp_code_idx])
            if flt(row[lwp_idx]) > 0:
                create_leave_application(emp, emp_name, row[lwp_idx])
            #if flt(row[pother_idx]) > 0:
            #    create_additional_salary(emp, emp_name, flt(row[pother_idx]))
            
            if i % 100==0:
                frappe.db.commit()

            print(i)
            i+=1

def get_allowance_map():
    header, data = load_xlsx(emp_filename)
    ec_map = frappe._dict()

    half_hra = []

    for d in data:
        emp = d[header.index("EMPCODE")]
        ec_map.setdefault(emp, [])

        if cint(d[header.index("NONPAALL")]):
            ec_map[emp].append("12 - Non Practicing All")
        
        if cint(d[header.index("HANALL")]):
            ec_map[emp].append("35 - Handicap All")

        if cint(d[header.index("HRAALL")]) in (0, 2, 4):
            ec_map[emp].append("3 - HRA")

        if cint(d[header.index("HRAALL")]) == 3:
            half_hra.append(emp)

    comp_code = {}
    for d in frappe.get_all("Salary Component", fields=["name", "component_code"], filters={"type": "Earning"}):
        comp_code.setdefault(d.component_code, d.name)

    header, data = load_xlsx(allowance_filename)

    for i, d in enumerate(data):
        for n in range(3, 12):
            if d[n]:
                if comp_code.get(d[n]):
                    ec_map.setdefault(d[0], []).append(comp_code.get(d[n]))
    
    return ec_map, half_hra

def get_deduction_component_map():
    comp_code = {}
    for d in frappe.get_all("Salary Component", fields=["name", "component_code"],
        filters={"type": "Deduction", "component_code": ["!=", ""]}):
            comp_code.setdefault(d.component_code, d.name)

    header, data = load_xlsx(deduction_filename)
    dc_map = frappe._dict()
    for d in data:
        if d[0] and d[3] and d[6]:
            dc_map.setdefault(d[0], []).append([comp_code.get(d[3]), d[6]])

    return dc_map

def create_salary_structure(emp, emp_name, basic, grade_pay, allowances, deductions, half_hra):
    ss = frappe.new_doc("Salary Structure")
    ss.name = "SS-" + emp + "-" + emp_name
    ss.company = company
    ss.is_active = "Yes"
    ss.payroll_frequency = 'Monthly'
    ss.is_default = "Yes"

    ss.append("earnings", {
        "salary_component": "1 - Basic",
        "amount": basic
    })

    ss.append("earnings", {
        "salary_component": "2 - Grade Pay",
        "amount": grade_pay
    })

    # DA, HRA
    allowances = ["4 - Dearness Allowance", "6 - City Allowance"] + allowances
    for d in allowances:
        if d not in ["041 - UNCLEAN ALLOWANCE"]:
            ss.append("earnings", {
                "salary_component": d
            })
    
    # half hra
    if emp in half_hra:
        ss.append("earnings", {
            "salary_component": "3 - HRA",
            "amount_based_on_formula": 1,
            "formula": ".6*(BA+GP)",
            "depends_on_lwp": 1,
            "is_payable": 1
        })

    for d in ["Provident Fund Deducted from Salary", "Postal Stamp Charge", "5 - Professional Tax"]:
        ss.append("deductions", {
            "salary_component": d
        })

    # for d in deductions:
    #     ss.append("deductions", {
    #         "salary_component": d[0],
    #         "amount": d[1]
    #     })

    ss.save()
    ss.submit()

    return ss.name

def create_salary_structure_assignment(ss, employee):
    ssa = frappe.new_doc("Salary Structure Assignment")
    ssa.employee = cstr(employee)
    ssa.salary_structure = ss
    ssa.from_date = "2018-04-01"
    ssa.company = company
    ssa.save()
    ssa.submit()

def create_leave_application(emp, emp_name, lwp):
    l = frappe.new_doc("Leave Application")
    l.employee = emp
    l.leave_type = 'Leave Without Pay'
    l.from_date = "2018-08-01"
    l.to_date = add_days("2018-08-01", round(lwp)-1)
    if lwp != round(lwp):
        l.half_day = 1
        l.half_day_date = l.to_date
    l.posting_date = nowdate()
    l.company = company
    l.status = "Approved"
    l.save()
    l.submit()

def create_additional_salary(emp, emp_name, amount):
    a = frappe.new_doc("Additional Salary")
    a.salary_component = "425 - ADDITIONAL ADJUSTED PAY"
    a.employee = emp
    a.amount = amount
    a.from_date = "2018-08-01"
    a.to_date = "2018-08-31"
    a.company = company
    a.overwrite_salary_structure_amount = 1
    a.save()
    a.submit()

def load_xlsx(filename):
    from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file
    path = os.path.join(frappe.get_app_path('erpnext'), 'tmc', filename)
    raw = read_xlsx_file_from_attached_file(filepath=path)
    header = raw[0]
    data = raw[1:]
    return header, data

def create_banks():
    header, data = load_xlsx("bank.xlsx")
    for d in data:
        try:
            bank = frappe.new_doc("Bank")
            bank.bank_code = d[0]
            bank.bank_name = d[1]
            bank.description = d[2]
            bank.save()
        except:
            pass