// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'arm_disarm_command.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$ArmDisarmCommandImpl _$$ArmDisarmCommandImplFromJson(
  Map<String, dynamic> json,
) => _$ArmDisarmCommandImpl(
  id: json['id'] as String? ?? '',
  action: json['action'] as String? ?? '',
  status: json['status'] as String? ?? '',
  createdAt: json['created_at'] as String? ?? '',
  executedAt: json['executed_at'] as String?,
  deviceSerial: json['device_serial'] as String?,
  subsystem: json['subsystem'] as String?,
  requestedBy: json['requested_by'] as String?,
  failureReason: json['failure_reason'] as String?,
);

Map<String, dynamic> _$$ArmDisarmCommandImplToJson(
  _$ArmDisarmCommandImpl instance,
) => <String, dynamic>{
  'id': instance.id,
  'action': instance.action,
  'status': instance.status,
  'created_at': instance.createdAt,
  'executed_at': instance.executedAt,
  'device_serial': instance.deviceSerial,
  'subsystem': instance.subsystem,
  'requested_by': instance.requestedBy,
  'failure_reason': instance.failureReason,
};

_$PaginatedCommandsImpl _$$PaginatedCommandsImplFromJson(
  Map<String, dynamic> json,
) => _$PaginatedCommandsImpl(
  count: (json['count'] as num?)?.toInt() ?? 0,
  next: json['next'] as String?,
  previous: json['previous'] as String?,
  results:
      (json['results'] as List<dynamic>?)
          ?.map((e) => ArmDisarmCommand.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
);

Map<String, dynamic> _$$PaginatedCommandsImplToJson(
  _$PaginatedCommandsImpl instance,
) => <String, dynamic>{
  'count': instance.count,
  'next': instance.next,
  'previous': instance.previous,
  'results': instance.results,
};
