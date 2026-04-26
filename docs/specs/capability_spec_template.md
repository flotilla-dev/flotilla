# Capability / Subsystem Specification (Generic)

## 1. Executive Summary

-   Describe the purpose of this subsystem
-   Define its role within the application
-   Explain the value it provides

----------

## 2. Architectural Context

-   Describe how this subsystem interacts with others
-   Identify upstream inputs and downstream consumers
-   Define boundaries and ownership within the system

----------

## 3. Responsibilities

-   Define what this subsystem must do
-   Capture the primary behaviors and guarantees
-   Focus on outcomes, not implementation

----------

## 4. Non-Responsibilities

-   Define what this subsystem explicitly does not handle
-   Clarify separation of concerns
-   Prevent overlap with other subsystems

----------

## 5. Core Concepts

-   Define key domain concepts and abstractions
-   Introduce terminology used within this subsystem
-   Provide context needed to understand behavior

----------

## 6. Interaction Model

-   Describe how the subsystem communicates:
    -   Synchronous (request/response)
    -   Asynchronous (events, messaging)
-   Define input/output patterns
-   Clarify invocation and response behavior

----------

## 7. Data Flow

-   Describe how data moves through the subsystem
-   Identify transformations, storage, and outputs
-   Highlight critical data dependencies

----------

## 8. Policies and Rules

-   Define governing rules such as:
    -   Authentication and authorization
    -   Transaction handling
    -   Error handling strategies
-   Capture decisions that shape subsystem behavior

----------

## 9. Technology Decisions

-   Specify technologies used within this subsystem
-   Include frameworks, protocols, or libraries
-   Justify decisions where necessary

----------

## 10. Constraints & Guarantees

-   Define system-level guarantees:
    -   Consistency and ordering
    -   Concurrency behavior
    -   Performance expectations
-   Identify constraints that must be respected

----------

## 11. Observability

-   Define logging, tracing, and metrics expectations
-   Identify key events or signals to monitor
-   Ensure visibility into system behavior and failures

----------

## 12. Related Specifications

-   Reference the Application Specification
-   Reference dependent or related subsystem specs
-   Link to detailed component-level specifications