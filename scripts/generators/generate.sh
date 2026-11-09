#!/bin/bash
#
# A unified script to generate KMIP data types, enums, and structures.
#
set -e

# Source the common script from the parent directory
# shellcheck source=../common.sh
source "$(dirname "$0")/../common.sh"

# --- Configuration ---
readonly BASE_DIR="$(pwd)"
readonly MAIN_JAVA="src/main/java/org/purplebean/kmip"
readonly TEST_JAVA="src/test/java/org/purplebean/kmip"
readonly TEMPLATE_BASE_DIR="scripts/generators/templates"
readonly UNIFIED_TEMPLATE_DIR="${TEMPLATE_BASE_DIR}/unified"

# --- Version helpers ---

# Compute SUPPORTED_VERSIONS and DEFAULT_SPEC from a module name.
# Sets variables in the caller's scope.
compute_version_vars() {
    local module="$1"
    case "${module}" in
        "core"|"v1x2")
            SUPPORTED_VERSIONS="Set.of(KmipSpec.UnknownVersion, KmipSpec.V1_2)"
            DEFAULT_SPEC="KmipSpec.V1_2"
            KMIP_VERSION="1.2"
            ;;
        "v1x3")
            SUPPORTED_VERSIONS="Set.of(KmipSpec.UnknownVersion, KmipSpec.V1_3)"
            DEFAULT_SPEC="KmipSpec.V1_3"
            KMIP_VERSION="1.3"
            ;;
        "v1x4")
            SUPPORTED_VERSIONS="Set.of(KmipSpec.UnknownVersion, KmipSpec.V1_4)"
            DEFAULT_SPEC="KmipSpec.V1_4"
            KMIP_VERSION="1.4"
            ;;
        "v2x0")
            SUPPORTED_VERSIONS="Set.of(KmipSpec.UnknownVersion, KmipSpec.V2_0)"
            DEFAULT_SPEC="KmipSpec.V2_0"
            KMIP_VERSION="2.0"
            ;;
        "v2x1")
            SUPPORTED_VERSIONS="Set.of(KmipSpec.UnknownVersion, KmipSpec.V2_1, KmipSpec.V3_0)"
            DEFAULT_SPEC="KmipSpec.V2_1"
            KMIP_VERSION="2.1"
            ;;
        "v3x0")
            SUPPORTED_VERSIONS="Set.of(KmipSpec.UnknownVersion, KmipSpec.V3_0)"
            DEFAULT_SPEC="KmipSpec.V3_0"
            KMIP_VERSION="3.0"
            ;;
        *)
            echo "Warning: Unknown module '${module}', defaulting to core (KMIP 1.2)"
            SUPPORTED_VERSIONS="Set.of(KmipSpec.UnknownVersion, KmipSpec.V1_2)"
            DEFAULT_SPEC="KmipSpec.V1_2"
            KMIP_VERSION="1.2"
            ;;
    esac
}

# --- Main ---
main() {
    if [[ $# -lt 1 ]]; then
        usage
        exit 1
    fi

    local entity_type="$1"
    shift

    case "${entity_type}" in
        "enum")
            generate_enum "$@"
            ;;
        "datatype")
            generate_datatype "$@"
            ;;
        "structure")
            generate_structure "$@"
            ;;
        *)
            echo "Error: Unknown entity type '${entity_type}'"
            usage
            exit 1
            ;;
    esac
}

# --- Usage ---
usage() {
    cat <<EOF
Usage: $0 <entity_type> [options] <Name>

Entity Types:
  enum         - Generate a KMIP enumeration.
  datatype     - Generate a KMIP data type.
  structure    - Generate a KMIP structure.

For entity-specific options, use:
  $0 <entity_type> --help
EOF
}

# --- Unified Generator Functions ---

generate_unified_codec_test() {
    local name="$1" sub_path="$2" format="$3" create_default="$4" create_variant="$5"
    local format_pascal suite_name pdot
    format_pascal=$(get_pascal_case "${format}")
    suite_name="${name}${format_pascal}Test"
    pdot=$(slash_to_dot "${sub_path}")

    render_template "${UNIFIED_TEMPLATE_DIR}/CodecTest.java.template" "${TEST_JAVA}/codec/${format}/${sub_path}/${suite_name}.java" \
        "pdot" "${pdot}" "NAME" "${name}" "format" "${format}" "format_pascal" "${format_pascal}" \
        "suite_name" "${suite_name}" "create_default" "${create_default}" "create_variant" "${create_variant}"
}

generate_unified_benchmark_subject() {
    local name="$1" sub_path="$2" create_default="$3"
    local pdot
    pdot=$(slash_to_dot "${sub_path}")

    render_template "${UNIFIED_TEMPLATE_DIR}/BenchmarkSubject.java.template" "${TEST_JAVA}/benchmark/subjects/${sub_path}/${name}BenchmarkSubject.java" \
        "pdot" "${pdot}" "NAME" "${name}" "create_default" "${create_default}"
    add_service_entry "src/test/resources/META-INF/services/org.purplebean.kmip.benchmark.api.KmipBenchmarkSubject" \
        "org.purplebean.kmip.benchmark.subjects.${pdot}.${name}BenchmarkSubject"
}

generate_unified_serializer() {
    local name="$1" sub_path="$2" format="$3"
    local format_pascal pdot
    format_pascal=$(get_pascal_case "${format}")
    pdot=$(slash_to_dot "${sub_path}")

    render_template "${UNIFIED_TEMPLATE_DIR}/${format_pascal}Serializer.java.template" "${MAIN_JAVA}/codec/${format}/serializer/${sub_path}/${name}${format_pascal}Serializer.java" \
        "pdot" "${pdot}" "NAME" "${name}"
    add_service_entry "src/main/resources/META-INF/services/org.purplebean.kmip.codec.${format}.serializer.api.KmipDataType${format_pascal}Serializer" \
        "org.purplebean.kmip.codec.${format}.serializer.${pdot}.${name}${format_pascal}Serializer"
}

generate_unified_deserializer() {
    local name="$1" sub_path="$2" format="$3" super_call="$4"
    local format_pascal pdot
    format_pascal=$(get_pascal_case "${format}")
    pdot=$(slash_to_dot "${sub_path}")

    render_template "${UNIFIED_TEMPLATE_DIR}/${format_pascal}Deserializer.java.template" "${MAIN_JAVA}/codec/${format}/deserializer/${sub_path}/${name}${format_pascal}Deserializer.java" \
        "pdot" "${pdot}" "NAME" "${name}" "SUPER_CALL" "${super_call}"
    add_service_entry "src/main/resources/META-INF/services/org.purplebean.kmip.codec.${format}.deserializer.api.KmipDataType${format_pascal}Deserializer" \
        "org.purplebean.kmip.codec.${format}.deserializer.${pdot}.${name}${format_pascal}Deserializer"
}


# --- Entity-Specific Generator Functions ---
generate_enum() {
    local TEMPLATE_DIR="${TEMPLATE_BASE_DIR}/enumeration"
    local GEN_CLASS=false GEN_JSON_SER=false GEN_JSON_DES=false GEN_XML_SER=false GEN_XML_DES=false
    local GEN_TTLV_SER=false GEN_TTLV_DES=false GEN_DOMAIN_TEST=false GEN_JSON_TEST=false GEN_XML_TEST=false
    local GEN_TTLV_TEST=false GEN_BENCHMARK=false
    local DRY_RUN="${DRY_RUN:-false}"
    local IF_ATTR=false
    local module="core"
    local sub_package=""

    usage_enum() { cat <<EOF
Usage: $0 enum [options] <Name>
Options:
  -m, --module <module>     Set the module for generation (e.g., 'core', 'v1x2'). Default: 'core'
  -s, --sub-package <pkg>   Set a nested sub-package for generation.
  --attr              Generate an attribute enumeration (changes class and domain test templates)
  --class, --json-ser, --json-des, --xml-ser, --xml-des, --ttlv-ser, --ttlv-des,
  --domain-test, --json-test, --xml-test, --ttlv-test, --benchmark, --all, -h, --help
EOF
    }

    local NAMES=()
    local any_flag=false
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -m|--module) module="$2"; shift; shift ;;
            -s|--sub-package) sub_package="$2"; shift; shift ;;
            --attr) IF_ATTR=true; shift ;;
            --dry-run) DRY_RUN=true; shift ;;
            --class) GEN_CLASS=true; any_flag=true; shift ;;
            --json-ser) GEN_JSON_SER=true; any_flag=true; shift ;;
            --json-des) GEN_JSON_DES=true; any_flag=true; shift ;;
            --xml-ser) GEN_XML_SER=true; any_flag=true; shift ;;
            --xml-des) GEN_XML_DES=true; any_flag=true; shift ;;
            --ttlv-ser) GEN_TTLV_SER=true; any_flag=true; shift ;;
            --ttlv-des) GEN_TTLV_DES=true; any_flag=true; shift ;;
            --domain-test) GEN_DOMAIN_TEST=true; any_flag=true; shift ;;
            --json-test) GEN_JSON_TEST=true; any_flag=true; shift ;;
            --xml-test) GEN_XML_TEST=true; any_flag=true; shift ;;
            --ttlv-test) GEN_TTLV_TEST=true; any_flag=true; shift ;;
            --benchmark) GEN_BENCHMARK=true; any_flag=true; shift ;;
            --all)
                GEN_CLASS=true; GEN_JSON_SER=true; GEN_JSON_DES=true; GEN_XML_SER=true; GEN_XML_DES=true;
                GEN_TTLV_SER=true; GEN_TTLV_DES=true; GEN_DOMAIN_TEST=true; GEN_JSON_TEST=true; GEN_XML_TEST=true;
                GEN_TTLV_TEST=true; GEN_BENCHMARK=true;
                any_flag=true; shift ;;
            -h|--help) usage_enum; return 0 ;;
            *) NAMES[${#NAMES[@]}]="$1"; shift ;;
        esac
    done

    if [[ ${#NAMES[@]} -eq 0 ]]; then echo "Error: at least one enum name required."; usage_enum; return 1; fi
    if [[ "${any_flag}" == "false" ]]; then
        DRY_RUN=true; echo "No generation flags provided -> performing DRY RUN."
        GEN_CLASS=true; GEN_JSON_SER=true; GEN_JSON_DES=true; GEN_XML_SER=true; GEN_XML_DES=true;
        GEN_TTLV_SER=true; GEN_TTLV_DES=true; GEN_DOMAIN_TEST=true; GEN_JSON_TEST=true; GEN_XML_TEST=true;
        GEN_TTLV_TEST=true; GEN_BENCHMARK=true
    fi

    local SUPPORTED_VERSIONS DEFAULT_SPEC KMIP_VERSION
    compute_version_vars "${module}"

    local SUB_PATH="model/${module}"
    if [[ -n "${sub_package}" ]]; then
        SUB_PATH="${SUB_PATH}/enumeration/${sub_package}"
    else
        SUB_PATH="${SUB_PATH}/enumeration"
    fi

    for name in "${NAMES[@]}"; do
        echo -e "\nProcessing enum: ${name}"
        local ENUM_NAME
        ENUM_NAME=$(get_pascal_case "${name}")
        local ENUM_NAME_SNAKE
        ENUM_NAME_SNAKE=$(to_snake_upper "${ENUM_NAME}")
        local pdot
        pdot=$(slash_to_dot "${SUB_PATH}")

        if ${GEN_CLASS}; then
            local class_template
            if ${IF_ATTR}; then
                class_template="${TEMPLATE_BASE_DIR}/attribute/enumeration/AttributeEnum.java.template"
            else
                class_template="${TEMPLATE_DIR}/Enum.java.template"
            fi
            render_template "${class_template}" "${MAIN_JAVA}/${SUB_PATH}/${ENUM_NAME}.java" \
                "pdot" "${pdot}" "ENUM_NAME" "${ENUM_NAME}" "ENUM_NAME_SNAKE" "${ENUM_NAME_SNAKE}" \
                "ATTRIBUTE_NAME" "${ENUM_NAME}" "ATTRIBUTE_NAME_SNAKE" "${ENUM_NAME_SNAKE}" \
                "SUPPORTED_VERSIONS" "${SUPPORTED_VERSIONS}" "DEFAULT_SPEC" "${DEFAULT_SPEC}" \
                "KMIP_VERSION" "${KMIP_VERSION}"
            add_service_entry "src/main/resources/META-INF/services/org.purplebean.kmip.api.KmipDataType" "org.purplebean.kmip.${pdot}.${ENUM_NAME}"
        fi

        if ${GEN_DOMAIN_TEST}; then
            local test_template
            if ${IF_ATTR}; then
                test_template="${TEMPLATE_BASE_DIR}/attribute/enumeration/AttributeEnumTest.java.template"
            else
                test_template="${TEMPLATE_DIR}/EnumTest.java.template"
            fi
            render_template "${test_template}" "${TEST_JAVA}/${SUB_PATH}/${ENUM_NAME}Test.java" \
                "pdot" "${pdot}" "ENUM_NAME" "${ENUM_NAME}" "ATTRIBUTE_NAME" "${ENUM_NAME}" \
                "SUPPORTED_VERSIONS" "${SUPPORTED_VERSIONS}" "DEFAULT_SPEC" "${DEFAULT_SPEC}" \
                "KMIP_VERSION" "${KMIP_VERSION}"
        fi

        local create_default="${ENUM_NAME}.Standard.values()[0].inst()"
        local create_variant="${ENUM_NAME}.Standard.values()[1].inst()"

        if ${GEN_JSON_SER}; then generate_unified_serializer "${ENUM_NAME}" "${SUB_PATH}" "json"; fi
        if ${GEN_JSON_DES}; then generate_unified_deserializer "${ENUM_NAME}" "${SUB_PATH}" "json" "${ENUM_NAME}.fromName(ctxt.readValue(p, String.class))"; fi
        if ${GEN_XML_SER}; then generate_unified_serializer "${ENUM_NAME}" "${SUB_PATH}" "xml"; fi
        if ${GEN_XML_DES}; then generate_unified_deserializer "${ENUM_NAME}" "${SUB_PATH}" "xml" "${ENUM_NAME}.fromName(ctxt.readValue(p, String.class))"; fi
        if ${GEN_TTLV_SER}; then generate_unified_serializer "${ENUM_NAME}" "${SUB_PATH}" "ttlv"; fi
        if ${GEN_TTLV_DES}; then generate_unified_deserializer "${ENUM_NAME}" "${SUB_PATH}" "ttlv" "${ENUM_NAME}.fromValue(mapper.readValue(p, Integer.class))"; fi

        if ${GEN_JSON_TEST}; then generate_unified_codec_test "${ENUM_NAME}" "${SUB_PATH}" "json" "${create_default}" "${create_variant}"; fi
        if ${GEN_XML_TEST}; then generate_unified_codec_test "${ENUM_NAME}" "${SUB_PATH}" "xml" "${create_default}" "${create_variant}"; fi
        if ${GEN_TTLV_TEST}; then generate_unified_codec_test "${ENUM_NAME}" "${SUB_PATH}" "ttlv" "${create_default}" "${create_variant}"; fi
        if ${GEN_BENCHMARK}; then generate_unified_benchmark_subject "${ENUM_NAME}" "${SUB_PATH}" "${create_default}"; fi
    done
    if [ "${DRY_RUN}" = "true" ]; then echo -e "\nDRY RUN complete."; else echo -e "\nGeneration complete."; fi
}

generate_datatype() {
    local TEMPLATE_DIR="${TEMPLATE_BASE_DIR}/datatype"
    local GEN_CLASS=false GEN_JSON_SER=false GEN_JSON_DES=false GEN_XML_SER=false GEN_XML_DES=false
    local GEN_TTLV_SER=false GEN_TTLV_DES=false GEN_DOMAIN_TEST=false GEN_JSON_TEST=false GEN_XML_TEST=false
    local GEN_TTLV_TEST=false GEN_BENCHMARK=false
    local DRY_RUN="${DRY_RUN:-false}"
    local DATA_TYPE="ByteBuffer"
    local IF_ATTR=false
    local module="core"
    local sub_package=""

    usage_datatype() { cat <<EOF
Usage: $0 datatype [options] <Name>
Options:
  -m, --module <module>     Set the module for generation (e.g., 'core', 'v1x2'). Default: 'core'
  -s, --sub-package <pkg>   Set a nested sub-package for generation.
  --attr              Generate an attribute data type (changes class and domain test templates)
  --type <java_type>  The underlying Java type (e.g., Integer, String, ByteBuffer). Default: ByteBuffer
  --class, --json-ser, --json-des, --xml-ser, --xml-des, --ttlv-ser, --ttlv-des,
  --domain-test, --json-test, --xml-test, --ttlv-test, --benchmark, --all, -h, --help
EOF
    }

    local NAMES=()
    local any_flag=false
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -m|--module) module="$2"; shift; shift ;;
            -s|--sub-package) sub_package="$2"; shift; shift ;;
            --attr) IF_ATTR=true; shift ;;
            --type) DATA_TYPE="$2"; shift; shift ;;
            --dry-run) DRY_RUN=true; shift ;;
            --class) GEN_CLASS=true; any_flag=true; shift ;;
            --json-ser) GEN_JSON_SER=true; any_flag=true; shift ;;
            --json-des) GEN_JSON_DES=true; any_flag=true; shift ;;
            --xml-ser) GEN_XML_SER=true; any_flag=true; shift ;;
            --xml-des) GEN_XML_DES=true; any_flag=true; shift ;;
            --ttlv-ser) GEN_TTLV_SER=true; any_flag=true; shift ;;
            --ttlv-des) GEN_TTLV_DES=true; any_flag=true; shift ;;
            --domain-test) GEN_DOMAIN_TEST=true; any_flag=true; shift ;;
            --json-test) GEN_JSON_TEST=true; any_flag=true; shift ;;
            --xml-test) GEN_XML_TEST=true; any_flag=true; shift ;;
            --ttlv-test) GEN_TTLV_TEST=true; any_flag=true; shift ;;
            --benchmark) GEN_BENCHMARK=true; any_flag=true; shift ;;
            --all)
                GEN_CLASS=true; GEN_JSON_SER=true; GEN_JSON_DES=true; GEN_XML_SER=true; GEN_XML_DES=true;
                GEN_TTLV_SER=true; GEN_TTLV_DES=true; GEN_DOMAIN_TEST=true; GEN_JSON_TEST=true; GEN_XML_TEST=true;
                GEN_TTLV_TEST=true; GEN_BENCHMARK=true;
                any_flag=true; shift ;;
            -h|--help) usage_datatype; return 0 ;;
            *) NAMES[${#NAMES[@]}]="$1"; shift ;;
        esac
    done

    if [[ ${#NAMES[@]} -eq 0 ]]; then echo "Error: at least one datatype name required."; usage_datatype; return 1; fi

    local ENCODING_TYPE DEFAULT_VALUE VARIANT_VALUE ATTRIBUTE_VALUE_TYPE
    case "${DATA_TYPE}" in
        "Integer") ENCODING_TYPE="INTEGER"; DEFAULT_VALUE="123"; VARIANT_VALUE="456"; ATTRIBUTE_VALUE_TYPE="Integer";;
        "Long") ENCODING_TYPE="LONG_INTEGER"; DEFAULT_VALUE="12345L"; VARIANT_VALUE="54321L"; ATTRIBUTE_VALUE_TYPE="LongInteger";;
        "BigInteger") ENCODING_TYPE="BIG_INTEGER"; DEFAULT_VALUE='new BigInteger("1234567890")'; VARIANT_VALUE='new BigInteger("9876543210")'; ATTRIBUTE_VALUE_TYPE="BigInteger";;
        "Boolean") ENCODING_TYPE="BOOLEAN"; DEFAULT_VALUE="true"; VARIANT_VALUE="false"; ATTRIBUTE_VALUE_TYPE="Boolean";;
        "String") ENCODING_TYPE="TEXT_STRING"; DEFAULT_VALUE='"default-string"'; VARIANT_VALUE='"variant-string"'; ATTRIBUTE_VALUE_TYPE="TextString";;
        "ByteBuffer") ENCODING_TYPE="BYTE_STRING"; DEFAULT_VALUE="ByteBuffer.wrap(new byte[]{0x01, 0x02, 0x03})"; VARIANT_VALUE="ByteBuffer.wrap(new byte[]{0x04, 0x05, 0x06})"; ATTRIBUTE_VALUE_TYPE="ByteString";;
        "OffsetDateTime") ENCODING_TYPE="DATE_TIME"; DEFAULT_VALUE='OffsetDateTime.of(2024, 1, 2, 3, 4, 5, 0, ZoneOffset.UTC)'; VARIANT_VALUE='OffsetDateTime.of(2025, 1, 2, 3, 4, 5, 0, ZoneOffset.UTC)'; ATTRIBUTE_VALUE_TYPE="DateTime";;
        *) echo "Warning: Unknown data type '${DATA_TYPE}'."; ENCODING_TYPE="UNDEFINED"; DEFAULT_VALUE="null"; VARIANT_VALUE="null"; ATTRIBUTE_VALUE_TYPE="AttributeValue";;
    esac

    if [[ "${any_flag}" == "false" ]]; then
        DRY_RUN=true; echo "No generation flags provided -> performing DRY RUN."
        GEN_CLASS=true; GEN_JSON_SER=true; GEN_JSON_DES=true; GEN_XML_SER=true; GEN_XML_DES=true;
        GEN_TTLV_SER=true; GEN_TTLV_DES=true; GEN_DOMAIN_TEST=true; GEN_JSON_TEST=true; GEN_XML_TEST=true;
        GEN_TTLV_TEST=true; GEN_BENCHMARK=true
    fi

    local SUPPORTED_VERSIONS DEFAULT_SPEC KMIP_VERSION
    compute_version_vars "${module}"

    local SUB_PATH="model/${module}"
    if [[ -n "${sub_package}" ]]; then
        SUB_PATH="${SUB_PATH}/type/${sub_package}"
    else
        SUB_PATH="${SUB_PATH}/type"
    fi

    for name in "${NAMES[@]}"; do
        echo -e "\nProcessing datatype: ${name}"
        local DATA_NAME
        DATA_NAME=$(get_pascal_case "${name}")
        local DATA_NAME_SNAKE
        DATA_NAME_SNAKE=$(to_snake_upper "${DATA_NAME}")
        local pdot
        pdot=$(slash_to_dot "${SUB_PATH}")

        if ${GEN_CLASS}; then
            local class_template
            if ${IF_ATTR}; then
                class_template="${TEMPLATE_BASE_DIR}/attribute/datatype/AttributeDataType.java.template"
            else
                class_template="${TEMPLATE_DIR}/DataType.java.template"
            fi
            render_template "${class_template}" "${MAIN_JAVA}/${SUB_PATH}/${DATA_NAME}.java" \
                "pdot" "${pdot}" "DATA_NAME" "${DATA_NAME}" "DATA_NAME_SNAKE" "${DATA_NAME_SNAKE}" "DATA_TYPE" "${DATA_TYPE}" "ENCODING_TYPE" "${ENCODING_TYPE}" \
                "ATTRIBUTE_NAME" "${DATA_NAME}" "ATTRIBUTE_NAME_SNAKE" "${DATA_NAME_SNAKE}" "ATTRIBUTE_VALUE_TYPE" "${ATTRIBUTE_VALUE_TYPE}" \
                "SUPPORTED_VERSIONS" "${SUPPORTED_VERSIONS}" "DEFAULT_SPEC" "${DEFAULT_SPEC}" "KMIP_VERSION" "${KMIP_VERSION}"
            add_service_entry "src/main/resources/META-INF/services/org.purplebean.kmip.api.KmipDataType" "org.purplebean.kmip.${pdot}.${DATA_NAME}"
        fi

        if ${GEN_DOMAIN_TEST}; then
            local test_template
            if ${IF_ATTR}; then
                test_template="${TEMPLATE_BASE_DIR}/attribute/datatype/AttributeDataTypeTest.java.template"
            else
                test_template="${TEMPLATE_DIR}/DataTypeTest.java.template"
            fi
            render_template "${test_template}" "${TEST_JAVA}/${SUB_PATH}/${DATA_NAME}Test.java" \
                "pdot" "${pdot}" "DATA_NAME" "${DATA_NAME}" "DEFAULT_VALUE" "${DEFAULT_VALUE}" "ENCODING_TYPE" "${ENCODING_TYPE}" "DATA_TYPE" "${DATA_TYPE}" \
                "ATTRIBUTE_NAME" "${DATA_NAME}" \
                "SUPPORTED_VERSIONS" "${SUPPORTED_VERSIONS}" "DEFAULT_SPEC" "${DEFAULT_SPEC}" "KMIP_VERSION" "${KMIP_VERSION}"
        fi

        if ${GEN_JSON_SER}; then generate_unified_serializer "${DATA_NAME}" "${SUB_PATH}" "json"; fi
        if ${GEN_JSON_DES}; then generate_unified_deserializer "${DATA_NAME}" "${SUB_PATH}" "json" "ctxt.readValue(p, ${DATA_TYPE}.class)"; fi
        if ${GEN_XML_SER}; then generate_unified_serializer "${DATA_NAME}" "${SUB_PATH}" "xml"; fi
        if ${GEN_XML_DES}; then generate_unified_deserializer "${DATA_NAME}" "${SUB_PATH}" "xml" "ctxt.readValue(p, ${DATA_TYPE}.class)"; fi
        if ${GEN_TTLV_SER}; then generate_unified_serializer "${DATA_NAME}" "${SUB_PATH}" "ttlv"; fi
        if ${GEN_TTLV_DES}; then generate_unified_deserializer "${DATA_NAME}" "${SUB_PATH}" "ttlv" "mapper.readValue(p, ${DATA_TYPE}.class)"; fi

        local create_default="${DATA_NAME}.of(${DEFAULT_VALUE})"
        local create_variant="${DATA_NAME}.of(${VARIANT_VALUE})"
        if ${GEN_JSON_TEST}; then generate_unified_codec_test "${DATA_NAME}" "${SUB_PATH}" "json" "${create_default}" "${create_variant}"; fi
        if ${GEN_XML_TEST}; then generate_unified_codec_test "${DATA_NAME}" "${SUB_PATH}" "xml" "${create_default}" "${create_variant}"; fi
        if ${GEN_TTLV_TEST}; then generate_unified_codec_test "${DATA_NAME}" "${SUB_PATH}" "ttlv" "${create_default}" "${create_variant}"; fi
        if ${GEN_BENCHMARK}; then generate_unified_benchmark_subject "${DATA_NAME}" "${SUB_PATH}" "${create_default}"; fi
    done
    if [ "${DRY_RUN}" = "true" ]; then echo -e "\nDRY RUN complete."; else echo -e "\nGeneration complete."; fi
}

generate_structure() {
    local TEMPLATE_DIR="${TEMPLATE_BASE_DIR}/structure"
    local GEN_CLASS=false GEN_JSON_SER=false GEN_JSON_DES=false GEN_XML_SER=false GEN_XML_DES=false
    local GEN_TTLV_SER=false GEN_TTLV_DES=false GEN_DOMAIN_TEST=false GEN_JSON_TEST=false GEN_XML_TEST=false
    local GEN_TTLV_TEST=false GEN_BENCHMARK=false
    local DRY_RUN="${DRY_RUN:-false}"
    local IF_ATTR=false
    local module="core"
    local sub_package=""

    usage_structure() { cat <<EOF
Usage: $0 structure [options] <Name>
Options:
  -m, --module <module>     Set the module for generation (e.g., 'core', 'v1x2'). Default: 'core'
  -s, --sub-package <pkg>   Set a nested sub-package for generation.
  --attr              Generate an attribute structure (changes class and domain test templates)
  --class, --json-ser, --json-des, --xml-ser, --xml-des, --ttlv-ser, --ttlv-des,
  --domain-test, --json-test, --xml-test, --ttlv-test, --benchmark, --all, -h, --help
EOF
    }

    local NAMES=()
    local any_flag=false
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -m|--module) module="$2"; shift; shift ;;
            -s|--sub-package) sub_package="$2"; shift; shift ;;
            --attr) IF_ATTR=true; shift ;;
            --dry-run) DRY_RUN=true; shift ;;
            --class) GEN_CLASS=true; any_flag=true; shift ;;
            --json-ser) GEN_JSON_SER=true; any_flag=true; shift ;;
            --json-des) GEN_JSON_DES=true; any_flag=true; shift ;;
            --xml-ser) GEN_XML_SER=true; any_flag=true; shift ;;
            --xml-des) GEN_XML_DES=true; any_flag=true; shift ;;
            --ttlv-ser) GEN_TTLV_SER=true; any_flag=true; shift ;;
            --ttlv-des) GEN_TTLV_DES=true; any_flag=true; shift ;;
            --domain-test) GEN_DOMAIN_TEST=true; any_flag=true; shift ;;
            --json-test) GEN_JSON_TEST=true; any_flag=true; shift ;;
            --xml-test) GEN_XML_TEST=true; any_flag=true; shift ;;
            --ttlv-test) GEN_TTLV_TEST=true; any_flag=true; shift ;;
            --benchmark) GEN_BENCHMARK=true; any_flag=true; shift ;;
            --all)
                GEN_CLASS=true; GEN_JSON_SER=true; GEN_JSON_DES=true; GEN_XML_SER=true; GEN_XML_DES=true;
                GEN_TTLV_SER=true; GEN_TTLV_DES=true; GEN_DOMAIN_TEST=true; GEN_JSON_TEST=true; GEN_XML_TEST=true;
                GEN_TTLV_TEST=true; GEN_BENCHMARK=true;
                any_flag=true; shift ;;
            -h|--help) usage_structure; return 0 ;;
            *) NAMES[${#NAMES[@]}]="$1"; shift ;;
        esac
    done

    if [[ ${#NAMES[@]} -eq 0 ]]; then echo "Error: at least one structure name required."; usage_structure; return 1; fi
    if [[ "${any_flag}" == "false" ]]; then
        DRY_RUN=true; echo "No generation flags provided -> performing DRY RUN."
        GEN_CLASS=true; GEN_JSON_SER=true; GEN_JSON_DES=true; GEN_XML_SER=true; GEN_XML_DES=true;
        GEN_TTLV_SER=true; GEN_TTLV_DES=true; GEN_DOMAIN_TEST=true; GEN_JSON_TEST=true; GEN_XML_TEST=true;
        GEN_TTLV_TEST=true; GEN_BENCHMARK=true
    fi

    local SUPPORTED_VERSIONS DEFAULT_SPEC KMIP_VERSION
    compute_version_vars "${module}"

    local SUB_PATH="model/${module}"
    if [[ -n "${sub_package}" ]]; then
        SUB_PATH="${SUB_PATH}/structure/${sub_package}"
    else
        SUB_PATH="${SUB_PATH}/structure"
    fi

    for name in "${NAMES[@]}"; do
        echo -e "\nProcessing structure: ${name}"
        local STRUCTURE_NAME
        STRUCTURE_NAME=$(get_pascal_case "${name}")
        local STRUCTURE_NAME_SNAKE
        STRUCTURE_NAME_SNAKE=$(to_snake_upper "${STRUCTURE_NAME}")
        local varname
        varname=$(get_camel_case "${STRUCTURE_NAME}")
        local pdot
        pdot=$(slash_to_dot "${SUB_PATH}")

        if ${GEN_CLASS}; then
            local class_template
            if ${IF_ATTR}; then
                class_template="${TEMPLATE_BASE_DIR}/attribute/structure/AttributeStructure.java.template"
            else
                class_template="${TEMPLATE_DIR}/Structure.java.template"
            fi
            render_template "${class_template}" "${MAIN_JAVA}/${SUB_PATH}/${STRUCTURE_NAME}.java" \
                "pdot" "${pdot}" "STRUCTURE_NAME" "${STRUCTURE_NAME}" "STRUCTURE_NAME_SNAKE" "${STRUCTURE_NAME_SNAKE}" \
                "ATTRIBUTE_NAME" "${STRUCTURE_NAME}" "ATTRIBUTE_NAME_SNAKE" "${STRUCTURE_NAME_SNAKE}" \
                "SUPPORTED_VERSIONS" "${SUPPORTED_VERSIONS}" "DEFAULT_SPEC" "${DEFAULT_SPEC}" "KMIP_VERSION" "${KMIP_VERSION}"
            add_service_entry "src/main/resources/META-INF/services/org.purplebean.kmip.api.KmipDataType" "org.purplebean.kmip.${pdot}.${STRUCTURE_NAME}"
        fi

        if ${GEN_DOMAIN_TEST}; then
            local test_template
            if ${IF_ATTR}; then
                test_template="${TEMPLATE_BASE_DIR}/attribute/structure/AttributeStructureTest.java.template"
            else
                test_template="${TEMPLATE_DIR}/StructureTest.java.template"
            fi
            render_template "${test_template}" "${TEST_JAVA}/${SUB_PATH}/${STRUCTURE_NAME}Test.java" \
                "pdot" "${pdot}" "STRUCTURE_NAME" "${STRUCTURE_NAME}" "ATTRIBUTE_NAME" "${STRUCTURE_NAME}" \
                "SUPPORTED_VERSIONS" "${SUPPORTED_VERSIONS}" "DEFAULT_SPEC" "${DEFAULT_SPEC}" "KMIP_VERSION" "${KMIP_VERSION}"
        fi

        if ${GEN_JSON_SER}; then generate_unified_serializer "${STRUCTURE_NAME}" "${SUB_PATH}" "json"; fi
        if ${GEN_JSON_DES}; then
            render_template "${TEMPLATE_DIR}/StructureJsonDeserializer.java.template" "${MAIN_JAVA}/codec/json/deserializer/${SUB_PATH}/${STRUCTURE_NAME}JsonDeserializer.java" \
                "pdot" "${pdot}" "STRUCTURE_NAME" "${STRUCTURE_NAME}" "varname" "${varname}"
            add_service_entry "src/main/resources/META-INF/services/org.purplebean.kmip.codec.json.deserializer.api.KmipDataTypeJsonDeserializer" \
                "org.purplebean.kmip.codec.json.deserializer.${pdot}.${STRUCTURE_NAME}JsonDeserializer"
        fi
        if ${GEN_XML_SER}; then generate_unified_serializer "${STRUCTURE_NAME}" "${SUB_PATH}" "xml"; fi
        if ${GEN_XML_DES}; then
            render_template "${TEMPLATE_DIR}/StructureXmlDeserializer.java.template" "${MAIN_JAVA}/codec/xml/deserializer/${SUB_PATH}/${STRUCTURE_NAME}XmlDeserializer.java" \
                "pdot" "${pdot}" "STRUCTURE_NAME" "${STRUCTURE_NAME}" "varname" "${varname}"
            add_service_entry "src/main/resources/META-INF/services/org.purplebean.kmip.codec.xml.deserializer.api.KmipDataTypeXmlDeserializer" \
                "org.purplebean.kmip.codec.xml.deserializer.${pdot}.${STRUCTURE_NAME}XmlDeserializer"
        fi
        if ${GEN_TTLV_SER}; then generate_unified_serializer "${STRUCTURE_NAME}" "${SUB_PATH}" "ttlv"; fi
        if ${GEN_TTLV_DES}; then
            render_template "${TEMPLATE_DIR}/StructureTtlvDeserializer.java.template" "${MAIN_JAVA}/codec/ttlv/deserializer/${SUB_PATH}/${STRUCTURE_NAME}TtlvDeserializer.java" \
                "pdot" "${pdot}" "STRUCTURE_NAME" "${STRUCTURE_NAME}" "varname" "${varname}"
            add_service_entry "src/main/resources/META-INF/services/org.purplebean.kmip.codec.ttlv.deserializer.api.KmipDataTypeTtlvDeserializer" \
                "org.purplebean.kmip.codec.ttlv.deserializer.${pdot}.${STRUCTURE_NAME}TtlvDeserializer"
        fi

        local create_default_struct="${STRUCTURE_NAME}.builder().build()"
        local create_variant_struct="${STRUCTURE_NAME}.builder().build()"
        if ${GEN_JSON_TEST}; then generate_unified_codec_test "${STRUCTURE_NAME}" "${SUB_PATH}" "json" "${create_default_struct}" "${create_variant_struct}"; fi
        if ${GEN_XML_TEST}; then generate_unified_codec_test "${STRUCTURE_NAME}" "${SUB_PATH}" "xml" "${create_default_struct}" "${create_variant_struct}"; fi
        if ${GEN_TTLV_TEST}; then generate_unified_codec_test "${STRUCTURE_NAME}" "${SUB_PATH}" "ttlv" "${create_default_struct}" "${create_variant_struct}"; fi
        if ${GEN_BENCHMARK}; then generate_unified_benchmark_subject "${STRUCTURE_NAME}" "${SUB_PATH}" "${create_default_struct}"; fi
    done
    if [ "${DRY_RUN}" = "true" ]; then echo -e "\nDRY RUN complete."; else echo -e "\nGeneration complete."; fi
}

# --- Entrypoint ---
main "$@"
