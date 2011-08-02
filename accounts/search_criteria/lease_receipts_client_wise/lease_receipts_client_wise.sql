SELECT gl.account,sum(gl.credit) as amount
FROM `tabGL Entry` gl, `tabAccount` a
WHERE gl.account=a.name and a.master_type='Customer' and gl.posting_date between '%(date)s' and '%(date1)s'
GROUP BY gl.account
ORDER BY posting_date
