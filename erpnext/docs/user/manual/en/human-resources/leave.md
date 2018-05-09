#Leaves - Overview
This section will help you understand how ERPNext enables you to effectively manage the leave schedule of your organization. It also explains the way employees can apply for leaves.
Employees create leave requests, which their respective managers (leave approver) can approve or reject. An Employee can select from a number of leave types such as sick leave, casual leave, privilege leave and so on. The number and type of leaves an Employee can apply is controlled by Leave Allocations. You can create Leave Allocations for a Leave Period based on the company's Leave Policy. You can also allocate additional leaves to your employees and generate reports to track leaves taken by Employees.

---

#Leave Type
> Human Resources > Leaves and Holiday > Leave Type > New Leave Type

Leave Type refers to types of leave allotted to an employee by a company. An employee can select a particular Leave Type while requesting for a leave. You can create any number of Leave Types based on your company’s
requirement.

<img class="screenshot" alt="New Leave Type"
	src="{{docs_base_url}}/assets/img/human-resources/new-leave-type.png">

**Max Leaves Allowed:** This field allows you to set the maximum number of leaves of this Leave Type that Employees can apply within a Leave Period.

**Applicable After (Working Days):** Employees who have worked with the company for this number of days are only allowed to apply for this Leave Type. Do note that any other leaves availed by the Employee after her joining date is also considered while calculating working days.

**Maximum Continuous Days Applicable:** It refers to maximum number of days this particular Leave Type can be availed at a stretch. If an employee exceeds the maximum number of days under a particular Leave Type, his/her extended leave may be considered as ‘Leave Without Pay’ and this may affect his/her salary calculation.

**Is Carry Forward:** If checked, the balance leave will be carried forwarded to the next allocation period.

**Is Leave Without Pay:** This ensures that the Leave Type will be treated as leaves without pay and salary will get deducted for this Leave Type.

**Allow Negative Balance:** If checked, system will always allow to approve leave application for the Leave Type, even if there is no leave balance.

**Include holidays within leaves as leaves:** Check this option if you wish to count holidays within leaves as a ‘leave’. Such holidays will be deducted from the total number of leaves.

**Is Compensatory:** Compensatory leaves are leaves granted for working overtime or on holidays, normally compensated as an encashable leave. You can check this option to mark the Leave Type as compensatory. An Employee can request for compensatory leaves (Compensatory Leave Request) and on approval of such requests, Leave Allocations are created allowing her to apply for leaves of this type later on.

**Is Optional:** Check this Optional Leaves are holidays which Employees can choose to avail from a list of holidays published by the company. The Holiday List for optional leaves can have any number of holidays but you can restrict the number of such leaves granted to an Employee in a Leave Period by setting the Max Days Leave Allowed field.

**Encashment:** It is possible that Employees can receive cash from their Employer for unused leaves granted to them in a Leave Period. Not all Leave Types need to be encashable, so you should set "Allow Encashment" for Leave Types which are encashable. Leave encashment is allowed only in the last month of the Leave Period.

<img class="screenshot" alt="Leave Encashment"
	src="{{docs_base_url}}/assets/img/human-resources/leave-encashment.png">

You can set the **Encashment Threshold Days** field so that the Employees wont be able to encash that many days. These days should be carry forwarded to the next Leave Period so that it can be either encashed or availed. You may also want to set the **Earning Component** for use in Salary Slip while paying out the encashed amount to Employees as part of their Salary.

**Earned Leave:** Earned Leaves are leaves earned by an employee after working with the company for a certain amount of time. Checking "Is Earned Leave" will allot leaves pro rata by automatically updating Leave Allocation for leaves of this type at intervals set by **Earned Leave Frequency**. For example, if an employee earns 2 leaves of type Paid Leaves monthly, ERPNext automatically increments the Leave Allocation for Paid Leave at the end of every month by 2. The leave allotment process (background job) will only allot leaves considering the max leaves for the leave type, and will round to **Rounding** for fractions.

<img class="screenshot" alt="Earned Leave"
	src="{{docs_base_url}}/assets/img/human-resources/earned-leave.png">

###Default Leave Types
There are some pre-loaded Leave Types in the system, as below:

- **Leave Without Pay:** You can avail these leaves for different purposes, such as, extended medical issues, educational purpose or unavoidable personal reason. Employee does not get paid for such leaves.
- **Privilege leave:** These are like earned leaves which can be availed for the purpose of travel, family vacation and so on.
- **Sick leave:** You can avail these leaves if you are unwell.
- **Compensatory off:** These are compensatory leave allotted to employees for overtime work.
- **Casual leave:** You can avail this leave to take care of urgent and unseen matters.

---

#Leave Policy
> Human Resources > Leaves and Holiday > Leave Policy > New Leave Policy

It is a practice for many enterprises to enforce a general Leave Policy to effectively track and manage Employee leaves. ERPNext allows you to create and manage multiple Leave Policies and allocate leaves to Employees as defined by the policy.

<img class="screenshot" alt="Leave Policy"
	src="{{docs_base_url}}/assets/img/human-resources/leave-policy.png">

### Enforcing the Leave Policy
To enforce the Leave Policy, you can either:
* Apply the Leave Policy in Employee Grade
<img class="screenshot" alt="Employee Grade"
	src="{{docs_base_url}}/assets/img/human-resources/employee-grade.png">

This will ensure all leave allocations for all employees of this grade will be as per the Leave Policy

* Update Employee record with appropriate Leave Policy. In case you need to selectively update the Leave Policy for a particular Employee, you can do so by updating the Employee record.

<img class="screenshot" alt="Employee Leave Policy"
	src="{{docs_base_url}}/assets/img/human-resources/employee-leave-policy.png">

#Leave Period
Most companies manage leaves based on a Leave Period. ERPNext allows you to create a Leave period by going to
> Human Resources > Leaves and Holiday > Leave Period > New Leave Period

	<img class="screenshot" alt="Leave Period"
		src="{{docs_base_url}}/assets/img/human-resources/leave-period.png">

#Granting Leaves to Employees
Leave Management in ERPNext is based on Leave Allocations created for each employee. This means, Employees can only avail as many leaves (of each Leave Type) allocated to them. There are multiple ways by which you can create Leave Allocations for Employees.

###Leave Allocation
Leave Allocation enables you to allot a specific number of leaves to a particular employee. You can allocate a number of leaves to different types of leave.

###Allocating leaves for a Leave Period
> Human Resources > Leaves and Holiday > Leave Period

Leave Period helps you manage leaves for a period and also doubles up as a tool to help you grant leaves for a category of employees. The **Grant** button will generate Leave Allocations based on the Leave Policy applicable to each Employee. You can allocate leaves based on Employee Grade, Department or Designation. Also, note that **Carry Forward Leaves** check will enable you to carry forward any unused leaves (for Leave Types with Is Carry Forward turned on) from previous allocations to new ones.

<img class="screenshot" alt="Grant Leaves from Leave Period"
	src="{{docs_base_url}}/assets/img/human-resources/leave-period-grant.png">

###Manual Allocation of leaves
> Human Resources > Leaves and Holiday > Leave Allocation > New Leave Allocation

To manually allocate leaves for an Employee, select the period and the number of leaves you want to allocate. You can also add unused leaves from previous allocation period.

<img class="screenshot" alt="Manual Leave Allocation"
	src="{{docs_base_url}}/assets/img/human-resources/manual-leave-allocation.png">

---

#Leave Application
> Human Resources > Leaves and Holiday > Leave Application > New Leave Application

Leave Application section enables an employee to apply for leaves. Employee can select the type of leave and the Leave Approver who will authorize the Leave Application. User with "Leave Approver" role are considered as Leave approver. Leave Approvers can also be restricted/pre-defined in the Employee record. Based on selected dates and applicable Holiday List, total leave days is calculated automatically.

**Basic Workflow:**

- Employee applies for leave through Leave Application
- Approver gets notification via email, "Follow via Email" should be checked for this.
- Approver reviews Leave Application
- Approver approves/rejects Leave Application
- Employee gets notification on the status of his/her Leave Application

<img class="screenshot" alt="Leave Allocation Tool"
	src="{{docs_base_url}}/assets/img/human-resources/new-leave-application.png">


**Notes:**

- Leave Application period must be within a single Leave Allocation period. In case, you are applying for leave across leave allocation period, you have to create two Leave Application records.
- Application period must be in the latest Allocation period.
- Employee can't apply for leave on the dates which are added in the "Leave Block List".

---

#Leave Block List

> Human Resources > Leaves and Holiday > Leave Block List > New Leave Block List

Leave Block List is a list of dates in a year, on which employees can not apply for leave. You can define a list of users who can approve Leave Application on blocked days, in case of urgency. You can also define whether the list will applied on entire company or any specific departments.

<img class="screenshot" alt="Leave Allocation Tool"
	src="{{docs_base_url}}/assets/img/human-resources/leave-block-list.png">
