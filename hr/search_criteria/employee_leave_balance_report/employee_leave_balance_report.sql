SELECT
	leave_alloc.employee AS 'employee',
	leave_alloc.employee_name AS 'employee_name',
	leave_alloc.fiscal_year AS 'fiscal_year',
	leave_alloc.leave_type AS 'leave_type',
	leave_alloc.total_leaves_allocated AS 'total_leaves_allocated',
	SUM(leave_app.total_leave_days) AS 'total_leaves_applied'
FROM
	`tabLeave Allocation` AS leave_alloc LEFT JOIN `tabLeave Application` AS leave_app
	ON leave_alloc.employee=leave_app.employee AND
	leave_alloc.leave_type=leave_app.leave_type AND
	leave_alloc.fiscal_year=leave_app.fiscal_year AND
	leave_app.docstatus=1
WHERE
	leave_alloc.docstatus=1  AND
	leave_alloc.fiscal_year LIKE '%(fiscal_year)s%%' AND
	leave_alloc.employee_name LIKE '%(employee_name)s%%'
GROUP BY
	employee,
	fiscal_year,
	leave_type
ORDER BY
	employee,
	fiscal_year,
	leave_type