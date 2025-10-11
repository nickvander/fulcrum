# Task: Phase 7 - Adopt `uv` and Refine Documentation

## 1. Goal

To significantly improve the speed and ergonomics of Python dependency management by adopting `uv`. Additionally, to enhance the structure, clarity, and presentation of the project's documentation.

## 2. Implementation Strategy

---

### **Stage 1: Adopt `uv`**

1.  **Update CI Workflows:**
    -   **Action:** Modify all workflows that install Python dependencies (`ci-lint`, `backend-02-unit-tests`, `docs-02-build`).
    -   **Action:** Add a step to install `uv` and replace the `python3 -m pip install` commands with the much faster `uv pip install`.
    -   **Benefit:** Speeds up all CI jobs that rely on Python dependencies.

2.  **Update Local Scripts:**
    -   **Action:** Modify the `test:backend:fast` and `docs:serve` scripts in `package.json` to use `uv pip install`.
    -   **Benefit:** Improves the speed and consistency of local setup.

3.  **Update Setup Documentation:**
    -   **Action:** Rewrite the "Setting Up a Virtual Environment" section in `docs/source/backend-setup.md` to use the simpler `uv venv` and `uv pip install` commands.
    -   **Benefit:** Provides a faster, more modern, and easier-to-follow setup guide for new developers.

---

### **Stage 2: Refine Documentation Content**

1.  **Improve Documentation Landing Page:**
    -   **Action:** Rewrite `docs/source/README.md` to be a more welcoming and informative introduction to the Fulcrum project's technical documentation.
    -   **Action:** Remove the numbering from the table of contents in this file to improve readability.
    -   **Benefit:** Creates a clearer and more professional entry point for anyone reading the docs.

2.  **Clarify the Documentation Meta-Guide:**
    -   **Action:** Rewrite the top-level `docs/README.md` to clearly separate its purpose. It will have two sections: "About This Documentation" (what the content is) and "Contributing to the Documentation" (how to build it locally).
    -   **Benefit:** Reduces confusion by making it clear that this file is about the documentation *system*, not the project itself.
