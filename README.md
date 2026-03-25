# Serverless-PDF-Tools
- A lightweight tool for performing common PDF operations without relying on external SaaS platforms.
- Deploy it inside your own cloud environment to process documents securely while maintaining full control over your data.

## Highlights
- A fully serverless web app to handle everyday PDF tasks.
- Compress, split, merge, remove-pages, and password-protect PDFs.
- Frontend is served via S3 Static Website Hosting.
- Backend uses API Gateway + Lambda + S3.
- S3 lifecycle rule auto-deletes uploaded and processed PDFs after 1 day.
- **Near-zero cost when idle!**

## Architecture
<img src="documentation/architecture-diagram.png" style="width:90%;" alt="Architecture">

## Screenshots
<img src="screenshots/home-screen.png" style="width:90%;" alt="Home Screen">

See more in the [screenshots/](screenshots/) folder.
