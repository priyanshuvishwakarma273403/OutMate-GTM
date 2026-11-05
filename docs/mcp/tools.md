# Outmate GTM — MCP Tool Catalog

The Outmate GTM MCP Server exposes 9 production tools. All tools execute against real application services and public evidence citations. No tool generates synthetic contacts, fabricated facts, or mocked results.

---

## 1. Company Intelligence Tools

### `search_company`
- **Description**: Search public web records for corporate mentions, domains, and general background.
- **Required Scope**: `company:search`
- **Underlying Service**: `SearchClient.search` (Tavily / Exa search client)
- **Input Parameters**:
  - `query` (string, required): Company name or search keywords (min 2 chars).
  - `domain` (string, optional): Target corporate domain filter (e.g., `vercel.com`).
  - `limit` (integer, default 5): Maximum search results to return (1 to 20).
- **Example Usage**:
  ```json
  {
    "query": "Vercel",
    "domain": "vercel.com",
    "limit": 5
  }
  ```

### `research_company`
- **Description**: Execute comprehensive company intelligence research including domain resolution, industry classification, headcount, tech stack, and multi-source evidence corroboration.
- **Required Scope**: `company:research`
- **Underlying Service**: `CompanyResearchService.research_company`
- **Input Parameters**:
  - `company_name` (string, required): Commercial name of target company.
  - `company_domain` (string, optional): Target corporate website domain.
  - `research_depth` (string, default "standard"): Depth of research (`standard` or `deep`).
- **Output**: Returns full `CompanyResearchReport` containing verified company profile, corroboration findings, limitations, and public evidence citations.

### `get_company_profile`
- **Description**: Retrieve an existing verified company profile by its research run reference ID.
- **Required Scope**: `company:read`
- **Underlying Service**: `InMemoryReportRepository.get_report`
- **Input Parameters**:
  - `research_reference` (string, required): Unique `research_id` of the completed company research run.

---

## 2. Decision-Maker Discovery Tools

### `find_decision_makers`
- **Description**: Discover real business executives and decision-makers for a target company, verify active employment, classify organizational roles, and assess commercial purchasing influence.
- **Required Scope**: `people:discover`
- **Underlying Service**: `PeopleResearchService.discover_decision_makers`
- **Input Parameters**:
  - `company_name` (string, required): Target company name.
  - `company_domain` (string, optional): Corporate primary domain.
  - `product_context` (string, optional): Commercial context for scoring buyer persona fit.
  - `target_departments` (list[string], optional): Target departments (e.g. `["engineering", "executive"]`).
  - `seniority_levels` (list[string], optional): Target seniority levels (e.g. `["c_level", "vp"]`).
  - `discovery_limit` (integer, default 10): Maximum candidates to discover (1 to 50).
  - `research_depth` (string, default "standard"): `standard` or `deep`.
- **Output**: Full `DecisionMakerReport` including scored prospects (`scored_people`), audit summary, and cited evidence.

### `verify_person`
- **Description**: Corroborate a discovered person's active employment and identity against public evidence citations.
- **Required Scope**: `people:verify`
- **Underlying Service**: `EmploymentVerificationService.verify_employment`
- **Input Parameters**:
  - `research_reference` (string, required): Decision-maker research run ID.
  - `person_reference` (string, required): Unique `person_id` of the candidate.
- **Output**: Corroboration status, employment status, confidence score (0.0 to 1.0), and textual explanation.

### `get_person_details`
- **Description**: Retrieve in-depth profile, buying influence assessment, and evidence citations for a decision-maker.
- **Required Scope**: `people:read`
- **Underlying Service**: `InMemoryReportRepository.get_person`
- **Input Parameters**:
  - `research_reference` (string, required): Research run ID.
  - `person_reference` (string, required): Unique `person_id` of candidate.

---

## 3. Evidence Audit & Dossier Tools

### `get_research_sources`
- **Description**: Retrieve the public evidence records and source audit trail backing a completed company research dossier.
- **Required Scope**: `research:sources:read`
- **Underlying Service**: `InMemoryReportRepository.get_report`
- **Input Parameters**:
  - `research_reference` (string, required): Company research run ID.

### `get_decision_maker_sources`
- **Description**: Retrieve public evidence citations backing discovered decision-makers or a specific person.
- **Required Scope**: `research:sources:read`
- **Underlying Service**: `InMemoryReportRepository.get_decision_maker_report`
- **Input Parameters**:
  - `research_reference` (string, required): Decision-maker research ID.
  - `person_reference` (string, optional): Filter evidence for a single candidate `person_id`.

### `get_research_report`
- **Description**: Retrieve a full completed company or decision-maker research report by ID.
- **Required Scope**: `company:read`
- **Underlying Service**: `InMemoryReportRepository`
- **Input Parameters**:
  - `research_reference` (string, required): Unique report ID.

