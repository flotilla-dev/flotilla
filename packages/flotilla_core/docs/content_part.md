# ContentPart Specification (v1.4-draft)

----------

## 1. Executive Summary

### Purpose

`ContentPart` defines the canonical, strongly-typed, immutable content model used across system boundaries.

It provides:

-   A closed, discriminated union of content types
-   Strong typing and validation
-   Deterministic serialization
-   Lossless round-trip reconstruction
    
`ContentPart` is **transport-agnostic** and is designed to operate consistently across:

-   APIs (e.g., HTTP)
-   Durable storage systems
-   Message buses (e.g., Kafka)
-   RPC systems (e.g., gRPC)
    
No transport-specific behavior is encoded in the model.

----------

## 2. Architectural Context

`ContentPart` sits at the shared content boundary for runtime I/O, thread entries, agent events, tools, and transport adapters.

It is used anywhere Flotilla needs to carry user-visible, machine-readable, or externally referenced content without binding that content to a specific transport or storage implementation.

### Design Principles

### 2.1 Canonical IO Contract

`ContentPart` is the **single source of truth** for all system IO.

No alternate representations are permitted.

----------

### 2.2 Strong Typing Over Generic Structures

-   No untyped structures beyond serialization boundaries
-   Each content variant is a concrete class
-   Validation occurs at deserialization time
    
----------

### 2.3 Immutable Data Model

All `ContentPart` instances MUST be immutable after creation.

----------

### 2.4 Closed Type System

The set of supported content types is fixed and explicitly declared.

----------

### 2.5 Semantic Separation

Each content instance MUST fall into exactly one category:

| Category | Description |
|--|--|
| Renderable  | Intended for direct user presentation |
| Structured | Intended for machine interpretation |
| External | References externally stored content |

----------

## 3. Core Concepts

----------

### 3.1 TextPart (Renderable Content)
```python
class  TextPart(ContentPartBase):  
  type: Literal["text"]  
  text: str  
  mime_type: str = "text/plain"
```
#### Semantics

-   Represents human-readable content
-   Intended for rendering
-   MUST NOT be interpreted as structured data
    

#### MIME Type Rules

-   MUST match pattern: `^text/.*`
-   Custom subtypes are allowed

Examples:

-   `text/plain`
-   `text/markdown`
-   `text/html`
-   `text/x-custom`
    
----------

### 3.2 StructuredPart (Machine-Readable Content)

```python
class  StructuredPart(ContentPartBase):  
  type: Literal["structured"]  
  mime_type: str = "application/json"
  data: Any
```
#### Semantics

-   Represents structured data for programmatic use
-   MAY be consumed by runtime, tools, or UI bindings

#### MIME Type Rules

-   MUST match pattern: `^application/.*`
-   Custom types allowed

Examples:

-   `application/json`
-   `application/xml`
-   `application/vnd.custom+json`

#### Data Constraints

-   SHOULD be JSON-serializable; serialization will fail if the value cannot be encoded as JSON
-   SHOULD align with declared `mime_type`
    
----------

### 3.3 FilePart (External Content)
```python
class  FilePart(ContentPartBase):  
  type: Literal["file"]  
  url: str  
  mime_type: str  
  bytes: Optional[int]  
  sha256: Optional[str]
```

#### Semantics

-   Represents externally stored or binary content    
-   Content is not embedded in the system
    
----------

### Base Model

```python
class  ContentPartBase(BaseModel, ABC):  
  type: str  
  id: Optional[str]  
  
  model_config  =  ConfigDict(  
  extra="forbid",  
  frozen=True,  
  use_enum_values=True,  
 )
```
----------

### Discriminated Union

```python
ContentPart  =  Annotated[  
  Union[TextPart, StructuredPart, FilePart],  
  Field(discriminator="type"),  
]
```
## 4. Responsibilities

`ContentPart` is responsible for:

- Providing the canonical content representation across Flotilla boundaries.
- Preserving strong typing for supported content variants.
- Supporting deterministic serialization and deserialization.
- Enforcing validation for known content types.
- Remaining immutable after creation.

## 5. Non-Responsibilities

`ContentPart` is NOT responsible for:

- Defining transport protocols.
- Persisting content to durable storage.
- Fetching external files referenced by `FilePart`.
- Interpreting application-specific structured payloads.
- Providing alternate error or metadata channels.

----------

## 6. Behavioral Contract

### Serialization & Deserialization

----------

### 6.1 Canonical Serialization

Each concrete `ContentPart` MUST implement:

```python
def  serialize(self) -> str
```

#### Requirements

-   MUST return a JSON string representation    
-   MUST be deterministic for equivalent instances
-   MUST exclude undefined or null optional fields unless explicitly required
-   MUST preserve all information required for reconstruction
    
----------

### 6.2 Canonical Deserialization

Each concrete `ContentPart` MUST implement:

```python
@classmethod  
def  deserialize(cls, payload: str) -> Self
```

#### Requirements

-   MUST parse the serialized representation    
-   MUST validate all fields according to schema
-   MUST return a strongly typed instance
-   MUST raise validation errors on failure
    
----------

### 6.3 Static Factory

`ContentPartFactory` MUST expose:
```python
@staticmethod
def deserialize_part(payload: str) -> ContentPart
```

#### Behavior

-   MUST parse payload to extract `type`    
-   MUST reject payloads missing `type`
-   MUST reject unknown `type` values
-   MUST delegate to the corresponding subtype’s `deserialize()` method
-   MUST NOT perform subtype validation itself
    
----------

### 6.4 Round-Trip Guarantee

The following MUST hold:
```python
part  ==  ContentPart.deserialize_part(part.serialize())
```
----------

### 6.5 Prohibited Patterns

The following are NOT allowed:

```python
# ❌ bypass validation  
TextPart(**raw_data)  
  
# ❌ manual discriminator logic  
if  data["type"] == ...  
  
# ❌ partial parsing
```

All deserialization MUST go through the canonical factory.

----------

### Validation Rules

Validation MUST be enforced during deserialization.

----------

### 7.1 Base Validation

| Field | Required | Rule |
|--|--| -- |
| type | Yes | MUST match known discriminator |
| id |  No | MUST be string if present |
| extra fields | Not Allowed | MUST be rejected |

----------

### 7.2 TextPart Validation
| Field | Required | Rule |
|--|--| -- |
| text | Yes | MUST be string |
| mime_type | No | Defaults to `text/plain`; MUST match `^text/.*` if provided |

Invalid examples:
```json
{ "type": "text", "text": 123 }  
{ "type": "text", "text": "hi", "mime_type": "application/json" }
```
----------

### 7.3 StructuredPart Validation
| Field | Required | Rule |
|--|--| -- | 
| mime_type | No | Defaults to `application/json`; MUST match `^application/.*` if provided |
| data | Yes | MUST be JSON-serializable |

Invalid examples:
```json
{ "type": "structured", "mime_type": "text/plain", "data": {} }  
{ "type": "structured", "data": set() }
```
----------

### 7.4 FilePart Validation
| Field | Required | Rule |
|--|--| -- |
| url | Yes | MUST be string |
| mime_type | Yes | MUST be string |
| bytes | No | MUST be ≥ 0 if present |
| sha256 | No | MUST match `[a-fA-F0-9]{64}` |

----------

### 7.5 Error Behavior

Validation failures MUST:

-   Raise a validation exception
-   Include:
    -   field path    
    -   expected vs actual value
    -   human-readable error message
        

Factory failures MUST:

-   Fail fast on:
    -   invalid JSON
    -   missing `type`
    -   unknown `type`
        
----------

## 7. Constraints & Guarantees

The system MUST guarantee:

1.  Deterministic serialization
2.  Lossless round-trip reconstruction
3.  Strong typing at all boundaries
4.  No implicit coercion of invalid data
5.  Immutable instances
    
----------

## 8. Extension Points

New content types MAY be added ONLY if:

-   They preserve semantic separation
-   They implement `serialize()` and `deserialize()`
-   They are registered in the discriminated union
-   They maintain deterministic behavior

## 9. Related Specifications

- `Runtime I/O`
- `Thread Model`
- `AgentEvent`
- `FlotillaTool`
