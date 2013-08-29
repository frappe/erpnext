---
{
	"_label": "Material Request"
}
---
A Material Request is a simple document identifying a requirement of a set of Items (products or services) for a particular reason.


![Workflow](img/material-request-workflow.jpg)




To generate a Material Request manually go to:

> Buying > Material Request > New Material Request

**Step 1**

![Material Request](img/material-request-1.png)




A Material Request can be generated:

- By a User.
- Automatically from a Sales Order.
- Automatically when the Projected Quantity of an Item in stores reaches a particular level.
- Automatically from your Bill of Materials if you use Production Plan to plan your manufacturing activities.

**Step 2**

![Material Request 2](img/material-request-2.png)




In the Material Request form, 

- Fill in the Items you want and their quantities.

- If your Items are inventory items, you must also mention the Warehouse where you expect these Items to be delivered. This helps to keep track of the Projected Quantity for this Item. Projected Quantity is the level of stock that is predicted for a particular Item, based on the current stock levels and other requirements.It is the quantity of gross inventory, including supply and demand in the past that is done as part of the planning process. The projected inventory is used by the planning system to monitor the reorder point and to determine the reorder quantity. The projected Quantity is used by the planning engine to monitor the safety stock levels. These levels are maintained to serve unexpected demands. Having a tight control of the projected inventory is crucial to detect when the reorder point is being crossed and to calculate the right order quantity.


- You can optionally add the Terms, using the Terms and Conditions master and also the reason.


> Info: Material Request is not mandatory. It is ideal if you have centralized buying so that you can collect this information from various departments.

#### Authorization

If you want your Material Request to be authorized by a senior person like a Purchase Manager then you can give “Submit” rights only to that person. Everyone can create requests, but only the authorized person can “Submit”.