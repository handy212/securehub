// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'alarm_event.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

AlarmEvent _$AlarmEventFromJson(Map<String, dynamic> json) {
  return _AlarmEvent.fromJson(json);
}

/// @nodoc
mixin _$AlarmEvent {
  String get id => throw _privateConstructorUsedError;
  String get eventType =>
      throw _privateConstructorUsedError; // Classification fields added in backend migration 0004
  String get eventCategory => throw _privateConstructorUsedError;
  String get severity => throw _privateConstructorUsedError;
  String get occurredAt => throw _privateConstructorUsedError;
  String get siteName => throw _privateConstructorUsedError;
  String? get subsystem => throw _privateConstructorUsedError;
  String? get subsystemName => throw _privateConstructorUsedError;
  String? get zone => throw _privateConstructorUsedError;
  String? get zoneName => throw _privateConstructorUsedError;
  int? get zoneNumber => throw _privateConstructorUsedError;
  String? get zoneDetectorType => throw _privateConstructorUsedError;
  bool get hasMedia =>
      throw _privateConstructorUsedError; // Acknowledgement state
  bool get acknowledged => throw _privateConstructorUsedError;
  String? get acknowledgedAt => throw _privateConstructorUsedError;
  String? get performedBy => throw _privateConstructorUsedError;
  Map<String, dynamic> get payload => throw _privateConstructorUsedError;

  /// Serializes this AlarmEvent to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of AlarmEvent
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $AlarmEventCopyWith<AlarmEvent> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $AlarmEventCopyWith<$Res> {
  factory $AlarmEventCopyWith(
    AlarmEvent value,
    $Res Function(AlarmEvent) then,
  ) = _$AlarmEventCopyWithImpl<$Res, AlarmEvent>;
  @useResult
  $Res call({
    String id,
    String eventType,
    String eventCategory,
    String severity,
    String occurredAt,
    String siteName,
    String? subsystem,
    String? subsystemName,
    String? zone,
    String? zoneName,
    int? zoneNumber,
    String? zoneDetectorType,
    bool hasMedia,
    bool acknowledged,
    String? acknowledgedAt,
    String? performedBy,
    Map<String, dynamic> payload,
  });
}

/// @nodoc
class _$AlarmEventCopyWithImpl<$Res, $Val extends AlarmEvent>
    implements $AlarmEventCopyWith<$Res> {
  _$AlarmEventCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of AlarmEvent
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? eventType = null,
    Object? eventCategory = null,
    Object? severity = null,
    Object? occurredAt = null,
    Object? siteName = null,
    Object? subsystem = freezed,
    Object? subsystemName = freezed,
    Object? zone = freezed,
    Object? zoneName = freezed,
    Object? zoneNumber = freezed,
    Object? zoneDetectorType = freezed,
    Object? hasMedia = null,
    Object? acknowledged = null,
    Object? acknowledgedAt = freezed,
    Object? performedBy = freezed,
    Object? payload = null,
  }) {
    return _then(
      _value.copyWith(
            id: null == id
                ? _value.id
                : id // ignore: cast_nullable_to_non_nullable
                      as String,
            eventType: null == eventType
                ? _value.eventType
                : eventType // ignore: cast_nullable_to_non_nullable
                      as String,
            eventCategory: null == eventCategory
                ? _value.eventCategory
                : eventCategory // ignore: cast_nullable_to_non_nullable
                      as String,
            severity: null == severity
                ? _value.severity
                : severity // ignore: cast_nullable_to_non_nullable
                      as String,
            occurredAt: null == occurredAt
                ? _value.occurredAt
                : occurredAt // ignore: cast_nullable_to_non_nullable
                      as String,
            siteName: null == siteName
                ? _value.siteName
                : siteName // ignore: cast_nullable_to_non_nullable
                      as String,
            subsystem: freezed == subsystem
                ? _value.subsystem
                : subsystem // ignore: cast_nullable_to_non_nullable
                      as String?,
            subsystemName: freezed == subsystemName
                ? _value.subsystemName
                : subsystemName // ignore: cast_nullable_to_non_nullable
                      as String?,
            zone: freezed == zone
                ? _value.zone
                : zone // ignore: cast_nullable_to_non_nullable
                      as String?,
            zoneName: freezed == zoneName
                ? _value.zoneName
                : zoneName // ignore: cast_nullable_to_non_nullable
                      as String?,
            zoneNumber: freezed == zoneNumber
                ? _value.zoneNumber
                : zoneNumber // ignore: cast_nullable_to_non_nullable
                      as int?,
            zoneDetectorType: freezed == zoneDetectorType
                ? _value.zoneDetectorType
                : zoneDetectorType // ignore: cast_nullable_to_non_nullable
                      as String?,
            hasMedia: null == hasMedia
                ? _value.hasMedia
                : hasMedia // ignore: cast_nullable_to_non_nullable
                      as bool,
            acknowledged: null == acknowledged
                ? _value.acknowledged
                : acknowledged // ignore: cast_nullable_to_non_nullable
                      as bool,
            acknowledgedAt: freezed == acknowledgedAt
                ? _value.acknowledgedAt
                : acknowledgedAt // ignore: cast_nullable_to_non_nullable
                      as String?,
            performedBy: freezed == performedBy
                ? _value.performedBy
                : performedBy // ignore: cast_nullable_to_non_nullable
                      as String?,
            payload: null == payload
                ? _value.payload
                : payload // ignore: cast_nullable_to_non_nullable
                      as Map<String, dynamic>,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$AlarmEventImplCopyWith<$Res>
    implements $AlarmEventCopyWith<$Res> {
  factory _$$AlarmEventImplCopyWith(
    _$AlarmEventImpl value,
    $Res Function(_$AlarmEventImpl) then,
  ) = __$$AlarmEventImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    String id,
    String eventType,
    String eventCategory,
    String severity,
    String occurredAt,
    String siteName,
    String? subsystem,
    String? subsystemName,
    String? zone,
    String? zoneName,
    int? zoneNumber,
    String? zoneDetectorType,
    bool hasMedia,
    bool acknowledged,
    String? acknowledgedAt,
    String? performedBy,
    Map<String, dynamic> payload,
  });
}

/// @nodoc
class __$$AlarmEventImplCopyWithImpl<$Res>
    extends _$AlarmEventCopyWithImpl<$Res, _$AlarmEventImpl>
    implements _$$AlarmEventImplCopyWith<$Res> {
  __$$AlarmEventImplCopyWithImpl(
    _$AlarmEventImpl _value,
    $Res Function(_$AlarmEventImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of AlarmEvent
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? eventType = null,
    Object? eventCategory = null,
    Object? severity = null,
    Object? occurredAt = null,
    Object? siteName = null,
    Object? subsystem = freezed,
    Object? subsystemName = freezed,
    Object? zone = freezed,
    Object? zoneName = freezed,
    Object? zoneNumber = freezed,
    Object? zoneDetectorType = freezed,
    Object? hasMedia = null,
    Object? acknowledged = null,
    Object? acknowledgedAt = freezed,
    Object? performedBy = freezed,
    Object? payload = null,
  }) {
    return _then(
      _$AlarmEventImpl(
        id: null == id
            ? _value.id
            : id // ignore: cast_nullable_to_non_nullable
                  as String,
        eventType: null == eventType
            ? _value.eventType
            : eventType // ignore: cast_nullable_to_non_nullable
                  as String,
        eventCategory: null == eventCategory
            ? _value.eventCategory
            : eventCategory // ignore: cast_nullable_to_non_nullable
                  as String,
        severity: null == severity
            ? _value.severity
            : severity // ignore: cast_nullable_to_non_nullable
                  as String,
        occurredAt: null == occurredAt
            ? _value.occurredAt
            : occurredAt // ignore: cast_nullable_to_non_nullable
                  as String,
        siteName: null == siteName
            ? _value.siteName
            : siteName // ignore: cast_nullable_to_non_nullable
                  as String,
        subsystem: freezed == subsystem
            ? _value.subsystem
            : subsystem // ignore: cast_nullable_to_non_nullable
                  as String?,
        subsystemName: freezed == subsystemName
            ? _value.subsystemName
            : subsystemName // ignore: cast_nullable_to_non_nullable
                  as String?,
        zone: freezed == zone
            ? _value.zone
            : zone // ignore: cast_nullable_to_non_nullable
                  as String?,
        zoneName: freezed == zoneName
            ? _value.zoneName
            : zoneName // ignore: cast_nullable_to_non_nullable
                  as String?,
        zoneNumber: freezed == zoneNumber
            ? _value.zoneNumber
            : zoneNumber // ignore: cast_nullable_to_non_nullable
                  as int?,
        zoneDetectorType: freezed == zoneDetectorType
            ? _value.zoneDetectorType
            : zoneDetectorType // ignore: cast_nullable_to_non_nullable
                  as String?,
        hasMedia: null == hasMedia
            ? _value.hasMedia
            : hasMedia // ignore: cast_nullable_to_non_nullable
                  as bool,
        acknowledged: null == acknowledged
            ? _value.acknowledged
            : acknowledged // ignore: cast_nullable_to_non_nullable
                  as bool,
        acknowledgedAt: freezed == acknowledgedAt
            ? _value.acknowledgedAt
            : acknowledgedAt // ignore: cast_nullable_to_non_nullable
                  as String?,
        performedBy: freezed == performedBy
            ? _value.performedBy
            : performedBy // ignore: cast_nullable_to_non_nullable
                  as String?,
        payload: null == payload
            ? _value._payload
            : payload // ignore: cast_nullable_to_non_nullable
                  as Map<String, dynamic>,
      ),
    );
  }
}

/// @nodoc

@JsonSerializable(fieldRename: FieldRename.snake)
class _$AlarmEventImpl implements _AlarmEvent {
  const _$AlarmEventImpl({
    this.id = '',
    this.eventType = '',
    this.eventCategory = 'info',
    this.severity = 'low',
    this.occurredAt = '',
    this.siteName = '',
    this.subsystem,
    this.subsystemName,
    this.zone,
    this.zoneName,
    this.zoneNumber,
    this.zoneDetectorType,
    this.hasMedia = false,
    this.acknowledged = false,
    this.acknowledgedAt,
    this.performedBy,
    final Map<String, dynamic> payload = const {},
  }) : _payload = payload;

  factory _$AlarmEventImpl.fromJson(Map<String, dynamic> json) =>
      _$$AlarmEventImplFromJson(json);

  @override
  @JsonKey()
  final String id;
  @override
  @JsonKey()
  final String eventType;
  // Classification fields added in backend migration 0004
  @override
  @JsonKey()
  final String eventCategory;
  @override
  @JsonKey()
  final String severity;
  @override
  @JsonKey()
  final String occurredAt;
  @override
  @JsonKey()
  final String siteName;
  @override
  final String? subsystem;
  @override
  final String? subsystemName;
  @override
  final String? zone;
  @override
  final String? zoneName;
  @override
  final int? zoneNumber;
  @override
  final String? zoneDetectorType;
  @override
  @JsonKey()
  final bool hasMedia;
  // Acknowledgement state
  @override
  @JsonKey()
  final bool acknowledged;
  @override
  final String? acknowledgedAt;
  @override
  final String? performedBy;
  final Map<String, dynamic> _payload;
  @override
  @JsonKey()
  Map<String, dynamic> get payload {
    if (_payload is EqualUnmodifiableMapView) return _payload;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableMapView(_payload);
  }

  @override
  String toString() {
    return 'AlarmEvent(id: $id, eventType: $eventType, eventCategory: $eventCategory, severity: $severity, occurredAt: $occurredAt, siteName: $siteName, subsystem: $subsystem, subsystemName: $subsystemName, zone: $zone, zoneName: $zoneName, zoneNumber: $zoneNumber, zoneDetectorType: $zoneDetectorType, hasMedia: $hasMedia, acknowledged: $acknowledged, acknowledgedAt: $acknowledgedAt, performedBy: $performedBy, payload: $payload)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$AlarmEventImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.eventType, eventType) ||
                other.eventType == eventType) &&
            (identical(other.eventCategory, eventCategory) ||
                other.eventCategory == eventCategory) &&
            (identical(other.severity, severity) ||
                other.severity == severity) &&
            (identical(other.occurredAt, occurredAt) ||
                other.occurredAt == occurredAt) &&
            (identical(other.siteName, siteName) ||
                other.siteName == siteName) &&
            (identical(other.subsystem, subsystem) ||
                other.subsystem == subsystem) &&
            (identical(other.subsystemName, subsystemName) ||
                other.subsystemName == subsystemName) &&
            (identical(other.zone, zone) || other.zone == zone) &&
            (identical(other.zoneName, zoneName) ||
                other.zoneName == zoneName) &&
            (identical(other.zoneNumber, zoneNumber) ||
                other.zoneNumber == zoneNumber) &&
            (identical(other.zoneDetectorType, zoneDetectorType) ||
                other.zoneDetectorType == zoneDetectorType) &&
            (identical(other.hasMedia, hasMedia) ||
                other.hasMedia == hasMedia) &&
            (identical(other.acknowledged, acknowledged) ||
                other.acknowledged == acknowledged) &&
            (identical(other.acknowledgedAt, acknowledgedAt) ||
                other.acknowledgedAt == acknowledgedAt) &&
            (identical(other.performedBy, performedBy) ||
                other.performedBy == performedBy) &&
            const DeepCollectionEquality().equals(other._payload, _payload));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    id,
    eventType,
    eventCategory,
    severity,
    occurredAt,
    siteName,
    subsystem,
    subsystemName,
    zone,
    zoneName,
    zoneNumber,
    zoneDetectorType,
    hasMedia,
    acknowledged,
    acknowledgedAt,
    performedBy,
    const DeepCollectionEquality().hash(_payload),
  );

  /// Create a copy of AlarmEvent
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$AlarmEventImplCopyWith<_$AlarmEventImpl> get copyWith =>
      __$$AlarmEventImplCopyWithImpl<_$AlarmEventImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$AlarmEventImplToJson(this);
  }
}

abstract class _AlarmEvent implements AlarmEvent {
  const factory _AlarmEvent({
    final String id,
    final String eventType,
    final String eventCategory,
    final String severity,
    final String occurredAt,
    final String siteName,
    final String? subsystem,
    final String? subsystemName,
    final String? zone,
    final String? zoneName,
    final int? zoneNumber,
    final String? zoneDetectorType,
    final bool hasMedia,
    final bool acknowledged,
    final String? acknowledgedAt,
    final String? performedBy,
    final Map<String, dynamic> payload,
  }) = _$AlarmEventImpl;

  factory _AlarmEvent.fromJson(Map<String, dynamic> json) =
      _$AlarmEventImpl.fromJson;

  @override
  String get id;
  @override
  String get eventType; // Classification fields added in backend migration 0004
  @override
  String get eventCategory;
  @override
  String get severity;
  @override
  String get occurredAt;
  @override
  String get siteName;
  @override
  String? get subsystem;
  @override
  String? get subsystemName;
  @override
  String? get zone;
  @override
  String? get zoneName;
  @override
  int? get zoneNumber;
  @override
  String? get zoneDetectorType;
  @override
  bool get hasMedia; // Acknowledgement state
  @override
  bool get acknowledged;
  @override
  String? get acknowledgedAt;
  @override
  String? get performedBy;
  @override
  Map<String, dynamic> get payload;

  /// Create a copy of AlarmEvent
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$AlarmEventImplCopyWith<_$AlarmEventImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

AlarmPicture _$AlarmPictureFromJson(Map<String, dynamic> json) {
  return _AlarmPicture.fromJson(json);
}

/// @nodoc
mixin _$AlarmPicture {
  String get url => throw _privateConstructorUsedError;
  bool get encrypt => throw _privateConstructorUsedError;
  String get type => throw _privateConstructorUsedError;
  String? get id => throw _privateConstructorUsedError;

  /// Serializes this AlarmPicture to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of AlarmPicture
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $AlarmPictureCopyWith<AlarmPicture> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $AlarmPictureCopyWith<$Res> {
  factory $AlarmPictureCopyWith(
    AlarmPicture value,
    $Res Function(AlarmPicture) then,
  ) = _$AlarmPictureCopyWithImpl<$Res, AlarmPicture>;
  @useResult
  $Res call({String url, bool encrypt, String type, String? id});
}

/// @nodoc
class _$AlarmPictureCopyWithImpl<$Res, $Val extends AlarmPicture>
    implements $AlarmPictureCopyWith<$Res> {
  _$AlarmPictureCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of AlarmPicture
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? url = null,
    Object? encrypt = null,
    Object? type = null,
    Object? id = freezed,
  }) {
    return _then(
      _value.copyWith(
            url: null == url
                ? _value.url
                : url // ignore: cast_nullable_to_non_nullable
                      as String,
            encrypt: null == encrypt
                ? _value.encrypt
                : encrypt // ignore: cast_nullable_to_non_nullable
                      as bool,
            type: null == type
                ? _value.type
                : type // ignore: cast_nullable_to_non_nullable
                      as String,
            id: freezed == id
                ? _value.id
                : id // ignore: cast_nullable_to_non_nullable
                      as String?,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$AlarmPictureImplCopyWith<$Res>
    implements $AlarmPictureCopyWith<$Res> {
  factory _$$AlarmPictureImplCopyWith(
    _$AlarmPictureImpl value,
    $Res Function(_$AlarmPictureImpl) then,
  ) = __$$AlarmPictureImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({String url, bool encrypt, String type, String? id});
}

/// @nodoc
class __$$AlarmPictureImplCopyWithImpl<$Res>
    extends _$AlarmPictureCopyWithImpl<$Res, _$AlarmPictureImpl>
    implements _$$AlarmPictureImplCopyWith<$Res> {
  __$$AlarmPictureImplCopyWithImpl(
    _$AlarmPictureImpl _value,
    $Res Function(_$AlarmPictureImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of AlarmPicture
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? url = null,
    Object? encrypt = null,
    Object? type = null,
    Object? id = freezed,
  }) {
    return _then(
      _$AlarmPictureImpl(
        url: null == url
            ? _value.url
            : url // ignore: cast_nullable_to_non_nullable
                  as String,
        encrypt: null == encrypt
            ? _value.encrypt
            : encrypt // ignore: cast_nullable_to_non_nullable
                  as bool,
        type: null == type
            ? _value.type
            : type // ignore: cast_nullable_to_non_nullable
                  as String,
        id: freezed == id
            ? _value.id
            : id // ignore: cast_nullable_to_non_nullable
                  as String?,
      ),
    );
  }
}

/// @nodoc

@JsonSerializable(fieldRename: FieldRename.snake)
class _$AlarmPictureImpl implements _AlarmPicture {
  const _$AlarmPictureImpl({
    this.url = '',
    this.encrypt = false,
    this.type = 'image',
    this.id,
  });

  factory _$AlarmPictureImpl.fromJson(Map<String, dynamic> json) =>
      _$$AlarmPictureImplFromJson(json);

  @override
  @JsonKey()
  final String url;
  @override
  @JsonKey()
  final bool encrypt;
  @override
  @JsonKey()
  final String type;
  @override
  final String? id;

  @override
  String toString() {
    return 'AlarmPicture(url: $url, encrypt: $encrypt, type: $type, id: $id)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$AlarmPictureImpl &&
            (identical(other.url, url) || other.url == url) &&
            (identical(other.encrypt, encrypt) || other.encrypt == encrypt) &&
            (identical(other.type, type) || other.type == type) &&
            (identical(other.id, id) || other.id == id));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, url, encrypt, type, id);

  /// Create a copy of AlarmPicture
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$AlarmPictureImplCopyWith<_$AlarmPictureImpl> get copyWith =>
      __$$AlarmPictureImplCopyWithImpl<_$AlarmPictureImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$AlarmPictureImplToJson(this);
  }
}

abstract class _AlarmPicture implements AlarmPicture {
  const factory _AlarmPicture({
    final String url,
    final bool encrypt,
    final String type,
    final String? id,
  }) = _$AlarmPictureImpl;

  factory _AlarmPicture.fromJson(Map<String, dynamic> json) =
      _$AlarmPictureImpl.fromJson;

  @override
  String get url;
  @override
  bool get encrypt;
  @override
  String get type;
  @override
  String? get id;

  /// Create a copy of AlarmPicture
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$AlarmPictureImplCopyWith<_$AlarmPictureImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

PaginatedEvents _$PaginatedEventsFromJson(Map<String, dynamic> json) {
  return _PaginatedEvents.fromJson(json);
}

/// @nodoc
mixin _$PaginatedEvents {
  int get count => throw _privateConstructorUsedError;
  String? get next => throw _privateConstructorUsedError;
  String? get previous => throw _privateConstructorUsedError;
  List<AlarmEvent> get results => throw _privateConstructorUsedError;

  /// Serializes this PaginatedEvents to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of PaginatedEvents
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $PaginatedEventsCopyWith<PaginatedEvents> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $PaginatedEventsCopyWith<$Res> {
  factory $PaginatedEventsCopyWith(
    PaginatedEvents value,
    $Res Function(PaginatedEvents) then,
  ) = _$PaginatedEventsCopyWithImpl<$Res, PaginatedEvents>;
  @useResult
  $Res call({
    int count,
    String? next,
    String? previous,
    List<AlarmEvent> results,
  });
}

/// @nodoc
class _$PaginatedEventsCopyWithImpl<$Res, $Val extends PaginatedEvents>
    implements $PaginatedEventsCopyWith<$Res> {
  _$PaginatedEventsCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of PaginatedEvents
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? count = null,
    Object? next = freezed,
    Object? previous = freezed,
    Object? results = null,
  }) {
    return _then(
      _value.copyWith(
            count: null == count
                ? _value.count
                : count // ignore: cast_nullable_to_non_nullable
                      as int,
            next: freezed == next
                ? _value.next
                : next // ignore: cast_nullable_to_non_nullable
                      as String?,
            previous: freezed == previous
                ? _value.previous
                : previous // ignore: cast_nullable_to_non_nullable
                      as String?,
            results: null == results
                ? _value.results
                : results // ignore: cast_nullable_to_non_nullable
                      as List<AlarmEvent>,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$PaginatedEventsImplCopyWith<$Res>
    implements $PaginatedEventsCopyWith<$Res> {
  factory _$$PaginatedEventsImplCopyWith(
    _$PaginatedEventsImpl value,
    $Res Function(_$PaginatedEventsImpl) then,
  ) = __$$PaginatedEventsImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    int count,
    String? next,
    String? previous,
    List<AlarmEvent> results,
  });
}

/// @nodoc
class __$$PaginatedEventsImplCopyWithImpl<$Res>
    extends _$PaginatedEventsCopyWithImpl<$Res, _$PaginatedEventsImpl>
    implements _$$PaginatedEventsImplCopyWith<$Res> {
  __$$PaginatedEventsImplCopyWithImpl(
    _$PaginatedEventsImpl _value,
    $Res Function(_$PaginatedEventsImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of PaginatedEvents
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? count = null,
    Object? next = freezed,
    Object? previous = freezed,
    Object? results = null,
  }) {
    return _then(
      _$PaginatedEventsImpl(
        count: null == count
            ? _value.count
            : count // ignore: cast_nullable_to_non_nullable
                  as int,
        next: freezed == next
            ? _value.next
            : next // ignore: cast_nullable_to_non_nullable
                  as String?,
        previous: freezed == previous
            ? _value.previous
            : previous // ignore: cast_nullable_to_non_nullable
                  as String?,
        results: null == results
            ? _value._results
            : results // ignore: cast_nullable_to_non_nullable
                  as List<AlarmEvent>,
      ),
    );
  }
}

/// @nodoc

@JsonSerializable(fieldRename: FieldRename.snake)
class _$PaginatedEventsImpl implements _PaginatedEvents {
  const _$PaginatedEventsImpl({
    this.count = 0,
    this.next,
    this.previous,
    final List<AlarmEvent> results = const [],
  }) : _results = results;

  factory _$PaginatedEventsImpl.fromJson(Map<String, dynamic> json) =>
      _$$PaginatedEventsImplFromJson(json);

  @override
  @JsonKey()
  final int count;
  @override
  final String? next;
  @override
  final String? previous;
  final List<AlarmEvent> _results;
  @override
  @JsonKey()
  List<AlarmEvent> get results {
    if (_results is EqualUnmodifiableListView) return _results;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_results);
  }

  @override
  String toString() {
    return 'PaginatedEvents(count: $count, next: $next, previous: $previous, results: $results)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$PaginatedEventsImpl &&
            (identical(other.count, count) || other.count == count) &&
            (identical(other.next, next) || other.next == next) &&
            (identical(other.previous, previous) ||
                other.previous == previous) &&
            const DeepCollectionEquality().equals(other._results, _results));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    count,
    next,
    previous,
    const DeepCollectionEquality().hash(_results),
  );

  /// Create a copy of PaginatedEvents
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$PaginatedEventsImplCopyWith<_$PaginatedEventsImpl> get copyWith =>
      __$$PaginatedEventsImplCopyWithImpl<_$PaginatedEventsImpl>(
        this,
        _$identity,
      );

  @override
  Map<String, dynamic> toJson() {
    return _$$PaginatedEventsImplToJson(this);
  }
}

abstract class _PaginatedEvents implements PaginatedEvents {
  const factory _PaginatedEvents({
    final int count,
    final String? next,
    final String? previous,
    final List<AlarmEvent> results,
  }) = _$PaginatedEventsImpl;

  factory _PaginatedEvents.fromJson(Map<String, dynamic> json) =
      _$PaginatedEventsImpl.fromJson;

  @override
  int get count;
  @override
  String? get next;
  @override
  String? get previous;
  @override
  List<AlarmEvent> get results;

  /// Create a copy of PaginatedEvents
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$PaginatedEventsImplCopyWith<_$PaginatedEventsImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
