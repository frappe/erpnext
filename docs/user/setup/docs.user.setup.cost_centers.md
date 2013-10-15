---
{
	"_label": "Cost Centers and Budgeting",
	"_icon": "sitemap",
	"_links": [
		"docs.user.accounts"
	]
}
---

Your Chart of Accounts is mainly designed to provide reports to the government and tax authorities.
￼
Most businesses have multiple activities like different product lines, market segments, areas of business, etc that share some common overheads.They should ideally have their own structure to report, whether they are profitable or not. For this purpose, there is an alternate structure, called the Chart of Cost Centers.

You can create a tree of Cost Centers to represent your business better. Each Income / Expense entry is also tagged against a Cost Center. 

For example, if you have two types of sales:

- Walk-in Sales
- Online Sales

You may not have shipping expenses for your walk-in customers, and no shop-rent for your online customers. If you want to get the profitability of each of these separately, you should create the two as Cost Centers and mark all sales as either "Walk-in" or "Online". Mark your all your purchases in the same way.

Thus when you do your analysis you get a better understanding as to which side of your business is doing better. Since ERPNext has an option to add multiple Companies, you can create Cost Centers for each Company and manage it separately.

To understand chart of cost centers in detail visit [Accounting Knowledge](docs.user.knowledge.accounting.html)


### Chart of Cost Centers

To setup your Chart of Cost Centers go to:

> Accounts > Chart of Cost Centers


![Chart of Cost Center](img/chart-of-cost-centers.png)


Cost centers help you in one more activity, budgeting.

### Budgeting

ERPNext will help you set and manage budgets on your Cost Centers. This is useful when, for example, you are doing online sales. You have a budget for search ads, and you want ERPNext to stop or warn you from over spending, based on that budget. 

Budgets are also great for planning purposes. When you are making plans for the next financial year, you would typically target a revenue based on which you would set your expenses. Setting a budget will ensure that your expenses do not get out of hand, at any point, as per your plans.

You can define it in the Cost Center. If you have seasonal sales you can also define a budget distribution that the budget will follow.

> Accounts > Budget Distribution > New Budget Distribution


![Budget Distribution](img/budgeting.png)



￼
#### Budget Actions

ERPNext allows you to either:

- Stop.
- Warn or, 
- Ignore 

if you exceed budgets. 

These can be defined from the Company record.

Even if you choose to “ignore” budget overruns, you will get a wealth of information from the “Budget vs Actual” variance report.

> Note: When you set a budget, it has to be set as per Account under the Cost Center. For example if you have a Cost Center “Online Sales”, you can restrict “Advertising Budget” by creating a row with that Account and defining the amount.