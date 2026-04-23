// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'messages_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$inboxMessagesHash() => r'7169b8dc46bee61b596d956cae168a2803d86c4e';

/// See also [inboxMessages].
@ProviderFor(inboxMessages)
final inboxMessagesProvider =
    AutoDisposeFutureProvider<List<InboxMessage>>.internal(
      inboxMessages,
      name: r'inboxMessagesProvider',
      debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
          ? null
          : _$inboxMessagesHash,
      dependencies: null,
      allTransitiveDependencies: null,
    );

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
typedef InboxMessagesRef = AutoDisposeFutureProviderRef<List<InboxMessage>>;
String _$markMessageAsReadHash() => r'3b9636924fa10dd75c87b924b25e78a53ff4b61c';

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

/// See also [markMessageAsRead].
@ProviderFor(markMessageAsRead)
const markMessageAsReadProvider = MarkMessageAsReadFamily();

/// See also [markMessageAsRead].
class MarkMessageAsReadFamily extends Family<AsyncValue<void>> {
  /// See also [markMessageAsRead].
  const MarkMessageAsReadFamily();

  /// See also [markMessageAsRead].
  MarkMessageAsReadProvider call(String messageId) {
    return MarkMessageAsReadProvider(messageId);
  }

  @override
  MarkMessageAsReadProvider getProviderOverride(
    covariant MarkMessageAsReadProvider provider,
  ) {
    return call(provider.messageId);
  }

  static const Iterable<ProviderOrFamily>? _dependencies = null;

  @override
  Iterable<ProviderOrFamily>? get dependencies => _dependencies;

  static const Iterable<ProviderOrFamily>? _allTransitiveDependencies = null;

  @override
  Iterable<ProviderOrFamily>? get allTransitiveDependencies =>
      _allTransitiveDependencies;

  @override
  String? get name => r'markMessageAsReadProvider';
}

/// See also [markMessageAsRead].
class MarkMessageAsReadProvider extends AutoDisposeFutureProvider<void> {
  /// See also [markMessageAsRead].
  MarkMessageAsReadProvider(String messageId)
    : this._internal(
        (ref) => markMessageAsRead(ref as MarkMessageAsReadRef, messageId),
        from: markMessageAsReadProvider,
        name: r'markMessageAsReadProvider',
        debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
            ? null
            : _$markMessageAsReadHash,
        dependencies: MarkMessageAsReadFamily._dependencies,
        allTransitiveDependencies:
            MarkMessageAsReadFamily._allTransitiveDependencies,
        messageId: messageId,
      );

  MarkMessageAsReadProvider._internal(
    super._createNotifier, {
    required super.name,
    required super.dependencies,
    required super.allTransitiveDependencies,
    required super.debugGetCreateSourceHash,
    required super.from,
    required this.messageId,
  }) : super.internal();

  final String messageId;

  @override
  Override overrideWith(
    FutureOr<void> Function(MarkMessageAsReadRef provider) create,
  ) {
    return ProviderOverride(
      origin: this,
      override: MarkMessageAsReadProvider._internal(
        (ref) => create(ref as MarkMessageAsReadRef),
        from: from,
        name: null,
        dependencies: null,
        allTransitiveDependencies: null,
        debugGetCreateSourceHash: null,
        messageId: messageId,
      ),
    );
  }

  @override
  AutoDisposeFutureProviderElement<void> createElement() {
    return _MarkMessageAsReadProviderElement(this);
  }

  @override
  bool operator ==(Object other) {
    return other is MarkMessageAsReadProvider && other.messageId == messageId;
  }

  @override
  int get hashCode {
    var hash = _SystemHash.combine(0, runtimeType.hashCode);
    hash = _SystemHash.combine(hash, messageId.hashCode);

    return _SystemHash.finish(hash);
  }
}

@Deprecated('Will be removed in 3.0. Use Ref instead')
// ignore: unused_element
mixin MarkMessageAsReadRef on AutoDisposeFutureProviderRef<void> {
  /// The parameter `messageId` of this provider.
  String get messageId;
}

class _MarkMessageAsReadProviderElement
    extends AutoDisposeFutureProviderElement<void>
    with MarkMessageAsReadRef {
  _MarkMessageAsReadProviderElement(super.provider);

  @override
  String get messageId => (origin as MarkMessageAsReadProvider).messageId;
}

// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
