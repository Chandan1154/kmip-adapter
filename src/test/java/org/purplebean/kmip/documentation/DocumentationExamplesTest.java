package org.purplebean.kmip.documentation;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.HexFormat;
import java.util.Set;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.purplebean.kmip.api.KmipContext;
import org.purplebean.kmip.api.KmipInitializer;
import org.purplebean.kmip.api.KmipSpec;
import org.purplebean.kmip.codec.KmipCodecManager;
import org.purplebean.kmip.model.core.enumeration.ObjectType;
import org.purplebean.kmip.model.core.enumeration.Operation;
import org.purplebean.kmip.model.core.enumeration.State;
import org.purplebean.kmip.model.core.structure.Attribute;
import org.purplebean.kmip.model.core.structure.ProtocolVersion;
import org.purplebean.kmip.model.core.type.ActivationDate;
import org.purplebean.kmip.model.core.type.AttributeIndex;
import org.purplebean.kmip.model.core.type.BatchCount;
import org.purplebean.kmip.model.v2x1.structure.Attributes;
import org.purplebean.kmip.model.v2x1.structure.request.RequestBatchItem;
import org.purplebean.kmip.model.v2x1.structure.request.RequestHeader;
import org.purplebean.kmip.model.v2x1.structure.request.RequestMessage;
import org.purplebean.kmip.model.v2x1.structure.request.payload.CreateOpRequestPayload;

/**
 * Executes the code samples shown in {@code README.md} and {@code docs/guides/examples.md}, so the
 * documentation fails the build when the API drifts. Keep this class in sync with those files.
 */
class DocumentationExamplesTest {

  @BeforeAll
  static void initializeTypes() {
    // Registration runs in static initializers under the current spec, so do it before setSpec.
    KmipContext.clear();
    KmipInitializer.initialize();
  }

  @AfterEach
  void clearContext() {
    KmipContext.clear();
  }

  @Test
  void roundTripInAllThreeFormats() throws Exception {
    KmipContext.setSpec(KmipSpec.V1_2);
    ProtocolVersion version = ProtocolVersion.of(1, 2);

    var json = KmipCodecManager.createJsonMapper();
    String jsonText = json.writeValueAsString(version);
    assertThat(jsonText).isEqualTo(
        "{\"tag\":\"ProtocolVersion\",\"type\":\"Structure\",\"value\":["
            + "{\"tag\":\"ProtocolVersionMajor\",\"type\":\"Integer\",\"value\":1},"
            + "{\"tag\":\"ProtocolVersionMinor\",\"type\":\"Integer\",\"value\":2}]}");
    assertThat(json.readValue(jsonText, ProtocolVersion.class)).isEqualTo(version);

    var xml = KmipCodecManager.createXmlMapper();
    String xmlText = xml.writeValueAsString(version);
    assertThat(xmlText).isEqualTo(
        "<ProtocolVersion><ProtocolVersionMajor type=\"Integer\" value=\"1\"/>"
            + "<ProtocolVersionMinor type=\"Integer\" value=\"2\"/></ProtocolVersion>");
    assertThat(xml.readValue(xmlText, ProtocolVersion.class)).isEqualTo(version);

    var ttlv = KmipCodecManager.createTtlvMapper();
    byte[] bytes = ttlv.writeValueAsBytes(version);
    assertThat(HexFormat.of().formatHex(bytes)).isEqualTo(
        "420069010000002042006a0200000004000000010000000042006b02000000040000000200000000");
    assertThat(ttlv.readValue(bytes, ProtocolVersion.class)).isEqualTo(version);
  }

  @Test
  void enumerationsAndExtensionValues() throws Exception {
    KmipContext.setSpec(KmipSpec.V1_2);
    var json = KmipCodecManager.createJsonMapper();

    State active = State.Standard.ACTIVE.inst();
    assertThat(json.writeValueAsString(active))
        .isEqualTo("{\"tag\":\"State\",\"type\":\"Enumeration\",\"value\":\"Active\"}");

    State quarantined =
        State.register(0x80000001, "Quarantined", Set.of(KmipSpec.V1_2)).inst();
    String text = json.writeValueAsString(quarantined);
    assertThat(text).contains("\"value\":\"Quarantined\"");
    assertThat(json.readValue(text, State.class)).isEqualTo(quarantined);
  }

  @Test
  void attributesWrapTypedValues() throws Exception {
    KmipContext.setSpec(KmipSpec.V1_2);
    ActivationDate date =
        ActivationDate.of(OffsetDateTime.of(2026, 1, 2, 3, 4, 5, 0, ZoneOffset.UTC));

    Attribute attribute = Attribute.builder()
        .attributeName(date.getAttributeName())
        .attributeIndex(AttributeIndex.of(0))
        .attributeValue(date.getAttributeValue())
        .build();

    var json = KmipCodecManager.createJsonMapper();
    String text = json.writeValueAsString(attribute);
    assertThat(text).contains("\"value\":\"Activation Date\"");
    assertThat(json.readValue(text, Attribute.class)).isEqualTo(attribute);

    assertThat(ActivationDate.of(attribute.getAttributeName(), attribute.getAttributeValue()))
        .isEqualTo(date);
  }

  @Test
  void contextScopesTheSpecVersion() {
    assertThat(KmipContext.getSpec()).isEqualTo(KmipSpec.UnknownVersion);

    KmipSpec inside = KmipContext.withSpec(KmipSpec.V2_1, KmipContext::getSpec);
    assertThat(inside).isEqualTo(KmipSpec.V2_1);
    assertThat(KmipContext.getSpec()).isEqualTo(KmipSpec.UnknownVersion);

    KmipContext.setSpec(KmipSpec.V1_0);
    assertThatThrownBy(() -> ActivationDate.of(OffsetDateTime.now()))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("Unsupported object type for V1.0");
  }

  @Test
  void createRequestMessageForKmip21() throws Exception {
    KmipContext.setSpec(KmipSpec.V2_1);

    CreateOpRequestPayload payload = CreateOpRequestPayload.builder()
        .objectType(ObjectType.Standard.SYMMETRIC_KEY.inst())
        .attributes(Attributes.builder().build())
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
        .requestBatchItemError(new Exception("placeholder"))
        .build();

    var json = KmipCodecManager.createJsonMapper();
    String jsonText = json.writeValueAsString(message);
    assertThat(jsonText).contains("\"tag\":\"Operation\",\"type\":\"Enumeration\","
        + "\"value\":\"Create\"");
    RequestMessage fromJson = json.readValue(jsonText, RequestMessage.class);
    assertThat(json.writeValueAsString(fromJson)).isEqualTo(jsonText);

    var xml = KmipCodecManager.createXmlMapper();
    String xmlText = xml.writeValueAsString(message);
    assertThat(xmlText).startsWith("<RequestMessage><RequestHeader>");
    assertThat(xml.writeValueAsString(xml.readValue(xmlText, RequestMessage.class)))
        .isEqualTo(xmlText);

    var ttlv = KmipCodecManager.createTtlvMapper();
    byte[] bytes = ttlv.writeValueAsBytes(message);
    assertThat(ttlv.writeValueAsBytes(ttlv.readValue(bytes, RequestMessage.class)))
        .isEqualTo(bytes);
  }
}
