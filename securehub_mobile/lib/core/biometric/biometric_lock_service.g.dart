// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'biometric_lock_service.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$biometricLockServiceHash() =>
    r'96dda3f42075d5753f139e33daf0c5846bda1885';

/// See also [biometricLockService].
@ProviderFor(biometricLockService)
final biometricLockServiceProvider =
    AutoDisposeProvider<BiometricLockService>.internal(
      biometricLockService,
      name: r'biometricLockServiceProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$biometricLockServiceHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef BiometricLockServiceRef = AutoDisposeProviderRef<BiometricLockService>;
String _$appLockedHash() => r'53038da6868ee1307fb77d8b6424f773fe53e569';

/// Whether the app is currently showing the lock screen.
///
/// Copied from [AppLocked].
@ProviderFor(AppLocked)
final appLockedProvider = AutoDisposeNotifierProvider<AppLocked, bool>.internal(
  AppLocked.new,
  name: r'appLockedProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$appLockedHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$AppLocked = AutoDisposeNotifier<bool>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
