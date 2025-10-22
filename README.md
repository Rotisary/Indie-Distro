# 🎬 Indie Distro

A platform for independent filmmakers and film lovers. It allows filmmakers to upload their films and set custom sale prices; interested viewers then purchase the movies before they can get viewing access. 
It helps creators bypass traditional gatekeepers and earn revenue without relying on ad views or platform algorithms.


## 🚀 Features

- 🎥 **Film Uploads:** Creators can upload movies securely with metadata and pricing.
- 💰 **Monetization:** Custom sale prices and secure payment integration.
- 🔒 **Access Control:** Viewers must purchase before streaming access is granted.
- ⚙️ **Background Processing:** Celery workers handle video uploads and transcoding asynchronously.
- 📦 **Cloud Storage:** All files stored on AWS S3 (or similar) for scalability.
- 🚦 **Caching:** Redis-powered caching for fast retrieval and reduced load.
- 🧾 **Analytics (Planned):** Track views, purchases, and user engagement.
  

## 🧱 Tech Stack

| Layer | Technology |
|-------|-------------|
| Backend Framework | Django, Django REST Framework |
| Task Queue | Celery + Redis |
| Database | PostgreSQL |
| Storage | AWS S3 |
| Authentication | JWT (djangorestframework-simplejwt) |

⭐ If you like this project, consider starring the repo!
