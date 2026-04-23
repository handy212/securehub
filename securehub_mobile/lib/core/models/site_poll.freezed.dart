// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'site_poll.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

LastEvent _$LastEventFromJson(Map<String, dynamic> json) {
  return _LastEvent.fromJson(json);
}

/// @nodoc
mixin _$LastEvent {
  String? get id => throw _privateConstructorUsedError;
  String? get type => throw _privateConstructorUsedError;
  String? get occurredAt => throw _privateConstructorUsedError;

  /// Serializes this LastEvent to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of LastEvent
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $LastEventCopyWith<LastEvent> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $LastEventCopyWith<$Res> {
  factory $LastEventCopyWith(LastEvent value, $Res Function(LastEvent) then) =
      _$LastEventCopyWithImpl<$Res, LastEvent>;
  @useResult
  $Res call({String? id, String? type, String? occurredAt});
}

/// @nodoc
class _$LastEventCopyWithImpl<$Res, $Val extends LastEvent>
    implements $LastEventCopyWith<$Res> {
  _$LastEventCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of LastEvent
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = freezed,
    Object? type = freezed,
    Object? occurredAt = freezed,
  }) {
    return _then(
      _value.copyWith(
            id: freezed == id
                ? _value.id
                : id // ignore: cast_nullable_to_non_nullable
                      as String?,
            type: freezed == type
                ? _value.type
                : type // ignore: cast_nullable_to_non_nullable
                      as String?,
            occurredAt: freezed == occurredAt
                ? _value.occurredAt
                : occurredAt // ignore: cast_nullable_to_non_nullable
                      as String?,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$LastEventImplCopyWith<$Res>
    implements $LastEventCopyWith<$Res> {
  factory _$$LastEventImplCopyWith(
    _$LastEventImpl value,
    $Res Function(_$LastEventImpl) then,
  ) = __$$LastEventImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({String? id, String? type, String? occurredAt});
}

/// @nodoc
class __$$LastEventImplCopyWithImpl<$Res>
    extends _$LastEventCopyWithImpl<$Res, _$LastEventImpl>
    implements _$$LastEventImplCopyWith<$Res> {
  __$$LastEventImplCopyWithImpl(
    _$LastEventImpl _value,
    $Res Function(_$LastEventImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of LastEvent
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = freezed,
    Object? type = freezed,
    Object? occurredAt = freezed,
  }) {
    return _then(
      _$LastEventImpl(
        id: freezed == id
            ? _value.id
            : id // ignore: cast_nullable_to_non_nullable
                  as String?,
        type: freezed == type
            ? _value.type
            : type // ignore: cast_nullable_to_non_nullable
                  as String?,
        occurredAt: freezed == occurredAt
            ? _value.occurredAt
            : occurredAt // ignore: cast_nullable_to_non_nullable
                  as String?,
      ),
    );
  }
}

/// @nodoc

@JsonSerializable(fieldRename: FieldRename.snake)
class _$LastEventImpl implements _LastEvent {
  const _$LastEventImpl({this.id, this.type, this.occurredAt});

  factory _$LastEventImpl.fromJson(Map<String, dynamic> json) =>
      _$$LastEventImplFromJson(json);

  @override
  final String? id;
  @override
  final String? type;
  @override
  final String? occurredAt;

  @override
  String toString() {
    return 'LastEvent(id: $id, type: $type, occurredAt: $occurredAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$LastEventImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.type, type) || other.type == type) &&
            (identical(other.occurredAt, occurredAt) ||
                other.occurredAt == occurredAt));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, id, type, occurredAt);

  /// Create a copy of LastEvent
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$LastEventImplCopyWith<_$LastEventImpl> get copyWith =>
      __$$LastEventImplCopyWithImpl<_$LastEventImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$LastEventImplToJson(this);
  }
}

abstract class _LastEvent implements LastEvent {
  const factory _LastEvent({
    final String? id,
    final String? type,
    final String? occurredAt,
  }) = _$LastEventImpl;

  factory _LastEvent.fromJson(Map<String, dynamic> json) =
      _$LastEventImpl.fromJson;

  @override
  String? get id;
  @override
  String? get type;
  @override
  String? get occurredAt;

  /// Create a copy of LastEvent
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$LastEventImplCopyWith<_$LastEventImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

SitePoll _$SitePollFromJson(Map<String, dynamic> json) {
  return _SitePoll.fromJson(json);
}

/// @nodoc
mixin _$SitePoll {
  String get siteId => throw _privateConstructorUsedError;
  int get armedSubsystems => throw _privateConstructorUsedError;
  int get disarmedSubsystems => throw _privateConstructorUsedError;
  int get activeAlarmCount => throw _privateConstructorUsedError;
  int get offlineDeviceCount => throw _privateConstructorUsedError;
  LastEvent? get lastEvent => throw _privateConstructorUsedError;
  List<Subsystem> get subsystems => throw _privateConstructorUsedError;

  /// Serializes this SitePoll to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of SitePoll
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $SitePollCopyWith<SitePoll> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $SitePollCopyWith<$Res> {
  factory $SitePollCopyWith(SitePoll value, $Res Function(SitePoll) then) =
      _$SitePollCopyWithImpl<$Res, SitePoll>;
  @useResult
  $Res call({
    String siteId,
    int armedSubsystems,
    int disarmedSubsystems,
    int activeAlarmCount,
    int offlineDeviceCount,
    LastEvent? lastEvent,
    List<Subsystem> subsystems,
  });

  $LastEventCopyWith<$Res>? get lastEvent;
}

/// @nodoc
class _$SitePollCopyWithImpl<$Res, $Val extends SitePoll>
    implements $SitePollCopyWith<$Res> {
  _$SitePollCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of SitePoll
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? siteId = null,
    Object? armedSubsystems = null,
    Object? disarmedSubsystems = null,
    Object? activeAlarmCount = null,
    Object? offlineDeviceCount = null,
    Object? lastEvent = freezed,
    Object? subsystems = null,
  }) {
    return _then(
      _value.copyWith(
            siteId: null == siteId
                ? _value.siteId
                : siteId // ignore: cast_nullable_to_non_nullable
                      as String,
            armedSubsystems: null == armedSubsystems
                ? _value.armedSubsystems
                : armedSubsystems // ignore: cast_nullable_to_non_nullable
                      as int,
            disarmedSubsystems: null == disarmedSubsystems
                ? _value.disarmedSubsystems
                : disarmedSubsystems // ignore: cast_nullable_to_non_nullable
                      as int,
            activeAlarmCount: null == activeAlarmCount
                ? _value.activeAlarmCount
                : activeAlarmCount // ignore: cast_nullable_to_non_nullable
                      as int,
            offlineDeviceCount: null == offlineDeviceCount
                ? _value.offlineDeviceCount
                : offlineDeviceCount // ignore: cast_nullable_to_non_nullable
                      as int,
            lastEvent: freezed == lastEvent
                ? _value.lastEvent
                : lastEvent // ignore: cast_nullable_to_non_nullable
                      as LastEvent?,
            subsystems: null == subsystems
                ? _value.subsystems
                : subsystems // ignore: cast_nullable_to_non_nullable
                      as List<Subsystem>,
          )
          as $Val,
    );
  }

  /// Create a copy of SitePoll
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $LastEventCopyWith<$Res>? get lastEvent {
    if (_value.lastEvent == null) {
      return null;
    }

    return $LastEventCopyWith<$Res>(_value.lastEvent!, (value) {
      return _then(_value.copyWith(lastEvent: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$SitePollImplCopyWith<$Res>
    implements $SitePollCopyWith<$Res> {
  factory _$$SitePollImplCopyWith(
    _$SitePollImpl value,
    $Res Function(_$SitePollImpl) then,
  ) = __$$SitePollImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    String siteId,
    int armedSubsystems,
    int disarmedSubsystems,
    int activeAlarmCount,
    int offlineDeviceCount,
    LastEvent? lastEvent,
    List<Subsystem> subsystems,
  });

  @override
  $LastEventCopyWith<$Res>? get lastEvent;
}

/// @nodoc
class __$$SitePollImplCopyWithImpl<$Res>
    extends _$SitePollCopyWithImpl<$Res, _$SitePollImpl>
    implements _$$SitePollImplCopyWith<$Res> {
  __$$SitePollImplCopyWithImpl(
    _$SitePollImpl _value,
    $Res Function(_$SitePollImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of SitePoll
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? siteId = null,
    Object? armedSubsystems = null,
    Object? disarmedSubsystems = null,
    Object? activeAlarmCount = null,
    Object? offlineDeviceCount = null,
    Object? lastEvent = freezed,
    Object? subsystems = null,
  }) {
    return _then(
      _$SitePollImpl(
        siteId: null == siteId
            ? _value.siteId
            : siteId // ignore: cast_nullable_to_non_nullable
                  as String,
        armedSubsystems: null == armedSubsystems
            ? _value.armedSubsystems
            : armedSubsystems // ignore: cast_nullable_to_non_nullable
                  as int,
        disarmedSubsystems: null == disarmedSubsystems
            ? _value.disarmedSubsystems
            : disarmedSubsystems // ignore: cast_nullable_to_non_nullable
                  as int,
        activeAlarmCount: null == activeAlarmCount
            ? _value.activeAlarmCount
            : activeAlarmCount // ignore: cast_nullable_to_non_nullable
                  as int,
        offlineDeviceCount: null == offlineDeviceCount
            ? _value.offlineDeviceCount
            : offlineDeviceCount // ignore: cast_nullable_to_non_nullable
                  as int,
        lastEvent: freezed == lastEvent
            ? _value.lastEvent
            : lastEvent // ignore: cast_nullable_to_non_nullable
                  as LastEvent?,
        subsystems: null == subsystems
            ? _value._subsystems
            : subsystems // ignore: cast_nullable_to_non_nullable
                  as List<Subsystem>,
      ),
    );
  }
}

/// @nodoc

@JsonSerializable(fieldRename: FieldRename.snake)
class _$SitePollImpl implements _SitePoll {
  const _$SitePollImpl({
    this.siteId = '',
    this.armedSubsystems = 0,
    this.disarmedSubsystems = 0,
    this.activeAlarmCount = 0,
    this.offlineDeviceCount = 0,
    this.lastEvent,
    final List<Subsystem> subsystems = const [],
  }) : _subsystems = subsystems;

  factory _$SitePollImpl.fromJson(Map<String, dynamic> json) =>
      _$$SitePollImplFromJson(json);

  @override
  @JsonKey()
  final String siteId;
  @override
  @JsonKey()
  final int armedSubsystems;
  @override
  @JsonKey()
  final int disarmedSubsystems;
  @override
  @JsonKey()
  final int activeAlarmCount;
  @override
  @JsonKey()
  final int offlineDeviceCount;
  @override
  final LastEvent? lastEvent;
  final List<Subsystem> _subsystems;
  @override
  @JsonKey()
  List<Subsystem> get subsystems {
    if (_subsystems is EqualUnmodifiableListView) return _subsystems;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_subsystems);
  }

  @override
  String toString() {
    return 'SitePoll(siteId: $siteId, armedSubsystems: $armedSubsystems, disarmedSubsystems: $disarmedSubsystems, activeAlarmCount: $activeAlarmCount, offlineDeviceCount: $offlineDeviceCount, lastEvent: $lastEvent, subsystems: $subsystems)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$SitePollImpl &&
            (identical(other.siteId, siteId) || other.siteId == siteId) &&
            (identical(other.armedSubsystems, armedSubsystems) ||
                other.armedSubsystems == armedSubsystems) &&
            (identical(other.disarmedSubsystems, disarmedSubsystems) ||
                other.disarmedSubsystems == disarmedSubsystems) &&
            (identical(other.activeAlarmCount, activeAlarmCount) ||
                other.activeAlarmCount == activeAlarmCount) &&
            (identical(other.offlineDeviceCount, offlineDeviceCount) ||
                other.offlineDeviceCount == offlineDeviceCount) &&
            (identical(other.lastEvent, lastEvent) ||
                other.lastEvent == lastEvent) &&
            const DeepCollectionEquality().equals(
              other._subsystems,
              _subsystems,
            ));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    siteId,
    armedSubsystems,
    disarmedSubsystems,
    activeAlarmCount,
    offlineDeviceCount,
    lastEvent,
    const DeepCollectionEquality().hash(_subsystems),
  );

  /// Create a copy of SitePoll
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$SitePollImplCopyWith<_$SitePollImpl> get copyWith =>
      __$$SitePollImplCopyWithImpl<_$SitePollImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$SitePollImplToJson(this);
  }
}

abstract class _SitePoll implements SitePoll {
  const factory _SitePoll({
    final String siteId,
    final int armedSubsystems,
    final int disarmedSubsystems,
    final int activeAlarmCount,
    final int offlineDeviceCount,
    final LastEvent? lastEvent,
    final List<Subsystem> subsystems,
  }) = _$SitePollImpl;

  factory _SitePoll.fromJson(Map<String, dynamic> json) =
      _$SitePollImpl.fromJson;

  @override
  String get siteId;
  @override
  int get armedSubsystems;
  @override
  int get disarmedSubsystems;
  @override
  int get activeAlarmCount;
  @override
  int get offlineDeviceCount;
  @override
  LastEvent? get lastEvent;
  @override
  List<Subsystem> get subsystems;

  /// Create a copy of SitePoll
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$SitePollImplCopyWith<_$SitePollImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
