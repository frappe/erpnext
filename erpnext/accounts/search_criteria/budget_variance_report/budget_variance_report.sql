SELECT 
	CONCAT(REPEAT('     ', COUNT(parent.name) - 1), node.name) AS name 
FROM 
	`tabCost Center` AS node,`tabCost Center` AS parent 
WHERE 
	node.lft BETWEEN parent.lft AND parent.rgt 
	AND node.docstatus !=2
	AND node.company_name like '%(company)s%%'
GROUP BY node.name 
ORDER BY node.lft
