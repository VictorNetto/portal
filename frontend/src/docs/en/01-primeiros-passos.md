<!-- page: primeiros-passos -->
# Getting started

Before recording your first vulnerability, it helps to know the ground: how to sign in, how the portal is laid out, how long a session lasts and what your role lets you do. This chapter covers those points. If you have been using the portal for a while, you can move on to the next chapter and come back here when you need to.

<!-- page: inicio -->
# Signing in and finding your way

The first time, sign in with the username and temporary password the administrator gave you. Before showing anything else, the portal asks for a new password, and the same happens whenever an administrator resets your password. Choose the new password on your **Profile**, which opens by itself at that moment, and the portal lets you through.

Once you are in, the screen has two fixed areas. On the left is the menu, with an icon for each area of the portal. The ☰ button at the top opens the menu with the names spelled out; with the menu closed, hover over an icon to see what it is. Some areas have more than one page: under **Reports**, for example, are *Create Report* and *Templates*, and you pick one by hovering over the icon.

In the top right corner is the button with your user. It holds what belongs to no area in particular: the portal's language, this documentation, your profile, the time left in your session and the button to sign out.

The menu only shows what your role lets you use. If an area someone mentioned doesn't appear for you, it isn't a mistake: you don't have access to it. [Roles and access](#papeis) explains what each role sees.

<!-- page: sessao -->
# The session

For security, a session in the portal doesn't last forever. It ends for one of two reasons: **1 hour** after signing in, however you use it, or earlier, after **15 minutes without activity**. Moving the mouse, typing or scrolling counts as activity, in any open tab of the portal.

Your user menu shows both limits side by side, as **Session mm:ss / mm:ss**. The first is the time until the session ends for inactivity, and the second, the time until the hour is up. The portal also warns you before each one. Two minutes before the inactivity limit, the question *"Are you still there?"* appears, and clicking **Stay signed in** starts the count again. Five minutes before the hour is up, the portal asks you to save whatever you are editing, because that limit can't be extended.

If the session ends while you have unsaved changes, nothing is lost straight away. The page stays open and the portal asks for your password again; once you are back in, save as usual. If you would rather abandon what you were doing, **Discard and leave** ends it without saving.

After five failed sign-in attempts within 15 minutes, the account is locked for a few minutes. If you forgot your password, ask an administrator to reset it.

<!-- page: perfil -->
# Your profile and your name

Your **Profile**, in your user menu, shows who you are to the portal: your username, your role and the names others know you by. It is also where you change your password.

Your **username** is what you type to sign in. It may be an email address, an employee number or any other identifier your organisation uses. Only an administrator sets it, and it doesn't change afterwards.

Besides the username, you have two names, and each appears in a different place. Your **full name** goes into the documents that leave the portal, such as the list of operators in a report's PDF, so it should be your formal name. Your **display name** is how colleagues see you inside the portal: in a vulnerability's operators, in the notice of who is editing a report, as the owner of a template. If the display name is empty, the portal uses the full name; if both are empty, it uses the username.

To change a name, edit the field and click **Save**. Leaving a field blank and saving clears that name. In search and in filters such as `operator:`, both your name and your username find you.

<!-- page: papeis -->
# Roles and access

Everyone in the portal has a **role**, set by an administrator, and the role decides what they see and what they can change. Most of the team works with access to everything. The restricted roles exist for people who should only see part of the work, and two roles serve audiences outside the Red Team.

| Role | Sees | Can |
|---|---|---|
| **Administrator** | Everything | Everything, including managing users, API keys and the sharing of templates |
| **Editor (all)** | Everything | Create and change any vulnerability or report |
| **Reader (all)** | Everything | Only look |
| **Auditor** | Everything, and the audit logs too | Only look |
| **Restricted editor** | What they created, what they are an operator of and what was shared with them | Create vulnerabilities and reports, change what they created or operate, delete only what they created |
| **Restricted reader** | What they created, what they are an operator of and what was shared with them | Only look |
| **Dashboards** | Only counts, never the vulnerabilities | Build dashboards and TV links |
| **Defense** | Only sent vulnerabilities, without internal notes, operators or reports | Accept each one, record the RVS ID or accept the risk |

The restricted roles depend on two fields of each record. **Operators** are the people who work on the finding or the operation. **Shared with** is a list of people who may follow the record without working on it. For a Restricted reader to see a vulnerability, for example, add them to *Shared with*. A report's vulnerabilities follow the report's access: whoever sees the report sees all of them.

Defense and Dashboards accounts are different from the others. They don't enter the Red Team's areas, and each has its own part of this guide, which only they and administrators see.
