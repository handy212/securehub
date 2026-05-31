import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/client_guarding_api.dart';
import '../models/client_guarding_models.dart';

final clientGuardingSnapshotProvider =
    FutureProvider.autoDispose<ClientGuardingSnapshot>((ref) async {
      return ref.watch(clientGuardingApiProvider).fetchSnapshot();
    });
