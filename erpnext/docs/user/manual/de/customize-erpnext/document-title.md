# Dokumentenbezeichnung
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Sie können die Bezeichnung von Dokumenten basierend auf den Einstellungen anpassen, so dass Sie für die Listenansichten eine sinnvolle Bedeutung erhalten.

Beispiel: Die Standardbezeichung eines **Angebotes** ist der Kundenname. Wenn Sie aber Geschäftsbeziehungen mit wenigen Kunden haben, diesen aber sehr viele Angebote erstellen, könnte es sinnvoll sein, die Bezeichnungen anzupassen.

### Bezeichnung von Feldern einstellen

Ab der Version 6.0 von ERPNext haben alle Transaktionen eine Eigenschaft "Bezeichnung". Wenn Sie keine Eigenschaft "Bezeichnung" finden, können Sie ein **benutzerdefiniertes Feld** "Bezeichnung" hinzufügen und dieses über **Formular anpassen** entsprechend gestalten.

Sie können für diese Eigenschaft den Standardwert übernehmen indem Sie in **Standard** oder **Optionen** den Python-Kode einfügen.

Um eine Standard-Bezeichnung einzufügen, gehen Sie zu:

1. Einstellungen > Anpassen > Formular anpassen
2. Wählen Sie Ihre Transaktion aus
3. Bearbeiten Sie das Feld "Standard" in Ihrem Formular

### Bezeichnungen definieren

Sie können eine Bezeichnung definieren, indem Sie Dokumenteneinstellungen in geschweifte Klammern {} setzen. Beispiel: Wenn Ihr Dokument die Eigenschaften customer_name und project hat, können Sie die Standard-Bezeichnung wie folgt setzen:

> {customer_name} for {project}

<img class="screenshot" alt = "Bezeichnung anpassen"
    src="/docs/assets/img/customize/customize-title.gif">

### Fest eingestellte und bearbeitbare Bezeichnungen

Wenn Ihre Bezeichnung als Standard-Bezeichnung generiert wurde, kann sie vom Benutzer durch klicken auf den Kopf des Dokuments bearbeitet werden.

<img class="screenshot" alt = "Bearbeitbare Bezeichnung"
    src="/docs/assets/img/customize/editable-title.gif">

Wenn Sie eine fest eingestellte Bezeichnung haben wollen, können Sie dies als Regel unter **Optionen** einstellen. Auf diese Weise wird die Bezeichnung jedesmal automatisch aktualisiert, wenn das Dokument aktualisiert wird.

{next}
