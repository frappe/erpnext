# Laboratory

If you wish to use features of Laboratory, you can create Users with "Laboratory User". Lab Tests, Sample Collection etc. are only visible to users with this Role enabled.

### Laboratory Settings
> Healthcare > Setup > Healthcare Settings > Laboratory Settings

* Manage Sample Collection - If this flag is enabled, every time you create a Lab Test, a Sample Collection document will be created.

* Require Lab Test Approval - Turning this on will restrict printing and emailing of Lab Tests only if the documents are in Approved status. You can use this flag to ensure that every Test result leaves your facility after verification.

* Enable the third option if you want the name and designation of the Employee associated with the User who submits the document to be printed in the Lab Test Report.

##### SMS Alerts
You can configure ERPNext Healthcare to alert Patients via SMS when the Lab Test result gets ready (Submit) and when you Email the result. You an configure the templates for the SMS as registered with your provider here.
> Healthcare > Setup > Healthcare Settings > Laboratory SMS Alerts


### Lab Test Templates
Whenever you create a new Lab Test, the Lab Test document is loaded based on the template configured for that particular test. This means, you will have to have separate templates configured for each Lab Test.

Here's how you can configure various types of templates.
> Healthcare > Setup > Lab Test Template > New Lab Test Template

After providing the Name for the Test you will have to select a Code and Item group for creating the mapped Item. ERPNext Healthcare maps every Lab Test (every other billable healthcare service) to an Item with "Maintain Stock" set to false. This way, the Accounts Module will invoice the Item and you can see the Sales related reports of Selling Module. You can also set selling rate of the Lab Test here - this will update the Selling Price List.

> The Standard Selling Rate field behaves similar to the Item Standard Selling Rate, updating this will not update the Selling Price List

The Is Billable flag in Lab Test Template creates the Item, but as Disabled. Likewise, unchecking this flag will Enable the Item.

###### Result Format
Following are the result formats available in ERPNext Healthcare

* Single - select this format for results which require only a single input, result UOM and normal value
* Compound - allows you to configure results which require multiple input fields with corresponding event names, result UOMs and normal values
* Descriptive - this format is helpful for results which have multiple result components and corresponding result entry fields.
* Grouped - You can group test templates which are already configured and combine as a single test. For such templates select "Grouped".
* No Result - Select this if you don not need to enter or manage test result. Also, no Lab Test document will be created. e.g., Sub Tests for Grouped results.

###### Normal values
For Single and Compound result formats, you can set the normal values.

###### Sample
You will have to select the Sample required for the test. You can also mention the quantity of sample that needs to be collected. These details will be used when creating the Sample Collection document for the Lab Test.

### Medical Department
To organize your clinic into departments, you can create multiple Medical Departments. You can select appropriate departments in Lab Test Template and will be included in the Lab Test result print.
> Healthcare > Setup > Medical Department > New Medical Department

### Lab Test Sample
You can create various masters for Samples that are to be collected for a Lab Test.
> Healthcare > Setup > Lab Test Sample > New Lab Test Sample


### Lab Test UOM
You can create various masters for Unit of Measures to be used in Lab Test document.
> Healthcare > Setup > Lab Test UOM > New Lab Test UOM

### Antibiotic
You can create masters for a list of Antibiotics.
> Healthcare > Setup > Antibiotic > New Antibiotic

### Sensitivity
You can create masters for a list of Sensitivity to various Antibiotics.
> Healthcare > Setup > Sensitivity > New Sensitivity

{next}
