---
trigger: always_on
---

## Folder-Level Documentation & Architecture Alignment

- **Mandatory README:** Every major directory MUST contain a `README.md`.
- **Content Requirements:** The `README.md` must include:
  1. **Folder Responsibility:** A high-level description of what this domain/module handles.
  2. **File Manifest:** A brief explanation of each file's specific role within the folder.
  3. **Architecture & Design:** Explain design patterns (e.g., Singleton, Factory), data flow, or dependencies used here.
  4. **Implementation Guidelines:** Specific rules for adding new features or files to this folder to maintain consistency.
- **Sync Policy:** This `README.md` MUST be updated **simultaneously** with any code implementation or refactoring.
  - Treat documentation update as part of the "Definition of Done".
- **Goal:** Ensure both Human Maintainers and AI Agents can instantly understand the structure and align future code with the established architecture.
- **Language:** Follow the **Artifacts & Documentation Language Policy** (Traditional Chinese + English Terms).
