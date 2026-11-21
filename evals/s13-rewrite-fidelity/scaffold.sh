#!/usr/bin/env bash
set -euo pipefail
mkdir -p docs/img
cat > docs/consumer-config.md <<'MD'
# Consumer configuration

The consumer reads messages from a queue and hands them to your handler, and how it does this is controlled by a few settings that you can pass either as flags to `qconsume run` or as environment variables, where the environment variable wins if both are set, which is the opposite of what most people expect, so be careful. The prefetch count, set with `--prefetch=32` or `QCONSUME_PREFETCH`, is how many messages the consumer fetches ahead of your handler; the default is 32 and values above 500 are rejected at start-up. The maximum number of messages processed at the same time is `--max-inflight=64` (`QCONSUME_MAX_INFLIGHT`), default 64, and it must not be lower than the prefetch count or the consumer will refuse to start with `error: max-inflight < prefetch`. When a handler fails, the message is retried with exponential backoff starting at 2 s and capped at 5 min, up to `--max-retries=8` times (`QCONSUME_MAX_RETRIES`), after which it goes to the dead-letter queue, which is described in [Dead-letter queue](../ops/dlq.md); the retry flow is shown below.

![Retry flow from failure to dead-letter queue](img/retry-flow.png)

> **Warning:** setting `QCONSUME_ACK_MODE=auto` acknowledges messages before your handler runs, so a crash loses them. Use `manual` (the default) unless losing messages is acceptable.

| Setting | Flag | Environment variable | Default |
|---|---|---|---|
| Prefetch | `--prefetch` | `QCONSUME_PREFETCH` | 32 |
| Max in flight | `--max-inflight` | `QCONSUME_MAX_INFLIGHT` | 64 |
| Max retries | `--max-retries` | `QCONSUME_MAX_RETRIES` | 8 |
| Ack mode | `--ack-mode` | `QCONSUME_ACK_MODE` | manual |

To check the effective configuration run `qconsume config show`, which prints every setting with its source (flag, env or default).
MD
