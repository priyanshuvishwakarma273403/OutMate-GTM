"""Candidate person identity resolution and deduplication service."""

import re

from app.domain.models.person import DecisionMaker, EmploymentStatus


class PersonIdentityResolutionService:
    """Resolves identities, prevents conflation of distinct individuals, and deduplicates candidates."""

    HONORIFICS_REGEX = re.compile(
        r"^(dr\.?|mr\.?|mrs\.?|ms\.?|prof\.?|sir)\s+",
        re.IGNORECASE,
    )
    CREDENTIALS_REGEX = re.compile(
        r"[,;\s]+(ph\.?d|m\.?b\.?a|m\.?d|cpa|pmp|esq)\b",
        re.IGNORECASE,
    )

    def normalize_name(self, raw_name: str) -> str:
        """Strip honorifics, academic titles, and extraneous punctuation."""
        if not raw_name:
            return ""
        name = self.HONORIFICS_REGEX.sub("", raw_name.strip())
        name = self.CREDENTIALS_REGEX.sub("", name)
        name = re.sub(r"[,;]+", "", name)
        return re.sub(r"\s+", " ", name).strip()

    def deduplicate_candidates(
        self,
        candidates: list[DecisionMaker],
    ) -> list[DecisionMaker]:
        """Deduplicate candidates from multiple search passes while disambiguating similarly named people."""
        deduped_by_key: dict[str, DecisionMaker] = {}

        for candidate in candidates:
            clean_name = self.normalize_name(candidate.full_name)
            name_token = re.sub(r"[^a-z0-9]", "", clean_name.lower())
            company_token = re.sub(r"[^a-z0-9]", "", candidate.company_name.lower())

            key = f"{name_token}@{company_token}"

            if key not in deduped_by_key:
                candidate.full_name = clean_name
                deduped_by_key[key] = candidate
                continue

            existing = deduped_by_key[key]

            # Compare titles to distinguish duplicate mentions from two distinct people with same name
            existing_title = existing.title.lower()
            new_title = candidate.title.lower()

            # Check if one is a subset or variation of the other (e.g., 'CEO' and 'CEO and Founder')
            is_compatible_role = (
                existing.department == candidate.department
                or existing_title in new_title
                or new_title in existing_title
                or existing.seniority == candidate.seniority
            )

            if is_compatible_role:
                # Merge evidence
                seen_urls = {ev.source_url for ev in existing.evidence}
                for ev in candidate.evidence:
                    if ev.source_url not in seen_urls:
                        existing.evidence.append(ev)
                        seen_urls.add(ev.source_url)

                # Keep longer, more specific title
                if len(candidate.title) > len(existing.title):
                    existing.title = candidate.title

                # Prefer official URLs if newly found
                if candidate.contact_info.linkedin_url and not existing.contact_info.linkedin_url:
                    existing.contact_info.linkedin_url = candidate.contact_info.linkedin_url
                if candidate.biography and not existing.biography:
                    existing.biography = candidate.biography
                if candidate.biography_url and not existing.biography_url:
                    existing.biography_url = candidate.biography_url
            else:
                # Wildly divergent roles: could be two different individuals at the same company!
                # Mark both as ambiguous rather than merging destructively
                existing.employment_status = EmploymentStatus.IDENTITY_AMBIGUOUS
                candidate.employment_status = EmploymentStatus.IDENTITY_AMBIGUOUS
                # Store separate key with distinct title to preserve both records
                alt_key = f"{key}#{len(deduped_by_key)}"
                candidate.full_name = clean_name
                deduped_by_key[alt_key] = candidate

        return list(deduped_by_key.values())
