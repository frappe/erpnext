---
{
	"_label": "Manufacturing",
	"_toc": [
		"docs.user.mfg.bom",
		"docs.user.mfg.planning",
		"docs.user.mfg.production_order"
	]
}
---
The Manufacturing module in ERPNext helps you to maintain multi-level Bill of Materials (BOMs) for your Items. It helps you in Product Costing, planing your production via Production Plan, creating Production Orders for your manufacturing shop floors and planing your inventory by getting your material requirement via BOMs (also called Material Requirements Planning MRP).

### Types of Production Planning

Broadly there are three types of Production Planning Systems

- Make-to-Stock: In these systems, production is planned based on a forecast and the Items are then sold to distributors or customers. All fast moving consumer goods that are sold in retail shops like soaps, packaged water etc and electronics like phones etc are Made to Stock.
- Make-to-Order: In these systems, manufacturing takes place after a firm order is placed by a Customer.
- Engineer-to-Order:  In this case each sale is a separate Project and has to be designed and engineered to the requirements of the Customer. Common examples of this are any custom business like furniture, machine tools, speciality devices, metal fabrication etc.

Most small and medium sized manufacturing businesses are based on a make-to-order or engineer-to-order system and so is ERPNext.

For engineer-to-order systems, the Manufacturing module should be used along with the Projects module.

#### Manufacturing and Inventory
￼
You can track work-in-progress by creating work-in-progress Warehouses. 

ERPNext will help you track material movement by automatically creating Stock Entries from your Production Orders by building from Bill of Materials.


---

### Material Requirements Planning (MRP):

The earliest ERP systems were made for manufacturing. The earliest adopters were automobile companies who had thousands of raw materials and sub-assemblies and found it very hard to keep track of requirements and plan purchases. They started using computers to build the material requirements from forecasts and Bill of Materials. 

Later these systems were expanded to include Finances, Payroll, Order Processing, and Purchasing and thus became the more generic Enterprise Resource Systems (ERP). More recently Customer Relationship Management (CRM) was added as a function and is now an integral part of ERP systems.

These days the term ERP is used to describe systems that help manage any kind of organization like education institutes (Education ERP) or Hospitals (Hospital ERP) and so on. 

---

### Best Practice: Lean Manufacturing

The state of art manufacturing philosophy (the rationale behind the planning processes) comes from Japanese auto major Toyota. At the time when American manufacturers depended on MRP systems to plan their manufacturing based on their sales forecasts, they turned around the problem by discovering a leaner way of planning their production. They realized that:

The biggest cause of wastage in manufacturing is variation (in product and quantity).

So they standardized their products and sub-assemblies and sold fixed quantities based on what they produced or did not produce based on what they sold. This way, they had an extremely predictable and stable product mix. If they sold less than planned, they would simply stop production. 

Their card signaling system kanban, would notify all their suppliers to stop production too. Hence they never used any of the complex material planning tools like MRP to play day-to-day material requirements, but a simple signaling system that said either STOP or GO.

They combined this system with neatly managed factories with well labeled racks.

Small manufacturing companies are usually make-to-order or engineer-to-order and can hardly afford to have a high level of standardization. Thus small manufacturing businesses should aim for repeatability by innovating processes and creating a common platform for products.