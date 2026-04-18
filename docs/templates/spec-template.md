# {ID}: {Feature Name}

**Status**: Spec | **Created**: {YYYY-MM-DD} | **Author**: {author}
**F-xxx Mapping**: {F-xxx ID and name} | **Phase**: {Phase X - Name} | **Priority**: {Critical/High/Medium/Low}

---

## 1. Overview

**Problem**: {One-sentence problem statement}

**Solution**: {One-sentence solution description}

**Goals**: {Measurable outcomes, e.g., "+25% daily consumption"}

**Non-Goals**: {What this feature explicitly does NOT do}

---

## 2. Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | {Functional requirement 1} | P0 |
| FR-2 | {Functional requirement 2} | P0 |
| FR-3 | {Functional requirement 3} | P1 |
| NFR-1 | {Non-functional requirement 1} | P0 |
| NFR-2 | {Non-functional requirement 2} | P0 |

---

## 3. User Story / Behavior

{As a {user type}, I want to {action}, so that {benefit}.}

### Key Behaviors

- {Behavior 1}
- {Behavior 2}
- {Behavior 3}

---

## 4. Data Models

### New Tables

**{table_name}**: {field1}, {field2}, {field3}...

### Existing Used

- `{TableName}` ({purpose})
- `{TableName}` ({purpose})

---

## 5. API Design

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/path/to/resource` | GET | Get resources |
| `/path/to/resource` | POST | Create resource |
| `/path/to/{id}` | PUT | Update resource |
| `/path/to/{id}` | DELETE | Delete resource |

### Request/Response Examples

**Request:**
```json
{
  "field": "value"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "field": "value"
}
```

---

## 6. Implementation

### Files

- `{path/to/file.py}` - {purpose}
- `{path/to/file.py}` - {purpose}

### Key Logic

1. {Step 1}
2. {Step 2}
3. {Step 3}

### Dependencies

**Requires** (satisfied by):
- {ID} - {brief description}

**Provides** (for future):
- {ID or feature} - {brief description}

---

## 7. Edge Cases

| Scenario | Handling |
|----------|----------|
| {Edge case 1} | {How it's handled} |
| {Edge case 2} | {How it's handled} |
| {Edge case 3} | {How it's handled} |

---

## 8. Testing

- **Unit**: {What unit tests cover}
- **Integration**: {What integration tests cover}
- **Acceptance**: {Key acceptance criteria}

---

## 9. Sensory Verification

- **Visual (시각)**: {What should be seen - UI rendering, system state, DB content}
- **Auditory (청각)**: {What should be logged - errors, API responses, events}
- **Tactile (촉각)**: {What should feel right - workflow completion, latency, interaction}

---

## 10. Future Enhancements

1. {Future enhancement 1}
2. {Future enhancement 2}
3. {Future enhancement 3}

---

## 11. References

- {Related spec: [ID.md](specs/ID.md)}
- {External reference: [Title](URL)}
