# Authorization Rule

Authorization Rule is a tool to define rule for conditional authorization.

If you sales and purchase transactions of higher value or discount requires an authorization from senior manager, you can set authorization rule for it.

To create new Authorization Rule, go to:

> Setup > Customize > Authorization Rule

Let's consider an example of Authorization Rule to learn better.

Assume that Sales Manager needs to authorize Sales Orders, only if its Grand Total value exceeds 10000. If Sales Orer values is less than 10000, then even Sales User will be able to submit it. It means Submit permision of Sales User will be restricted only upto Sales Order of Grand Total less than 10000.

**Step 1:**

Open new Authorization Rule

**Step 2:**

Select Company and Transaction on which Authorization Rule will be applicable. This functionality is available for limited transactions only.

**Step 3:**

Select Based On. Authorization Rule will be applied based on value selected in this field.

**Step 4:**

Select Role on whom this Authorization Rule will be applicable. As per the example considered, Sales User will be selected as Application To (Role). To be more specific you can also select Applicable To User, if you wish to apply the rule for specific Sales User, and not all Sales User. Its okay to not select Sales User, as its not mandatory.

**Step 5:**

Select approvers Role. It will be Sales Manager role which if assigned to user, will be able to submit Sales Order above 10000. Also you can select specific Sales Manager, and then rule should be applicable for that User only. Selecting Approving User field is not mandatory.

**Step 6:**

Set Above Value. Given the exmaple, Above Value will be set as 10000.

<img class="screenshot" alt="Authorization Rule" src="{{docs_base_url}}/assets/img/setup/auth-rule.png">

If Sales User tries submitting Sales Order of value higher than 10000, then he will get error message.

>If you wish to restrict Sales User from submitting Sales Orders, then instead of creating Authorization Rule, you should remove submit previledge from Role Permission Manager for Sales User.

{next}
