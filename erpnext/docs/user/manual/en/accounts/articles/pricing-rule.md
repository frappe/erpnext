<h1>Pricing Rule</h1>

Pricing Rule allows you to define rules based on which item's price or discount to be applied is determined.

### Scenario:

Following are the few cases which can be addressed using Pricing Rule.

1. As per the promotional sale policy, if customer purchases more than 10 units of an item, he enjoys 20% discount. 

2. For Customer "XYZ", selling price for the specific or group of "Products" should be updated as ###.

3. Items categorized under specific Item Group has same selling or buying price.

4. Customers catering to specific Customer Group has same selling price.

5. Supplier's categorized under common Supplier Type should have same buying rate applied.

To have %Discount and Price List Rate for an Item auto-applied, you should set Pricing Rules for it.

Pricing Rule master has two sections:

### 1. Applicability Section:

In this section, conditions are set for the Pricing Rule. When transaction meets condition as specified in the Pricing Rule, Price or Discount as specified in the Item master will be applicable. You can set condition on following values.

####1.1 Applicable On:

![Applicable On]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-04-09 at 1.26.23 pm.png)

If you want Pricing Rule to be applied on all the items, you should apply rule based on Item Group, and select most Parent Item Group for a value.

####1.2 Applicable For:

Applicability option will updated based on our selection for Selling or Buying or both. You can set applicability on one of the following master.

![Applicable for]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-04-09 at 1.27.31 pm.png)

####1.3 Quantity:

Specify minimum and maximum qty of an item when this Pricing Rule should be applicable.

![Pricing Rule Qty limit]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-04-09 at 1.28.05 pm.png)

###2. Application:

Using Price List Rule, you can ultimately define price or %discount to be applied on an item.

![Pricing Rule Apply on]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-04-09 at 1.33.24 pm.png)

####2.1 Price

Price or Discount specified in the Pricing Rule will be applied only if above applicability rules are matched with values in the transaction. Price mentioned in Pricing Rule will be given priority over item's Price List rate.

![Pricing Rule Price]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-04-09 at 1.30.27 pm.png)

####2.2 Discount Percentage

Discount Percentage can be applied for a specific Price List. To have it applied for all the Price List, %Discount field should be left blank.

![Rule Discount Percent]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-04-09 at 1.31.01 pm.png)

#### Validity

Enter From and To date between which this Pricing Rule will be applicable. This will be useful if creating Pricing Rule for sales promotion exercise available for certain days.

![Pricing Rule Validity]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-04-09 at 1.36.29 pm.png)

####Disable

Check Disable to inactive specific Pricing Rule.

![Pricing Rule Disabled]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-04-09 at 1.37.38 pm.png)

<!-- markdown -->