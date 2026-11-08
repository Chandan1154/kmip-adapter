# Glossary

| Term | Meaning |
|---|---|
| **KMIP** | Key Management Interoperability Protocol (OASIS standard) for clients to manage cryptographic objects on a key server |
| **Managed object** | A server-held object: symmetric/private/public key, certificate, secret data, opaque data, split key, PGP key, template |
| **Attribute** | Named metadata of a managed object (Activation Date, State, Name, ...). Capabilities such as client-modifiable are in the spec's attribute tables |
| **Operation** | A request type: Create, Get, Register, Locate, Query, ... Each has a request and a response payload |
| **Message / batch item** | A request or response message holds a header and one or more batch items; each batch item is one operation |
| **Payload** | The operation-specific content of a batch item |
| **Tag** | 3-byte identifier of an element (`0x420069` = Protocol Version). Standard tags are `0x42xxxx`; vendor extensions `0x54xxxx` |
| **TTLV** | Tag-Type-Length-Value, KMIP's binary encoding. Items are padded to 8-byte multiples |
| **Item type / encoding type** | Structure, Integer, Long Integer, Big Integer, Enumeration, Boolean, Text String, Byte String, Date-Time, Interval, ... (`EncodingType`) |
| **Structure** | An item whose value is an ordered list of child items |
| **Enumeration** | Integer-valued item with named values per tag; `0x8xxxxxxx` is reserved for extensions |
| **Mask** | Integer bit field (e.g. Cryptographic Usage Mask) |
| **Spec / profile version** | A KMIP release (1.0-1.4, 2.0, 2.1, 3.0). `KmipSpec` in this library |
| **`UnknownVersion`** | The default `KmipContext` spec; used for spec-independent types and generic scaffolding |
| **Standard / Extension** | Spec-defined enum values (`Standard`) versus vendor values registered at runtime (`Extension`) |
| **SPI file** | A `META-INF/services/...` file listing classes the library loads at startup |
| **Gap report** | `docs/kmip-pending-implementation.md`: generated comparison of the spec against the code |
