# DartaLink Administrative Workflow

DartaLink follows a documented administrative workflow:

```text
Customer → Darta Staff → Relevant Sakha/Branch Staff → Sakha Pramukh
→ Darta Registration → Karyalaya Pramukh/Hakim → Chalani → Completed
```

Every request action is recorded with the responsible user, department,
remarks, timestamps, references, and status changes.

## 1. Customer request intake

### Responsible team

**Darta Staff**

Demo users:

- `darta1` — Sita Poudel — Darta Officer
- `darta2` — Hari Bhandari — Darta Assistant

### Information collected

Darta staff receives the request from the customer and records:

- Customer name
- Customer contact details
- Request title
- Request category
- Request description
- Required date
- Requested amount, when applicable
- Supporting documents and photographs
- Relevant branch or Sakha

Darta staff selects the receiving Sakha, such as IT, Prabidhik, Revenue,
Budget, or Lekha.

The system records:

- Customer information
- Darta intake staff
- Receiving department
- Uploaded documents
- Request number, for example `DL-REQ-2026-00013`

## 2. Branch preparation and Sakha verification

Customer requests received by Darta do not skip branch verification.

```text
Darta Staff
    ↓
Relevant Branch/Sakha Staff
    ↓
Sakha Pramukh
    ↓
Darta registration
```

After Darta submits the request, the selected branch staff:

- Checks the customer documents and photographs.
- Confirms the request belongs to the selected Sakha.
- Adds or uploads missing supporting material where permitted.
- Selects **Prepare for Pramukh review**.

The Sakha Pramukh then verifies the prepared request. A verified request is
returned to Darta for formal registration.

The system represents this path as:

```text
SUBMITTED → BRANCH_REVIEW → VERIFIED → REGISTERED
```

Internal requests created by branch staff continue to use the shorter path:

```text
SUBMITTED → VERIFIED → REGISTERED
```

## 3. Darta registration

The Darta process is:

```text
Customer → Darta Staff → Branch verification → Register in Darta
```

Before registration, Darta staff checks that:

- The request is understandable.
- Customer information is present.
- Required documents are attached.
- The correct receiving Sakha has been selected.

When Darta staff selects **Register in Darta**, the system:

- Assigns a Darta number such as `DARTA-2083/84-0001`.
- Records the Darta date.
- Records the registering staff member.
- Updates the request status to `REGISTERED`.
- Makes the request ready for forwarding.

Darta staff then forwards the registered request to the relevant branch or
authority.

## 4. General Sakha flow

The standard branch workflow is:

```text
Darta Staff
    ↓
Relevant Sakha Staff
    ↓
Sakha Pramukh verification
    ↓
Darta registration
    ↓
Karyalaya Pramukh / Hakim
    ↓
Chalani Staff
    ↓
Completed
```

A Sakha may:

- Review the request.
- Verify technical, financial, revenue, or operational details.
- Add a recommendation.
- Add a tippani.
- Issue a Tok Aadesh when authorized.
- Forward the request.
- Return the request for revision.
- Reject the request where authorized.
- Forward the request to the Karyalaya Pramukh for a final decision.

## 5. IT Sakha flow

### Demo users

- `it_staff` — Nabin Lama — System Engineer
- `it_staff2` — Mina Tamang — Network Technician
- `itchief` — Anita Rai — IT Sakha Pramukh

### Suitable requests

- VPN access
- Network equipment
- Server maintenance
- Hardware and software
- Communication infrastructure
- Security and access requests
- IT support

### Process

```text
Customer or requester
    ↓
Darta Staff
    ↓
Darta registration
    ↓
IT Staff
    ↓
IT Sakha Pramukh
    ↓
Budget/Lekha or Prabidhik review, if required
    ↓
Karyalaya Pramukh approval
    ↓
Chalani
    ↓
Completed
```

IT staff checks technical requirements, specifications, justification, and
supporting documents. The IT Sakha Pramukh validates the technical review,
adds recommendations or tippani, and forwards the request for decision.

## 6. Prabidhik Sakha flow

### Demo users

- `tech_staff` — Rojina Basnet — Engineer
- `prabidhik` — Sunita Gurung — Prabidhik Pramukh / Chief Engineer

### Suitable requests

- Engineering work
- Tower or site visits
- Fibre and network infrastructure
- Field inspection
- Technical construction or maintenance
- Equipment specifications
- Safety-related approvals

### Process

```text
Customer or requester
    ↓
Darta Staff
    ↓
Darta registration
    ↓
Prabidhik Staff
    ↓
Prabidhik Pramukh
    ↓
Karyalaya Pramukh / Hakim
    ↓
Chalani
    ↓
Completed
```

Prabidhik staff checks engineering feasibility, field requirements,
specifications, cost estimates, and safety requirements. The Prabidhik
Pramukh validates the technical recommendation and forwards the request.

## 7. Rajaswa Sakha flow

### Demo users

- `rev_staff` — Deepak Joshi — Revenue Officer
- `rajaswa` — Kamala Thapa — Rajaswa Sakha Pramukh

### Suitable requests

- Revenue collection
- Revenue audits
- Customer payment matters
- Revenue reports
- Revenue-related procurement
- Field revenue activities

### Process

```text
Customer or requester
    ↓
Darta Staff
    ↓
Darta registration
    ↓
Rajaswa Staff
    ↓
Rajaswa Sakha Pramukh
    ↓
Lekha/Budget or Karyalaya authority
    ↓
Karyalaya Pramukh decision
    ↓
Chalani
    ↓
Completed
```

Rajaswa staff verifies revenue facts, payment details, supporting
documents, and financial implications. The Rajaswa Sakha Pramukh may add a
recommendation or tippani and route the request to Lekha, Budget, or the
Karyalaya Pramukh.

## 8. Budget Sakha flow

### Demo user

- `budget` — Prakash Koirala — Budget Sakha Pramukh

The current demo data contains a Budget Sakha Pramukh but no separate Budget
Staff user.

### Suitable requests

- Budget availability
- Expenditure approvals
- Annual program requests
- Capital expenditure
- Procurement funding
- Financial allocation

### Process

```text
Customer or requester
    ↓
Darta Staff
    ↓
Darta registration
    ↓
Originating Sakha
    ↓
Budget Sakha
    ↓
Budget verification
    ↓
Karyalaya Pramukh decision
    ↓
Chalani
    ↓
Completed
```

The Budget Sakha checks:

- Budget availability.
- Correct budget head.
- Reasonableness of the requested amount.
- Capital or operational classification.
- Cost estimates and supporting financial documents.

## 9. Lekha Sakha flow

### Demo user

- `lekha` — Bishnu Sharma — Lekha Pramukh

### Suitable requests

- Financial verification
- Payment processing
- Advance settlement
- Accounting classification
- Expenditure review
- Budget-head verification
- Financial compliance

### Process

```text
Darta Staff
    ↓
Darta registration
    ↓
Relevant Sakha
    ↓
Lekha Sakha
    ↓
Financial verification
    ↓
Karyalaya Pramukh decision
    ↓
Chalani
    ↓
Completed
```

Lekha reviews amounts, calculations, financial documents, quotations,
estimates, budget heads, payment requirements, and compliance.

## 10. Karyalaya Pramukh / Hakim flow

### Demo user

- `karyalaya` — Ramesh Adhikari — Karyalaya Pramukh / Office Head

The Karyalaya Pramukh is the final decision-making authority in the current
workflow.

The Karyalaya Pramukh reviews:

- Sakha recommendations
- Tippani
- Tok Aadesh
- Supporting documents
- Financial verification
- Technical verification
- Customer details
- Complete workflow history

The Karyalaya Pramukh can:

### Approve

```text
Approved → Chalani processing
```

### Reject

```text
Rejected → Final rejected state
```

A rejection reason is required.

### Return for revision

```text
Returned → Requester or Darta corrects the request
```

A return reason is required.

### Issue Tok Aadesh

The Karyalaya Pramukh may issue instructions such as:

- Proceed with the request.
- Obtain additional quotations.
- Conduct a site inspection.
- Attach a technical report.
- Coordinate with another Sakha.
- Use a specified budget head.

## 11. Approval confirmation

After approval, DartaLink provides a printable **Approval confirmation**.

It includes:

- Customer name
- Customer contact
- Request title
- Darta number
- Branch or Sakha
- Requested amount
- Required date
- Decision remarks
- Verifying Sakha authority
- Approving Karyalaya Pramukh
- Darta intake officer
- Chalani number, once assigned

The approval flow is:

```text
Sakha verification
    ↓
Recommendation / Tippani
    ↓
Karyalaya Pramukh approval
    ↓
Approval confirmation generated
    ↓
Chalani processing
```

The confirmation currently displays official signature blocks for the
verifying Sakha authority and approving authority. It is print-ready and can
later be connected to uploaded or cryptographic digital signatures.

## 12. Chalani flow

### Demo users

- `chalani1` — Gita Karki — Chalani Officer
- `chalani2` — Binod Shrestha — Chalani Assistant

### Process

```text
Approved request
    ↓
Chalani Staff receives request
    ↓
Start processing
    ↓
Register Chalani
    ↓
Enter recipient or destination
    ↓
Dispatch document
    ↓
Mark completed
```

Chalani staff:

1. Starts processing the approved request.
2. Enters the office or person receiving the document.
3. Registers the outgoing Chalani record.
4. Dispatches the document.
5. Marks the request completed after dispatch.

The system automatically generates a number such as:

```text
CHALANI-2083/84-0001
```

The system records:

- Chalani number
- Chalani date
- Recipient or destination
- Dispatching staff member
- Completion timestamp

## 13. Returned request flow

A request may be returned when:

- Documents are missing.
- Customer information is incomplete.
- Technical justification is insufficient.
- Budget documents are missing.
- A quotation or estimate is required.
- The request was sent to the wrong Sakha.
- Additional remarks or corrections are required.

```text
Review stage
    ↓
Return for revision
    ↓
Requester or Darta corrects details
    ↓
Resubmit
    ↓
Verification
    ↓
Darta registration
    ↓
Branch review continues
```

The return reason is stored in the workflow history.

## 14. Rejected request flow

A request may be rejected when:

- It is not justified.
- Budget is unavailable.
- The request is outside the office mandate.
- Required conditions are not met.
- The approving authority does not authorize it.

```text
Review
    ↓
Karyalaya Pramukh rejects
    ↓
Rejection reason recorded
    ↓
Final rejected state
```

Rejected requests cannot proceed to Chalani.

## 15. Cancelled request flow

A requester may cancel a request while it is:

- A draft
- Submitted
- Returned for revision

```text
Draft / Submitted / Returned
    ↓
Requester cancels
    ↓
Cancelled
```

A cancelled request cannot be reopened through the normal workflow.

## 16. System Administrator flow

### Demo user

- `admin` — System Administrator

The System Administrator has broad system visibility and manages the
organization's configuration.

The administrator can:

- View all requests.
- View all Darta records.
- View all Chalani records.
- Search across departments.
- Review audit logs.
- Create staff accounts.
- Edit staff accounts.
- Assign roles.
- Assign departments.
- Activate or deactivate staff.
- Manage authority departments.
- Configure registry departments.
- Review workflow activity.
- Access Django administration.
- Access API documentation.

The administrator configures roles, departments, and authorities but does not
normally perform operational Darta, Sakha, or Chalani actions on behalf of
staff.

## 17. Complete end-to-end example

Example: IT equipment procurement.

```text
1. Customer or staff submits a request.
2. Darta staff receives the documents.
3. Darta staff records customer and request details.
4. Darta staff selects IT Sakha.
5. Darta staff submits the request.
6. Darta staff registers the request in Darta.
7. The system generates a Darta number.
8. Darta staff forwards the request to IT.
9. IT staff checks technical requirements.
10. IT Sakha Pramukh verifies the technical need.
11. IT Sakha Pramukh adds a recommendation.
12. Budget or Lekha checks financial details, if required.
13. Karyalaya Pramukh reviews all documents.
14. Karyalaya Pramukh adds Tok Aadesh, if required.
15. Karyalaya Pramukh approves the request.
16. DartaLink generates an approval confirmation.
17. Chalani staff starts processing.
18. Chalani staff generates the Chalani number.
19. The approved document is dispatched.
20. Chalani staff marks the request completed.
```

## 18. Implemented request statuses

The implemented status sequence is:

```text
DRAFT
  ↓
SUBMITTED
  ↓
BRANCH_REVIEW
  ↓
VERIFIED
  ↓
REGISTERED
  ↓
FORWARDED
  ↓
UNDER_REVIEW
  ↓
APPROVED / REJECTED / RETURNED
  ↓
PROCESSING
  ↓
DISPATCHED
  ↓
COMPLETED
```

The system also supports:

```text
CANCELLED
```

for requests cancelled before final processing.

## 19. Role responsibility summary

| Role | Main responsibility |
|---|---|
| Customer | Provides the request, identity, details, and documents |
| Darta Staff | Receives, records, registers, and routes requests |
| Section Staff | Performs technical, financial, revenue, or operational review |
| Sakha Pramukh | Verifies branch-level requests and adds recommendations or tippani |
| Budget Sakha | Checks budget availability and expenditure classification |
| Lekha Sakha | Checks financial and accounting correctness |
| Prabidhik Pramukh | Validates technical and engineering matters |
| Karyalaya Pramukh/Hakim | Makes the final approval, rejection, or return decision |
| Chalani Staff | Registers outward dispatch and sends approved documents |
| System Administrator | Manages users, roles, departments, visibility, and configuration |

## 20. Reference user accounts

| Staff ID | Username | Person | Role | Department |
|---|---|---|---|---|
| `NTC-SA-001` | `admin` | System Administrator | System Administrator | — |
| `NTC-KP-001` | `karyalaya` | Ramesh Adhikari | Karyalaya Pramukh | Karyalaya |
| `NTC-PP-001` | `prabidhik` | Sunita Gurung | Prabidhik Pramukh | Prabidhik |
| `NTC-LP-001` | `lekha` | Bishnu Sharma | Lekha Pramukh | Lekha |
| `NTC-RS-001` | `rajaswa` | Kamala Thapa | Rajaswa Sakha Pramukh | Rajaswa |
| `NTC-BS-001` | `budget` | Prakash Koirala | Budget Sakha Pramukh | Budget |
| `NTC-IT-001` | `itchief` | Anita Rai | IT Sakha Pramukh | IT |
| `NTC-DT-001` | `darta1` | Sita Poudel | Darta Officer | Darta |
| `NTC-DT-002` | `darta2` | Hari Bhandari | Darta Assistant | Darta |
| `NTC-CH-001` | `chalani1` | Gita Karki | Chalani Officer | Chalani |
| `NTC-CH-002` | `chalani2` | Binod Shrestha | Chalani Assistant | Chalani |
| `NTC-IT-002` | `it_staff` | Nabin Lama | System Engineer | IT |
| `NTC-IT-003` | `it_staff2` | Mina Tamang | Network Technician | IT |
| `NTC-RS-002` | `rev_staff` | Deepak Joshi | Revenue Officer | Rajaswa |
| `NTC-PP-002` | `tech_staff` | Rojina Basnet | Engineer | Prabidhik |

All demo users use the configured demo password from the `seed_demo`
management command.
