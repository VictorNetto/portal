<!-- page: vulnerabilidades -->
# Vulnerabilities

A vulnerability is the record of a finding: a flaw found in a system, with a description of the problem, the details of how it was found, how to fix it and the evidence. It is the portal's basic unit. It can stand alone, as a standalone finding, or sit inside a report, together with the other vulnerabilities of an operation.

A vulnerability goes through several stages, from the draft you start writing to the fix confirmed by a retest, and the portal keeps the date of each one. This chapter follows that path: how to create and write a vulnerability, which statuses it goes through, what happens after it is sent, and how the portal deals with two people editing the same vulnerability.

## The three identifications of a record

Before starting, it is worth knowing the three identifications that appear on screen, because they show up at different moments.

The **identifier** is the name you give the finding, such as *SQL injection in the Customer Portal*. It is what lists and titles show, and you can change it while the content is open for editing.

The **internal ID** is the number the portal assigns, such as `VULN-0012`, or `OP-0003` for a report. A standalone vulnerability gets it when it is completed; a report and the vulnerabilities inside it, when the report is sent. Before that the record has no number, and afterwards the number never changes. The internal ID is what identifies the finding in any conversation with other teams.

The **RVS ID** is the number the defense team gives when it accepts to fix the vulnerability. It only exists on vulnerabilities, only after sending, and it doesn't change once recorded either.

<!-- page: vuln-criar -->
# Creating a vulnerability

To record a finding, open the menu and choose **Create Vulnerability**. The form that appears is the same one you will later use to edit it, and nothing has to be complete now: you can save a draft with just the identifier and come back to it as often as you like. Only to **complete** the vulnerability do three fields become required: the **Identifier**, the **Description** and the **Finding Details**. **Mitigation / Solution** may stay blank, for cases where the fix is up to the people who know the system.

## Who works on the finding

You start as the vulnerability's operator. If other people worked on the finding, add them with the **+** button next to **Operators**; to remove someone, click their name. Next to it, **Shared with** works the same way, but for people who should only follow the record, such as a Restricted reader who needs to see that finding.

## The CVSS score

Severity follows CVSS v3.1. If you already have the score and the vector, type them into the fields. If not, click **Calculator**, next to the *CVSS vector* field. It shows the eight base metrics (attack vector, complexity, privileges, user interaction, scope and the three impacts) and computes the score, the severity and the vector exactly as FIRST's official calculator does. **Apply** fills in both fields. If the vulnerability already has a vector, the calculator opens with it, which makes it easy to adjust one metric without redoing the others.

## The creation date

The **Creation date** starts as today, and nearly always that's right. Sometimes, though, a finding is recorded days after it was found, and then it is worth correcting the date, because the vulnerability's timeline and the dashboards' durations count from it. Future dates aren't accepted. The date can only be changed while the content is open for editing, that is, in draft or ready, and even then it can't be later than the day the vulnerability was completed.

## What may appear at the top

Next to the status, at the top of the page, two notes may appear. **Batch `BATCH-0001`** means the vulnerability is part of a batch, usually created by a tool that recorded several findings at once through the API. Clicking the batch shows, in Operations, every vulnerability that came with it. **Imported on …** means it came from another system together with its history (status, dates, number and RVS ID), and that the dates in its timeline are from there, not from work done in the portal.

<!-- page: textos -->
# Text, images and attachments

The long text fields, such as Description and Finding Details, use **Markdown**, a simple way to format text with a few symbols: `**bold**`, `*italic*`, `# heading`, lists starting with `-`, and so on. You don't need to memorise any of it, because the editor's toolbar has buttons for bold, italic, heading, lists, code, link and quote. **Preview** shows the text as it will appear.

When you need room, **Expand** makes the editor as tall as the window; **Collapse**, or the *Esc* key, brings it back to its normal size.

## Images

A screenshot is often the best evidence, so the editor takes images directly: paste an image, drag a file into the text or pick one with the image button. The portal asks for a name, stores the file as evidence and inserts the image where you were in the text. In exported documents, it appears in the same place.

## Attachments

For evidence that doesn't fit in the text, such as a log or a file of requests, use the **Attachments** area. Each file may be up to 50 MB, in PDF, PNG, JPG, GIF, WebP, TXT, CSV or ZIP format. The portal checks the type from the file's content, not just its extension; an executable renamed to `.png` is refused.

## Internal notes

The **Internal notes** field is for what matters only to the team: hypotheses, loose ends, the context of the operation. It never leaves the portal, not in exports, not in delivered reports, not through the API. That is why, together with the operators, it stays editable after sending.

<!-- page: vuln-ciclo -->
# The lifecycle

Every vulnerability has a **status**, which says where it is on its path and who should act next. The normal path has six stages, nearly always taken in order.

A vulnerability starts as a **Draft**. At this stage it can be saved as often as needed with **Save draft**, even when incomplete. Once the finding is described, **Complete** checks the required fields and assigns the internal ID `VULN-xxxx`, and the vulnerability becomes **Ready**.

A **Ready** vulnerability is complete but hasn't left the Red Team yet. It stays editable, for a final review. When everything is right, **Send** delivers it to the team responsible.

Once sent, the vulnerability is **Sent** and its content closes for editing: what was delivered no longer changes. Now it is the defense team's turn, and it has two paths. The usual one is to **accept** the vulnerability and record the RVS ID opened to fix it, which takes it to **Fixing**. The other is to **accept the risk** of not fixing it, with a reason, which ends the path with the status **Risk accepted**. The reason appears in the timeline, and the defense team can undo that decision later, which returns the vulnerability to *Sent*.

While **Fixing**, the team responsible works on the problem. When it is done, the defense team asks for verification with **Request retest**; the Red Team can make that request too. If a retest isn't needed, the defense team can use **Mark as fixed**, which takes the vulnerability straight to the end.

While **Retesting**, the Red Team checks whether the fix works. If it does, **Pass retest** takes the vulnerability to **Fixed**, the end of the path. If not, **Fail retest** sends it back to *Fixing*, and the cycle repeats until the fix passes.

The timeline, at the top of each vulnerability's page, shows when each of these stages happened.

<!-- page: vuln-apos -->
# After sending: the RVS ID and corrections

Sending is a point of no return for the content. From then on, what was delivered stays as it was delivered, and only the **operators** and the **internal notes** remain editable, because they concern the team's work and not what the other team received.

## The RVS ID

The RVS ID is the number the defense team uses to follow the fix in its own systems. The defense team records it itself, with a Defense account in the portal: it accepts the sent vulnerability and enters the ID, and the vulnerability moves to *Fixing*. Each ID belongs to a single vulnerability and doesn't change once recorded.

On the Red Team's side, nothing needs to be done for this to happen, but you can follow along. Each vulnerability's timeline shows the RVS ID as soon as it is recorded, or the reason, if the defense team accepted the risk. To see everything still waiting for the defense team, filter Operations by `status:sent`; `status:sent -sent:15d` shows the ones waiting for more than fifteen days.

## When something goes wrong

Sometimes a status changes by mistake, or an RVS ID is recorded on the wrong vulnerability. In those cases, an administrator can use **Adjust status** to return the vulnerability to an earlier stage, giving the reason, and the adjustment is kept in the audit logs. For a wrong RVS ID, the administrator returns the vulnerability to *Sent*, and the defense team records the right ID.

<!-- page: vuln-conflitos -->
# Simultaneous edits

In a team, it is natural for two people to open the same vulnerability at the same time. The portal doesn't prevent that, but it does prevent one from erasing the other's work without noticing.

Each vulnerability keeps a version, which goes up with every saved change. When you save, the portal checks whether the version you opened is still the current one. If someone saved in the meantime, your save is refused with a notice, and the page shows the latest version. Nothing the other person wrote is overwritten: you look at what changed and redo your change on top of the new version.

The same applies to changes that come from outside. If a tool changes the vulnerability through the API while you are editing it, you will see the notice when you save.

Reports work differently, with a reservation that prevents simultaneous editing from the start. The next chapter explains how.
