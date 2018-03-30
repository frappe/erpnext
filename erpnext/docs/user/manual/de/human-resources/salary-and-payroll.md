# Gehalt und Gehaltsabrechung
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Ein Gehalt ist ein fester Geldbetrag oder eine Ersatzvergütung die vom Arbeitsgeber für die Arbeitsleistung des Arbeitnehmers an diesen gezahlt wird.

Die Gehaltsabrechnung ist der zugrundeliegende Datensatz zum Verwaltungsakt von Gehältern, Löhnen, Boni, Nettoauszahlungen und Abzügen für einen Mitarbeiter.

Um in ERPNext eine Gehaltsabrechnung durchzuführen

1. Erstellen Sie Gehaltsstrukturen für alle Arbeitnehmer.
2. Erstellen Sie über den Prozess Gehaltsabrechnung Gehaltsabrechnungen.
3. Buchen Sie das Gehalt in Ihren Konten.

### Gehaltsstruktur

Die Gehaltsstruktur gibt an, wie Gehälter auf Basis von Einkommen und Abzügen errechnet werden.

Gehaltsstrukturen werden verwendet um Organisationen zu helfen

1. Gehaltslevel zu erhalten, die am Markt wettbewerbsfähig sind.
2. Ein ausgeglichenes Verhältnis zwischen den Entlohnungen intern anfallender Jobs zu erreichen.
3. Unterschiede in den Ebenen von Verwantwortung, Begabungen und Leistungen zu erkennen und entsprechend zu vergüten und Gehaltserhöhungen zu verwalten.

Eine Gehaltsstruktur kann folgende Komponenten enthalten:

* **Basisgehalt:** Das ist das steuerbare Basiseinkommen.
* **Spezielle Zulagen:** Normalerweise kleiner als das Basiseinkommen
* **Urlaubsgeld:** Betrag den der Arbeitgeber dem Arbeitnehmer für einen Urlaub zahlt
* **Abfindung:** Bestimmter Betrag, der dem Arbeitnehmer vom Arbeitgeber gezahlt wird, wenn der Mitarbeiter das Unternehmen verlässt oder in Rente geht.
* **Rentenversicherung:** Betrag für zukünftige Rentenzahlungen und andere Leistunge, die unter die Rentenversicherung fallen.
* **Krankenversicherung**
* **Pflegeversicherung**
* **Arbeitslosenversicherung**
* **Solidaritätszuschlag**
* **Steuern**
* **Boni**: Steuerbare Beträge, die dem Arbeitnehmer aufgrund guter individueller Leistungen gezahlt werden.
* **Mietzulage**
* **Aktienoptionen für Mitarbeiter**

Um eine neue Gehaltsstruktur zu erstellen, gehen Sie zu:

> Personalwesen > Einstellungen > Gehaltsstruktur > Neu

#### Abbildung 1: Gehaltsstruktur

<img class="screenshot" alt="Gehaltsstruktur" src="{{docs_base_url}}/assets/img/human-resources/salary-structure.png">

### In der Gehaltsstruktur

* Wählen Sie einen Arbeitnehmer.
* Geben Sie das Startdatum an, ab dem die Gehaltsstruktur gültig ist (Anmerkung: Es kann während eines bestimmten Zeitraums immer nur eine Gehaltsstruktur für einen Arbeitnehmer aktiv sein.)
* In der Tabelle Einkommen und Abzüge werden alle von Ihnen definierten Einkommens- und Abzugsarten automatisch eingetragen. Geben Sie für Einkommen und Abzüge Beträge ein und speichern Sie die Gehaltsstruktur.

### Unbezahlter Urlaub

Unbezahlter Urlaub entsteht dann, wenn ein Mitarbeiter keinen normalen Urlaub mehr hat oder ohne Genehmigung über einen Urlaubsantrag abwesend ist. Wenn Sie möchten, dass ERPNext automatisch unbezahlten Urlaub abzieht, müssen Sie in der Vorlage "Einkommens- und Abzugsart" "Unbezahlten Urlaub anwenden" anklicken. Der Betrag der dem Gehalt gekürzt wird ergibt sich aus dem Verhältnis zwischen den Tagen des unbezahlten Urlaubs und den Gesamtarbeitstagen des Monats (basierend auf der Urlaubstabelle).

Wenn Sie nicht möchten, dass ERPNext unbezahlten Urlaub verwaltet, klicken Sie die Option in keiner Einkommens und Abzugsart an.

* * *

### Gehaltszettel erstellen

Wenn die Gehaltsstruktur einmal angelegt ist, können Sie eine Gehaltsabrechnung aus demselben Formular heraus erstellen, oder Sie können für den Monat eine Gehaltsabrechnung erstellen über den Punkt "Gehaltsabrechnung bearbeiten".

Um eine Gehaltsabrechnung über die Gehaltsstruktur zu erstellen, klicken Sie auf die Schaltfläche "Gehaltsabrechnung erstellen".

#### Abbildung 2: Gehaltsabrechnung

<img class="screenshot" alt="Lohnzettel" src="{{docs_base_url}}/assets/img/human-resources/salary-slip.png">

Sie können auch Gehaltsabrechnungen für mehrere verschiedene Mitarbeiter über "Gehaltsabrechnung bearbeiten" anlegen.

> Personalwesen > Werkzeuge > Gehaltsabrechnung bearbeiten

#### Abbildung 3: Gehaltsabrechnung durchführen

<img class="screenshot" alt="Gehaltsabrechnung durchführen" src="{{docs_base_url}}/assets/img/human-resources/process-payroll.png">

Beim Bearbeiten einer Gehaltsabrechnung

1. Wählen Sie die Firma, für die Sie Gehaltsabrechnungen erstellen wollen.
2. Wählen Sie den ensprechenden Monat und das Jahr.
3. Klicken Sie auf "Gehaltsabrechnung erstellen". Hierdurch werden für jeden aktiven Mitarbeiter für den gewählten Monat Datensätze für die Gehaltsabrechnung angelegt. Wenn die Gehaltsabrechnungen einmal angelegt sind, erstellt das System keine weiteren Gehaltsabrechnungen. Alle Aktualisierungen werden im Bereich "Aktivitätsprotokoll" angezeigt.
4. Wenn alle Gehaltsabrechnungen erstellt wurden, können Sie prüfen, ob Sie richtig sind, und sie bearbeiten, wenn Sie unbezahlten Urlaub abziehen wollen.
5. Wenn Sie das geprüft haben, können Sie sie alle gemeinsam "übertragen" indem Sie auf die Schaltfläche "Gehaltsabrechnung übertragen" klicken. Wenn Sie möchten, dass Sie automatisch per E-Mail an einen Mitarbeiter verschickt werden, stellen Sie sicher, dass Sie die Option "E-Mail absenden" angeklickt haben.

### Gehälter in Konten buchen

Der letzte Schritt ist, die Gehälter mit Ihren Konten zu verbuchen.

Gehälter unterliegen im Geschäftsablauf normalerweise sehr strengen Datenschutzregeln. In den meisten Fällen gibt die Firma eine einzige Zahlung an die Bank, die alle Gehälter beinhaltet, und die Bank verteilt dann die Gehälter an die einzelnen Konten der Mitarbeiter. Bei dieser Vorgehensweise gibt es nur eine einzige Zahlungsbuchung im Hauptbuch der Firma niemand mit Zugriff auf die Konten des Unternehmens hat auf die individuellen Gehaltsdaten Zugriff.

Die Buchung zur Gehaltsabrechnung ist eine Journalbuchung welche das Bankkonto des Unternehmens belastet und den Gesamtbetrag aller Gehälter dem Gehaltskonto gutschreibt.

Um einen Beleg über die Gehaltszahlung aus dem Punkt "Gehaltsabrechnung bearbeiten" heraus zu erstellen, klicken Sie auf "Bankbeleg erstellen" und es wird eine neue Journalbuchung  mit den Gesamtbeträgen der Gehälter erstellt.

{next}
