// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'command_list_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$commandListHash() => r'492b599ea8df4ce11b4d129f6fea9883e5dd2911';

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

/// See also [commandList].
@ProviderFor(commandList)
const commandListProvider = CommandListFamily();

/// See also [commandList].
class CommandListFamily extends Family<AsyncValue<List<ArmDisarmCommand>>> {
  /// See also [commandList].
  const CommandListFamily();

  /// See also [commandList].
  CommandListProvider call(String siteId) {
    return CommandListProvider(siteId);
  }

  @override
  CommandListProvider getProviderOverride(
    covariant CommandListProvider provider,
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
  String? get name => r'commandListProvider';
}

/// See also [commandList].
class CommandListProvider
    extends AutoDisposeFutureProvider<List<ArmDisarmCommand>> {
  /// See also [commandList].
  CommandListProvider(String siteId)
    : this._internal(
        (ref) => commandList(ref as CommandListRef, siteId),
        from: commandListProvider,
        name: r'commandListProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$commandListHash,
        dependencies: CommandListFamily._dependencies,
        allTransitiveDependencies: CommandListFamily._allTransitiveDependencies,
        siteId: siteId,
      );

  CommandListProvider._internal(
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
    FutureOr<List<ArmDisarmCommand>> Function(CommandListRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: CommandListProvider._internal(
        (ref) => create(ref as CommandListRef),
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
  AutoDisposeFutureProviderElement<List<ArmDisarmCommand>> createElement() {
    return _CommandListProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is CommandListProvider && other.siteId == siteId;
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
mixin CommandListRef on AutoDisposeFutureProviderRef<List<ArmDisarmCommand>> {
  /// The parameter `siteId` of this provider.
  String get siteId;
}

class _CommandListProviderElement
    extends AutoDisposeFutureProviderElement<List<ArmDisarmCommand>>
    with CommandListRef {
  _CommandListProviderElement(super.provider);

  @override
  String get siteId => (origin as CommandListProvider).siteId;
}

// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
