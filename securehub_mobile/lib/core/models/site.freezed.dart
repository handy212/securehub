// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'site.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

Zone _$ZoneFromJson(Map<String, dynamic> json) {
  return _Zone.fromJson(json);
}

/// @nodoc
mixin _$Zone {
  String get id => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  @JsonKey(name: 'zoneNumber')
  int get zoneNumber => throw _privateConstructorUsedError;
  String get state => throw _privateConstructorUsedError;
  @JsonKey(name: 'lowBattery')
  bool get lowBattery => throw _privateConstructorUsedError;
  bool get tamper => throw _privateConstructorUsedError;
  @JsonKey(name: 'signalStrength')
  String get signalStrength => throw _privateConstructorUsedError;
  @JsonKey(name: 'isOnline')
  bool get isOnline => throw _privateConstructorUsedError;
  @JsonKey(name: 'deviceNumber')
  int? get deviceNumber => throw _privateConstructorUsedError;
  @JsonKey(name: 'detectorType')
  String get detectorType => throw _privateConstructorUsedError;
  @JsonKey(name: 'deviceType')
  String get deviceType => throw _privateConstructorUsedError;
  @JsonKey(name: 'chargeValue')
  int? get chargeValue => throw _privateConstructorUsedError;
  @JsonKey(name: 'displayType')
  String get displayType => throw _privateConstructorUsedError;
  @JsonKey(name: 'iconType')
  String get iconType => throw _privateConstructorUsedError;
  @JsonKey(name: 'firmwareVersion')
  String get firmwareVersion => throw _privateConstructorUsedError;
  @JsonKey(name: 'hardwareVersion')
  String get hardwareVersion => throw _privateConstructorUsedError;
  @JsonKey(name: 'modelNumber')
  String get modelNumber => throw _privateConstructorUsedError;

  /// Serializes this Zone to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of Zone
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $ZoneCopyWith<Zone> get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $ZoneCopyWith<$Res> {
  factory $ZoneCopyWith(Zone value, $Res Function(Zone) then) =
      _$ZoneCopyWithImpl<$Res, Zone>;
  @useResult
  $Res call({
    String id,
    String name,
    @JsonKey(name: 'zoneNumber') int zoneNumber,
    String state,
    @JsonKey(name: 'lowBattery') bool lowBattery,
    bool tamper,
    @JsonKey(name: 'signalStrength') String signalStrength,
    @JsonKey(name: 'isOnline') bool isOnline,
    @JsonKey(name: 'deviceNumber') int? deviceNumber,
    @JsonKey(name: 'detectorType') String detectorType,
    @JsonKey(name: 'deviceType') String deviceType,
    @JsonKey(name: 'chargeValue') int? chargeValue,
    @JsonKey(name: 'displayType') String displayType,
    @JsonKey(name: 'iconType') String iconType,
    @JsonKey(name: 'firmwareVersion') String firmwareVersion,
    @JsonKey(name: 'hardwareVersion') String hardwareVersion,
    @JsonKey(name: 'modelNumber') String modelNumber,
  });
}

/// @nodoc
class _$ZoneCopyWithImpl<$Res, $Val extends Zone>
    implements $ZoneCopyWith<$Res> {
  _$ZoneCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of Zone
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? zoneNumber = null,
    Object? state = null,
    Object? lowBattery = null,
    Object? tamper = null,
    Object? signalStrength = null,
    Object? isOnline = null,
    Object? deviceNumber = freezed,
    Object? detectorType = null,
    Object? deviceType = null,
    Object? chargeValue = freezed,
    Object? displayType = null,
    Object? iconType = null,
    Object? firmwareVersion = null,
    Object? hardwareVersion = null,
    Object? modelNumber = null,
  }) {
    return _then(
      _value.copyWith(
            id: null == id
                ? _value.id
                : id // ignore: cast_nullable_to_non_nullable
                      as String,
            name: null == name
                ? _value.name
                : name // ignore: cast_nullable_to_non_nullable
                      as String,
            zoneNumber: null == zoneNumber
                ? _value.zoneNumber
                : zoneNumber // ignore: cast_nullable_to_non_nullable
                      as int,
            state: null == state
                ? _value.state
                : state // ignore: cast_nullable_to_non_nullable
                      as String,
            lowBattery: null == lowBattery
                ? _value.lowBattery
                : lowBattery // ignore: cast_nullable_to_non_nullable
                      as bool,
            tamper: null == tamper
                ? _value.tamper
                : tamper // ignore: cast_nullable_to_non_nullable
                      as bool,
            signalStrength: null == signalStrength
                ? _value.signalStrength
                : signalStrength // ignore: cast_nullable_to_non_nullable
                      as String,
            isOnline: null == isOnline
                ? _value.isOnline
                : isOnline // ignore: cast_nullable_to_non_nullable
                      as bool,
            deviceNumber: freezed == deviceNumber
                ? _value.deviceNumber
                : deviceNumber // ignore: cast_nullable_to_non_nullable
                      as int?,
            detectorType: null == detectorType
                ? _value.detectorType
                : detectorType // ignore: cast_nullable_to_non_nullable
                      as String,
            deviceType: null == deviceType
                ? _value.deviceType
                : deviceType // ignore: cast_nullable_to_non_nullable
                      as String,
            chargeValue: freezed == chargeValue
                ? _value.chargeValue
                : chargeValue // ignore: cast_nullable_to_non_nullable
                      as int?,
            displayType: null == displayType
                ? _value.displayType
                : displayType // ignore: cast_nullable_to_non_nullable
                      as String,
            iconType: null == iconType
                ? _value.iconType
                : iconType // ignore: cast_nullable_to_non_nullable
                      as String,
            firmwareVersion: null == firmwareVersion
                ? _value.firmwareVersion
                : firmwareVersion // ignore: cast_nullable_to_non_nullable
                      as String,
            hardwareVersion: null == hardwareVersion
                ? _value.hardwareVersion
                : hardwareVersion // ignore: cast_nullable_to_non_nullable
                      as String,
            modelNumber: null == modelNumber
                ? _value.modelNumber
                : modelNumber // ignore: cast_nullable_to_non_nullable
                      as String,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$ZoneImplCopyWith<$Res> implements $ZoneCopyWith<$Res> {
  factory _$$ZoneImplCopyWith(
    _$ZoneImpl value,
    $Res Function(_$ZoneImpl) then,
  ) = __$$ZoneImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    String id,
    String name,
    @JsonKey(name: 'zoneNumber') int zoneNumber,
    String state,
    @JsonKey(name: 'lowBattery') bool lowBattery,
    bool tamper,
    @JsonKey(name: 'signalStrength') String signalStrength,
    @JsonKey(name: 'isOnline') bool isOnline,
    @JsonKey(name: 'deviceNumber') int? deviceNumber,
    @JsonKey(name: 'detectorType') String detectorType,
    @JsonKey(name: 'deviceType') String deviceType,
    @JsonKey(name: 'chargeValue') int? chargeValue,
    @JsonKey(name: 'displayType') String displayType,
    @JsonKey(name: 'iconType') String iconType,
    @JsonKey(name: 'firmwareVersion') String firmwareVersion,
    @JsonKey(name: 'hardwareVersion') String hardwareVersion,
    @JsonKey(name: 'modelNumber') String modelNumber,
  });
}

/// @nodoc
class __$$ZoneImplCopyWithImpl<$Res>
    extends _$ZoneCopyWithImpl<$Res, _$ZoneImpl>
    implements _$$ZoneImplCopyWith<$Res> {
  __$$ZoneImplCopyWithImpl(_$ZoneImpl _value, $Res Function(_$ZoneImpl) _then)
    : super(_value, _then);

  /// Create a copy of Zone
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? zoneNumber = null,
    Object? state = null,
    Object? lowBattery = null,
    Object? tamper = null,
    Object? signalStrength = null,
    Object? isOnline = null,
    Object? deviceNumber = freezed,
    Object? detectorType = null,
    Object? deviceType = null,
    Object? chargeValue = freezed,
    Object? displayType = null,
    Object? iconType = null,
    Object? firmwareVersion = null,
    Object? hardwareVersion = null,
    Object? modelNumber = null,
  }) {
    return _then(
      _$ZoneImpl(
        id: null == id
            ? _value.id
            : id // ignore: cast_nullable_to_non_nullable
                  as String,
        name: null == name
            ? _value.name
            : name // ignore: cast_nullable_to_non_nullable
                  as String,
        zoneNumber: null == zoneNumber
            ? _value.zoneNumber
            : zoneNumber // ignore: cast_nullable_to_non_nullable
                  as int,
        state: null == state
            ? _value.state
            : state // ignore: cast_nullable_to_non_nullable
                  as String,
        lowBattery: null == lowBattery
            ? _value.lowBattery
            : lowBattery // ignore: cast_nullable_to_non_nullable
                  as bool,
        tamper: null == tamper
            ? _value.tamper
            : tamper // ignore: cast_nullable_to_non_nullable
                  as bool,
        signalStrength: null == signalStrength
            ? _value.signalStrength
            : signalStrength // ignore: cast_nullable_to_non_nullable
                  as String,
        isOnline: null == isOnline
            ? _value.isOnline
            : isOnline // ignore: cast_nullable_to_non_nullable
                  as bool,
        deviceNumber: freezed == deviceNumber
            ? _value.deviceNumber
            : deviceNumber // ignore: cast_nullable_to_non_nullable
                  as int?,
        detectorType: null == detectorType
            ? _value.detectorType
            : detectorType // ignore: cast_nullable_to_non_nullable
                  as String,
        deviceType: null == deviceType
            ? _value.deviceType
            : deviceType // ignore: cast_nullable_to_non_nullable
                  as String,
        chargeValue: freezed == chargeValue
            ? _value.chargeValue
            : chargeValue // ignore: cast_nullable_to_non_nullable
                  as int?,
        displayType: null == displayType
            ? _value.displayType
            : displayType // ignore: cast_nullable_to_non_nullable
                  as String,
        iconType: null == iconType
            ? _value.iconType
            : iconType // ignore: cast_nullable_to_non_nullable
                  as String,
        firmwareVersion: null == firmwareVersion
            ? _value.firmwareVersion
            : firmwareVersion // ignore: cast_nullable_to_non_nullable
                  as String,
        hardwareVersion: null == hardwareVersion
            ? _value.hardwareVersion
            : hardwareVersion // ignore: cast_nullable_to_non_nullable
                  as String,
        modelNumber: null == modelNumber
            ? _value.modelNumber
            : modelNumber // ignore: cast_nullable_to_non_nullable
                  as String,
      ),
    );
  }
}

/// @nodoc

@JsonSerializable(fieldRename: FieldRename.snake)
class _$ZoneImpl implements _Zone {
  const _$ZoneImpl({
    this.id = '',
    this.name = '',
    @JsonKey(name: 'zoneNumber') this.zoneNumber = 0,
    this.state = 'normal',
    @JsonKey(name: 'lowBattery') this.lowBattery = false,
    this.tamper = false,
    @JsonKey(name: 'signalStrength') this.signalStrength = '',
    @JsonKey(name: 'isOnline') this.isOnline = true,
    @JsonKey(name: 'deviceNumber') this.deviceNumber = 0,
    @JsonKey(name: 'detectorType') this.detectorType = '',
    @JsonKey(name: 'deviceType') this.deviceType = '',
    @JsonKey(name: 'chargeValue') this.chargeValue = 0,
    @JsonKey(name: 'displayType') this.displayType = '',
    @JsonKey(name: 'iconType') this.iconType = '',
    @JsonKey(name: 'firmwareVersion') this.firmwareVersion = '',
    @JsonKey(name: 'hardwareVersion') this.hardwareVersion = '',
    @JsonKey(name: 'modelNumber') this.modelNumber = '',
  });

  factory _$ZoneImpl.fromJson(Map<String, dynamic> json) =>
      _$$ZoneImplFromJson(json);

  @override
  @JsonKey()
  final String id;
  @override
  @JsonKey()
  final String name;
  @override
  @JsonKey(name: 'zoneNumber')
  final int zoneNumber;
  @override
  @JsonKey()
  final String state;
  @override
  @JsonKey(name: 'lowBattery')
  final bool lowBattery;
  @override
  @JsonKey()
  final bool tamper;
  @override
  @JsonKey(name: 'signalStrength')
  final String signalStrength;
  @override
  @JsonKey(name: 'isOnline')
  final bool isOnline;
  @override
  @JsonKey(name: 'deviceNumber')
  final int? deviceNumber;
  @override
  @JsonKey(name: 'detectorType')
  final String detectorType;
  @override
  @JsonKey(name: 'deviceType')
  final String deviceType;
  @override
  @JsonKey(name: 'chargeValue')
  final int? chargeValue;
  @override
  @JsonKey(name: 'displayType')
  final String displayType;
  @override
  @JsonKey(name: 'iconType')
  final String iconType;
  @override
  @JsonKey(name: 'firmwareVersion')
  final String firmwareVersion;
  @override
  @JsonKey(name: 'hardwareVersion')
  final String hardwareVersion;
  @override
  @JsonKey(name: 'modelNumber')
  final String modelNumber;

  @override
  String toString() {
    return 'Zone(id: $id, name: $name, zoneNumber: $zoneNumber, state: $state, lowBattery: $lowBattery, tamper: $tamper, signalStrength: $signalStrength, isOnline: $isOnline, deviceNumber: $deviceNumber, detectorType: $detectorType, deviceType: $deviceType, chargeValue: $chargeValue, displayType: $displayType, iconType: $iconType, firmwareVersion: $firmwareVersion, hardwareVersion: $hardwareVersion, modelNumber: $modelNumber)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ZoneImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.zoneNumber, zoneNumber) ||
                other.zoneNumber == zoneNumber) &&
            (identical(other.state, state) || other.state == state) &&
            (identical(other.lowBattery, lowBattery) ||
                other.lowBattery == lowBattery) &&
            (identical(other.tamper, tamper) || other.tamper == tamper) &&
            (identical(other.signalStrength, signalStrength) ||
                other.signalStrength == signalStrength) &&
            (identical(other.isOnline, isOnline) ||
                other.isOnline == isOnline) &&
            (identical(other.deviceNumber, deviceNumber) ||
                other.deviceNumber == deviceNumber) &&
            (identical(other.detectorType, detectorType) ||
                other.detectorType == detectorType) &&
            (identical(other.deviceType, deviceType) ||
                other.deviceType == deviceType) &&
            (identical(other.chargeValue, chargeValue) ||
                other.chargeValue == chargeValue) &&
            (identical(other.displayType, displayType) ||
                other.displayType == displayType) &&
            (identical(other.iconType, iconType) ||
                other.iconType == iconType) &&
            (identical(other.firmwareVersion, firmwareVersion) ||
                other.firmwareVersion == firmwareVersion) &&
            (identical(other.hardwareVersion, hardwareVersion) ||
                other.hardwareVersion == hardwareVersion) &&
            (identical(other.modelNumber, modelNumber) ||
                other.modelNumber == modelNumber));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    id,
    name,
    zoneNumber,
    state,
    lowBattery,
    tamper,
    signalStrength,
    isOnline,
    deviceNumber,
    detectorType,
    deviceType,
    chargeValue,
    displayType,
    iconType,
    firmwareVersion,
    hardwareVersion,
    modelNumber,
  );

  /// Create a copy of Zone
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$ZoneImplCopyWith<_$ZoneImpl> get copyWith =>
      __$$ZoneImplCopyWithImpl<_$ZoneImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$ZoneImplToJson(this);
  }
}

abstract class _Zone implements Zone {
  const factory _Zone({
    final String id,
    final String name,
    @JsonKey(name: 'zoneNumber') final int zoneNumber,
    final String state,
    @JsonKey(name: 'lowBattery') final bool lowBattery,
    final bool tamper,
    @JsonKey(name: 'signalStrength') final String signalStrength,
    @JsonKey(name: 'isOnline') final bool isOnline,
    @JsonKey(name: 'deviceNumber') final int? deviceNumber,
    @JsonKey(name: 'detectorType') final String detectorType,
    @JsonKey(name: 'deviceType') final String deviceType,
    @JsonKey(name: 'chargeValue') final int? chargeValue,
    @JsonKey(name: 'displayType') final String displayType,
    @JsonKey(name: 'iconType') final String iconType,
    @JsonKey(name: 'firmwareVersion') final String firmwareVersion,
    @JsonKey(name: 'hardwareVersion') final String hardwareVersion,
    @JsonKey(name: 'modelNumber') final String modelNumber,
  }) = _$ZoneImpl;

  factory _Zone.fromJson(Map<String, dynamic> json) = _$ZoneImpl.fromJson;

  @override
  String get id;
  @override
  String get name;
  @override
  @JsonKey(name: 'zoneNumber')
  int get zoneNumber;
  @override
  String get state;
  @override
  @JsonKey(name: 'lowBattery')
  bool get lowBattery;
  @override
  bool get tamper;
  @override
  @JsonKey(name: 'signalStrength')
  String get signalStrength;
  @override
  @JsonKey(name: 'isOnline')
  bool get isOnline;
  @override
  @JsonKey(name: 'deviceNumber')
  int? get deviceNumber;
  @override
  @JsonKey(name: 'detectorType')
  String get detectorType;
  @override
  @JsonKey(name: 'deviceType')
  String get deviceType;
  @override
  @JsonKey(name: 'chargeValue')
  int? get chargeValue;
  @override
  @JsonKey(name: 'displayType')
  String get displayType;
  @override
  @JsonKey(name: 'iconType')
  String get iconType;
  @override
  @JsonKey(name: 'firmwareVersion')
  String get firmwareVersion;
  @override
  @JsonKey(name: 'hardwareVersion')
  String get hardwareVersion;
  @override
  @JsonKey(name: 'modelNumber')
  String get modelNumber;

  /// Create a copy of Zone
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$ZoneImplCopyWith<_$ZoneImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

Subsystem _$SubsystemFromJson(Map<String, dynamic> json) {
  return _Subsystem.fromJson(json);
}

/// @nodoc
mixin _$Subsystem {
  String get id => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  @JsonKey(name: 'hikSubsystemId')
  String get hikSubsystemId => throw _privateConstructorUsedError;
  @JsonKey(name: 'subsystemNumber')
  int get subsystemNumber => throw _privateConstructorUsedError;
  String get status => throw _privateConstructorUsedError;
  List<Zone> get zones => throw _privateConstructorUsedError;

  /// Serializes this Subsystem to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of Subsystem
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $SubsystemCopyWith<Subsystem> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $SubsystemCopyWith<$Res> {
  factory $SubsystemCopyWith(Subsystem value, $Res Function(Subsystem) then) =
      _$SubsystemCopyWithImpl<$Res, Subsystem>;
  @useResult
  $Res call({
    String id,
    String name,
    @JsonKey(name: 'hikSubsystemId') String hikSubsystemId,
    @JsonKey(name: 'subsystemNumber') int subsystemNumber,
    String status,
    List<Zone> zones,
  });
}

/// @nodoc
class _$SubsystemCopyWithImpl<$Res, $Val extends Subsystem>
    implements $SubsystemCopyWith<$Res> {
  _$SubsystemCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of Subsystem
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? hikSubsystemId = null,
    Object? subsystemNumber = null,
    Object? status = null,
    Object? zones = null,
  }) {
    return _then(
      _value.copyWith(
            id: null == id
                ? _value.id
                : id // ignore: cast_nullable_to_non_nullable
                      as String,
            name: null == name
                ? _value.name
                : name // ignore: cast_nullable_to_non_nullable
                      as String,
            hikSubsystemId: null == hikSubsystemId
                ? _value.hikSubsystemId
                : hikSubsystemId // ignore: cast_nullable_to_non_nullable
                      as String,
            subsystemNumber: null == subsystemNumber
                ? _value.subsystemNumber
                : subsystemNumber // ignore: cast_nullable_to_non_nullable
                      as int,
            status: null == status
                ? _value.status
                : status // ignore: cast_nullable_to_non_nullable
                      as String,
            zones: null == zones
                ? _value.zones
                : zones // ignore: cast_nullable_to_non_nullable
                      as List<Zone>,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$SubsystemImplCopyWith<$Res>
    implements $SubsystemCopyWith<$Res> {
  factory _$$SubsystemImplCopyWith(
    _$SubsystemImpl value,
    $Res Function(_$SubsystemImpl) then,
  ) = __$$SubsystemImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    String id,
    String name,
    @JsonKey(name: 'hikSubsystemId') String hikSubsystemId,
    @JsonKey(name: 'subsystemNumber') int subsystemNumber,
    String status,
    List<Zone> zones,
  });
}

/// @nodoc
class __$$SubsystemImplCopyWithImpl<$Res>
    extends _$SubsystemCopyWithImpl<$Res, _$SubsystemImpl>
    implements _$$SubsystemImplCopyWith<$Res> {
  __$$SubsystemImplCopyWithImpl(
    _$SubsystemImpl _value,
    $Res Function(_$SubsystemImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of Subsystem
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? hikSubsystemId = null,
    Object? subsystemNumber = null,
    Object? status = null,
    Object? zones = null,
  }) {
    return _then(
      _$SubsystemImpl(
        id: null == id
            ? _value.id
            : id // ignore: cast_nullable_to_non_nullable
                  as String,
        name: null == name
            ? _value.name
            : name // ignore: cast_nullable_to_non_nullable
                  as String,
        hikSubsystemId: null == hikSubsystemId
            ? _value.hikSubsystemId
            : hikSubsystemId // ignore: cast_nullable_to_non_nullable
                  as String,
        subsystemNumber: null == subsystemNumber
            ? _value.subsystemNumber
            : subsystemNumber // ignore: cast_nullable_to_non_nullable
                  as int,
        status: null == status
            ? _value.status
            : status // ignore: cast_nullable_to_non_nullable
                  as String,
        zones: null == zones
            ? _value._zones
            : zones // ignore: cast_nullable_to_non_nullable
                  as List<Zone>,
      ),
    );
  }
}

/// @nodoc

@JsonSerializable(fieldRename: FieldRename.snake)
class _$SubsystemImpl implements _Subsystem {
  const _$SubsystemImpl({
    this.id = '',
    this.name = '',
    @JsonKey(name: 'hikSubsystemId') this.hikSubsystemId = '',
    @JsonKey(name: 'subsystemNumber') this.subsystemNumber = 0,
    this.status = 'disarmed',
    final List<Zone> zones = const [],
  }) : _zones = zones;

  factory _$SubsystemImpl.fromJson(Map<String, dynamic> json) =>
      _$$SubsystemImplFromJson(json);

  @override
  @JsonKey()
  final String id;
  @override
  @JsonKey()
  final String name;
  @override
  @JsonKey(name: 'hikSubsystemId')
  final String hikSubsystemId;
  @override
  @JsonKey(name: 'subsystemNumber')
  final int subsystemNumber;
  @override
  @JsonKey()
  final String status;
  final List<Zone> _zones;
  @override
  @JsonKey()
  List<Zone> get zones {
    if (_zones is EqualUnmodifiableListView) return _zones;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_zones);
  }

  @override
  String toString() {
    return 'Subsystem(id: $id, name: $name, hikSubsystemId: $hikSubsystemId, subsystemNumber: $subsystemNumber, status: $status, zones: $zones)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$SubsystemImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.hikSubsystemId, hikSubsystemId) ||
                other.hikSubsystemId == hikSubsystemId) &&
            (identical(other.subsystemNumber, subsystemNumber) ||
                other.subsystemNumber == subsystemNumber) &&
            (identical(other.status, status) || other.status == status) &&
            const DeepCollectionEquality().equals(other._zones, _zones));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    id,
    name,
    hikSubsystemId,
    subsystemNumber,
    status,
    const DeepCollectionEquality().hash(_zones),
  );

  /// Create a copy of Subsystem
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$SubsystemImplCopyWith<_$SubsystemImpl> get copyWith =>
      __$$SubsystemImplCopyWithImpl<_$SubsystemImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$SubsystemImplToJson(this);
  }
}

abstract class _Subsystem implements Subsystem {
  const factory _Subsystem({
    final String id,
    final String name,
    @JsonKey(name: 'hikSubsystemId') final String hikSubsystemId,
    @JsonKey(name: 'subsystemNumber') final int subsystemNumber,
    final String status,
    final List<Zone> zones,
  }) = _$SubsystemImpl;

  factory _Subsystem.fromJson(Map<String, dynamic> json) =
      _$SubsystemImpl.fromJson;

  @override
  String get id;
  @override
  String get name;
  @override
  @JsonKey(name: 'hikSubsystemId')
  String get hikSubsystemId;
  @override
  @JsonKey(name: 'subsystemNumber')
  int get subsystemNumber;
  @override
  String get status;
  @override
  List<Zone> get zones;

  /// Create a copy of Subsystem
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$SubsystemImplCopyWith<_$SubsystemImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

AlarmPanelDevice _$AlarmPanelDeviceFromJson(Map<String, dynamic> json) {
  return _AlarmPanelDevice.fromJson(json);
}

/// @nodoc
mixin _$AlarmPanelDevice {
  String get id => throw _privateConstructorUsedError;
  String get site => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  @JsonKey(name: 'serialNumber')
  String get serialNumber => throw _privateConstructorUsedError;
  @JsonKey(name: 'hikDeviceId')
  String get hikDeviceId => throw _privateConstructorUsedError;
  @JsonKey(name: 'deviceType')
  String get deviceType => throw _privateConstructorUsedError;
  @JsonKey(name: 'isOnline')
  bool get isOnline => throw _privateConstructorUsedError;
  @JsonKey(name: 'firmwareVersion')
  String get firmwareVersion => throw _privateConstructorUsedError;
  @JsonKey(name: 'hardwareVersion')
  String get hardwareVersion => throw _privateConstructorUsedError;
  @JsonKey(name: 'modelNumber')
  String get modelNumber => throw _privateConstructorUsedError;
  DateTime? get lastSeen => throw _privateConstructorUsedError;
  List<Subsystem> get subsystems => throw _privateConstructorUsedError;

  /// Serializes this AlarmPanelDevice to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of AlarmPanelDevice
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $AlarmPanelDeviceCopyWith<AlarmPanelDevice> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $AlarmPanelDeviceCopyWith<$Res> {
  factory $AlarmPanelDeviceCopyWith(
    AlarmPanelDevice value,
    $Res Function(AlarmPanelDevice) then,
  ) = _$AlarmPanelDeviceCopyWithImpl<$Res, AlarmPanelDevice>;
  @useResult
  $Res call({
    String id,
    String site,
    String name,
    @JsonKey(name: 'serialNumber') String serialNumber,
    @JsonKey(name: 'hikDeviceId') String hikDeviceId,
    @JsonKey(name: 'deviceType') String deviceType,
    @JsonKey(name: 'isOnline') bool isOnline,
    @JsonKey(name: 'firmwareVersion') String firmwareVersion,
    @JsonKey(name: 'hardwareVersion') String hardwareVersion,
    @JsonKey(name: 'modelNumber') String modelNumber,
    DateTime? lastSeen,
    List<Subsystem> subsystems,
  });
}

/// @nodoc
class _$AlarmPanelDeviceCopyWithImpl<$Res, $Val extends AlarmPanelDevice>
    implements $AlarmPanelDeviceCopyWith<$Res> {
  _$AlarmPanelDeviceCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of AlarmPanelDevice
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? site = null,
    Object? name = null,
    Object? serialNumber = null,
    Object? hikDeviceId = null,
    Object? deviceType = null,
    Object? isOnline = null,
    Object? firmwareVersion = null,
    Object? hardwareVersion = null,
    Object? modelNumber = null,
    Object? lastSeen = freezed,
    Object? subsystems = null,
  }) {
    return _then(
      _value.copyWith(
            id: null == id
                ? _value.id
                : id // ignore: cast_nullable_to_non_nullable
                      as String,
            site: null == site
                ? _value.site
                : site // ignore: cast_nullable_to_non_nullable
                      as String,
            name: null == name
                ? _value.name
                : name // ignore: cast_nullable_to_non_nullable
                      as String,
            serialNumber: null == serialNumber
                ? _value.serialNumber
                : serialNumber // ignore: cast_nullable_to_non_nullable
                      as String,
            hikDeviceId: null == hikDeviceId
                ? _value.hikDeviceId
                : hikDeviceId // ignore: cast_nullable_to_non_nullable
                      as String,
            deviceType: null == deviceType
                ? _value.deviceType
                : deviceType // ignore: cast_nullable_to_non_nullable
                      as String,
            isOnline: null == isOnline
                ? _value.isOnline
                : isOnline // ignore: cast_nullable_to_non_nullable
                      as bool,
            firmwareVersion: null == firmwareVersion
                ? _value.firmwareVersion
                : firmwareVersion // ignore: cast_nullable_to_non_nullable
                      as String,
            hardwareVersion: null == hardwareVersion
                ? _value.hardwareVersion
                : hardwareVersion // ignore: cast_nullable_to_non_nullable
                      as String,
            modelNumber: null == modelNumber
                ? _value.modelNumber
                : modelNumber // ignore: cast_nullable_to_non_nullable
                      as String,
            lastSeen: freezed == lastSeen
                ? _value.lastSeen
                : lastSeen // ignore: cast_nullable_to_non_nullable
                      as DateTime?,
            subsystems: null == subsystems
                ? _value.subsystems
                : subsystems // ignore: cast_nullable_to_non_nullable
                      as List<Subsystem>,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$AlarmPanelDeviceImplCopyWith<$Res>
    implements $AlarmPanelDeviceCopyWith<$Res> {
  factory _$$AlarmPanelDeviceImplCopyWith(
    _$AlarmPanelDeviceImpl value,
    $Res Function(_$AlarmPanelDeviceImpl) then,
  ) = __$$AlarmPanelDeviceImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    String id,
    String site,
    String name,
    @JsonKey(name: 'serialNumber') String serialNumber,
    @JsonKey(name: 'hikDeviceId') String hikDeviceId,
    @JsonKey(name: 'deviceType') String deviceType,
    @JsonKey(name: 'isOnline') bool isOnline,
    @JsonKey(name: 'firmwareVersion') String firmwareVersion,
    @JsonKey(name: 'hardwareVersion') String hardwareVersion,
    @JsonKey(name: 'modelNumber') String modelNumber,
    DateTime? lastSeen,
    List<Subsystem> subsystems,
  });
}

/// @nodoc
class __$$AlarmPanelDeviceImplCopyWithImpl<$Res>
    extends _$AlarmPanelDeviceCopyWithImpl<$Res, _$AlarmPanelDeviceImpl>
    implements _$$AlarmPanelDeviceImplCopyWith<$Res> {
  __$$AlarmPanelDeviceImplCopyWithImpl(
    _$AlarmPanelDeviceImpl _value,
    $Res Function(_$AlarmPanelDeviceImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of AlarmPanelDevice
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? site = null,
    Object? name = null,
    Object? serialNumber = null,
    Object? hikDeviceId = null,
    Object? deviceType = null,
    Object? isOnline = null,
    Object? firmwareVersion = null,
    Object? hardwareVersion = null,
    Object? modelNumber = null,
    Object? lastSeen = freezed,
    Object? subsystems = null,
  }) {
    return _then(
      _$AlarmPanelDeviceImpl(
        id: null == id
            ? _value.id
            : id // ignore: cast_nullable_to_non_nullable
                  as String,
        site: null == site
            ? _value.site
            : site // ignore: cast_nullable_to_non_nullable
                  as String,
        name: null == name
            ? _value.name
            : name // ignore: cast_nullable_to_non_nullable
                  as String,
        serialNumber: null == serialNumber
            ? _value.serialNumber
            : serialNumber // ignore: cast_nullable_to_non_nullable
                  as String,
        hikDeviceId: null == hikDeviceId
            ? _value.hikDeviceId
            : hikDeviceId // ignore: cast_nullable_to_non_nullable
                  as String,
        deviceType: null == deviceType
            ? _value.deviceType
            : deviceType // ignore: cast_nullable_to_non_nullable
                  as String,
        isOnline: null == isOnline
            ? _value.isOnline
            : isOnline // ignore: cast_nullable_to_non_nullable
                  as bool,
        firmwareVersion: null == firmwareVersion
            ? _value.firmwareVersion
            : firmwareVersion // ignore: cast_nullable_to_non_nullable
                  as String,
        hardwareVersion: null == hardwareVersion
            ? _value.hardwareVersion
            : hardwareVersion // ignore: cast_nullable_to_non_nullable
                  as String,
        modelNumber: null == modelNumber
            ? _value.modelNumber
            : modelNumber // ignore: cast_nullable_to_non_nullable
                  as String,
        lastSeen: freezed == lastSeen
            ? _value.lastSeen
            : lastSeen // ignore: cast_nullable_to_non_nullable
                  as DateTime?,
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
class _$AlarmPanelDeviceImpl implements _AlarmPanelDevice {
  const _$AlarmPanelDeviceImpl({
    this.id = '',
    this.site = '',
    this.name = '',
    @JsonKey(name: 'serialNumber') this.serialNumber = '',
    @JsonKey(name: 'hikDeviceId') this.hikDeviceId = '',
    @JsonKey(name: 'deviceType') this.deviceType = 'panel',
    @JsonKey(name: 'isOnline') this.isOnline = true,
    @JsonKey(name: 'firmwareVersion') this.firmwareVersion = '',
    @JsonKey(name: 'hardwareVersion') this.hardwareVersion = '',
    @JsonKey(name: 'modelNumber') this.modelNumber = '',
    this.lastSeen,
    final List<Subsystem> subsystems = const [],
  }) : _subsystems = subsystems;

  factory _$AlarmPanelDeviceImpl.fromJson(Map<String, dynamic> json) =>
      _$$AlarmPanelDeviceImplFromJson(json);

  @override
  @JsonKey()
  final String id;
  @override
  @JsonKey()
  final String site;
  @override
  @JsonKey()
  final String name;
  @override
  @JsonKey(name: 'serialNumber')
  final String serialNumber;
  @override
  @JsonKey(name: 'hikDeviceId')
  final String hikDeviceId;
  @override
  @JsonKey(name: 'deviceType')
  final String deviceType;
  @override
  @JsonKey(name: 'isOnline')
  final bool isOnline;
  @override
  @JsonKey(name: 'firmwareVersion')
  final String firmwareVersion;
  @override
  @JsonKey(name: 'hardwareVersion')
  final String hardwareVersion;
  @override
  @JsonKey(name: 'modelNumber')
  final String modelNumber;
  @override
  final DateTime? lastSeen;
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
    return 'AlarmPanelDevice(id: $id, site: $site, name: $name, serialNumber: $serialNumber, hikDeviceId: $hikDeviceId, deviceType: $deviceType, isOnline: $isOnline, firmwareVersion: $firmwareVersion, hardwareVersion: $hardwareVersion, modelNumber: $modelNumber, lastSeen: $lastSeen, subsystems: $subsystems)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$AlarmPanelDeviceImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.site, site) || other.site == site) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.serialNumber, serialNumber) ||
                other.serialNumber == serialNumber) &&
            (identical(other.hikDeviceId, hikDeviceId) ||
                other.hikDeviceId == hikDeviceId) &&
            (identical(other.deviceType, deviceType) ||
                other.deviceType == deviceType) &&
            (identical(other.isOnline, isOnline) ||
                other.isOnline == isOnline) &&
            (identical(other.firmwareVersion, firmwareVersion) ||
                other.firmwareVersion == firmwareVersion) &&
            (identical(other.hardwareVersion, hardwareVersion) ||
                other.hardwareVersion == hardwareVersion) &&
            (identical(other.modelNumber, modelNumber) ||
                other.modelNumber == modelNumber) &&
            (identical(other.lastSeen, lastSeen) ||
                other.lastSeen == lastSeen) &&
            const DeepCollectionEquality().equals(
              other._subsystems,
              _subsystems,
            ));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    id,
    site,
    name,
    serialNumber,
    hikDeviceId,
    deviceType,
    isOnline,
    firmwareVersion,
    hardwareVersion,
    modelNumber,
    lastSeen,
    const DeepCollectionEquality().hash(_subsystems),
  );

  /// Create a copy of AlarmPanelDevice
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$AlarmPanelDeviceImplCopyWith<_$AlarmPanelDeviceImpl> get copyWith =>
      __$$AlarmPanelDeviceImplCopyWithImpl<_$AlarmPanelDeviceImpl>(
        this,
        _$identity,
      );

  @override
  Map<String, dynamic> toJson() {
    return _$$AlarmPanelDeviceImplToJson(this);
  }
}

abstract class _AlarmPanelDevice implements AlarmPanelDevice {
  const factory _AlarmPanelDevice({
    final String id,
    final String site,
    final String name,
    @JsonKey(name: 'serialNumber') final String serialNumber,
    @JsonKey(name: 'hikDeviceId') final String hikDeviceId,
    @JsonKey(name: 'deviceType') final String deviceType,
    @JsonKey(name: 'isOnline') final bool isOnline,
    @JsonKey(name: 'firmwareVersion') final String firmwareVersion,
    @JsonKey(name: 'hardwareVersion') final String hardwareVersion,
    @JsonKey(name: 'modelNumber') final String modelNumber,
    final DateTime? lastSeen,
    final List<Subsystem> subsystems,
  }) = _$AlarmPanelDeviceImpl;

  factory _AlarmPanelDevice.fromJson(Map<String, dynamic> json) =
      _$AlarmPanelDeviceImpl.fromJson;

  @override
  String get id;
  @override
  String get site;
  @override
  String get name;
  @override
  @JsonKey(name: 'serialNumber')
  String get serialNumber;
  @override
  @JsonKey(name: 'hikDeviceId')
  String get hikDeviceId;
  @override
  @JsonKey(name: 'deviceType')
  String get deviceType;
  @override
  @JsonKey(name: 'isOnline')
  bool get isOnline;
  @override
  @JsonKey(name: 'firmwareVersion')
  String get firmwareVersion;
  @override
  @JsonKey(name: 'hardwareVersion')
  String get hardwareVersion;
  @override
  @JsonKey(name: 'modelNumber')
  String get modelNumber;
  @override
  DateTime? get lastSeen;
  @override
  List<Subsystem> get subsystems;

  /// Create a copy of AlarmPanelDevice
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$AlarmPanelDeviceImplCopyWith<_$AlarmPanelDeviceImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

VideoChannel _$VideoChannelFromJson(Map<String, dynamic> json) {
  return _VideoChannel.fromJson(json);
}

/// @nodoc
mixin _$VideoChannel {
  String get id => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  @JsonKey(name: 'hikChannelId')
  String get hikChannelId => throw _privateConstructorUsedError;
  @JsonKey(name: 'channelNumber')
  int get channelNumber => throw _privateConstructorUsedError;
  @JsonKey(name: 'isOnline')
  bool get isOnline => throw _privateConstructorUsedError;

  /// Serializes this VideoChannel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of VideoChannel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $VideoChannelCopyWith<VideoChannel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $VideoChannelCopyWith<$Res> {
  factory $VideoChannelCopyWith(
    VideoChannel value,
    $Res Function(VideoChannel) then,
  ) = _$VideoChannelCopyWithImpl<$Res, VideoChannel>;
  @useResult
  $Res call({
    String id,
    String name,
    @JsonKey(name: 'hikChannelId') String hikChannelId,
    @JsonKey(name: 'channelNumber') int channelNumber,
    @JsonKey(name: 'isOnline') bool isOnline,
  });
}

/// @nodoc
class _$VideoChannelCopyWithImpl<$Res, $Val extends VideoChannel>
    implements $VideoChannelCopyWith<$Res> {
  _$VideoChannelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of VideoChannel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? hikChannelId = null,
    Object? channelNumber = null,
    Object? isOnline = null,
  }) {
    return _then(
      _value.copyWith(
            id: null == id
                ? _value.id
                : id // ignore: cast_nullable_to_non_nullable
                      as String,
            name: null == name
                ? _value.name
                : name // ignore: cast_nullable_to_non_nullable
                      as String,
            hikChannelId: null == hikChannelId
                ? _value.hikChannelId
                : hikChannelId // ignore: cast_nullable_to_non_nullable
                      as String,
            channelNumber: null == channelNumber
                ? _value.channelNumber
                : channelNumber // ignore: cast_nullable_to_non_nullable
                      as int,
            isOnline: null == isOnline
                ? _value.isOnline
                : isOnline // ignore: cast_nullable_to_non_nullable
                      as bool,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$VideoChannelImplCopyWith<$Res>
    implements $VideoChannelCopyWith<$Res> {
  factory _$$VideoChannelImplCopyWith(
    _$VideoChannelImpl value,
    $Res Function(_$VideoChannelImpl) then,
  ) = __$$VideoChannelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    String id,
    String name,
    @JsonKey(name: 'hikChannelId') String hikChannelId,
    @JsonKey(name: 'channelNumber') int channelNumber,
    @JsonKey(name: 'isOnline') bool isOnline,
  });
}

/// @nodoc
class __$$VideoChannelImplCopyWithImpl<$Res>
    extends _$VideoChannelCopyWithImpl<$Res, _$VideoChannelImpl>
    implements _$$VideoChannelImplCopyWith<$Res> {
  __$$VideoChannelImplCopyWithImpl(
    _$VideoChannelImpl _value,
    $Res Function(_$VideoChannelImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of VideoChannel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? hikChannelId = null,
    Object? channelNumber = null,
    Object? isOnline = null,
  }) {
    return _then(
      _$VideoChannelImpl(
        id: null == id
            ? _value.id
            : id // ignore: cast_nullable_to_non_nullable
                  as String,
        name: null == name
            ? _value.name
            : name // ignore: cast_nullable_to_non_nullable
                  as String,
        hikChannelId: null == hikChannelId
            ? _value.hikChannelId
            : hikChannelId // ignore: cast_nullable_to_non_nullable
                  as String,
        channelNumber: null == channelNumber
            ? _value.channelNumber
            : channelNumber // ignore: cast_nullable_to_non_nullable
                  as int,
        isOnline: null == isOnline
            ? _value.isOnline
            : isOnline // ignore: cast_nullable_to_non_nullable
                  as bool,
      ),
    );
  }
}

/// @nodoc

@JsonSerializable(fieldRename: FieldRename.snake)
class _$VideoChannelImpl implements _VideoChannel {
  const _$VideoChannelImpl({
    this.id = '',
    this.name = '',
    @JsonKey(name: 'hikChannelId') this.hikChannelId = '',
    @JsonKey(name: 'channelNumber') this.channelNumber = 0,
    @JsonKey(name: 'isOnline') this.isOnline = true,
  });

  factory _$VideoChannelImpl.fromJson(Map<String, dynamic> json) =>
      _$$VideoChannelImplFromJson(json);

  @override
  @JsonKey()
  final String id;
  @override
  @JsonKey()
  final String name;
  @override
  @JsonKey(name: 'hikChannelId')
  final String hikChannelId;
  @override
  @JsonKey(name: 'channelNumber')
  final int channelNumber;
  @override
  @JsonKey(name: 'isOnline')
  final bool isOnline;

  @override
  String toString() {
    return 'VideoChannel(id: $id, name: $name, hikChannelId: $hikChannelId, channelNumber: $channelNumber, isOnline: $isOnline)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$VideoChannelImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.hikChannelId, hikChannelId) ||
                other.hikChannelId == hikChannelId) &&
            (identical(other.channelNumber, channelNumber) ||
                other.channelNumber == channelNumber) &&
            (identical(other.isOnline, isOnline) ||
                other.isOnline == isOnline));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode =>
      Object.hash(runtimeType, id, name, hikChannelId, channelNumber, isOnline);

  /// Create a copy of VideoChannel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$VideoChannelImplCopyWith<_$VideoChannelImpl> get copyWith =>
      __$$VideoChannelImplCopyWithImpl<_$VideoChannelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$VideoChannelImplToJson(this);
  }
}

abstract class _VideoChannel implements VideoChannel {
  const factory _VideoChannel({
    final String id,
    final String name,
    @JsonKey(name: 'hikChannelId') final String hikChannelId,
    @JsonKey(name: 'channelNumber') final int channelNumber,
    @JsonKey(name: 'isOnline') final bool isOnline,
  }) = _$VideoChannelImpl;

  factory _VideoChannel.fromJson(Map<String, dynamic> json) =
      _$VideoChannelImpl.fromJson;

  @override
  String get id;
  @override
  String get name;
  @override
  @JsonKey(name: 'hikChannelId')
  String get hikChannelId;
  @override
  @JsonKey(name: 'channelNumber')
  int get channelNumber;
  @override
  @JsonKey(name: 'isOnline')
  bool get isOnline;

  /// Create a copy of VideoChannel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$VideoChannelImplCopyWith<_$VideoChannelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

VideoDevice _$VideoDeviceFromJson(Map<String, dynamic> json) {
  return _VideoDevice.fromJson(json);
}

/// @nodoc
mixin _$VideoDevice {
  String get id => throw _privateConstructorUsedError;
  String get site => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  @JsonKey(name: 'serialNumber')
  String get serialNumber => throw _privateConstructorUsedError;
  @JsonKey(name: 'hikDeviceId')
  String get hikDeviceId => throw _privateConstructorUsedError;
  @JsonKey(name: 'deviceType')
  String get deviceType => throw _privateConstructorUsedError;
  @JsonKey(name: 'isOnline')
  bool get isOnline => throw _privateConstructorUsedError;
  @JsonKey(name: 'firmwareVersion')
  String get firmwareVersion => throw _privateConstructorUsedError;
  @JsonKey(name: 'hardwareVersion')
  String get hardwareVersion => throw _privateConstructorUsedError;
  @JsonKey(name: 'modelNumber')
  String get modelNumber => throw _privateConstructorUsedError;
  DateTime? get lastSeen => throw _privateConstructorUsedError;
  List<VideoChannel> get channels => throw _privateConstructorUsedError;

  /// Serializes this VideoDevice to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of VideoDevice
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $VideoDeviceCopyWith<VideoDevice> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $VideoDeviceCopyWith<$Res> {
  factory $VideoDeviceCopyWith(
    VideoDevice value,
    $Res Function(VideoDevice) then,
  ) = _$VideoDeviceCopyWithImpl<$Res, VideoDevice>;
  @useResult
  $Res call({
    String id,
    String site,
    String name,
    @JsonKey(name: 'serialNumber') String serialNumber,
    @JsonKey(name: 'hikDeviceId') String hikDeviceId,
    @JsonKey(name: 'deviceType') String deviceType,
    @JsonKey(name: 'isOnline') bool isOnline,
    @JsonKey(name: 'firmwareVersion') String firmwareVersion,
    @JsonKey(name: 'hardwareVersion') String hardwareVersion,
    @JsonKey(name: 'modelNumber') String modelNumber,
    DateTime? lastSeen,
    List<VideoChannel> channels,
  });
}

/// @nodoc
class _$VideoDeviceCopyWithImpl<$Res, $Val extends VideoDevice>
    implements $VideoDeviceCopyWith<$Res> {
  _$VideoDeviceCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of VideoDevice
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? site = null,
    Object? name = null,
    Object? serialNumber = null,
    Object? hikDeviceId = null,
    Object? deviceType = null,
    Object? isOnline = null,
    Object? firmwareVersion = null,
    Object? hardwareVersion = null,
    Object? modelNumber = null,
    Object? lastSeen = freezed,
    Object? channels = null,
  }) {
    return _then(
      _value.copyWith(
            id: null == id
                ? _value.id
                : id // ignore: cast_nullable_to_non_nullable
                      as String,
            site: null == site
                ? _value.site
                : site // ignore: cast_nullable_to_non_nullable
                      as String,
            name: null == name
                ? _value.name
                : name // ignore: cast_nullable_to_non_nullable
                      as String,
            serialNumber: null == serialNumber
                ? _value.serialNumber
                : serialNumber // ignore: cast_nullable_to_non_nullable
                      as String,
            hikDeviceId: null == hikDeviceId
                ? _value.hikDeviceId
                : hikDeviceId // ignore: cast_nullable_to_non_nullable
                      as String,
            deviceType: null == deviceType
                ? _value.deviceType
                : deviceType // ignore: cast_nullable_to_non_nullable
                      as String,
            isOnline: null == isOnline
                ? _value.isOnline
                : isOnline // ignore: cast_nullable_to_non_nullable
                      as bool,
            firmwareVersion: null == firmwareVersion
                ? _value.firmwareVersion
                : firmwareVersion // ignore: cast_nullable_to_non_nullable
                      as String,
            hardwareVersion: null == hardwareVersion
                ? _value.hardwareVersion
                : hardwareVersion // ignore: cast_nullable_to_non_nullable
                      as String,
            modelNumber: null == modelNumber
                ? _value.modelNumber
                : modelNumber // ignore: cast_nullable_to_non_nullable
                      as String,
            lastSeen: freezed == lastSeen
                ? _value.lastSeen
                : lastSeen // ignore: cast_nullable_to_non_nullable
                      as DateTime?,
            channels: null == channels
                ? _value.channels
                : channels // ignore: cast_nullable_to_non_nullable
                      as List<VideoChannel>,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$VideoDeviceImplCopyWith<$Res>
    implements $VideoDeviceCopyWith<$Res> {
  factory _$$VideoDeviceImplCopyWith(
    _$VideoDeviceImpl value,
    $Res Function(_$VideoDeviceImpl) then,
  ) = __$$VideoDeviceImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    String id,
    String site,
    String name,
    @JsonKey(name: 'serialNumber') String serialNumber,
    @JsonKey(name: 'hikDeviceId') String hikDeviceId,
    @JsonKey(name: 'deviceType') String deviceType,
    @JsonKey(name: 'isOnline') bool isOnline,
    @JsonKey(name: 'firmwareVersion') String firmwareVersion,
    @JsonKey(name: 'hardwareVersion') String hardwareVersion,
    @JsonKey(name: 'modelNumber') String modelNumber,
    DateTime? lastSeen,
    List<VideoChannel> channels,
  });
}

/// @nodoc
class __$$VideoDeviceImplCopyWithImpl<$Res>
    extends _$VideoDeviceCopyWithImpl<$Res, _$VideoDeviceImpl>
    implements _$$VideoDeviceImplCopyWith<$Res> {
  __$$VideoDeviceImplCopyWithImpl(
    _$VideoDeviceImpl _value,
    $Res Function(_$VideoDeviceImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of VideoDevice
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? site = null,
    Object? name = null,
    Object? serialNumber = null,
    Object? hikDeviceId = null,
    Object? deviceType = null,
    Object? isOnline = null,
    Object? firmwareVersion = null,
    Object? hardwareVersion = null,
    Object? modelNumber = null,
    Object? lastSeen = freezed,
    Object? channels = null,
  }) {
    return _then(
      _$VideoDeviceImpl(
        id: null == id
            ? _value.id
            : id // ignore: cast_nullable_to_non_nullable
                  as String,
        site: null == site
            ? _value.site
            : site // ignore: cast_nullable_to_non_nullable
                  as String,
        name: null == name
            ? _value.name
            : name // ignore: cast_nullable_to_non_nullable
                  as String,
        serialNumber: null == serialNumber
            ? _value.serialNumber
            : serialNumber // ignore: cast_nullable_to_non_nullable
                  as String,
        hikDeviceId: null == hikDeviceId
            ? _value.hikDeviceId
            : hikDeviceId // ignore: cast_nullable_to_non_nullable
                  as String,
        deviceType: null == deviceType
            ? _value.deviceType
            : deviceType // ignore: cast_nullable_to_non_nullable
                  as String,
        isOnline: null == isOnline
            ? _value.isOnline
            : isOnline // ignore: cast_nullable_to_non_nullable
                  as bool,
        firmwareVersion: null == firmwareVersion
            ? _value.firmwareVersion
            : firmwareVersion // ignore: cast_nullable_to_non_nullable
                  as String,
        hardwareVersion: null == hardwareVersion
            ? _value.hardwareVersion
            : hardwareVersion // ignore: cast_nullable_to_non_nullable
                  as String,
        modelNumber: null == modelNumber
            ? _value.modelNumber
            : modelNumber // ignore: cast_nullable_to_non_nullable
                  as String,
        lastSeen: freezed == lastSeen
            ? _value.lastSeen
            : lastSeen // ignore: cast_nullable_to_non_nullable
                  as DateTime?,
        channels: null == channels
            ? _value._channels
            : channels // ignore: cast_nullable_to_non_nullable
                  as List<VideoChannel>,
      ),
    );
  }
}

/// @nodoc

@JsonSerializable(fieldRename: FieldRename.snake)
class _$VideoDeviceImpl implements _VideoDevice {
  const _$VideoDeviceImpl({
    this.id = '',
    this.site = '',
    this.name = '',
    @JsonKey(name: 'serialNumber') this.serialNumber = '',
    @JsonKey(name: 'hikDeviceId') this.hikDeviceId = '',
    @JsonKey(name: 'deviceType') this.deviceType = 'nvr',
    @JsonKey(name: 'isOnline') this.isOnline = true,
    @JsonKey(name: 'firmwareVersion') this.firmwareVersion = '',
    @JsonKey(name: 'hardwareVersion') this.hardwareVersion = '',
    @JsonKey(name: 'modelNumber') this.modelNumber = '',
    this.lastSeen,
    final List<VideoChannel> channels = const [],
  }) : _channels = channels;

  factory _$VideoDeviceImpl.fromJson(Map<String, dynamic> json) =>
      _$$VideoDeviceImplFromJson(json);

  @override
  @JsonKey()
  final String id;
  @override
  @JsonKey()
  final String site;
  @override
  @JsonKey()
  final String name;
  @override
  @JsonKey(name: 'serialNumber')
  final String serialNumber;
  @override
  @JsonKey(name: 'hikDeviceId')
  final String hikDeviceId;
  @override
  @JsonKey(name: 'deviceType')
  final String deviceType;
  @override
  @JsonKey(name: 'isOnline')
  final bool isOnline;
  @override
  @JsonKey(name: 'firmwareVersion')
  final String firmwareVersion;
  @override
  @JsonKey(name: 'hardwareVersion')
  final String hardwareVersion;
  @override
  @JsonKey(name: 'modelNumber')
  final String modelNumber;
  @override
  final DateTime? lastSeen;
  final List<VideoChannel> _channels;
  @override
  @JsonKey()
  List<VideoChannel> get channels {
    if (_channels is EqualUnmodifiableListView) return _channels;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_channels);
  }

  @override
  String toString() {
    return 'VideoDevice(id: $id, site: $site, name: $name, serialNumber: $serialNumber, hikDeviceId: $hikDeviceId, deviceType: $deviceType, isOnline: $isOnline, firmwareVersion: $firmwareVersion, hardwareVersion: $hardwareVersion, modelNumber: $modelNumber, lastSeen: $lastSeen, channels: $channels)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$VideoDeviceImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.site, site) || other.site == site) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.serialNumber, serialNumber) ||
                other.serialNumber == serialNumber) &&
            (identical(other.hikDeviceId, hikDeviceId) ||
                other.hikDeviceId == hikDeviceId) &&
            (identical(other.deviceType, deviceType) ||
                other.deviceType == deviceType) &&
            (identical(other.isOnline, isOnline) ||
                other.isOnline == isOnline) &&
            (identical(other.firmwareVersion, firmwareVersion) ||
                other.firmwareVersion == firmwareVersion) &&
            (identical(other.hardwareVersion, hardwareVersion) ||
                other.hardwareVersion == hardwareVersion) &&
            (identical(other.modelNumber, modelNumber) ||
                other.modelNumber == modelNumber) &&
            (identical(other.lastSeen, lastSeen) ||
                other.lastSeen == lastSeen) &&
            const DeepCollectionEquality().equals(other._channels, _channels));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    id,
    site,
    name,
    serialNumber,
    hikDeviceId,
    deviceType,
    isOnline,
    firmwareVersion,
    hardwareVersion,
    modelNumber,
    lastSeen,
    const DeepCollectionEquality().hash(_channels),
  );

  /// Create a copy of VideoDevice
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$VideoDeviceImplCopyWith<_$VideoDeviceImpl> get copyWith =>
      __$$VideoDeviceImplCopyWithImpl<_$VideoDeviceImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$VideoDeviceImplToJson(this);
  }
}

abstract class _VideoDevice implements VideoDevice {
  const factory _VideoDevice({
    final String id,
    final String site,
    final String name,
    @JsonKey(name: 'serialNumber') final String serialNumber,
    @JsonKey(name: 'hikDeviceId') final String hikDeviceId,
    @JsonKey(name: 'deviceType') final String deviceType,
    @JsonKey(name: 'isOnline') final bool isOnline,
    @JsonKey(name: 'firmwareVersion') final String firmwareVersion,
    @JsonKey(name: 'hardwareVersion') final String hardwareVersion,
    @JsonKey(name: 'modelNumber') final String modelNumber,
    final DateTime? lastSeen,
    final List<VideoChannel> channels,
  }) = _$VideoDeviceImpl;

  factory _VideoDevice.fromJson(Map<String, dynamic> json) =
      _$VideoDeviceImpl.fromJson;

  @override
  String get id;
  @override
  String get site;
  @override
  String get name;
  @override
  @JsonKey(name: 'serialNumber')
  String get serialNumber;
  @override
  @JsonKey(name: 'hikDeviceId')
  String get hikDeviceId;
  @override
  @JsonKey(name: 'deviceType')
  String get deviceType;
  @override
  @JsonKey(name: 'isOnline')
  bool get isOnline;
  @override
  @JsonKey(name: 'firmwareVersion')
  String get firmwareVersion;
  @override
  @JsonKey(name: 'hardwareVersion')
  String get hardwareVersion;
  @override
  @JsonKey(name: 'modelNumber')
  String get modelNumber;
  @override
  DateTime? get lastSeen;
  @override
  List<VideoChannel> get channels;

  /// Create a copy of VideoDevice
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$VideoDeviceImplCopyWith<_$VideoDeviceImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

Site _$SiteFromJson(Map<String, dynamic> json) {
  return _Site.fromJson(json);
}

/// @nodoc
mixin _$Site {
  String get id => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  String get address => throw _privateConstructorUsedError;
  String get city => throw _privateConstructorUsedError;
  String get country => throw _privateConstructorUsedError;
  @JsonKey(name: 'hikSiteId')
  String get hikSiteId => throw _privateConstructorUsedError;
  String get timezone => throw _privateConstructorUsedError;
  @JsonKey(name: 'isActive')
  bool get isActive => throw _privateConstructorUsedError;
  bool get canControlAlarm => throw _privateConstructorUsedError;
  List<AlarmPanelDevice> get devices => throw _privateConstructorUsedError;
  List<VideoDevice> get videoDevices => throw _privateConstructorUsedError;
  List<Subsystem> get subsystems => throw _privateConstructorUsedError;

  /// Serializes this Site to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of Site
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $SiteCopyWith<Site> get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $SiteCopyWith<$Res> {
  factory $SiteCopyWith(Site value, $Res Function(Site) then) =
      _$SiteCopyWithImpl<$Res, Site>;
  @useResult
  $Res call({
    String id,
    String name,
    String address,
    String city,
    String country,
    @JsonKey(name: 'hikSiteId') String hikSiteId,
    String timezone,
    @JsonKey(name: 'isActive') bool isActive,
    bool canControlAlarm,
    List<AlarmPanelDevice> devices,
    List<VideoDevice> videoDevices,
    List<Subsystem> subsystems,
  });
}

/// @nodoc
class _$SiteCopyWithImpl<$Res, $Val extends Site>
    implements $SiteCopyWith<$Res> {
  _$SiteCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of Site
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? address = null,
    Object? city = null,
    Object? country = null,
    Object? hikSiteId = null,
    Object? timezone = null,
    Object? isActive = null,
    Object? canControlAlarm = null,
    Object? devices = null,
    Object? videoDevices = null,
    Object? subsystems = null,
  }) {
    return _then(
      _value.copyWith(
            id: null == id
                ? _value.id
                : id // ignore: cast_nullable_to_non_nullable
                      as String,
            name: null == name
                ? _value.name
                : name // ignore: cast_nullable_to_non_nullable
                      as String,
            address: null == address
                ? _value.address
                : address // ignore: cast_nullable_to_non_nullable
                      as String,
            city: null == city
                ? _value.city
                : city // ignore: cast_nullable_to_non_nullable
                      as String,
            country: null == country
                ? _value.country
                : country // ignore: cast_nullable_to_non_nullable
                      as String,
            hikSiteId: null == hikSiteId
                ? _value.hikSiteId
                : hikSiteId // ignore: cast_nullable_to_non_nullable
                      as String,
            timezone: null == timezone
                ? _value.timezone
                : timezone // ignore: cast_nullable_to_non_nullable
                      as String,
            isActive: null == isActive
                ? _value.isActive
                : isActive // ignore: cast_nullable_to_non_nullable
                      as bool,
            canControlAlarm: null == canControlAlarm
                ? _value.canControlAlarm
                : canControlAlarm // ignore: cast_nullable_to_non_nullable
                      as bool,
            devices: null == devices
                ? _value.devices
                : devices // ignore: cast_nullable_to_non_nullable
                      as List<AlarmPanelDevice>,
            videoDevices: null == videoDevices
                ? _value.videoDevices
                : videoDevices // ignore: cast_nullable_to_non_nullable
                      as List<VideoDevice>,
            subsystems: null == subsystems
                ? _value.subsystems
                : subsystems // ignore: cast_nullable_to_non_nullable
                      as List<Subsystem>,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$SiteImplCopyWith<$Res> implements $SiteCopyWith<$Res> {
  factory _$$SiteImplCopyWith(
    _$SiteImpl value,
    $Res Function(_$SiteImpl) then,
  ) = __$$SiteImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    String id,
    String name,
    String address,
    String city,
    String country,
    @JsonKey(name: 'hikSiteId') String hikSiteId,
    String timezone,
    @JsonKey(name: 'isActive') bool isActive,
    bool canControlAlarm,
    List<AlarmPanelDevice> devices,
    List<VideoDevice> videoDevices,
    List<Subsystem> subsystems,
  });
}

/// @nodoc
class __$$SiteImplCopyWithImpl<$Res>
    extends _$SiteCopyWithImpl<$Res, _$SiteImpl>
    implements _$$SiteImplCopyWith<$Res> {
  __$$SiteImplCopyWithImpl(_$SiteImpl _value, $Res Function(_$SiteImpl) _then)
    : super(_value, _then);

  /// Create a copy of Site
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? address = null,
    Object? city = null,
    Object? country = null,
    Object? hikSiteId = null,
    Object? timezone = null,
    Object? isActive = null,
    Object? canControlAlarm = null,
    Object? devices = null,
    Object? videoDevices = null,
    Object? subsystems = null,
  }) {
    return _then(
      _$SiteImpl(
        id: null == id
            ? _value.id
            : id // ignore: cast_nullable_to_non_nullable
                  as String,
        name: null == name
            ? _value.name
            : name // ignore: cast_nullable_to_non_nullable
                  as String,
        address: null == address
            ? _value.address
            : address // ignore: cast_nullable_to_non_nullable
                  as String,
        city: null == city
            ? _value.city
            : city // ignore: cast_nullable_to_non_nullable
                  as String,
        country: null == country
            ? _value.country
            : country // ignore: cast_nullable_to_non_nullable
                  as String,
        hikSiteId: null == hikSiteId
            ? _value.hikSiteId
            : hikSiteId // ignore: cast_nullable_to_non_nullable
                  as String,
        timezone: null == timezone
            ? _value.timezone
            : timezone // ignore: cast_nullable_to_non_nullable
                  as String,
        isActive: null == isActive
            ? _value.isActive
            : isActive // ignore: cast_nullable_to_non_nullable
                  as bool,
        canControlAlarm: null == canControlAlarm
            ? _value.canControlAlarm
            : canControlAlarm // ignore: cast_nullable_to_non_nullable
                  as bool,
        devices: null == devices
            ? _value._devices
            : devices // ignore: cast_nullable_to_non_nullable
                  as List<AlarmPanelDevice>,
        videoDevices: null == videoDevices
            ? _value._videoDevices
            : videoDevices // ignore: cast_nullable_to_non_nullable
                  as List<VideoDevice>,
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
class _$SiteImpl implements _Site {
  const _$SiteImpl({
    this.id = '',
    this.name = '',
    this.address = '',
    this.city = '',
    this.country = '',
    @JsonKey(name: 'hikSiteId') this.hikSiteId = '',
    this.timezone = 'UTC',
    @JsonKey(name: 'isActive') this.isActive = true,
    this.canControlAlarm = false,
    final List<AlarmPanelDevice> devices = const [],
    final List<VideoDevice> videoDevices = const [],
    final List<Subsystem> subsystems = const [],
  }) : _devices = devices,
       _videoDevices = videoDevices,
       _subsystems = subsystems;

  factory _$SiteImpl.fromJson(Map<String, dynamic> json) =>
      _$$SiteImplFromJson(json);

  @override
  @JsonKey()
  final String id;
  @override
  @JsonKey()
  final String name;
  @override
  @JsonKey()
  final String address;
  @override
  @JsonKey()
  final String city;
  @override
  @JsonKey()
  final String country;
  @override
  @JsonKey(name: 'hikSiteId')
  final String hikSiteId;
  @override
  @JsonKey()
  final String timezone;
  @override
  @JsonKey(name: 'isActive')
  final bool isActive;
  @override
  @JsonKey()
  final bool canControlAlarm;
  final List<AlarmPanelDevice> _devices;
  @override
  @JsonKey()
  List<AlarmPanelDevice> get devices {
    if (_devices is EqualUnmodifiableListView) return _devices;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_devices);
  }

  final List<VideoDevice> _videoDevices;
  @override
  @JsonKey()
  List<VideoDevice> get videoDevices {
    if (_videoDevices is EqualUnmodifiableListView) return _videoDevices;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_videoDevices);
  }

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
    return 'Site(id: $id, name: $name, address: $address, city: $city, country: $country, hikSiteId: $hikSiteId, timezone: $timezone, isActive: $isActive, canControlAlarm: $canControlAlarm, devices: $devices, videoDevices: $videoDevices, subsystems: $subsystems)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$SiteImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.address, address) || other.address == address) &&
            (identical(other.city, city) || other.city == city) &&
            (identical(other.country, country) || other.country == country) &&
            (identical(other.hikSiteId, hikSiteId) ||
                other.hikSiteId == hikSiteId) &&
            (identical(other.timezone, timezone) ||
                other.timezone == timezone) &&
            (identical(other.isActive, isActive) ||
                other.isActive == isActive) &&
            (identical(other.canControlAlarm, canControlAlarm) ||
                other.canControlAlarm == canControlAlarm) &&
            const DeepCollectionEquality().equals(other._devices, _devices) &&
            const DeepCollectionEquality().equals(
              other._videoDevices,
              _videoDevices,
            ) &&
            const DeepCollectionEquality().equals(
              other._subsystems,
              _subsystems,
            ));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    id,
    name,
    address,
    city,
    country,
    hikSiteId,
    timezone,
    isActive,
    canControlAlarm,
    const DeepCollectionEquality().hash(_devices),
    const DeepCollectionEquality().hash(_videoDevices),
    const DeepCollectionEquality().hash(_subsystems),
  );

  /// Create a copy of Site
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$SiteImplCopyWith<_$SiteImpl> get copyWith =>
      __$$SiteImplCopyWithImpl<_$SiteImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$SiteImplToJson(this);
  }
}

abstract class _Site implements Site {
  const factory _Site({
    final String id,
    final String name,
    final String address,
    final String city,
    final String country,
    @JsonKey(name: 'hikSiteId') final String hikSiteId,
    final String timezone,
    @JsonKey(name: 'isActive') final bool isActive,
    final bool canControlAlarm,
    final List<AlarmPanelDevice> devices,
    final List<VideoDevice> videoDevices,
    final List<Subsystem> subsystems,
  }) = _$SiteImpl;

  factory _Site.fromJson(Map<String, dynamic> json) = _$SiteImpl.fromJson;

  @override
  String get id;
  @override
  String get name;
  @override
  String get address;
  @override
  String get city;
  @override
  String get country;
  @override
  @JsonKey(name: 'hikSiteId')
  String get hikSiteId;
  @override
  String get timezone;
  @override
  @JsonKey(name: 'isActive')
  bool get isActive;
  @override
  bool get canControlAlarm;
  @override
  List<AlarmPanelDevice> get devices;
  @override
  List<VideoDevice> get videoDevices;
  @override
  List<Subsystem> get subsystems;

  /// Create a copy of Site
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$SiteImplCopyWith<_$SiteImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

PaginatedSites _$PaginatedSitesFromJson(Map<String, dynamic> json) {
  return _PaginatedSites.fromJson(json);
}

/// @nodoc
mixin _$PaginatedSites {
  int get count => throw _privateConstructorUsedError;
  String? get next => throw _privateConstructorUsedError;
  String? get previous => throw _privateConstructorUsedError;
  List<Site> get results => throw _privateConstructorUsedError;

  /// Serializes this PaginatedSites to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of PaginatedSites
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $PaginatedSitesCopyWith<PaginatedSites> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $PaginatedSitesCopyWith<$Res> {
  factory $PaginatedSitesCopyWith(
    PaginatedSites value,
    $Res Function(PaginatedSites) then,
  ) = _$PaginatedSitesCopyWithImpl<$Res, PaginatedSites>;
  @useResult
  $Res call({int count, String? next, String? previous, List<Site> results});
}

/// @nodoc
class _$PaginatedSitesCopyWithImpl<$Res, $Val extends PaginatedSites>
    implements $PaginatedSitesCopyWith<$Res> {
  _$PaginatedSitesCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of PaginatedSites
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
                      as List<Site>,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$PaginatedSitesImplCopyWith<$Res>
    implements $PaginatedSitesCopyWith<$Res> {
  factory _$$PaginatedSitesImplCopyWith(
    _$PaginatedSitesImpl value,
    $Res Function(_$PaginatedSitesImpl) then,
  ) = __$$PaginatedSitesImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({int count, String? next, String? previous, List<Site> results});
}

/// @nodoc
class __$$PaginatedSitesImplCopyWithImpl<$Res>
    extends _$PaginatedSitesCopyWithImpl<$Res, _$PaginatedSitesImpl>
    implements _$$PaginatedSitesImplCopyWith<$Res> {
  __$$PaginatedSitesImplCopyWithImpl(
    _$PaginatedSitesImpl _value,
    $Res Function(_$PaginatedSitesImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of PaginatedSites
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
      _$PaginatedSitesImpl(
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
                  as List<Site>,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$PaginatedSitesImpl implements _PaginatedSites {
  const _$PaginatedSitesImpl({
    required this.count,
    this.next,
    this.previous,
    required final List<Site> results,
  }) : _results = results;

  factory _$PaginatedSitesImpl.fromJson(Map<String, dynamic> json) =>
      _$$PaginatedSitesImplFromJson(json);

  @override
  final int count;
  @override
  final String? next;
  @override
  final String? previous;
  final List<Site> _results;
  @override
  List<Site> get results {
    if (_results is EqualUnmodifiableListView) return _results;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_results);
  }

  @override
  String toString() {
    return 'PaginatedSites(count: $count, next: $next, previous: $previous, results: $results)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$PaginatedSitesImpl &&
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

  /// Create a copy of PaginatedSites
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$PaginatedSitesImplCopyWith<_$PaginatedSitesImpl> get copyWith =>
      __$$PaginatedSitesImplCopyWithImpl<_$PaginatedSitesImpl>(
        this,
        _$identity,
      );

  @override
  Map<String, dynamic> toJson() {
    return _$$PaginatedSitesImplToJson(this);
  }
}

abstract class _PaginatedSites implements PaginatedSites {
  const factory _PaginatedSites({
    required final int count,
    final String? next,
    final String? previous,
    required final List<Site> results,
  }) = _$PaginatedSitesImpl;

  factory _PaginatedSites.fromJson(Map<String, dynamic> json) =
      _$PaginatedSitesImpl.fromJson;

  @override
  int get count;
  @override
  String? get next;
  @override
  String? get previous;
  @override
  List<Site> get results;

  /// Create a copy of PaginatedSites
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$PaginatedSitesImplCopyWith<_$PaginatedSitesImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
