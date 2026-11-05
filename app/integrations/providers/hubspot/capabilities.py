"""HubSpot integration capabilities, default properties, and scope declarations."""

# Standard HubSpot OAuth scopes required for read-only CRM intelligence
HUBSPOT_READ_SCOPES = [
    "crm.objects.companies.read",
    "crm.objects.contacts.read",
    "crm.objects.deals.read",
]

# Standard company properties requested from HubSpot CRM v3 API
HUBSPOT_COMPANY_PROPERTIES = [
    "name",
    "domain",
    "industry",
    "description",
    "annualrevenue",
    "numberofemployees",
    "city",
    "state",
    "country",
    "website",
    "createdate",
    "hs_lastmodifieddate",
]

# Standard contact properties requested from HubSpot CRM v3 API
HUBSPOT_CONTACT_PROPERTIES = [
    "firstname",
    "lastname",
    "email",
    "jobtitle",
    "department",
    "phone",
    "mobilephone",
    "associatedcompanyid",
    "lifecyclestage",
    "hs_lead_status",
    "createdate",
    "lastmodifieddate",
]

# Standard deal properties requested from HubSpot CRM v3 API
HUBSPOT_DEAL_PROPERTIES = [
    "dealname",
    "dealstage",
    "amount",
    "closedate",
    "pipeline",
    "createdate",
    "hs_lastmodifieddate",
]

