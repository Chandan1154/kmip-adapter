# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ExceptionInInitializerError` / `NoClassDefFoundError: Could not initialize class ...` with a cause like `Value 'ClientRegistrationMethod' for KmipTag is not supported for KMIP spec V1.2` | A type was first loaded while the thread's spec was already set; registration runs in static initializers under the current spec | Call `KmipInitializer.initialize()` (or touch `KmipCodecManager`) before `KmipContext.setSpec`. The failed class stays broken for the JVM's life, so restart. See [Versioning](versioning.md) |
| `IllegalArgumentException: Unsupported object type for V1.0: KmipTag(...)` | The type is not tagged for the current spec | Set the right spec, or check the type's `supportedVersions` |
| Works in one thread, `UnknownVersion` behaviour in another | `KmipContext` is a `ThreadLocal`; executors do not inherit it | Set the spec inside each task, clear in `finally` |
| `NoSuchElementException: No State value found for 'X' in KMIP spec V2.1` | Enum name/integer not supported in the current spec, or an extension value that was never registered | Register vendor values at startup before reading data; verify the spec |
| `NoSuchElementException: No class registered for tag N and encoding type T` | Type not in `META-INF/services/org.purplebean.kmip.api.KmipDataType`, not tagged for this spec, or (TTLV) read through a message *interface* | Check the SPI file; read into the concrete class ([Messages](messages.md#quirks-to-know)) |
| `IllegalArgumentException: requestBatchItems and requestBatchItemErrors must have the same size` | `RequestMessage`/`Simple*` validate a parallel error list | Add one placeholder error per batch item ([Messages](messages.md#quirks-to-know)) |
| `IllegalArgumentException: Extension value ... must be in range` | Vendor enum values must be `0x80000000`-`0xFFFFFFFF`; vendor tags `0x540000`-`0x54FFFF` | Use a value in the right range |
| `mvn test` fails in `validate` with hundreds of checkstyle errors | New generated code is not Google-style | See [First contribution](first-contribution.md#5-make-it-pass-checkstyle); use `-Dcheckstyle.skip` only while iterating |
| Generator output does not compile: `cannot find symbol ... KmipTag.Standard.X` | The tag is not defined | Add it to `KmipTag` first |
| A new type is silently ignored when reading | Missing from an SPI file | Re-run the generator or add the class name to each file ([Architecture](architecture.md#wiring-how-a-type-becomes-known)) |
| `KmipCodecManager.serialize(...)` output looks escaped | It escapes XML/JSON by design and rejects TTLV | Use the mappers directly ([Serialization](serialization.md)) |
