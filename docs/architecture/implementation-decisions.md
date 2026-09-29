# Implementation decisions

The organizer's full-platform implementation request supersedes the discovery-only instruction and earlier MVP exclusions. All justified core modules will be integrated. Original event documents remain unchanged.

Stack: Python 3.11, Django 5.2 LTS, PostgreSQL, Django ORM, templates with progressive JavaScript, django-otp, database-backed outbox, private filesystem storage with an external scanner hook, and WhiteNoise for versioned static assets. Exact resolved dependencies are locked. No separate frontend application, distributed queue, microservices or public cloud accounts are required to develop locally.

Unknown policy values stay inactive/configurable. Initial registration mode is closed; payment mode is undecided; public release and privacy approval are explicit. Event identity/dates are imported from repository sources by a management command with provenance, not embedded in views. Named staff are not fabricated. Payment production adapters cannot be selected without a provider decision; a typed contract and sandbox tests will cover the boundary.

Local PostgreSQL uses an isolated cluster/port and generated credentials in ignored local files. Existing PostgreSQL databases are not altered. The application directory is the deployment build context; private original sources are never copied into the image.
