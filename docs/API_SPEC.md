# API Specification

## Controller and Intent APIs

- `POST /api/intent/submit`
  - submit high-level intent
  - accepts JSON or form data
- `POST /api/context/update`
  - publish monitoring or ML context
  - accepts JSON or form data
- `GET /api/network/hosts`
  - return discovered hosts
- `GET /api/network/topology`
  - return controller, switches, links, services, and alert state
- `POST /api/flow/install`
  - install a manual OpenFlow-compatible rule
  - accepts JSON or form data
- `POST /api/flow/delete`
  - delete a manual controller rule
  - accepts JSON or form data

## Monitoring and ML APIs

- `POST /api/ml/predict`
  - run prediction on telemetry metrics
  - accepts JSON or form data
- `POST /api/v1/component-2/telemetry`
  - integrated telemetry pipeline
- `POST /api/v1/component-2/models/train`
  - train bundled ML models

## Security APIs

- `POST /api/v1/auth/login`
  - operator password step
- `POST /api/v1/auth/verify-otp`
  - QR / TOTP verification step
- `POST /auth/login`
  - compatibility session login for component 4 auth flow
- `POST /auth/verify`
  - compatibility session verification
- `POST /api/v1/component-4/cti/alert`
  - Suricata-style alert ingestion

## SDN Runtime APIs

- `POST /api/v1/sdn/events`
  - ingest runtime events from Ryu, Mininet, or automation
- `GET /api/v1/sdn/status`
  - live SDN, monitoring, and OpenStack status
- `POST /api/v1/sdn/start`
  - start Linux SDN lab
- `POST /api/v1/openstack/deploy`
  - deploy OpenStack control plane on supported Linux runtime

## Notes

- The compatibility APIs are intentionally tolerant so Postman, curl, forms, and GUI calls do not fail with strict body-shape errors.
- The authoritative integrated APIs remain under `/api/v1/...`.
