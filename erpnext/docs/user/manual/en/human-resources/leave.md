#Overview
This section enables you to manage leave schedule of your organization. It also explains the way employees can apply for leaves.  
Employees create leave request and manager (leave approver) approves or rejects the request. You can select from a number of leave types such as sick leave, casual leave, privilege leave and so on. You can also allocate leaves to your employees and generate reports to track leaves record.

---

#Leave Type

> Human Resources > Setup > Leave Type > New Leave Type

Leave Type refers to types of leave allotted to an employee by a company. An employee can select a particular Leave Type while requesting for a leave. You can create any number of Leave Types based on your company’s 
requirement.

<img class="screenshot" alt="New Leave Type" 
	src="/docs/assets/img/human-resources/new-leave-type.png">

**Max Days Leave Allowed:** It refers to maximum number of days this particular Leave Type can be availed at a stretch. If an employee exceeds the maximum number of days under a particular Leave Type, his/her extended leave may be considered as ‘Leave Without Pay’ and this may affect his/her salary calculation.

**Is Carry Forward:** If checked, the balance leave will be carried forwarded to the next allocation period.

**Is Leave Without Pay:** This ensures that the Leave Type will be treated as leaves whithout pay and salary will get deducted for this Leave Type.

**Allow Nagative Balance:** If checked, system will always allow to approve leave application for the Leave Type, even if there is no leave balance.

**Include holidays within leaves as leaves:** Check this option if you wish to count holidays within leaves as a ‘leave’. Such holidays will be deducted from the total number of leaves.

###Default Leave Types
There are some pre-loaded Leave Types in the system, as below:

- **Leave Without Pay:** You can avail these leaves for different purposes, such as, extended medical issues, educational purpose or unavoidable personal reason. Employee does not get paid for such leaves.
- **Privilege leave:** These are like earned leaves which can be availed for the purpose of travel, family vacation and so on.
- **Sick leave:** You can avail these leaves if you are unwell.
- **Compensatory off:** These are compensatory leave allotted to employees for overtime work.
- **Casual leave:** You can avail this leave to take care of urgent and unseen matters.

---

#Leave Allocation

Leave Allocation enables you to allot a specific number of leaves to a particular employee. You can allocate a number of leaves to different types of leave. You also have the option to allocate leaves to your employees manually or via the Leave Allocation Tool.

###Manual Allocation
> Human Resources > Setup > Leave Allocation > New Leave Allocation

To allocate leaves to an Employee, select the period and the number of leaves you want to allocate. You can also add unused leaves from previous allocation period.

<img class="screenshot" alt="Manual Leave Allocation" 
	src="/docs/assets/img/human-resources/manual-leave-allocation.png">

###Via Leave Allocation Tool
> Human Resources > Tools > Leave Allocation Tool

This tool enables you to allocate leaves for a category of employees, instead of individual ones. You can allocate leaves based on Employee Type, Branch, Department and Designation. Leave Allocation Tool is also known as Leave Control Panel.

<img class="screenshot" alt="Leave Allocation Tool"
	src="/docs/assets/img/human-resources/leave-allocation-tool.png">

---

#Leave Application
> Human Resources > Documents > Leave Application > New Leave Application

Leave Application section enables an employee to apply for leaves. Employee can select the type of leave and the Leave Approver who will authorize the Leave Application. User with "Leave Approver" role are considered as Leave approver. Leave Approvers can also be restricted/pre-defined in the Employee record. Based on selected dates and applicable Holiday List, total leave days is calculated automatically.

**Basic Workflow:**

- Employee applies for leave through Leave Application
- Approver gets notification via email, "Follow via Email" should be checked for this.
- Approver reviews Leave Application
- Approver approves/rejects Leave Application
- Employee gets notification on the status of his/her Leave Application

<img class="screenshot" alt="Leave Allocation Tool"
	src="/docs/assets/img/human-resources/new-leave-application.png">

	
**Notes:**

- Leave Application period must be within a single Leave Allocation period. In case, you are applying for leave across leave allocation period, you have to create two Leave Application records.
- Application period must be in the latest Allocation period.
- Employee can't apply for leave on the dates which are added in the "Leave Block List".

---

#Leave Block List

> Human Resources > Setup > Leave Block List > New Leave Block List

Leave Block List is a list of dates in a year, on which employees can not apply for leave. You can define a list of users who can approve Leave Application on blocked days, in case of urgency. You can also define whether the list will applied on entire company or any specific departments.

<img class="screenshot" alt="Leave Allocation Tool"
	src="/docs/assets/img/human-resources/leave-block-list.png">