# Serialization

Three codecs, all registered through Jackson-style modules and built by `KmipCodecManager`:

| Format | Factory | Mapper type | Module |
|---|---|---|---|
| JSON | `createJsonMapper()` | `JsonMapper` | `KmipJsonModule` |
| XML | `createXmlMapper()` | `XmlMapper` | `KmipXmlModule` |
| TTLV | `createTtlvMapper()` | `TtlvMapper` (project class) | `KmipTtlvModule` |

JSON and XML mappers also register `JavaTimeModule` and disable `WRITE_DATES_AS_TIMESTAMPS`.
`KmipCodecManager.getJsonMapper()/getXmlMapper()/getTtlvMapper()` return lazily created shared
instances. Mappers read the spec from `KmipContext` at call time, so set it first.

## Wire shapes

`ProtocolVersion 1.2` in each format (verified by `DocumentationExamplesTest`):

**JSON** (KMIP JSON profile: `tag`, `type`, `value`)

```json
{"tag":"ProtocolVersion","type":"Structure","value":[
  {"tag":"ProtocolVersionMajor","type":"Integer","value":1},
  {"tag":"ProtocolVersionMinor","type":"Integer","value":2}]}
```

**XML** (KMIP XML profile: tag is the element name, `type` and `value` attributes)

```xml
<ProtocolVersion><ProtocolVersionMajor type="Integer" value="1"/><ProtocolVersionMinor type="Integer" value="2"/></ProtocolVersion>
```

**TTLV** (hex)

```
420069 01 00000020                 ProtocolVersion, Structure, 32 bytes
  42006a 02 00000004 00000001 00000000   ProtocolVersionMajor, Integer, 1 (+4 pad)
  42006b 02 00000004 00000002 00000000   ProtocolVersionMinor, Integer, 2 (+4 pad)
```

Value conventions:

| KMIP type | JSON / XML value | Notes |
|---|---|---|
| Enumeration | description string (`"Active"`) | TTLV uses the integer |
| Date-Time | ISO-8601 with offset (`2026-01-02T03:04:05+00:00`) | Java `OffsetDateTime`; equality of `ActivationDate` ignores sub-second precision |
| Byte String | hex (JSON/XML), raw bytes (TTLV) | |
| Integer / Long / Big Integer / Boolean / Text String | native | |

## TTLV API

```java
TtlvMapper ttlv = KmipCodecManager.createTtlvMapper();
byte[] bytes = ttlv.writeValueAsBytes(value);          // or writeValueAsByteBuffer
T back = ttlv.readValue(bytes, T.class);               // byte[] or ByteBuffer
```

`TtlvObject.fromBuffer(buffer)` parses raw TTLV into a tree; `getStructuredByteString()` prints
it indented (used by `Main`). Unrecognized vendor tags inside a message extension are handled by
`TtlvDataType`.

## Convenience API

`KmipCodecManager.serialize(obj)` / `deserialize(value, type)` use `defaultType` (`XML` by
default, settable) and **escape** the output (`escapeXml11` / `escapeJson`), so the result is for
embedding in another document, not for sending as KMIP. `TTLV` is not implemented there and throws
`IllegalArgumentException`. Prefer the mappers directly.

## How a type is wired into a codec

Per type and per format there is a serializer and a deserializer in
`codec/<format>/{serializer,deserializer}/model/<v>/<kind>/`, named
`<Type><Format>Serializer` / `<Type><Format>Deserializer`. Each is listed in a
`META-INF/services/...` file for its format (`KmipDataType<Format>Serializer`,
`...Deserializer`), and `Kmip<Format>Module` loads them. Structure serializers usually inherit
everything from an abstract base; structure deserializers implement a `setValue` switch on child
tag. [Extending](extending.md) shows how the generator creates all of this.
