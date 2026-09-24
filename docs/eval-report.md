# Eval Report

- Run ID: `EVAL_10375B81B3`
- Started: `2026-05-01T18:35:06.709496`
- Completed: `2026-05-01T18:35:09.893428`
- Passed: `12/12`

## TC001 - Wrong Document Uploaded

- Passed: `True`
- Expected: `None`
- Actual: `None`
- Member message: `You uploaded PRESCRIPTION, PRESCRIPTION, but this CONSULTATION claim also needs HOSPITAL_BILL. Please re-submit with the missing document type.`

### Trace

- `intake` / `OK`: Claim intake completed. | warnings=[] | error=None
- `member_validation` / `OK`: Policy and member validation completed. | warnings=[] | error=None
- `classification` / `OK`: Document classification completed. | warnings=[] | error=None
- `verification` / `BLOCKED`: Document requirement verification completed. | warnings=[] | error=None

## TC002 - Unreadable Document

- Passed: `True`
- Expected: `None`
- Actual: `None`
- Member message: `The required document blurry_bill.jpg could not be read clearly. Please re-upload a sharper image or PDF of that document.`

### Trace

- `intake` / `OK`: Claim intake completed. | warnings=[] | error=None
- `member_validation` / `OK`: Policy and member validation completed. | warnings=[] | error=None
- `classification` / `OK`: Document classification completed. | warnings=[] | error=None
- `verification` / `BLOCKED`: Document requirement verification completed. | warnings=[] | error=None

## TC003 - Documents Belong to Different Patients

- Passed: `True`
- Expected: `None`
- Actual: `None`
- Member message: `The uploaded documents do not belong to the same person. We found these names: prescription_rajesh.jpg: Rajesh Kumar, bill_arjun.jpg: Arjun Mehta. Please upload documents for a single patient.`

### Trace

- `intake` / `OK`: Claim intake completed. | warnings=[] | error=None
- `member_validation` / `OK`: Policy and member validation completed. | warnings=[] | error=None
- `classification` / `OK`: Document classification completed. | warnings=[] | error=None
- `verification` / `OK`: Document requirement verification completed. | warnings=[] | error=None
- `extraction` / `WARNING`: Document extraction completed. | warnings=['prescription_rajesh.jpg: OCR provider is not configured for binary uploads.', 'bill_arjun.jpg: OCR provider is not configured for binary uploads.'] | error=prescription_rajesh.jpg: OCR provider is not configured for binary uploads.; bill_arjun.jpg: OCR provider is not configured for binary uploads.
- `matching` / `BLOCKED`: Patient normalization and matching completed. | warnings=[] | error=None

## TC004 - Clean Consultation — Full Approval

- Passed: `True`
- Expected: `APPROVED`
- Actual: `APPROVED`
- Member message: `None`

### Trace

- `intake` / `OK`: Claim intake completed. | warnings=[] | error=None
- `member_validation` / `OK`: Policy and member validation completed. | warnings=[] | error=None
- `classification` / `OK`: Document classification completed. | warnings=[] | error=None
- `verification` / `OK`: Document requirement verification completed. | warnings=[] | error=None
- `extraction` / `OK`: Document extraction completed. | warnings=[] | error=None
- `matching` / `OK`: Patient normalization and matching completed. | warnings=[] | error=None
- `rules` / `OK`: Policy adjudication completed. | warnings=[] | error=None
- `fraud` / `OK`: Fraud scoring completed. | warnings=[] | error=None

## TC005 - Waiting Period — Diabetes

- Passed: `True`
- Expected: `REJECTED`
- Actual: `REJECTED`
- Member message: `None`

### Trace

- `intake` / `OK`: Claim intake completed. | warnings=[] | error=None
- `member_validation` / `OK`: Policy and member validation completed. | warnings=[] | error=None
- `classification` / `OK`: Document classification completed. | warnings=[] | error=None
- `verification` / `OK`: Document requirement verification completed. | warnings=[] | error=None
- `extraction` / `OK`: Document extraction completed. | warnings=[] | error=None
- `matching` / `OK`: Patient normalization and matching completed. | warnings=[] | error=None
- `rules` / `OK`: Policy adjudication completed. | warnings=[] | error=None
- `fraud` / `OK`: Fraud scoring completed. | warnings=[] | error=None

## TC006 - Dental Partial Approval — Cosmetic Exclusion

- Passed: `True`
- Expected: `PARTIAL`
- Actual: `PARTIAL`
- Member message: `None`

### Trace

- `intake` / `OK`: Claim intake completed. | warnings=[] | error=None
- `member_validation` / `OK`: Policy and member validation completed. | warnings=[] | error=None
- `classification` / `OK`: Document classification completed. | warnings=[] | error=None
- `verification` / `OK`: Document requirement verification completed. | warnings=[] | error=None
- `extraction` / `OK`: Document extraction completed. | warnings=[] | error=None
- `matching` / `OK`: Patient normalization and matching completed. | warnings=[] | error=None
- `rules` / `OK`: Policy adjudication completed. | warnings=[] | error=None
- `fraud` / `OK`: Fraud scoring completed. | warnings=[] | error=None

## TC007 - MRI Without Pre-Authorization

- Passed: `True`
- Expected: `REJECTED`
- Actual: `REJECTED`
- Member message: `None`

### Trace

- `intake` / `OK`: Claim intake completed. | warnings=[] | error=None
- `member_validation` / `OK`: Policy and member validation completed. | warnings=[] | error=None
- `classification` / `OK`: Document classification completed. | warnings=[] | error=None
- `verification` / `OK`: Document requirement verification completed. | warnings=[] | error=None
- `extraction` / `OK`: Document extraction completed. | warnings=[] | error=None
- `matching` / `OK`: Patient normalization and matching completed. | warnings=[] | error=None
- `rules` / `OK`: Policy adjudication completed. | warnings=[] | error=None
- `fraud` / `OK`: Fraud scoring completed. | warnings=[] | error=None

## TC008 - Per-Claim Limit Exceeded

- Passed: `True`
- Expected: `REJECTED`
- Actual: `REJECTED`
- Member message: `None`

### Trace

- `intake` / `OK`: Claim intake completed. | warnings=[] | error=None
- `member_validation` / `OK`: Policy and member validation completed. | warnings=[] | error=None
- `classification` / `OK`: Document classification completed. | warnings=[] | error=None
- `verification` / `OK`: Document requirement verification completed. | warnings=[] | error=None
- `extraction` / `OK`: Document extraction completed. | warnings=[] | error=None
- `matching` / `OK`: Patient normalization and matching completed. | warnings=[] | error=None
- `rules` / `OK`: Policy adjudication completed. | warnings=[] | error=None
- `fraud` / `OK`: Fraud scoring completed. | warnings=[] | error=None

## TC009 - Fraud Signal — Multiple Same-Day Claims

- Passed: `True`
- Expected: `MANUAL_REVIEW`
- Actual: `MANUAL_REVIEW`
- Member message: `None`

### Trace

- `intake` / `OK`: Claim intake completed. | warnings=[] | error=None
- `member_validation` / `OK`: Policy and member validation completed. | warnings=[] | error=None
- `classification` / `OK`: Document classification completed. | warnings=[] | error=None
- `verification` / `OK`: Document requirement verification completed. | warnings=[] | error=None
- `extraction` / `OK`: Document extraction completed. | warnings=[] | error=None
- `matching` / `OK`: Patient normalization and matching completed. | warnings=[] | error=None
- `rules` / `OK`: Policy adjudication completed. | warnings=[] | error=None
- `fraud` / `WARNING`: Fraud scoring completed. | warnings=['Member exceeded the same-day claim threshold.'] | error=None

## TC010 - Network Hospital — Discount Applied

- Passed: `True`
- Expected: `APPROVED`
- Actual: `APPROVED`
- Member message: `None`

### Trace

- `intake` / `OK`: Claim intake completed. | warnings=[] | error=None
- `member_validation` / `OK`: Policy and member validation completed. | warnings=[] | error=None
- `classification` / `OK`: Document classification completed. | warnings=[] | error=None
- `verification` / `OK`: Document requirement verification completed. | warnings=[] | error=None
- `extraction` / `OK`: Document extraction completed. | warnings=[] | error=None
- `matching` / `OK`: Patient normalization and matching completed. | warnings=[] | error=None
- `rules` / `OK`: Policy adjudication completed. | warnings=[] | error=None
- `fraud` / `OK`: Fraud scoring completed. | warnings=[] | error=None

## TC011 - Component Failure — Graceful Degradation

- Passed: `True`
- Expected: `APPROVED`
- Actual: `APPROVED`
- Member message: `None`

### Trace

- `intake` / `OK`: Claim intake completed. | warnings=[] | error=None
- `member_validation` / `OK`: Policy and member validation completed. | warnings=[] | error=None
- `classification` / `OK`: Document classification completed. | warnings=[] | error=None
- `verification` / `OK`: Document requirement verification completed. | warnings=[] | error=None
- `extraction` / `OK`: Document extraction completed. | warnings=[] | error=None
- `matching` / `WARNING`: Patient normalization and matching completed. | warnings=['Secondary consistency-check agent timed out; cross-document identity verification was partially skipped.'] | error=Consistency-check agent timeout
- `rules` / `OK`: Policy adjudication completed. | warnings=[] | error=None
- `fraud` / `OK`: Fraud scoring completed. | warnings=[] | error=None

## TC012 - Excluded Treatment

- Passed: `True`
- Expected: `REJECTED`
- Actual: `REJECTED`
- Member message: `None`

### Trace

- `intake` / `OK`: Claim intake completed. | warnings=[] | error=None
- `member_validation` / `OK`: Policy and member validation completed. | warnings=[] | error=None
- `classification` / `OK`: Document classification completed. | warnings=[] | error=None
- `verification` / `OK`: Document requirement verification completed. | warnings=[] | error=None
- `extraction` / `OK`: Document extraction completed. | warnings=[] | error=None
- `matching` / `OK`: Patient normalization and matching completed. | warnings=[] | error=None
- `rules` / `OK`: Policy adjudication completed. | warnings=[] | error=None
- `fraud` / `OK`: Fraud scoring completed. | warnings=[] | error=None
