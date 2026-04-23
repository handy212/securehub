// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$AppUserImpl _$$AppUserImplFromJson(Map<String, dynamic> json) =>
    _$AppUserImpl(
      id: (json['id'] as num).toInt(),
      username: json['username'] as String,
      email: json['email'] as String? ?? '',
      firstName: json['first_name'] as String? ?? '',
      lastName: json['last_name'] as String? ?? '',
    );

Map<String, dynamic> _$$AppUserImplToJson(_$AppUserImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'username': instance.username,
      'email': instance.email,
      'first_name': instance.firstName,
      'last_name': instance.lastName,
    };

_$CustomerProfileImpl _$$CustomerProfileImplFromJson(
  Map<String, dynamic> json,
) => _$CustomerProfileImpl(
  user: AppUser.fromJson(json['user'] as Map<String, dynamic>),
  phoneNumber: json['phone_number'] as String? ?? '',
  isMobileUser: json['is_mobile_user'] as bool? ?? false,
);

Map<String, dynamic> _$$CustomerProfileImplToJson(
  _$CustomerProfileImpl instance,
) => <String, dynamic>{
  'user': instance.user,
  'phone_number': instance.phoneNumber,
  'is_mobile_user': instance.isMobileUser,
};
