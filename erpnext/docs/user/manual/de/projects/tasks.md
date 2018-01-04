# Aufgaben
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Ein Projekt wird in Aufgaben unterteilt. In ERPNext können Sie auch Abhängigkeiten zwischen Aufgaben erstellen.

<img class="screenshot" alt="Aufgabe" src="/docs/assets/img/project/task.png">

### Status der Aufgabe

Ein Aufgabe kann folgende Stati haben: "Offen", "In Arbeit", "Wartet auf Überprüfung", "Geschlossen" und "Abgebrochen".

<img class="screenshot" alt="Aufgabe - Status" src="/docs/assets/img/project/task_status.png">

* Standardmäßig sollte jede neu erstellte Aufgabe den Status "Offen" haben.
* Wenn ein Zeitprotokoll für eine Aufgabe erstellt wird, sollte ihr Status "In Arbeit" sein.

### Abhängige Aufgaben

Sie können eine Liste von abhängigen Aufgaben im Bereich "Hängt ab von" erstellen.

<img class="screenshot" alt="Anhängigkeiten" src="/docs/assets/img/project/task_depends_on.png">

* Sie können eine übergeordnete Aufgabe nicht abschliessen bis alle abhängigen Aufgaben abgeschlossen sind.
* Wenn sich die abhängige Aufgabe verzögert und sich mit dem voraussichtlichen Startdatum der übergeordneten Aufgabe überlappt, überarbeitet das System die übergeordnete Aufgabe.

### Zeitmanagement

ERPNext verwendet [Zeitprotokolle](/docs/user/manual/de/projects/time-log.html) um den Fortschritt einer Aufgabe mitzuprotokollieren. Sie können mehrere unterschiedliche Zeitprotokolle zu jeder Aufgabe erstellen. Das aktuelle Start- und Enddatum kann dann zusammen mit der auf dem Zeitprotokoll basierenden Kostenberechnung aktualisiert werden.

* Um ein zu einer Aufgabe erstelltes Zeitprotokoll anzuschauen, klicken Sie auf "Zeitprotokolle".

<img class="screenshot" alt="Aufgabe - Zeitprotokoll ansehen" src="/docs/assets/img/project/task_view_time_log.png">

<img class="screenshot" alt="Aufgabe - Liste der Zeitprotokolle" src="/docs/assets/img/project/task_time_log_list.png">

* Sie können ein Zeitprotokoll auch direkt erstellen und mit einer Aufgabe verknüpfen.

<img class="screenshot" alt="Aufgabe - Zeitprotokoll verknüpfen" src="/docs/assets/img/project/task_time_log_link.png">

### Ausgabenmanagement

Sie können [Aufwandsabrechnungen](/docs/user/manual/de/human-resources/expense-claim.html) mit einer Aufgabe verbuchen. Das System aktualisiert den Gesamtbetrag der Aufwandsabrechnungen im Abschnitt Kostenberechnung.

* Um eine Aufwandsabrechnung, die zu einer Aufgabe erstellt wurde, anzuschauen, klicken Sie auf "Aufwandsabrechnung".

<img class="screenshot" alt="Aufgabe - Aufwandsabrechnung ansehen" src="/docs/assets/img/project/task_view_expense_claim.png">

* Sie können eine Aufwandsabrechnung auch direkt erstellen und sie mit einer Aufgabe verknüpfen.

<img class="screenshot" alt="Aufgabe - Aufwandsabrechnung verknüpfen" src="/docs/assets/img/project/task_expense_claim_link.png">

* Der Gesamtbetrag der Aufwandsabrechnungen zu einer Aufgabe wird unter "Gesamtbetrag der Aufwandsabrechnungen" im Abschnitt Kostenabrechnung angezeigt.

<img class="screenshot" alt="Aufgabe - Gesamtsumme Aufwandsabrechnung" src="/docs/assets/img/project/task_total_expense_claim.png">

{next}

