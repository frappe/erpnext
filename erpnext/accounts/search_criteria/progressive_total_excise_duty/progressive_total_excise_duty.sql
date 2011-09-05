SELECT t1.posting_date, t1.name, SUM(CASE WHEN t2.account_head like '%(main_acc_head)s%' THEN t2.tax_amount ELSE 0.00 END), SUM(CASE WHEN t2.account_head like '%(edu_cess_acc_head)s' THEN t2.tax_amount ELSE 0.00 END),  SUM(CASE WHEN t2.account_head like '%(sh_edu_cess_acc_head)s' THEN t2.tax_amount ELSE 0.00 END), '' AS remarks
 FROM `tabDelivery Note` t1, `tabRV Tax Detail` t2
 WHERE t2.parent = t1.name
 AND t2.parenttype = 'Delivery Note'
 AND (t2.account_head LIKE '%(main_acc_head)s%%'
 OR t2.account_head LIKE '%(edu_cess_acc_head)s%%'
 OR t2.account_head LIKE '%(sh_edu_cess_acc_head)s%%')
 AND t1.`posting_date` >= '%(posting_date)s'
 AND t1.`posting_date` <= '%(posting_date1)s'
 AND t1.docstatus =1
 GROUP BY t1.`name`

UNION

SELECT t1.posting_date, t1.name, SUM(CASE WHEN t2.account like '%(main_acc_head)s' THEN t2.credit ELSE 0.00 END), SUM(CASE WHEN t2.account like '%(edu_cess_acc_head)s' THEN t2.credit ELSE 0.00 END),  SUM(CASE WHEN t2.account like '%(sh_edu_cess_acc_head)s' THEN t2.credit ELSE 0.00 END), t1.`remark`
 FROM `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2
 WHERE (t2.credit is not NULL OR t2.credit != '')
 AND t2.credit > 0
 AND t2.parent = t1.name
 AND (t2.account LIKE '%(main_acc_head)s%'
 OR t2.account LIKE '%(edu_cess_acc_head)s%'
 OR t2.account LIKE '%(sh_edu_cess_acc_head)s%') 
 AND t1.`posting_date` >= '%(posting_date)s'
 AND t1.`posting_date` <= '%(posting_date1)s'
 AND t1.docstatus =1
 GROUP BY t2.`parent`

ORDER BY `posting_date`,`name`