# Ward publishing

The site publisher reads only:
- Milton Ward Sacrament_website
- Milton Ward Activities_website
- the Announcements Doc

The middleware sync is a separate Actions workflow. It reads the old workbooks and copies only the named public columns into the private sheets. Dates older than 14 days are frozen. Invalid tabs retain their last good row and produce a workflow warning. An unreadable source or mismatched table header stops the job before publication. No source links are included in the site's payload.

The publisher keeps the password gate, noindex, hymn links, meeting order, stable calendar feed, and announcement graveyard rules. A failed read or invalid clean table fails the build without replacing the live encrypted data.

For cutover: run the middleware sync on this branch, inspect its summary, run a preview, compare rendered fields and calendar URL, then merge only after owner approval. The current production source path stays unchanged until that merge.
