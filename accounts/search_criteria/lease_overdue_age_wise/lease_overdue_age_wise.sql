select account,sum(od_30)as od_30,sum(od_90)as od_90,sum(od_180)as od_180,sum(od_360)as od_360,sum(od_1yr)as od_1yr from
(
	select account,case when age<=30 then amount end as od_30,case when age between 31 and 90 then amount end as od_90,case when age between 91 and 180 then amount end as od_180,case when age between 181 and 360 then amount end as od_360,case when age>360 then amount end as od_1yr from
	(
		select la.account,lai.amount,cast('%(date)s' as date)-due_date as age
		from `tabLease Agreement` la,`tabLease Installment` lai
		where la.name=lai.parent and lai.due_date<'%(date)s' and (lai.cheque_date is null or lai.cheque_date > '%(date)s')
	)a
)b group by account order by account
