// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'sites_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$siteListHash() => r'5c63e772bee08e230c095641ddcebcc5c29078ed';

/// See also [siteList].
@ProviderFor(siteList)
final siteListProvider = AutoDisposeFutureProvider<List<Site>>.internal(
  siteList,
  name: r'siteListProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$siteListHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef SiteListRef = AutoDisposeFutureProviderRef<List<Site>>;
String _$siteDetailHash() => r'c4bb5005a2e4682db4654572d92c317808e93a8c';

/// Copied from Dart SDK
class _SystemHash {
  _SystemHash._();

  static int combine(int hash, int value) {
    // ignore: parameter_assignments
    hash = 0x1fffffff & (hash + value);
    // ignore: parameter_assignments
    hash = 0x1fffffff & (hash + ((0x0007ffff & hash) << 10));
    return hash ^ (hash >> 6);
  }

  static int finish(int hash) {
    // ignore: parameter_assignments
    hash = 0x1fffffff & (hash + ((0x03ffffff & hash) << 3));
    // ignore: parameter_assignments
    hash = hash ^ (hash >> 11);
    return 0x1fffffff & (hash + ((0x00003fff & hash) << 15));
  }
}

/// See also [siteDetail].
@ProviderFor(siteDetail)
const siteDetailProvider = SiteDetailFamily();

/// See also [siteDetail].
class SiteDetailFamily extends Family<AsyncValue<Site>> {
  /// See also [siteDetail].
  const SiteDetailFamily();

  /// See also [siteDetail].
  SiteDetailProvider call(String siteId) {
    return SiteDetailProvider(siteId);
  }

  @override
  SiteDetailProvider getProviderOverride(
    covariant SiteDetailProvider provider,
  ) {
    return call(provider.siteId);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'siteDetailProvider';
}

/// See also [siteDetail].
class SiteDetailProvider extends AutoDisposeFutureProvider<Site> {
  /// See also [siteDetail].
  SiteDetailProvider(String siteId)
    : this._internal(
        (ref) => siteDetail(ref as SiteDetailRef, siteId),
        from: siteDetailProvider,
        name: r'siteDetailProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$siteDetailHash,
        dependencies: SiteDetailFamily._dependencies,
        allTransitiveDependencies: SiteDetailFamily._allTransitiveDependencies,
        siteId: siteId,
      );

  SiteDetailProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.siteId,
  }) : super.internal();

  final String siteId;

  @override
  Override overrideWith(
    FutureOr<Site> Function(SiteDetailRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: SiteDetailProvider._internal(
        (ref) => create(ref as SiteDetailRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        siteId: siteId,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<Site> createElement() {
    return _SiteDetailProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is SiteDetailProvider && other.siteId == siteId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, siteId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin SiteDetailRef on AutoDisposeFutureProviderRef<Site> {
  /// The parameter `siteId` of this provider.
  String get siteId;
}

class _SiteDetailProviderElement extends AutoDisposeFutureProviderElement<Site>
    with SiteDetailRef {
  _SiteDetailProviderElement(super.provider);

  @override
  String get siteId => (origin as SiteDetailProvider).siteId;
}

String _$sitePollHash() => r'bc5bc933552de40eba9fe1ebb7f8c64d5abbe9e0';

/// See also [sitePoll].
@ProviderFor(sitePoll)
const sitePollProvider = SitePollFamily();

/// See also [sitePoll].
class SitePollFamily extends Family<AsyncValue<SitePoll>> {
  /// See also [sitePoll].
  const SitePollFamily();

  /// See also [sitePoll].
  SitePollProvider call(String siteId) {
    return SitePollProvider(siteId);
  }

  @override
  SitePollProvider getProviderOverride(covariant SitePollProvider provider) {
    return call(provider.siteId);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'sitePollProvider';
}

/// See also [sitePoll].
class SitePollProvider extends AutoDisposeStreamProvider<SitePoll> {
  /// See also [sitePoll].
  SitePollProvider(String siteId)
    : this._internal(
        (ref) => sitePoll(ref as SitePollRef, siteId),
        from: sitePollProvider,
        name: r'sitePollProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$sitePollHash,
        dependencies: SitePollFamily._dependencies,
        allTransitiveDependencies: SitePollFamily._allTransitiveDependencies,
        siteId: siteId,
      );

  SitePollProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.siteId,
  }) : super.internal();

  final String siteId;

  @override
  Override overrideWith(
    Stream<SitePoll> Function(SitePollRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: SitePollProvider._internal(
        (ref) => create(ref as SitePollRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        siteId: siteId,
      ),
    );
  }

  @override
  AutoDisposeStreamProviderElement<SitePoll> createElement() {
    return _SitePollProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is SitePollProvider && other.siteId == siteId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, siteId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin SitePollRef on AutoDisposeStreamProviderRef<SitePoll> {
  /// The parameter `siteId` of this provider.
  String get siteId;
}

class _SitePollProviderElement
    extends AutoDisposeStreamProviderElement<SitePoll>
    with SitePollRef {
  _SitePollProviderElement(super.provider);

  @override
  String get siteId => (origin as SitePollProvider).siteId;
}

String _$cameraLiveUrlHash() => r'894bf55ea428f5de355cb60261de5e3e05dfb5f1';

/// See also [cameraLiveUrl].
@ProviderFor(cameraLiveUrl)
const cameraLiveUrlProvider = CameraLiveUrlFamily();

/// See also [cameraLiveUrl].
class CameraLiveUrlFamily extends Family<AsyncValue<String>> {
  /// See also [cameraLiveUrl].
  const CameraLiveUrlFamily();

  /// See also [cameraLiveUrl].
  CameraLiveUrlProvider call(String siteId, String channelId) {
    return CameraLiveUrlProvider(siteId, channelId);
  }

  @override
  CameraLiveUrlProvider getProviderOverride(
    covariant CameraLiveUrlProvider provider,
  ) {
    return call(provider.siteId, provider.channelId);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'cameraLiveUrlProvider';
}

/// See also [cameraLiveUrl].
class CameraLiveUrlProvider extends AutoDisposeFutureProvider<String> {
  /// See also [cameraLiveUrl].
  CameraLiveUrlProvider(String siteId, String channelId)
    : this._internal(
        (ref) => cameraLiveUrl(ref as CameraLiveUrlRef, siteId, channelId),
        from: cameraLiveUrlProvider,
        name: r'cameraLiveUrlProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$cameraLiveUrlHash,
        dependencies: CameraLiveUrlFamily._dependencies,
        allTransitiveDependencies:
            CameraLiveUrlFamily._allTransitiveDependencies,
        siteId: siteId,
        channelId: channelId,
      );

  CameraLiveUrlProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.siteId,
    required this.channelId,
  }) : super.internal();

  final String siteId;
  final String channelId;

  @override
  Override overrideWith(
    FutureOr<String> Function(CameraLiveUrlRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: CameraLiveUrlProvider._internal(
        (ref) => create(ref as CameraLiveUrlRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        siteId: siteId,
        channelId: channelId,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<String> createElement() {
    return _CameraLiveUrlProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is CameraLiveUrlProvider &&
        other.siteId == siteId &&
        other.channelId == channelId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, siteId.hashCode);
    hash = _SystemHash.combine(hash, channelId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin CameraLiveUrlRef on AutoDisposeFutureProviderRef<String> {
  /// The parameter `siteId` of this provider.
  String get siteId;

  /// The parameter `channelId` of this provider.
  String get channelId;
}

class _CameraLiveUrlProviderElement
    extends AutoDisposeFutureProviderElement<String>
    with CameraLiveUrlRef {
  _CameraLiveUrlProviderElement(super.provider);

  @override
  String get siteId => (origin as CameraLiveUrlProvider).siteId;
  @override
  String get channelId => (origin as CameraLiveUrlProvider).channelId;
}

String _$hardwareRefreshHash() => r'25db0832a7b46e719b6d20cf129e54b487211063';

abstract class _$HardwareRefresh
    extends BuildlessAutoDisposeNotifier<AsyncValue<void>> {
  late final String siteId;

  AsyncValue<void> build(String siteId);
}

/// See also [HardwareRefresh].
@ProviderFor(HardwareRefresh)
const hardwareRefreshProvider = HardwareRefreshFamily();

/// See also [HardwareRefresh].
class HardwareRefreshFamily extends Family<AsyncValue<void>> {
  /// See also [HardwareRefresh].
  const HardwareRefreshFamily();

  /// See also [HardwareRefresh].
  HardwareRefreshProvider call(String siteId) {
    return HardwareRefreshProvider(siteId);
  }

  @override
  HardwareRefreshProvider getProviderOverride(
    covariant HardwareRefreshProvider provider,
  ) {
    return call(provider.siteId);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'hardwareRefreshProvider';
}

/// See also [HardwareRefresh].
class HardwareRefreshProvider
    extends AutoDisposeNotifierProviderImpl<HardwareRefresh, AsyncValue<void>> {
  /// See also [HardwareRefresh].
  HardwareRefreshProvider(String siteId)
    : this._internal(
        () => HardwareRefresh()..siteId = siteId,
        from: hardwareRefreshProvider,
        name: r'hardwareRefreshProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$hardwareRefreshHash,
        dependencies: HardwareRefreshFamily._dependencies,
        allTransitiveDependencies:
            HardwareRefreshFamily._allTransitiveDependencies,
        siteId: siteId,
      );

  HardwareRefreshProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.siteId,
  }) : super.internal();

  final String siteId;

  @override
  AsyncValue<void> runNotifierBuild(covariant HardwareRefresh notifier) {
    return notifier.build(siteId);
  }

  @override
  Override overrideWith(HardwareRefresh Function() create) {
    return ProviderOverride(
      origin: this,
      override: HardwareRefreshProvider._internal(
        () => create()..siteId = siteId,
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        siteId: siteId,
      ),
    );
  }

  @override
  AutoDisposeNotifierProviderElement<HardwareRefresh, AsyncValue<void>>
  createElement() {
    return _HardwareRefreshProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is HardwareRefreshProvider && other.siteId == siteId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, siteId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin HardwareRefreshRef on AutoDisposeNotifierProviderRef<AsyncValue<void>> {
  /// The parameter `siteId` of this provider.
  String get siteId;
}

class _HardwareRefreshProviderElement
    extends
        AutoDisposeNotifierProviderElement<HardwareRefresh, AsyncValue<void>>
    with HardwareRefreshRef {
  _HardwareRefreshProviderElement(super.provider);

  @override
  String get siteId => (origin as HardwareRefreshProvider).siteId;
}

// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
