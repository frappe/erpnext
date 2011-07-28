SELECT date_format(gl.posting_date,'%M'),year(gl.posting_date),sum(gl.credit) as amount
FROM `tabGL Entry` gl, `tabAccount` a
WHERE gl.account=a.name and a.master_type='Customer' and gl.credit>0 and gl.posting_date between '%(date)s' and '%(date1)s'
GROUP BY month(gl.posting_date),year(gl.posting_date)
ORDER BY year(gl.posting_date),month(gl.posting_date)
