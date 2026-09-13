# ChainSignal — Event Taxonomy

## EventType taxonomy

**Version:** 1

Supported V1 values:

- `EARTHQUAKE`
- `FLOOD`
- `CONFLICT`
- `PROTEST`
- `STRIKE`

An external provider's category must be explicitly mapped into this controlled taxonomy by the Python normalization layer.

Unsupported event types must not be silently mapped to `OTHER`. They remain preserved in raw/Bronze data and are quarantined/rejected from canonical risk processing until support is intentionally added.

## Severity taxonomy

**Version:** 1

- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

Canonical severity is a normalized business-readable classification. Provider-specific measures such as earthquake magnitude may remain as selected canonical metadata while the complete provider payload stays in raw/Bronze storage.

## Versioning rule

Taxonomy changes must be documented with:

- new version
- reason for change
- compatibility impact
- normalization changes required
- downstream impact

Canonical schema version and taxonomy documentation version are separate concepts and do not need to increase together for every change.
