import 'package:freezed_annotation/freezed_annotation.dart';
import 'site.dart';

part 'site_poll.freezed.dart';
part 'site_poll.g.dart';

// Removed PollSubsystem since the API uses the full Subsystem schema in the poll response.

@Freezed(fromJson: true)
class LastEvent with _$LastEvent {
  @JsonSerializable(fieldRename: FieldRename.snake)
  const factory LastEvent({
    String? id,
    String? type,
    String? occurredAt,
  }) = _LastEvent;

  factory LastEvent.fromJson(Map<String, dynamic> json) =>
      _$LastEventFromJson(json);
}

@Freezed(fromJson: true)
class SitePoll with _$SitePoll {
  @JsonSerializable(fieldRename: FieldRename.snake)
  const factory SitePoll({
    @Default('') String siteId,
    @Default(0) int armedSubsystems,
    @Default(0) int disarmedSubsystems,
    @Default(0) int activeAlarmCount,
    @Default(0) int offlineDeviceCount,
    LastEvent? lastEvent,
    @Default([]) List<Subsystem> subsystems,
  }) = _SitePoll;

  factory SitePoll.fromJson(Map<String, dynamic> json) =>
      _$SitePollFromJson(json);
}
