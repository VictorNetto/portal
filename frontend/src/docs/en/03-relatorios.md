<!-- page: relatorios -->
# Reports

A report brings together the outcome of a whole operation: who did it, when, with what scope, an executive summary for those who decide, the story of the work for those who want to understand it, the vulnerabilities found and the evidence. It is what the team responsible receives at the end of a pentest, delivered all at once, as a unit.

While it is a draft, a report is a closed workspace. The vulnerabilities inside it have no life of their own: they are written, reviewed and sent together with the report. Only after sending do they follow a vulnerability's normal lifecycle, appear to the defense team and get fixed one by one.

This chapter shows how to create a report and reserve it for editing, what goes into each part of it and what happens when it is sent.

<!-- page: rel-criar -->
# Creating and reserving a report

To start a report, open **Reports** in the menu and choose **Create Report**. You can start from scratch or pick a **template**, which already brings the executive summary, the introduction and the additional sections with text ready to adjust. The report copies the template's text when it is created, and the [Templates](#templates) chapter explains how they work.

## The reservation

A report is a long document written by several people, and two of them editing at once would end up undoing each other's work. So to edit a report you first **reserve** it, with the **Edit** button. While the reservation is yours, nobody else changes the report or the vulnerabilities inside it, and whoever opens the report sees who is editing.

The reservation is released when you leave editing, or by itself after **10 minutes** without activity, so a report isn't stuck just because someone closed the window. If you need to edit and the reservation is held by someone else, talk to them; as a last resort, an administrator can release the reservation.

<!-- page: rel-conteudo -->
# What a report contains

A report is organised in parts, from top to bottom of the page, in the same order they appear in the delivered document.

**General Information** and **Report Data** describe the operation: the name, the client, the dates, the type and model of the test, the environment, where the request came from and the scope. Then come the texts: the **Executive Summary**, for those who need the conclusion without the technical detail, and the **Introduction**, which sets the scene. If the report needs more text, such as a methodology or a list of limitations, **Additional Sections** let you create as many as needed, each with its own title and in the order you want.

After the texts come the operation's **vulnerabilities**, the **evidence** for the report as a whole and the **internal notes**, which, as with vulnerabilities, never leave the portal.

Outside editing, the page shows the content as it appears in the document. While editing, each part becomes a form.

## The report's vulnerabilities

While editing, the *Vulnerabilities* part has three actions. **Add vulnerability** creates a new one, already inside the report. **Link** brings into the report standalone vulnerabilities that haven't been sent yet: a *Ready* vulnerability goes back to *Draft* when it joins, keeping its internal ID, and is then edited and sent with the report. **Unlink** does the opposite: the vulnerability leaves the report and becomes standalone again, as a draft.

## What goes into the document

Not everything in the portal has to go into the document. Next to each section's title is the **In document** option, which says whether it goes into the generated files: **Export** (PDF, Word and Excel), the batch export and the sent report. An unticked section stays in the portal but is left out of the documents; in Excel, its cell is left empty.

The option exists on Report Data, the Executive Summary, the Introduction and each additional section, and also, on vulnerabilities, on the Description, the Finding Details, the Mitigation / Solution and the References. The choice is saved at once, without reserving or saving the report, and can be changed at any time, also after sending, by anyone who can change the record. Internal notes never go into any document.

<!-- page: rel-envio -->
# Sending, progress and deletion

A report has only two statuses: **Draft**, while it is being written, and **Sent**. Sending is when everything closes at once. **Send** gives the report its internal ID (`OP-xxxx`), assigns internal IDs to the vulnerabilities that don't have one yet, generates the documents and delivers them. The vulnerabilities become *Sent* and from then on follow the normal lifecycle, each at its own pace.

## When sending fails

Sending happens in two steps: first the portal freezes the report, then it generates and delivers the documents. If delivery fails, for example because the email server didn't answer, the report isn't left half-sent. It stays a *Draft*, locked for editing, with the notice **Sending failed**, and the **Retry** button repeats the delivery with the same content.

## Progress

After sending, the portal follows the fixing of the report's vulnerabilities and shows the progress, such as *2 of 5 fixed*. When all of them are fixed, or have had their risk accepted by the defense team, the report shows as **Completed**. Nobody needs to mark this: the portal works it out from each vulnerability's status.

## Deleting

Only a draft report can be deleted. Once sent, it is part of the record of what was delivered and stays in the portal.
