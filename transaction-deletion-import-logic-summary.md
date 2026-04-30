# Transaction Deletion CSV Import Logic - Updated Behavior

## Auto-Detection of Company Field

When importing a CSV without a `company_field` column or with empty values, the system uses smart auto-detection:

### Priority Order:

1. **"company" field** (most common convention)
   - Check if a field named `company` exists that links to Company DocType
   - ✅ Use "company" if found

2. **First Company link field** (custom fields)
   - If no "company" field, get all fields linking to Company DocType
   - ✅ Use the first one (sorted by field index)

3. **No company field** (DocTypes without company filtering)
   - If no Company link fields exist at all
   - ✅ Leave `company_field` as None/empty
   - ✅ Delete ALL records (no company filtering)

## Import CSV Format

### Minimal Format (Auto-Detection)
```csv
doctype_name,child_doctypes
Sales Order,Sales Order Item
Note,
Task,
```

**Result:**
- `Sales Order`: Auto-detects "company" field → Filters by company
- `Note`: No company field → Deletes all Note records
- `Task`: Has "company" field → Filters by company

### Explicit Format (Recommended)
```csv
doctype_name,company_field,child_doctypes
Sales Order,company,Sales Order Item
Sales Contract,primary_company,Sales Contract Item
Sales Contract,billing_company,Sales Contract Item
Note,,
```

**Result:**
- `Sales Order`: Uses "company" field explicitly
- `Sales Contract` (row 1): Uses "primary_company" field
- `Sales Contract` (row 2): Uses "billing_company" field (separate row!)
- `Note`: No company field, deletes all records

### Multiple Company Fields Example
```csv
doctype_name,company_field,child_doctypes
Customer Invoice,head_office,Customer Invoice Item
Customer Invoice,billing_company,Customer Invoice Item
```

**Deletion Process:**
1. Row 1 deletes: `WHERE head_office = 'ABC Company'`
2. Row 2 deletes: `WHERE billing_company = 'ABC Company'`
3. Documents with both fields = ABC get deleted in first pass
4. Documents with only billing_company = ABC get deleted in second pass

## Validation Rules

### ✅ Accepted Cases

1. **DocType with "company" field** - Auto-detected
2. **DocType with custom Company link field** - Auto-detected (first field used)
3. **DocType with multiple Company fields** - Auto-detected (first field used), but user can add multiple rows
4. **DocType with NO Company fields** - Accepted! Deletes ALL records
5. **Explicit company_field provided** - Validated and used

### ❌ Rejected Cases

1. **Protected DocTypes** - User, Role, DocType, etc.
2. **Child tables** - Auto-deleted with parent
3. **Virtual DocTypes** - No database table
4. **Invalid company_field** - Field doesn't exist or isn't a Company link
5. **DocType doesn't exist** - Not found in system

## Code Flow

```python
# 1. Read company_field from CSV (may be empty)
company_field = row.get("company_field", "").strip()

# 2. Auto-detect if not provided
if not company_field:
    # Try "company" first
    if exists("company" field linking to Company):
        company_field = "company"
    else:
        # Check for other Company link fields
        company_fields = get_all_company_link_fields()
        if company_fields:
            company_field = company_fields[0]  # Use first
        # else: company_field stays empty

# 3. Validate if company_field was provided/detected
if company_field:
    if not is_valid_company_link_field(company_field):
        skip_with_error()

# 4. Count documents
if company_field:
    count = count(WHERE company_field = self.company)
else:
    count = count(all records)

# 5. Store in To Delete list
append({
    "doctype_name": doctype_name,
    "company_field": company_field or None,  # Store None if empty
    "document_count": count
})
```

## Examples

### Example 1: Standard DocType with "company" Field

**CSV:**
```csv
doctype_name,company_field,child_doctypes
Sales Order,,
```

**Auto-Detection:**
- Finds "company" field linking to Company
- Sets `company_field = "company"`
- Counts: `WHERE company = 'Test Company'`
- Result: Deletes only Test Company's Sales Orders

### Example 2: Custom Company Field

**CSV:**
```csv
doctype_name,company_field,child_doctypes
Project Contract,,
```

**Auto-Detection:**
- No "company" field found
- Finds "contracting_company" field linking to Company
- Sets `company_field = "contracting_company"`
- Counts: `WHERE contracting_company = 'Test Company'`
- Result: Deletes only Test Company's Project Contracts

### Example 3: No Company Field (Global DocType)

**CSV:**
```csv
doctype_name,company_field,child_doctypes
Note,,
Global Settings,,
```

**Auto-Detection:**
- No Company link fields found
- Sets `company_field = None`
- Counts: All records
- Result: Deletes ALL Note and Global Settings records

### Example 4: Multiple Company Fields (Explicit)

**CSV:**
```csv
doctype_name,company_field,child_doctypes
Sales Contract,primary_company,Sales Contract Item
Sales Contract,billing_company,Sales Contract Item
```

**No Auto-Detection:**
- Row 1: Uses "primary_company" explicitly
- Row 2: Uses "billing_company" explicitly
- Both rows validated as valid Company link fields
- Result: Two separate deletion passes

### Example 5: Mixed Approaches

**CSV:**
```csv
doctype_name,company_field,child_doctypes
Sales Order,,Sales Order Item
Sales Contract,billing_company,Sales Contract Item
Note,,
```

**Result:**
- Row 1: Auto-detects "company" field
- Row 2: Uses "billing_company" explicitly
- Row 3: No company field (deletes all)

## User Benefits

✅ **Flexible**: Supports auto-detection and explicit specification
✅ **Safe**: Validates all fields before processing
✅ **Clear**: Empty company_field means "delete all"
✅ **Powerful**: Can target specific company fields in multi-company setups
✅ **Backward Compatible**: Old CSVs (without company_field column) still work

## Migration from Old Format

**Old CSV (without company_field):**
```csv
doctype_name,child_doctypes
Sales Order,Sales Order Item
```

**New System Behavior:**
- Auto-detects "company" field
- Works identically to before
- ✅ Backward compatible

**New CSV (with company_field):**
```csv
doctype_name,company_field,child_doctypes
Sales Order,company,Sales Order Item
```

**Benefits:**
- Explicit and clear
- Supports multiple rows per DocType
- Can specify custom company fields

---

*Generated for Transaction Deletion Record enhancement*
