<!--
Sync Impact Report
==================
Version change: [TEMPLATE, unratified] → 2.1.0
Rationale: Initial ratification of the LingoAI project constitution in this
repository. The template contained only placeholder tokens with no prior
ratified content, so this is treated as the founding version. The version
number 2.1.0 was supplied explicitly by the project owner (not derived via
the MINOR-bump heuristic, since there was no prior in-repo version).

Modified principles: N/A (initial fill, no prior named principles to rename)

Added sections (all new):
  1. Product Principle
  2. Specification First
  3. Architecture Principles
  4. Client Independence
  5. AI Architecture
  6. Technology Principles
  7. Environment Independence
  8. Configuration Management
  9. Database Principles
  10. Engineering Quality
  11. Testing Principles
  12. Data Principles
  13. Security
  14. API Principles
  15. Documentation
  16. Git Workflow
  17. MVP Principle
  18. Final Decision Rule
  Governance (amendment procedure, versioning policy, compliance review)

Removed sections: N/A (removed only template placeholder scaffolding)

Templates requiring follow-up review (not modified by this command; owned by
their respective commands):
  - .specify/templates/plan-template.md — verify its Constitution Check
    section references principles by name accurately (⚠ pending manual check)
  - .specify/templates/spec-template.md — verify no contradictions with
    Section 2 (Specification First) required fields (⚠ pending manual check)
  - .specify/templates/tasks-template.md — verify task categorization aligns
    with Section 3 (Architecture Principles) and Section 11 (Testing
    Principles) (⚠ pending manual check)
  - .specify/templates/checklist-template.md — no constitution-specific
    references expected (✅ low risk)

Deferred items / TODOs:
  - TODO(RATIFICATION_DATE): Original adoption date of this constitution was
    not provided and could not be derived from repository history (no prior
    ratified version exists in this repo). Replace with the actual date this
    governance document was first adopted by the project.
-->

# LingoAI Constitution

## Core Principles

### 1. Product Principle

LingoAI is an AI-powered English learning platform, not a chatbot. The
educational experience is the product. Artificial Intelligence assists the
learning process but MUST NOT independently define pedagogical decisions or
user progression. Every technical decision MUST improve the user's learning
experience.

### 2. Specification First

No implementation MAY begin without an approved specification. Every
specification MUST include: Problem Statement, Functional Requirements,
Non-functional Requirements, Acceptance Criteria, Technical Impact, Testing
Strategy, and Rollback Considerations (when applicable).

The development workflow is immutable:

Specification → Technical Plan → Task Breakdown → Implementation → Review → Validation

Specifications are the source of truth.

### 3. Architecture Principles

The system MUST follow Clean Architecture, Domain-Driven Design (DDD),
Modular Design, and Separation of Concerns. Business rules MUST exist only
inside the Domain layer. Infrastructure, Controllers, and UI MUST remain
independent of business logic. Dependencies MUST point inward.

Prefer a modular monolith during the MVP. Microservices MUST NOT be
introduced unless justified by a specific architectural or scalability
requirement.

### 4. Client Independence

The pedagogical engine and business logic MUST remain independent of the
client. The initial product interface SHOULD be implemented as a responsive
Web application and MAY evolve into a Progressive Web App (PWA).

Web and future mobile clients MUST communicate with the backend through
defined APIs. Adding a new client MUST NOT require changes to core business
rules. Client-specific logic MUST remain inside the respective client layer.

### 5. AI Architecture

Artificial Intelligence MUST be implemented through specialized agents. Each
agent MUST have: single responsibility, explicit inputs, explicit outputs,
a deterministic workflow whenever possible, and independent testing.

Prompt templates are application assets and MUST be version-controlled. AI
providers MUST be replaceable without affecting business rules.
Vendor-specific implementations MUST remain isolated.

### 6. Technology Principles

Prefer open-source technologies, low operational cost, vendor independence,
simple infrastructure, and mature ecosystems.

Avoid premature optimization, unnecessary frameworks, vendor lock-in, and
overengineering.

Infrastructure MUST remain portable across environments. Technology choices
MUST be justified by project requirements rather than personal preference or
technological trends.

### 7. Environment Independence

Development is Local-First. The complete application MUST run locally
without cloud dependencies whenever practical. Infrastructure-specific
implementations MUST remain isolated.

Cloud deployment MUST require minimal or no application code changes.
Configuration MUST determine the running environment. The MVP environment
MUST prioritize development simplicity over production scalability.

### 8. Configuration Management

Configuration MUST NEVER be hardcoded. Secrets MUST come from environment
variables or secret managers. Different environments MUST be configured
externally.

Default development configuration SHOULD work immediately after project
setup. Local development configuration MUST NOT be committed when it
contains secrets or environment-specific sensitive information.

### 9. Database Principles

Database schema changes MUST be managed through migrations. Database
structure MUST be version-controlled. Business logic MUST NOT depend on
database-specific features unless technically justified.

The application SHOULD remain database-portable whenever practical.
Transactional data and analytical events MUST have clearly defined
responsibilities.

### 10. Engineering Quality

Engineering decisions MUST prioritize, in order: Simplicity, Maintainability,
Testability, Security, Scalability.

Production-ready code MUST include: automated tests, documentation,
structured logging, error handling, and basic observability. Complexity MUST
always require justification.

### 11. Testing Principles

Testing SHOULD follow the testing pyramid, in priority order: Unit Tests,
Integration Tests, End-to-End Tests.

Critical business rules MUST always be covered by automated tests.
End-to-end tests SHOULD focus on critical user journeys rather than
implementation details. Tests MUST be deterministic and reproducible.

### 12. Data Principles

Learning progress MUST be event-driven. Analytics MUST rely on events
instead of transactional tables.

Data models MUST support: user evolution, learning history, personalization,
and future analytics. Learning events SHOULD be immutable whenever possible.
The system MUST preserve the distinction between operational data and
analytical data.

### 13. Security

Security is mandatory. Every feature MUST consider: authentication,
authorization, input validation, secret protection, privacy, and least
privilege.

Sensitive information MUST NEVER be stored in source code. Security
requirements MUST be considered during specification, not only during
implementation.

### 14. API Principles

Public APIs MUST expose explicit contracts. Breaking changes REQUIRE
specification updates. APIs SHOULD remain versionable.

External integrations MUST be abstracted behind interfaces. API contracts
MUST NOT expose internal domain or infrastructure implementation details.

### 15. Documentation

Documentation MUST evolve together with the codebase. Major architectural
decisions SHOULD be documented using ADRs (Architecture Decision Records).

Outdated documentation MUST be updated as part of the related
implementation. Technical documentation MUST explain decisions when the
reasoning is not obvious from the code.

### 16. Git Workflow

The project MUST use feature branches, Pull Requests, Code Reviews, and
Conventional Commits.

Direct commits to the main branch are prohibited. The main branch MUST
always remain deployable.

### 17. MVP Principle

Always implement the smallest solution that satisfies the specification.
Avoid optimization before validated demand. Avoid distributed systems unless
clearly necessary. Prefer a well-structured modular monolith over
microservices during the MVP.

The MVP MUST prioritize: product validation, learning effectiveness,
development speed, and low operational cost. Scalability requirements MUST
be introduced when justified by measured demand.

### 18. Final Decision Rule

Whenever multiple technical solutions exist, prioritize, in order: user
learning impact, simplicity, maintainability, portability, cost efficiency,
scalability.

Every technical decision MUST contribute to building a better AI English
teacher while preserving long-term maintainability and client independence.

## Governance

This constitution supersedes all other engineering practices, style guides,
and informal conventions. Where a conflict exists between this document and
any other project artifact, this constitution prevails.

**Amendment procedure**: Amendments MUST be proposed via a feature branch and
Pull Request against `.specify/memory/constitution.md`, following the same
Git Workflow required by Section 16. Every amendment PR MUST include an
updated Sync Impact Report (prepended as an HTML comment at the top of this
file) describing the version change, modified/added/removed sections, and
any deferred TODOs. Amendments require review and approval before merge;
direct commits to main are prohibited, including for this document.

**Versioning policy**: This constitution is versioned using semantic
versioning (MAJOR.MINOR.PATCH):

- MAJOR: Backward-incompatible governance or principle removals or
  redefinitions.
- MINOR: A new principle or section is added, or existing guidance is
  materially expanded.
- PATCH: Clarifications, wording, typo fixes, or other non-semantic
  refinements.

**Compliance review**: Every specification, technical plan, and Pull Request
MUST be checked against this constitution before approval. Any deviation
from a MUST/MUST NOT rule requires explicit justification recorded in the
relevant specification's Technical Impact section; unjustified deviations
MUST block merge. Complexity introduced beyond what a principle requires
MUST be justified per Section 10 (Engineering Quality).

**Version**: 2.1.0 | **Ratified**: TODO(RATIFICATION_DATE): original adoption date not provided | **Last Amended**: 2026-08-11
