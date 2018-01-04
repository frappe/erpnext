# Kunde
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Ein Kunde, manchmal auch als Auftraggeber, Käufer oder Besteller bezeichnet, ist diejenige Person, die von einem Verkäufer für eine monetäre Gegenleistung Waren, Dienstleistungen, Produkte oder Ideen bekommt. Ein Kunde kann von einem Hersteller oder Lieferanten auch aufgrund einer anderen (nicht monetären) Vergütung waren oder Dienstleistungen erhalten.

Sie können Ihre Kunden entweder direkt erstellen über

> CRM > Dokumente > Kunde > Neu

<img class="screenshot" alt="Kunde" src="/docs/assets/img/crm/create-customer.gif">

oder einen Upload über ein Datenimportwerkzeug durchführen.

> Anmerkung: Kunden werden von Kontakten und Adressen getrennt verwaltet. Ein Kunde kann mehrere verschiedene Kontakte und Adressen haben.

### Kontakte und Adressen

Kontakte und Adressen werden in ERPNext getrennt gespeichert, damit Sie mehrere verschiedene Kontakte oder Adressen mit Kunden und Lieferanten verknüpfen können.

Lesen Sie hierzu auch [Kontakt](/docs/user/manual/de/CRM/contact.html).

### Einbindung in Konten

In ERPNext gibt es für jeden Kunden und für jede Firma einen eigenen Kontodatensatz.

Wenn Sie einen neuen Kunden anlegen, erstellt ERPNext automatisch im Kundendatensatz unter den Forderungskonten der Firma ein Kontenblatt für den Kunden.

> Hinweis für Fortgeschrittene: Wenn Sie die Kontengruppe, unter der das Kundenkonto erstellt wurde, ändern wollen, können Sie das in den Firmenstammdaten einstellen.

Wenn Sie in einer anderen Firma ein Konto erstellen wollen, ändern Sie einfach die Einstellung der Firma und speichern Sie den Kunden erneut.

### Kundeneinstellungen

Sie können eine Preisliste mit einem Kunden verknüpfen (wählen Sie hierzu "Standardpreisliste"), so dass die Preisliste automatisch aufgerufen wird, wenn Sie den Kunden auswählen.

Sie können die Zieltage so einstellen, dass diese Einstellung automatisch in Ausgangsrechnungen an diesen Kunden verwendet wird. Zieltage können als festeingestellte Tage definiert werden oder als letzter Tag des nächsten Monats  basierend auf dem Rechnungsdatum.

Sie können einstellen, wieviel Ziel Sie für einen Kunden durch hinzufügen der "Kreditlinie" erlauben wollen. Sie können auch ein allgemeines Ziel-Limit in den Unternehmensstammdaten einstellen. 

### Kundenklassifizierung

ERPNext erlaubt es Ihnen Ihre Kunden in Kundengruppen zu gruppieren und sie in Regionen aufzuteilen. Das Gruppieren hilft Ihnen bei der genaueren Auswertung Ihrer Daten und bei der Identifizierung welche Kunden gewinnbringend sind und welche nicht. Die Regionalisierung hilft Ihnen dabei, Ziele für genau diese Regionen festzulegen. Sie können auch Vertriebspersonen als Ansprechpartner für einen Kunden festlegen.

### Vertriebspartner

Ein Vertriebspartner ist ein Drittparteien-Großhändler, -händler, -kommissionär, -partner oder -wiederverkäufer, der die Produkte des Unternehmens für eine Provision verkauft. Diese Option ist dann sinnvoll, wenn Sie unter Zuhilfenahme eines Vertriebspartners an den Endkunden verkaufen.

Wenn Sie an Ihren Vertriebspartner verkaufen, und dieser dann wiederum an den Endkunden, müssen Sie für den Vertriebspartner einen Kunden erstellen.

{next}
