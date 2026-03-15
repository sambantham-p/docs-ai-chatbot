# SecureDoc AI — Frontend

> React + TypeScript + Vite · Double E2E Encrypted · RAG Document Chat

## What This Is

The frontend for **SecureDoc AI** — an AI-powered document assistant where users upload sensitive documents and chat with them using Gemini 1.5. Every request and response is application-layer encrypted using RSA-OAEP + AES-GCM hybrid encryption, layered on top of TLS.

The client owns the RSA private key. It never leaves the browser.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | React 18 + TypeScript + Vite |
| State Management | MobX |
| HTTP Client | Axios (with custom encryption interceptors) |
| Encryption | Web Crypto API (`window.crypto.subtle`) |
| Styling | Tailwind CSS |
| Routing | React Router v6 |

---

## Key Architecture Concepts

### ClientEncryptionService
The most important service in the frontend. Lives at `src/api/encryption/encryption.service.ts`.
- Generates RSA-OAEP 2048-bit key pair on every session via `window.crypto.subtle`
- Conducts key exchange with backend (`POST /api/v1/key-exchange`)
- Encrypts every outgoing request body (AES-GCM + RSA-wrapped session key)
- Decrypts every incoming response body

### Axios Interceptors (`Api.manager.ts`)
- **Request interceptor**: calls `ClientEncryptionService.encryptRequest()` before every API call
- **Response interceptor**: calls `ClientEncryptionService.decryptResponse()` on every response
- Adds `x-encrypted: true` and `x-client-id` headers automatically
- Business logic components never touch encryption — they just use plain JS objects

### MobX Stores
Reactive state containers for auth, documents, and chat. Components observe store properties and re-render automatically.

---

## Pages

| Page | Route | Purpose |
|---|---|---|
| LoginPage | `/login` | Email/password login + key exchange |
| RegisterPage | `/register` | New user registration |
| DocumentsPage | `/documents` | List documents, upload new |
| DocumentDetailPage | `/documents/:id` | Chunk sensitivity tagging UI |
| ChatPage | `/chat/:conversationId` | AI chat with document context |
| AuditPage | `/audit` | Decrypt event audit log |

---

## UI Design

- **Color scheme**: Dark sidebar (`#111827`) + light content area (`#f9fafb`)
- **Primary color**: `#1a56db` (blue)
- **Sensitivity badges**: Green for PUBLIC (`#dcfce7` / `#166534`) · Red for PRIVATE (`#fee2e2` / `#991b1b`)
- Encryption shield badge in topbar — shows session status on hover

---

## Environment Variables

Create a `.env` file in the `frontend/` root:

```env
VITE_API_BASE_URL=http://localhost:4000/api/v1
```
