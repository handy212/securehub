import 'package:freezed_annotation/freezed_annotation.dart';

part 'arm_disarm_command.freezed.dart';
part 'arm_disarm_command.g.dart';

@Freezed(fromJson: true)
class ArmDisarmCommand with _$ArmDisarmCommand {
  @JsonSerializable(fieldRename: FieldRename.snake)
  const factory ArmDisarmCommand({
    @Default('') String id,
    @Default('') String action,
    @Default('') String status,
    @Default('') String createdAt,
    // Timestamp when the panel acknowledged the command (added in backend 0004)
    String? executedAt,
    // Serial of the panel that received the command
    String? deviceSerial,
    String? subsystem,
    String? requestedBy,
    String? failureReason,
  }) = _ArmDisarmCommand;

  factory ArmDisarmCommand.fromJson(Map<String, dynamic> json) =>
      _$ArmDisarmCommandFromJson(json);
}

@Freezed(fromJson: true)
class PaginatedCommands with _$PaginatedCommands {
  @JsonSerializable(fieldRename: FieldRename.snake)
  const factory PaginatedCommands({
    @Default(0) int count,
    String? next,
    String? previous,
    @Default([]) List<ArmDisarmCommand> results,
  }) = _PaginatedCommands;

  factory PaginatedCommands.fromJson(Map<String, dynamic> json) =>
      _$PaginatedCommandsFromJson(json);
}
