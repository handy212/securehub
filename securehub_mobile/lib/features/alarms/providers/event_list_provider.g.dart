// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'event_list_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$filteredEventsHash() => r'6dff91e718fb9ec99d1f387ae22b80febc3da858';

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

/// See also [filteredEvents].
@ProviderFor(filteredEvents)
const filteredEventsProvider = FilteredEventsFamily();

/// See also [filteredEvents].
class FilteredEventsFamily extends Family<List<AlarmEvent>> {
  /// See also [filteredEvents].
  const FilteredEventsFamily();

  /// See also [filteredEvents].
  FilteredEventsProvider call(
    String siteId, {
    String query = '',
    String filter = 'all',
  }) {
    return FilteredEventsProvider(siteId, query: query, filter: filter);
  }

  @override
  FilteredEventsProvider getProviderOverride(
    covariant FilteredEventsProvider provider,
  ) {
    return call(
      provider.siteId,
      query: provider.query,
      filter: provider.filter,
    );
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'filteredEventsProvider';
}

/// See also [filteredEvents].
class FilteredEventsProvider extends AutoDisposeProvider<List<AlarmEvent>> {
  /// See also [filteredEvents].
  FilteredEventsProvider(
    String siteId, {
    String query = '',
    String filter = 'all',
  }) : this._internal(
         (ref) => filteredEvents(
           ref as FilteredEventsRef,
           siteId,
           query: query,
           filter: filter,
         ),
         from: filteredEventsProvider,
         name: r'filteredEventsProvider',
         debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
             ? null
             : _$filteredEventsHash,
         dependencies: FilteredEventsFamily._dependencies,
         allTransitiveDependencies:
             FilteredEventsFamily._allTransitiveDependencies,
         siteId: siteId,
         query: query,
         filter: filter,
       );

  FilteredEventsProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.siteId,
    required this.query,
    required this.filter,
  }) : super.internal();

  final String siteId;
  final String query;
  final String filter;

  @override
  Override overrideWith(
    List<AlarmEvent> Function(FilteredEventsRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: FilteredEventsProvider._internal(
        (ref) => create(ref as FilteredEventsRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        siteId: siteId,
        query: query,
        filter: filter,
      ),
    );
  }

  @override
  AutoDisposeProviderElement<List<AlarmEvent>> createElement() {
    return _FilteredEventsProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is FilteredEventsProvider &&
        other.siteId == siteId &&
        other.query == query &&
        other.filter == filter;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, siteId.hashCode);
    hash = _SystemHash.combine(hash, query.hashCode);
    hash = _SystemHash.combine(hash, filter.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin FilteredEventsRef on AutoDisposeProviderRef<List<AlarmEvent>> {
  /// The parameter `siteId` of this provider.
  String get siteId;

  /// The parameter `query` of this provider.
  String get query;

  /// The parameter `filter` of this provider.
  String get filter;
}

class _FilteredEventsProviderElement
    extends AutoDisposeProviderElement<List<AlarmEvent>>
    with FilteredEventsRef {
  _FilteredEventsProviderElement(super.provider);

  @override
  String get siteId => (origin as FilteredEventsProvider).siteId;
  @override
  String get query => (origin as FilteredEventsProvider).query;
  @override
  String get filter => (origin as FilteredEventsProvider).filter;
}

String _$alarmPicturesHash() => r'629d368ae3c8a6ab614ffd0d72adb1eb3027de72';

/// See also [alarmPictures].
@ProviderFor(alarmPictures)
const alarmPicturesProvider = AlarmPicturesFamily();

/// See also [alarmPictures].
class AlarmPicturesFamily extends Family<AsyncValue<List<AlarmPicture>>> {
  /// See also [alarmPictures].
  const AlarmPicturesFamily();

  /// See also [alarmPictures].
  AlarmPicturesProvider call(String siteId, AlarmEvent event) {
    return AlarmPicturesProvider(siteId, event);
  }

  @override
  AlarmPicturesProvider getProviderOverride(
    covariant AlarmPicturesProvider provider,
  ) {
    return call(provider.siteId, provider.event);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'alarmPicturesProvider';
}

/// See also [alarmPictures].
class AlarmPicturesProvider
    extends AutoDisposeFutureProvider<List<AlarmPicture>> {
  /// See also [alarmPictures].
  AlarmPicturesProvider(String siteId, AlarmEvent event)
    : this._internal(
        (ref) => alarmPictures(ref as AlarmPicturesRef, siteId, event),
        from: alarmPicturesProvider,
        name: r'alarmPicturesProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$alarmPicturesHash,
        dependencies: AlarmPicturesFamily._dependencies,
        allTransitiveDependencies:
            AlarmPicturesFamily._allTransitiveDependencies,
        siteId: siteId,
        event: event,
      );

  AlarmPicturesProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.siteId,
    required this.event,
  }) : super.internal();

  final String siteId;
  final AlarmEvent event;

  @override
  Override overrideWith(
    FutureOr<List<AlarmPicture>> Function(AlarmPicturesRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: AlarmPicturesProvider._internal(
        (ref) => create(ref as AlarmPicturesRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        siteId: siteId,
        event: event,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<List<AlarmPicture>> createElement() {
    return _AlarmPicturesProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is AlarmPicturesProvider &&
        other.siteId == siteId &&
        other.event == event;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, siteId.hashCode);
    hash = _SystemHash.combine(hash, event.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin AlarmPicturesRef on AutoDisposeFutureProviderRef<List<AlarmPicture>> {
  /// The parameter `siteId` of this provider.
  String get siteId;

  /// The parameter `event` of this provider.
  AlarmEvent get event;
}

class _AlarmPicturesProviderElement
    extends AutoDisposeFutureProviderElement<List<AlarmPicture>>
    with AlarmPicturesRef {
  _AlarmPicturesProviderElement(super.provider);

  @override
  String get siteId => (origin as AlarmPicturesProvider).siteId;
  @override
  AlarmEvent get event => (origin as AlarmPicturesProvider).event;
}

String _$eventListNotifierHash() => r'a89270abccbddf43a8059a2f190bed79bbf28c76';

abstract class _$EventListNotifier
    extends BuildlessAutoDisposeAsyncNotifier<List<AlarmEvent>> {
  late final String siteId;

  FutureOr<List<AlarmEvent>> build(String siteId);
}

/// See also [EventListNotifier].
@ProviderFor(EventListNotifier)
const eventListNotifierProvider = EventListNotifierFamily();

/// See also [EventListNotifier].
class EventListNotifierFamily extends Family<AsyncValue<List<AlarmEvent>>> {
  /// See also [EventListNotifier].
  const EventListNotifierFamily();

  /// See also [EventListNotifier].
  EventListNotifierProvider call(String siteId) {
    return EventListNotifierProvider(siteId);
  }

  @override
  EventListNotifierProvider getProviderOverride(
    covariant EventListNotifierProvider provider,
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
  String? get name => r'eventListNotifierProvider';
}

/// See also [EventListNotifier].
class EventListNotifierProvider
    extends
        AutoDisposeAsyncNotifierProviderImpl<
          EventListNotifier,
          List<AlarmEvent>
        > {
  /// See also [EventListNotifier].
  EventListNotifierProvider(String siteId)
    : this._internal(
        () => EventListNotifier()..siteId = siteId,
        from: eventListNotifierProvider,
        name: r'eventListNotifierProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$eventListNotifierHash,
        dependencies: EventListNotifierFamily._dependencies,
        allTransitiveDependencies:
            EventListNotifierFamily._allTransitiveDependencies,
        siteId: siteId,
      );

  EventListNotifierProvider._internal(
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
  FutureOr<List<AlarmEvent>> runNotifierBuild(
    covariant EventListNotifier notifier,
  ) {
    return notifier.build(siteId);
  }

  @override
  Override overrideWith(EventListNotifier Function() create) {
    return ProviderOverride(
      origin: this,
      override: EventListNotifierProvider._internal(
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
  AutoDisposeAsyncNotifierProviderElement<EventListNotifier, List<AlarmEvent>>
  createElement() {
    return _EventListNotifierProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is EventListNotifierProvider && other.siteId == siteId;
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
mixin EventListNotifierRef
    on AutoDisposeAsyncNotifierProviderRef<List<AlarmEvent>> {
  /// The parameter `siteId` of this provider.
  String get siteId;
}

class _EventListNotifierProviderElement
    extends
        AutoDisposeAsyncNotifierProviderElement<
          EventListNotifier,
          List<AlarmEvent>
        >
    with EventListNotifierRef {
  _EventListNotifierProviderElement(super.provider);

  @override
  String get siteId => (origin as EventListNotifierProvider).siteId;
}

// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
