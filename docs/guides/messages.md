# Building request and response messages

A KMIP message is `RequestMessage` -> `RequestHeader` + one or more `BatchItem`s -> each carries an
`Operation` and a `RequestPayload`. The version-specific classes live in
`model/v1x2/structure/request` and `model/v2x1/structure/request` (KMIP 2.1; 3.0 has its own
`v3x0` header and batch item). Responses mirror them under `.../response`.

## Create request (KMIP 2.1)

```java
KmipInitializer.initialize();
KmipContext.setSpec(KmipSpec.V2_1);

CreateOpRequestPayload payload = CreateOpRequestPayload.builder()
    .objectType(ObjectType.Standard.SYMMETRIC_KEY.inst())
    .attributes(Attributes.builder().build())          // add KmipAttribute values here
    .build();

RequestBatchItem item = RequestBatchItem.builder()
    .operation(Operation.Standard.CREATE.inst())
    .requestPayloadStructure(payload)
    .build();

RequestHeader header = RequestHeader.builder()
    .protocolVersion(ProtocolVersion.of(2, 1))
    .batchCount(BatchCount.of(1))
    .build();

RequestMessage message = RequestMessage.builder()
    .requestHeader(header)
    .requestBatchItem(item)
    .requestBatchItemError(new Exception("placeholder")) // see quirks
    .build();

byte[] wire = KmipCodecManager.createTtlvMapper().writeValueAsBytes(message);
```

JSON output (shortened):

```json
{"tag":"RequestMessage","type":"Structure","value":[
  {"tag":"RequestHeader","type":"Structure","value":[
    {"tag":"ProtocolVersion", ...2.1...},
    {"tag":"BatchCount","type":"Integer","value":1}]},
  {"tag":"BatchItem","type":"Structure","value":[
    {"tag":"Operation","type":"Enumeration","value":"Create"},
    {"tag":"RequestPayload","type":"Structure","value":[
      {"tag":"ObjectType","type":"Enumeration","value":"SymmetricKey"},
      {"tag":"Attributes","type":"Structure","value":[]}]}]}]}
```

Executed by `DocumentationExamplesTest#createRequestMessageForKmip21`, which also reads the
message back in all three formats.

## Reading messages

Read into the **concrete** class for the negotiated version:

```java
RequestMessage back = ttlv.readValue(wire, RequestMessage.class);
```

## Quirks to know

- **Batch item errors.** `RequestMessage` keeps a parallel `List<Exception>` that is never
  serialized, and its constructor requires it to have the same size as the batch item list. Supply
  one placeholder per item when building by hand. Because exceptions compare by identity,
  `message.equals(readBack)` is `false`; compare the re-serialized output instead, as the test does.
- **Do not read through the interface in TTLV.** `ttlv.readValue(bytes, RequestMessageStructure.class)`
  resolves the header with the generic `SimpleRequestHeaderTtlvDeserializer`, which does not know
  `BatchCount`, and fails with `No class registered for tag 4325389`. JSON and XML resolve
  correctly; use the concrete class everywhere.
- **`Simple*` classes** (`SimpleRequestMessage`, ...) are generic scaffolding registered for
  `UnknownVersion` only, with a header that carries just a `ProtocolVersion`. Use the versioned
  classes above for real messages.
- **Version limits.** `BatchCount` is tagged for 1.2 and 2.1 only (not 3.0); `v3x0` has its own
  header and batch item.

## Operation payloads

Payload classes are named `<Operation>Op{Request,Response}Payload` and register against
`(spec, Operation)` via `RequestPayloadStructure.register`. Find the one for your operation:

```bash
ls src/main/java/org/purplebean/kmip/model/v2x1/structure/request/payload
```

Operations added in 1.2 live in `model/v1x2/.../payload`, those added in 3.0 in `model/v3x0/...`.
Known gap: the Query response does not yet include capability, profile and validation information
(see the [roadmap](../roadmap.md)).
