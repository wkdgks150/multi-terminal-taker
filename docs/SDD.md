# Service Design Document (SDD)

> **Project**: [project name]
> **Last modified**: [YYYY-MM-DD]
> **Version**: v0.1
> **Author**: [name]

---

## 1. Service Overview

<!-- What is this service? What is its core value proposition? -->



---

## 2. Information Architecture (IA)

<!-- Overall menu structure and screen hierarchy -->

```
[Service Name]
├── Home
├── [Main Menu 1]
│   ├── [Sub Screen]
│   └── [Sub Screen]
├── [Main Menu 2]
│   ├── [Sub Screen]
│   └── [Sub Screen]
├── My Page
│   ├── Profile
│   └── Settings
└── Auth
    ├── Login
    └── Sign Up
```

---

## 3. User Flows

### Core Flow A: [flow name]
<!-- e.g., Sign Up → Browse → Join → Participate -->

```
[Start] → [Step 1] → [Step 2] → [Step 3] → [End]
```

### Core Flow B: [flow name]

```
[Start] → [Step 1] → [Step 2] → [End]
```

---

## 4. Screen Specifications

### 4.1 [Screen Name]

- **Purpose**:
- **Entry path**:
- **Components**:
- **User actions**:
- **System responses**:
- **Error handling**:

### 4.2 [Screen Name]

- **Purpose**:
- **Entry path**:
- **Components**:
- **User actions**:
- **System responses**:
- **Error handling**:

<!-- Add 4.N sections as screens are added -->

---

## 5. Data Model

### Key Entities

| Entity | Description | Key Fields |
|--------|-------------|------------|
| | | |
| | | |

### ERD (Entity Relationship Diagram)

<!-- Mermaid or text-based relationship diagram -->

```
[Entity A] 1──N [Entity B]
[Entity B] N──M [Entity C]
```

---

## 6. API Specification

### Auth

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| POST | /api/auth/signup | Sign up | | |
| POST | /api/auth/login | Login | | |

### [Domain]

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| | | | | |

<!-- Add domain sections as APIs are added -->

---

## 7. Tech Stack

| Area | Technology | Rationale |
|------|------------|-----------|
| Frontend | | |
| Backend | | |
| Database | | |
| Infrastructure | | |
| Other | | |

---

## 8. Policies

### Auth & Security Policy
<!-- Password rules, session management, token policy, etc. -->

### Permission Policy
<!-- Role-based access control -->

### Data Policy
<!-- Privacy, data retention period, etc. -->
