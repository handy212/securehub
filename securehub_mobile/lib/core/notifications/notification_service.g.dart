// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'notification_service.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$notificationServiceHash() =>
    r'40a7b535c39c2868e0cf22df92d1bc2b31d4f68d';

/// See also [notificationService].
@ProviderFor(notificationService)
final notificationServiceProvider = Provider<NotificationService>.internal(
  notificationService,
  name: r'notificationServiceProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$notificationServiceHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef NotificationServiceRef = ProviderRef<NotificationService>;
String _$notificationNavHash() => r'b124ab78f785bd9206cef73d7c3f6b29365360e6';

/// See also [NotificationNav].
@ProviderFor(NotificationNav)
final notificationNavProvider =
    AutoDisposeNotifierProvider<NotificationNav, String?>.internal(
      NotificationNav.new,
      name: r'notificationNavProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$notificationNavHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

typedef _$NotificationNav = AutoDisposeNotifier<String?>;
String _$criticalAlarmNavHash() => r'0867184fa241c010dbdc84e2177e28b120c101cf';

/// See also [CriticalAlarmNav].
@ProviderFor(CriticalAlarmNav)
final criticalAlarmNavProvider =
    AutoDisposeNotifierProvider<
      CriticalAlarmNav,
      Map<String, String>?
    >.internal(
      CriticalAlarmNav.new,
      name: r'criticalAlarmNavProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$criticalAlarmNavHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

typedef _$CriticalAlarmNav = AutoDisposeNotifier<Map<String, String>?>;
String _$billingLockoutNavHash() => r'd3137ae38db5f7af1959fa1e8f0811ff3fc5a2b5';

/// See also [BillingLockoutNav].
@ProviderFor(BillingLockoutNav)
final billingLockoutNavProvider =
    AutoDisposeNotifierProvider<BillingLockoutNav, bool>.internal(
      BillingLockoutNav.new,
      name: r'billingLockoutNavProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$billingLockoutNavHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

typedef _$BillingLockoutNav = AutoDisposeNotifier<bool>;
String _$messagesNavHash() => r'3612503799602fcdcc106d5e346fee8c7532fee1';

/// See also [MessagesNav].
@ProviderFor(MessagesNav)
final messagesNavProvider =
    AutoDisposeNotifierProvider<MessagesNav, bool>.internal(
      MessagesNav.new,
      name: r'messagesNavProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$messagesNavHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

typedef _$MessagesNav = AutoDisposeNotifier<bool>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
