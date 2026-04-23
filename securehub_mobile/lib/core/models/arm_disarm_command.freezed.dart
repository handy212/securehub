// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'arm_disarm_command.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

ArmDisarmCommand _$ArmDisarmCommandFromJson(Map<String, dynamic> json) {
  return _ArmDisarmCommand.fromJson(json);
}

/// @nodoc
mixin _$ArmDisarmCommand {
  String get id => throw _privateConstructorUsedError;
  String get action => throw _privateConstructorUsedError;
  String get status => throw _privateConstructorUsedError;
  String get createdAt =>
      throw _privateConstructorUsedError; // Timestamp when the panel acknowledged the command (added in backend 0004)
  String? get executedAt =>
      throw _privateConstructorUsedError; // Serial of the panel that received the command
  String? get deviceSerial => throw _privateConstructorUsedError;
  String? get subsystem => throw _privateConstructorUsedError;
  String? get requestedBy => throw _privateConstructorUsedError;
  String? get failureReason => throw _privateConstructorUsedError;

  /// Serializes this ArmDisarmCommand to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of ArmDisarmCommand
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $ArmDisarmCommandCopyWith<ArmDisarmCommand> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $ArmDisarmCommandCopyWith<$Res> {
  factory $ArmDisarmCommandCopyWith(
    ArmDisarmCommand value,
    $Res Function(ArmDisarmCommand) then,
  ) = _$ArmDisarmCommandCopyWithImpl<$Res, ArmDisarmCommand>;
  @useResult
  $Res call({
    String id,
    String action,
    String status,
    String createdAt,
    String? executedAt,
    String? deviceSerial,
    String? subsystem,
    String? requestedBy,
    String? failureReason,
  });
}

/// @nodoc
class _$ArmDisarmCommandCopyWithImpl<$Res, $Val extends ArmDisarmCommand>
    implements $ArmDisarmCommandCopyWith<$Res> {
  _$ArmDisarmCommandCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of ArmDisarmCommand
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? action = null,
    Object? status = null,
    Object? createdAt = null,
    Object? executedAt = freezed,
    Object? deviceSerial = freezed,
    Object? subsystem = freezed,
    Object? requestedBy = freezed,
    Object? failureReason = freezed,
  }) {
    return _then(
      _value.copyWith(
            id: null == id
                ? _value.id
                : id // ignore: cast_nullable_to_non_nullable
                      as String,
            action: null == action
                ? _value.action
                : action // ignore: cast_nullable_to_non_nullable
                      as String,
            status: null == status
                ? _value.status
                : status // ignore: cast_nullable_to_non_nullable
                      as String,
            createdAt: null == createdAt
                ? _value.createdAt
                : createdAt // ignore: cast_nullable_to_non_nullable
                      as String,
            executedAt: freezed == executedAt
                ? _value.executedAt
                : executedAt // ignore: cast_nullable_to_non_nullable
                      as String?,
            deviceSerial: freezed == deviceSerial
                ? _value.deviceSerial
                : deviceSerial // ignore: cast_nullable_to_non_nullable
                      as String?,
            subsystem: freezed == subsystem
                ? _value.subsystem
                : subsystem // ignore: cast_nullable_to_non_nullable
                      as String?,
            requestedBy: freezed == requestedBy
                ? _value.requestedBy
                : requestedBy // ignore: cast_nullable_to_non_nullable
                      as String?,
            failureReason: freezed == failureReason
                ? _value.failureReason
                : failureReason // ignore: cast_nullable_to_non_nullable
                      as String?,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$ArmDisarmCommandImplCopyWith<$Res>
    implements $ArmDisarmCommandCopyWith<$Res> {
  factory _$$ArmDisarmCommandImplCopyWith(
    _$ArmDisarmCommandImpl value,
    $Res Function(_$ArmDisarmCommandImpl) then,
  ) = __$$ArmDisarmCommandImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    String id,
    String action,
    String status,
    String createdAt,
    String? executedAt,
    String? deviceSerial,
    String? subsystem,
    String? requestedBy,
    String? failureReason,
  });
}

/// @nodoc
class __$$ArmDisarmCommandImplCopyWithImpl<$Res>
    extends _$ArmDisarmCommandCopyWithImpl<$Res, _$ArmDisarmCommandImpl>
    implements _$$ArmDisarmCommandImplCopyWith<$Res> {
  __$$ArmDisarmCommandImplCopyWithImpl(
    _$ArmDisarmCommandImpl _value,
    $Res Function(_$ArmDisarmCommandImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of ArmDisarmCommand
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? action = null,
    Object? status = null,
    Object? createdAt = null,
    Object? executedAt = freezed,
    Object? deviceSerial = freezed,
    Object? subsystem = freezed,
    Object? requestedBy = freezed,
    Object? failureReason = freezed,
  }) {
    return _then(
      _$ArmDisarmCommandImpl(
        id: null == id
            ? _value.id
            : id // ignore: cast_nullable_to_non_nullable
                  as String,
        action: null == action
            ? _value.action
            : action // ignore: cast_nullable_to_non_nullable
                  as String,
        status: null == status
            ? _value.status
            : status // ignore: cast_nullable_to_non_nullable
                  as String,
        createdAt: null == createdAt
            ? _value.createdAt
            : createdAt // ignore: cast_nullable_to_non_nullable
                  as String,
        executedAt: freezed == executedAt
            ? _value.executedAt
            : executedAt // ignore: cast_nullable_to_non_nullable
                  as String?,
        deviceSerial: freezed == deviceSerial
            ? _value.deviceSerial
            : deviceSerial // ignore: cast_nullable_to_non_nullable
                  as String?,
        subsystem: freezed == subsystem
            ? _value.subsystem
            : subsystem // ignore: cast_nullable_to_non_nullable
                  as String?,
        requestedBy: freezed == requestedBy
            ? _value.requestedBy
            : requestedBy // ignore: cast_nullable_to_non_nullable
                  as String?,
        failureReason: freezed == failureReason
            ? _value.failureReason
            : failureReason // ignore: cast_nullable_to_non_nullable
                  as String?,
      ),
    );
  }
}

/// @nodoc

@JsonSerializable(fieldRename: FieldRename.snake)
class _$ArmDisarmCommandImpl implements _ArmDisarmCommand {
  const _$ArmDisarmCommandImpl({
    this.id = '',
    this.action = '',
    this.status = '',
    this.createdAt = '',
    this.executedAt,
    this.deviceSerial,
    this.subsystem,
    this.requestedBy,
    this.failureReason,
  });

  factory _$ArmDisarmCommandImpl.fromJson(Map<String, dynamic> json) =>
      _$$ArmDisarmCommandImplFromJson(json);

  @override
  @JsonKey()
  final String id;
  @override
  @JsonKey()
  final String action;
  @override
  @JsonKey()
  final String status;
  @override
  @JsonKey()
  final String createdAt;
  // Timestamp when the panel acknowledged the command (added in backend 0004)
  @override
  final String? executedAt;
  // Serial of the panel that received the command
  @override
  final String? deviceSerial;
  @override
  final String? subsystem;
  @override
  final String? requestedBy;
  @override
  final String? failureReason;

  @override
  String toString() {
    return 'ArmDisarmCommand(id: $id, action: $action, status: $status, createdAt: $createdAt, executedAt: $executedAt, deviceSerial: $deviceSerial, subsystem: $subsystem, requestedBy: $requestedBy, failureReason: $failureReason)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ArmDisarmCommandImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.action, action) || other.action == action) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.createdAt, createdAt) ||
                other.createdAt == createdAt) &&
            (identical(other.executedAt, executedAt) ||
                other.executedAt == executedAt) &&
            (identical(other.deviceSerial, deviceSerial) ||
                other.deviceSerial == deviceSerial) &&
            (identical(other.subsystem, subsystem) ||
                other.subsystem == subsystem) &&
            (identical(other.requestedBy, requestedBy) ||
                other.requestedBy == requestedBy) &&
            (identical(other.failureReason, failureReason) ||
                other.failureReason == failureReason));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    id,
    action,
    status,
    createdAt,
    executedAt,
    deviceSerial,
    subsystem,
    requestedBy,
    failureReason,
  );

  /// Create a copy of ArmDisarmCommand
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$ArmDisarmCommandImplCopyWith<_$ArmDisarmCommandImpl> get copyWith =>
      __$$ArmDisarmCommandImplCopyWithImpl<_$ArmDisarmCommandImpl>(
        this,
        _$identity,
      );

  @override
  Map<String, dynamic> toJson() {
    return _$$ArmDisarmCommandImplToJson(this);
  }
}

abstract class _ArmDisarmCommand implements ArmDisarmCommand {
  const factory _ArmDisarmCommand({
    final String id,
    final String action,
    final String status,
    final String createdAt,
    final String? executedAt,
    final String? deviceSerial,
    final String? subsystem,
    final String? requestedBy,
    final String? failureReason,
  }) = _$ArmDisarmCommandImpl;

  factory _ArmDisarmCommand.fromJson(Map<String, dynamic> json) =
      _$ArmDisarmCommandImpl.fromJson;

  @override
  String get id;
  @override
  String get action;
  @override
  String get status;
  @override
  String get createdAt; // Timestamp when the panel acknowledged the command (added in backend 0004)
  @override
  String? get executedAt; // Serial of the panel that received the command
  @override
  String? get deviceSerial;
  @override
  String? get subsystem;
  @override
  String? get requestedBy;
  @override
  String? get failureReason;

  /// Create a copy of ArmDisarmCommand
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$ArmDisarmCommandImplCopyWith<_$ArmDisarmCommandImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

PaginatedCommands _$PaginatedCommandsFromJson(Map<String, dynamic> json) {
  return _PaginatedCommands.fromJson(json);
}

/// @nodoc
mixin _$PaginatedCommands {
  int get count => throw _privateConstructorUsedError;
  String? get next => throw _privateConstructorUsedError;
  String? get previous => throw _privateConstructorUsedError;
  List<ArmDisarmCommand> get results => throw _privateConstructorUsedError;

  /// Serializes this PaginatedCommands to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of PaginatedCommands
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $PaginatedCommandsCopyWith<PaginatedCommands> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $PaginatedCommandsCopyWith<$Res> {
  factory $PaginatedCommandsCopyWith(
    PaginatedCommands value,
    $Res Function(PaginatedCommands) then,
  ) = _$PaginatedCommandsCopyWithImpl<$Res, PaginatedCommands>;
  @useResult
  $Res call({
    int count,
    String? next,
    String? previous,
    List<ArmDisarmCommand> results,
  });
}

/// @nodoc
class _$PaginatedCommandsCopyWithImpl<$Res, $Val extends PaginatedCommands>
    implements $PaginatedCommandsCopyWith<$Res> {
  _$PaginatedCommandsCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of PaginatedCommands
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
                      as List<ArmDisarmCommand>,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$PaginatedCommandsImplCopyWith<$Res>
    implements $PaginatedCommandsCopyWith<$Res> {
  factory _$$PaginatedCommandsImplCopyWith(
    _$PaginatedCommandsImpl value,
    $Res Function(_$PaginatedCommandsImpl) then,
  ) = __$$PaginatedCommandsImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    int count,
    String? next,
    String? previous,
    List<ArmDisarmCommand> results,
  });
}

/// @nodoc
class __$$PaginatedCommandsImplCopyWithImpl<$Res>
    extends _$PaginatedCommandsCopyWithImpl<$Res, _$PaginatedCommandsImpl>
    implements _$$PaginatedCommandsImplCopyWith<$Res> {
  __$$PaginatedCommandsImplCopyWithImpl(
    _$PaginatedCommandsImpl _value,
    $Res Function(_$PaginatedCommandsImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of PaginatedCommands
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
      _$PaginatedCommandsImpl(
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
                  as List<ArmDisarmCommand>,
      ),
    );
  }
}

/// @nodoc

@JsonSerializable(fieldRename: FieldRename.snake)
class _$PaginatedCommandsImpl implements _PaginatedCommands {
  const _$PaginatedCommandsImpl({
    this.count = 0,
    this.next,
    this.previous,
    final List<ArmDisarmCommand> results = const [],
  }) : _results = results;

  factory _$PaginatedCommandsImpl.fromJson(Map<String, dynamic> json) =>
      _$$PaginatedCommandsImplFromJson(json);

  @override
  @JsonKey()
  final int count;
  @override
  final String? next;
  @override
  final String? previous;
  final List<ArmDisarmCommand> _results;
  @override
  @JsonKey()
  List<ArmDisarmCommand> get results {
    if (_results is EqualUnmodifiableListView) return _results;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_results);
  }

  @override
  String toString() {
    return 'PaginatedCommands(count: $count, next: $next, previous: $previous, results: $results)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$PaginatedCommandsImpl &&
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

  /// Create a copy of PaginatedCommands
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$PaginatedCommandsImplCopyWith<_$PaginatedCommandsImpl> get copyWith =>
      __$$PaginatedCommandsImplCopyWithImpl<_$PaginatedCommandsImpl>(
        this,
        _$identity,
      );

  @override
  Map<String, dynamic> toJson() {
    return _$$PaginatedCommandsImplToJson(this);
  }
}

abstract class _PaginatedCommands implements PaginatedCommands {
  const factory _PaginatedCommands({
    final int count,
    final String? next,
    final String? previous,
    final List<ArmDisarmCommand> results,
  }) = _$PaginatedCommandsImpl;

  factory _PaginatedCommands.fromJson(Map<String, dynamic> json) =
      _$PaginatedCommandsImpl.fromJson;

  @override
  int get count;
  @override
  String? get next;
  @override
  String? get previous;
  @override
  List<ArmDisarmCommand> get results;

  /// Create a copy of PaginatedCommands
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$PaginatedCommandsImplCopyWith<_$PaginatedCommandsImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
