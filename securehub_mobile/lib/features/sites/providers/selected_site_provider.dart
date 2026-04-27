import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'sites_provider.dart';
import '../../../core/auth/auth_notifier.dart';

part 'selected_site_provider.g.dart';

@riverpod
class SelectedSite extends _$SelectedSite {
  @override
  String? build() {
    // We don't initialize here because siteList is async.
    // The UI or a listener will handle the initial selection.
    return null;
  }

  void select(String siteId) {
    state = siteId;
  }
}

@riverpod
String? currentSiteId(Ref ref) {
  final authState = ref.watch(authNotifierProvider);
  if (authState is! AuthAuthenticated) return null;

  final manualSelection = ref.watch(selectedSiteProvider);
  if (manualSelection != null) return manualSelection;

  // Fallback to the first site in the list if no manual selection exists.
  final sitesAsync = ref.watch(siteListProvider);
  return sitesAsync.when(
    data: (sites) => sites.isNotEmpty ? sites.first.id : null,
    loading: () => null,
    error: (_, _) => null,
  );
}
