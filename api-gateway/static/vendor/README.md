# Swagger UI vendor assets

These files are distributed from `swagger-ui-dist` version `5.35.1`:

- `swagger-ui-bundle.js`
- `swagger-ui.css`
- `NOTICE`
- `swagger-ui-bundle.js.LICENSE.txt`

The package is licensed under Apache License 2.0; see `LICENSE`. The favicon is
the package's `favicon-32x32.png`, copied to `app/static/favicon.png` for the
path configured by the FastAPI Swagger route.

To update these files, download the matching package release and copy only the
assets used by `app/main.py`, along with its license and notice files.
