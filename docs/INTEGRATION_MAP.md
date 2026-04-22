# Integration Map

## Component mapping

- **Component 1** contributes the hybrid Round Robin + Genetic Algorithm resource optimizer and flow-management concepts.
- **Component 2** contributes monitoring, visualization, telemetry features, and ML-driven policy recommendations.
- **Component 3** contributes the intent-based SDN controller concepts, DFPS prioritization, host discovery, and compatibility REST endpoints.
- **Component 4** contributes continuous authentication, micro-segmentation, CTI ingestion, and mitigation workflows.

## Implemented integration pattern

1. Monitoring and ML publish context to `/api/v1/context`.
2. The resource optimizer publishes backend weights to `/api/v1/resource-plans`.
3. Security services publish block/quarantine actions to `/api/v1/security-actions`.
4. Manual intents are submitted to `/api/v1/intents` or the compatibility path `/api/intent/submit`.
5. The orchestration engine decides the highest-priority action and records the result in the state store.

## Priority order

1. security actions (`block`, `quarantine`)
2. manual intents
3. ML recommendations
4. optimizer plans
5. default observe-only mode
