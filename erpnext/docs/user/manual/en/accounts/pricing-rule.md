#Pricing Rule

Pricing Rule is a master where you can define rules based on which discount is applied to specific Customer or Supplier.
### Scenario:

Following are the few cases which can be addressed using Pricing Rule.

1. As per the promotional sale policy, if customer purchases more than 10 units of an item, he enjoys 20% discount. 

2. For Customer "XYZ", selling price for the specific Item should be updated as ###.

3. Items categorized under specific Item Group has same selling or buying price.

4. Customers balonging to specific Customer Group should get ### selling price, ot % of Discount on Items.

5. Supplier's categorized under specific Supplier Type should have ### buying rate applied.

To have %Discount and Price List Rate for an Item auto-applied, you should create Pricing Rules for it.

Pricing Rule master has two sections:

### 1. Applicability Section:

In this section, conditions are set for the application of Pricing Rule. When transaction meets condition as specified in this section, Price or Discount as specified in the Pricing Rule will be applied. You can set condition on following values.

####1.1 Applicable On:

<img alt="Applicable On" class="screenshot" src="{{docs_base_url}}/assets/img/articles/pricing-rule-on.png">

If you want Pricing Rule to be applied on all the items, select based on Item Group. For value, select **All Item Group** (parent Item Group).

####1.2 Applicable For:

Applicability option will updated based on our selection for Selling or Buying or both. You can set applicability on one of the following master.

<img alt="Applicable for" class="screenshot" src="{{docs_base_url}}/assets/img/articles/pricing-rule-for.png">

####1.3 Quantity:

Specify minimum and maximum qty of an item when this Pricing Rule should be applicable.

<img alt="Applicable Qty" class="screenshot" src="{{docs_base_url}}/assets/img/articles/pricing-rule-qty.png">

###2. Application:

Using Price List Rule, you can ultimately define price or %discount to be applied on an item.

<img alt="Applicable" class="screenshot" src="{{docs_base_url}}/assets/img/articles/pricing-rule-application.png">

####2.1 Price

Price or Discount specified in the Pricing Rule will be applied only if above applicability rules are matched with values in the transaction. Price mentioned in Pricing Rule will be given priority over item's Price List rate.

<img alt="Applicable Price" class="screenshot" src="{{docs_base_url}}/assets/img/articles/pricing-rule-price.png">

#### 2.2 Discount Percentage

Discount Percentage can be applied for a specific Price List. To have it applied for all the Price List, %Discount field should be left blank.

<img alt="Discount" class="screenshot" src="{{docs_base_url}}/assets/img/articles/pricing-rule-discount.png">

If %Discount is to be applied on all Price Lists, then leave Price List field blank.

#### Validity

Enter From and To date between which this Pricing Rule will be applicable. This will be useful if creating Pricing Rule for sales promotion exercise available for certain days.

<img alt="Validity" class="screenshot" src="{{docs_base_url}}/assets/img/articles/pricing-rule-validity.png">

#### Priority

If two or more Pricing Rules are found based on same conditions, Priority is applied. Priority is a number between 0 to 20 while default value is zero (blank). Higher number means it will take precedence if there are multiple Pricing Rules with same conditions.

<img alt="Priority" class="screenshot" src="{{docs_base_url}}/assets/img/articles/pricing-rule-priority.png">

#### Disable

Check to Disable Pricing Rule.

<img alt="Disable" class="screenshot" src="{{docs_base_url}}/assets/img/articles/pricing-rule-disable.png">

### Add Margin

Using pricing rule user can add margin on the sales transactions

For example :  User want to add 10% margin on the supplier price list at the time of sales

####1. Make Price List

Create price list for supllier and create item price against the price list.

<img alt="Disable" class="screenshot" src="{{docs_base_url}}/assets/img/articles/price-list.png">


####2. Make Pricing Rule 

Create pricing rule for the item against which supplier rate has created

<img alt="Disable" class="screenshot" src="{{docs_base_url}}/assets/img/articles/pricing-rule-margin.png">

####2. Make Invoice

System apply the margin rate on the item price on selection of an item.

<img alt="Disable" class="screenshot" src="{{docs_base_url}}/assets/img/articles/pricing-rule-invoice.png">

For more details about pricing rule [Click Here]({{docs_base_url}}/user/manual/en/selling/articles/adding-margin.html)

<!-- markdown -->