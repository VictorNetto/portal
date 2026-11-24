<!-- page: gerenciamento -->
# Administration

This chapter is for those who run the portal. It covers what keeps the portal working for everyone else: people's accounts and what each one reaches, the keys of integrated systems, the team's templates and report reservations that get stuck. The audit logs, which administrators also consult, have their own chapter.

As an administrator, you see and change everything in the portal, and you also see the documentation of every role, including the defense team's and the dashboards' parts, so you know what each audience finds.

<!-- page: adm-usuarios -->
# Users and access

The **Users** page, in the menu, lists every account. You can search by username and filter by role or state, and the selected user is kept in the page's address, so you can send the link to another administrator.

To create an account, use **New user** and enter the username, a temporary password and the role. Give the password to the person through a secure channel; at their first sign-in, they will have to change it. The role can be changed later on the user's page, and the change applies at once.

When someone forgets their password, **Reset password** sets a new temporary password and forces the change at the next sign-in; that person's open sessions are blocked until they change it. When someone leaves the team, **Deactivate** blocks their access at once, open sessions included. You can't deactivate your own account.

## What each person reaches

With the restricted roles, it isn't always obvious what a person can see. Each user's page has an access list that answers that: it shows which vulnerabilities and reports the person reaches, and why. The reason can be *Created*, *Operator*, *Shared*, through the *Shared with* field, or *Via report*, for the vulnerabilities of a report the person can access. For the roles with full access (Administrator, Editor and Reader of all, and Auditor), the page simply says the person sees everything.

It is worth checking that list before sharing something with a Restricted editor or reader, to be sure they will see what they should, and nothing more.

<!-- page: adm-chaves -->
# API keys

Each system that talks to the portal through the API uses a key, and administrators are the ones who create them, on the **API keys** page. Create one key per system, with a name that says which system it belongs to, only the scopes it uses and, preferably, an expiry date. [Keys, scopes and authentication](#api-chaves) describes each scope.

The full key is shown once only, right after it is created. Copy it and give it to the person responsible for the system through a secure channel. After that, the portal only shows the prefix, and there is no way to recover the rest; if a key is lost, create another.

The list of keys shows each one's scopes, expiry and last use, which helps to spot forgotten keys. **Revoke** turns a key off at once: do that with the ones no longer used and with any that may have leaked.

The `vulns:import` scope calls for extra care, because it lets the key create vulnerabilities with past statuses, dates and numbers. Give it only to the key of the script that brings in past vulnerabilities, and revoke that key when the import is done.

<!-- page: adm-templates -->
# Approving templates

Shared templates belong to the whole team, so they go through an administrator before appearing for everyone. On the **Templates** page, the **N awaiting approval** shortcut lists the sharing requests. Open each template and read its content before deciding.

**Approve** makes the template *Shared*, available to everyone. **Reject** returns it to *Private*, so the author can adjust it and ask again if they want. Later, if a shared template stops being useful, **Unshare** makes it *Unavailable* to everyone, the author included, and **Share again** brings it back.

As an administrator, you see every template, private ones included, and can edit or delete any of them.

<!-- page: adm-reservas -->
# Report reservations

While someone is editing a report, the report's page shows who holds the reservation and since when. Most of the time there is nothing to do: if the person leaves without releasing the reservation, it expires by itself after 10 minutes without activity.

When you can't wait, **Release lock**, on the report's page, releases the reservation at once. Do it with care, because the changes the person hadn't saved yet are lost. The release is kept in the audit logs.
