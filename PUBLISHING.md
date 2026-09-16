# Publishing

`.github/workflows/publish.yml` checks the source sheets and announcements Doc hourly and republishes encrypted `data.enc` only when output changes. It can also be run manually.

Repository Actions secrets required:

- `WARD_SITE_PASSPHRASE`: site passphrase
- `GOOGLE_SERVICE_ACCOUNT_JSON`: a Google service-account key JSON. Share the announcements Doc with the service account's `client_email` as Viewer.

The existing unguessable `.ics` filename is preserved by `build_site.sh`.
