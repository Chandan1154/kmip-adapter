# Examples

All samples run in `DocumentationExamplesTest`. Common setup:

```java
KmipInitializer.initialize();           // once, before any setSpec
KmipContext.setSpec(KmipSpec.V1_2);     // per thread; clear() when done
var json = KmipCodecManager.createJsonMapper();
var xml  = KmipCodecManager.createXmlMapper();
var ttlv = KmipCodecManager.createTtlvMapper();
```

## 1. Round trip in JSON, XML and TTLV

```java
ProtocolVersion version = ProtocolVersion.of(1, 2);

String jsonText = json.writeValueAsString(version);
version.equals(json.readValue(jsonText, ProtocolVersion.class));   // true

String xmlText = xml.writeValueAsString(version);
version.equals(xml.readValue(xmlText, ProtocolVersion.class));     // true

byte[] bytes = ttlv.writeValueAsBytes(version);
HexFormat.of().formatHex(bytes);
// 420069010000002042006a0200000004000000010000000042006b02000000040000000200000000
version.equals(ttlv.readValue(bytes, ProtocolVersion.class));      // true
```

## 2. Enumerations, including vendor extensions

```java
State active = State.Standard.ACTIVE.inst();
json.writeValueAsString(active);
// {"tag":"State","type":"Enumeration","value":"Active"}
xml.writeValueAsString(active);
// <State type="Enumeration" value="Active"/>

State quarantined = State.register(0x80000001, "Quarantined", Set.of(KmipSpec.V1_2)).inst();
String text = json.writeValueAsString(quarantined);   // ... "value":"Quarantined"
json.readValue(text, State.class).equals(quarantined); // true
```

Register extension values at startup, before reading data that contains them.

## 3. Primitive types and attributes

```java
ActivationDate date =
    ActivationDate.of(OffsetDateTime.of(2026, 1, 2, 3, 4, 5, 0, ZoneOffset.UTC));
json.writeValueAsString(date);
// {"tag":"ActivationDate","type":"DateTime","value":"2026-01-02T03:04:05+00:00"}

// Generic KMIP 1.x Attribute structure wrapping the typed value
Attribute attribute = Attribute.builder()
    .attributeName(date.getAttributeName())          // "Activation Date"
    .attributeIndex(AttributeIndex.of(0))
    .attributeValue(date.getAttributeValue())
    .build();
json.writeValueAsString(attribute);
// {"tag":"Attribute","type":"Structure","value":[
//   {"tag":"AttributeName","type":"TextString","value":"Activation Date"},
//   {"tag":"AttributeIndex","type":"Integer","value":0},
//   {"tag":"AttributeValue","type":"DateTime","value":"2026-01-02T03:04:05+00:00"}]}

// Back to the typed attribute
ActivationDate.of(attribute.getAttributeName(), attribute.getAttributeValue()).equals(date); // true
```

## 4. Scoping the spec version

```java
KmipContext.getSpec();                                   // UnknownVersion on a fresh thread
KmipSpec inside = KmipContext.withSpec(KmipSpec.V2_1, KmipContext::getSpec);   // V2.1
KmipContext.getSpec();                                   // UnknownVersion again

KmipContext.setSpec(KmipSpec.V1_0);
ActivationDate.of(OffsetDateTime.now());
// IllegalArgumentException: Unsupported object type for V1.0: KmipTag(...ACTIVATION_DATE...)
```

## 5. Per-request context in a web handler

```java
Object handle(byte[] body, KmipSpec negotiated) throws IOException {
  KmipContext.setSpec(negotiated);       // pool threads do not inherit it
  try {
    return KmipCodecManager.getTtlvMapper().readValue(body, ProtocolVersion.class);
  } finally {
    KmipContext.clear();
  }
}
```

(Illustrative; not executed. It uses only APIs shown above.)

## Generating more samples

`AllFormatsSerializationTest` serializes every registered benchmark subject and writes
`build/reports/kmip/serialization.md` (JSON, XML and TTLV hex side by side). Run it to see real
output for any type: `mvn test -Dtest=AllFormatsSerializationTest`.
