# Clinic / Practice
Configuring ERPNext Healthcare for your practice is simple.
> Healthcare > Setup > Healthcare Settings > Out Patient Settings

By default Patient document uses the patient name as the name, but you can opt to use a naming series if required.

The "Manage Customer" option will enable the system to create and link a Customer whenever a new Patient is created. This Customer is used while booking all transactions.

Here, you can also select the default Medical Code Standard to use.

###### Collect Fee for Patient Registration
If you enable this, all new Patients you create will by default be in Disabled mode and will be enabled only after Invoicing the Registration Fee. To create Invoice and record the payment receipt, you can use the "Invoice Patient Registration" button in the Patient document. Also note that all ERPNext Healthcare documents, "Disabled" Patients are filtered out. You can set the registration fee to be collected here.

###### Consultation Fee validity
Many healthcare facilities do not charge for follow up consultations within a time period after the first visit. You can configure the number of free visits allowed as well as the time period for free consultations here.

### Medical Department
To organize your clinic into departments, you can create multiple Medical Departments.
> Healthcare > Setup > Medical Department > New Medical Department

### Appointment Type
You can create masters for various type of Appointments. This is optional and not considered while appointment scheduling.
> Healthcare > Setup > Appointment Type > New Appointment Type

### Prescription Dosage & Duration
You can configure different dosages to be used while prescribing medication to patients. You can name the Prescription dosage in anyway you want (for example, BID or I-0-I), and then set the strength of the drug and the times at which it should be administered.
> Healthcare > Setup > Prescription Dosage > New Prescription Dosage

> Healthcare > Setup > Prescription Duration > New Prescription Duration

### Complaint and Diagnosis
To ease the data entry while recording the encounter impression, ERPNext Healthcare allows you to save each of the Complaint / Diagnosis data you enter, from the Consultation screen itself. This way, the database keeps building a list of all complaints and diagnosis you entered. Later on, every time you start keying in, you will be able to select the previously entered word / sentence from the search field. You can also configure the masters manually.

> Healthcare > Setup > Complaints > New Complaint

> Healthcare > Setup > Diagnosis > New Diagnosis

{next}
