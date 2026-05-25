import 'user.dart';

/// API profile payload including guard/customer/staff routing fields.
class SessionProfile {
  const SessionProfile({
    required this.customer,
    required this.accountKind,
    this.guardProfileId = '',
    this.guardEmployeeNumber = '',
    this.isStaff = false,
  });

  final CustomerProfile customer;
  final String accountKind;
  final String guardProfileId;
  final String guardEmployeeNumber;
  final bool isStaff;

  bool get isGuard => accountKind == 'guard';
  bool get isCustomer => accountKind == 'customer';

  factory SessionProfile.fromJson(Map<String, dynamic> json) {
    return SessionProfile(
      customer: CustomerProfile.fromJson(json),
      accountKind: json['account_kind'] as String? ?? 'customer',
      guardProfileId: json['guard_profile_id'] as String? ?? '',
      guardEmployeeNumber: json['guard_employee_number'] as String? ?? '',
      isStaff: json['is_staff'] as bool? ?? false,
    );
  }
}
