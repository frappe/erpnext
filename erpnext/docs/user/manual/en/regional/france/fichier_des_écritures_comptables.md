# Le Fichier des Écritures Comptables [FEC]

Since 2014, a legal requirement makes it mandatory for companies operating in France to provide a file of their general accounting postings by fiscal year corresponding to an electronic accounting journal.

For ERPNext users this file can be generated using a report available if you system's country is France.


### Requirements

To generate the report correctly, your Chart of Account needs to be setup according to the french accounting rules.

All accounts need to have a number in line with the General Chart of Account (PCG) and a name.

The SIREN number of your company can be added in the "Company" doctype.


### CSV generation

You can generate the required CSV file by clicking on "Export" in the top right corner of the report.


### Testing Instructions

To test the validity of your file, the tax administration provides a testing tool at the following address: [Outil de test des fichiers des écritures comptables (FEC)](http://www.economie.gouv.fr/dgfip/outil-test-des-fichiers-des-ecritures-comptables-fec)
