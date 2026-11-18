# Choosing a diagram

A diagram earns its place when the reader must hold several elements and their relationships in mind at once. Name
the diagram by its notation, type and level: a precise name is what lets a tool or skill that draws that notation
recognise the work.

## Situation → diagram

| The text explains | Diagram |
|---|---|
| An exchange between several participants over time: a request across services, an authentication handshake, a callback with retries | UML sequence diagram |
| The lifecycle of one thing: states, events, transitions (an order, a delivery, a subscription) | UML state machine diagram |
| Steps with decisions, loops or parallel branches inside one system or algorithm | UML activity diagram |
| A business process across roles or organisations, with hand-offs, events, timers | BPMN 2.0 process diagram (collaboration diagram when several organisations take part) |
| The system, its users and the external systems it depends on | C4 System Context diagram |
| The applications, services and data stores of a system and how they communicate | C4 Container diagram |
| The parts inside one application or service | C4 Component diagram |
| A runtime scenario across C4 elements | C4 Dynamic diagram |
| Where the software runs: nodes, environments, networks | UML deployment diagram, or C4 Deployment diagram |
| Stored data: entities, keys, cardinalities | ERD in crow's foot notation |
| The concepts of a domain and their relationships | UML class diagram of the domain model |
| Data crossing trust boundaries (security or privacy review) | Data-flow diagram with trust boundaries |

When the project already uses a notation for this kind of content, use it.

## When not to draw

- Three elements or fewer, or a straight sequence of steps with no branches or loops: a numbered list says it.
- Facts with no connections between them (attributes, options, error codes): a table says it. A table of states
  or steps is not a substitute when the reader needs to see the transitions, loops or branches between them.
- Reference docs for a single member: the contract is text.
- Class diagrams of DTOs or of code that changes often: they go stale with every change.
- To decorate: a diagram the text doesn't need will not be maintained.

## User diagrams and contributor diagrams

- A diagram in user text shows only what the user can see or act on: their system, the product's API, observable
  states and events. Never internal services, queues, hosts, data stores or project IDs.
- Contributor diagrams may show internals and cite requirement and decision IDs.
- Every diagram has a text equivalent: the prose around it, or alt text that states its point.

## Brief

Write the brief before drawing; it is also what you hand over when you can't draw.

```markdown
Diagram: UML state machine diagram — subscription lifecycle
Audience: account owners (user text, user guide > Billing > Subscriptions)
Question it answers: what happens to a subscription when a payment fails, and how to get it back
Elements: states trial, active, past due, suspended, cancelled
Transitions: trial → active (first payment succeeds); active → past due (renewal payment fails);
  past due → active (payment succeeds within 14 days); past due → suspended (14 days without payment);
  suspended → active (overdue amount paid); any state → cancelled (owner cancels)
Leave out: internal components, queues and storage
```

## Drawing it

- If a skill or tool available to you produces this notation, use it with the brief. Put the result in the
  project's existing diagram format and location, next to the text it supports.
- Otherwise give the brief to the user in your reply. Don't leave a placeholder or a TODO in the document: the text
  must read fine without the diagram.
