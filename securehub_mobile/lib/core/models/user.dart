import 'package:freezed_annotation/freezed_annotation.dart';

part 'user.freezed.dart';
part 'user.g.dart';

@Freezed(fromJson: true)
class AppUser with _$AppUser {
  @JsonSerializable(fieldRename: FieldRename.snake)
  const factory AppUser({
    required int id,
    required String username,
    @Default('') String email,
    @Default('') String firstName,
    @Default('') String lastName,
  }) = _AppUser;

  factory AppUser.fromJson(Map<String, dynamic> json) =>
      _$AppUserFromJson(json);
}

@Freezed(fromJson: true)
class CustomerProfile with _$CustomerProfile {
  @JsonSerializable(fieldRename: FieldRename.snake)
  const factory CustomerProfile({
    required AppUser user,
    @Default('') String phoneNumber,
    @Default(false) bool isMobileUser,
  }) = _CustomerProfile;

  factory CustomerProfile.fromJson(Map<String, dynamic> json) =>
      _$CustomerProfileFromJson(json);
}
