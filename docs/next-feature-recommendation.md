# Next Feature Recommendation: Post-Booking Ratings & Reviews

## Why this should be next
Kinshields already has strong trust and safety foundations (verification levels, monitored messages, incident reports, disputes, panic alerts, and geofence check-ins), but it lacks one core marketplace trust signal: **outcome-based feedback after completed services**.

A structured ratings + reviews system would:
- help families choose based on real service quality,
- reward high-performing caregivers,
- improve match quality over time,
- and reduce support load by surfacing quality trends early.

## Evidence from current codebase
- The home page explicitly lists **"Caregiver Ratings"** as an upcoming feature, which makes it a natural near-term priority.
- Caregiver list/search currently exposes availability, verification, experience, and rate—but no user feedback signal.
- Booking lifecycle and safety telemetry already exist, so ratings can be tied to real completed bookings (mitigating fake reviews).

## Proposed scope (MVP)
1. **Family-to-caregiver reviews**
   - Allow review creation only when booking status is `released`.
   - One review per booking.
   - Fields: overall rating (1–5), punctuality (1–5), communication (1–5), cleanliness/professionalism (1–5), optional text feedback.

2. **Caregiver public reputation summary**
   - Show average rating and total review count on:
     - caregiver cards (`profile_list`),
     - caregiver detail page.

3. **Moderation controls**
   - `is_visible` toggle for admins.
   - optional `flagged` boolean + reason for sensitive/abusive reviews.

4. **Safety linkage**
   - If a review includes very low ratings (e.g., <=2 overall), prompt family to optionally file an incident report.

## Data model proposal
Create new app model (or place in `families`):

- `CaregiverReview`
  - `booking` (OneToOne -> `families.Booking`)
  - `family` (FK -> `families.FamilyProfile`)
  - `caregiver` (FK -> `caregivers.CaregiverProfile`)
  - `overall_rating` (PositiveSmallIntegerField 1–5)
  - `punctuality_rating` (1–5)
  - `communication_rating` (1–5)
  - `professionalism_rating` (1–5)
  - `comment` (TextField, blank)
  - `is_visible` (Boolean, default True)
  - `flagged` / `flag_reason` (optional moderation fields)
  - timestamps

## Rollout order
1. Model + migration + admin.
2. Review form/view on completed booking screen.
3. Aggregate annotations in caregiver list/detail queries.
4. Minimal moderation workflow.
5. Tests for permissions, one-review-per-booking, and aggregate stats rendering.

## Success metrics
- % of released bookings with reviews submitted.
- Lift in caregiver profile-to-booking conversion.
- Drop in first-contact churn (families messaging but not booking).
- Correlation of low-rated caregivers with disputes (for proactive intervention).
