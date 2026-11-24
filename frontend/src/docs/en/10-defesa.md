<!-- page: defesa -->
# The defense team in the portal

The Red Team finds vulnerabilities, and the defense team decides what to do with them. The portal is where the two meet. Each vulnerability the Red Team sends reaches you, and for each one you say what will happen. Either it will be fixed, and then you **accept** it and record the **RVS ID** opened for the fix, or it won't, and you **accept the risk**, explaining why. From then on, the portal follows the fix until a retest confirms the problem is gone.

## Signing in

The first time, use the temporary password the portal's administrator gave you; the portal asks for a new password before going on. Once you are in, the menu on the left has a section for each stage of the work, explained in [The sections and the vulnerabilities](#def-secoes). The ☰ button at the top shows the sections' names; with the menu closed, hover over an icon. In the top right corner, the button with your user holds the language, this documentation, your profile, the session time and the button to sign out.

## What you see

You only see the vulnerabilities the Red Team has already sent. Drafts, the Red Team's internal notes, the operators' names and the content of reports are left out: what reaches you is what was delivered, with the evidence.

## Confidentiality and record

Vulnerabilities and evidence are **confidential**. Don't copy them to channels outside the organisation's authorised systems.

The portal keeps a record of who did what and when: sign-ins, vulnerabilities and attachments opened, acceptances, RVS IDs recorded, retests requested, vulnerabilities marked as fixed, risks accepted and undone. The Red Team and the auditors consult that record.

<!-- page: def-sessao -->
# The session

A session in the portal ends for one of two reasons: **1 hour** after signing in, or earlier, after **15 minutes without activity**. Your user menu shows both limits, as **Session mm:ss / mm:ss**. Two minutes before the inactivity limit, the portal asks *"Are you still there?"*, and **Stay signed in** starts the count again.

After five failed sign-in attempts within 15 minutes, the account is locked for a few minutes. If you forgot your password, ask the portal's administrator to reset it.

<!-- page: def-secoes -->
# The sections and the vulnerabilities

Each vulnerability sits in a section of the menu, according to the stage it is at, and each section stands for a decision waiting for you, or for none.

**New** holds the vulnerabilities the Red Team sent that nobody on the defense team has accepted yet. That is where the work starts: for each one, you decide between **accepting** it and **accepting the risk**. Accepted ones move to **Awaiting RVS**, where they wait until you record the fix's RVS ID, or accept the risk, if you change your mind. With the RVS ID recorded, the vulnerability goes to **In progress**, where it stays while it is fixed and retested; there, when the fix is ready, you request the retest or mark it as fixed. Those the retest confirmed are in **Fixed**, for reference only. And those the defense team decided not to fix are in **Risk accepted**, from where the decision can be undone.

The lists show, for each vulnerability, the identifier, the state, the CVSS (red from 7, orange from 4 to 6.9), the originating report, when it was received and the RVS ID, fifty vulnerabilities per page. Click a row to open the vulnerability.

## A vulnerability's page

At the top of the page are the title, the state and the **internal ID**, such as `VULN-0042`, which identifies the vulnerability in any conversation with the Red Team. Just below, the **timeline** shows when it was received and each later stage, with the RVS ID or the reason the risk was accepted. Then come the general information (CWE, CVSS, CVSS vector and the originating report), the **Description**, the **Finding details** and the **Mitigation / Solution**, with the evidence images in the text itself, and finally the **References** and the **Attachments**, which you save with **Download**.

The action buttons are in the top right corner and change with the stage. The path at the top, such as *New › title*, goes back to the section you opened the vulnerability from.

<!-- page: def-aceitar -->
# Accepting and recording the RVS ID

Starting the fix of a vulnerability takes two steps, and they are separate on purpose: accepting tells the Red Team the vulnerability was received and will be dealt with, even before there is a ticket for it.

In **New**, open the vulnerability and click **Accept**. It moves to *Awaiting RVS*, with your name and the date of acceptance. Then open the RVS in your team's system and, on the vulnerability, enter the **RVS ID** and click **Record RVS**. It moves to *In progress*, and the fix begins. You have to accept before recording the RVS ID.

## The RVS ID

Each vulnerability has its own RVS ID. An ID already used on another vulnerability is refused, and the message says which vulnerability has it. Case and spaces don't count in the comparison: `RVS-1` and ` rvs-1 ` are the same ID.

The ID can't be changed once recorded. If you recorded a wrong ID, ask the Red Team to correct it: an administrator returns the vulnerability to *Awaiting RVS*, and you record the right ID.

<!-- page: def-risco -->
# Accepting the risk

Not every vulnerability will be fixed. The system may be about to be retired, there may be a control that compensates for the flaw, or the business may decide to live with it. In those cases, instead of accepting, use **Accept risk**, in *New* or in *Awaiting RVS*.

The portal asks for a reason, at least five characters long, and it is required: it is the record of why that flaw still exists, and the Red Team sees it in the timeline. The vulnerability goes to **Risk accepted**, and its path ends there, as if it had been fixed. A report counts as completed when all its vulnerabilities are fixed or have had their risk accepted.

If the decision changes, open the vulnerability in *Risk accepted* and use **Undo accepted risk**. It goes back to *New*, or to *Awaiting RVS* if it had already been accepted. The earlier reason isn't lost: it stays in the audit record.

<!-- page: def-lote -->
# Several vulnerabilities at once

A report usually brings many vulnerabilities, and dealing with them one by one would be slow. In the sections with actions (*New*, *Awaiting RVS*, *In progress* and *Risk accepted*), you can act on several at once.

To choose the vulnerabilities, tick the boxes to the left of the rows; the header box ticks the whole page. There is also a shortcut for the most common case: clicking a report's name selects all of its vulnerabilities in the section, across every page and within the current filter, and a second click clears the selection. With the selection made, click **Actions** and choose; the menu only shows what the section allows.

Most actions only ask for a confirmation: **Accept**, **Request retest**, **Mark as fixed** and **Undo accepted risk**. Requesting a retest and marking as fixed only apply to vulnerabilities being fixed; those being retested are skipped. **Accept risk** asks for a reason, which applies to all the selected ones.

**Record RVS** is different, because each vulnerability has its own ID. The action opens a form with one line per vulnerability, with the internal ID, the title and a field for the RVS ID. Fill in what you have; blank fields are left for later. IDs repeated in the form, or already used on another vulnerability, are pointed out on their line, and the lines recorded leave the form, so you see what is left.

At the end of any action, the portal says how many vulnerabilities were handled, how many were skipped because the action didn't apply to them and how many failed, with the reason for each failure.

<!-- page: def-filtros -->
# Filters

Each section has the **Filter** box at the top. Free text searches the vulnerability's identifier; to filter by something else, write a key, a colon and a value. Type `/` to see the available keys.

| Filter | Shows |
|---|---|
| `status:fixing` | The exact state: `sent`, `fixing`, `retesting`, `fixed` or `risk_accepted` |
| `cvss:7` | Those with a CVSS of 7 or more |
| `report:Data` | Those from a report whose name contains the text; `report:none`, those that didn't come from a report |

Several terms combine, and all of them must hold at once. A `-` before the key excludes what matches. The value runs up to the first space, so for values with spaces, use quotes: `report:"Data Center Network"`. Each section starts with no filter.

## Dates

**More filters…**, at the end of the `/` menu, holds the date filters: `sent` (received), `accepted` (accepted), `fixing` (start of the fix), `retesting` (retest requested), `fixed` (fixed) and `risk` (risk accepted). The value says the period.

`sent:7d` means in the last seven days, today included, and in the same way `m` counts months and `y` counts years. A date on its own means that whole period: `fixed:10-2026` is October 2026, and a date can also be a day (`05-10-2026`), a year (`2026`), a semester (`26S1`) or a quarter (`26T3`). Two dots make a range, both ends included, as in `fixed:01-09-2026..30-09-2026`, and an empty end leaves it open, as in `sent:01-10-2026..`.

A `-` inverts the period: `-sent:15d` shows those received more than fifteen days ago, a good filter for the *New* section.

<!-- page: def-depois -->
# After the RVS ID

With the RVS ID recorded, the vulnerability stays in **In progress** while it is fixed. The team responsible works on the fix and, when it is ready, you open the vulnerability and choose one of two paths.

The normal path is **Request retest**, so the Red Team checks whether the fix works. If the retest passes, the Red Team moves the vulnerability to *Fixed*. If not, it goes back to being fixed, and you request a new retest once the team fixes it again.

When a retest isn't needed, **Mark as fixed** takes the vulnerability straight to *Fixed*, without the Red Team's check. That choice is recorded.

Each vulnerability's timeline shows when each stage happened.
